"""Regression checks for actual cabinet visibility, character schema and save repair."""
import copy
import hashlib
import json
import re
from pathlib import Path
from hoi4_script import parse, one, entries, scalar, walk
from validate_historical import State, Runner
from vanilla_historical import LEADERS, char_id
from build_focus_integration import ISLAND_TAGS, owned_character

ROOT=Path(__file__).resolve().parents[1]
MOD=ROOT/'mod'


def audit(check, gfx):
    spec=json.loads((ROOT/'design/focus-integration-4.6.json').read_text(encoding='utf-8'))
    release_files=spec['files'] if (ROOT/'VERSION').read_text().strip()==spec['version'] else []
    for row in release_files:
        p=ROOT/row['relative']
        check(p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'],
              'Integration payload matches reviewed hash: '+row['relative'])
    for row in spec['deletions']:
        check(not (ROOT/row['relative']).exists(),'Retired atlas absent: '+row['relative'])
    for row in spec.get('carried_forward', []) if release_files else []:
        p=ROOT/row['relative']
        check(hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'],
              'Independent installed tooltip repair preserved: '+row['relative'])
    meta=json.loads((ROOT/'design/historical-cabinet.json').read_text(encoding='utf-8'))
    cabinet=one(parse((MOD/'common/ideas/sofzh_cabinet.txt').read_text()),'ideas').value
    ideas={n.key:n.value for c in cabinet for n in c.value if isinstance(n.value,list)}
    ideas.update({n.key:n.value for n in one(one(parse((MOD/'common/ideas/sof_vanilla_major.txt').read_text()),'ideas').value,'country').value})
    triggers={n.key:n.value for n in parse((MOD/'common/scripted_triggers/sofzh_cabinet.txt').read_text())}
    effects={n.key:n.value for n in parse((MOD/'common/scripted_effects/sof_vanilla_major.txt').read_text())}
    chars=one(parse((MOD/'common/characters/sof_vanilla_historical.txt').read_text()),'characters').value
    base={v[0] for v in LEADERS.values()}
    expected_count=len(base)+len(ISLAND_TAGS)*len({v for v in base if v.startswith('ITA_')})
    check(len(chars)==expected_count,'Base leaders and five independent island rosters defined')
    for node in chars:
        check(node.key is not None and isinstance(node.value,list),'Character definition has a valid token')
        check(bool(entries(node.value,'country_leader')),'Character has an attachable leader role: '+node.key)
        for role in entries(node.value,'country_leader'):
            check(all(n.key in {'ideology','expire','traits','id'} for n in role.value),
                  'Leader role uses native definition fields: '+node.key)
        for portrait in entries(node.value,'portraits'):
            for group in portrait.value:
                check(group.key in {'civilian','army','navy','operative','scientist'},'Portrait group supported: '+node.key)
                if not isinstance(group.value,list):continue
                for value in group.value:
                    check(value.key in {'small','large'} and isinstance(value.value,str) and
                          re.fullmatch(r'"GFX_[A-Za-z0-9_]+"',value.value) is not None,
                          'Whole portrait token; no dangling suffix: '+node.key)
                    if value.key in {'small','large'}:
                        check(value.value.strip('"') in gfx,'Leader portrait sprite resolves: '+node.key+' '+value.value)
    for p in meta['members']:
        prefix='SFP_' if p['source'].startswith('FRA_') else 'SFC_'
        state=State('sofzh_paris' if prefix=='SFP_' else 'sofzh_corsica',(p['governments'] or ['democratic'])[0])
        runner=Runner(ideas,triggers,effects,[state]);body=ideas[p['id']]
        check(not runner.matches(one(body,'visible').value,state),'Locked historical member omitted: '+p['id'])
        state.focus.add(prefix+p['focuses'][0])
        check(runner.matches(one(body,'visible').value,state),'Unlocked historical member displayed: '+p['id'])
        state.ideas.add(p['id']);state.flags.add('sofzh_cabinet_'+p['slot']+'_cooldown')
        check(runner.matches(one(body,'visible').value,state),'Current member remains visible during cooldown: '+p['id'])
    for category in cabinet:
        if not category.key.startswith('sofzh_cabinet_'):continue
        for node in category.value:
            if not isinstance(node.value,list):continue
            on_add=one(node.value,'on_add').value
            check(len(on_add)==1 and on_add[0].key=='hidden_effect','Internal replacement list hidden: '+node.key)
    for old,(source,ideology,gov) in LEADERS.items():
        state=State('sofzh_paris' if old.startswith('FRA_') else 'sofzh_corsica',gov)
        state.focus.add(('SFP_' if old.startswith('FRA_') else 'SFC_')+old[4:])
        state.flags.update({'sof_hist_migrated_410','sof_hist_complete_'+old.lower()+'_done'})
        existing='sofzh_minister_executive_2';state.ideas.add(existing)
        before=copy.deepcopy((state.ideas,state.variables,state.dynamic,state.pp,state.gov))
        runner=Runner(ideas,triggers,effects,[state]);runner.execute(effects['sof_hist_repair_roles_460'],state)
        cid=owned_character(source,state.tag)
        check(state.leader==cid and ideology in state.roles[cid],'Broken completed-focus save gets leader: '+old)
        check(before==(state.ideas,state.variables,state.dynamic,state.pp,state.gov),'Save repair preserves paid chief, regime and earned bonuses: '+old)
        snapshot=copy.deepcopy(state.__dict__);runner.execute(effects['sof_hist_repair_roles_460'],state)
        check(snapshot==state.__dict__,'Save repair is idempotent: '+old)
        other=State(state.tree,next(g for g in ['democratic','fascism','communism','neutrality'] if g!=gov))
        other.focus=state.focus.copy();runner=Runner(ideas,triggers,effects,[other]);snapshot=copy.deepcopy(other.__dict__)
        runner.execute(effects['sof_hist_repair_roles_460'],other)
        check(other.__dict__==snapshot,'Save repair does not reverse later political choices: '+old)
    actions=parse((MOD/'common/on_actions/sof20_startup.txt').read_text())
    check(sum(n.key=='sof_hist_repair_roles_460' for n in walk(actions))==2,'Leader repair wired to startup and weekly country pulses')
    for old,(source,ideology,gov) in LEADERS.items():
        if not source.startswith('ITA_'):continue
        completion=effects['sof_hist_complete_'+old.lower()]
        check(not entries(completion,'if') and bool(entries(completion,'hidden_effect')),
              'Island roster dispatch is hidden from focus tooltip: '+old)
        world=[State('sofzh_corsica',gov,tag=tag) for tag in ISLAND_TAGS]
        # One country already owns the pre-update shared token.
        world[1].characters.add(char_id(source))
        for c in world:
            c.focus.add('SFC_'+old[4:])
            Runner(ideas,triggers,effects,world).execute(effects['sof_hist_repair_roles_460'],c)
        check(len({c.leader for c in world})==len(world),'Simultaneous completed routes use distinct owners: '+old)
        for c in world:
            check(c.leader==owned_character(source,c.tag),'Every island receives its own historical leader: '+old+' '+c.tag)
            Runner(ideas,triggers,effects,world).execute(effects['sof_hist_complete_'+old.lower()],c)
            check(c.leader==owned_character(source,c.tag) and ideology in c.roles[c.leader],
                  'Focus repeat cannot steal another country character: '+old+' '+c.tag)
