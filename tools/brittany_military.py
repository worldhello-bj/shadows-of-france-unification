"""Brittany's common services and two mutually exclusive military programmes.

Geographic names describe fictional plans, not documented interwar operations.
All modifiers are bounded; offensive planning never grants a war declaration.
"""

DATA = '''
B0|雷恩兵籍与动员档案|selective_training_act|60,13|M9
B1|市镇军官轮训|build_the_pentagon|58,15|B0
B2|法语与布列塔尼语军令|desegregate_the_armed_forces|62,15|B0;P9
B3|乡村救护运输队|womens_armed_service_integration_act|58,17|B1;M7
B4|军需采购公开招标|military_construction|62,17|B2;P10
B5|雷恩电台与信号兵|magic|66,15|A5;M3
B6|圣布里厄维修队|support_rock_island|66,17|B5;E8
B7|南部铁路军运时刻表|USACE_projects|70,17|M6;E5
B8|地方燃料储备委员会|wartime_industry|70,19|B7;B4
B9|迪纳尔航空勤务学校|us_army_airforce|74,15|A5
B10|渔港气象观测站|air_war_plans_division|74,17|B9;N1
B11|沿岸航空修理工坊|TAC|74,19|B10;B6
B12|布雷斯特航海训练班|bureau_of_ships|78,15|N8
B13|洛里昂轮机技师|fleet_submarines|78,17|B12;N5
B14|渔民与商船无线电网|convoy_tactics|78,19|B13;B5
B15|议会三军采购委员会|department_of_defense|68,22|B8;B11;B14;P21
F0|孤立防御：守住半岛|hemisphere_defense|96,2|M0
F1|市镇国民卫队|selective_training_act|88,4|F0;M1
F2|博卡日防御图|louisiana_maneuvers|92,4|F0;M2
F3|沿岸观察哨网络|air_war_plans_division|100,4|F0;A1
F4|维莱讷河阻滞计划|first_special_service_force|88,6|F1;M8
F5|朗斯河渡口工事|military_construction|92,6|F2;M8
F6|蒙达雷山地通路|army_of_the_united_states|96,6|F2
F7|市镇防空警报|air_support|100,6|F3;A5
F8|布雷斯特港口防空|escort_fighters|104,6|F3;N2
F9|乡村分散军需仓|wartime_industry|88,8|F4;M6
F10|预备役冬季轮训|selective_training_act|92,8|F5;M1
F11|地方炮兵观察所|support_rock_island|96,8|F6;M4
F12|迪纳尔本土截击队|escort_fighters|100,8|F7;A2
F13|雷达与空情值班室|magic|104,8|F8;A5
F14|雷恩后方救护中心|womens_armed_service_integration_act|88,10|F9;P16
F15|粮食储运与围困配给|agricultural_adjustment_act|92,10|F10;E3
F16|海岸炮兵测距|bureau_of_ships|96,10|F11;N0
F17|夜间港口警戒|air_support|100,10|F12;F13
F18|近海护航防线|escort_effort|104,10|F13;N6
F19|圣马洛航道巡逻|convoy_tactics|88,12|F14;N6
F20|渔船救难队|maritime_commission|92,12|F15;N3
F21|滨海障碍与工兵阵地|first_special_service_force|96,12|F16;M8
F22|舰艇损管与港口救火|bureau_of_ships|100,12|F17;N2
F23|武装中立巡航规则|neutrality_act|104,12|F18;I1/I2
F24|乡镇战时通信员|magic|88,14|F19;B5
F25|合作社应急供给|agricultural_adjustment_act|92,14|F20;P17
F26|圣布里厄反击预案|louisiana_maneuvers|96,14|F21;M2
F27|空海防御联络席|air_war_plans_division|100,14|F22;A4
F28|轻型护航艇工艺|escort_effort|104,14|F23;N4
F29|乡村分散修理所|support_rock_island|88,16|F24;B6
F30|农时与服役协调|worker_management_act|92,16|F25;P17
F31|本土防御联合演习|louisiana_maneuvers|96,16|F26;F27
F32|海港撤离演练|maritime_commission|100,16|F27;F20
F33|地方防卫预算审查|income_tax_reform|104,16|F28;P21
F34|保卫自治共同体|hemisphere_defense|94,18|F29;F30;F31
F35|堡垒半岛|department_of_defense|100,20|F34;F32;F33
O0|积极进攻：议会远征军|war_plans_division|124,2|M0;I2/I8
O1|雷恩机动参谋部|build_the_pentagon|116,4|O0;M3
O2|职业志愿兵团|army_of_the_united_states|120,4|O0;M1
O3|迪纳尔战术航空联队|TAC|128,4|O0;A3
O4|布雷斯特出海筹备处|two_ocean_navy_act|132,4|O0;N2
O5|维莱讷河突破演习|louisiana_maneuvers|116,6|O1;M2
O6|沿公路展开的步兵|armored_infantry|120,6|O2;M6
O7|轻装甲维修班|tank_experiments|124,6|O2;E8
O8|前沿航空观察员|CAS|128,6|O3;A1
O9|舰队前进锚地规划|bureau_of_ships|132,6|O4;N1
O10|野战炮兵集中射击|support_rock_island|116,8|O5;M4
O11|机动反坦克分队|tank_destroyer_doctrine|120,8|O6;M4
O12|工兵渡河突击|first_special_service_force|124,8|O7;M8
O13|空地无线电协同|magic|128,8|O8;A5
O14|洛里昂潜航出击|fleet_submarines|132,8|O9;N5
O15|南特方向军运推演|USACE_projects|116,10|O10;B7
O16|摩托化补给纵队|armored_infantry|120,10|O11;M6
O17|军官与军士战场轮换|build_the_pentagon|124,10|O12;B1
O18|沿岸攻击航空训练|CAS|128,10|O13;A4
O19|海峡侦察与舰队联络|convoy_tactics|132,10|O14;B14
O20|有限目标作战章程|war_powers_act|116,12|O15;P21
O21|布列塔尼机动旅|army_of_the_united_states|120,12|O16;O17
O22|联合火力指挥所|air_support|124,12|O17;O13
O23|迪纳尔快速整补|us_army_airforce|128,12|O18;B11
O24|海上出击保障队|fund_the_navy|132,12|O19;N8
O25|布雷斯特登陆筹备队|expand_the_USMC|116,14|O20;N8
O26|圣马洛装船演练|liberty_ships|120,14|O21;N3
O27|滩头通信与炮火引导|amphibious_operations|124,14|O22;O25
O28|海空登陆掩护|carrier_primacy|128,14|O23;O26
O29|港口突击损管规程|bureau_of_ships|132,14|O24;O27
O30|议会战役目标书|war_powers_act|116,16|O25;I10
O31|远征补给预算|wartime_industry|120,16|O26;P15
O32|半岛联合进攻演习|louisiana_maneuvers|124,16|O27;O28
O33|军民责任与战地救护|womens_armed_service_integration_act|128,16|O28;P16
O34|三军远征指挥部|department_of_defense|132,18|O29;O32
O35|议会授权下的主动出击|global_hegemony|124,20|O30;O31;O33;O34
'''

RENAMED = {
 'M0':'布列塔尼地方防务署','M1':'市镇预备役名册','M2':'维莱讷河与博卡日演习',
 'M3':'雷恩军士与参谋学校','M4':'圣布里厄炮械标准','M5':'布列塔尼地方守备队',
 'M6':'半岛道路与军需车队','M7':'雷恩妇女军需与救护队','M8':'沿岸工兵与河口勤务',
 'M9':'地方议会军政委员会','A0':'迪纳尔与雷恩航空规划','A1':'渔港空情与沿岸侦察',
 'A2':'迪纳尔战斗机技术班','A3':'半岛航空观察员训练','A4':'近海对舰飞行训练',
 'A5':'雷恩无线电与雷达室','A6':'布列塔尼联合航空队','N0':'布列塔尼海防委员会',
 'N1':'圣马洛沿海运输局','N2':'布雷斯特船厂协作','N3':'渔港商船修造计划',
 'N4':'布雷斯特轻舰设计班','N5':'洛里昂潜艇工艺','N6':'渔港至军港护航规程',
 'N7':'洛里昂潜航可靠性','N8':'布列塔尼海军拨款','N9':'布雷斯特海军陆战队',
 'N10':'布列塔尼登陆协同演习',
}


def augment(rewards,gates,ideas,exclusive,descriptions,bills,research,idea):
    # Shared foundations do not pre-empt the doctrinal choice.
    ideas['home_defence']=('地方守备制度','市镇兵籍与有限的守备役训练。',dict(army_core_defence_factor=.03,conscription=.002))
    ideas.update({
     'defensive_program':('孤立防御纲领','本土阵地与民生优先，削减远洋船厂投入。',dict(army_core_defence_factor=.06,planning_speed=-.05,consumer_goods_factor=-.01,production_speed_dockyard_factor=-.05)),
     'offensive_program':('议会远征纲领','机动作战占用民用投资，并削弱固定阵地防卫。',dict(planning_speed=.06,max_planning_factor=.04,army_core_defence_factor=-.04,production_speed_industrial_complex_factor=-.08,consumer_goods_factor=.02)),
     'bocage':('博卡日阵地训练','密集村落、田界与道路构成纵深防御训练的背景。',dict(dig_in_speed_factor=.08,max_dig_in_factor=.06)),
     'watch':('沿岸空情网','岸上观察与战斗机值班协调。',dict(air_intercept_efficiency=.05)),
     'shelter':('分散军需与救护','减少战场损耗；分散采购稍微降低产出。',dict(experience_loss_factor=-.04,industrial_capacity_factory=-.01)),
     'coast_guard':('半岛近海警戒','节省航行燃料并提高近海护航效率。',dict(convoy_escort_efficiency=.04,navy_fuel_consumption_factor=-.04)),
     'fortress':('堡垒半岛','维持本土纵深，主动攻击效率受到约束。',dict(army_core_defence_factor=.04,army_attack_factor=-.03)),
     'mobile':('布列塔尼机动旅制度','野战运输提高组织恢复，但增加补给消耗。',dict(army_org_regain=.04,supply_consumption_factor=.04)),
     'air_ground':('迪纳尔空地协同','有限的近距支援与任务勤务改进。',dict(air_cas_present_factor=.03,air_mission_efficiency=.03)),
     'expedition_supply':('远征补给预算','本土道路以外的补给需要专门拨款。',dict(supply_consumption_factor=-.04,consumer_goods_factor=.01)),
     'initiative':('议会授权下的主动出击','提高攻击效率，同时增加战场补给负担。',dict(army_attack_factor=.04,planning_speed=.04,supply_consumption_factor=.05)),
     'signals':('半岛通信标准','三军统一信号与备件标准。',dict(land_reinforce_rate=.01)),
    })
    exclusive.update(F0=['O0'],O0=['F0'])
    gates['F0']='sof_brt_majority = yes'
    gates['O0']='sof_brt_supermajority = yes has_country_flag = sof_brt_law_expedition check_variable = { sof_brt_isolation < 3 }'
    bills['expedition']=('远征军组织与预算案',66,'has_completed_focus = SOF_BRT_M0 OR = { has_completed_focus = SOF_BRT_I2 has_completed_focus = SOF_BRT_I8 }','has_country_flag = sof_brt_pledge_legorgeu sof_brt_external_threat = yes')
    rewards.update({
      'B0':'add_army_experience = 10','B1':research('support_tech',.25),'B2':'add_army_experience = 10',
      'B3':research('support_tech',.25),'B4':'add_political_power = 25','B5':idea('signals'),
      'B6':research('industry',.25),'B7':'add_army_experience = 10','B8':'add_political_power = 20',
      'B9':'add_air_experience = 10','B10':research('electronics',.25),'B11':research('light_air',.25),
      'B12':'add_navy_experience = 10','B13':research('ss_tech',.25),'B14':research('electronics',.25),
      'B15':'add_army_experience = 10 add_air_experience = 10 add_navy_experience = 10',
      'F0':idea('defensive_program'),'F1':'add_army_experience = 10','F2':idea('bocage'),
      'F3':'add_air_experience = 10','F4':research('engineers_tech',.25),'F5':'add_army_experience = 10',
      'F6':'add_army_experience = 10','F7':research('cat_anti_air',.25),'F8':research('cat_anti_air',.25),
      'F9':idea('shelter'),'F10':'add_army_experience = 15','F11':research('artillery',.25),
      'F12':idea('watch'),'F13':research('electronics',.25),'F14':research('support_tech',.25),
      'F15':'add_stability = .015','F16':'add_navy_experience = 10','F17':'add_air_experience = 10',
      'F18':idea('coast_guard'),'F19':'add_navy_experience = 10','F20':'add_equipment_to_stockpile = { type = convoy amount = 6 }',
      'F21':research('engineers_tech',.25),'F22':'add_navy_experience = 10','F23':'add_stability = .015',
      'F24':research('electronics',.25),'F25':'add_political_power = 20','F26':'add_army_experience = 15',
      'F27':'add_air_experience = 10 add_navy_experience = 10','F28':research('dd_tech',.25),
      'F29':research('support_tech',.25),'F30':'add_stability = .015','F31':'add_army_experience = 20',
      'F32':'add_navy_experience = 15','F33':'add_political_power = 25','F34':'add_war_support = .025','F35':idea('fortress'),
      'O0':idea('offensive_program'),'O1':'add_army_experience = 10','O2':'add_army_experience = 15',
      'O3':research('medium_air',.25),'O4':'add_navy_experience = 10','O5':'add_army_experience = 15',
      'O6':research('motorized_equipment',.25),'O7':research('armor',.25),'O8':'add_air_experience = 10',
      'O9':'add_navy_experience = 10','O10':research('artillery',.25),'O11':research('cat_anti_tank',.25),
      'O12':research('engineers_tech',.25),'O13':idea('air_ground'),'O14':research('ss_tech',.25),
      'O15':'add_army_experience = 10','O16':research('motorized_equipment',.25),'O17':'add_army_experience = 15',
      'O18':research('cas_bomber',.25),'O19':'add_navy_experience = 15','O20':'add_political_power = 25',
      'O21':idea('mobile'),'O22':'add_army_experience = 10 add_air_experience = 10','O23':research('light_air',.25),
      'O24':research('dd_tech',.25),'O25':research('marine_tech',.25),'O26':'add_equipment_to_stockpile = { type = convoy amount = 6 }',
      'O27':'add_army_experience = 15 add_navy_experience = 10','O28':'add_air_experience = 15',
      'O29':'add_navy_experience = 15','O30':'add_war_support = .025','O31':idea('expedition_supply'),
      'O32':'add_army_experience = 20 add_air_experience = 10','O33':research('support_tech',.25),
      'O34':'add_army_experience = 15 add_air_experience = 15 add_navy_experience = 15','O35':idea('initiative'),
    })
    for c in ['O30','O35']:gates[c]='has_country_flag = sof_brt_war_authorized check_variable = { sof_brt_isolation = 0 }'
    for c in ['F8','F16','F18','F19','F20','F22','F28','F32','O4','O9','O19','O24','O25','O26','O27','O28','O29']:
        gates[c]=gates.get(c,'')+' sof_brt_owned_coast = yes'
    gates['F33']='sof_brt_majority = yes'
    gates['O31']='sof_brt_majority = yes'
    for code in RENAMED:
        descriptions[code]=f'{RENAMED[code]}以半岛乡镇、港口和有限工业为基础。作为两条军事路线共用的专业准备，其奖励只能领取一次；不会绕过中立与战争授权。'
    for row in DATA.strip().splitlines():
        code,title,_,_,_=row.split('|')
        if code.startswith('F'):
            descriptions[code]=f'{title}属于孤立防御纲领。把有限财力用于本土纵深、军需与近海勤务，而非追求域外优势。国策中的地点与作战方案为架空推演。'
        elif code.startswith('O'):
            descriptions[code]=f'{title}属于积极进攻纲领。专业训练和远征补给占用地方资源；组建进攻力量仍不等于取得宣战权。域外战役须另经75席战争授权。地点与作战方案为架空推演。'
        else:
            descriptions[code]=f'{title}服务布列塔尼三军的人员、维修和采购。以地方议会监督为基础，为本土防卫或有限远征提供共同准备。'
    descriptions['F0']='51席支持确立孤立防御纲领，与积极进攻互斥。本土防御提高6%，消费品系数减少1%，计划速度降低5%，船坞建设速度降低5%。保留紧急自卫和议会政治。'
    descriptions['O0']='远征组织法案须66席、勒戈尔热有效支持与外部威胁，审议45日。选择后提高计划速度与计划上限，减少本土防御、民用建设并增加消费品；与孤立防御互斥。战争权仍由单独的75席表决授予。'
    descriptions['N2']='实际拥有并完全控制布雷斯特后扩建一个船坞，解锁本地潜艇制造商。'
    descriptions['N5']='实际拥有并完全控制洛里昂后扩建一个船坞，研究潜艇工艺。'
    descriptions['N8']='议会多数批准且实际拥有并完全控制布雷斯特后，继续扩建一个船坞。'
    descriptions['N9']='积极进攻路线的登陆筹备完成后，研究一支规模有限的布雷斯特海军陆战队。必须实际控制本地海岸。'
    descriptions['N10']='积极进攻路线完成海空登陆掩护并取得全面动员后，新增1份海军入侵计划和2个可登陆师名额。'


def decorate(nodes):
    for n in nodes:
        c=n['code'];n['name']=RENAMED.get(c,n['name'])
        if c in ['N9','N10']:
            n['x']=136
            n['prerequisites'].append(['O25' if c=='N9' else 'O28'])
        if c[0] in 'BFO':n['days']=70 if c in ['B15','F0','F35','O0','O35'] else 35
        if c[0] in 'MABNFO':n['days']=35 if c in ['B15','F0','F35','O0','O35','N2','N5','N8'] else 21
        n['branch']='孤立防御' if c.startswith('F') else '积极进攻' if c.startswith('O') else '共同军备' if c[0] in 'MABN' else '地方政治'


def military_icons(mod,nodes):
    """Reviewed image_gen Breton badges in native two-frame focus sheets."""
    from brittany_art import badge_sheet
    import hashlib
    air={'F3','F7','F8','F12','F13','F17','F27','O3','O8','O13','O18','O23','O28','B9','B10','B11'}
    sea={'F16','F18','F19','F20','F22','F23','F28','F32','O4','O9','O14','O19','O24','O25','O26','O27','O29','B12','B13','B14'}
    supplies={'F9','F14','F15','F24','F25','F29','F30','O15','O16','O31','O33','B3','B4','B6','B7','B8'}
    roots={'F0','F34','F35','O0','O20','O30','O34','O35','B0','B15','M0','M9'}
    result={};art=[];gfx=[]
    for n in nodes:
        c=n['code']
        if c[0] not in 'MABNFO':continue
        route='defence' if c.startswith('F') else 'offence' if c.startswith('O') else 'service'
        role='command' if c in roots else 'air' if c.startswith('A') or c in air else 'sea' if c.startswith('N') or c in sea else 'supply' if c in supplies else 'land'
        key=route+'_'+role;name='GFX_sof_brt_military_'+key;result[c]=name
        if any(a['key']==key for a in art):continue
        sheet=badge_sheet(key)
        rel='gfx/interface/sof_brt/military/'+key+'.dds';p=mod/rel;p.parent.mkdir(parents=True,exist_ok=True);sheet.save(p)
        gfx.append(f'spriteType = {{ name = "{name}" texturefile = "{rel}" noOfFrames = 2 }}')
        art.append(dict(key=key,path=rel,source='art/brittany/generated-v1/'+key+'.png',sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    return result,gfx,art
