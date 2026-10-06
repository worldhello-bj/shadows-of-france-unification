"""Build the Marseille communist route without replacing local leader work.

Existing generic IDs become shared focuses, so bookmark completions and old
country histories retain their IDs. Changes are snapshotted before each write.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import zipfile
from collections import defaultdict, deque
from copy import deepcopy
from hoi4_script import parse, entries, one, scalar, walk, replace

ROOT = Path(__file__).resolve().parent.parent
MOD = ROOT / 'mod'
PASS = ROOT.parent.parent / 'zh_work/marseille-red-pass'
VERSION = '4.3.3'
PREFIX = 'SOF_MRS_RED_'
LOC = {}
OUTPUT = {}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def baseline(rel):
    saved = PASS / 'before-source' / rel
    current = MOD / rel
    if not saved.exists():
        saved.parent.mkdir(parents=True, exist_ok=True)
        saved.write_bytes(current.read_bytes())
    return saved.read_text(encoding='utf-8-sig')


def put(rel, content, bom=False, expected_current=None):
    path = MOD / rel
    previous_path = PASS / 'overlay' / rel
    if path.exists():
        original = PASS / 'before-source' / rel
        if original.exists():
            allowed = {sha(original.read_bytes())}
            if previous_path.exists():
                allowed.add(sha(previous_path.read_bytes()))
            if expected_current is not None and path.read_bytes()==expected_current:
                # Rebase only verified output of the current canonical builder.
                merged=PASS/'before-merged-source'/rel
                merged.parent.mkdir(parents=True,exist_ok=True)
                if not merged.exists():merged.write_bytes(expected_current)
                allowed.add(sha(expected_current))
            assert sha(path.read_bytes()) in allowed, 'Concurrent source edit: ' + rel
        elif previous_path.exists():
            assert path.read_bytes()==previous_path.read_bytes(), 'Concurrent new-file edit: '+rel
        else:
            original.parent.mkdir(parents=True, exist_ok=True)
            original.write_bytes(path.read_bytes())
    data = content if isinstance(content, bytes) else (content.rstrip() + '\n').encode('utf-8-sig' if bom else 'utf-8')
    if rel.endswith('.txt') or rel.endswith('.gfx'):
        parse(data.decode('utf-8-sig'))
    path.parent.mkdir(parents=True, exist_ok=True)
    previous_path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    previous_path.write_bytes(data)
    OUTPUT[rel] = sha(data)


def localize(key, name, desc=None):
    assert key not in LOC or LOC[key] == name, key
    LOC[key] = name
    if desc is not None:
        LOC[key + '_desc'] = desc


def fid(code):
    return PREFIX + code


def done(code):
    return 'has_completed_focus = ' + fid(code)


def bonus(category='industry', name='sof_mrs_red_study'):
    return f'add_tech_bonus = {{ name = {name} bonus = 0.5 uses = 1 category = {category} }}'


def tension(amount):
    return f'add_to_variable = {{ sof_mrs_red_tension = {amount} }} sof_mrs_red_refresh_tension = yes'


def factory_gate(kind):
    return ('any_owned_state = { sofzh_unification_french_state = yes '
            'is_fully_controlled_by = ROOT ' + ('is_coastal = yes ' if kind == 'dockyard' else '') +
            f'free_building_slots = {{ building = {kind} size > 0 include_locked = no }} }}')


def factory_reward(kind):
    return ('random_owned_controlled_state = { limit = { sofzh_unification_french_state = yes '
            'is_fully_controlled_by = ROOT ' + ('is_coastal = yes ' if kind == 'dockyard' else '') +
            f'free_building_slots = {{ building = {kind} size > 0 include_locked = no }} }} '
            f'add_building_construction = {{ type = {kind} level = 1 instant_build = yes }} }}')


def factories(count):
    return 'OR = { ' + ' '.join(
        f'AND = {{ num_of_civilian_factories >= {n} num_of_military_factories >= {count-n} }}'
        for n in range(count + 1)) + ' }'


def french_states(count):
    return f'check_variable = {{ sof_mrs_red_french_states >= {count} }}'


def read_design():
    doc = ROOT.parent.parent / 'designs/MARSEILLE-COMMUNIST-ROUTE-ZH.md'
    result = []
    for line in doc.read_text(encoding='utf-8').splitlines():
        row = [c.strip() for c in line.strip().strip('|').split('|')]
        if len(row) == 5 and re.fullmatch(r'[APEMDU]\d+', row[0]):
            code, name, days, prerequisite, description = row
            groups = [[p for p in re.findall(r'[APEMDU]\d+', prerequisite)]] if '或' in prerequisite else [[p] for p in re.findall(r'[APEMDU]\d+', prerequisite)]
            result.append(dict(code=code, id=fid(code), name=name, days=int(days), prerequisites=groups, description=description))
    assert len(result) == 52
    return result


def public_focuses():
    source = baseline('common/national_focus/SoF_generic.txt')
    tree = one(parse(source), 'focus_tree')
    nodes = entries(tree.value, 'focus')
    assert len(nodes) == 153
    edits = []
    shared = []
    public_ids = []
    roots = []
    for n in nodes:
        ident = scalar(n.value, 'id')
        public_ids.append(ident)
        if not entries(n.value, 'prerequisite'): roots.append(ident)
        text = source[n.start:n.end]
        text = re.sub(r'^focus\s*=', 'shared_focus =', text)
        # Public governance and basic science remain available. Equipment gifts,
        # industrial/military spirits and old campaigns yield to the red route.
        military_or_industry = any(r.key and r.key.startswith('sofzh_reward_') and
            re.search(r'(industry|infantry|artillery|small_arms|motor|tank|fighter|plane|naval|submarine|dockyard|doctrine|army_staff|railway_logistics)', r.key)
            for r in walk(n.value)) or ident.startswith('SOF_UNIFY_')
        extra = ''
        if military_or_industry:
            available = entries(n.value, 'available')
            if available:
                a = available[0]
                at = a.end - n.start - 1
                text = text[:at + len('shared_')] + ' sof_mrs_red_public_allowed = yes ' + text[at + len('shared_'):]
            else:
                extra += ' available = { sof_mrs_red_public_allowed = yes }\n'
        if not entries(n.value, 'relative_position_id'):
            extra += ' offset = { x = 80 y = 0 trigger = { original_tag = MRS } }\n'
        text = text[:-1] + '\n' + extra + '}'
        # Shared branches load their prerequisite descendants automatically.
        # Only reference roots, avoiding repeated inclusion of descendants.
        if any(r.key=='add_research_slot' for r in walk(n.value)):
            text = re.sub(r'add_research_slot\s*=\s*1',
                'if = { limit = { OR = { NOT = { original_tag = MRS } amount_research_slots < 4 } } add_research_slot = 1 }', text)
            availability=entries(parse(text)[0].value,'available')
            research_gate=' OR = { NOT = { original_tag = MRS } amount_research_slots < 4 } '
            if availability:
                at=availability[0].end-1;text=text[:at]+research_gate+text[at:]
            else:text=text[:-1]+' available = { '+research_gate+' } }'
        parse(text)
        shared.append(text)
        edits.append((n.start, n.end, 'shared_focus = ' + ident if ident in roots else ''))
    generic = replace(source, edits)
    put('common/national_focus/SoF_generic.txt', generic)
    put('common/national_focus/sof_mrs_shared_generic.txt', '\n\n'.join(shared))
    save_json(ROOT / 'design/marseille-public-focuses.json', dict(ids=public_ids, roots=roots, original_sha256=sha(source.encode()), count=153))
    return roots, nodes


def positions(design):
    out = {}
    for i in range(1, 6): out['A' + str(i)] = (18, i - 1)
    out.update(P1=(14,5),P2=(14,6),P3=(14,7),P4=(22,5),P5=(22,6),P6=(22,7),P7=(18,8),P8=(18,9))
    out.update(E1=(4,4),E2=(0,5),E3=(8,5),E4=(8,6),E5=(8,7),E6=(0,6),E7=(4,7),E8=(2,8),E9=(2,9),E10=(0,10),E11=(6,10),E12=(3,11))
    out.update(M1=(30,4),M2=(30,5),M3=(26,6),M4=(30,6),M5=(34,6),M6=(30,7),M7=(27,8),M8=(33,8),M9=(37,7),M10=(37,8),M11=(30,9),M12=(30,10))
    out.update(D1=(44,4),D2=(44,5),D3=(44,7),D4=(41,6),D5=(47,6),D6=(44,8),D7=(44,9))
    for i in range(1, 9): out['U' + str(i)] = (56, i + 3)
    by_code={n['code']:n for n in design};placed={};active=set()
    def place(code):
        if code in placed:return placed[code]
        assert code not in active,'Layout prerequisite cycle: '+code
        active.add(code)
        parents=[p for group in by_code[code]['prerequisites'] for p in group]
        y=max([out[code][1]]+[place(p)[1]+1 for p in parents])
        placed[code]=(out[code][0],y);active.remove(code);return placed[code]
    for code in out:place(code)
    out.update(placed)
    return out


def make_focuses(design, public_ids):
    R = {
        'A1': 'set_country_flag = sof_mrs_red_chosen add_popularity = { ideology = communism popularity = 0.08 } add_political_power = 25 country_event = { id = sof_mrs_red.1 days = 1 }',
        'A2': 'add_popularity = { ideology = communism popularity = 0.07 } add_stability = 0.03',
        'A3': 'army_experience = 15',
        'A4': 'add_political_power = -50 if = { limit = { NOT = { has_character = MRS_jean_cristofol } } recruit_character = MRS_jean_cristofol } promote_character = MRS_jean_cristofol set_politics = { ruling_party = communism elections_allowed = no } set_country_flag = sof_mrs_red_government sof_mrs_red_remove_legacy = yes set_cosmetic_tag = SOF_MRS_WORKERS country_event = { id = sof_mrs_red.2 days = 1 }',
        'A5': 'add_political_power = 25 set_variable = { sof_mrs_red_tension = 20 } set_country_flag = sof_mrs_red_congress sof_mrs_red_refresh_tension = yes country_event = { id = sof_mrs_red.3 days = 1 }',
        'P1': tension(-10) + ' sof_mrs_red_restore_ideas = yes',
        'P2': tension(5) + ' sof_mrs_red_restore_ideas = yes',
        'P3': 'country_event = { id = sof_mrs_red.4 days = 1 }',
        'P4': 'add_stability = 0.05 ' + tension(-10),
        'P5': 'add_stability = 0.05 sof_mrs_red_restore_ideas = yes',
        'P6': tension(-15),
        'P7': 'add_stability = 0.05 add_war_support = 0.05',
        'P8': 'set_country_flag = sof_mrs_red_emergency_ended clr_country_flag = sof_mrs_red_crisis_pending add_stability = 0.05 sof_mrs_red_refresh_tension = yes',
        'E1': bonus(),
        'E2': factory_reward('industrial_complex') + ' set_country_flag = sof_mrs_red_plan_started sof_mrs_red_restore_ideas = yes',
        'E3': factory_reward('industrial_complex'),
        'E4': bonus('excavation_tech'),
        'E5': '446 = { if = { limit = { is_owned_by = ROOT is_fully_controlled_by = ROOT NOT = { OR = { has_state_flag = sofzh_generic_aluminium_expansion has_state_flag = sofzh_mining_provence_bauxite_1 has_state_flag = sof_mrs_red_aluminium } } } add_resource = { type = aluminium amount = 4 } set_state_flag = sofzh_generic_aluminium_expansion set_state_flag = sofzh_mining_provence_bauxite_1 set_state_flag = sof_mrs_red_aluminium } }',
        'E6': 'custom_effect_tooltip = sof_mrs_red_transport_tt',
        'E7': factory_reward('arms_factory') + ' ' + bonus(),
        'E8': factory_reward('industrial_complex') + ' sof_mrs_red_restore_ideas = yes country_event = { id = sof_mrs_red.5 days = 1 }',
        'E9': factory_reward('arms_factory'),
        'E10': 'sof_mrs_red_restore_ideas = yes',
        'E11': 'add_stability = 0.05 sof_mrs_red_restore_ideas = yes',
        'E12': factory_reward('industrial_complex') + ' ' + bonus(),
        'M1': 'army_experience = 15',
        'M2': 'set_country_flag = sof_mrs_red_reform_started add_timed_idea = { idea = sof_mrs_red_reform days = 140 }',
        'M3': 'army_experience = 20 add_doctrine_cost_reduction = { name = sof_mrs_red_school cost_reduction = 0.5 uses = 1 category = land_doctrine }',
        'M4': 'sof_mrs_red_restore_ideas = yes',
        'M5': 'sof_mrs_red_restore_ideas = yes',
        'M6': 'remove_ideas = sof_mrs_red_reform army_experience = 15',
        'M7': 'sof_mrs_red_restore_ideas = yes',
        'M8': 'sof_mrs_red_restore_ideas = yes',
        'M9': factory_reward('dockyard') + ' ' + bonus('dd_tech'),
        'M10': bonus('naval_bomber') + ' navy_experience = 15',
        'M11': 'add_war_support = 0.1 add_stability = 0.05',
        'M12': 'add_timed_idea = { idea = sof_mrs_red_defence days = 120 }',
        'D1': bonus(),
        'D2': 'add_political_power = 25',
        'D3': 'add_political_power = -75 set_rule = { can_create_factions = yes } create_faction = sof_mrs_red_league set_country_flag = sof_mrs_red_league_created',
        'D4': 'add_stability = 0.05 ' + tension(-10),
        'D5': 'custom_effect_tooltip = sof_mrs_red_outreach_tt',
        'D6': 'custom_effect_tooltip = sof_mrs_red_escort_tt',
        'D7': 'set_country_flag = sof_mrs_red_tech_enabled sof_mrs_red_share_research = yes',
        'U1': 'set_country_flag = sofzh_unification_started set_country_flag = sofzh_unification_war_ready',
        'U2': 'custom_effect_tooltip = sof_mrs_red_rhone_tt',
        'U3': 'sof_mrs_red_region_name = yes',
        'U4': 'custom_effect_tooltip = sof_mrs_red_north_tt',
        'U5': 'add_stability = 0.05 add_political_power = 50',
        'U6': 'add_war_support = 0.05',
        'U7': 'sofzh_unification_proclaim_france = yes if = { limit = { has_country_flag = sofzh_unification_complete } remove_ideas = sofzh_unify_french_state set_cosmetic_tag = SOF_MRS_FRANCE set_country_flag = sof_mrs_red_national country_event = { id = sof_mrs_red.8 days = 1 } }',
        'U8': 'set_country_flag = { flag = sof_mrs_red_rebuilding days = 180 } sof_mrs_red_restore_ideas = yes',
    }
    G = {
        'A4': 'communism > 0.499 has_stability > 0.349 political_power > 49',
        'P3': 'political_power > 24',
        'P8': 'has_country_flag = { flag = sof_mrs_red_congress days > 179 } check_variable = { sof_mrs_red_tension < 40 } has_stability > 0.449',
        'E2': factory_gate('industrial_complex'), 'E3': factory_gate('industrial_complex'),
        'E5': '446 = { is_owned_by = ROOT is_fully_controlled_by = ROOT }',
        'E7': factory_gate('arms_factory'),
        'E8': 'has_country_flag = { flag = sof_mrs_red_plan_started days > 364 } ' + factories(6) + ' ' + factory_gate('industrial_complex'),
        'E9': french_states(15) + ' ' + factory_gate('arms_factory'),
        'E12': factory_gate('industrial_complex'),
        'M6': 'has_country_flag = { flag = sof_mrs_red_reform_started days > 139 }',
        'M9': factory_gate('dockyard'),
        'M11': 'has_defensive_war = yes',
        'M12': 'has_defensive_war = yes has_country_flag = { flag = sof_mrs_red_defensive_war days > 89 }',
        'D3': 'is_in_faction = no political_power > 74',
        'D7': 'any_other_country = { is_in_faction_with = ROOT is_subject = no has_capitulated = no }',
        'U1': 'num_divisions > 2 has_equipment = { infantry_equipment > 499 }',
        'U2': french_states(6) + ' sof_mrs_red_has_rhone_link = yes',
        'U3': french_states(8), 'U4': french_states(20),
        'U5': '143 = { is_owned_by = ROOT is_fully_controlled_by = ROOT }',
        'U6': french_states(272),
        'U7': 'sofzh_unification_all_france = yes has_war = no',
        'U8': 'has_war = no has_country_flag = { flag = sof_mrs_red_peace days > 179 }',
    }
    pairs = dict(P1='P4',P4='P1',E10='E11',E11='E10',M7='M8',M8='M7',D4='D5',D5='D4')
    tree = ['focus_tree = { id = sof_mrs_red country = { factor = 0 modifier = { add = 1000 original_tag = MRS } } default = no reset_on_civilwar = no initial_show_position = { focus = '+fid('A1')+' } continuous_focus_position = { x = 50 y = 3400 }']
    for code in ['A1','E1','M1','D1','U1']:
        localize('sof_mrs_red_shortcut_'+code, dict(A1='政治与夺权',E1='五年计划',M1='红军改革',D1='地中海外交',U1='统一法国')[code])
        tree.append(f'shortcut = {{ name = sof_mrs_red_shortcut_{code} target = {fid(code)} scroll_wheel_factor = 0.65 }}')
    tree.extend('shared_focus = '+i for i in public_ids)
    xy = positions(design)
    for n in design:
        code = n['code']; x,y = xy[code]
        icon = 'GFX_sof_mrs_red_' + code.lower()
        pre = ' '.join('prerequisite = { '+' '.join('focus = '+fid(v) for v in group)+' }' for group in n['prerequisites'])
        ex = f'mutually_exclusive = {{ focus = {fid(pairs[code])} }}' if code in pairs else ''
        common = 'sof_mrs_red_candidate = yes' if code in ['A1','A2','A3','A4'] else 'sof_mrs_red_active = yes'
        gate = common + ' ' + G.get(code,'')
        filtername = dict(A='POLITICAL',P='POLITICAL',E='INDUSTRY',M='ARMY_XP',D='POLITICAL',U='WAR_SUPPORT')[code[0]]
        reward = R[code]
        # Guard again at completion, and record each reward independently of
        # completed-focus state (migration/console commands cannot duplicate it).
        reward = 'sof_mrs_red_count_states = yes if = { limit = { '+gate+' NOT = { has_country_flag = sof_mrs_red_paid_'+code+' } } set_country_flag = sof_mrs_red_paid_'+code+' '+reward+' }'
        tree.append(f'focus = {{ id = {fid(code)} icon = {icon} cost = {n["days"]//7} x = {x} y = {y} {pre} {ex} search_filters = {{ FOCUS_FILTER_{filtername} }} available = {{ {gate} }} cancel_if_invalid = yes continue_if_invalid = no completion_reward = {{ {reward} }} ai_will_do = {{ factor = 12 }} }}')
        localize(fid(code), n['name'], n['description'])
        n.update(x=x,y=y,gate=gate,reward=R[code],exclusive=pairs.get(code))
    tree.append('}')
    put('common/national_focus/sof_mrs_red.txt', '\n'.join(tree))
    save_json(ROOT/'design/marseille-red-route.json', dict(version=VERSION,nodes=design,public_focus_count=153))


def make_ideas():
    specs = {
        'central_1': ('中央组织', {'political_power_factor':0.05}),
        'central_2': ('统一党的领导', {'political_power_factor':0.10,'industrial_capacity_factory':0.03}),
        'union': ('工会代表治理', {'political_power_factor':0.05,'industrial_capacity_factory':-0.03}),
        'plan_1': ('第一五年计划', {'production_speed_buildings_factor':0.05,'consumer_goods_factor':0.05}),
        'plan_2': ('第一计划验收', {'production_speed_buildings_factor':0.08,'consumer_goods_factor':0.03}),
        'plan_heavy': ('第二计划重工业方向', {'production_speed_buildings_factor':0.08,'industrial_capacity_factory':0.08,'production_factory_max_efficiency_factor':0.05,'consumer_goods_factor':0.05}),
        'plan_civil': ('第二计划民生方向', {'production_speed_buildings_factor':0.08,'industrial_capacity_factory':0.03,'consumer_goods_factor':-0.02}),
        'rebuilding': ('战后重建', {'industry_repair_factor':0.20,'consumer_goods_factor':0.05}),
        'reform': ('革命军整编期', {'army_org_factor':-0.05,'army_morale_factor':-0.05}),
        'commissars': ('政治委员制度', {'army_org_factor':0.03,'army_morale_factor':0.02}),
        'logistics': ('港口铁路军需', {'supply_consumption_factor':-0.05}),
        'mass': ('工农群众动员', {'conscription':0.005,'army_org_factor':0.03,'training_time_army_factor':0.05}),
        'cadres': ('职业骨干', {'experience_gain_army_factor':0.10,'army_attack_factor':0.03}),
        'defence': ('人民的卫国战争', {'army_core_defence_factor':0.10}),
        'dispute': ('港务与工会争议', {'political_power_factor':-0.10,'industrial_capacity_factory':-0.05}),
        'distrust': ('党政军互不信任', {'political_power_factor':-0.15,'industrial_capacity_factory':-0.05,'army_org_factor':-0.05}),
        'audit': ('组织审查恢复期', {'political_power_factor':-0.10,'industrial_capacity_factory':-0.05}),
        'paralysis': ('革命政府瘫痪', {'industrial_capacity_factory':-0.10}),
        'tech': ('社会主义技术合作', {}),
        'transport_work': ('交通工程占用民用工业', {'civilian_factory_use':2}),
    }
    output=['ideas = { country = {']
    for key,(name,mods) in specs.items():
        iid='sof_mrs_red_'+key
        cancel = 'NOT = { has_country_flag = sof_mrs_red_tech_partner }' if key=='tech' else 'NOT = { sof_mrs_red_active = yes }'
        picture = 'sofzh_spirit_v1_sofzh_reward_civil_industry_1' if key.startswith('plan') or key in ['rebuilding','tech'] else 'sofzh_spirit_v1_sofzh_reward_administration_1'
        research = 'research_bonus = { industry = 0.05 }' if key=='tech' else ''
        output.append(f'{iid} = {{ allowed = {{ always = no }} allowed_civil_war = {{ always = no }} removal_cost = -1 picture = {picture} cancel = {{ {cancel} }} {research} modifier = {{ '+ ' '.join(f'{k} = {v}' for k,v in mods.items())+' } }')
        localize(iid,name,'本精神由红色马赛线路获得。制度变更、项目期限和合作条件决定其是否保留；同一家族的阶段精神通过替换升级。')
    output.append('} }')
    put('common/ideas/sof_mrs_red.txt','\n'.join(output))
    return specs


def make_triggers():
    paca = [383,398,408,413,418,422,425,426,427,436,438,440,444,446,448,452,463,469,483,484]
    rhone = [301,307,308,313,314,315,316,319,329,330,336,337,339,341,342,355,360,361,365,375,377,385,396,397,406]
    text = '''
sof_mrs_red_candidate = {
 original_tag = MRS is_subject = no has_capitulated = no
 capital_scope = { is_owned_by = PREV is_fully_controlled_by = PREV }
}
sof_mrs_red_active = { sof_mrs_red_candidate = yes has_government = communism has_country_flag = sof_mrs_red_government }
sof_mrs_red_public_allowed = { NOT = { sof_mrs_red_active = yes } }
sof_mrs_red_partner_target = {
 sofzh_unification_candidate = yes is_subject = no has_capitulated = no has_war = no
 NOT = { tag = ROOT } NOT = { has_war_with = ROOT }
 NOT = { has_country_flag = sof_mrs_red_offer_target }
 OR = { is_neighbor_of = ROOT AND = { any_owned_state = { is_coastal = yes is_fully_controlled_by = PREV } ROOT = { any_owned_state = { is_coastal = yes is_fully_controlled_by = PREV } } } }
}
sof_mrs_red_federation_target = {
 sof_mrs_red_partner_target = yes has_government = communism is_in_faction_with = ROOT
 has_opinion = { target = ROOT value > 74 }
}
sof_mrs_red_campaign_target = {
 sofzh_unification_new_land_target = yes is_neighbor_of = ROOT
 NOT = { ROOT = { has_wargoal_against = PREV } }
}
sof_mrs_red_sea_target = {
 sofzh_unification_legal_target = yes NOT = { is_neighbor_of = ROOT }
 any_owned_state = { sofzh_unification_french_state = yes is_coastal = yes is_fully_controlled_by = PREV naval_base > 0 }
 NOT = { ROOT = { has_wargoal_against = PREV } }
}
sof_mrs_red_sea_ready = {
 has_navy_size = { size > 3 } has_equipment = { convoy > 19 }
 any_owned_state = { is_coastal = yes is_fully_controlled_by = PREV naval_base > 0 }
}
sof_mrs_red_offer_sender_valid = {
 FROM = { sof_mrs_red_active = yes has_war = no has_country_flag = sof_mrs_red_diplomatic_pending }
 sofzh_unification_candidate = yes has_war = no
 NOT = { has_war_with = FROM }
 has_country_flag = sof_mrs_red_offer_target
}
sof_mrs_red_invitation_valid = {
 sof_mrs_red_offer_sender_valid = yes has_government = communism is_in_faction = no
 FROM = { is_faction_leader = yes has_country_flag = sof_mrs_red_league_created }
}
sof_mrs_red_federation_valid = {
 sof_mrs_red_offer_sender_valid = yes has_government = communism
 is_in_faction_with = FROM has_opinion = { target = FROM value > 74 }
 OR = { is_neighbor_of = FROM AND = { any_owned_state = { is_coastal = yes is_fully_controlled_by = PREV } FROM = { any_owned_state = { is_coastal = yes is_fully_controlled_by = PREV } } } }
}
'''
    text += 'sof_mrs_red_paca_state = { OR = { '+ ' '.join('state = '+str(v) for v in paca) +' } }\n'
    text += 'sof_mrs_red_rhone_state = { OR = { '+ ' '.join('state = '+str(v) for v in rhone) +' } }\n'
    text += 'sof_mrs_red_all_paca = { '+ ' '.join(f'{v} = {{ is_owned_by = PREV is_fully_controlled_by = PREV }}' for v in paca) +' }\n'
    text += 'sof_mrs_red_has_rhone_link = { any_owned_state = { sof_mrs_red_rhone_state = yes is_fully_controlled_by = PREV } }\n'
    put('common/scripted_triggers/sof_mrs_red.txt',text)


def legacy_guards():
    blocked = set()
    family = re.compile(r'^sofzh_(reward|dedicated)_(civil_industry|mil_industry|dockyards|infantry|staff|engineering|artillery|motorized|armor|surface_navy|submarines|air_support|air_defence)_')
    for path in (MOD/'common/ideas').glob('*.txt'):
        for row in parse(path.read_text(encoding='utf-8-sig')):
            if row.key=='ideas':
                for group in row.value:
                    if isinstance(group.value,list):
                        for idea in group.value:
                            if idea.key and (family.match(idea.key) or idea.key.startswith('sofzh_ideology_')):
                                blocked.add(idea.key)
    blocked.update(['sofzh_unify_mobilization','sofzh_unify_unified_command','sofzh_unify_logistics','sofzh_unify_french_state','sofzh_unify_national_market'])
    guarded = []
    for path in (MOD/'common/scripted_effects').glob('*.txt'):
        if path.name == 'sof_mrs_red.txt': continue
        rel=path.relative_to(MOD).as_posix()
        current=path.read_text(encoding='utf-8-sig')
        if not any(word in current for word in blocked) and 'sofzh_sync_ideology' not in current: continue
        source=baseline(rel);changes=[]
        for effect in parse(source):
            if not isinstance(effect.value,list):continue
            grants = {r.value for r in walk(effect.value) if r.key in ['add_ideas','add_timed_idea','idea'] and isinstance(r.value,str)}
            # Do not guard the common national proclamation: its shared flag,
            # capital change and one-time political reward must still execute.
            if effect.key == 'sofzh_unification_proclaim_france':continue
            if effect.key == 'sofzh_sync_ideology' or grants & blocked:
                inner=source[source.index('{',effect.start)+1:effect.end-1]
                body=f'{effect.key} = {{ if = {{ limit = {{ sof_mrs_red_public_allowed = yes }} {inner} }} }}'
                changes.append((effect.start,effect.end,body));guarded.append(effect.key)
        if changes:put(rel,replace(source,changes))
    # Legacy campaign buttons must not bypass the new 90-day preparation.
    for rel in ['common/decisions/sofzh_unification.txt']:
        source=baseline(rel);changes=[]
        for group in parse(source):
            if not isinstance(group.value,list):continue
            for decision in group.value:
                if not isinstance(decision.value,list):continue
                for availability in entries(decision.value,'available'):
                    changes.append((availability.end-1,availability.end-1,' sof_mrs_red_public_allowed = yes '))
        if changes:put(rel,replace(source,changes))
    save_json(ROOT/'design/marseille-reward-guards.json',dict(blocked_ideas=sorted(blocked),guarded_effects=guarded))
    rel='common/scripted_triggers/sofzh_maritime_ai.txt'
    original=baseline(rel)
    anchor='sofzh_ai_naval_intent = {\n    OR = {'
    assert anchor in original
    put(rel,original.replace(anchor,anchor+'\n        AND = { original_tag = MRS has_focus_tree = sof_mrs_red has_completed_focus = SOF_MRS_RED_M9 }',1))
    return blocked


def make_effects(blocked):
    def paid(code):return 'has_country_flag = sof_mrs_red_paid_'+code
    def grant(idea):return f'if = {{ limit = {{ NOT = {{ has_idea = sof_mrs_red_{idea} }} }} add_ideas = sof_mrs_red_{idea} }}'
    def family(idea,others):
        return f'if = {{ limit = {{ NOT = {{ has_idea = sof_mrs_red_{idea} }} }} '+' '.join('remove_ideas = sof_mrs_red_'+other for other in others if other!=idea)+f' add_ideas = sof_mrs_red_{idea} }}'
    plan_names=['plan_1','plan_2','plan_heavy','plan_civil','rebuilding']
    restoration='''sof_mrs_red_restore_ideas = { if = { limit = { sof_mrs_red_active = yes }
'''
    for i,(condition,idea) in enumerate([(paid('P2'),'central_2'),(paid('P1'),'central_1'),(paid('P5'),'union')]):
        restoration+=('if' if i==0 else 'else_if')+' = { limit = { '+condition+' } '+family(idea,['central_1','central_2','union'])+' }\n'
    for i,(condition,idea) in enumerate([('has_country_flag = sof_mrs_red_rebuilding','rebuilding'),(paid('E10'),'plan_heavy'),(paid('E11'),'plan_civil'),(paid('E8'),'plan_2'),(paid('E2'),'plan_1')]):
        restoration+=('if' if i==0 else 'else_if')+' = { limit = { '+condition+' } '+family(idea,plan_names)+' }\n'
    for code,idea in [('M4','commissars'),('M5','logistics'),('M7','mass'),('M8','cadres')]:
        restoration+='if = { limit = { '+paid(code)+' } '+grant(idea)+' }\n'
    restoration+='} }\n'
    cleanup='sof_mrs_red_remove_legacy = { '+ ' '.join('remove_ideas = '+i for i in sorted(blocked))+' }\n'
    text=cleanup+restoration+'''
sof_mrs_red_count_states = {
 set_variable = { sof_mrs_red_french_states = 0 }
 every_owned_state = { limit = { sofzh_unification_french_state = yes is_fully_controlled_by = PREV }
  PREV = { add_to_variable = { sof_mrs_red_french_states = 1 } }
 }
}
sof_mrs_red_region_name = {
 if = { limit = { sof_mrs_red_active = yes }
  if = { limit = { has_country_flag = sof_mrs_red_national } set_cosmetic_tag = SOF_MRS_FRANCE }
  else_if = { limit = { has_completed_focus = SOF_MRS_RED_U3 sof_mrs_red_all_paca = yes } set_cosmetic_tag = SOF_MRS_PROVENCE }
  else = { set_cosmetic_tag = SOF_MRS_WORKERS }
 }
}
sof_mrs_red_resolve_crisis = {
 if = { limit = { sof_mrs_red_active = yes NOT = { has_country_flag = sof_mrs_red_emergency_ended } has_country_flag = { flag = sof_mrs_red_crisis_pending days > 89 } check_variable = { sof_mrs_red_tension >= 90 } NOT = { has_country_flag = sof_mrs_red_recovery } }
  add_political_power = -75 add_stability = -0.15
  remove_ideas = sof_mrs_red_distrust remove_ideas = sof_mrs_red_dispute
  add_timed_idea = { idea = sof_mrs_red_paralysis days = 180 }
  set_country_flag = { flag = sof_mrs_red_recovery days = 180 }
  clr_country_flag = sof_mrs_red_crisis_pending set_variable = { sof_mrs_red_tension = 60 }
  sof_mrs_red_refresh_tension = yes
 }
}
sof_mrs_red_refresh_tension = {
 clamp_variable = { var = sof_mrs_red_tension min = 0 max = 100 }
 if = { limit = { sof_mrs_red_active = yes NOT = { has_country_flag = sof_mrs_red_emergency_ended } NOT = { has_country_flag = sof_mrs_red_recovery } has_country_flag = sof_mrs_red_congress }
  if = { limit = { check_variable = { sof_mrs_red_tension >= 70 } }
   remove_ideas = sof_mrs_red_dispute
   if = { limit = { NOT = { has_idea = sof_mrs_red_distrust } } add_ideas = sof_mrs_red_distrust }
  } else_if = { limit = { check_variable = { sof_mrs_red_tension >= 40 } }
   remove_ideas = sof_mrs_red_distrust
   if = { limit = { NOT = { has_idea = sof_mrs_red_dispute } } add_ideas = sof_mrs_red_dispute }
  } else = { remove_ideas = sof_mrs_red_dispute remove_ideas = sof_mrs_red_distrust }
  if = { limit = { check_variable = { sof_mrs_red_tension >= 90 } NOT = { has_country_flag = sof_mrs_red_crisis_pending } NOT = { has_country_flag = sof_mrs_red_recovery } }
   set_country_flag = sof_mrs_red_crisis_pending country_event = { id = sof_mrs_red.7 days = 1 } country_event = { id = sof_mrs_red.15 days = 90 }
  }
  if = { limit = { check_variable = { sof_mrs_red_tension < 90 } } clr_country_flag = sof_mrs_red_crisis_pending }
 } else = { remove_ideas = sof_mrs_red_dispute remove_ideas = sof_mrs_red_distrust clr_country_flag = sof_mrs_red_crisis_pending }
}
sof_mrs_red_share_research = {
 every_country = { limit = { has_country_flag = sof_mrs_red_tech_partner NOT = { AND = { is_subject = no has_capitulated = no MRS = { sof_mrs_red_active = yes has_country_flag = sof_mrs_red_tech_enabled is_in_faction = yes } OR = { tag = MRS is_in_faction_with = MRS } } } }
  clr_country_flag = sof_mrs_red_tech_partner remove_ideas = sof_mrs_red_tech
 }
 if = { limit = { sof_mrs_red_active = yes has_country_flag = sof_mrs_red_tech_enabled is_in_faction = yes }
  every_country = { limit = { is_subject = no has_capitulated = no OR = { tag = MRS is_in_faction_with = MRS } }
   set_country_flag = sof_mrs_red_tech_partner if = { limit = { NOT = { has_idea = sof_mrs_red_tech } } add_ideas = sof_mrs_red_tech }
  }
 }
}
sof_mrs_red_weekly = {
 if = { limit = { original_tag = MRS }
  if = { limit = { OR = { has_focus_tree = sof_generic has_focus_tree = sof20_MRS } }
   load_focus_tree = { tree = sof_mrs_red keep_completed = yes }
  }
  sof_mrs_red_count_states = yes
  if = { limit = { sof_mrs_red_active = yes }
   sof_mrs_red_remove_legacy = yes sof_mrs_red_restore_ideas = yes sof_mrs_red_refresh_tension = yes sof_mrs_red_region_name = yes
   if = { limit = { has_war = no NOT = { has_country_flag = sof_mrs_red_peace } } set_country_flag = sof_mrs_red_peace }
   if = { limit = { has_war = yes } clr_country_flag = sof_mrs_red_peace }
   if = { limit = { has_defensive_war = yes NOT = { has_country_flag = sof_mrs_red_defensive_war } } set_country_flag = sof_mrs_red_defensive_war }
   if = { limit = { has_defensive_war = no } clr_country_flag = sof_mrs_red_defensive_war }
  } else = {
   clr_country_flag = sof_mrs_red_peace clr_country_flag = sof_mrs_red_defensive_war
   clr_country_flag = sof_mrs_red_crisis_pending
   if = { limit = { has_country_flag = sof_mrs_red_government NOT = { has_government = communism } } drop_cosmetic_tag = yes }
  }
  sof_mrs_red_share_research = yes
 }
}
sof_mrs_red_monthly = {
 if = { limit = { sof_mrs_red_active = yes has_country_flag = sof_mrs_red_congress NOT = { has_country_flag = sof_mrs_red_emergency_ended } }
  add_to_variable = { sof_mrs_red_tension = 3 } sof_mrs_red_refresh_tension = yes
 }
}
sof_mrs_red_finish_offer = {
 clr_country_flag = sof_mrs_red_offer_target
 FROM = { clr_country_flag = sof_mrs_red_diplomatic_pending }
}
sof_mrs_red_refuse_offer = {
 sof_mrs_red_finish_offer = yes
 FROM = { country_event = { id = sof_mrs_red.13 days = 1 } }
}
sof_mrs_red_accept_federation = {
 if = { limit = { sof_mrs_red_federation_valid = yes }
  every_owned_state = { set_state_flag = sof_mrs_red_negotiated_transfer }
  sof_mrs_red_finish_offer = yes
  FROM = {
   annex_country = { target = ROOT transfer_troops = no }
   every_owned_state = { limit = { has_state_flag = sof_mrs_red_negotiated_transfer }
    if = { limit = { sofzh_unification_french_state = yes is_owned_by = PREV is_fully_controlled_by = PREV NOT = { is_core_of = PREV } }
     if = { limit = { NOT = { has_state_flag = sofzh_occupation_registered } } sofzh_occupation_register = yes }
    }
    clr_state_flag = sof_mrs_red_negotiated_transfer
   }
   country_event = { id = sof_mrs_red.14 days = 1 }
  }
 }
}
'''
    put('common/scripted_effects/sof_mrs_red.txt',text)
    put('common/on_actions/zz_sof_mrs_red.txt','''on_actions = {
 on_startup = { effect = { every_country = { limit = { original_tag = MRS } sof_mrs_red_weekly = yes } } }
 on_weekly = { effect = { if = { limit = { original_tag = MRS } sof_mrs_red_weekly = yes } } }
 on_monthly = { effect = { if = { limit = { original_tag = MRS } sof_mrs_red_monthly = yes } } }
}''')


def make_decisions():
    tags=[]
    for path in (MOD/'common/country_tags').glob('*.txt'):
        tags.extend(r.key for r in parse(path.read_text(encoding='utf-8-sig')) if r.key and r.key!='MRS' and isinstance(r.value,str) and r.value.strip('"').startswith('countries/'))
    targets='targets = { '+' '.join(sorted(set(tags)))+' }'
    output=['sof_mrs_red_politics = {']
    def decision(group,key,name,desc,body):
        output.append(f'sof_mrs_red_{key} = {{ {body} }}')
        localize('sof_mrs_red_'+key,name,desc)
    def lower(key,name,condition,cost,days,amount,cooldown,stability=0):
        decision('politics',key,name,f'消耗{cost}政治点，办理{days}天，党内矛盾减少{amount}；冷却{cooldown}天。同一时间只能进行一个政治协调项目。',f'''
icon = sof_cw_accord cost = {cost} days_remove = {days} days_re_enable = {cooldown}
visible = {{ has_country_flag = sof_mrs_red_congress {condition} NOT = {{ has_country_flag = sof_mrs_red_emergency_ended }} }}
available = {{ sof_mrs_red_active = yes NOT = {{ has_country_flag = sof_mrs_red_political_work }} check_variable = {{ sof_mrs_red_tension > 0 }} }}
complete_effect = {{ set_country_flag = sof_mrs_red_political_work }}
remove_effect = {{ clr_country_flag = sof_mrs_red_political_work if = {{ limit = {{ sof_mrs_red_active = yes }} {tension(-amount)} add_stability = {stability} }} }}
cancel_trigger = {{ sof_mrs_red_active = no }} cancel_effect = {{ clr_country_flag = sof_mrs_red_political_work }}
ai_will_do = {{ factor = 2 modifier = {{ factor = 8 check_variable = {{ sof_mrs_red_tension >= 40 }} }} modifier = {{ factor = 0 check_variable = {{ sof_mrs_red_tension < 20 }} }} }}''')
    lower('central_meeting','召开组织整顿会议',done('P1'),35,45,15,90)
    lower('union_meeting','协调工会与市镇代表',done('P4'),35,45,15,90)
    lower('food_supply','改善粮食和港区供给','',50,60,10,180,0.03)
    decision('politics','communist_campaign','继续组织共产主义宣传','消耗25政治点，35天后共产党支持率增加5个百分点。支持率不足时仍可推进政权交接。','''
icon = sof_cw_civil cost = 25 days_remove = 35 days_re_enable = 60
visible = { has_country_flag = sof_mrs_red_chosen NOT = { has_country_flag = sof_mrs_red_government } }
available = { sof_mrs_red_candidate = yes communism < 0.6 }
remove_effect = { if = { limit = { sof_mrs_red_candidate = yes } add_popularity = { ideology = communism popularity = 0.05 } } }
cancel_trigger = { sof_mrs_red_candidate = no }
ai_will_do = { factor = 10 modifier = { factor = 0 communism > 0.499 } }''')
    decision('politics','engineering_slot','建立港区科研学院','12座民用及军用工厂以上可一次增加科研槽，总数上限4。若已由通用研究取得第四槽则无法重复领取。',f'''
icon = sof_cw_specialty cost = 75 fire_only_once = yes
visible = {{ {done('E7')} NOT = {{ has_country_flag = sof_mrs_red_research_paid }} }}
available = {{ sof_mrs_red_active = yes {factories(12)} amount_research_slots < 4 }}
complete_effect = {{ if = {{ limit = {{ amount_research_slots < 4 NOT = {{ has_country_flag = sof_mrs_red_research_paid }} }} add_research_slot = 1 set_country_flag = sof_mrs_red_research_paid }} }}
ai_will_do = {{ factor = 8 }}''')
    output.append('}\nsof_mrs_red_military = {')
    decision('military','militia_course','赤卫队训练章程','消耗25政治点和150步兵装备进行60天训练；获得3营赤卫队模板及10陆军经验。部队须在原生招募界面训练，实际消耗装备和人力。',f'''
icon = sof_cw_specialty cost = 25 days_remove = 60 fire_only_once = yes
visible = {{ OR = {{ {done('A3')} {done('M1')} }} NOT = {{ has_country_flag = sof_mrs_red_militia_template }} }}
available = {{ sof_mrs_red_candidate = yes manpower > 2999 has_equipment = {{ infantry_equipment > 149 }} }}
custom_cost_trigger = {{ has_equipment = {{ infantry_equipment > 149 }} }} custom_cost_text = sof_mrs_red_militia_cost_tt
complete_effect = {{ add_equipment_to_stockpile = {{ type = infantry_equipment amount = -150 }} set_country_flag = sof_mrs_red_militia_training }}
remove_effect = {{ clr_country_flag = sof_mrs_red_militia_training if = {{ limit = {{ sof_mrs_red_candidate = yes NOT = {{ has_country_flag = sof_mrs_red_militia_template }} }}
division_template = {{ name = "马赛赤卫队" regiments = {{ infantry = {{ x = 0 y = 0 }} infantry = {{ x = 0 y = 1 }} infantry = {{ x = 0 y = 2 }} }} priority = 0 }}
set_country_flag = sof_mrs_red_militia_template army_experience = 10 }} }}
cancel_trigger = {{ sof_mrs_red_candidate = no }} cancel_effect = {{ if = {{ limit = {{ has_country_flag = sof_mrs_red_militia_training }} add_equipment_to_stockpile = {{ type = infantry_equipment amount = 150 }} clr_country_flag = sof_mrs_red_militia_training }} }}
ai_will_do = {{ factor = 4 }}''')
    decision('military','transport_investment','投资港口与内陆铁路','投入35政治点，占用2座民用工厂90天；在全线属于本国的路径上建设或升级2级铁路。目标失控则取消，不跨越外国领土。',f'''
icon = sof_cw_supply state_target = any_owned_state on_map_mode = map_and_decisions_view cost = 35 days_remove = 90 days_re_enable = 180
target_root_trigger = {{ original_tag = MRS }} target_trigger = {{ FROM = {{ sofzh_unification_french_state = yes is_fully_controlled_by = ROOT NOT = {{ state = 463 }} }} }}
visible = {{ {done('E6')} }}
available = {{ sof_mrs_red_active = yes NOT = {{ has_country_flag = sof_mrs_red_transport_pending }} num_of_available_civilian_factories > 1 463 = {{ is_owned_by = ROOT is_fully_controlled_by = ROOT }} FROM = {{ is_owned_by = ROOT is_fully_controlled_by = ROOT }} }}
complete_effect = {{ set_country_flag = sof_mrs_red_transport_pending add_ideas = sof_mrs_red_transport_work }}
remove_effect = {{ clr_country_flag = sof_mrs_red_transport_pending remove_ideas = sof_mrs_red_transport_work if = {{ limit = {{ sof_mrs_red_active = yes FROM = {{ is_owned_by = ROOT is_fully_controlled_by = ROOT }} 463 = {{ is_owned_by = ROOT is_fully_controlled_by = ROOT }} }}
build_railway = {{ level = 2 start_state = 463 target_state = FROM build_only_on_allied = yes controller_priority = {{ base = -1 modifier = {{ add = 2 tag = MRS }} }} }} }} }}
cancel_trigger = {{ OR = {{ sof_mrs_red_active = no FROM = {{ OR = {{ NOT = {{ is_owned_by = ROOT }} NOT = {{ is_fully_controlled_by = ROOT }} }} }} 463 = {{ OR = {{ NOT = {{ is_owned_by = ROOT }} NOT = {{ is_fully_controlled_by = ROOT }} }} }} }} }}
cancel_effect = {{ clr_country_flag = sof_mrs_red_transport_pending remove_ideas = sof_mrs_red_transport_work }}
ai_will_do = {{ factor = 2 modifier = {{ factor = 0 has_war = yes }} }}''')
    # Country targets use the game's explicit target list, not undocumented
    # dynamic target selectors. The legal target filter prunes this to neighbors.
    decision('military','campaign_prepare','准备陆上革命战役','消耗50政治点、准备90天；成功后对所选合法相邻政权取得180天有效的战争目标。一次只准备一个目标，不自动宣战。',f'''
icon = sof_cw_campaign {targets} cost = 50 days_remove = 90 days_re_enable = 180
target_root_trigger = {{ original_tag = MRS }} target_trigger = {{ FROM = {{ sof_mrs_red_campaign_target = yes }} }}
visible = {{ {done('U1')} NOT = {{ has_country_flag = sofzh_unification_complete }} }}
available = {{ sof_mrs_red_active = yes has_war = no NOT = {{ has_country_flag = sof_mrs_red_campaign_pending }} FROM = {{ sof_mrs_red_campaign_target = yes }} }}
complete_effect = {{ set_country_flag = sof_mrs_red_campaign_pending }}
remove_effect = {{ clr_country_flag = sof_mrs_red_campaign_pending if = {{ limit = {{ sof_mrs_red_active = yes has_war = no FROM = {{ sof_mrs_red_campaign_target = yes }} }} create_wargoal = {{ type = annex_everything target = FROM expire = 180 }} }} }}
cancel_trigger = {{ OR = {{ sof_mrs_red_active = no has_war = yes FROM = {{ sof_mrs_red_campaign_target = no }} }} }}
cancel_effect = {{ clr_country_flag = sof_mrs_red_campaign_pending }}
ai_will_do = {{ factor = 4 modifier = {{ factor = 0 OR = {{ has_stability < 0.45 manpower < 3000 strength_ratio = {{ tag = FROM ratio < 1.1 }} FROM = {{ OR = {{ has_war = yes is_in_faction = yes }} }} }} }} }}''')
    decision('military','sea_campaign_prepare','准备海上革命战役','需要4艘军舰、20艘运输船与受控港口。消耗50政治点、准备90天，取得对合法法国沿海政权的180天战争目标；舰队、登陆计划和宣战仍需自行安排。与陆上准备共用一个筹备名额。',f'''
icon = sof_cw_campaign {targets} cost = 50 days_remove = 90 days_re_enable = 180
target_root_trigger = {{ original_tag = MRS }} target_trigger = {{ FROM = {{ sof_mrs_red_sea_target = yes }} }}
visible = {{ {done('U1')} {done('M9')} NOT = {{ has_country_flag = sofzh_unification_complete }} }}
available = {{ sof_mrs_red_active = yes has_war = no sof_mrs_red_sea_ready = yes NOT = {{ has_country_flag = sof_mrs_red_campaign_pending }} FROM = {{ sof_mrs_red_sea_target = yes }} }}
complete_effect = {{ set_country_flag = sof_mrs_red_campaign_pending }}
remove_effect = {{ clr_country_flag = sof_mrs_red_campaign_pending if = {{ limit = {{ sof_mrs_red_active = yes has_war = no sof_mrs_red_sea_ready = yes FROM = {{ sof_mrs_red_sea_target = yes }} }} create_wargoal = {{ type = annex_everything target = FROM expire = 180 }} }} }}
cancel_trigger = {{ OR = {{ sof_mrs_red_active = no has_war = yes sof_mrs_red_sea_ready = no FROM = {{ sof_mrs_red_sea_target = no }} }} }}
cancel_effect = {{ clr_country_flag = sof_mrs_red_campaign_pending }}
ai_will_do = {{ factor = 1 }}''')
    output.append('}\nsof_mrs_red_diplomacy = {')
    offers=[('invite','邀请加入社会主义协约','D3',40,0,6,'has_government = communism is_in_faction = no','is_faction_leader = yes'),
            ('outreach','国际工人互助提案','D5',40,0,9,'is_neighbor_of = ROOT',''),
            ('coal_supply','煤炭采购联络','E4',25,0,11,'any_owned_state = { has_resources_amount = { resource = coal amount > 0 } }',''),
            ('naval_escort','地中海护航协定','D6',35,0,12,'is_in_faction_with = ROOT','has_navy_size = { size > 3 }'),
            ('federation','提出社会主义联邦谈判','U3',75,180,10,'sof_mrs_red_federation_target = yes','has_equipment = { support_equipment > 49 } NOT = { has_country_flag = sof_mrs_red_federal_pending }')]
    for key,name,code,cost,days,event,target_gate,actor_gate in offers:
        project = 'days_remove = 180' if days else ''
        send=f'FROM = {{ set_country_flag = {{ flag = sof_mrs_red_offer_target days = 30 }} country_event = {{ id = sof_mrs_red.{event} days = 1 }} }} set_country_flag = {{ flag = sof_mrs_red_diplomatic_pending days = 30 }}'
        extra=''
        complete=send
        if key=='federation':
            complete='add_equipment_to_stockpile = { type = support_equipment amount = -50 } set_country_flag = sof_mrs_red_federal_pending'
            extra=f'''remove_effect = {{ clr_country_flag = sof_mrs_red_federal_pending if = {{ limit = {{ sof_mrs_red_active = yes has_war = no FROM = {{ sof_mrs_red_federation_target = yes }} }} {send} }} }}
cancel_trigger = {{ OR = {{ sof_mrs_red_active = no has_war = yes FROM = {{ sof_mrs_red_federation_target = no }} }} }} cancel_effect = {{ clr_country_flag = sof_mrs_red_federal_pending }}
custom_cost_trigger = {{ has_equipment = {{ support_equipment > 49 }} }} custom_cost_text = sof_mrs_red_federation_cost_tt'''
        decision('diplomacy',key,name,'只向合格的实际存在国家提出合作，由目标明确接受或拒绝。领土合并不授予核心，仍需占领治理。',f'''
icon = sof_cw_offer {targets} cost = {cost} days_re_enable = 180 {project}
target_root_trigger = {{ original_tag = MRS }} target_trigger = {{ FROM = {{ sof_mrs_red_partner_target = yes {target_gate} }} }}
visible = {{ {done(code)} }} available = {{ sof_mrs_red_active = yes has_war = no NOT = {{ has_country_flag = sof_mrs_red_diplomatic_pending }} NOT = {{ has_country_flag = sof_mrs_red_federal_pending }} {actor_gate} FROM = {{ sof_mrs_red_partner_target = yes {target_gate} }} }}
complete_effect = {{ {complete} }} {extra}
ai_will_do = {{ factor = 2 modifier = {{ factor = 0 has_stability < 0.45 }} }}''')
    output.append('}')
    put('common/decisions/sof_mrs_red.txt','\n'.join(output))
    put('common/decisions/categories/sof_mrs_red.txt','''
sof_mrs_red_politics = { icon = sof_cw_civil visible = { original_tag = MRS has_country_flag = sof_mrs_red_chosen } }
sof_mrs_red_military = { icon = sof_cw_supply visible = { original_tag = MRS has_country_flag = sof_mrs_red_chosen } }
sof_mrs_red_diplomacy = { icon = sof_cw_pact visible = { original_tag = MRS has_country_flag = sof_mrs_red_government } }
''')
    for key,name in [('politics','红色马赛政治协调'),('military','红军与港口工程'),('diplomacy','社会主义外交')]:
        localize('sof_mrs_red_'+key,name,'党内矛盾：[?sof_mrs_red_tension|0]。拥有并完全控制的法国州：[?sof_mrs_red_french_states|0]。所有项目检查政治、领土和实际库存条件。')


def make_events():
    text=['add_namespace = sof_mrs_red']
    def event(number,title,desc,options):
        key=f'sof_mrs_red.{number}'
        localize(key+'.t',title);localize(key+'.d',desc)
        text.append(f'country_event = {{ id = {key} title = {key}.t desc = {key}.d picture = GFX_report_event_generic_read_write is_triggered_only = yes '+options+' }')
    def option(number,letter,name,body=''):
        key=f'sof_mrs_red.{number}.{letter}';localize(key,name)
        return f'option = {{ name = {key} {body} }}'
    event(1,'旧港的政治集会','港口工人开始建立跨码头的组织网络。共产党需要争取多数支持，准备地方自卫，并把市政权力交接与生产秩序一起安排。',option(1,'a','组织工人代表会'))
    event(2,'市政权力的交接','工人代表会取得执政权，让·克里斯托福尔成为新政府领袖。马赛工人共和国需要处理工会、市镇与军事机构之间的权力关系。',option(2,'a','建立工人共和国'))
    event(3,'马赛共产党第一次代表大会','党内矛盾从20开始，每月增加3。中央组织和工会代表大会是互斥的治理方向；政治协调、粮食供给和结束紧急状态可以恢复稳定。',option(3,'a','制定党的组织路线'))
    event(4,'港务反对派的审查','虚构的港务反对派要求放慢集中管理。政治妥协消耗50政治点，减少15矛盾；免职行动消耗25政治点，减少25矛盾，但180天内政治点获取减少10%、工厂产出减少5%。',
          option(4,'a','政治妥协','trigger = { sof_mrs_red_active = yes political_power > 49 } ai_chance = { factor = 60 } add_political_power = -50 '+tension(-15))+
          option(4,'b','免职港务反对派','trigger = { sof_mrs_red_active = yes political_power > 24 } ai_chance = { factor = 30 } add_political_power = -25 '+tension(-25)+' add_timed_idea = { idea = sof_mrs_red_audit days = 180 }')+
          option(4,'c','暂缓处理','ai_chance = { factor = 10 }'))
    event(5,'第一计划的年度报告','第一计划已经运行至少一年，并完成港务、机具、交通和工厂条件验收。下一阶段要在实际拥有的地区上组织新的产业规模。',option(5,'a','准备第二五年计划'))
    event(7,'革命政府的九十日警告','党内矛盾达到90。政府有90天处理分歧，降到90以下会取消倒计时。若危机持续，将损失75政治点、15稳定度，并承受180天工厂产出减少10%的政府瘫痪。',option(7,'a','立即开始政治协调'))
    event(8,'法兰西社会主义共和国成立','全国建国条件已经完成。统一并不消除地方治理问题；非核心地区仍须达到控制时间、顺从度、抵抗度和登记费用要求。',option(8,'a','开始战后建设'))
    common='ai_chance = { factor = 30 modifier = { factor = 0 has_stability > 0.8 } }'
    refusal=lambda n,refund='':option(n,'b','拒绝提案','ai_chance = { factor = 70 } '+refund+' sof_mrs_red_refuse_offer = yes')
    event(6,'地中海社会主义协约邀请','马赛邀请我国加入社会主义协约。接受后将加入其阵营；政府与领土保持独立。',
          option(6,'a','加入协约','trigger = { sof_mrs_red_invitation_valid = yes } '+common+' FROM = { add_to_faction = ROOT } sof_mrs_red_finish_offer = yes')+refusal(6))
    event(9,'国际工人互助提案','马赛提出政治组织和教育互助。接受后共产党支持率增加5个百分点，我国获得15政治点；拒绝不会改变我国政体或支持率。',
          option(9,'a','接受互助','trigger = { sof_mrs_red_offer_sender_valid = yes } ai_chance = { factor = 15 modifier = { factor = 0 AND = { NOT = { has_government = communism } has_stability > 0.6 } } } add_popularity = { ideology = communism popularity = 0.05 } add_political_power = 15 sof_mrs_red_finish_offer = yes')+
          refusal(9,'if = { limit = { sof_mrs_red_offer_sender_valid = yes } FROM = { add_political_power = 20 } }'))
    event(10,'社会主义联邦谈判的结果','经历180天的关系培养后，马赛提出正式合并。接受将把我国领土并入马赛，原有军队不作为免费奖励转交，新地区不自动成为核心。',
          option(10,'a','同意加入联邦','trigger = { sof_mrs_red_federation_valid = yes } ai_chance = { factor = 10 modifier = { factor = 0 num_of_owned_states > 8 } } sof_mrs_red_accept_federation = yes')+refusal(10))
    for n,title,desc,extra in [(11,'煤炭供应联络','马赛希望建立采购渠道。接受改善双方关系；资源必须由原生贸易实际采购与运输，协议不生成资源。',''),(12,'地中海护航协定','双方将协调现有舰队的任务安排。接受改善外交关系，护航仍需在海军界面实际执行，协议不自动保证运输安全。','is_in_faction_with = FROM')]:
        event(n,title,desc,option(n,'a','同意开展合作','trigger = { sof_mrs_red_offer_sender_valid = yes '+extra+' } '+common+' add_opinion_modifier = { target = FROM modifier = sof_mrs_red_cooperation } FROM = { add_opinion_modifier = { target = ROOT modifier = sof_mrs_red_cooperation } } sof_mrs_red_finish_offer = yes')+refusal(n))
    event(13,'合作提案遭到拒绝','对方政府拒绝了当前提案。双方领土与政体没有变化；可在冷却结束且条件符合时重新接触。',option(13,'a','尊重对方的决定'))
    event(14,'地方政权加入联邦','地方政权同意并入我国。新地区进入正常治理流程，登记整合仍需政治点、装备、顺从度、抵抗度与连续控制时间。',option(14,'a','组织地方登记'))
    text.append('country_event = { id = sof_mrs_red.15 hidden = yes is_triggered_only = yes immediate = { sof_mrs_red_resolve_crisis = yes } }')
    put('events/sof_mrs_red.txt','\n'.join(text))
    put('common/opinion_modifiers/sof_mrs_red.txt','opinion_modifiers = { sof_mrs_red_cooperation = { value = 30 decay = 0.05 } }')
    localize('sof_mrs_red_cooperation','社会主义合作协议')


def make_owned_railways():
    """Use verified existing rail segments and check every state of each path.

    Controller-priority pathing alone would also allow occupied foreign states;
    explicit paths make the ownership promise verifiable before and after work.
    """
    province_state={};capital={};france=set()
    trigger=one(parse((MOD/'common/scripted_triggers/sofzh_unification.txt').read_text(encoding='utf-8-sig')),'sofzh_unification_french_state')
    france={int(r.value) for r in walk(trigger.value) if r.key=='state'}
    for p in (MOD/'history/states').glob('*.txt'):
        s=one(parse(p.read_text(encoding='utf-8-sig')),'state').value
        sid=int(scalar(s,'id'))
        provinces=one(s,'provinces').value
        for r in provinces:province_state[int(r.value)]=sid
        histories=entries(s,'history')
        h=histories[0].value if histories else []
        points=[]
        for vp in entries(h,'victory_points'):
            values=[int(v.value) for v in vp.value]
            if len(values)==2:points.append((values[1],values[0]))
        if provinces:capital[sid]=max(points)[1] if points else int(provinces[0].value)
    graph=defaultdict(set)
    for line in (MOD/'map/railways.txt').read_text(encoding='utf-8-sig').splitlines():
        numbers=[int(n) for n in line.split('#')[0].split()]
        if len(numbers)<3:continue
        path=numbers[2:]
        assert len(path)==numbers[1]
        for a,b in zip(path,path[1:]):graph[a].add(b);graph[b].add(a)
    previous={929:None};queue=deque([929])
    while queue:
        current=queue.popleft()
        for neighbor in sorted(graph[current]):
            if neighbor not in previous:previous[neighbor]=current;queue.append(neighbor)
    gates=[];effects=[];routes=[]
    for sid in sorted(france-{463}):
        destination=capital.get(sid)
        if destination not in previous:continue
        path=[];v=destination
        while v is not None:path.append(v);v=previous[v]
        path.reverse()
        states=sorted({province_state[v] for v in path})
        control=' '.join(f'{s} = {{ is_owned_by = ROOT is_fully_controlled_by = ROOT }}' for s in states)
        gates.append(f'AND = {{ state = {sid} {control} }}')
        effects.append(f'if = {{ limit = {{ state = {sid} {control} }} build_railway = {{ level = 2 path = {{ '+ ' '.join(map(str,path))+' } } }')
        routes.append(dict(state=sid,provinces=path,states=states))
    assert len(routes)>200,len(routes)
    put('common/scripted_triggers/sof_mrs_railways.txt','sof_mrs_red_transport_target = { OR = { '+'\n'.join(gates)+' } }')
    put('common/scripted_effects/sof_mrs_railways.txt','sof_mrs_red_build_owned_railway = { '+'\n'.join(effects)+' }')
    rel='common/decisions/sof_mrs_red.txt'
    text=(MOD/rel).read_text(encoding='utf-8')
    text=text.replace('sofzh_unification_french_state = yes is_fully_controlled_by = ROOT NOT = { state = 463 }','sof_mrs_red_transport_target = yes')
    text=text.replace('FROM = { is_owned_by = ROOT is_fully_controlled_by = ROOT }','FROM = { sof_mrs_red_transport_target = yes }')
    text=text.replace('build_railway = { level = 2 start_state = 463 target_state = FROM build_only_on_allied = yes controller_priority = { base = -1 modifier = { add = 2 tag = MRS } } }','FROM = { sof_mrs_red_build_owned_railway = yes }')
    text=text.replace('FROM = { OR = { NOT = { is_owned_by = ROOT } NOT = { is_fully_controlled_by = ROOT } } }','FROM = { sof_mrs_red_transport_target = no }')
    put(rel,text)
    save_json(ROOT/'design/marseille-railway-paths.json',dict(source='map/railways.txt',routes=routes))


def make_localization_and_flags():
    for key,name in [('SOF_MRS_WORKERS','马赛工人共和国'),('SOF_MRS_PROVENCE','普罗旺斯社会主义共和国'),('SOF_MRS_FRANCE','法兰西社会主义共和国')]:
        for suffix in ['communism','communism_DEF','communism_ADJ']:localize(key+'_'+suffix,name)
        for size in ['', 'medium/', 'small/']:
            rel='gfx/flags/'+size+key+'.tga'
            data=(MOD/('gfx/flags/'+size+'MRS_communism.tga')).read_bytes()
            destination=MOD/rel;destination.parent.mkdir(parents=True,exist_ok=True)
            stage=PASS/'overlay'/rel;stage.parent.mkdir(parents=True,exist_ok=True)
            assert not destination.exists() or destination.read_bytes()==data
            destination.write_bytes(data);stage.write_bytes(data);OUTPUT[rel]=sha(data)
    for key,value in {
        'sof_mrs_red_league':'地中海社会主义协约',
        'sof_mrs_red_study':'苏维埃技术资料',
        'sof_mrs_red_school':'红军军官课程',
        'sof_mrs_red_transport_tt':'解锁港口与内陆铁路投资，需实际拥有并控制整条线路；占用两座民用工厂90天。',
        'sof_mrs_red_outreach_tt':'解锁政治互助提案，目标可接受或拒绝，180天冷却。',
        'sof_mrs_red_escort_tt':'解锁护航外交协作；实际护航由现有舰队的原生任务完成。',
        'sof_mrs_red_rhone_tt':'开放罗讷河谷方向的扩张与行政发展；战争目标仍需90天准备。',
        'sof_mrs_red_north_tt':'开放北方工人联络。实际拥有与控制的领土决定全国大会资格。',
        'sof_mrs_red_militia_cost_tt':'§Y150步兵装备§!用于训练材料，真实部队在原生招募界面消耗装备与人力。',
        'sof_mrs_red_federation_cost_tt':'§Y50支援装备§!用于联邦行政筹备。',
    }.items():localize(key,value)
    text=['l_simp_chinese:']
    for key,value in sorted(LOC.items()):
        escaped=value.replace('\\','\\\\').replace('"','\\"').replace('\n','\\n')
        text.append(f' {key}:0 "{escaped}"')
    put('localisation/simp_chinese/replace/sof_mrs_red_l_simp_chinese.yml','\n'.join(text),bom=True)


def extend_manufacturers():
    # Keep all 4.3 organizations and their values; add the red-route industrial
    # milestones to Marseille's existing alternative unlock conditions.
    from build_regional_manufacturers import render, OUTPUTS
    path=ROOT/'design/regional-manufacturers.json'
    backup=PASS/'before-repository/regional-manufacturers.json'
    if not backup.exists():backup.write_bytes(path.read_bytes())
    design=json.loads(path.read_text(encoding='utf-8'))
    head=render(design)
    clean=deepcopy(design)
    clean_mrs=next(r for r in clean['manufacturers'] if r['tag']=='MRS')
    for field,code in [('unlock','E7'),('specialize','E9'),('capstone','E12')]:
        if fid(code) in clean_mrs[field]:
            at=clean_mrs[field].index(fid(code));clean_mrs[field].pop(at);clean_mrs[field+'_names'].pop(at)
    clean_head=render(clean)
    names={n['code']:n['name'] for n in read_design()}
    mrs=next(r for r in design['manufacturers'] if r['tag']=='MRS')
    for field,code in [('unlock','E7'),('specialize','E9'),('capstone','E12')]:
        if fid(code) not in mrs[field]:
            mrs[field].append(fid(code));mrs[field+'_names'].append(names[code])
    save_json(path,design)
    for kind,text in render(design).items():
        relative=OUTPUTS[kind]
        if relative.startswith('mod/'):
            head_bytes=(head[kind].rstrip()+'\n').encode('utf-8-sig' if kind=='loc' else 'utf-8')
            clean_bytes=(clean_head[kind].rstrip()+'\n').encode('utf-8-sig' if kind=='loc' else 'utf-8')
            if (ROOT/relative).read_bytes()==clean_bytes:head_bytes=clean_bytes
            put(relative[4:],text,bom=kind=='loc',expected_current=head_bytes)
        else:(ROOT/relative).write_text(text,encoding='utf-8')


def publish_metadata():
    descriptor=baseline('descriptor.mod')
    descriptor=re.sub(r'(?m)^version=.*$',f'version="{VERSION}"',descriptor)
    put('descriptor.mod',descriptor)
    old_version=ROOT/'VERSION'
    before=PASS/'before-repository/VERSION'
    if not before.exists():before.parent.mkdir(parents=True,exist_ok=True);before.write_bytes(old_version.read_bytes())
    assert old_version.read_text().strip() in ['4.3.0','4.3.1','4.3.2',VERSION]
    old_version.write_text(VERSION+'\n',encoding='utf-8')
    changelog=ROOT/'CHANGELOG.md'
    original=PASS/'before-repository/CHANGELOG.md'
    if not original.exists():original.write_bytes(changelog.read_bytes())
    old=changelog.read_text(encoding='utf-8-sig')
    addition='''## 4.3.3候选 · 2026-10-06

- 马赛增加红色马赛专属树：52项新国策，中央与工会组织、五年计划方向、军队建设及外交互斥选择。
- 153项通用国策抽为共享定义，原有ID、剧本完成状态、历史人物与其他国家的通用树保留；马赛公共节点移至专属分支右侧。
- 增加党内矛盾、90日危机警告、付费政治协调、140日军事整编、365日计划验收和180日重建。
- 外交提案由目标明确接受或拒绝；联邦并入使用原有占领登记，不增加新核心。铁路建设检查路径上每个州的真实所有权与控制权。
- 新路线接管后，同用途旧经济军事精神和意识形态奖励停止重复发放；所有新国策使用独立的一次性领取记录。
- 静态与引擎验收结果分别记录，未完成游戏内验收的效果不作为已验证玩法发布。

'''
    if '## 4.3.3候选 · 2026-10-06' not in old:
        changelog.write_text(old.replace('# 版本记录\n\n','# 版本记录\n\n'+addition,1),encoding='utf-8')


def build():
    PASS.mkdir(parents=True,exist_ok=True)
    design=read_design()
    public_ids,_=public_focuses()
    from marseille_focus_art import export
    export(put)
    make_focuses(design,public_ids)
    make_ideas();make_triggers()
    blocked=legacy_guards()
    make_effects(blocked);make_decisions();make_events();make_owned_railways()
    make_localization_and_flags();extend_manufacturers();publish_metadata()
    manifest={rel:dict(after_sha256=digest,before_sha256=sha((PASS/'before-source'/rel).read_bytes()) if (PASS/'before-source'/rel).exists() else None) for rel,digest in OUTPUT.items()}
    save_json(PASS/'source-manifest.json',dict(version=VERSION,files=manifest,game_engine_verified=False))
    with zipfile.ZipFile(PASS/'before-source.zip','w',zipfile.ZIP_DEFLATED) as z:
        for path in (PASS/'before-source').rglob('*'):
            if path.is_file():z.write(path,path.relative_to(PASS/'before-source').as_posix())
    print(json.dumps(dict(ok=True,version=VERSION,new_focuses=52,shared_focuses=153,shared_roots=len(public_ids),changed_files=len(OUTPUT),work=str(PASS)),ensure_ascii=False))


def build_art():
    """Update artwork alone while another chat is editing tree navigation."""
    from marseille_focus_art import export
    export(put)
    path=MOD/'common/national_focus/sof_mrs_red.txt'
    text=path.read_text(encoding='utf-8');tree=one(parse(text),'focus_tree')
    nodes=entries(tree.value,'focus');assert len(nodes)==52
    changes=[]
    for node in nodes:
        ident=scalar(node.value,'id');assert ident.startswith(PREFIX)
        icon=one(node.value,'icon');sprite='GFX_sof_mrs_red_'+ident.removeprefix(PREFIX).lower()
        changes.append((icon.start,icon.end,'icon = '+sprite))
    updated=replace(text,changes)
    put('common/national_focus/sof_mrs_red.txt',updated,expected_current=path.read_bytes())
    manifest=json.loads((PASS/'source-manifest.json').read_text(encoding='utf-8'))
    for rel,digest in OUTPUT.items():
        manifest['files'][rel]=dict(after_sha256=digest,before_sha256=sha((PASS/'before-source'/rel).read_bytes()) if (PASS/'before-source'/rel).exists() else None)
    save_json(PASS/'source-manifest.json',manifest)
    print(json.dumps(dict(ok=True,new_icons=52,changed_files=len(OUTPUT),scope='Marseille icons only')))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--art-only',action='store_true');args=parser.parse_args()
    build_art() if args.art_only else build()
