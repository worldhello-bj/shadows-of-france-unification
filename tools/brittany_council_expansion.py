"""Stronger specialist institutions, council programmes and a historical bench."""
import json
import re

# The home field is a political base, mapped to this mod's coarse state grid.
# It is not always the politician's birthplace. These mappings are game design.
POOL = [
 dict(slot='chateau',key='la_chambre',name='居伊·拉尚布尔',short='拉尚布尔',home=165,town='圣塞尔旺／圣马洛',ideology='liberalism',source='https://www2.assemblee-nationale.fr/sycomore/fiche/4175?legislature=47',role='圣塞尔旺市长、圣马洛选区众议员'),
 dict(slot='lemaistre',key='lefas',name='亚历山大·勒法',short='勒法',home=179,town='圣欧班迪科尔米耶／富热尔',ideology='conservatism',source='https://www.senat.fr/senateur-3eme-republique/lefas_alexandre0535r3.html',role='伊勒－维莱讷参议员、前地方议会主席'),
 dict(slot='bahon',key='goude',name='埃米尔·古德',short='古德',home=168,town='布雷斯特',ideology='socialism',source='https://www2.assemblee-nationale.fr/sycomore/fiche/3491',role='布雷斯特选区众议员，历史上1936年退出议会'),
 dict(slot='legorgeu',key='rio',name='阿尔方斯·里奥',short='里奥',home=198,town='基伯龙／莫尔比昂',ideology='liberalism',source='https://www.senat.fr/senateur-3eme-republique/rio_alphonse0903r3.html',role='莫尔比昂参议员、航海与海运事务政治人物'),
 dict(slot='tremintin',key='pinvidic',name='约瑟夫·潘维迪克',short='潘维迪克',home=162,town='朗迪维肖',ideology='conservatism',source='https://www2.assemblee-nationale.fr/sycomore/fiche/5952',role='1935年朗迪维肖市议员；此时尚非国会议员'),
 dict(slot='prigent',key='perrot',name='让·佩罗',short='佩罗',home=200,town='埃斯基比安／坎佩尔地区',ideology='liberalism',source='https://www2.assemblee-nationale.fr/sycomore/fiche/5825?legislature=41',role='菲尼斯泰尔众议员与农业地方政治人物'),
]
PRIMARY_HOME=dict(chateau=188,lemaistre=188,bahon=188,legorgeu=168,tremintin=162,prigent=162)
PRIMARY_TOWN=dict(chateau='雷恩',lemaistre='雷恩',bahon='雷恩',legorgeu='布雷斯特',tremintin='普卢埃斯卡',prigent='圣让迪杜瓦')
HOME_STATES={188:'雷恩',168:'布雷斯特',162:'莫尔莱及北菲尼斯泰尔',165:'圣马洛',179:'富热尔地区',198:'莫尔比昂沿岸',200:'坎佩尔及西南菲尼斯泰尔'}
PROGRAMMES={
 'economy':dict(title='公共建设与工坊拨款',pre='has_completed_focus = SOF_BRT_P15',sponsors=['chateau','lemaistre'],mods=dict(production_speed_industrial_complex_factor=.12,industrial_capacity_factory=.08)),
 'army':dict(title='陆军训练与军需预算',pre='has_completed_focus = SOF_BRT_M3 OR = { has_completed_focus = SOF_BRT_F0 has_completed_focus = SOF_BRT_O0 }',sponsors=['bahon','lemaistre'],mods=dict(army_attack_factor=.06,army_defence_factor=.08,army_org_factor=.04)),
 'navy':dict(title='海军舰艇与护航拨款',pre='has_completed_focus = SOF_BRT_N2 has_country_flag = sof_brt_law_ports',sponsors=['legorgeu'],mods=dict(industrial_capacity_dockyard=.10,convoy_escort_efficiency=.08)),
 'air':dict(title='航空训练与维修拨款',pre='has_completed_focus = SOF_BRT_A2',sponsors=['bahon','tremintin'],mods=dict(air_mission_efficiency=.08,air_accidents_factor=-.08)),
 'science':dict(title='地方高校与实验室基金',pre='has_completed_focus = SOF_BRT_E9 has_completed_focus = SOF_BRT_P9',sponsors=['lemaistre','tremintin'],mods=dict(research_speed_factor=.08)),
 'diplomacy':dict(title='西部协商与领事事务预算',pre='has_completed_focus = SOF_BRT_D0 has_completed_focus = SOF_BRT_P20',sponsors=['chateau','legorgeu'],mods=dict(improve_relations_maintain_cost_factor=-.20,trade_opinion_factor=.15,political_power_factor=.05)),
}


def programme_gate(p):
    return 'sof_brt_active = yes is_subject = no has_capitulated = no sof_brt_majority = yes '+p['pre']+' '+' '.join('has_country_flag = sof_brt_pledge_'+key for key in p['sponsors'])


def slot_active_here(slot,state):
    reserve=next(p for p in POOL if p['slot']==slot)
    parts=[]
    if PRIMARY_HOME[slot]==state:parts.append(f'NOT = {{ has_country_flag = sof_brt_reserve_{slot} }}')
    if reserve['home']==state:parts.append(f'has_country_flag = sof_brt_reserve_{slot}')
    return parts[0] if len(parts)==1 else 'OR = { '+' '.join(parts)+' }' if parts else 'always = no'


def home_triggers():
    # An allied army holding our own state is not treated as an enemy occupation.
    return '\n'.join(f'sof_brt_home_access_{state} = {{ OR = {{ controls_state = {state} {state} = {{ is_owned_by = ROOT controller = {{ is_in_faction_with = ROOT }} }} }} }}' for state in HOME_STATES)+'\n'


def strengthen(root,rewards,gates,ideas,descriptions,build_local):
    # Use the actual generic mature profiles, not a guessed vanilla baseline.
    baseline=root/'design/dynamic-spirits.json'
    if not baseline.exists():baseline=root/'design/brittany-generic-baseline.json'
    generic=json.loads(baseline.read_text(encoding='utf-8'))['states']
    comparisons=[]
    mapping={'civil_industry':'civic_bureau','mil_industry':'production','infantry':'home_defence','staff':'staff_bureau','research':'science_bureau','dockyards':'naval_bureau','air_support':'air_ground','air_defence':'watch'}
    for family,key in mapping.items():
        base=generic[family]['g3']['modifiers']
        mods={k:round(float(v)*1.30,3) for k,v in base.items()}
        old=ideas.get(key,(key,'',{}))
        ideas[key]=(dict(civic_bureau='市镇公共建设总局',staff_bureau='雷恩联合参谋学校',science_bureau='布列塔尼技术研究院',naval_bureau='布雷斯特船坞统筹局').get(key,old[0]),'专属成熟体系的主要数值按本模组通用成熟体系的130%设计。具体数值与路线代价见修正列表。',mods)
        comparisons += [dict(family=family,modifier=k,generic=float(v),brittany=mods[k]) for k,v in base.items()]
    ideas['home_defence'][2]['conscription']=.008
    ideas['defensive_program'][2].update(army_core_defence_factor=.16,planning_speed=-.05)
    ideas['fortress'][2].update(army_core_defence_factor=.10,army_attack_factor=-.03)
    ideas['offensive_program'][2].update(army_attack_factor=.06,planning_speed=.10,max_planning_factor=.06)
    ideas['initiative'][2].update(army_attack_factor=.12,planning_speed=.08)
    ideas['air_service']=('布列塔尼联合航空勤务','地方航空队的专业勤务与燃料管理。',dict(air_mission_efficiency=.104,air_fuel_consumption_factor=-.156))
    for key,p in PROGRAMMES.items():ideas['committee_'+key]=(p['title'],'议会拨款持续180日；失去多数或必要的议员承诺将即时撤销，必须重新拨款。',p['mods'])
    ideas['exile_relief']=('流亡代表与地方救济','在失陷地区之外维持代表团，增加临时公共支出。',dict(consumer_goods_factor=.02))
    rewards['E7']+=' add_ideas = sof_brt_civic_bureau'
    rewards['M9']+=' add_ideas = sof_brt_staff_bureau'
    rewards['E10']+=' add_ideas = sof_brt_science_bureau'
    rewards['N8']+=' add_ideas = sof_brt_naval_bureau'
    rewards['A6']+=' add_ideas = sof_brt_air_service'
    rewards['M1']+=' add_manpower = 10000'
    # Two uses at 125%, versus the generic opening's one 100% small-arms bonus.
    for c in ['M3','M4','M8','A1','A2','A3','A4','A5','N4','N5','N7']:
        rewards[c]=re.sub(r'bonus = [\d.]+ uses = 1', 'bonus = 1.25 uses = 2',rewards[c])
    for c in list(rewards):
        if c[0] in 'BFO':rewards[c]=rewards[c].replace('bonus = 0.25','bonus = 0.75')
    for c,b in [('E3','industrial_complex'),('E4','industrial_complex'),('E7','industrial_complex'),('E11','arms_factory'),('I6','arms_factory'),('I7','arms_factory')]:
        rewards[c]+=' '+build_local(b)
    for c,state in [('N2',168),('N5',208),('N8',168)]:rewards[c]+=' '+build_local('dockyard',state)
    descriptions['F0']='51席确立孤立防御纲领，与积极进攻互斥。本土防御提高16%，消费品系数减少1%，计划速度降低5%，船坞建设速度降低5%。议会可另行拨款加强训练和勤务。'
    descriptions['O0']='66席远征组织法案、勒戈尔热有效支持与外部威胁是前提。增加6%攻击、10%计划速度和6%计划上限，同时削减4%本土防御、8%民用建设并增加消费品。宣战仍须独立的75席授权。'
    for c in ['E3','E4','E7','E11','I6','I7','N2','N5','N8']:
        descriptions[c]='授权两项本地建设拨款。每次建设均检查实际所有权、完整控制和可用容量；没有容量时每项补偿25政治点。船坞项目必须位于国策指定的布雷斯特或洛里昂，其他工场位于布列塔尼地区。'
    for c,idea in [('E7','civic_bureau'),('M9','staff_bureau'),('E10','science_bureau'),('N8','naval_bureau')]:descriptions[c]+=' 同时建立强度高于通用成熟体系的专属常设机构。'
    descriptions['P12']='市政协商席和财政审计席的现任代表均须有效支持，且形成51席多数。初始代表是沙托与勒梅斯特；改任候补后按同一委员会议席重新协商。'
    descriptions['P13']='劳工席和农业席的现任代表均须有效支持，且形成51席多数。初始代表是巴翁与唐吉－普里让；候补接任不会额外增加议席。'
    descriptions['P14']='财政审计席和地方教育席的现任代表均须有效支持，且形成51席多数。初始代表是勒梅斯特与特雷曼坦。'
    descriptions['O0']=descriptions['O0'].replace('勒戈尔热有效支持','港务席现任代表有效支持')
    out=root/'docs/reports/brittany/balance-comparison.json';out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(dict(baseline='Current mod generic g3 profiles; corresponding permanent specialist values only',ratio=1.30,rows=comparisons,engine_balance_tested=False),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def extra_effects(delegates):
    code=['sof_brt_prepare_bench = { if = { limit = { sof_brt_active = yes NOT = { has_country_flag = sof_brt_bench_prepared } }']
    for p in POOL:code.append('recruit_character = SOF_BRT_'+p['key'])
    for k in ['legorgeu','tremintin','prigent']:code.append('recruit_character = SOF_BRT_'+k)
    code.append('set_country_flag = sof_brt_bench_prepared } }')
    for key,_,_,_,_,contract in delegates:
        p=next(p for p in POOL if p['slot']==key)
        code.append(f'''sof_brt_replace_{key} = {{
 clr_country_flag = sof_brt_pledge_{key} remove_ideas = sof_brt_{contract} clr_country_flag = sof_brt_suspended_{key}
 if = {{ limit = {{ has_country_flag = sof_brt_reserve_{key} }} clr_country_flag = sof_brt_reserve_{key} }} else = {{ set_country_flag = sof_brt_reserve_{key} }}
 if = {{ limit = {{ OR = {{ AND = {{ has_country_flag = sof_brt_reserve_{key} has_country_flag = sof_brt_home_seen_{p['home']} sof_brt_home_access_{p['home']} = no }} AND = {{ NOT = {{ has_country_flag = sof_brt_reserve_{key} }} has_country_flag = sof_brt_home_seen_{PRIMARY_HOME[key]} sof_brt_home_access_{PRIMARY_HOME[key]} = no }} }} }} set_country_flag = sof_brt_suspended_{key} }}
 set_country_flag = {{ flag = sof_brt_replacement_cooldown_{key} days = 180 }}
 sof_brt_count_support = yes sof_brt_committee_sync = yes
}}''')
    code.append('sof_brt_committee_sync = {')
    for key,p in PROGRAMMES.items():code.append(f'if = {{ limit = {{ NOT = {{ {programme_gate(p)} }} }} remove_ideas = sof_brt_committee_{key} }}')
    code.append('}')
    # Snapshot current control first: loading a game is never a capture event.
    code.append('sof_brt_home_watch = { if = { limit = { sof_brt_active = yes }')
    code.append('if = { limit = { NOT = { has_country_flag = sof_brt_home_watch_initialized } }')
    for state in HOME_STATES:code.append(f'if = {{ limit = {{ sof_brt_home_access_{state} = yes }} set_country_flag = sof_brt_home_held_{state} set_country_flag = sof_brt_home_seen_{state} }}')
    code.append('set_country_flag = sof_brt_home_watch_initialized } else = {')
    for i,state in enumerate(HOME_STATES):
        code.append(f'if = {{ limit = {{ sof_brt_home_access_{state} = yes NOT = {{ has_country_flag = sof_brt_home_held_{state} }} }}')
        code.append(f'if = {{ limit = {{ NOT = {{ has_country_flag = sof_brt_home_notice_{state} }} }} if = {{ limit = {{ has_country_flag = sof_brt_home_seen_{state} }} country_event = {{ id = sof_brt_local.{102+i*3} days = 1 }} }} else = {{ country_event = {{ id = sof_brt_local.{101+i*3} days = 1 }} }} set_country_flag = {{ flag = sof_brt_home_notice_{state} days = 14 }} }}')
        code.append(f'set_country_flag = sof_brt_home_held_{state} set_country_flag = sof_brt_home_seen_{state}')
        for slot,_,_,_,_,_ in delegates:code.append(f'if = {{ limit = {{ {slot_active_here(slot,state)} }} clr_country_flag = sof_brt_suspended_{slot} }}')
        code.append('}')
        code.append(f'if = {{ limit = {{ sof_brt_home_access_{state} = no has_country_flag = sof_brt_home_held_{state} }} clr_country_flag = sof_brt_home_held_{state}')
        for slot,_,_,_,_,contract in delegates:
            code.append(f'if = {{ limit = {{ {slot_active_here(slot,state)} }} clr_country_flag = sof_brt_pledge_{slot} remove_ideas = sof_brt_{contract} set_country_flag = sof_brt_suspended_{slot} }}')
        code.append(f'if = {{ limit = {{ NOT = {{ has_country_flag = sof_brt_home_notice_{state} }} }} country_event = {{ id = sof_brt_local.{100+i*3} days = 1 }} set_country_flag = {{ flag = sof_brt_home_notice_{state} days = 14 }} }} sof_brt_count_support = yes sof_brt_committee_sync = yes }}')
    code.append('} } }')
    return '\n'.join(code)+'\n'


def author_pool(mod,root,delegates):
    loc={};files=[]
    def write(rel,text,bom=False):
        p=mod/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8-sig' if bom else 'utf-8',newline='\n');files.append(rel)
    characters=['characters = {']
    for p in POOL+[dict(key=k,name=n,ideology='liberalism') for k,n,_,_,_,_ in delegates if k in ['legorgeu','tremintin','prigent']]:
        key='SOF_BRT_'+p['key'];loc[key]=p['name']
        characters.append(f'{key} = {{ name = {key} portraits = {{ civilian = {{ large = "GFX_portrait_unknown" }} }} country_leader = {{ ideology = {p["ideology"]} expire = "1970.1.1.1" }} }}')
    characters.append('}');write('common/characters/sof_brittany_council.txt','\n'.join(characters)+'\n')
    decision=['sof_brt_committees = {']
    for p in POOL:
        slot=p['slot'];key='sof_brt_rotate_'+slot
        decision.append(f'{key} = {{ icon = sof_cw_civil cost = 50 days_re_enable = 180 visible = {{ has_completed_focus = SOF_BRT_P1 }} available = {{ sof_brt_active = yes is_subject = no has_capitulated = no NOT = {{ has_country_flag = sof_brt_replacement_cooldown_{slot} }} }} complete_effect = {{ sof_brt_replace_{slot} = yes }} ai_will_do = {{ factor = 0 }} }}')
        old=next(n for k,n,_,_,_,_ in delegates if k==slot)
        loc[key]=f'改任地方代表：{old} ⇄ {p["name"]}'
        loc[key+'_desc']=f'候补身份：{p["role"]}。政治驻地：{p["town"]}（映射{p["home"]}州）。花费50政治点并冷却180日，往返切换同一议席代表，保留原席位总额；清除当前支持与拨款承诺，新代表必须重新协商。不会额外增加议席。沦陷并不意味着该人物历史上死亡。'
    for key,p in PROGRAMMES.items():
        d='sof_brt_fund_'+key;gate=programme_gate(p)
        decision.append(f'{d} = {{ icon = sof_cw_register cost = 35 days_re_enable = 180 visible = {{ {p["pre"]} }} available = {{ {gate} NOT = {{ has_idea = sof_brt_committee_{key} }} }} complete_effect = {{ add_timed_idea = {{ idea = sof_brt_committee_{key} days = 180 }} }} ai_will_do = {{ factor = 5 }} }}')
        loc[d]='议会专项：'+p['title'];loc[d+'_desc']='须51席及相关委员会代表的有效支持。支付35政治点，拨款持续180日。失去多数、必要支持或独立执政条件后撤销；代表更换也会触发复核。不能重复叠加。'
    decision.append('}');write('common/decisions/sof_brittany_committees.txt','\n'.join(decision)+'\n')
    write('common/decisions/categories/sof_brittany_committees.txt','sof_brt_committees = { icon = sof_cw_register priority = 89 visible = { sof_brt_active = yes has_completed_focus = SOF_BRT_P1 } }\n')
    loc['sof_brt_committees']='议会委员会与候补代表';loc['sof_brt_committees_desc']='财政、陆军、海军、航空、科研和外交均可取得有期限的专项拨款。维持多数和议员支持才能保留强化效果。六个议席各有一名历史候补，改任不增加总席位。'
    events=['add_namespace = sof_brt_local']
    for i,(state,town) in enumerate(HOME_STATES.items()):
        for offset,kind in [(0,'loss'),(1,'capture'),(2,'recover')]:
            eid=100+i*3+offset;prefix=f'sof_brt_local.{eid}'
            loc[prefix+'.t']=town+dict(loss='：地方代表驻地沦陷',capture='：攻下代表的家乡地区',recover='：家乡地区重获控制')[kind]
            loc[prefix+'.d']=f'{town}的控制权发生变化。这里的家乡指代表的地方政治基地，并按本模组州界映射。'+('驻地在此的现任代表暂失地方授权，其支持和关联专项拨款已撤销。我们可以维持流亡代表团，或在委员会决议中改任候补。' if kind=='loss' else '相关现任代表恢复协商资格；旧支持没有免费续期。请重新协商地方支持，任何占领整合仍须遵守现有制度。')
            picture='GFX_sof_brt_event_home_loss' if kind=='loss' else 'GFX_sof_brt_event_home_recovery'
            events.append(f'country_event = {{ id = {prefix} title = {prefix}.t desc = {prefix}.d picture = {picture} is_triggered_only = yes')
            if kind=='loss':
                restore=' '.join(f'if = {{ limit = {{ {slot_active_here(slot,state)} }} clr_country_flag = sof_brt_suspended_{slot} }}' for slot,_,_,_,_,_ in delegates)
                events.append(f'option = {{ name = sof_brt_local.exile trigger = {{ sof_brt_active = yes is_subject = no has_capitulated = no NOT = {{ has_political_power < 25 }} sof_brt_home_access_{state} = no }} add_political_power = -25 add_timed_idea = {{ idea = sof_brt_exile_relief days = 180 }} {restore} ai_chance = {{ factor = 60 }} }}')
            events.append('option = { name = sof_brt_local.acknowledge ai_chance = { factor = 40 } } }')
    loc['sof_brt_local.exile']='拨款25政治点维持流亡代表团';loc['sof_brt_local.acknowledge']='尊重地方授权，交由委员会重新协商'
    write('events/sof_brittany_hometowns.txt','\n'.join(events)+'\n')
    write('localisation/simp_chinese/replace/sof_brittany_pool_l_simp_chinese.yml','l_simp_chinese:\n'+'\n'.join(f' {k}:0 "{v}"' for k,v in loc.items())+'\n',True)
    spec=dict(reserves=POOL,primary_homes=PRIMARY_HOME,primary_towns=PRIMARY_TOWN,home_states=HOME_STATES,programmes=PROGRAMMES,total_seats=100,replacement_cost=50,replacement_cooldown=180,events=21,portraits='Native unknown portrait placeholders; no fabricated historical likenesses',state_mapping='Political bases, approximate state-level mapping; not birthplaces or exact province control')
    (root/'design/brittany-council-pool.json').write_text(json.dumps(spec,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return files
