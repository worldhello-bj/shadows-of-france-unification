"""Audit the actual GUI, read-only adapters and scoped Clausewitz fixtures.

Fixtures interpret the checked-in script; they do not execute the HOI4 engine.
"""
from pathlib import Path
import argparse
import hashlib
import json
import math
import re
from PIL import Image
from hoi4_script import parse, one, entries, scalar, walk
from build_ideology_panel import ROOT, MOD, PASS, PROFILES, DEFAULTS, GUI_REL, SYNC_REL


def normalized(rows):
    return [(r.key, r.operator, normalized(r.value) if isinstance(r.value, list) else r.value) for r in rows]


class Fixture:
    """Only the data adapter's documented variable and trigger operations."""
    def __init__(self, support, ruling='democratic', leader='liberalism', representatives=None, ai=False):
        self.support = dict(zip(DEFAULTS, support))
        self.ruling, self.leader, self.ai = ruling, leader, ai
        self.characters = representatives or []
        self.variables = {'sofzh_chart_dirty': 7, 'sofzh_chart_liberal': 99}
        self.temps = {}
        self.arrays = {'sofzh_chart_pie': [99] * 130}
        self.triggers = {r.key: r.value for r in parse((MOD/'common/scripted_triggers/sofzh_ideology_panel.txt').read_text())}
        self.effects = one(parse((MOD/'common/scripted_effects/sofzh_ideology_panel.txt').read_text()), 'sofzh_refresh_ideology_chart').value
        self.executed = 0

    def number(self, token):
        if token.startswith('party_popularity_100@'):
            return self.support[token.split('@')[1]]
        if '^' in token:
            name, index = token.split('^')
            return self.arrays[name][int(self.number(index))]
        try:
            return float(token)
        except ValueError:
            return self.temps.get(token, self.variables.get(token, 0))

    def trigger(self, rows, scopes=('country',)):
        def test(r):
            key, value = r.key, r.value
            if key in ('OR', 'AND', 'NOT'):
                found = [test(x) for x in value]
                return any(found) if key == 'OR' else not any(found) if key == 'NOT' else all(found)
            if key == 'is_ai': return self.ai == (value == 'yes')
            if key == 'has_government': return self.ruling == value
            if key == 'has_country_leader_ideology': return self.leader == value
            if key == 'has_ideology': return value in scopes[-1]['ideologies']
            if key == 'any_character':
                return any(self.trigger(value, scopes+(c,)) for c in self.characters)
            if key == 'PREV':
                return self.trigger(value, scopes+(scopes[-2],))
            if key == 'has_country_leader':
                character = scopes[-2] if scalar(value, 'character') == 'PREV' else None
                return bool(character and character['active'])
            if key == 'check_variable':
                a,b = self.number(scalar(value,'var')),self.number(scalar(value,'value'))
                return {'equals':a==b, 'greater_than':a>b, 'less_than':a<b}[scalar(value,'compare','equals')]
            if key in self.triggers:
                return self.trigger(self.triggers[key], scopes) == (value=='yes')
            raise AssertionError(('Unhandled fixture trigger',key))
        return all(test(r) for r in rows)

    def run(self, rows=None):
        previous_if = False
        for r in self.effects if rows is None else rows:
            key,value = r.key,r.value
            self.executed += 1
            assert self.executed < 5000, 'Unbounded adapter'
            if key in ('if','else_if'):
                matched = (key=='if' or not previous_if) and self.trigger(one(value,'limit').value)
                if matched: self.run([x for x in value if x.key!='limit'])
                previous_if = matched if key=='if' else previous_if or matched
                continue
            if key == 'clear_array': self.arrays[value]=[]; continue
            if key == 'resize_array':
                self.arrays[scalar(value,'array')]=[self.number(scalar(value,'value'))]*int(self.number(scalar(value,'size')))
                continue
            if key == 'for_loop_effect':
                start,end = int(self.number(scalar(value,'start'))),int(self.number(scalar(value,'end')))
                assert 0 <= start <= end <= 100, ('Pie range',start,end)
                for index in range(start,end):
                    self.temps[scalar(value,'value','v')]=index
                    self.run([x for x in value if x.key not in ('start','end','value')])
                continue
            if key.startswith('clamp_'):
                name=scalar(value,'var')
                target=self.temps if 'temp' in key else self.variables
                target[name]=min(self.number(scalar(value,'max')),max(self.number(scalar(value,'min')),self.number(name)))
                continue
            if key == 'round_temp_variable':
                self.temps[value]=math.floor(self.number(value)+0.5); continue
            assert isinstance(value,list) and len(value)==1, ('Unexpected mutation',key)
            name,operand = value[0].key,self.number(value[0].value)
            old=self.number(name)
            new=(operand if key.startswith('set_') else old+operand if key.startswith('add_to_') else old/operand if key.startswith('divide_') else old*operand if key.startswith('multiply_') else None)
            assert new is not None, ('Unexpected mutation',key)
            if '^' in name:
                array,index=name.split('^');self.arrays[array][int(self.number(index))]=new
            else:
                (self.temps if 'temp' in key else self.variables)[name]=new
        return self


def fixtures(check):
    count=0
    def scenario(support, ruling='democratic', leader='liberalism', representatives=None):
        nonlocal count
        f=Fixture(support,ruling,leader,representatives).run();count+=1
        raw=[min(100,max(0,v)) for v in support];total=sum(raw)
        expected=[100*v/total if total else 0 for v in raw]
        values=[f.variables['sofzh_chart_'+p[0]] for p in PROFILES]
        check(abs(sum(values)-(100 if total else 0))<1e-7, f'Fixture {count}: support total')
        for group,weight in zip(DEFAULTS,expected):
            check(abs(sum(v for v,p in zip(values,PROFILES) if p[1]==group)-weight)<1e-7, f'Fixture {count}: preserved {group} share')
        pie=f.arrays['sofzh_chart_pie']
        check(len(pie)==100 and all(1<=v<=13 and v==int(v) for v in pie), f'Fixture {count}: exactly 100 valid frames')
        for i,p in enumerate(PROFILES,1):
            check(abs(pie.count(i)-f.variables['sofzh_chart_'+p[0]])<=1.000001,f'Fixture {count}: rounding bound {p[0]}')
        if total:check(13 not in pie,f'Fixture {count}: no empty wedges')
        else:check(pie==[13]*100,f'Fixture {count}: zero-support empty disc')
        return f
    for weights in [(30,35,15,20),(100,0,0,0),(0,100,0,0),(0,0,100,0),(0,0,0,100),(0,0,0,0),
                    (33.333,33.333,33.334,0),(24.49,25.49,25.49,24.53),(0.01,0.01,0.01,99.97),
                    (99.49,0.51,0,0),(-10,130,0,0),(0.1,0.2,0.3,0.4)]:
        scenario(weights)
    for i,p in enumerate(PROFILES,1):
        for alias in p[3].split():
            f=scenario((30,35,15,20),p[1],alias)
            check(f.variables['sofzh_chart_ruling']==i,'Ruling profile alias: '+alias)
            check(f.variables['sofzh_chart_'+p[0]]>0,'Ruling support alias: '+alias)
        # Mutated/generated opposition leaders, with a stale inactive rival.
        ruling='democratic' if p[1]!='democratic' else 'neutrality'
        leader='liberalism' if ruling=='democratic' else 'sof_localism'
        representatives=[dict(ideologies=p[3].split(),active=True),dict(ideologies=['conservatism','nazism','sof_monarchism'],active=False)]
        f=scenario((30,35,15,20),ruling,leader,representatives)
        check(f.variables['sofzh_chart_'+p[0]]>0,'Opposition leader: '+p[0])
    for group,default in DEFAULTS.items():
        f=scenario((25,25,25,25),group,'unknown_legacy_subtype')
        check(f.variables['sofzh_chart_ruling']==default,'Unknown subtype fallback: '+group)
    f=scenario((30,35,15,20),'democratic','socialism',[
        dict(ideologies=['marxism'],active=True),dict(ideologies=['despotism'],active=True)])
    check([f.variables['sofzh_chart_'+p] for p in ('social','revolutionary','fascist','authoritarian')]==[30,35,15,20],'Actual Marseille party profile mapping')
    stable={k:v for k,v in f.variables.items() if k!='sofzh_chart_dirty'};pie=list(f.arrays['sofzh_chart_pie'])
    f.run()
    check(stable=={k:v for k,v in f.variables.items() if k!='sofzh_chart_dirty'} and pie==f.arrays['sofzh_chart_pie'],'Repeated refresh is idempotent except dirty counter')
    f.leader='conservatism';f.run()
    check(f.variables['sofzh_chart_social']==0 and f.variables['sofzh_chart_conservative']==30,'Paused route change clears the former profile')
    ai=Fixture((25,25,25,25),ai=True);before=dict(ai.variables);ai.run()
    check(ai.variables==before and ai.arrays['sofzh_chart_pie']==[99]*130,'AI refresh has no writes')
    return count


def audit(check):
    data=json.loads((ROOT/'design/ideology-panel.json').read_text(encoding='utf-8'))
    check(len(data['profiles'])==12 and len({p['color'] for p in data['profiles']})==12,'Twelve distinct sub-ideology colors')
    for rel in data['files']:
        check((MOD/rel).is_file(),'Panel file exists: '+rel)
        if rel.endswith(('.txt','.gui','.gfx')):parse((MOD/rel).read_text(encoding='utf-8-sig'))
    subtypes={r.key for group in one(parse((MOD/'common/ideologies/00_ideologies.txt').read_text()),'ideologies').value for r in one(group.value,'types').value}
    aliases=[a for p in data['profiles'] for a in p['aliases']]
    check(set(aliases)==subtypes and len(aliases)==len(set(aliases)),'Every engine sub-ideology maps to exactly one existing profile')
    effect=parse((MOD/'common/scripted_effects/sofzh_ideology_panel.txt').read_text())
    forbidden={'add_ideas','remove_ideas','add_political_power','set_popularities','add_popularity','set_politics','set_country_leader_ideology','create_country_leader'}
    check(not any(n.key in forbidden for n in walk(effect)),'Chart adapter does not modify political gameplay')
    for n in walk(effect):
        if n.key in {'set_variable','add_to_variable','multiply_variable','divide_variable'}:
            check(all(v.key.startswith('sofzh_chart_') for v in n.value),'Persistent writes are confined to panel caches')
    gui=one(one(parse((MOD/'interface/sofzh_ideology_panel.gui').read_text()),'guiTypes').value,'containerWindowType').value
    nodes={scalar(n.value,'name').strip('"'):n.value for n in walk(gui) if isinstance(n.value,list) and scalar(n.value,'name')}
    sg=one(one(parse((MOD/'common/scripted_guis/sofzh_ideology_panel.txt').read_text()),'scripted_gui').value,'sofzh_ideology_panel_gui').value
    check(scalar(sg,'parent_window_token')=='politics_tab' and scalar(sg,'context_type')=='player_context','Chart attached to the actual politics tab')
    check(entries(one(sg,'effects').value,'sofzh_chart_refresh_click') and 'sofzh_chart_refresh' in nodes,'Paused-save refresh is a real bound button')
    props=one(sg,'properties').value
    check(len(props)==100,'All 100 segments have scripted frame bindings')
    for i in range(100):
        name='sofzh_chart_piece_'+str(i)
        check(name in nodes and scalar(one(props,name).value,'frame')=='sofzh_chart_pie^'+str(i),'Segment binding '+str(i))
        check(abs(float(scalar(nodes[name],'rotation'))-i*math.tau/100)<1e-9,'Segment rotation '+str(i))
    legend=nodes['sofzh_chart_legend'];scale=float(scalar(legend,'scale'))
    for p in data['profiles']:
        name='sofzh_chart_name_'+p['id'];row=nodes[name]
        pos=one(row,'position').value
        bottom=140-1+(float(scalar(pos,'y'))+float(scalar(row,'maxHeight')))*scale
        check(bottom<303,'Legend stays above national spirits: '+p['id'])
        check(scalar(row,'font')=='"hoi_16mbs"','Legend uses the existing Chinese font: '+p['id'])
    textures=[('segments',(6656,512),13),('swatches',(144,12),12),('disc',(128,128),1),('refresh',(54,18),3)]
    for name,size,frames in textures:
        im=Image.open(MOD/f'gfx/interface/sofzh_ideology_panel/{name}.dds').convert('RGBA')
        check(im.size==size,'DDS dimensions: '+name)
        check(im.getchannel('A').getextrema()==(0,255),'DDS transparency: '+name)
        if name=='segments':
            hashes=[hashlib.sha256(im.crop((i*512,0,(i+1)*512,512)).tobytes()).hexdigest() for i in range(frames)]
            check(len(set(hashes))==13,'Twelve unique wedge frames and transparent no-data frame')
    native_text=(MOD/GUI_REL).read_text(encoding='utf-8');native=one(parse(native_text),'guiTypes').value[0].value
    old_native=one(parse((ROOT/'references/ideology-panel'/GUI_REL).read_text(encoding='utf-8')),'guiTypes').value[0].value
    allowed={('chart_explanation','position'),('political_pie_chart','position'),('pol_faction_icon','position')}
    def strip(rows):
        result=[]
        for n in rows:
            if not isinstance(n.value,list):result.append(n);continue
            name=scalar(n.value,'name','').strip('"')
            if name in ('ideology','elections'):
                result.append(type(n)(n.key,[x for x in n.value if x.key not in ('position','font','maxWidth','maxHeight')],n.start,n.end,n.operator))
            else:
                result.append(type(n)(n.key,[x for x in strip(n.value) if (name,x.key) not in allowed],n.start,n.end,n.operator))
        return result
    check(normalized(strip(native))==normalized(strip(old_native)),'Native leaders, cabinet, focus, spirits and faction controls preserved')
    sync=one(parse((MOD/SYNC_REL).read_text()),'sofzh_sync_ideology').value
    old_sync=one(parse((ROOT/'references/ideology-panel'/SYNC_REL).read_text()),'sofzh_sync_ideology').value
    check(normalized([n for n in sync if n.key!='sofzh_refresh_ideology_chart'])==normalized(old_sync),'Existing ideology effects and Marseille guard preserved')
    check(len(entries(sync,'sofzh_refresh_ideology_chart'))==1,'Refresh runs outside the Marseille national-spirit guard')
    locpath=MOD/'localisation/simp_chinese/replace/sofzh_ideology_panel_l_simp_chinese.yml'
    check(locpath.read_bytes().startswith(b'\xef\xbb\xbf'),'New localization has UTF8 BOM')
    loc=dict(re.findall(r'^ ([^ :]+):\d* "(.*)"',locpath.read_text(encoding='utf-8-sig'),re.M))
    check(len(loc)==43,'All panel labels, percentages and tooltips localized')
    for n in walk(gui):
        if n.key in ('text','pdx_tooltip') and isinstance(n.value,str) and n.value.strip('"'):
            check(n.value.strip('"') in loc,'GUI localization resolves: '+n.value)
    return fixtures(check)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path);args=parser.parse_args()
    errors=[];checks=0
    def check(ok,message):
        nonlocal checks
        checks+=1
        if not ok:errors.append(message)
    cases=audit(check)
    report=dict(ok=not errors,checks=checks,fixture_cases=cases,errors=errors,profiles=12,game_engine_verified=False,scope='Actual-source GUI/DDS audit and interpreted data-adapter fixtures')
    if args.output:
        args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False));raise SystemExit(0 if report['ok'] else 1)


if __name__=='__main__':main()
