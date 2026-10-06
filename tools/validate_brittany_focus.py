"""Parse and exercise the authored council, isolation and territorial gates.

Scenario execution is a limited interpreter of actual game script, not HOI4.
Unknown operations fail loudly in modeled paths.
"""
from copy import deepcopy
import hashlib
import itertools
import json
import os
import re
from pathlib import Path

from hoi4_script import entries, one, parse, scalar, walk
from build_brittany_focus import ROOT, MOD, REF, REPORT, STATES, DELEGATES, BILLS, authored_nodes, GAME


def norm(rows):
    return [(r.key,r.operator,norm(r.value) if isinstance(r.value,list) else r.value) for r in rows]


class Scenario:
    def __init__(self,**kwargs):
        self.c=dict(vars={},flags={},ideas=set(),completed=set(),tree='sof_brittany',tag='REN',
                    subject=False,capitulated=False,war=False,threat=False,coast=False,
                    owned=set(),controlled=set(),ally_controlled=set(),slots=2,factories=4,pp=300,day=0,war_support=.5,characters=set(),events=[])
        self.c.update(kwargs)
        self.effects={r.key:r.value for r in parse((MOD/'common/scripted_effects/sof_brittany.txt').read_text(encoding='utf-8'))}
        self.triggers={r.key:r.value for r in parse((MOD/'common/scripted_triggers/sof_brittany.txt').read_text(encoding='utf-8'))}
        self.time_ideas={}

    def advance(self,days):
        self.c['day']+=days
        self.c['flags']={k:v for k,v in self.c['flags'].items() if v is None or v>self.c['day']}
        for k,expiry in self.time_ideas.items():
            if expiry<=self.c['day']:self.c['ideas'].discard(k)

    def number(self,value):
        try:return float(value)
        except ValueError:return self.c['vars'].get(value,0)

    def cond(self,rows):
        values=[]
        for row in rows:
            k,v=row.key,row.value
            if k=='NOT':val=not self.cond(v)
            elif k=='OR':val=any(self.cond([r]) for r in v)
            elif k in ['AND','limit']:val=self.cond(v)
            elif k=='has_country_flag':val=v in self.c['flags']
            elif k=='has_idea':val=v in self.c['ideas']
            elif k=='has_completed_focus':val=v in self.c['completed']
            elif k=='controls_state':val=int(v) in self.c['controlled']
            elif k=='has_focus_tree':val=v==self.c['tree']
            elif k=='original_tag':val=v==self.c['tag']
            elif k in ['is_subject','has_capitulated','has_war']:
                val=self.c[dict(is_subject='subject',has_capitulated='capitulated',has_war='war')[k]]==(v=='yes')
            elif k=='always':val=v=='yes'
            elif k=='check_variable':
                term=next(r for r in v if r.key not in ['var','value','compare'])
                a=self.c['vars'].get(term.key,0);b=self.number(term.value)
                val={'=':a==b,'>':a>b,'<':a<b,'>=':a>=b,'<=':a<=b,'!=':a!=b}[term.operator]
            elif k in ['amount_research_slots','num_of_factories','has_war_support','has_political_power']:
                a=self.c[dict(amount_research_slots='slots',num_of_factories='factories',has_war_support='war_support',has_political_power='pp')[k]];b=self.number(v)
                val={'=':a==b,'>':a>b,'<':a<b,'>=':a>=b,'<=':a<=b}[row.operator]
            elif k and k.isdigit():
                if any(r.key=='controller' for r in v):
                    assert scalar(one(v,'controller').value,'is_in_faction_with')=='ROOT'
                    val=int(k) in self.c['owned'] and int(k) in self.c['ally_controlled']
                else:val=int(k) in self.c['owned'] and int(k) in self.c['controlled']
            elif k=='sof_brt_external_threat':val=(self.c['war'] or self.c['threat'])==(v=='yes')
            elif k=='sof_brt_owned_coast':val=self.c['coast']==(v=='yes')
            elif k in self.triggers:val=self.cond(self.triggers[k])==(v=='yes')
            else:raise AssertionError('Unsupported modeled trigger '+str(k))
            values.append(val)
        return all(values)

    def run(self,rows):
        matched=False
        for row in rows:
            k,v=row.key,row.value
            if k=='if':
                matched=self.cond(one(v,'limit').value)
                if matched:self.run([r for r in v if r.key!='limit'])
            elif k=='else':
                if not matched:self.run(v)
            elif k in ['set_variable','set_temp_variable','add_to_variable','add_to_temp_variable']:
                term=v[0];value=self.number(term.value)
                self.c['vars'][term.key]=value if k.startswith('set_') else self.c['vars'].get(term.key,0)+value
            elif k=='clamp_variable':
                key=scalar(v,'var');self.c['vars'][key]=min(float(scalar(v,'max')),max(float(scalar(v,'min')),self.c['vars'].get(key,0)))
            elif k=='set_country_flag':
                key=v if isinstance(v,str) else scalar(v,'flag')
                self.c['flags'][key]=None if isinstance(v,str) else self.c['day']+int(scalar(v,'days'))
            elif k=='clr_country_flag':self.c['flags'].pop(v,None)
            elif k=='add_political_power':self.c['pp']+=float(v)
            elif k=='add_ideas':self.c['ideas'].add(v)
            elif k=='remove_ideas':self.c['ideas'].discard(v)
            elif k=='add_timed_idea':
                key=scalar(v,'idea');self.c['ideas'].add(key);self.time_ideas[key]=self.c['day']+int(scalar(v,'days'))
            elif k=='add_research_slot':self.c['slots']+=int(v)
            elif k=='load_focus_tree':self.c['tree']=scalar(v,'tree')
            elif k=='recruit_character':self.c['characters'].add(v)
            elif k=='country_event':self.c['events'].append(scalar(v,'id'))
            elif k=='promote_character':self.c['leader']=v
            elif k in ['custom_effect_tooltip']:pass
            elif k in self.effects:self.run(self.effects[k])
            else:raise AssertionError('Unsupported modeled effect '+str(k))

    def effect(self,key):self.run(self.effects[key])


def audit(check):
    spec=json.loads((ROOT/'design/brittany-focus.json').read_text(encoding='utf-8'))
    tree=one(parse((MOD/'common/national_focus/sof_brittany.txt').read_text(encoding='utf-8')),'focus_tree').value
    focuses={scalar(n.value,'id'):n.value for n in entries(tree,'focus')}
    ids=set(focuses);codes={n['code']:n['id'] for n in spec['nodes']}
    locpath=MOD/'localisation/simp_chinese/replace/sof_brittany_l_simp_chinese.yml'
    loc=dict(re.findall(r'(?m)^ ([^\s:]+):0 "(.*)"',locpath.read_text(encoding='utf-8-sig')))
    gfx={scalar(n.value,'name').strip('"'):n.value for group in entries(parse((MOD/'interface/sof_brittany.gfx').read_text(encoding='utf-8')),'spriteTypes') for n in group.value}
    check(len(ids)==174 and len(spec['nodes'])==174,'174 authored focuses and no repeated IDs')
    check(locpath.read_bytes().startswith(b'\xef\xbb\xbf'),'Chinese text has BOM')
    check(sum(x[2] for x in DELEGATES)==100,'Six named delegates total 100 fictional seats')
    check(len({(n['x'],n['y']) for n in spec['nodes']})==174,'All coordinates distinct')
    positions={n['id']:(n['x'],n['y']) for n in spec['nodes']}
    for fid,rows in focuses.items():
        check(fid in loc and fid+'_desc' in loc,'Title and description: '+fid)
        icon=scalar(rows,'icon');check(icon in gfx,'Focus sprite: '+fid)
        if icon in gfx:check((MOD/scalar(gfx[icon],'texturefile').strip('"')).is_file(),'Texture exists: '+fid)
        check(scalar(rows,'cancel_if_invalid')=='yes','Invalid territorial or legislative gate cancels: '+fid)
        check(not any(r.key in ['add_core_of','annex_country','create_wargoal'] for r in walk(rows)),'No free core or automatic offensive war: '+fid)
        for pre in entries(rows,'prerequisite'):
            for r in entries(pre.value,'focus'):
                check(r.value in ids,'Prerequisite resolves: '+fid)
                if r.value in ids:check(positions[r.value][1]<positions[fid][1],'Prerequisite is above focus: '+fid)
        for mutual in entries(rows,'mutually_exclusive'):
            for r in entries(mutual.value,'focus'):
                check(r.value in ids and any(x.value==fid for m in entries(focuses[r.value],'mutually_exclusive') for x in entries(m.value,'focus')),'Mutual exclusion reciprocal: '+fid)
        reward=one(rows,'completion_reward').value
        receipt=next(r.value for r in walk(reward) if r.key=='set_country_flag' and r.value.startswith('sof_brt_grant_'))
        check(any(r.key=='has_country_flag' and r.value==receipt for r in walk(one(reward,'if').value)),'One-time receipt guard: '+fid)
    # Global duplicates would silently select the wrong tree even if this file is valid.
    all_ids=[]
    for p in (MOD/'common/national_focus').glob('*.txt'):
        rows=parse(p.read_text(encoding='utf-8-sig'))
        for t in entries(rows,'focus_tree'):all_ids += [scalar(f.value,'id') for f in entries(t.value,'focus')]
        all_ids += [scalar(f.value,'id') for f in entries(rows,'shared_focus')]
    check(all(all_ids.count(fid)==1 for fid in ids),'New IDs globally unique')
    decisions=one(parse((MOD/'common/decisions/sof_brittany.txt').read_text(encoding='utf-8')),'sof_brt_council').value
    bykey={r.key:r.value for r in decisions}
    scenarios=[]
    def record(name,condition):check(condition,name);scenarios.append(name)
    s=Scenario();s.effect('sof_brt_initialize');s.effect('sof_brt_sync')
    record('New REN starts with 35 seats and exactly isolation stage 3',s.c['vars']['sof_brt_support']==35 and s.c['ideas']=={'sof_brt_isolation_3'})
    before=deepcopy(s.c);s.effect('sof_brt_initialize');s.effect('sof_brt_sync')
    record('Initialization and weekly sync are idempotent',s.c==before)
    foreign=Scenario(tag='LIL',tree='sof_generic');before=deepcopy(foreign.c);foreign.effect('sof_brt_initialize');foreign.effect('sof_brt_sync')
    record('Foreign country remains untouched',foreign.c==before)
    old=Scenario(tree='sof_generic',completed={'SOF_GENERIC_basic_industry'});old.effect('sof_brt_initialize')
    record('Old REN switches tree once and preserves recorded old completions',old.c['tree']=='sof_brittany' and old.c['completed']=={'SOF_GENERIC_basic_industry'})
    for key,_,seats,_,cost,_ in DELEGATES:
        d=bykey['sof_brt_negotiate_'+key];s=Scenario(completed={dict(chateau='SOF_BRT_P3',lemaistre='SOF_BRT_P4',bahon='SOF_BRT_P5',legorgeu='SOF_BRT_P6',tremintin='SOF_BRT_P7',prigent='SOF_BRT_P8')[key]})
        record('Listening focus exposes paid negotiation: '+key,s.cond(one(d,'available').value))
        s.c['pp']-=int(scalar(d,'cost'));s.run(one(d,'complete_effect').value)
        record('Negotiation charges actual cost and adds exact seats: '+key,s.c['pp']==300-cost and s.c['vars']['sof_brt_support']==seats)
        record('An active pledge cannot be bought twice: '+key,not s.cond(one(d,'available').value))
        s.effect('sof_brt_count_support');record('Recount does not stack seats: '+key,s.c['vars']['sof_brt_support']==seats)
        s.advance(180);s.effect('sof_brt_count_support');record('Pledge and its concession expire: '+key,s.c['vars']['sof_brt_support']==0 and not s.c['ideas'])
    for key,(_,threshold,pre,extra) in BILLS.items():
        d=bykey['sof_brt_vote_'+key];gate=one(d,'available').value
        member_flags={'sof_brt_pledge_'+k:None for k,_,_,_,_,_ in DELEGATES}
        # Keep conditional issue sponsors active while changing total votes.
        s=Scenario(flags=member_flags,threat=True,coast=True);s.effect('sof_brt_count_support')
        s.c['vars']['sof_brt_support']=threshold-1
        record('One seat below required vote blocks '+key,not s.cond(gate))
        s.c['vars']['sof_brt_support']=threshold
        record('Exact threshold permits '+key,s.cond(gate))
        s.c['pp']-=int(scalar(d,'cost'));s.run(one(d,'complete_effect').value)
        record('Single active bill prevents concurrent review: '+key,not s.cond(gate))
        s.advance(45);s.run(one(d,'remove_effect').value)
        record('Successful review enacts once and clears pending flag: '+key,'sof_brt_law_'+key in s.c['flags'] and 'sof_brt_bill_pending' not in s.c['flags'] and s.c['pp']==270)
        s=Scenario(flags={'sof_brt_pledge_'+k:30 for k,_,_,_,_,_ in DELEGATES},threat=True,coast=True);s.effect('sof_brt_count_support')
        s.c['pp']-=30;s.run(one(d,'complete_effect').value);s.advance(45);s.run(one(d,'remove_effect').value)
        record('Expired coalition defeats bill and refunds only 10: '+key,'sof_brt_law_'+key not in s.c['flags'] and s.c['pp']==280 and 'sof_brt_bill_pending' not in s.c['flags'])
        if key in ['aid','revision','mobilization','war','expedition']:
            s=Scenario(flags=member_flags,threat=False);s.effect('sof_brt_count_support')
            record('Peace without external threat blocks '+key,not s.cond(gate))
        if key=='mobilization':
            s=Scenario(flags=member_flags,threat=True,war_support=.34);s.effect('sof_brt_count_support')
            record('Low war support blocks full mobilization',not s.cond(gate))
    # Coalition routes must satisfy both the overall majority and named sponsors.
    for code,required in [('P12',['chateau','lemaistre']),('P13',['bahon','prigent']),('P14',['lemaistre','tremintin'])]:
        s=Scenario(flags={'sof_brt_pledge_'+k:None for k,_,_,_,_,_ in DELEGATES});s.effect('sof_brt_count_support')
        gate=one(focuses[codes[code]],'available').value
        record('Named coalition passes with current sponsors: '+code,s.cond(gate))
        s.c['flags'].pop('sof_brt_pledge_'+required[0]);s.effect('sof_brt_count_support')
        record('Losing a required sponsor blocks coalition despite overall majority: '+code,not s.cond(gate))
    for stage in [1,2,3]:
        s=Scenario(vars={'sof_brt_isolation':stage},flags={'sof_brt_initialized':None})
        s.effect('sof_brt_sync');s.c['war']=True;s.effect('sof_brt_sync')
        record('War removes isolation for immediate self-defence: '+str(stage),s.c['vars']['sof_brt_isolation']==0 and s.c['ideas']=={'sof_brt_isolation_0'})
        record('Emergency self-defence grants no offensive campaign: '+str(stage),'sofzh_unification_war_ready' not in s.c['flags'])
        s.c['war']=False;s.effect('sof_brt_sync')
        record('Peace restores previous restrictions: '+str(stage),s.c['vars']['sof_brt_isolation']==stage and s.c['ideas']=={'sof_brt_isolation_'+str(stage)})
    s=Scenario(vars={'sof_brt_isolation':3},flags={'sof_brt_initialized':None},war=True);s.effect('sof_brt_sync')
    s.c['completed'].add('SOF_BRT_I9');s.effect('sof_brt_set_stage_0');s.c['war']=False;s.effect('sof_brt_sync')
    record('Parliament-approved mobilization survives a subsequent peace',s.c['vars']['sof_brt_isolation']==0)
    s=Scenario(vars={'sof_brt_isolation':0},flags={'sof_brt_war_authorized':None});s.effect('sof_brt_sync')
    record('War authorization plus completed mobilization grants border campaign','sofzh_unification_war_ready' in s.c['flags'] and s.cond(s.triggers['sof_brt_expansion_allowed']))
    s.c['vars']['sof_brt_isolation']=2;s.effect('sof_brt_sync')
    record('Any restored isolation clears border authorization','sofzh_unification_war_ready' not in s.c['flags'] and not s.cond(s.triggers['sof_brt_expansion_allowed']))
    for code,state in [('N2',168),('N5',208),('N8',168)]:
        gate=one(focuses[codes[code]],'available').value
        for owned,controlled in itertools.product([False,True],repeat=2):
            s=Scenario(vars={'sof_brt_support':100},owned={state} if owned else set(),controlled={state} if controlled else set())
            record('Shipyard needs ownership and full control: '+code+f' {owned}/{controlled}',s.cond(gate)==(owned and controlled))
        reward=one(focuses[codes[code]],'completion_reward').value
        record('Territorial checks repeated at shipyard reward: '+code,any(r.key=='is_owned_by' for r in walk(reward)) and any(r.key=='is_fully_controlled_by' for r in walk(reward)))
    for code,minfact,targetslots in [('E9',6,3),('E10',12,4)]:
        gate=one(focuses[codes[code]],'available').value
        for fact,slots in itertools.product([minfact-1,minfact],range(2,6)):
            s=Scenario(factories=fact,slots=slots)
            record('Research slot gate: '+code+f' factories={fact} slots={slots}',s.cond(gate)==(fact>=minfact and slots<targetslots))
            if s.cond(gate):
                s.run(one(focuses[codes[code]],'completion_reward').value);once=s.c['slots']
                s.run(one(focuses[codes[code]],'completion_reward').value)
                record('Research completion receipt prevents a repeated grant: '+code,s.c['slots']==once)
    # Shared changes remain bounded to explicit extension points.
    for rel,allowed in [
        ('common/scripted_effects/sof_vanilla_major.txt',{'sof_van_setup'}),
        ('common/scripted_triggers/sofzh_corsica.txt',{'sofzh_ai_supported_focus_tree'})]:
        old={n.key:n.value for n in parse((REF/'mod'/rel).read_text(encoding='utf-8-sig'))}
        new={n.key:n.value for n in parse((MOD/rel).read_text(encoding='utf-8-sig'))}
        check(old.keys()==new.keys(),'Shared definitions preserved: '+rel)
        check(all(norm(old[k])==norm(new[k]) for k in old if k not in allowed),'Other countries effects/triggers preserved: '+rel)
    # Even within migration, only REN's branch may change.
    rel='common/scripted_effects/sof_vanilla_major.txt'
    before=one(parse((REF/'mod'/rel).read_text(encoding='utf-8-sig')),'sof_van_setup').value
    after=one(parse((MOD/rel).read_text(encoding='utf-8-sig')),'sof_van_setup').value
    check(len(before)==len(after),'Same number of existing migration branches')
    check(all(norm([a])==norm([b]) for a,b in zip(before,after) if not (a.key=='if' and scalar(one(a.value,'limit').value,'original_tag')=='REN')),'Non-REN migration unchanged')
    for rel,key in [('common/military_industrial_organization/organizations/sof_regional_manufacturers.txt','sof_reg_ren_organization'),('common/ideas/sof_regional_manufacturers.txt','sof_reg_ren_organization_legacy')]:
        old=parse((REF/'mod'/rel).read_text(encoding='utf-8-sig'));new=parse((MOD/rel).read_text(encoding='utf-8-sig'))
        a={n.key:n.value for n in walk(old) if n.key and n.key.startswith('sof_reg_') and isinstance(n.value,list)}
        b={n.key:n.value for n in walk(new) if n.key and n.key.startswith('sof_reg_') and isinstance(n.value,list)}
        check(a.keys()==b.keys() and all(norm(a[k])==norm(b[k]) for k in a if k!=key),'Other 19 manufacturers unchanged: '+rel)
    for row in spec['art']:
        check(hashlib.sha256((MOD/row['path']).read_bytes()).hexdigest()==row['sha256'],'Focus icon source hash: '+row['path'])
    scenarios+=audit_expansion(check,record,focuses,bykey,spec)
    audit_pool(check,record,spec)
    return scenarios


def audit_expansion(check,record,focuses,decisions,spec):
    # The caller's record appends to the same scenario list. Return no duplicates.
    from PIL import Image,ImageFont
    from brittany_military import RENAMED
    military=[n for n in spec['nodes'] if n['code'][0] in 'MABNFO']
    check(len(military)==116,'116 dedicated military focuses')
    check(sum(n['code'].startswith('F') for n in military)==36 and sum(n['code'].startswith('O') for n in military)==36,'36 focuses in each military programme')
    check(all(n['name']==RENAMED[n['code']] for n in military if n['code'] in RENAMED),'All original military nodes replaced with local design')
    for prefix,root in [('F','SOF_BRT_F0'),('O','SOF_BRT_O0')]:
        def ancestors(fid):
            return {p.value for g in entries(focuses[fid],'prerequisite') for p in entries(g.value,'focus')} \
                | {a for g in entries(focuses[fid],'prerequisite') for p in entries(g.value,'focus') for a in ancestors(p.value)}
        check(all(root in ancestors(n['id']) for n in military if n['code'].startswith(prefix) and n['id']!=root),'Entire route depends on its selected programme: '+prefix)
    s=Scenario(vars={'sof_brt_support':51})
    record('Defensive programme requires a council majority',s.cond(one(focuses['SOF_BRT_F0'],'available').value))
    s.c['vars']['sof_brt_support']=50
    record('Defensive programme blocks below 51 seats',not s.cond(one(focuses['SOF_BRT_F0'],'available').value))
    for support,stage,law in itertools.product([65,66],[0,1,2,3],[False,True]):
        s=Scenario(vars={'sof_brt_support':support,'sof_brt_isolation':stage},flags={'sof_brt_law_expedition':None} if law else {})
        record(f'Offensive programme law/vote/isolation gate {support}/{stage}/{law}',s.cond(one(focuses['SOF_BRT_O0'],'available').value)==(support>=66 and stage<3 and law))
    for c in ['F0','F35','O0','O35']:
        s=Scenario();s.run(one(focuses['SOF_BRT_'+c],'completion_reward').value)
        record('Military reward does not grant war authorization: '+c,'sof_brt_war_authorized' not in s.c['flags'] and 'sofzh_unification_war_ready' not in s.c['flags'])
    for c in ['O30','O35']:
        for stage,war in itertools.product([0,1],[False,True]):
            s=Scenario(vars={'sof_brt_isolation':stage},flags={'sof_brt_war_authorized':None} if war else {})
            record(f'Offensive capstone still needs separate war law {c}/{stage}/{war}',s.cond(one(focuses['SOF_BRT_'+c],'available').value)==(stage==0 and war))
    # A clickable GUI has to enforce the same paid negotiation as the decision.
    for key,_,seats,_,cost,_ in DELEGATES:
        milestone=dict(chateau='P3',lemaistre='P4',bahon='P5',legorgeu='P6',tremintin='P7',prigent='P8')[key]
        for pp,unlocked,subject,capitulated in itertools.product([cost-1,cost-.01,cost],[False,True],[False,True],[False,True]):
            s=Scenario(pp=pp,subject=subject,capitulated=capitulated,completed={'SOF_BRT_'+milestone} if unlocked else set())
            before=deepcopy(s.c);s.effect('sof_brt_gui_lobby_'+key)
            allowed=pp>=cost and unlocked and not subject and not capitulated
            record(f'GUI negotiation rechecks payment/focus/sovereignty {key}/{pp}/{unlocked}/{subject}/{capitulated}',
                   (s.c['pp']==pp-cost and s.c['vars']['sof_brt_support']==seats) if allowed else s.c==before)
            if allowed:
                before=deepcopy(s.c);s.effect('sof_brt_gui_lobby_'+key)
                record('Repeated GUI click charges no extra PP or seats: '+key,s.c==before)
        # Current pledge is the sole source for both exact vote count and seat art.
    for mask in range(64):
        flags={'sof_brt_pledge_'+k:None for i,(k,_,_,_,_,_) in enumerate(DELEGATES) if mask&(1<<i)}
        s=Scenario(flags=flags);s.effect('sof_brt_count_support')
        expected=sum(seats for i,(_,_,seats,_,_,_) in enumerate(DELEGATES) if mask&(1<<i))
        record('Seat diagram and count match every possible coalition: '+str(mask),s.c['vars']['sof_brt_support']==expected and all(s.c['vars']['sof_brt_ui_'+k]==(2 if 'sof_brt_pledge_'+k in flags else 1) for k,_,_,_,_,_ in DELEGATES))
    for key in BILLS:
        d=decisions['sof_brt_vote_'+key]
        flags={'sof_brt_pledge_'+k:None for k,_,_,_,_,_ in DELEGATES}
        s=Scenario(flags=flags,threat=True,coast=True);s.effect('sof_brt_count_support');s.run(one(d,'complete_effect').value)
        record('Panel marks the exact bill under review: '+key,'sof_brt_bill_'+key in s.c['flags'])
        s.run(one(d,'cancel_effect').value)
        record('Cancellation clears both panel and shared review state: '+key,'sof_brt_bill_'+key not in s.c['flags'] and 'sof_brt_bill_pending' not in s.c['flags'])
    gui=one(parse((MOD/'common/scripted_guis/sof_brittany_council.txt').read_text(encoding='utf-8')),'scripted_gui').value
    cfg=one(gui,'sof_brt_council_gui').value
    check(scalar(cfg,'context_type')=='decision_category','UI uses native USA-style decision-category context')
    categories=parse((MOD/'common/decisions/categories/sof_brittany.txt').read_text(encoding='utf-8'))
    check(scalar(one(categories,'sof_brt_council').value,'scripted_gui')=='sof_brt_council_gui','Council category actually attaches its scripted GUI')
    ui=parse((MOD/'interface/sof_brittany_council.gui').read_text(encoding='utf-8'))
    names={scalar(r.value,'name').strip('"') for r in walk(ui) if r.key in ['containerWindowType','buttonType','iconType','instantTextBoxType']}
    for e in one(cfg,'effects').value:check(e.key.removesuffix('_click') in names,'GUI click binds a real button: '+e.key)
    for e in one(cfg,'triggers').value:check(re.sub('_(visible|click_enabled)$','',e.key) in names,'GUI trigger binds a real widget: '+e.key)
    for e in one(cfg,'properties').value:check(e.key in names,'GUI frame binds a real icon: '+e.key)
    effects={r.key:r.value for r in one(cfg,'effects').value}
    for key,index in [('members',0),('bills',1),('forces',2),('funds',3)]:
        s=Scenario();s.run(effects['sof_brt_tab_'+key+'_click'])
        record('GUI tab changes only its view variable: '+key,s.c['vars']=={'sof_brt_ui_tab':index} and s.c['pp']==300 and not s.c['flags'])
    layout=json.loads((ROOT/'design/brittany-gui-layout.json').read_text(encoding='utf-8'))
    check(len([r for r in layout['icons'] if r['name'].startswith('sof_brt_seat_')])==100,'Chamber has exactly 100 individual seats')
    for a in spec['gui']['assets']:
        check(hashlib.sha256((MOD/a['path']).read_bytes()).hexdigest()==a['sha256'],'Original UI asset hash: '+a['path'])
        im=Image.open(MOD/a['path']);check(im.width<=16384 and im.height<=16384,'DDS texture fits maximum dimensions: '+a['path'])
    for rel in ['interface/sof_brittany_council.gui','interface/sof_brittany_council.gfx','common/scripted_guis/sof_brittany_council.txt','common/scripted_localisation/sof_brittany_council.txt']:
        check(bool(parse((MOD/rel).read_text(encoding='utf-8'))),'Native GUI/script parses: '+rel)
    loc=(MOD/'localisation/simp_chinese/replace/sof_brittany_council_l_simp_chinese.yml').read_text(encoding='utf-8-sig')
    loc_keys=set(re.findall(r'^\s+(\S+):',loc,re.M))
    for r in walk(ui):
        if r.key in ['text','buttonText','pdx_tooltip']:check(r.value.strip('"') in loc_keys,'UI text/tooltip localised: '+r.value)
    sloc=parse((MOD/'common/scripted_localisation/sof_brittany_council.txt').read_text(encoding='utf-8'))
    definitions={scalar(n.value,'name') for n in sloc}
    for name in re.findall(r'\[(GetSofBrt\w+)\]',loc):check(name in definitions,'Dynamic council label resolves: '+name)
    if GAME.exists() and os.environ.get('BRT_OFFLINE_NATIVE')!='1':
        categories=one(parse((GAME/'common/technology_tags/00_technology.txt').read_text(encoding='utf-8-sig')),'technology_categories').value
        known={r.value for r in categories}
        modifier_doc=(GAME/'documentation/modifiers_documentation.md').read_text(encoding='utf-8-sig')
        known_modifiers=set(re.findall(r'^## ([\w]+)$',modifier_doc,re.M))
        native_ideas='\n'.join(p.read_text(encoding='utf-8-sig') for p in (GAME/'common/ideas').glob('*.txt'))
        known_building={k for k in ['production_speed_'+b+'_factor' for b in ['industrial_complex','arms_factory','dockyard','infrastructure']] if re.search(r'\b'+k+r'\s*=',native_ideas)}
    else:
        native=json.loads((ROOT/'design/brittany-native-119.json').read_text(encoding='utf-8'))
        known=set(native['research_categories']);known_modifiers=set(native['documented_modifiers']);known_building=set(native['building_modifiers'])
    for fid,rows in focuses.items():
        for r in walk(rows):
            if r.key=='add_tech_bonus':check(scalar(r.value,'category') in known,'Native research category resolves: '+fid)
    for r in walk(parse((MOD/'common/ideas/sof_brittany.txt').read_text(encoding='utf-8'))):
        if r.key=='modifier':
            for m in r.value:check(m.key in known_modifiers or m.key in known_building, 'Modifier documented or used by native 1.19 symbol snapshot: '+m.key)
    for rel in ['common/scripted_guis/sof_brittany_council.txt','common/scripted_effects/sof_brittany.txt']:
        check(not any(r.key=='political_power' for r in walk(parse((MOD/rel).read_text(encoding='utf-8')))),'Paid GUI uses native has_political_power trigger: '+rel)
    for rel in ['common/scripted_guis/sof_brittany_council.txt','common/scripted_effects/sof_brittany.txt','events/sof_brittany_hometowns.txt']:
        check(not any(r.operator in ('>=','<=') for r in walk(parse((MOD/rel).read_text(encoding='utf-8')))), 'Paid council and exile gates use native inclusive comparisons: '+rel)
    return []


def audit_pool(check,record,spec):
    from brittany_council_expansion import POOL,HOME_STATES,PRIMARY_HOME,PROGRAMMES,slot_active_here
    pool=json.loads((ROOT/'design/brittany-council-pool.json').read_text(encoding='utf-8'))
    check(len(POOL)==6 and len({p['key'] for p in POOL})==6,'Six distinct historical reserves')
    chars=one(parse((MOD/'common/characters/sof_brittany_council.txt').read_text(encoding='utf-8')),'characters').value
    check(len(chars)==9,'Six reserves and three previously unregistered original delegates have character definitions')
    s=Scenario();s.effect('sof_brt_prepare_bench');before=deepcopy(s.c);s.effect('sof_brt_prepare_bench')
    record('Historical bench recruited once without adding votes',s.c==before and len(s.c['characters'])==9 and 'sof_brt_support' not in s.c['vars'])
    declarations=one(parse((MOD/'common/decisions/sof_brittany_committees.txt').read_text(encoding='utf-8')),'sof_brt_committees').value
    ds={d.key:d.value for d in declarations}
    allflags={'sof_brt_pledge_'+k:None for k,_,_,_,_,_ in DELEGATES}
    completed={n['id'] for n in spec['nodes']}
    for key,p in PROGRAMMES.items():
        d=ds['sof_brt_fund_'+key];flags={**allflags,'sof_brt_law_ports':None}
        s=Scenario(flags=flags,completed=completed);s.effect('sof_brt_count_support')
        record('Council programme available with focus and sponsors: '+key,s.cond(one(d,'available').value))
        s.c['pp']-=int(scalar(d,'cost'));s.run(one(d,'complete_effect').value)
        record('Council programme costs 35 PP and cannot stack: '+key,s.c['pp']==265 and 'sof_brt_committee_'+key in s.c['ideas'] and not s.cond(one(d,'available').value))
        s.c['flags'].pop('sof_brt_pledge_'+p['sponsors'][0]);s.effect('sof_brt_count_support');s.effect('sof_brt_committee_sync')
        record('Losing named sponsor cancels programme despite majority: '+key,s.c['vars']['sof_brt_support']>=51 and 'sof_brt_committee_'+key not in s.c['ideas'])
        s=Scenario(flags=flags,completed=completed);s.effect('sof_brt_count_support');s.run(one(d,'complete_effect').value);s.c['vars']['sof_brt_support']=50;s.effect('sof_brt_committee_sync')
        record('Losing overall majority cancels programme: '+key,'sof_brt_committee_'+key not in s.c['ideas'])
        s=Scenario(flags=flags,completed=completed);s.effect('sof_brt_count_support');s.run(one(d,'complete_effect').value);s.advance(180)
        record('Special funding expires after 180 days: '+key,'sof_brt_committee_'+key not in s.c['ideas'])
    for p in POOL:
        slot=p['slot'];contract=next(c for k,_,_,_,_,c in DELEGATES if k==slot)
        s=Scenario(flags={**allflags},ideas={'sof_brt_'+contract});s.effect('sof_brt_count_support');seats=s.c['vars']['sof_brt_support']
        d=ds['sof_brt_rotate_'+slot];s.c['pp']-=int(scalar(d,'cost'));s.run(one(d,'complete_effect').value)
        record('Reserve replaces current pledge rather than adding seats: '+slot,'sof_brt_reserve_'+slot in s.c['flags'] and 'sof_brt_pledge_'+slot not in s.c['flags'] and s.c['pp']==250 and s.c['vars']['sof_brt_support']<seats and 'sof_brt_'+contract not in s.c['ideas'])
        s.c['completed'].add('SOF_BRT_P1');record('Replacement has 180-day cooldown: '+slot,not s.cond(one(d,'available').value))
        s.advance(180);record('Replacement can be reconsidered after cooldown: '+slot,s.cond(one(d,'available').value))
        s.run(one(d,'complete_effect').value);record('Return to original representative grants no free pledge: '+slot,'sof_brt_reserve_'+slot not in s.c['flags'] and 'sof_brt_pledge_'+slot not in s.c['flags'])
        s=Scenario(flags={f'sof_brt_home_seen_{p["home"]}':None});s.effect('sof_brt_replace_'+slot)
        record('Candidate from previously lost home does not evade suspension: '+slot,'sof_brt_suspended_'+slot in s.c['flags'])
    hometown_events=parse((MOD/'events/sof_brittany_hometowns.txt').read_text(encoding='utf-8'))
    ev={scalar(e.value,'id'):e.value for e in entries(hometown_events,'country_event')}
    check(len(ev)==21,'Seven mapped home regions each have loss/capture/recovery events')
    check(not any(r.key in ['add_core_of','annex_country','transfer_state','add_manpower','add_political_power'] and (r.key!='add_political_power' or float(r.value)>0) for r in walk(hometown_events)),'Home events cannot farm manpower/PP/annexations/cores')
    for i,state in enumerate(HOME_STATES):
        s=Scenario(flags={**allflags},controlled={state},owned={state});s.effect('sof_brt_home_watch')
        s.c['controlled'].clear();s.c['ally_controlled'].add(state);s.effect('sof_brt_home_watch')
        record('Friendly allied control of our home generates no occupation event: '+str(state),not s.c['events'] and all('sof_brt_pledge_'+key in s.c['flags'] for key,_,_,_,_,_ in DELEGATES))
        for reserve in [False,True]:
            flags={**allflags,**({'sof_brt_reserve_'+p['slot']:None for p in POOL} if reserve else {})}
            s=Scenario(flags=flags,controlled={state});s.effect('sof_brt_home_watch')
            record(f'Initial home snapshot generates no capture message {state}/{reserve}',not s.c['events'])
            s.c['controlled'].clear();s.effect('sof_brt_home_watch')
            affected={slot for slot,_,_,_,_,_ in DELEGATES if s.cond(parse(slot_active_here(slot,state)))}
            record(f'Home loss suspends only current local delegates {state}/{reserve}',all(('sof_brt_suspended_'+slot in s.c['flags'])==(slot in affected) for slot,_,_,_,_,_ in DELEGATES) and all(('sof_brt_pledge_'+slot in s.c['flags'])==(slot not in affected) for slot,_,_,_,_,_ in DELEGATES))
            record(f'One regional loss notification {state}/{reserve}',s.c['events']==[f'sof_brt_local.{100+i*3}'])
            before=deepcopy(s.c);s.effect('sof_brt_home_watch');record(f'No repeated daily loss event {state}/{reserve}',s.c==before)
            s.c['controlled'].add(state);s.effect('sof_brt_home_watch')
            record(f'Rapid recapture does not spam notifications {state}/{reserve}',len(s.c['events'])==1)
            record(f'Recovery restores eligibility without free votes {state}/{reserve}',all('sof_brt_suspended_'+slot not in s.c['flags'] and 'sof_brt_pledge_'+slot not in s.c['flags'] for slot in affected))
        s=Scenario();s.effect('sof_brt_home_watch');s.c['controlled'].add(state);s.effect('sof_brt_home_watch')
        record('Previously foreign home triggers first-capture event: '+str(state),s.c['events']==[f'sof_brt_local.{101+i*3}'])
        s.advance(14);s.c['controlled'].clear();s.effect('sof_brt_home_watch');s.advance(14);s.c['controlled'].add(state);s.effect('sof_brt_home_watch')
        record('Later control recovery uses separate recovery event: '+str(state),s.c['events'][-1]==f'sof_brt_local.{102+i*3}')
        loss=ev[f'sof_brt_local.{100+i*3}'];exile=entries(loss,'option')[0].value
        s=Scenario(pp=24.99)
        record('Exile option requires full 25 PP: '+str(state),not s.cond(one(exile,'trigger').value))
        s.c['pp']=25;record('Exile option rechecks current control: '+str(state),s.cond(one(exile,'trigger').value))
        s.c['controlled'].add(state);record('Late loss popup cannot charge after recapture: '+str(state),not s.cond(one(exile,'trigger').value))
    comparison=json.loads((REPORT/'balance-comparison.json').read_text(encoding='utf-8'))
    check(len(comparison['rows'])>=25 and all(abs(r['brittany']-round(r['generic']*1.30,3))<.00001 for r in comparison['rows']),'Brittany permanent institutions have 130 percent of matched current generic g3 values')
    for rel in ['common/characters/sof_brittany_council.txt','common/decisions/sof_brittany_committees.txt','events/sof_brittany_hometowns.txt']:
        check(rel in spec['files'],'Council expansion included in delivery manifest: '+rel)
    hook=one(parse((MOD/'common/on_actions/zz_sof_brittany.txt').read_text(encoding='utf-8')),'on_actions').value
    check(one(hook,'on_daily_REN') is not None,'Daily council and home watch use explicit REN-country on-action scope')


def validate():
    checks=[]
    def check(ok,description):checks.append(dict(ok=bool(ok),description=description))
    scenarios=audit(check)
    return dict(ok=all(c['ok'] for c in checks),checks=len(checks),errors=[c['description'] for c in checks if not c['ok']],
                scenarios=len(scenarios),scenario_names=scenarios,focuses=len(authored_nodes()),delegates=6,game_engine_verified=False,
                scope='Parsed-script scenarios and source/art checks; not game execution')


if __name__=='__main__':
    report=validate();REPORT.mkdir(parents=True,exist_ok=True)
    (REPORT/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='scenario_names'},ensure_ascii=False))
    raise SystemExit(0 if report['ok'] else 1)
