"""Author a Brittany tree inspired by USA, with a paid, expiring council coalition.

Only Brittany blocks in shared files are patched. Frozen source/live inputs are
retained separately; this builder never writes the installed game directory.
"""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil

from hoi4_script import entries, one, parse, replace, scalar, walk

ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / 'mod'
REF = ROOT / 'references/brittany-before-20261006'
GAME = Path(os.environ.get('HOI4_GAME_DIR', 'D:/steam/steamapps/common/Hearts of Iron IV'))
REPORT = ROOT / 'docs/reports/brittany'
PREFIX = 'SOF_BRT_'
STATES = [146,154,160,162,165,167,168,179,184,186,188,195,198,200,207,208,250]
DELEGATES = [
    ('chateau','弗朗索瓦·沙托',20,'市政工程与透明预算',25,'municipal'),
    ('lemaistre','让·勒梅斯特',15,'收支审计与地方自治',25,'fiscal'),
    ('bahon','卡尔·巴翁',15,'劳工保障与技术教育',30,'labour'),
    ('legorgeu','维克托·勒戈尔热',20,'港口投资与共和制度',35,'ports'),
    ('tremintin','皮埃尔·特雷曼坦',15,'市镇自治与地方教育',25,'schools'),
    ('prigent','弗朗索瓦·唐吉－普里让',15,'农业合作与农村救济',30,'rural'),
]

# code | title | USA donor suffix | x,y | prerequisite groups (AND; OR '/')
# Reward and gate strings are authored separately below, never inherited blindly.
DATA = '''
P0|召集布列塔尼地方议会|continue_the_new_deal|14,0|
P1|组建议事局|build_the_pentagon|14,1|P0
P2|议会责任内阁|guarantee_the_american_dream|14,3|P1
P3|沙托的市政方案|wpa|6,2|P1
P4|勒梅斯特财政委员会|income_tax_reform|10,2|P1
P5|巴翁的劳工听证|union_representation_act|18,2|P1
P6|勒戈尔热港务委员会|maritime_commission|24,2|P1
P7|特雷曼坦地方教育案|federal_housing_act|2,2|P1
P8|唐吉－普里让农业听证|agricultural_adjustment_act|22,3|P1
P9|地方语言与公民教育|full_desegregation|2,4|P7
P10|公布财政账目|accumulated_wealth_tax_act|10,4|P4
P11|市镇自治章程|liberty_for_the_philippines|6,4|P3;P7
P12|市政共和联盟|reestablish_the_gold_standard|10,5|P2
P13|工农合作内阁|democratic_socialism|14,5|P2
P14|自治保守联盟|america_first|18,5|P2
P15|公共建设法|wpa|6,6|P10;P11
P16|劳动保障法|fair_labour_standards_act|22,5|P5
P17|农村信用法|agricultural_adjustment_act|26,5|P8
P18|海港投资法|maritime_commission|30,5|P6
P19|退役军人救济|adjusted_compensation_act|22,7|P16
P20|跨党派常设委员会|worker_management_act|14,7|P12/P13/P14
P21|议会质询制度|voter_registration_act|12,8|P20
P22|公开公职考试|office_of_scientific_research_and_development|8,8|P10;P15
P23|普遍市民权|desegregate_the_armed_forces|2,7|P9;P11
P24|地方契约制度|labour_management_relations_act|16,8|P20
P25|布列塔尼共同体章程|reintegration|14,10|P21;P24;P23
E0|地方公共建设署|wpa|34,0|P0
E1|继续地方新政|continue_the_new_deal|32,2|E0
E2|平衡预算与地方信用|reestablish_the_gold_standard|36,2|E0
E3|农业合作与粮食储运|agricultural_adjustment_act|30,4|E1/E2;P17
E4|渔业与罐头工坊|national_employment_strategy|34,4|E1/E2
E5|内陆道路整修|USACE_projects|38,4|E1/E2;P15
E6|乡村电力合作社|privatize_the_TVA|30,6|E3;P15
E7|市镇住房工程|federal_housing_act|34,6|E4;P15
E8|机械工场联合采购|national_prosperity_program|38,6|E5
E9|雷恩技术教育联合会|office_of_scientific_research_and_development|30,8|E6;P9
E10|布列塔尼科学协会|institute_of_american_sciences|34,9|E9;P22
E11|地方军需订单|military_construction|38,8|E8;I6/I7
E12|共同体生产标准|wartime_industry|38,10|E11
E13|战时工业委员会|wartime_industry|34,11|E12;I9
I0|中立政策听证|neutrality_act|44,0|P0
I1|布列塔尼中立法案|neutrality_act|42,2|I0
I2|有限介入法案|limited_intervention|46,2|I0
I3|本土优先与非军事贸易|protectionist_tariffs|42,4|I1
I4|警戒半岛外的战争|war_propaganda|46,4|I2
I5|跨党派援助法案|lend_lease_act|48,6|I2;P20
I6|自治的军械库|arsenal_of_democracy|42,6|I3;P15
I7|共和制度的军械库|arsenal_of_democracy|46,7|I4;P15
I8|修订中立法|the_giant_wakes|42,8|I6;P20
I9|半岛的觉醒|the_giant_wakes|44,10|I8/I7
I10|议会战争授权|war_powers_act|44,12|I9;P21
I11|战后恢复文官预算|department_of_defense|44,14|I10;E13
D0|西部邻邦联络处|war_plans_division|52,0|P0
D1|南特商贸协商|intervention_in_the_americas|50,2|D0
D2|诺曼底海运协商|intervention_in_europe|54,2|D0
D3|半岛市镇互助|reinforce_monroe_doctrine|50,4|D1
D4|西部防卫协约|hemisphere_defense|54,5|D2;I9
D5|共同安全而非强制兼并|global_hegemony|52,7|D3;D4;P25
M0|地方防务部|war_department|60,0|P0
M1|登记地方预备役|selective_training_act|58,2|M0
M2|半岛联合演习|louisiana_maneuvers|60,4|M1
M3|军士与参谋学校|build_the_pentagon|62,2|M0
M4|机枪与炮兵标准|support_rock_island|62,4|M3
M5|布列塔尼防卫军|army_of_the_united_states|58,6|M2;I6/I7
M6|交通与野战补给|armored_infantry|62,6|M4
M7|妇女军需与医疗服务|womens_armed_service_integration_act|58,8|M5;P16
M8|工兵与沿岸反击|first_special_service_force|62,8|M6
M9|文官统筹军政|department_of_defense|60,10|M7;M8;P21
A0|地方航空规划处|air_war_plans_division|68,0|P0
A1|沿岸侦察与防空|air_support|66,2|A0
A2|战斗机技术合作|escort_fighters|70,2|A0
A3|战术航空支援|TAC|66,4|A1
A4|沿岸对舰航空|CAS|70,4|A2
A5|雷达与无线电|magic|68,6|A3;A4
A6|布列塔尼航空队|us_army_airforce|68,8|A5;I9
N0|海防筹备委员会|two_ocean_navy_act|76,0|P0
N1|沿海运输委员会|maritime_commission|74,2|N0
N2|布雷斯特船厂协作|bureau_of_ships|78,2|N0;P18
N3|沿岸商船修造|liberty_ships|74,4|N1
N4|护航舰艇优先|escort_effort|76,5|N2
N5|洛里昂潜艇工艺|fleet_submarines|80,5|N2
N6|沿岸护航规程|convoy_tactics|76,7|N4
N7|潜航训练与可靠性|unrestricted_submarine_warfare|80,7|N5
N8|共和海军预算|fund_the_navy|78,9|N6;N7;P20
N9|海军陆战勤务|expand_the_USMC|76,11|N8
N10|沿岸登陆演练|amphibious_operations|78,13|N9;I9
'''


def focus_id(code):
    return PREFIX + code


def research(category, bonus=.35):
    return f'add_tech_bonus = {{ name = {category} bonus = {bonus} uses = 1 category = {category} }}'


def idea(key):
    return 'add_ideas = sof_brt_' + key


def build_local(building, state=None):
    """State tests recheck at completion; never place a building on foreign land."""
    gate = f'is_owned_by = ROOT is_fully_controlled_by = ROOT free_building_slots = {{ building = {building} size > 0 include_locked = yes }}'
    if state:
        return f'if = {{ limit = {{ {state} = {{ {gate} }} }} {state} = {{ add_extra_state_shared_building_slots = 1 add_building_construction = {{ type = {building} level = 1 instant_build = yes }} }} }} else = {{ add_political_power = 25 }}'
    region = 'OR = { ' + ' '.join(f'state = {n}' for n in STATES) + ' }'
    return f'if = {{ limit = {{ any_owned_state = {{ {gate} {region} }} }} random_owned_state = {{ limit = {{ {gate} {region} }} add_extra_state_shared_building_slots = 1 add_building_construction = {{ type = {building} level = 1 instant_build = yes }} }} }} else = {{ add_political_power = 25 }}'


def state_gate(number):
    return f'{number} = {{ is_owned_by = ROOT is_fully_controlled_by = ROOT }}'


IDEAS = {
    'isolation_3': ('地方孤立与战争疑虑','稳定的自治生活伴随着对征兵和域外战争的疑虑。遭到攻击时可紧急动员。',dict(stability_factor=.08,conscription=-.005,industrial_capacity_factory=-.08,production_speed_industrial_complex_factor=.05,training_time_army_factor=.10)),
    'isolation_2': ('武装中立','海防与地方军需逐步完善，主动战争仍须经过议会。',dict(stability_factor=.06,conscription=-.003,industrial_capacity_factory=-.04,production_speed_industrial_complex_factor=.05)),
    'isolation_1': ('有限介入','部分限制已解除；全面动员仍需新的表决。',dict(stability_factor=.02,conscription=-.001,industrial_capacity_factory=-.02)),
    'isolation_0': ('议会监督下的动员','动员限制已解除，对外战争仍由战争授权法控制。',dict()),
    'coalition_republic': ('市政共和联盟','透明预算和市镇行政组成执政基础。',dict(political_power_factor=.08,stability_factor=.03)),
    'coalition_social': ('工农合作内阁','以劳工与农业协商稳定执政，保留公共支出。',dict(stability_factor=.04,industrial_capacity_factory=.04,consumer_goods_factor=.02)),
    'coalition_autonomy': ('自治保守联盟','地方教育和自治权换取财政谨慎。',dict(stability_factor=.05,political_power_factor=.05,production_speed_arms_factory_factor=-.05)),
    'new_deal': ('地方公共投资','扩大民用建设，公共支出占用部分消费品。',dict(production_speed_industrial_complex_factor=.12,consumer_goods_factor=.03)),
    'balanced_budget': ('平衡预算','降低消费品负担，但减少公共工程拨款。',dict(consumer_goods_factor=-.03,production_speed_infrastructure_factor=-.08)),
    'civil_rights': ('市镇公民契约','普遍市民权和基层教育。',dict(stability_factor=.03,compliance_gain=.005)),
    'oversight': ('议会监督制度','公开质询与责任内阁限制行政滥用。',dict(political_power_factor=.05,required_garrison_factor=-.05)),
    'production': ('共同体生产标准','有限的军需协调和生产效率。',dict(industrial_capacity_factory=.06,production_factory_max_efficiency_factor=.03)),
    'home_defence': ('半岛防卫军','防卫本土的地方军事制度。',dict(army_core_defence_factor=.08,conscription=.005)),
    'logistics': ('道路与军需统筹','降低野战补给消耗。',dict(supply_consumption_factor=-.05)),
    'escort': ('沿岸护航规程','优先维持商船与沿海交通。',dict(convoy_escort_efficiency=.08)),
    'landing': ('沿岸登陆演练','小规模海陆协同能力。',dict(naval_invasion_plan_cap=1,naval_invasion_division_cap=2)),
    'wartime': ('议会战时工业','战争期间增加军需产出，和平后撤销。',dict(industrial_capacity_factory=.08,production_speed_arms_factory_factor=.10,consumer_goods_factor=.03)),
    'trade': ('市镇贸易协约','180日的非军事商贸合作。',dict(trade_opinion_factor=.10)),
    'aid': ('议会援助授权','有限介入路线经表决解除军事援助的世界紧张度门槛。',dict(lend_lease_tension=-.50)),
    'municipal': ('市政拨款承诺','议会联盟的公共工程代价。',dict(consumer_goods_factor=.01,production_speed_infrastructure_factor=.05)),
    'fiscal': ('财政审计承诺','行政审计暂时消耗政治资源。',dict(political_power_factor=-.05)),
    'labour': ('劳工保障承诺','工时与工资协商需要生产调整。',dict(stability_factor=.03,industrial_capacity_factory=-.03)),
    'ports': ('港务拨款承诺','地方预算支持港务委员会。',dict(consumer_goods_factor=.02,production_speed_dockyard_factor=.08)),
    'schools': ('教育拨款承诺','维持地方教育与公共服务。',dict(consumer_goods_factor=.02,research_speed_factor=.02)),
    'rural': ('农业救济承诺','采购、信用与合作社补助。',dict(consumer_goods_factor=.02,stability_factor=.02)),
}

REWARDS = {
    'P0':'set_country_flag = sofzh_unification_started add_political_power = 35',
    'P1':'add_political_power = 25',
    'P2':'add_country_leader_role = { character = REN_francois_chateau promote_leader = yes country_leader = { ideology = liberalism expire = "1965.1.1.1" } } set_politics = { ruling_party = democratic elections_allowed = yes }',
    'P9':'add_stability = .02', 'P10':'add_political_power = 35',
    'P11':'add_stability = .02',
    'P12':idea('coalition_republic')+' promote_character = REN_francois_chateau',
    'P13':idea('coalition_social')+' promote_character = REN_carle_bahon',
    'P14':idea('coalition_autonomy')+' promote_character = REN_jean_lemaistre',
    'P15':'add_political_power = 25', 'P16':'add_stability = .025',
    'P17':'add_stability = .025', 'P18':'add_navy_experience = 10',
    'P19':'add_stability = .02', 'P20':'add_political_power = 40',
    'P21':idea('oversight'),'P22':research('industry',.3),
    'P23':idea('civil_rights'),'P24':'add_political_power = 30','P25':'add_stability = .04',
    'E0':'add_political_power = 20','E1':idea('new_deal'),'E2':idea('balanced_budget'),
    'E3':build_local('industrial_complex'),'E4':build_local('industrial_complex'),
    'E5':'sof_brt_local_roads = yes','E6':research('industry'),
    'E7':build_local('industrial_complex'),'E8':research('industry'),
    'E9':'if = { limit = { amount_research_slots < 3 num_of_factories > 5 } add_research_slot = 1 }',
    'E10':'if = { limit = { amount_research_slots < 4 num_of_factories > 11 } add_research_slot = 1 }',
    'E11':build_local('arms_factory'),'E12':idea('production'),'E13':idea('wartime'),
    'I0':'add_political_power = 20','I1':'add_stability = .025',
    'I2':'sof_brt_set_stage_2 = yes add_war_support = .03',
    'I3':'add_stability = .02','I4':'add_war_support = .04',
    'I5':'set_country_flag = sof_brt_aid_law '+idea('aid'),
    'I6':'sof_brt_set_stage_2 = yes '+build_local('arms_factory'),
    'I7':'sof_brt_set_stage_1 = yes '+build_local('arms_factory'),
    'I8':'sof_brt_set_stage_1 = yes','I9':'sof_brt_set_stage_0 = yes add_war_support = .05',
    'I10':'set_country_flag = sof_brt_war_authorized sof_brt_sync = yes',
    'I11':'remove_ideas = sof_brt_wartime add_stability = .03',
    'D0':'add_political_power = 20','D1':'add_political_power = 15','D2':'add_navy_experience = 10',
    'D3':'add_stability = .02','D4':'set_rule = { can_create_factions = yes }',
    'D5':'add_stability = .02',
    'M0':'add_army_experience = 10','M1':'add_army_experience = 10',
    'M2':'add_army_experience = 20','M3':research('support_tech'),
    'M4':research('artillery'),'M5':idea('home_defence'),'M6':idea('logistics'),
    'M7':'add_army_experience = 15','M8':research('engineers_tech'),'M9':'add_army_experience = 25',
    'A0':'add_air_experience = 10','A1':research('light_air'),'A2':research('light_air'),
    'A3':research('medium_air'),'A4':research('naval_bomber'),'A5':research('electronics'),
    'A6':'add_air_experience = 25',
    'N0':'add_navy_experience = 10','N1':'add_political_power = 20',
    'N2':build_local('dockyard',168),'N3':'add_equipment_to_stockpile = { type = convoy amount = 12 }',
    'N4':research('dd_tech'),'N5':build_local('dockyard',208)+' '+research('ss_tech'),
    'N6':idea('escort'),'N7':research('ss_tech'),'N8':build_local('dockyard',168),
    'N9':research('marine_tech'),'N10':idea('landing'),
}
GATES = {code:'sof_brt_majority = yes' for code in ['P2','P11','P12','P13','P14','P20','P25','E1','E2','E6','E7','N8']}
GATES.update({
    'P12':'sof_brt_majority = yes has_country_flag = sof_brt_pledge_chateau has_country_flag = sof_brt_pledge_lemaistre',
    'P13':'sof_brt_majority = yes has_country_flag = sof_brt_pledge_bahon has_country_flag = sof_brt_pledge_prigent',
    'P14':'sof_brt_majority = yes has_country_flag = sof_brt_pledge_lemaistre has_country_flag = sof_brt_pledge_tremintin',
    'P15':'has_country_flag = sof_brt_law_budget','P16':'has_country_flag = sof_brt_law_social',
    'P17':'has_country_flag = sof_brt_law_rural','P18':'has_country_flag = sof_brt_law_ports',
    'E9':'amount_research_slots < 3 num_of_factories > 5',
    'E10':'amount_research_slots < 4 num_of_factories > 11',
    'E13':'has_war = yes','I2':'sof_brt_majority = yes',
    'I5':'sof_brt_majority = yes has_country_flag = sof_brt_law_aid',
    'I8':'has_country_flag = sof_brt_law_revision',
    'I9':'has_country_flag = sof_brt_law_mobilization',
    'I10':'has_country_flag = sof_brt_law_war',
    'I11':'has_war = no','D4':'sof_brt_supermajority = yes',
    'N2':state_gate(168),'N5':state_gate(208),
    'N8':'sof_brt_majority = yes '+state_gate(168),
    'N3':'sof_brt_owned_coast = yes','N9':'sof_brt_owned_coast = yes',
    'N10':'sof_brt_owned_coast = yes',
})
EXCLUSIVE = {'P12':['P13','P14'],'P13':['P12','P14'],'P14':['P12','P13'],
             'E1':['E2'],'E2':['E1'],'I1':['I2'],'I2':['I1']}


def write(relative,text):
    path = MOD / relative
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(text,encoding='utf-8-sig' if path.suffix=='.yml' else 'utf-8',newline='\n')


def authored_nodes():
    nodes=[]
    from brittany_military import DATA as MILITARY_DATA, decorate
    for row in (DATA.strip()+'\n'+MILITARY_DATA.strip()).splitlines():
        code,title,donor,xy,pre=row.split('|')
        x,y=map(int,xy.split(','))
        if code in ['E0','I0','D0','M0','A0','N0']:y=1
        nodes.append(dict(code=code,id=focus_id(code),name=title,donor='USA_'+donor,x=x,y=y,
                          prerequisites=[group.split('/') for group in pre.split(';') if group],
                          exclusive=EXCLUSIVE.get(code,[]),days=35 if code in ['P0','P1','I0','D0','M0','A0','N0','E0'] else 70))
    decorate(nodes)
    bycode={n['code']:n for n in nodes}
    for _ in range(len(nodes)):
        changed=False
        for n in nodes:
            earlier=[bycode[c]['y']+1 for group in n['prerequisites'] for c in group]
            y=max([n['y']]+earlier)
            if y!=n['y']:n['y']=y;changed=True
        if not changed:break
    else:raise AssertionError('Prerequisite cycle in authored graph')
    assert len({(n['x'],n['y']) for n in nodes})==len(nodes),'Layout collision'
    return nodes


def build():
    nodes=authored_nodes()
    donor_path=REF/'usa.txt'
    if not donor_path.exists():donor_path=GAME/'common/national_focus/usa.txt'
    native_text=donor_path.read_text(encoding='utf-8-sig')
    donor_tree=one(parse(native_text),'focus_tree').value
    donor={scalar(n.value,'id'):n.value for n in entries(donor_tree,'focus')}
    native_gfx={}
    for p in list((GAME/'interface').glob('*.gfx'))+list((GAME/'dlc').glob('*/interface/*.gfx')):
        try: roots=parse(p.read_text(encoding='utf-8-sig'))
        except (UnicodeError,AssertionError):continue
        for group in entries(roots,'spriteTypes'):
            for n in group.value:
                if isinstance(n.value,list) and scalar(n.value,'name'):
                    native_gfx[scalar(n.value,'name').strip('"')]=n.value
    loc={};gfx=['spriteTypes = {'];copied=set();texture_rows=[]
    from brittany_military import military_icons
    local_icons,local_gfx,local_art=military_icons(MOD,nodes)
    gfx+=local_gfx;texture_rows+=local_art
    def localize(key,value):loc[key]=value
    def copy_icon(sprite):
        if sprite in copied:return 'GFX_sof_brt_'+sprite.removeprefix('GFX_')
        source=native_gfx[sprite];texture=scalar(source,'texturefile').strip('"')
        src=GAME/texture
        if not src.exists():
            matches=list((GAME/'dlc').glob('*/'+texture));assert matches,texture;src=matches[0]
        dest='gfx/interface/sof_brt/'+src.name
        target=MOD/dest;target.parent.mkdir(parents=True,exist_ok=True)
        if target.exists():assert target.read_bytes()==src.read_bytes(),dest
        else:shutil.copyfile(src,target)
        name='GFX_sof_brt_'+sprite.removeprefix('GFX_')
        gfx.append(f'spriteType = {{ name = "{name}" texturefile = "{dest}" noOfFrames = {scalar(source,"noOfFrames","1")} }}')
        copied.add(sprite);texture_rows.append(dict(path=dest,source=str(src),sha256=hashlib.sha256(target.read_bytes()).hexdigest()))
        return name
    tree=['focus_tree = { id = sof_brittany country = { factor = 0 modifier = { add = 100 original_tag = REN } } default = no reset_on_civilwar = no',
          'initial_show_position = { focus = SOF_BRT_P0 } continuous_focus_position = { x = 50 y = 2200 }']
    for code in ['P0','E0','I0','D0','M0','A0','N0','B0','F0','O0']:
        key='sof_brt_shortcut_'+code;localize(key,dict(P0='地方议会',E0='公共建设',I0='中立与动员',D0='西部协商',M0='地方陆军',A0='沿岸航空',N0='海防与船厂',B0='三军共同准备',F0='孤立防御',O0='积极进攻')[code])
        tree.append(f'shortcut = {{ name = {key} target = {focus_id(code)} scroll_wheel_factor = .65 }}')
    for n in nodes:
        code=n['code'];icon=local_icons[code] if code in local_icons else copy_icon(scalar(donor[n['donor']],'icon'));n['icon']=icon
        reward=REWARDS.get(code,'add_political_power = 15')
        # National-focus completion is already one-shot; independent receipt guards
        # also prevent manually switched old trees from duplicating factory grants.
        grant='sof_brt_grant_'+code.lower()
        gate='is_subject = no has_capitulated = no '+GATES.get(code,'')
        body=[f'focus = {{ id = {n["id"]} icon = {icon} x = {n["x"]} y = {n["y"]} cost = {n["days"]/7:g}',
              'search_filters = { '+('FOCUS_FILTER_POLITICAL' if code[0] in 'PID' else 'FOCUS_FILTER_INDUSTRY' if code[0]=='E' else 'FOCUS_FILTER_ARMY_XP' if code[0] in 'MBFO' else 'FOCUS_FILTER_AIR_XP' if code[0]=='A' else 'FOCUS_FILTER_NAVY_XP')+' }']
        body += ['prerequisite = { '+' '.join('focus = '+focus_id(p) for p in group)+' }' for group in n['prerequisites']]
        if n['exclusive']:body.append('mutually_exclusive = { '+' '.join('focus = '+focus_id(p) for p in n['exclusive'])+' }')
        body += [f'available = {{ {gate} }} cancel_if_invalid = yes continue_if_invalid = no',
                 f'completion_reward = {{ if = {{ limit = {{ NOT = {{ has_country_flag = {grant} }} }} {reward} set_country_flag = {grant} }} }}',
                 'ai_will_do = { factor = '+('12' if code[0]=='P' else '6' if code[0]=='E' else '3')+' } }']
        tree.extend(body);localize(n['id'],n['name'])
        desc=DESCRIPTIONS.get(code,f'{n["name"]}须在地方议会和责任内阁的框架下实施。根据地方财力分配有限的人力、科研与军需资源。')
        localize(n['id']+'_desc',desc)
    tree.append('}');write('common/national_focus/sof_brittany.txt','\n'.join(tree)+'\n')
    # Four restrictions are mutually exclusive and refreshed from one stage.
    ideas=['ideas = { country = {']
    for key,(title,desc,mods) in IDEAS.items():
        from brittany_art import spirit_picture
        picture=spirit_picture(key)
        rules='rule = { can_join_factions = no can_create_factions = no can_not_declare_war = yes }' if key in ['isolation_3','isolation_2','isolation_1'] else ''
        cancel='cancel = { has_war = no }' if key=='wartime' else ''
        ideas.append(f'sof_brt_{key} = {{ allowed = {{ always = no }} allowed_civil_war = {{ always = no }} removal_cost = -1 picture = {picture} {rules} {cancel} modifier = {{ '+ ' '.join(f'{k} = {v:g}' for k,v in mods.items())+' } }')
        localize('sof_brt_'+key,title);localize('sof_brt_'+key+'_desc',desc)
    ideas.append('} }');write('common/ideas/sof_brittany.txt','\n'.join(ideas)+'\n')
    triggers='''sof_brt_active = { original_tag = REN has_focus_tree = sof_brittany }
sof_brt_majority = { check_variable = { sof_brt_support > 50 } }
sof_brt_supermajority = { check_variable = { sof_brt_support > 65 } }
sof_brt_owned_coast = { any_owned_state = { is_fully_controlled_by = ROOT is_coastal = yes OR = { STATES } } }
sof_brt_external_threat = { OR = { has_war = yes any_neighbor_country = { OR = { has_war = yes has_wargoal_against = ROOT } } } }
sof_brt_expansion_allowed = { OR = { NOT = { original_tag = REN } AND = { has_country_flag = sof_brt_war_authorized check_variable = { sof_brt_isolation = 0 } } } }
'''.replace('STATES',' '.join('state = '+str(n) for n in STATES))
    from brittany_council_expansion import home_triggers
    write('common/scripted_triggers/sof_brittany.txt',triggers+home_triggers())
    effects=make_effects()
    write('common/scripted_effects/sof_brittany.txt',effects)
    write('common/on_actions/zz_sof_brittany.txt','''on_actions = {
on_startup = { effect = { every_country = { limit = { original_tag = REN } sof_brt_initialize = yes sof_brt_sync = yes } } }
on_daily_REN = { effect = { if = { limit = { original_tag = REN } sof_brt_initialize = yes sof_brt_sync = yes } } }
on_war = { effect = { if = { limit = { original_tag = REN } sof_brt_sync = yes } } }
}
''')
    decisions,extra=make_decisions();loc.update(extra)
    write('common/decisions/sof_brittany.txt',decisions)
    write('common/decisions/categories/sof_brittany.txt','''sof_brt_council = { icon = sof_cw_civil scripted_gui = sof_brt_council_gui visible_when_empty = yes priority = 90 visible = { sof_brt_active = yes } }
sof_brt_diplomacy = { icon = sof_cw_pact visible = { sof_brt_active = yes has_completed_focus = SOF_BRT_D0 } }
''')
    events,eventloc=make_events();loc.update(eventloc);write('events/sof_brittany.txt',events)
    localize('sof_brt_council','布列塔尼地方议会')
    localize('sof_brt_council_desc','议会支持：§Y[?sof_brt_support|0]/100席§!\\n普通法案须51席，修订中立与动员须66席，对外战争须75席。议员承诺通常持续180日，法案审议45日，表决结束重新核验支持。每项法案同时只能审议一次；支出承诺有实际代价。\\n六位人物取自1930年代地方政治；100席、党团规模与本议会为架空制度。')
    localize('sof_brt_diplomacy','西部市镇协商')
    localize('sof_brt_support_change_tt','重计仍有效的议员支持；同一议员重复协商不会累加席位。')
    localize('sof_brt_vote_fail_tt','法案未获通过：条件不足或审议被取消，退回10政治点；没有授予法案效果。')
    gfx.append('}');write('interface/sof_brittany.gfx','\n'.join(gfx)+'\n')
    write('localisation/simp_chinese/replace/sof_brittany_l_simp_chinese.yml','l_simp_chinese:\n'+'\n'.join(f' {k}:0 "{v.replace(chr(34),chr(39))}"' for k,v in loc.items())+'\n')
    from build_brittany_gui import build_gui
    ui=build_gui(MOD,ROOT,DELEGATES,BILLS)
    from brittany_council_expansion import author_pool, POOL
    pool_files=author_pool(MOD,ROOT,DELEGATES)
    from brittany_art import build_art
    art_files=build_art(MOD,ROOT)
    shared=patch_shared()
    files=[p.relative_to(MOD).as_posix() for folder in ['common/national_focus','common/ideas','common/scripted_effects','common/scripted_triggers','common/on_actions','common/decisions','common/decisions/categories','common/scripted_guis','common/scripted_localisation','events','interface','localisation/simp_chinese/replace'] for p in (MOD/folder).glob('*brittany*')]
    files+=sorted({r['path'] for r in texture_rows})+shared
    files+=ui['files']
    files+=pool_files
    files+=art_files
    spec=dict(format=1,tag='REN',tree='sof_brittany',donor_nodes=135,nodes=nodes,delegates=[dict(key=k,name=n,seats=s,demand=d,cost=c) for k,n,s,d,c,_ in DELEGATES],
              source_usa_sha256=hashlib.sha256(donor_path.read_bytes()).hexdigest(),sources=SOURCES+[dict(topic=p['name'],url=p['source']) for p in POOL],files=sorted(set(files)),art=texture_rows,gui=ui,reserves=POOL,game_engine_verified=False)
    (ROOT/'design/brittany-focus.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    REPORT.mkdir(parents=True,exist_ok=True)
    print(json.dumps(dict(ok=True,focuses=len(nodes),delegates=len(DELEGATES),runtime_files=len(spec['files']),icons=len(copied)),ensure_ascii=False))


DESCRIPTIONS = {
 'P0':'法国的分裂使雷恩必须建立自己的责任政治。布列塔尼既有地方自治传统，也有共和派、社会主义者和天主教民主派的分歧。召集地方政治代表，通过公开协商而非盲目动员维持半岛安全。',
 'P2':'普通多数决定责任内阁。至少51席支持才能组成政府，财政、军需与战争事务均接受议会监督。',
 'P3':'沙托在1935年成为雷恩市长。市政工程和透明预算是争取其地方支持的重点。国策开启议题，具体支持仍需付费协商。',
 'P4':'前雷恩市长勒梅斯特主持审计与收支讨论。议会支持不会自动变成免费工程。',
 'P5':'前雷恩市长巴翁代表社会主义市政传统。劳工保障与技术教育需要预算，也会暂时影响生产。',
 'P6':'布雷斯特市长、参议员勒戈尔热重视共和国与公共服务。港务承诺可以换取支持，船厂工程仍须拥有并完全控制当地。',
 'P7':'特雷曼坦是天主教民主派地方议员与市长。将市镇自治、地方教育和共和制度纳入协商。',
 'P8':'唐吉－普里让在1935年已任市长，1936年5月进入法国众议院。他的农业合作与农村保障诉求将进入地方议会。',
 'P12':'取得沙托与勒梅斯特的有效承诺，并形成51席多数。行政效率提升，内阁仍须重新争取法案票数。',
 'P13':'取得巴翁与唐吉－普里让的有效承诺，并形成51席多数。公共保障促进生产，但增加财政支出。',
 'P14':'取得勒梅斯特与特雷曼坦的有效承诺，并形成51席多数。地方自治与教育优先，对军用建设保持谨慎。',
 'P15':'先通过45日公共预算审议。开始与结束审议均须51席；若承诺失效，法案不能通过。',
 'P16':'工时与工资保障必须先完成劳工法案表决。议员对政策的支持附带真实公共支出。',
 'P17':'农村合作社与地方信用由农业法案授权。补助不能替代缺乏的交通与工场。',
 'P18':'港务法案授权建设资金，船厂国策另需实际控制布雷斯特或洛里昂。',
 'E1':'借鉴美国公共工程方案，以消费品支出换取较快的民用建设。与平衡预算保持真实取舍。',
 'E2':'减少公共支出，换取更低消费品负担；基础设施建设速度下降。',
 'E3':'建设一家食品储运与农业加工工场，仅限拥有并完全控制的布列塔尼州；没有容量时补偿25政治点。',
 'E5':'仅整修拥有并完全控制的本地道路，最多两个州各增加一级基础设施。',
 'E9':'六家工厂支撑第三个科研槽。不能提前完成后等待免费解锁。',
 'E10':'十二家工厂支撑第四个科研槽。科学协会以地方技术教育为基础。',
 'I1':'选择本土优先的中立路线，保留稳定与建设优势。中立并不妨碍自卫，但不能绕过议会主动扩张。',
 'I2':'51席同意有限介入。征兵和生产限制略有缓解，正式军事援助与全面动员需要另外立法。',
 'I5':'援助法案须51席与外部威胁，结束45日审议时复核；只向愿意接受的西部伙伴提供有限协作。',
 'I8':'66席同意修订中立法，外部战争或邻邦战争目标构成威胁依据。无法靠游说独自解除全部限制。',
 'I9':'全面动员须66席、外部威胁和至少35%战争支持；战争中可先紧急自卫，但不能获得主动扩张权。',
 'I10':'对外战争授权须75席与外部威胁。国策才授予原有边境战役权限；地区核心仍按占领整合制度处理。',
 'D4':'与愿意接受的西部伙伴建立防卫合作。需要66席支持，邀请由对方独立决定。',
 'N2':'布雷斯特实际拥有并完全控制后，扩建一个船坞并解锁本地潜艇制造商。',
 'N5':'实际拥有并完全控制洛里昂，扩建一个船坞并研究潜航工艺。',
 'N8':'经议会多数批准，继续为布雷斯特增加一个船坞；不追求美国式的全球大舰队。',
}


SOURCES = [
 dict(topic='美国国策结构',url='local:references/brittany-before-20261006/usa.txt'),
 dict(topic='沙托市长任期',url='https://cimetieres.rennes.fr/accueil/patrimoine/cimetieres_rennais/21_31/francois_chateau'),
 dict(topic='勒戈尔热',url='https://www.senat.fr/connaitre-le-senat/lhistoire-du-senat/dossiers-dhistoire/le-senat-a-la-fin-de-la-seconde-guerre-mondiale/victor-le-gorgeu-1881-1963.html'),
 dict(topic='特雷曼坦',url='https://www2.assemblee-nationale.fr/sycomore/fiche/7144'),
 dict(topic='巴翁与勒梅斯特的市长任期',url='https://archives-rennes.fr/media/pdf/Liste_maires_rennes.pdf'),
 dict(topic='唐吉普里让',url='https://www2.assemblee-nationale.fr/sycomore/bio?num_dept=6948'),
 dict(topic='两战间地方经济',url='https://www.bretagne.bzh/app/uploads/quels_modes_de_dvpt_pr_la_Bretagne.pdf'),
 dict(topic='旧制度议会与司法传统',url='https://patrimoine.bzh/gertrude-diffusion/dossier/IA22132633'),
]


def make_effects():
    effects=[]
    for stage in range(4):
        effects.append(f'sof_brt_set_stage_{stage} = {{ set_variable = {{ sof_brt_isolation = {stage} }} sof_brt_sync = yes }}')
    effects.append('sof_brt_count_support = { set_variable = { sof_brt_support = 0 }')
    for key,_,seats,_,_,_ in DELEGATES:
        effects.append(f'if = {{ limit = {{ has_country_flag = sof_brt_pledge_{key} }} add_to_variable = {{ sof_brt_support = {seats} }} set_variable = {{ sof_brt_ui_{key} = 2 }} }} else = {{ set_variable = {{ sof_brt_ui_{key} = 1 }} }}')
    effects.append('clamp_variable = { var = sof_brt_support min = 0 max = 100 } }')
    for key,_,_,_,cost,contract in DELEGATES:
        milestone=dict(chateau='P3',lemaistre='P4',bahon='P5',legorgeu='P6',tremintin='P7',prigent='P8')[key]
        gate=f'sof_brt_active = yes is_subject = no has_capitulated = no has_completed_focus = {focus_id(milestone)} NOT = {{ has_country_flag = sof_brt_pledge_{key} }} NOT = {{ has_country_flag = sof_brt_suspended_{key} }}'
        effects.append(f'sof_brt_pledge_{key}_grant = {{ set_country_flag = {{ flag = sof_brt_pledge_{key} days = 180 }} add_timed_idea = {{ idea = sof_brt_{contract} days = 180 }} sof_brt_count_support = yes }}')
        effects.append(f'sof_brt_gui_lobby_{key} = {{ if = {{ limit = {{ {gate} NOT = {{ has_political_power < {cost} }} }} add_political_power = -{cost} sof_brt_pledge_{key}_grant = yes }} }}')
    effects.append('''sof_brt_initialize = {
if = { limit = { original_tag = REN NOT = { has_country_flag = sof_brt_initialized } }
 if = { limit = { NOT = { has_focus_tree = sof_brittany } } load_focus_tree = { tree = sof_brittany keep_completed = yes } }
 set_country_flag = sof_brt_initialized set_country_flag = sof_van_generic_migrated
 set_variable = { sof_brt_isolation = 3 }
 set_country_flag = { flag = sof_brt_pledge_chateau days = 180 }
 set_country_flag = { flag = sof_brt_pledge_lemaistre days = 180 }
 clr_country_flag = sofzh_unification_war_ready
 }
}
sof_brt_sync = {
if = { limit = { sof_brt_active = yes }
 sof_brt_count_support = yes
 sof_brt_prepare_bench = yes
 sof_brt_home_watch = yes
 sof_brt_committee_sync = yes
 if = { limit = { has_war = yes NOT = { has_country_flag = sof_brt_emergency_active } check_variable = { sof_brt_isolation > 0 } }
  set_variable = { sof_brt_prewar_isolation = sof_brt_isolation }
  set_variable = { sof_brt_isolation = 0 } set_country_flag = sof_brt_emergency_active
 }
 if = { limit = { has_war = no has_country_flag = sof_brt_emergency_active }
  if = { limit = { NOT = { has_completed_focus = SOF_BRT_I9 } } set_variable = { sof_brt_isolation = sof_brt_prewar_isolation } }
  clr_country_flag = sof_brt_emergency_active remove_ideas = sof_brt_wartime
 }
 STAGE_REFRESH
 if = { limit = { has_country_flag = sof_brt_war_authorized check_variable = { sof_brt_isolation = 0 } }
  set_country_flag = sofzh_unification_war_ready
 } else = { clr_country_flag = sofzh_unification_war_ready }
}
}
'''.replace('STAGE_REFRESH','\n'.join(
    f'if = {{ limit = {{ check_variable = {{ sof_brt_isolation = {i} }} }} '+
    ' '.join(f'remove_ideas = sof_brt_isolation_{j}' for j in range(4) if j!=i)+
    f' if = {{ limit = {{ NOT = {{ has_idea = sof_brt_isolation_{i} }} }} add_ideas = sof_brt_isolation_{i} }} }}' for i in range(4))))
    # Roads: at most two local states; no foreign capital fallback.
    effects.append('sof_brt_local_roads = { set_temp_variable = { sof_brt_road_count = 0 } every_owned_state = { limit = { is_fully_controlled_by = ROOT infrastructure < 5 OR = { '+ ' '.join(f'state = {n}' for n in STATES)+' } } if = { limit = { ROOT = { check_variable = { sof_brt_road_count < 2 } } } add_building_construction = { type = infrastructure level = 1 instant_build = yes } ROOT = { add_to_temp_variable = { sof_brt_road_count = 1 } } } } }')
    from brittany_council_expansion import extra_effects
    return '\n'.join(effects)+'\n'+extra_effects(DELEGATES)


# Bill gates are re-evaluated at completion, not captured at the start.
BILLS = {
 'budget':('公共建设预算',51,'has_completed_focus = SOF_BRT_P10 has_completed_focus = SOF_BRT_P11',''),
 'social':('劳工与救济法案',51,'has_completed_focus = SOF_BRT_P5','has_country_flag = sof_brt_pledge_bahon'),
 'rural':('农村合作与信用法案',51,'has_completed_focus = SOF_BRT_P8','has_country_flag = sof_brt_pledge_prigent'),
 'ports':('海港投资法案',51,'has_completed_focus = SOF_BRT_P6','has_country_flag = sof_brt_pledge_legorgeu sof_brt_owned_coast = yes'),
 'aid':('有限军事援助法案',51,'has_completed_focus = SOF_BRT_I2 has_completed_focus = SOF_BRT_P20','sof_brt_external_threat = yes'),
 'revision':('中立法修正案',66,'has_completed_focus = SOF_BRT_I6 has_completed_focus = SOF_BRT_P20','sof_brt_external_threat = yes'),
 'mobilization':('全面动员法案',66,'OR = { has_completed_focus = SOF_BRT_I8 has_completed_focus = SOF_BRT_I7 }','sof_brt_external_threat = yes has_war_support > .349'),
 'war':('对外战争授权法案',75,'has_completed_focus = SOF_BRT_I9 has_completed_focus = SOF_BRT_P21','sof_brt_external_threat = yes'),
}


def make_decisions():
    code=['sof_brt_council = {'];loc={}
    for key,name,seats,demand,cost,contract in DELEGATES:
        decision='sof_brt_negotiate_'+key
        # Listening focus is political access, not a free pledge.
        milestone=dict(chateau='P3',lemaistre='P4',bahon='P5',legorgeu='P6',tremintin='P7',prigent='P8')[key]
        gate=f'sof_brt_active = yes is_subject = no has_capitulated = no has_completed_focus = {focus_id(milestone)} NOT = {{ has_country_flag = sof_brt_pledge_{key} }} NOT = {{ has_country_flag = sof_brt_suspended_{key} }}'
        code.append(f'''{decision} = {{ icon = sof_cw_civil cost = {cost} days_re_enable = 30
visible = {{ has_completed_focus = {focus_id(milestone)} }} available = {{ {gate} }}
complete_effect = {{ sof_brt_pledge_{key}_grant = yes custom_effect_tooltip = sof_brt_support_change_tt }}
ai_will_do = {{ factor = 10 modifier = {{ factor = 0 check_variable = {{ sof_brt_support > 84 }} }} }} }}''')
        loc[decision]=f'与[GetSofBrtName{key}]协商（{seats}席）'
        loc[decision+'_desc']=f'该地方委员会关注{demand}。协商支付{cost}政治点，以180日的公共支出承诺换取{seats}席支持；到期必须重新协商。改任候补后同一议席重新协商；驻地沦陷而未安排流亡代表时无法取得支持。'
    for key,(title,seats,pre,extra) in BILLS.items():
        decision='sof_brt_vote_'+key
        gate=f'sof_brt_active = yes is_subject = no has_capitulated = no check_variable = {{ sof_brt_support > {seats-1} }} {extra}'
        code.append(f'''{decision} = {{ icon = sof_cw_register cost = 30 days_remove = 45 days_re_enable = 45
visible = {{ {pre} NOT = {{ has_country_flag = sof_brt_law_{key} }} }}
available = {{ {gate} NOT = {{ has_country_flag = sof_brt_bill_pending }} }}
complete_effect = {{ set_country_flag = sof_brt_bill_pending set_country_flag = sof_brt_bill_{key} }}
remove_effect = {{ sof_brt_count_support = yes clr_country_flag = sof_brt_bill_pending clr_country_flag = sof_brt_bill_{key}
 if = {{ limit = {{ {gate} }} set_country_flag = sof_brt_law_{key} }} else = {{ add_political_power = 10 custom_effect_tooltip = sof_brt_vote_fail_tt }} }}
cancel_trigger = {{ OR = {{ sof_brt_active = no is_subject = yes has_capitulated = yes }} }}
cancel_effect = {{ clr_country_flag = sof_brt_bill_pending clr_country_flag = sof_brt_bill_{key} add_political_power = 10 custom_effect_tooltip = sof_brt_vote_fail_tt }}
ai_will_do = {{ factor = 8 }} }}''')
        loc[decision]=f'审议：{title}（{seats}席）'
        loc[decision+'_desc']=f'花费30政治点，审议45日。表决开始和结束均须至少{seats}席支持，且相关议员承诺与外部条件仍须成立。未通过或取消退回10政治点。法案授权相应国策；国策奖励只能领取一次。'
    code.append('}');code.append('sof_brt_diplomacy = {')
    for target,milestone in [('NAN','D1'),('ROU','D2'),('BRE','D3'),('LOR','D3'),('SMA','D3')]:
        key='sof_brt_trade_'+target.lower()
        code.append(f'''{key} = {{ icon = sof_cw_pact cost = 25 days_re_enable = 180
visible = {{ has_completed_focus = {focus_id(milestone)} country_exists = {target} }}
available = {{ sof_brt_active = yes has_war = no is_subject = no NOT = {{ has_country_flag = sof_brt_offer_pending }} {target} = {{ has_war = no is_subject = no NOT = {{ has_war_with = ROOT }} NOT = {{ has_country_flag = sof_brt_offer_target_pending }} }} }}
complete_effect = {{ set_country_flag = {{ flag = sof_brt_offer_pending days = 30 }} {target} = {{ set_country_flag = {{ flag = sof_brt_offer_target_pending days = 30 }} country_event = {{ id = sof_brt.1 days = 1 }} }} }} ai_will_do = {{ factor = 2 }} }}''')
        loc[key]=dict(NAN='与南特商贸协商',ROU='与鲁昂海运协商',BRE='与布雷斯特市镇互助',LOR='与洛里昂市镇互助',SMA='与圣马洛市镇互助')[target]
        loc[key+'_desc']='发出180日商贸合作提议，对方可以拒绝。协约不转移领土、船厂或核心。'
    for target in ['NAN','ROU','BRE','LOR','SMA']:
        key='sof_brt_defence_'+target.lower()
        gate=f'sof_brt_active = yes has_completed_focus = SOF_BRT_D4 sof_brt_supermajority = yes is_subject = no NOT = {{ has_country_flag = sof_brt_offer_pending }} check_variable = {{ sof_brt_isolation = 0 }} {target} = {{ is_subject = no is_in_faction = no has_war = no NOT = {{ has_war_with = ROOT }} NOT = {{ has_country_flag = sof_brt_offer_target_pending }} }} OR = {{ is_in_faction = no is_faction_leader = yes }}'
        code.append(f'''{key} = {{ icon = sof_cw_pact cost = 40 days_re_enable = 180
visible = {{ has_completed_focus = SOF_BRT_D4 country_exists = {target} }} available = {{ {gate} }}
complete_effect = {{ set_country_flag = {{ flag = sof_brt_offer_pending days = 30 }} {target} = {{ set_country_flag = {{ flag = sof_brt_offer_target_pending days = 30 }} country_event = {{ id = sof_brt.2 days = 1 }} }} }} ai_will_do = {{ factor = 2 }} }}''')
        loc[key]=f'邀请[{target}.GetName]加入西部防卫协约'
        loc[key+'_desc']='花费40政治点，须66席支持且动员限制解除。对方可以拒绝；签署协约不意味着吞并或取得核心。'
    code.append('}');return '\n'.join(code)+'\n',loc


def make_events():
    events='''add_namespace = sof_brt
country_event = { id = sof_brt.1 title = sof_brt.1.t desc = sof_brt.1.d picture = GFX_sof_brt_event_parliament is_triggered_only = yes
option = { name = sof_brt.accept ai_chance = { factor = 60 }
trigger = { has_war = no is_subject = no FROM = { exists = yes sof_brt_active = yes has_war = no is_subject = no } NOT = { has_war_with = FROM } }
add_timed_idea = { idea = sof_brt_trade days = 180 } FROM = { add_timed_idea = { idea = sof_brt_trade days = 180 } clr_country_flag = sof_brt_offer_pending } clr_country_flag = sof_brt_offer_target_pending }
option = { name = sof_brt.refuse ai_chance = { factor = 40 } clr_country_flag = sof_brt_offer_target_pending FROM = { clr_country_flag = sof_brt_offer_pending country_event = { id = sof_brt.3 days = 1 } } }
}
country_event = { id = sof_brt.2 title = sof_brt.2.t desc = sof_brt.2.d picture = GFX_sof_brt_event_parliament is_triggered_only = yes
option = { name = sof_brt.accept ai_chance = { factor = 45 }
trigger = { has_war = no is_subject = no is_in_faction = no NOT = { has_war_with = FROM }
FROM = { exists = yes sof_brt_active = yes is_subject = no has_completed_focus = SOF_BRT_D4 sof_brt_supermajority = yes check_variable = { sof_brt_isolation = 0 } OR = { is_in_faction = no is_faction_leader = yes } } }
FROM = { if = { limit = { is_in_faction = no } create_faction = sof_brt_western_pact } add_to_faction = ROOT clr_country_flag = sof_brt_offer_pending } clr_country_flag = sof_brt_offer_target_pending }
option = { name = sof_brt.refuse ai_chance = { factor = 55 } clr_country_flag = sof_brt_offer_target_pending FROM = { clr_country_flag = sof_brt_offer_pending country_event = { id = sof_brt.3 days = 1 } } }
}
country_event = { id = sof_brt.3 title = sof_brt.3.t desc = sof_brt.3.d picture = GFX_sof_brt_event_parliament is_triggered_only = yes option = { name = sof_brt.acknowledge } }
'''
    loc={'sof_brt.1.t':'布列塔尼的市镇商贸提议','sof_brt.1.d':'[From.GetName]希望签订180日的地方商贸协约。合作保留双方的政治自主与领土。',
         'sof_brt.2.t':'西部防卫协约邀请','sof_brt.2.d':'[From.GetName]经议会授权邀请我们加入西部防卫协约。我们有权拒绝并维持独立政策。',
         'sof_brt.3.t':'协商未能达成一致','sof_brt.3.d':'对方拒绝了协约提议。地方议会将继续通过公开协商处理西部关系。',
         'sof_brt.accept':'接受协约','sof_brt.refuse':'维持独立政策','sof_brt.acknowledge':'尊重对方的决定','sof_brt_western_pact':'西部防卫协约'}
    return events,loc


def patch_shared():
    changed=[]
    def patch(rel,fn):
        p=MOD/rel;before=p.read_text(encoding='utf-8-sig');after=fn(before)
        parse(after);write(rel,after);changed.append(rel)
    # Existing legacy cleanup would otherwise remove a new REN government's spirits.
    def migration(text):
        tree=one(parse(text),'sof_van_setup');changes=[]
        for row in entries(tree.value,'if'):
            lim=one(row.value,'limit')
            if scalar(lim.value,'original_tag')=='REN' and not any(n.key=='has_focus_tree' and n.value=='sof_brittany' for n in walk(lim.value)):
                changes.append((lim.end-1,lim.end-1,' NOT = { has_focus_tree = sof_brittany } '))
        return replace(text,changes)
    patch('common/scripted_effects/sof_vanilla_major.txt',migration)
    def campaign(text):
        category=one(parse(text),'sofzh_unification_campaign_category');decision=one(category.value,'sofzh_unification_border_campaign');gate=one(decision.value,'available')
        if not entries(gate.value,'sof_brt_expansion_allowed'):return replace(text,[(gate.end-1,gate.end-1,' sof_brt_expansion_allowed = yes ')])
        return text
    patch('common/decisions/sofzh_unification.txt',campaign)
    def ai(text):
        node=one(parse(text),'sofzh_ai_supported_focus_tree');branch=one(node.value,'OR')
        if not any(n.value=='sof_brittany' for n in entries(branch.value,'has_focus_tree')):
            return replace(text,[(branch.end-1,branch.end-1,' has_focus_tree = sof_brittany ')])
        return text
    patch('common/scripted_triggers/sofzh_corsica.txt',ai)
    # Add the new milestones to the authored MIO design, then change only REN
    # blocks/keys in its three shared runtime files.
    design_path=ROOT/'design/regional-manufacturers.json';design=json.loads(design_path.read_text(encoding='utf-8'))
    row=next(r for r in design['manufacturers'] if r['tag']=='REN')
    for field,code in [('unlock','N2'),('specialize','N7'),('capstone','N8')]:
        if focus_id(code) not in row[field]:
            row[field].append(focus_id(code));row[field+'_names'].append(next(r['name'] for r in authored_nodes() if r['code']==code))
    design_path.write_text(json.dumps(design,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    from build_regional_manufacturers import render
    rendered=render(design)
    def mio(text):
        new=rendered['mio'];old=one(parse(text),'sof_reg_ren_organization');node=one(parse(new),'sof_reg_ren_organization')
        return replace(text,[(old.start,old.end,new[node.start:node.end])])
    def legacy(text):
        new=rendered['ideas'];old=next(n for n in walk(parse(text)) if n.key=='sof_reg_ren_organization_legacy');node=next(n for n in walk(parse(new)) if n.key==old.key)
        return replace(text,[(old.start,old.end,new[node.start:node.end])])
    patch('common/military_industrial_organization/organizations/sof_regional_manufacturers.txt',mio)
    patch('common/ideas/sof_regional_manufacturers.txt',legacy)
    rel='localisation/simp_chinese/replace/sof_regional_manufacturers_l_simp_chinese.yml'
    text=(MOD/rel).read_text(encoding='utf-8-sig');replacement={line.split(':',1)[0]:line for line in rendered['loc'].splitlines() if line.startswith(' sof_reg_ren_')}
    text='\n'.join(replacement.get(line.split(':',1)[0],line) for line in text.splitlines())+'\n';write(rel,text);changed.append(rel)
    # The manufacturer rebuild contract also covers its generated documentation.
    (ROOT/'docs/REGIONAL-MANUFACTURERS-ZH.md').write_text(rendered['doc'],encoding='utf-8',newline='\n')
    return changed


from brittany_military import augment
augment(REWARDS,GATES,IDEAS,EXCLUSIVE,DESCRIPTIONS,BILLS,research,idea)
from brittany_council_expansion import strengthen
strengthen(ROOT,REWARDS,GATES,IDEAS,DESCRIPTIONS,build_local)

if __name__=='__main__':build()
