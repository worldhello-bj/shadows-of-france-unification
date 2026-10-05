"""Native graph equivalence, active selectors, reference and migration regression audits."""
import hashlib,json,re
import copy
from pathlib import Path
from hoi4_script import parse,one,scalar,entries,walk

ROOT=Path(__file__).resolve().parent.parent;MOD=ROOT/'mod'
def read(p):return p.read_text(encoding='utf-8-sig')
def shape(rows):return [(r.key,r.operator,shape(r.value) if isinstance(r.value,list) else r.value) for r in rows]

def audit(check,loc,gfx):
    from build_vanilla_remake import Builder,baseline
    from vanilla_startup import LEGACY_INITIAL
    data=json.loads(read(ROOT/'design/vanilla-major-remake.json'))
    check(len(data['donors'])==2,'Only Paris and Corsica are remade')
    check((MOD/'common/national_focus/SoF_generic.txt').read_bytes().decode('utf-8-sig').replace('\r\n','\n')==baseline('mod/common/national_focus/SoF_generic.txt'),'Generic focus tree remains unchanged from 3.2')
    all_loc={}
    for p in (MOD/'localisation/simp_chinese').rglob('*.yml'):
        all_loc.update(re.findall(r'(?m)^\s+([^\s:]+):\d*\s+"((?:[^"\\]|\\.)*)"',read(p)))
    all_ids=set();trees={}
    for p in (MOD/'common/national_focus').glob('*.txt'):
        for t in entries(parse(read(p)),'focus_tree'):
            tid=scalar(t.value,'id');check(tid not in trees,'Unique tree ID: '+tid);trees[tid]=t.value
            for n in entries(t.value,'focus'):
                fid=scalar(n.value,'id');check(fid not in all_ids,'Unique runtime focus ID: '+fid);all_ids.add(fid)
    # No alternative bespoke tree wins the country selector over the existing generic tree.
    for name,t in trees.items():
        if name.startswith('sof20_') or name.endswith('_legacy'):
            country=one(t,'country').value
            check(scalar(country,'factor')=='0' and not entries(country,'modifier'),'Inactive legacy selector: '+name)
    ideas=set()
    for p in (MOD/'common/ideas').glob('*.txt'):
        for group in entries(parse(read(p)),'ideas'):
            for cat in group.value:
                if isinstance(cat.value,list):ideas.update(r.key for r in cat.value if r.key)
    effects=set()
    for p in (MOD/'common/scripted_effects').glob('*.txt'):effects.update(r.key for r in parse(read(p)) if r.key)
    triggers=set()
    for p in (MOD/'common/scripted_triggers').glob('*.txt'):triggers.update(r.key for r in parse(read(p)) if r.key)
    dvars=set(data['dynamic_variables'].values())
    for report in data['donors']:
        donor=report['donor'];native=one(parse(read(ROOT/'references/vanilla'/f'{donor}-1.19.3.txt')),'focus_tree').value
        active=trees['sofzh_paris' if donor=='france' else 'sofzh_corsica'];nodes=entries(active,'focus');source_nodes=entries(native,'focus');removed=report.get('removed',{})
        expected_removed=set() if donor=='france' else {
            'ITA_a_time_for_war','ITA_all_within_the_state','ITA_anti_partisan_measures','ITA_battaglioni_m',
            'ITA_catholic_action','ITA_corpo_volontari_della_liberta','ITA_deus_vult','ITA_fronte_militare_clandestino',
            'ITA_gappisti','ITA_grande_rivolta_rurale','ITA_guardia_nazionale_repubblicana','ITA_il_vento_aureo',
            'ITA_independence_rds','ITA_independence_rsi','ITA_integrate_polizia_dell_africa_italiana',
            'ITA_liberation_or_death','ITA_partisan_republics','ITA_reinforce_the_gustav_line','ITA_the_carabinieri',
            'ITA_the_catholic_dominion','ITA_the_holy_lands','ITA_the_italian_liberation_war','ITA_the_italian_social_republic',
            'ITA_the_kings_finest','ITA_the_papacy_reborn','ITA_the_social_republic_prevails'}
        check(set(removed)==expected_removed,'Only agreed unportable branches removed: '+donor)
        check(len(nodes)==(185 if donor=='france' else 288),'Expected retained major focus count: '+donor)
        active_ids={scalar(n.value,'id') for n in nodes}
        original=[n for n in source_nodes if scalar(n.value,'id') not in removed]
        check(len(nodes)==len(original)==report['nodes'],'All retained native focus nodes copied: '+donor)
        check(len(source_nodes)==report.get('original_nodes',len(source_nodes)),'Original donor node count recorded: '+donor)
        check(not report['unadapted'],'All rewards adapted: '+donor)
        graphkeys={'x','y','relative_position_id','prerequisite','mutually_exclusive','cost'}
        prefix='FRA_' if donor=='france' else 'ITA_';dest='SFP_' if donor=='france' else 'SFC_'
        for source,target in zip(original,nodes):
            fid=scalar(target.value,'id')
            relative=scalar(target.value,'relative_position_id')
            if relative:check(relative in active_ids,'Relative layout anchor resolves: '+fid)
            fields=copy.deepcopy([r for r in source.value if r.key in graphkeys])
            for r in fields:
                if r.key in ['prerequisite','mutually_exclusive']:r.value=[v for v in r.value if v.key!='focus' or v.value not in removed]
            fields=[r for r in fields if r.key not in ['prerequisite','mutually_exclusive'] or r.value]
            a=shape(fields);a=json.loads(re.sub(r'\b'+prefix+r'\w+',lambda m:dest+m[0][4:],json.dumps(a)))
            if (ROOT/'design/balance-4.3.json').exists():
                from vanilla_balance import filter_graph
                # Apply only the reviewed mutual-exclusion whitelist to the
                # native graph. Coordinates, prerequisite groups and cost stay exact.
                namespaced=copy.deepcopy(fields)
                for r in walk(namespaced):
                    if isinstance(r.value,str):r.value=re.sub(r'\b'+prefix+r'\w+',lambda m:dest+m[0][4:],r.value)
                a=json.loads(json.dumps(shape(filter_graph(namespaced,fid))))
            c=json.loads(json.dumps(shape([r for r in target.value if r.key in graphkeys])))
            check(a==c,'Native coordinates, prerequisites, exclusions and cost: '+fid)
            check(fid in all_loc and fid+'_desc' in all_loc,'Chinese focus text: '+fid)
            check(bool(re.search('[\u4e00-\u9fff]',all_loc.get(fid,''))),'Chinese title resolved: '+fid)
            check(not any(s in all_loc.get(fid,'') for s in ['埃塞俄比亚','阿姆哈拉','索马里','利比亚','英意','法意','西意','巴尔干','格拉姆西','格兰迪','巴尔博','阿尔法·罗密欧','爱迪生','美国','德意志','斯特雷萨','巴利阿里']),'Original world-specific title removed: '+fid)
            icon=scalar(target.value,'icon');check(icon in gfx,'Native focus art bound: '+fid)
            reward=one(target.value,'completion_reward').value;check(bool(reward),'Nonempty reward: '+fid)
            for r in walk(reward):
                if r.key in ['add_ideas','remove_ideas'] and isinstance(r.value,str):check(r.value in ideas,'Idea resolves: '+fid+' '+r.value)
                if r.key in ['add_idea','remove_idea','idea'] and isinstance(r.value,str):check(r.value in ideas,'Idea reference resolves: '+fid+' '+r.value)
                if r.key and r.key.startswith('sof') and not isinstance(r.value,list):check(r.key in effects or r.key in triggers,'Custom helper resolves: '+fid+' '+r.key)
                if r.key in ['has_completed_focus','focus'] and isinstance(r.value,str):check(r.value in all_ids,'Focus reference resolves: '+fid+' '+r.value)
                if r.key in ['add_political_power','add_stability','add_war_support','add_manpower'] and isinstance(r.value,str):check(bool(re.fullmatch(r'-?\d+(?:\.\d+)?',r.value)),'Numeric reward does not read an uninitialized variable: '+fid)
    for p in (MOD/'interface').glob('sof_vanilla*.gfx'):
        for r in walk(parse(read(p))):
            if r.key=='texturefile':check((MOD/r.value.strip('"')).is_file(),'Imported art file exists: '+r.value)
    for p in (MOD/'common/ai_strategy_plans').glob('sofzh_*.txt'):
        for r in walk(parse(read(p))):
            if r.key and r.key.startswith(('SFC_','SFP_')):check(r.key in all_ids,'AI focus resolves: '+r.key)
    generic_ids={scalar(n.value,'id') for n in entries(trees['sof_generic'],'focus')}
    startup=json.loads(read(ROOT/'design/vanilla-startup.json'))
    for tag in startup['generic_tags']:
        p=next((MOD/'history/countries').glob(tag+' - *.txt'));text=read(p)
        check('sof20_legacy_' not in text,'Regional history marks completed generic focuses: '+tag)
        for r in walk(parse(text)):
            if r.key=='complete_national_focus':check(r.value in generic_ids,'Historical generic completion resolves: '+tag+' '+r.value)
    script=one(parse(read(MOD/'common/scripted_effects/sof_vanilla_major.txt')),'sof_van_setup').value
    cases=[]
    def matches(body,c):
        result=[]
        for r in body:
            if r.key=='NOT':v=not matches(r.value,c)
            elif r.key=='OR':v=any(matches([x],c) for x in r.value)
            elif r.key=='original_tag':v=c['tag']==r.value
            elif r.key=='has_focus_tree':v=c['tree']==r.value
            elif r.key=='has_country_flag':v=r.value in c['flags']
            else:raise AssertionError('Unhandled migration guard '+str(r.key))
            result.append(v)
        return all(result)
    def execute(rows,c):
        for r in rows:
            if r.key=='if':
                if matches(one(r.value,'limit').value,c):execute([x for x in r.value if x.key!='limit'],c)
            elif r.key=='remove_ideas':c['ideas'].discard(r.value)
            elif r.key=='set_country_flag':c['flags'].add(r.value)
            elif r.key=='load_focus_tree':c['tree']=scalar(r.value,'tree');c['loads']+=1
            elif r.key=='add_ideas':c['ideas'].update(x.value for x in r.value) if isinstance(r.value,list) else c['ideas'].add(r.value)
            elif r.key=='set_variable':c['vars'].update({x.key:x.value for x in r.value})
            elif r.key=='add_dynamic_modifier':c['dynamic'].add(scalar(r.value,'modifier'))
            else:raise AssertionError('Unexpected setup effect '+str(r.key))
    # Exercise fresh regional starts, old custom-tree saves, and repeated weekly pulses.
    for tag in startup['generic_tags']:
        for mode in ['fresh_region','old_save','earned_generic']:
            c=dict(tag=tag,tree='sof20_'+tag if mode=='old_save' else 'sof_generic',ideas=set(LEGACY_INITIAL)|{'sof20_'+tag+'_fragmentation','sof20_terrain_mountain','sofzh_reward_infantry_3'},flags={'sof_van_regional_bookmark'} if mode=='fresh_region' else ({'sof_van_generic_migrated'} if mode=='earned_generic' else set()),vars={},dynamic=set(),loads=0)
            execute(script,c)
            check((bool(c['ideas']&set(LEGACY_INITIAL)))==(mode=='earned_generic'),'Legacy spirits cleared once, earned rewards survive: '+tag+' '+mode)
            check({'sof20_terrain_mountain','sofzh_reward_infantry_3'}<=c['ideas'],'Terrain and later generic rewards survive: '+tag+' '+mode)
            before=json.dumps({k:sorted(v) if isinstance(v,set) else v for k,v in c.items()},sort_keys=True);execute(script,c)
            check(before==json.dumps({k:sorted(v) if isinstance(v,set) else v for k,v in c.items()},sort_keys=True),'Weekly migration is idempotent: '+tag+' '+mode)
            cases.append(tag+' '+mode)
    check(len(cases)==54,'54 start/save/repeated-pulse migration scenarios')
    for p in [MOD/'common/decisions/sof_vanilla_major.txt',MOD/'events/sof_vanilla_diplomacy.txt',MOD/'common/dynamic_modifiers/sof_vanilla_major.txt']:parse(read(p))
    check(len(data['dynamic_variables'])>50,'Native military and industry variable modifiers imported')
    check(set(data['imported_ideas'])<=ideas,'All imported spirits registered')
