"""Guarded setup and migration for the two native transplants and generic starts."""
import re
from hoi4_script import parse,one,scalar,entries,replace

LEGACY_INITIAL = '''fra_generic_propaganda_campaigns sofzh_reward_administration_1 sofzh_reward_administration_2 sofzh_reward_air_defence_1 sofzh_reward_air_defence_2 sofzh_reward_artillery_1 sofzh_reward_dockyards_1 sofzh_reward_engineering_1 sofzh_reward_engineering_2 sofzh_reward_engineering_3 sofzh_reward_infantry_1 sofzh_reward_infantry_2 sofzh_reward_mil_industry_1 sofzh_reward_motorized_1 sofzh_reward_research_1 sofzh_reward_staff_1 sofzh_reward_submarines_2 sofzh_reward_surface_navy_1 sofzh_reward_surface_navy_2'''.split()

def write(b):
    from build_vanilla_remake import ROOT,MOD,save,baseline
    profiles=__import__('json').loads((ROOT/'design/country-design.json').read_text(encoding='utf-8'))
    tags=[p['tag'] for p in profiles if p['tag'] not in ['PRS','AJC']]
    cleanup=[]
    for tag in tags:
        p=next((MOD/'history/countries').glob(tag+' - *.txt'));text=baseline('mod/'+p.relative_to(MOD).as_posix())
        text=re.sub(r'sof20_legacy_sof_generic_(\w+)\s*=\s*yes',lambda m:'complete_national_focus = SOF_GENERIC_'+m[1],text)
        history=parse(text);dated=one(history,'1936.1.2.1')
        closing=dated.end-1
        while closing>0 and text[closing-1] in ' \t':closing-=1
        text=replace(text,[(closing,dated.end-1,' set_country_flag = sof_van_regional_bookmark\n')])
        text=re.sub(r'(?m)^(.*complete_national_focus[^\n]*?)[ \t]+$',r'\1',text)
        save('mod/'+p.relative_to(MOD).as_posix(),text)
        oldids=re.findall(r'(?m)^\s*(sof20_'+tag+r'_\w+) =',baseline('mod/common/ideas/sof20_regions.txt'))
        removal=' '.join('remove_ideas = '+k for k in oldids+LEGACY_INITIAL)
        cleanup.append('if = { limit = { original_tag = '+tag+' NOT = { has_country_flag = sof_van_generic_migrated } OR = { has_country_flag = sof_van_regional_bookmark has_focus_tree = sof20_'+tag+' } } '+removal+' if = { limit = { has_focus_tree = sof20_'+tag+' } load_focus_tree = { tree = sof_generic keep_completed = yes } } set_country_flag = sof_van_generic_migrated }')
    remove=lambda rel:' '.join('remove_ideas = '+r.key for r in one(one(parse(baseline(rel)),'ideas').value,'country').value)
    # Keep the old marker definition for saved-game cleanup, but new games no
    # longer receive the empty marker whose donor-only event chain was removed.
    b.import_idea('FRA_political_violence','france')
    paris=[b.import_idea(k,'france') for k in ['FRA_disjointed_government','FRA_victors_of_wwi','FRA_full_employment','FRA_inefficient_economy_1']]
    assert all(paris),paris
    history=parse((b.game/'history/countries/ITA - Italy.txt').read_text(encoding='utf-8-sig'))
    initial={}
    for r in entries(history,'set_variable'):
        for v in r.value:
            if v.key in b.dvars and isinstance(v.value,str) and re.fullmatch(r'-?\d+(?:\.\d+)?',v.value):initial[v.key]=v.value
    setup=' '.join('set_variable = { '+new+' = '+initial.get(old,'0')+' }' for old,new in b.dvars.items())
    setup+=' '+' '.join('add_dynamic_modifier = { modifier = '+parse(row)[0].key+' }' for row in b.dynamic)
    code='sof_van_setup = {\n '+'\n '.join(cleanup)+'\n'
    code+=' if = { limit = { has_focus_tree = sofzh_paris NOT = { has_country_flag = sof_van_major_initialized } } '+remove('mod/common/ideas/sofzh_paris.txt')+' '+ ' '.join('remove_ideas = '+k for k in LEGACY_INITIAL)+' load_focus_tree = { tree = sofzh_paris keep_completed = yes } add_ideas = { '+' '.join(paris)+' } set_country_flag = sof_van_major_initialized }\n'
    code+=' if = { limit = { has_focus_tree = sofzh_corsica NOT = { has_country_flag = sof_van_major_initialized } } '+remove('mod/common/ideas/sofzh_corsica.txt')+' '+ ' '.join('remove_ideas = '+k for k in LEGACY_INITIAL)+' load_focus_tree = { tree = sofzh_corsica keep_completed = yes } '+setup+' set_country_flag = sof_van_major_initialized }\n}'
    b.effects.append(code)
    save('mod/common/on_actions/sof20_startup.txt','on_actions = { on_startup = { effect = { every_country = { limit = { sofzh_unification_candidate = yes } sof20_migrate_terrain = yes sof_van_setup = yes } } } on_weekly = { effect = { if = { limit = { sofzh_unification_candidate = yes } sof_van_setup = yes } } } }')
    for donor,tree in [('france','sofzh_paris'),('italy','sofzh_corsica')]:
        starts={'france':['FRA_devalue_the_franc','FRA_begin_rearmament','FRA_metropolitan_france','FRA_reform_the_labour_laws','FRA_strengthen_government'], 'italy':['ITA_ethiopian_war_logistics_bba','ITA_army_primacy','ITA_industrialization_program','ITA_via_della_vittoria','ITA_triumph_in_africa_bba']}[donor]
        ids=set(r['donor'] for r in b.records if r['tag']==('PRS' if donor=='france' else 'AJC'))
        factors=' '.join(b.namespace(k,donor)+' = 20' for k in starts if k in ids)
        save('mod/common/ai_strategy_plans/'+tree+'.txt',tree+'_native_plan = { name = "'+b.namespace(starts[0],donor)+'" desc = "'+b.namespace(starts[0],donor)+'_desc" allowed = { always = yes } enable = { is_ai = yes has_focus_tree = '+tree+' } abort = { NOT = { has_focus_tree = '+tree+' } } focus_factors = { '+factors+' } research = { industry = 20 infantry_weapons = 20 naval_equipment = 15 } weight = { factor = 1 } }')
    return dict(generic_tags=tags,legacy_initial=LEGACY_INITIAL,corsica_initial_variables=initial)
