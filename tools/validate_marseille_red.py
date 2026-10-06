"""Reference audits and a bounded interpreter for the new route's actual scripts.

This exercises eligibility, one-time payments, clocks and diplomatic rejection;
it does not substitute for the HOI4 engine, UI or an actual save-game playthrough.
"""
from pathlib import Path
from copy import deepcopy
import json
import re
from hoi4_script import parse, entries, scalar, one, walk

ROOT=Path(__file__).resolve().parent.parent
MOD=ROOT/'mod'


def shape(rows):
    return [(r.key,r.operator,shape(r.value) if isinstance(r.value,list) else r.value) for r in rows]


def shared_nodes(mod=MOD):
    result={}
    for p in (mod/'common/national_focus').glob('*.txt'):
        for n in entries(parse(p.read_text(encoding='utf-8-sig')),'shared_focus'):
            ident=scalar(n.value,'id');assert ident not in result,ident
            result[ident]=n
    return result


def generic_equivalent(mod, old):
    """Compare every original node after removing only Marseille-only additions."""
    before=one(parse(old),'focus_tree').value
    after=one(parse((mod/'common/national_focus/SoF_generic.txt').read_text(encoding='utf-8-sig')),'focus_tree').value
    if not entries(after,'shared_focus'):
        return shape(before)==shape(after)
    if shape([r for r in before if r.key!='focus'])!=shape([r for r in after if r.key!='shared_focus']):return False
    base=entries(before,'focus');shared=shared_nodes(mod)
    roots=[scalar(n.value,'id') for n in base if not entries(n.value,'prerequisite')]
    if roots!=[r.value for r in entries(after,'shared_focus')]:return False
    for original in base:
        ident=scalar(original.value,'id');new=deepcopy(shared[ident].value)
        for a in entries(new,'available'):
            a.value=[r for r in a.value if r.key!='sof_mrs_red_public_allowed']
            a.value=[r for r in a.value if not (r.key=='OR' and any(v.key=='amount_research_slots' for v in walk(r.value)))]
        def restore_research(rows):
            result=[]
            for r in rows:
                if r.key=='if' and isinstance(r.value,list) and any(v.key=='amount_research_slots' for v in walk(r.value)) and entries(r.value,'add_research_slot'):
                    result.extend(entries(r.value,'add_research_slot'))
                else:
                    if isinstance(r.value,list):r.value=restore_research(r.value)
                    result.append(r)
            return result
        new=restore_research(new)
        if not entries(original.value,'available'):
            new=[r for r in new if not (r.key=='available' and not r.value)]
        new=[r for r in new if not (r.key=='offset' and scalar(r.value,'x')=='80' and any(v.key=='original_tag' and v.value=='MRS' for v in walk(r.value)))]
        if shape(new)!=shape(original.value):return False
    return True


class Scripts:
    def __init__(self):
        self.effects={};self.triggers={};self.events={}
        for group,registry in [('scripted_effects',self.effects),('scripted_triggers',self.triggers)]:
            for p in (MOD/'common'/group).glob('*.txt'):
                registry.update({r.key:r.value for r in parse(p.read_text(encoding='utf-8-sig')) if r.key and isinstance(r.value,list)})
        for e in entries(parse((MOD/'events/sof_mrs_red.txt').read_text(encoding='utf-8')),'country_event'):
            self.events[scalar(e.value,'id')]=e.value


class World:
    def __init__(self,scripts):
        self.s=scripts;self.day=0;self.events=[];self.railways=[];self.wargoals=[];self.bonuses=[]
        self.countries={};self.states={}
        self.country('MRS',communism=0.35)
        self.country('LYO',communism=0.50)
        self.state(463,'MRS',civ=3,mil=2,cores={'MRS'})
        self.state(336,'LYO',civ=2,mil=1,cores={'LYO'})

    def country(self,tag,**values):
        c=dict(kind='country',tag=tag,original_tag=tag,is_subject=False,has_capitulated=False,government='democratic',stability=0.50,political_power=300,
               manpower=50000,amount_research_slots=2,tree='sof_mrs_red' if tag=='MRS' else 'sof_generic',cap=463 if tag=='MRS' else 336,
               flags={},vars={},ideas={},completed=set(),characters={'MRS_henri_tasso'} if tag=='MRS' else set(),stock={'infantry_equipment':1000,'support_equipment':100},
               war=False,defensive=False,faction=None,opinions={},neighbors={'LYO'} if tag=='MRS' else {'MRS'},leader=None,resources={})
        c.update(values);self.countries[tag]=c;return c

    def state(self,sid,owner,**values):
        s=dict(kind='state',id=sid,owner=owner,controller=owner,flags={},vars={},cores=set(),civ=0,mil=0,dock=0,slots=10,resources={},coastal=sid==463,resistance=0,has_resistance=False,naval_base=1 if sid==463 else 0)
        s.update(values);self.states[sid]=s;return s

    def ctx(self,current='MRS',root='MRS',sender=None,prev=None):
        def obj(v):
            if isinstance(v,dict):return v
            if v is None:return None
            if isinstance(v,int):return self.states[v]
            return self.countries[v]
        return dict(cur=obj(current),root=obj(root),sender=obj(sender),prev=obj(prev))

    def nested(self,ctx,current):return dict(ctx,cur=current,prev=ctx['cur'])

    def target(self,value,ctx):
        if value in ['ROOT','FROM','PREV','THIS']:return ctx[dict(ROOT='root',FROM='sender',PREV='prev',THIS='cur')[value]]
        if value.isdigit():return self.states.get(int(value))
        return self.countries.get(value)

    def flag(self,c,name):
        if name not in c['flags']:return None
        birth,expiry=c['flags'][name]
        if expiry is not None and self.day>=expiry:del c['flags'][name];return None
        return birth

    def number(self,v,ctx):
        try:return float(v.strip('"'))
        except ValueError:return ctx['cur']['vars'].get(v,0)

    @staticmethod
    def compare(a,b,op='='):
        return {'=':lambda:a==b,'>':lambda:a>b,'<':lambda:a<b,'>=':lambda:a>=b,'<=':lambda:a<=b,'!=':lambda:a!=b}[op]()

    def cond(self,rows,ctx):return all(self.test(r,ctx) for r in rows)

    def test(self,r,ctx):
        k,v=r.key,r.value;c=ctx['cur']
        if k in ['AND','OR','NOT']:
            values=[self.test(t,ctx) for t in v]
            return all(values) if k=='AND' else any(values) if k=='OR' else not all(values)
        if k in ['ROOT','FROM','PREV','THIS'] or (k and (k.isdigit() or k in self.countries)):
            t=self.target(k,ctx);return t is not None and self.cond(v,self.nested(ctx,t))
        if k in self.s.triggers:
            answer=self.cond(self.s.triggers[k],ctx);return answer if v=='yes' else not answer
        if k=='always':return v=='yes'
        if k=='capital_scope':return c['cap'] in self.states and self.cond(v,self.nested(ctx,self.states[c['cap']]))
        if k=='custom_trigger_tooltip':return self.cond([t for t in v if t.key!='tooltip'],ctx)
        if k=='check_variable':
            return all(self.compare(c['vars'].get(t.key,0),self.number(t.value,ctx),t.operator) for t in v)
        if k in ['has_country_flag','has_state_flag']:
            if isinstance(v,str):return self.flag(c,v) is not None
            birth=self.flag(c,scalar(v,'flag'))
            return birth is not None and all(self.compare(self.day-birth,self.number(t.value,ctx),t.operator) for t in v if t.key=='days')
        if k=='has_completed_focus':return v in c['completed']
        if k=='has_character':return v in c['characters']
        if k=='has_idea':return v in c['ideas'] and (c['ideas'][v] is None or c['ideas'][v]>self.day)
        if k=='has_focus_tree':return c['tree']==v
        if k=='has_government':return c['government']==v
        if k in ['is_subject','has_capitulated']:return c[k]==(v=='yes')
        if k=='has_war':return c['war']==(v=='yes')
        if k=='has_defensive_war':return c['defensive']==(v=='yes')
        if k=='is_in_faction':return (c['faction'] is not None)==(v=='yes')
        if k=='is_faction_leader':return bool(c.get('faction_leader'))==(v=='yes')
        if k=='original_tag':return c['original_tag']==v
        if k=='tag':return c['tag']==self.target(v,ctx)['tag'] if self.target(v,ctx) else c['tag']==v
        if k=='state':return c['id']==int(v)
        if k=='is_coastal':return c['coastal']==(v=='yes')
        if k=='has_resistance':return c['has_resistance']==(v=='yes')
        if k in ['resistance','naval_base']:return self.compare(c[k],self.number(v,ctx),r.operator)
        if k in ['is_owned_by','is_controlled_by','is_fully_controlled_by','is_core_of']:
            target=self.target(v,ctx)
            if target is None:return False
            return target['tag'] in c['cores'] if k=='is_core_of' else c['owner' if k=='is_owned_by' else 'controller']==target['tag']
        if k=='any_owned_state':return any(self.cond(v,self.nested(ctx,s)) for s in self.states.values() if s['owner']==c['tag'])
        if k=='any_other_country':return any(self.cond(v,self.nested(ctx,n)) for n in self.countries.values() if n!=c)
        if k=='has_equipment':return all(self.compare(c['stock'].get(t.key,0),self.number(t.value,ctx),t.operator) for t in v)
        if k=='has_opinion':
            target=self.target(scalar(v,'target'),ctx)
            return self.compare(c['opinions'].get(target['tag'],0),self.number(one(v,'value').value,ctx),one(v,'value').operator)
        if k=='is_neighbor_of':return self.target(v,ctx)['tag'] in c['neighbors']
        if k=='is_in_faction_with':
            target=self.target(v,ctx);return target is not None and c['faction'] is not None and c['faction']==target['faction']
        if k=='has_war_with':return False
        if k=='free_building_slots':return c['slots']>0
        if k in ['num_of_civilian_factories','num_of_military_factories','num_of_owned_states']:
            owned=[s for s in self.states.values() if s['owner']==c['tag']]
            value=len(owned) if k=='num_of_owned_states' else sum(s['civ' if k=='num_of_civilian_factories' else 'mil'] for s in owned)
            return self.compare(value,self.number(v,ctx),r.operator)
        if k in ['communism','political_power','manpower','amount_research_slots']:return self.compare(c[k],self.number(v,ctx),r.operator)
        if k=='has_stability':return self.compare(c['stability'],self.number(v,ctx),r.operator)
        if k=='impassable':return v=='no'
        raise AssertionError('Unsupported test primitive: '+str(k))

    def execute(self,rows,ctx):
        branch=False
        for r in rows:
            k,v=r.key,r.value;c=ctx['cur']
            if k in ['if','else_if','else']:
                eligible=k=='if' or not branch
                condition=eligible and (k=='else' or self.cond(one(v,'limit').value,ctx))
                if k=='if':branch=False
                if condition:self.execute([t for t in v if t.key!='limit'],ctx);branch=True
                continue
            if k in ['ROOT','FROM','PREV','THIS'] or (k and (k.isdigit() or k in self.countries)):
                target=self.target(k,ctx)
                if target is not None:self.execute(v,self.nested(ctx,target))
            elif k in self.s.effects:self.execute(self.s.effects[k],ctx)
            elif k in ['set_country_flag','set_state_flag']:
                name=v if isinstance(v,str) else scalar(v,'flag')
                days=None if isinstance(v,str) else scalar(v,'days')
                c['flags'][name]=(self.day,None if days is None else self.day+int(days))
            elif k in ['clr_country_flag','clr_state_flag']:c['flags'].pop(v,None)
            elif k in ['set_variable','add_to_variable']:
                for t in v:c['vars'][t.key]=self.number(t.value,ctx)+(c['vars'].get(t.key,0) if k=='add_to_variable' else 0)
            elif k=='clamp_variable':
                name=scalar(v,'var');c['vars'][name]=max(float(scalar(v,'min',0)),min(float(scalar(v,'max',100)),c['vars'].get(name,0)))
            elif k in ['add_ideas','remove_ideas']:
                if k=='add_ideas':c['ideas'][v]=None
                else:c['ideas'].pop(v,None)
            elif k=='add_timed_idea':c['ideas'][scalar(v,'idea')]=self.day+int(scalar(v,'days'))
            elif k in ['every_owned_state','random_owned_controlled_state','every_country']:
                possible=list(self.countries.values()) if k=='every_country' else [s for s in self.states.values() if s['owner']==c['tag']]
                limits=entries(v,'limit')
                candidates=[t for t in possible if not limits or self.cond(limits[0].value,self.nested(ctx,t))]
                for target in candidates[:1] if k.startswith('random') else candidates:self.execute([t for t in v if t.key!='limit'],self.nested(ctx,target))
            elif k=='add_political_power':c['political_power']+=float(v)
            elif k=='add_stability':c['stability']+=float(v)
            elif k=='add_popularity':c[scalar(v,'ideology')]=c.get(scalar(v,'ideology'),0)+float(scalar(v,'popularity'))
            elif k=='add_equipment_to_stockpile':
                typ=scalar(v,'type');c['stock'][typ]=c['stock'].get(typ,0)+float(scalar(v,'amount'))
            elif k=='add_research_slot':c['amount_research_slots']+=int(v)
            elif k=='recruit_character':c['characters'].add(v)
            elif k=='promote_character':c['leader']=v
            elif k=='set_politics':c['government']=scalar(v,'ruling_party')
            elif k=='set_cosmetic_tag':c['cosmetic']=v
            elif k=='drop_cosmetic_tag':c.pop('cosmetic',None)
            elif k=='set_capital':c['cap']=int(scalar(v,'state'))
            elif k=='load_focus_tree':c['tree']=scalar(v,'tree')
            elif k=='country_event':self.events.append((c.get('tag'),scalar(v,'id')))
            elif k in ['add_tech_bonus','add_doctrine_cost_reduction']:self.bonuses.append((c['tag'],k,shape(v)))
            elif k=='add_building_construction':
                key=dict(industrial_complex='civ',arms_factory='mil',dockyard='dock')[scalar(v,'type')]
                c[key]+=int(scalar(v,'level'));c['slots']-=int(scalar(v,'level'))
            elif k=='add_resource':
                key=scalar(v,'type');c['resources'][key]=c['resources'].get(key,0)+int(scalar(v,'amount'))
            elif k=='build_railway':self.railways.append([int(n.value) for n in one(v,'path').value])
            elif k=='create_wargoal':self.wargoals.append((c['tag'],self.target(scalar(v,'target'),ctx)['tag'],int(scalar(v,'expire'))))
            elif k=='annex_country':
                target=self.target(scalar(v,'target'),ctx)
                for s in self.states.values():
                    if s['owner']==target['tag']:
                        s['owner']=c['tag']
                        if s['controller']==target['tag']:s['controller']=c['tag']
            elif k=='add_to_faction':self.target(v,ctx)['faction']=c['faction']
            elif k=='create_faction':c['faction']=v;c['faction_leader']=True
            elif k=='start_resistance':c['has_resistance']=True
            elif k=='set_resistance':c['resistance']=float(v)
            elif k=='add_opinion_modifier':
                target=self.target(scalar(v,'target'),ctx);c['opinions'][target['tag']]=c['opinions'].get(target['tag'],0)+30
            elif k in ['set_rule','add_war_support','army_experience','navy_experience','custom_effect_tooltip','add_dynamic_modifier','remove_dynamic_modifier','division_template']:
                pass
            else:raise AssertionError('Unsupported effect primitive: '+str(k))

    def effect(self,name,current='MRS',root='MRS',sender=None):self.execute(self.s.effects[name],self.ctx(current,root,sender))


def audit(check,loc=None,gfx=None):
    if (ROOT/'design/marseille-focus-art.json').is_file():
        from marseille_focus_art import audit as audit_art
        audit_art(check, gfx)
    s=Scripts();tree=one(parse((MOD/'common/national_focus/sof_mrs_red.txt').read_text(encoding='utf-8')),'focus_tree').value
    nodes=entries(tree,'focus');ids={scalar(n.value,'id'):n.value for n in nodes};shared=shared_nodes()
    check(len(nodes)==52 and len(ids)==52,'Marseille has 52 unique new focuses')
    public=json.loads((ROOT/'design/marseille-public-focuses.json').read_text(encoding='utf-8'))
    check(set(public['ids'])<=shared.keys() and len(public['ids'])==153,'Marseille retains 153 shared generic IDs')
    check([r.value for r in entries(tree,'shared_focus')]==public['roots'],'Marseille references shared branch roots only')
    reachable=set(public['roots'])
    while True:
        before=len(reachable)
        for k,n in shared.items():
            if any(r.value in reachable for group in entries(n.value,'prerequisite') for r in entries(group.value,'focus')):reachable.add(k)
        if len(reachable)==before:break
    check(set(public['ids'])<=reachable,'Every public node is reachable from the eight shared roots')
    check(all(r.value in shared for r in entries(tree,'shared_focus')),'Public shared references resolve')
    selector=one(tree,'country').value
    check(scalar(selector,'factor')=='0' and any(r.key=='original_tag' and r.value=='MRS' for r in walk(selector)),'Only original MRS selects the new tree')
    mapping={k:[r.value for p in entries(v,'prerequisite') for r in entries(p.value,'focus')] for k,v in ids.items()}
    visited=set();active=set()
    def visit(k):
        check(k not in active,'No prerequisite cycle: '+k)
        if k in visited or k in active:return
        active.add(k)
        for dep in mapping[k]:
            check(dep in ids or dep in shared,'Prerequisite exists: '+dep)
            if dep in ids:visit(dep)
        active.remove(k);visited.add(k)
    for k,v in ids.items():
        visit(k)
        for dep in mapping[k]:
            if dep in ids:check(int(scalar(ids[dep],'y'))<int(scalar(v,'y')),'Prerequisite is above its dependent: '+k+' '+dep)
        for group in entries(v,'mutually_exclusive'):
            for r in entries(group.value,'focus'):
                check(any(other.value==k for g in entries(ids[r.value],'mutually_exclusive') for other in entries(g.value,'focus')),'Symmetric route exclusion: '+k)
        check(any(r.key=='has_country_flag' and isinstance(r.value,str) and r.value.startswith('sof_mrs_red_paid_') for r in walk(one(v,'completion_reward').value)),'Reward payment guard: '+k)
        for r in walk(v):
            if r.key in ['create_unit','add_core_of','declare_war_on']:check(False,'Forbidden direct reward: '+k+' '+r.key)
        if gfx is not None:check(scalar(v,'icon') in gfx,'New focus icon exists: '+k)
    all_loc={}
    for p in (MOD/'localisation/simp_chinese').rglob('*.yml'):
        all_loc.update(re.findall(r'(?m)^ ([^\s:]+):\d* "((?:[^"\\]|\\.)*)"',p.read_text(encoding='utf-8-sig')))
    for k in ids:check(k in all_loc and k+'_desc' in all_loc,'Focus title and description: '+k)
    check((MOD/'localisation/simp_chinese/replace/sof_mrs_red_l_simp_chinese.yml').read_bytes().startswith(b'\xef\xbb\xbf'),'Marseille Chinese localization has BOM')
    legacy=json.loads((ROOT/'design/marseille-reward-guards.json').read_text(encoding='utf-8'))
    for name in legacy['guarded_effects']:
        check(any(r.key=='sof_mrs_red_public_allowed' for r in walk(s.effects[name])),'Legacy reward is guarded: '+name)
    for e in s.events.values():
        for option in entries(e,'option'):
            check(not any(r.key=='add_core_of' for r in walk(option.value)),'Diplomatic option does not grant cores')
    routes=json.loads((ROOT/'design/marseille-railway-paths.json').read_text(encoding='utf-8'))['routes']
    check(len(routes)>200,'Owned-only railway paths cover mainland France')
    # Exercise actual completion code, not separately reimplemented outcomes.
    w=World(s);c=w.countries['MRS']
    def finish(world,code):
        ident='SOF_MRS_RED_'+code
        world.execute(one(ids[ident],'completion_reward').value,world.ctx())
        world.countries['MRS']['completed'].add(ident)
    finish(w,'A1');finish(w,'A2');finish(w,'A3');finish(w,'A4')
    check(c['government']=='communism' and c['leader']=='MRS_jean_cristofol','Power transfer recruits and promotes Cristofol')
    pp=c['political_power'];finish(w,'A4');check(c['political_power']==pp,'Power transfer cannot charge or grant twice')
    check(abs(c['communism']-.50)<1e-9,'Starting 35 percent reaches 50 after organization')
    finish(w,'A5');finish(w,'P1');finish(w,'P2')
    check('sof_mrs_red_central_2' in c['ideas'] and 'sof_mrs_red_central_1' not in c['ideas'],'Central organization upgrades without stacking')
    c['vars']['sof_mrs_red_tension']=95;w.effect('sof_mrs_red_refresh_tension')
    check('sof_mrs_red_crisis_pending' in c['flags'],'High tension issues a warning instead of immediate crisis')
    before=c['political_power'];w.day+=89;w.effect('sof_mrs_red_resolve_crisis')
    check(c['political_power']==before,'Crisis does not settle before 90 days')
    w.day+=1;w.execute(one(s.events['sof_mrs_red.15'],'immediate').value,w.ctx())
    check(c['political_power']==before-75 and 'sof_mrs_red_paralysis' in c['ideas'],'90-day crisis charges once and adds finite recovery')
    check('sof_mrs_red_dispute' not in c['ideas'] and 'sof_mrs_red_distrust' not in c['ideas'],'Recovery does not stack interval output penalties')
    before=c['political_power'];w.effect('sof_mrs_red_resolve_crisis');check(c['political_power']==before,'Recovery prevents duplicate crisis settlement')
    q=World(s);finish(q,'A1');finish(q,'A2');finish(q,'A4');finish(q,'A5');qc=q.countries['MRS']
    qc['vars']['sof_mrs_red_tension']=95;q.effect('sof_mrs_red_refresh_tension');qc['vars']['sof_mrs_red_tension']=80;q.effect('sof_mrs_red_refresh_tension')
    check('sof_mrs_red_crisis_pending' not in qc['flags'],'Lowering tension cancels the crisis warning')
    q.day=179;qc['vars']['sof_mrs_red_tension']=20
    check(not q.cond(one(ids['SOF_MRS_RED_P8'],'available').value,q.ctx()),'Emergency status cannot end before day 180')
    q.day=180;check(q.cond(one(ids['SOF_MRS_RED_P8'],'available').value,q.ctx()),'Emergency status can end on day 180')
    finish(q,'P8');before=qc['vars']['sof_mrs_red_tension'];q.effect('sof_mrs_red_monthly')
    check(qc['vars']['sof_mrs_red_tension']==before,'Constitutional stabilization stops passive tension growth')
    finish(q,'E2');q.day=544
    check(not q.cond(one(ids['SOF_MRS_RED_E8'],'available').value,q.ctx()),'Five-year-plan inspection requires a full 365 days')
    q.day=545;check(q.cond(one(ids['SOF_MRS_RED_E8'],'available').value,q.ctx()),'Plan inspection opens after 365 days')
    finish(q,'E8');finish(q,'E10');q.effect('sof_mrs_red_restore_ideas')
    check('sof_mrs_red_plan_heavy' in qc['ideas'] and 'sof_mrs_red_plan_1' not in qc['ideas'] and 'sof_mrs_red_plan_2' not in qc['ideas'],'Plan family retains only the selected highest stage')
    q.state(446,'MRS');finish(q,'E5');amount=q.states[446]['resources'].get('aluminium',0);finish(q,'E5')
    check(amount==4 and q.states[446]['resources'].get('aluminium')==4,'Mine expansion is site-specific and one-time')
    before=qc['political_power'];qc['government']='democratic';finish(q,'P1')
    check(qc['political_power']==before,'Government change blocks communist completion effects')
    d=World(s);dc=d.countries['MRS'];tc=d.countries['LYO']
    dc['government']='communism';dc['flags']['sof_mrs_red_government']=(0,None);dc['flags']['sof_mrs_red_diplomatic_pending']=(0,30);tc['flags']['sof_mrs_red_offer_target']=(0,30)
    before=dc['political_power'];pop=tc['communism'];owned=deepcopy(d.states)
    refusal=entries(s.events['sof_mrs_red.9'],'option')[1].value
    d.execute([r for r in refusal if r.key not in ['name','ai_chance']],d.ctx('LYO','LYO','MRS'))
    check(dc['political_power']==before+20 and tc['communism']==pop and d.states==owned,'Refused outreach refunds only the specified payment and changes no target policy or land')
    d.execute([r for r in refusal if r.key not in ['name','ai_chance']],d.ctx('LYO','LYO','MRS'))
    check(dc['political_power']==before+20,'Stale refusal cannot repeat the refund')
    tc['government']='communism';dc['faction']=tc['faction']='league';tc['opinions']['MRS']=80
    dc['flags']['sof_mrs_red_diplomatic_pending']=(0,30);tc['flags']['sof_mrs_red_offer_target']=(0,30)
    check(d.cond(s.triggers['sof_mrs_red_federation_valid'],d.ctx('LYO','LYO','MRS')),'Eligible federation can be accepted by its own government')
    d.effect('sof_mrs_red_accept_federation','LYO','LYO','MRS')
    check(d.states[336]['owner']=='MRS' and 'MRS' not in d.states[336]['cores'],'Accepted federation transfers ownership without instant cores')
    check('sofzh_occupation_registered' in d.states[336]['flags'] and 'sofzh_occupation_recent' in d.states[336]['flags'],'Federated state enters the existing control-duration registration flow')


def main():
    checks=0;errors=[]
    def check(ok,message):
        nonlocal checks
        checks+=1
        if not ok:errors.append(message)
    audit(check)
    result=dict(ok=not errors,checks=checks,errors=errors,game_engine_verified=False,scope='Actual-script interpreter and reference audit; no game execution')
    (ROOT/'docs/MARSEILLE-RED-VERIFICATION.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False));raise SystemExit(0 if result['ok'] else 1)


if __name__=='__main__':main()
