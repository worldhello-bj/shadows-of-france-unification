"""Apply the 4.4 shared-tree layout and reward policy without rebuilding majors or MIOs."""
from pathlib import Path
import json,re
from hoi4_script import parse,entries,one,scalar,walk,replace
ROOT=Path(__file__).resolve().parents[1];MOD=ROOT/'mod'
D=json.loads((ROOT/'design/generic-focus-4.4.json').read_text(encoding='utf-8'))
LABELS=dict(stability_factor='稳定度',political_power_gain='每日政治点',compliance_gain='每日顺从增长',required_garrison_factor='驻军需求',resistance_damage_to_garrison='驻军抵抗伤害',production_speed_industrial_complex_factor='民用工厂建设',consumer_goods_factor='消费品工厂系数',industry_repair_factor='工业修复',industrial_capacity_factory='工厂产出',production_speed_arms_factory_factor='军用工厂建设',production_factory_start_efficiency_factor='初始生产效率',production_speed_infrastructure_factor='基础设施建设',production_speed_rail_way_factor='铁路建设',research_speed_factor='研究速度',production_factory_efficiency_gain_factor='生产效率增长',line_change_production_efficiency_factor='生产线转换效率保留',industrial_capacity_dockyard='船坞产出',production_speed_dockyard_factor='船坞建设',repair_speed_factor='舰船维修',air_cas_efficiency='近距支援效率',air_mission_efficiency='空军任务效率',air_fuel_consumption_factor='空军燃油消耗',air_nav_efficiency='海军打击效率',naval_detection='海军探测',convoy_escort_efficiency='运输船护航效率',screening_efficiency='屏卫效率',navy_fuel_consumption_factor='海军燃油消耗',naval_speed_factor='舰船速度',convoy_raiding_efficiency_factor='破交效率',fuel_gain_factor='燃油获取',max_fuel_factor='燃油储量',army_fuel_consumption_factor='陆军燃油消耗',local_resources_factor='资源开采效率',war_support_weekly='每周战争支持',mobilization_speed='动员速度',command_power_gain_mult='指挥点获取',weekly_manpower='每周人力',training_time_factor='训练时间',army_morale_factor='陆军恢复速度',experience_gain_army_factor='陆军经验获取',army_org='陆军组织度',max_dig_in='最大堑壕',planning_speed='计划速度',land_reinforce_rate='增援率',special_forces_cap='特种部队容量',special_forces_min='最低特种营数',modifier_army_sub_unit_mountaineers_attack_factor='山地步兵攻击',modifier_army_sub_unit_marine_attack_factor='海军陆战队攻击',modifier_army_sub_unit_marine_defence_factor='海军陆战队防御',non_core_manpower='非核心人力系数',conscription_factor='适役人口系数',experience_gain_army_unit_factor='部队经验增长',special_forces_attack_factor='特种部队攻击',no_supply_grace='无补给宽限小时',out_of_supply_factor='断补给惩罚',modifier_army_sub_unit_mountaineers_speed_factor='山地步兵速度',org_loss_when_moving='移动组织度损失')
FLAT={'political_power_gain','compliance_gain','weekly_manpower','army_org','max_dig_in','special_forces_min','no_supply_grace','naval_invasion_division_cap','naval_invasion_plan_cap'}
def fmt(v):return f'{v:g}'
def stats_text(values):
 return '；'.join(LABELS.get(k,k)+' '+('+' if v>=0 else '')+fmt(v if k in FLAT else round(v*100,5))+('' if k in FLAT else '%') for k,v in values.items())+'。'
def read(rel):return (MOD/rel).read_text(encoding='utf-8-sig')
def put(rel,text,bom=False):
 p=MOD/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text.rstrip()+'\n',encoding='utf-8-sig' if bom else 'utf-8',newline='\r\n')
def f(s):return 'SOF_GENERIC_'+s
def update_field(text,rows,key,value):
 found=entries(rows,key)
 if found:return replace(text,[(n.start,n.end,value) for n in found])
 return text[:text.rfind('}')]+'\n '+value+'\n'+text[text.rfind('}'):]
def focus_tree():
 rel='common/national_focus/sof_mrs_shared_generic.txt';source=read(rel);changes=[]
 for node in entries(parse(source),'shared_focus'):
  ident=scalar(node.value,'id');policy=D['focuses'][ident];block=source[node.start:node.end]
  for key in ['relative_position_id','offset']:
   rows=one(parse(block),'shared_focus').value
   block=replace(block,[(n.start,n.end,'') for n in entries(rows,key)])
  for key in ['x','y','cost']:
   rows=one(parse(block),'shared_focus').value;block=update_field(block,rows,key,f'{key} = {policy[key]}')
  rows=one(parse(block),'shared_focus').value
  block=update_field(block,rows,'offset','offset = { x = 80 y = 0 trigger = { original_tag = MRS } }')
  if 'available' in policy:
   rows=one(parse(block),'shared_focus').value;block=update_field(block,rows,'available','available = { '+policy['available']+' }')
  if 'parents' in policy:
   rows=one(parse(block),'shared_focus').value;replacement=' '.join('prerequisite = { '+' '.join('focus = '+k for k in group)+' }' for group in policy['parents'])
   prev=entries(rows,'prerequisite');block=replace(block,[(n.start,n.end,replacement if j==0 else '') for j,n in enumerate(prev)])
  rows=one(parse(block),'shared_focus').value;reward=one(rows,'completion_reward');rewardtext=block[reward.start:reward.end]
  short=ident.removeprefix('SOF_GENERIC_')
  if short in ['arrondissement','department','province','region','state','nation']:
   value=dict(arrondissement=50,department=60,province=75,region=100,state=125,nation=150)[short]
   rewardtext=re.sub(r'add_political_power\s*=\s*\d+',f'add_political_power = {value}',rewardtext)
  if short in D['research_slots']:
   r=D['research_slots'][short];cap=r['cap'];limit=f'num_of_factories > {r["factories"]-1} amount_research_slots < {cap}'
   if short=='advanced_research':limit='num_of_factories > 15 OR = { AND = { NOT = { original_tag = MRS } amount_research_slots < 5 } AND = { original_tag = MRS amount_research_slots < 4 } }'
   rewardtext='completion_reward = { if = { limit = { '+limit+' } add_research_slot = 1 } sofzh_reward_sof_generic_'+short+' = yes }'
  if short=='250_naval_bombers':
   rewardtext='''completion_reward = { if = { limit = { has_dlc = "By Blood Alone" has_tech = iw_small_airframe has_tech = engines_1 has_tech = air_torpedoe_1 }
 create_equipment_variant = { name = "海岸巡逻鱼雷机" type = small_plane_naval_bomber_airframe_0 modules = { fixed_main_weapon_slot = torpedo_mounting engine_type_slot = engine_1_1x special_type_slot_1 = empty } }
 add_equipment_to_stockpile = { type = small_plane_naval_bomber_airframe_0 amount = 16 producer = ROOT variant_name = "海岸巡逻鱼雷机" }
 } else_if = { limit = { NOT = { has_dlc = "By Blood Alone" } has_tech = naval_bomber1 } add_equipment_to_stockpile = { type = nav_bomber_equipment_1 amount = 16 } }
 sofzh_reward_sof_generic_250_naval_bombers = yes }'''
  if short in ['military_industry','military_industrial_complex','advanced_industrial_technology','advanced_fighters','advanced_air_doctrine','advanced_naval_doctrine','nuclear_weapons','rocketry']:
   bonus=dict(military_industry='army_experience = 15',military_industrial_complex='army_experience = 25',advanced_industrial_technology='add_tech_bonus = { name = sof_generic_industry_440 bonus = 0.5 uses = 1 category = industry }',advanced_fighters='air_experience = 15',advanced_air_doctrine='air_experience = 15',advanced_naval_doctrine='navy_experience = 15',nuclear_weapons='add_tech_bonus = { name = sof_generic_nuclear_440 bonus = 1 uses = 1 category = nuclear }',rocketry='add_tech_bonus = { name = sof_generic_rockets_440 bonus = 0.5 uses = 1 category = rocketry }')[short]
   if 'sof_generic_focus_bonus_'+short not in rewardtext:
    rewardtext=rewardtext[:-1]+'\n # sof_generic_focus_bonus_'+short+'\n '+bonus+'\n}'
  block=replace(block,[(reward.start,reward.end,rewardtext)])
  changes.append((node.start,node.end,block))
 put(rel,replace(source,changes))
 # Eight shared roots retained; shortcuts are native focus-tree navigation.
 roots=[n.value for n in entries(one(parse(read('common/national_focus/SoF_generic.txt')),'focus_tree').value,'shared_focus')]
 shortcuts=[('治理',f('arrondissement')),('工业',f('basic_infrastructure')),('动员',f('3_infantry_divisions')),('陆军',f('basic_small_arms')),('空军',f('basic_fighters')),('海军',f('2_naval_dockyards')),('科研',f('basic_research')),('矿业','SOF_MINING_resource_survey'),('统一','SOF_UNIFY_national_mandate')]
 lines=['focus_tree = { id = sof_generic country = { factor = 1 } default = yes', 'continuous_focus_position = { x = 50 y = 2650 }','initial_show_position = { focus = SOF_GENERIC_arrondissement }']
 for label,target in shortcuts:lines.append('shortcut = { name = sof_generic_shortcut_'+target+' target = '+target+' scroll_wheel_factor = 0.65 }')
 lines+=['shared_focus = '+k for k in roots]+['}'];put('common/national_focus/SoF_generic.txt','\n'.join(lines))
 return shortcuts
def ideas():
 rel='common/ideas/sofzh_rewards.txt';source=read(rel);rows=one(one(parse(source),'ideas').value,'country');changes=[];new=[]
 for n in rows.value:
  match=re.fullmatch(r'sofzh_reward_(.+)_(\d)',n.key or '')
  if not match:continue
  family,tier=match[1],int(match[2]);mod=entries(n.value,'modifier')
  if family in D['modifier_series'] and not (family=='administration' and tier>3):
   values={k:v[tier-1] for k,v in D['modifier_series'][family].items()};m=mod[0]
   changes.append((m.start,m.end,'modifier = { '+' '.join(k+' = '+fmt(v) for k,v in values.items())+' }'))
  if family in D['equipment_cost_series']:
   for equip in entries(n.value,'equipment_bonus'):
    for b in walk(equip.value):
     if b.key=='build_cost_ic':changes.append((b.start,b.end,'build_cost_ic = '+fmt(D['equipment_cost_series'][family][tier-1])))
 for tier in [4,5,6]:
  values={k:v[tier-1] for k,v in D['modifier_series']['administration'].items()}
  ident='sofzh_reward_administration_'+str(tier)
  if not entries(rows.value,ident):
   new.append(ident+' = { allowed = { always = no } allowed_civil_war = { always = no } removal_cost = -1 picture = sofzh_spirit_v1_sofzh_reward_administration_3 modifier = { '+' '.join(k+' = '+fmt(v) for k,v in values.items())+' } }')
  else:
   m=one(one(rows.value,ident).value,'modifier');changes.append((m.start,m.end,'modifier = { '+' '.join(k+' = '+fmt(v) for k,v in values.items())+' }'))
 if new:changes.append((rows.end-1,rows.end-1,'\n'+'\n'.join(new)+'\n'))
 put(rel,replace(source,changes))
 rel='common/ideas/fra_generic.txt';source=read(rel);changes=[]
 for n in one(one(parse(source),'ideas').value,'country').value:
  if n.key in D['legacy_modifiers']:
   m=one(n.value,'modifier');values=D['legacy_modifiers'][n.key];changes.append((m.start,m.end,'modifier = { '+' '.join(k+' = '+fmt(v) for k,v in values.items())+' }'))
 put(rel,replace(source,changes))
def rewards():
 from idea_tier_swap import hidden_cleanup,tier_swap
 effects=[];rel='common/scripted_effects/sofzh_rewards.txt';source=read(rel);changes=[]
 peers={k:'sofzh_specialist_'+k for k in ['administration','civil_industry','mil_industry','engineering']}
 for k in ['infantry','recruitment','staff','special_forces','motorized','armor','artillery','air_defence','air_support','naval_air','dockyards','surface_navy','submarines','carrier','landing','fuel','recovery']:peers[k]='sofzh_dedicated_'+k
 families={m[1] for r in walk(parse(source)) if r.key and (m:=re.fullmatch(r'sof_generic_upgrade_(.+)_[1-6]',r.key))}
 allowed={'if','else_if','else','limit','NOT','OR','AND','has_idea','add_ideas','swap_ideas','remove_idea','add_idea','sof_mrs_red_public_allowed'}
 for n in parse(source):
  # Refactor pure tier-grant routines only; leave geography, temporary rewards and existing route logic intact.
  if not isinstance(n.value,list) or any(r.key not in allowed for r in walk(n.value)):continue
  grants=[r.value for r in walk(n.value) if r.key in ['add_ideas','add_idea'] and isinstance(r.value,str) and re.fullmatch(r'sofzh_reward_.+_[123]',r.value)]
  match=[re.fullmatch(r'sofzh_reward_(.+)_([123])',k) for k in grants]
  fam={m[1] for m in match}
  if len(fam)!=1:continue
  family=fam.pop();tier=min(int(m[2]) for m in match)
  if n.key.startswith('sofzh_reward_sof_generic_'):
   short=n.key.removeprefix('sofzh_reward_sof_generic_')
   if short in ['arrondissement','department','province','region','state','nation']:family='administration';tier=['arrondissement','department','province','region','state','nation'].index(short)+1
   if short=='civilian_industry':tier=3
   if short=='basic_industry':tier=1
  families.add(family);body=f'sof_generic_upgrade_{family}_{tier} = yes'
  guarded=any(r.key=='sof_mrs_red_public_allowed' for r in walk(n.value))
  if guarded:body='if = { limit = { sof_mrs_red_public_allowed = yes } '+body+' }'
  if n.key=='sofzh_reward_sof_generic_propaganda_campaigns':body='add_war_support = 0.03' # Political outreach cannot skip three administration levels.
  if n.key=='sofzh_reward_sof_generic_basic_industry':body+=' if = { limit = { sof_mrs_red_public_allowed = yes } sof_generic_upgrade_civil_industry_1 = yes }';families.add('civil_industry')
  if n.key=='sofzh_reward_sof_generic_improved_industry':body+=' if = { limit = { sof_mrs_red_public_allowed = yes } sof_generic_upgrade_civil_industry_2 = yes }'
  changes.append((n.start,n.end,n.key+' = { '+body+' }'))
 put(rel,replace(source,changes))
 for family in sorted(families):
  levels=6 if family=='administration' else 3
  names=['sofzh_reward_'+family+'_'+str(j) for j in range(1,levels+1)];peer=peers.get(family)
  for tier in range(1,levels+1):
   high=' '.join('has_idea = '+k for k in names[tier:]);remove=hidden_cleanup(names)
   # Route updates must never silently downgrade a higher generic tier or stack dedicated and generic counterparts.
   target=names[tier-1];body=''
   if peer and tier<=3:
    promote=''
    for j in range(3,tier,-1):promote+=('if' if j==3 else 'else_if')+' = { limit = { has_idea = '+names[j-1]+' } '+peer+'_'+str(j)+' = yes } '
    if promote:promote+='else = { '+peer+'_'+str(tier)+' = yes } '
    else:promote=peer+'_'+str(tier)+' = yes '
    body='if = { limit = { OR = { '+' '.join('has_idea = '+peer+'_'+str(j) for j in [1,2,3])+' } } '+promote+remove+' } else = { '
   candidates=names+([peer+'_'+str(j) for j in [1,2,3]] if peer and tier>3 else [])
   upgrade=('if = { limit = { NOT = { OR = { '+high+' has_idea = '+target+' } } } '+tier_swap(target,candidates)+' }')
   body+=upgrade
   if peer and tier<=3:body+=' }'
   if family=='administration' and tier<=3:
    body='if = { limit = { OR = { '+' '.join('has_idea = '+names[j-1] for j in [4,5,6])+' } } '+hidden_cleanup(peer+'_'+str(j) for j in [1,2,3])+' } else = { '+body+' }'
   effects.append('sof_generic_upgrade_'+family+'_'+str(tier)+' = { '+body+' sof_generic_normalize_profiles_440 = yes }')
 # Clean existing accidental multi-tier/peer stacks; never replay factories, PP, units or technology bonuses.
 normalize=[]
 for family in sorted(families):
  cap=6 if family=='administration' else 3;peer=peers.get(family)
  for j in range(cap,0,-1):
   target='sofzh_reward_'+family+'_'+str(j)
   condition='has_idea = '+target
   if peer and j<=3:condition='OR = { has_idea = '+target+' has_idea = '+peer+'_'+str(j)+' }'
   rm=[]
   for k in range(1,j):rm.append('remove_ideas = sofzh_reward_'+family+'_'+str(k))
   if peer:
    if j>3:rm += ['remove_ideas = '+peer+'_'+str(k) for k in [1,2,3]]
    else:
     rm += ['remove_ideas = '+peer+'_'+str(k) for k in range(1,j)]
     rm.append('if = { limit = { has_idea = '+peer+'_'+str(j)+' } remove_ideas = '+target+' }')
   normalize.append(('if' if j==cap else 'else_if')+' = { limit = { '+condition+' } '+' '.join(rm)+' }')
 effects.append('sof_generic_normalize_profiles_440 = { hidden_effect = { '+' '.join(normalize)+' } }')
 admin=[]
 for j,short in reversed(list(enumerate(['arrondissement','department','province','region','state','nation'],1))):admin.append(('if' if j==6 else 'else_if')+' = { limit = { has_completed_focus = '+f(short)+' } sof_generic_upgrade_administration_'+str(j)+' = yes }')
 effects.append('sof_generic_migrate_440 = { if = { limit = { NOT = { has_country_flag = sof_generic_migrated_440 } OR = { has_focus_tree = sof_generic has_focus_tree = sof_mrs_red has_completed_focus = SOF_GENERIC_arrondissement } } '+' '.join(admin)+' sof_generic_normalize_profiles_440 = yes set_country_flag = sof_generic_migrated_440 } }')
 put('common/scripted_effects/sof_generic_440.txt','\n'.join(effects))
 put('common/on_actions/sof_generic_440.txt','on_actions = { on_startup = { effect = { every_country = { sof_generic_migrate_440 = yes } } } on_weekly = { effect = { sof_generic_migrate_440 = yes } } }')
 # Original specialist routines cover three tiers. A six-tier administration cannot gain a second administration spirit.
 rel='common/scripted_effects/sofzh_progression.txt';source=read(rel);changes=[]
 for n in parse(source):
  if n.key in ['sofzh_specialist_administration_'+str(j) for j in [1,2,3]] and not any(r.key=='has_idea' and r.value=='sofzh_reward_administration_6' for r in walk(n.value)):
   raw=source[n.start:n.end];opening=raw.index('{')+1
   raw=raw[:opening]+' if = { limit = { NOT = { OR = { '+' '.join('has_idea = sofzh_reward_administration_'+str(j) for j in [4,5,6])+' } } } '+raw[opening:-1]+' } }';changes.append((n.start,n.end,raw))
 put(rel,replace(source,changes))
 return families
def localization(shortcuts):
 # Replace numeric descriptions in their original file, avoiding ambiguous duplicate localization overrides.
 rel='localisation/simp_chinese/replace/sofzh_rewards_l_simp_chinese.yml';source=read(rel)
 ideasource=read('common/ideas/sofzh_rewards.txt');idea_rows=one(one(parse(ideasource),'ideas').value,'country').value
 for n in idea_rows:
  m=re.fullmatch(r'sofzh_reward_(.+)_(\d)',n.key or '')
  if not m:continue
  family,tier=m[1],int(m[2]);changed=family in D['modifier_series'] or family in D['equipment_cost_series']
  if not changed:continue
  mod=entries(n.value,'modifier');values={k.key:float(k.value) for k in mod[0].value} if mod else {}
  desc=stats_text(values)
  if family in D['equipment_cost_series']:desc+='本系列相关装备生产成本 '+fmt(D['equipment_cost_series'][family][tier-1]*100)+'%。'
  desc+='\\n同类精神替换升级，通用与专属版本互斥保留；较低阶段不会使较高阶段降级。'
  if family=='administration':name='行政协约·'+['地方','省级','跨省','大区','邦国','全国'][tier-1]
  else:
   old=re.search(r'(?m)^ '+re.escape(n.key)+r':0 "(.*)"$',source);name=old[1] if old else n.key
  for key,value in [(n.key,name),(n.key+'_desc',desc)]:
   line=' '+key+':0 "'+value+'"';pattern=r'(?m)^ '+re.escape(key)+r':\d* ".*"$'
   if re.search(pattern,source):source=re.sub(pattern,lambda _:line,source)
   else:source+='\n'+line
 put(rel,source,True)
 rel='localisation/simp_chinese/replace/sofzh_military_balance_l_simp_chinese.yml';source=read(rel)
 source=source.replace('同阶军事系列基础数值比通用提高15%；登陆容量取整。','专属军事系列保留独立强化数值；登陆容量取整。');put(rel,source,True)
 loc=['l_simp_chinese:']
 for label,target in shortcuts:loc.append(' sof_generic_shortcut_'+target+':0 "'+label+'"')
 loc+=[' sof_generic_naval_air_tech_tt:0 "拥有鱼雷机所需科技：小型机身、发动机和航空鱼雷（无BBA时为海军轰炸机）。"',' sof_generic_industry_440:0 "全国工业标准化"',' sof_generic_nuclear_440:0 "核研究专项"',' sof_generic_rockets_440:0 "火箭试验计划"']
 # Edit focus descriptions at their original definition so the actual game has one authoritative key.
 allfiles={p:p.read_text(encoding='utf-8-sig') for p in (MOD/'localisation/simp_chinese/replace').glob('*.yml')}
 originalnames={}
 for p,t in allfiles.items():
  for key,name in re.findall(r'(?m)^ (SOF_GENERIC_\w+):\d* "((?:[^"\\]|\\.)*)"',t):originalnames[key]=name
 result=[]
 for ident,policy in D['focuses'].items():
  if 'available' not in policy:continue
  base=policy.get('names') or originalnames.get(ident,ident);days=policy['cost']*7;gate=policy.get('factories',0)
  story={'行政与治理':'建立税籍、财政与地方协调制度，使新接管区域逐步融入共同政府。','工业与资源':'扩充工人培训、基础设施和工业协作，让地方工业具备持续生产能力。','军队与动员':'从地方部队建立动员、训练与军官体系，形成可靠的正规军。','陆军装备与学说':'以实际装备能力安排研究、试制和战术训练，形成可持续的军备体系。','空军建设':'协调飞行学校、飞机制造与地勤保障，把有限资源投入清晰的空军任务。','海军建设':'依托自有海岸与船坞发展舰队，协调造船、补给和海上战术。','科研体系':'把研究机构、专业人员和试验设施连成稳定的科研网络。'}[policy['section']]
  desc=policy.get('narrative') or story
  desc+='\\n建设周期：'+str(days)+'日。'
  if gate:desc+='工业规模：至少'+str(gate)+'座工厂。'
  short=ident.removeprefix('SOF_GENERIC_')
  if short in ['arrondissement','department','province','region','state','nation']:
   tier=['arrondissement','department','province','region','state','nation'].index(short)+1;desc+='\\n行政精神提升至第'+str(tier)+'级：'+stats_text({k:v[tier-1] for k,v in D['modifier_series']['administration'].items()})
  if short in D['research_slots']:
   r=D['research_slots'][short];desc+='\\n符合工厂条件时增加1个科研槽，最多'+str(r['cap'])+'槽（马赛最多4槽）。达到槽位上限后仍可完成本国策并领取科研精神。'
  if short in ['oil_production','tungsten_production','steel_production','aluminium_production']:desc+='\\n扩产仍要求控制指定矿区；其他矿种的国策不会成为前置条件。'
  if short=='synthethic_rubber_production':desc+='\\n合成工业独立于指定天然矿区，不要求先占领油田或钨矿。'
  if short=='250_naval_bombers':desc+='\\n接收16架海军鱼雷机；BBA机身与传统飞机分别发放对应装备。'
  desc+='\\n同类永久精神只保留最高阶段；完成后的实际奖励以国策效果提示为准。'
  for key,value in [(ident,base),(ident+'_desc',desc)]:
   # Match exactly the localization parser's quoted grammar; original values can contain escaped quotation marks.
   pattern=r'(?m)^ '+re.escape(key)+r':\d* "(?:[^"\\]|\\.)*"$';matches=[p for p,t in allfiles.items() if re.search(pattern,t)]
   assert len(matches)<=1,(key,matches)
   line=' '+key+':0 "'+value+'"'
   if matches:p=matches[0];allfiles[p]=re.sub(pattern,lambda _:line,allfiles[p])
   else:loc.append(line)
  result.append(dict(id=ident,name=base,days=days,section=policy['section'],factories=gate))
 for p,t in allfiles.items():
  # Only save files whose focus entries actually changed; do not rewrite unrelated work.
  if t!=p.read_text(encoding='utf-8-sig'):p.write_text(t.rstrip()+'\n',encoding='utf-8-sig',newline='\r\n')
 for key,values in D['legacy_modifiers'].items():
  desc=stats_text(values)+'\\n本制度与通用成长精神共同生效；科研、产出和装备减价已按实际叠加重新分配。'
  pattern=r'(?m)^ '+re.escape(key+'_desc')+r':\d* "(?:[^"\\]|\\.)*"$'
  matches=[p for p in (MOD/'localisation/simp_chinese/replace').glob('*.yml') if re.search(pattern,p.read_text(encoding='utf-8-sig'))]
  assert len(matches)<=1,(key,matches)
  if matches:
   p=matches[0];t=p.read_text(encoding='utf-8-sig');t=re.sub(pattern,lambda _:' '+key+'_desc:0 "'+desc+'"',t);p.write_text(t,encoding='utf-8-sig',newline='\r\n')
  else:loc.append(' '+key+'_desc:0 "'+desc+'"')
 put('localisation/simp_chinese/replace/sof_generic_440_l_simp_chinese.yml','\n'.join(loc),True)
 (ROOT/'design/generic-focus-display.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
def main():
 shortcuts=focus_tree();ideas();rewards();localization(shortcuts);print('Built generic focus 4.4.0; 153 stable IDs; majors and MIO assets untouched.')
if __name__=='__main__':main()
