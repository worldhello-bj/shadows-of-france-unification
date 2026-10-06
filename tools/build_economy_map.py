"""Bounded resource and starting-industry edits; retain all other state history."""
from pathlib import Path
import json,re,csv,io,hashlib
from hoi4_script import parse,one,entries,scalar,walk,replace
ROOT=Path(__file__).resolve().parents[1];MOD=ROOT/'mod'
FLAG='sof_economy_resources_450'

def load():return json.loads((ROOT/'design/economy-map-4.5.json').read_text(encoding='utf-8'))
def put(path,text,bom=False):
 p=MOD/path;p.parent.mkdir(parents=True,exist_ok=True)
 p.write_text(text.rstrip()+'\n',encoding='utf-8-sig' if bom else 'utf-8',newline='\r\n')
def edit_fields(text,rows,values,parent):
 edits=[];missing=[]
 for key,value in values.items():
  found=entries(rows,key)
  assert len(found)<=1,key
  if found:edits.append((found[0].start,found[0].end,f'{key} = {value}'))
  elif value:missing.append(f'\n\t\t\t{key} = {value}')
 if missing:edits.append((parent.end-1,parent.end-1,''.join(missing)+'\n\t\t'))
 return replace(text,edits)

def build_states(d):
 for r in d['states']:
  text=(MOD/r['path']).read_text(encoding='utf-8-sig');s=one(parse(text),'state')
  h=one(s.value,'history');blocks=entries(h.value,'buildings');assert len(blocks)<=1
  if blocks:text=edit_fields(text,blocks[0].value,r['factories'],blocks[0])
  elif r['factory_budget']:
   insert='\n\t\tbuildings = { '+ ' '.join(f'{k} = {v}' for k,v in r['factories'].items() if v)+' }\n'
   text=replace(text,[(h.end-1,h.end-1,insert)])
  s=one(parse(text),'state');h=one(s.value,'history')
  extras=entries(h.value,'add_extra_state_shared_building_slots')
  assert sum(int(n.value) for n in extras) in [0,r['removed_compensation_slots']]
  changes=[(n.start,n.end,'') for n in extras]
  if not any(n.value==FLAG for n in entries(h.value,'set_state_flag')):
   changes.append((h.end-1,h.end-1,f'\n\t\t# SOF 4.5.0: this campaign already uses the new resource base.\n\t\tset_state_flag = {FLAG}\n\t'))
  text=replace(text,changes)
  text=re.sub(r'(?m)^.*# Retain existing industry after population-based classification\.\s*\n','',text)
  s=one(parse(text),'state');old=entries(s.value,'resources');assert len(old)<=1
  new='resources = { '+' '.join(f'{t} = {n}' for t,n in r['resources'].items())+' }' if r['resources'] else ''
  if old:text=replace(text,[(old[0].start,old[0].end,new)])
  elif new:text=replace(text,[(s.end-1,s.end-1,'\n\t'+new+'\n')])
  text=re.sub(r'(?m)^.*# SOF 2\.10\.0 local gameplay supply; historically based nodes documented separately\.\s*\n','',text)
  put(r['path'],text)

def retire_floors(d):
 # Keep the original airport, equipment-initialization and victory-point repair
 # instructions. Only retire the obsolete resource additions.
 for rel in d['legacy_files'][:3]:
  text=(MOD/rel).read_text(encoding='utf-8-sig')
  changes=[(n.start,n.end,'') for n in walk(parse(text)) if n.key=='add_resource']
  text=replace(text,changes)
  text=re.sub(r'(?m)^\s*\d+\s*=\s*\{\s*\}\s*\n','',text)
  put(rel,text)
 fresh='sof_economy_map_is_current = yes'
 scope='is_ai = no capital_scope = { sofzh_logistics_french_state = yes }'
 put('common/decisions/categories/sofzh_resource_map.txt',f'''sofzh_resource_map_category = {{ icon = generic_industry
 visible = {{ {scope} OR = {{ NOT = {{ {fresh} }} NOT = {{ has_global_flag = sofzh_resource_towns_2100 }} }} }}
}}''')
 towns=scope+' NOT = { has_global_flag = sofzh_resource_towns_2100 }'
 put('common/decisions/sofzh_resource_map.txt',f'''sofzh_resource_map_category = {{
 sofzh_resource_map_refresh = {{ icon = generic_industry cost = 0
  visible = {{ {towns} }}
  available = {{ custom_trigger_tooltip = {{ tooltip = sofzh_resource_map_refresh_available_tt {towns} }} }}
  complete_effect = {{ hidden_effect = {{ sofzh_resource_map_refresh_apply = yes }} custom_effect_tooltip = sofzh_resource_map_refresh_tt }}
  ai_will_do = {{ factor = 0 }}
 }}
}}''')
 replacements={
 'localisation/simp_chinese/replace/sofzh_resource_map_l_simp_chinese.yml':{
 'sofzh_resource_map_refresh':'更新小城镇标记',
 'sofzh_resource_map_refresh_desc':'一次性补齐旧版小城镇胜利点。地方煤钢及战略资源低保已经取消；资源使用新版地区分配。此项只修复城镇，不增加资源或工厂。',
 'sofzh_resource_map_refresh_available_tt':'当前存档尚未补全小城镇标记。',
 'sofzh_resource_map_refresh_tt':'补齐小城镇标记；不会恢复旧版资源低保。'},
 'localisation/simp_chinese/replace/sofzh_combined_arms_l_simp_chinese.yml':{
 'sofzh_strategic_refresh':'更新陆空军基础',
 'sofzh_strategic_refresh_desc':'旧版分散战略资源供给已经停用。保留原有基础机场和早期陆空装备设计的修复；资源重分配使用新版专门决议。',
 'sofzh_strategic_refresh_tt':'修复陆空军基础；不会恢复旧版战略资源低保。'},
 'localisation/simp_chinese/replace/sofzh_oil_supply_l_simp_chinese.yml':{
 'sofzh_oil_supply_refresh':'旧版石油供给已停用',
 'sofzh_oil_supply_refresh_desc':'各大区石油低保已经取消。石油集中到阿基坦、巴黎盆地、阿尔萨斯和少数南部产区；旧档使用新版资源重分配。',
 'sofzh_oil_supply_refresh_tt':'不会增加旧版石油低保。'}}
 for rel,values in replacements.items():
  text=(MOD/rel).read_text(encoding='utf-8-sig')
  for key,value in values.items():
   text,count=re.subn(r'(?m)^ '+re.escape(key)+r':\d* ".*"$',f' {key}:0 "{value}"',text)
   assert count==1,key
  put(rel,text,True)

def migration(d):
 put('common/scripted_triggers/sof_economy_map_450.txt','sof_economy_map_is_current = {\n'+
  ''.join(f" {r['id']} = {{ has_state_flag = {FLAG} }}\n" for r in d['states'])+'}')
 chunks=[]
 for r in d['states']:
  changes=[]
  for t in d['types']:
   delta=r['resources'].get(t,0)-r['previous_resources'].get(t,0)
   if delta:changes.append(f'   add_resource = {{ type = {t} amount = {delta} }}\n')
  chunks.append(f" {r['id']} = {{ if = {{ limit = {{ NOT = {{ has_state_flag = {FLAG} }} }}\n"+
   ''.join(changes)+f'   set_state_flag = {FLAG}\n }} }}\n')
 put('common/scripted_effects/sof_economy_map_450.txt',f'''# Resource migration is explicit. Existing factories/slots are never changed.
sof_economy_retire_supply_450 = {{
 set_global_flag = sofzh_resource_map_2100
 set_global_flag = sofzh_strategic_supply_2110
 set_global_flag = sofzh_oil_supply_2111
}}
sof_economy_resources_migrate_450 = {{
 if = {{ limit = {{ is_ai = no NOT = {{ sof_economy_map_is_current = yes }} }}
{''.join(chunks)}  sof_economy_retire_supply_450 = yes
  set_global_flag = {FLAG}
 }}
}}
sof_economy_startup_450 = {{
 sof_economy_retire_supply_450 = yes
 if = {{ limit = {{ sof_economy_map_is_current = yes }} set_global_flag = {FLAG} }}
}}''')
 put('common/on_actions/sof_economy_map_450.txt','on_actions = { on_startup = { effect = { sof_economy_startup_450 = yes } } }')
 eligible='is_ai = no capital_scope = { sofzh_logistics_french_state = yes } NOT = { sof_economy_map_is_current = yes }'
 put('common/decisions/sof_economy_map_450.txt',f'''sofzh_resource_map_category = {{
 sof_economy_resources_migrate = {{ icon = generic_industry cost = 0
  visible = {{ {eligible} }}
  available = {{ custom_trigger_tooltip = {{ tooltip = sof_economy_resources_migrate_available_tt {eligible} }} }}
  complete_effect = {{ hidden_effect = {{ sof_economy_resources_migrate_450 = yes }} custom_effect_tooltip = sof_economy_resources_migrate_tt }}
  ai_will_do = {{ factor = 0 }}
 }}
}}''')
 locale=dict(sof_economy_resources_migrate='旧档资源重分配',
  sof_economy_resources_migrate_desc='适用于采用旧版分散供给的存档。将全法国的基础煤炭、钢铁、铝、油、橡胶、钨、铬调整为新的集中产区配置；取消各地低保。只应用一次基础差额，保留已经追加的矿业产出。现有工厂和建筑槽位不变；80%初始工厂配置需新开局。更早、尚未采用完整旧供给的存档建议新开局。',
  sof_economy_resources_migrate_available_tt='当前存档尚未使用新版集中资源分配；由法国玩家执行一次。',
  sof_economy_resources_migrate_tt='全法国资源基础重分配一次：煤炭1500、钢铁1400、铝1100、石油1000、橡胶850、钨1000、铬1000。保留矿业追加；不会修改旧档工厂、槽位、胜利点或归属。')
 put('localisation/simp_chinese/replace/sof_economy_map_450_l_simp_chinese.yml','l_simp_chinese:\n'+''.join(f' {k}:0 "{v}"\n' for k,v in locale.items()),True)

def documents(d):
 out=ROOT/'docs';out.mkdir(exist_ok=True)
 buffer=io.StringIO(newline='');w=csv.writer(buffer)
 w.writerow(['州ID','名称','大区','基础槽位','初始工厂','民工','军工','船坞','煤炭','钢铁','铝','石油','橡胶','钨','铬'])
 for s in d['states']:
  w.writerow([s['id'],s['name'],s['region'],s['slots'],s['factory_budget'],s['factories']['industrial_complex'],s['factories']['arms_factory'],s['factories']['dockyard'],*[s['resources'].get(t,0) for t in ['coal','steel','aluminium','oil','rubber','tungsten','chromium']]])
 (out/'ECONOMY-4.5.csv').write_text(buffer.getvalue(),encoding='utf-8-sig',newline='')
 summary=d['summary']
 rows='\n'.join(f"| {d['labels'][t]} | {summary['totals'][t]} | {summary['carriers'][t]} | {d['resource_profiles'][t]} |" for t in ['coal','steel','aluminium','oil','rubber','tungsten','chromium'])
 doc=f'''# 法国地区资源与初始工业 · 4.5.0

法国342州取消地方煤钢低保、分散战略资源低保和大区石油低保。80州拥有基础战略资源，262州无基础战略资源；资源缺口通过贸易和争夺矿区解决，各大区不再自动得到等量配额。

| 资源 | 法国基础总量 | 产区州数 | 地区方向 |
|---|---:|---:|---|
{rows}

所有数值是游戏基础供给单位，不能作为1936年矿藏或吨位引用。煤钢与部分矿区保留地理方向；各矿区产能放大、提前开发、铬矿扩展及橡胶化工供给属于经用户许可的架空配置。橡胶基础供给与后来建设的合成炼油厂分别计算。科技、基建、民族精神、贸易法、占领和国策追加会改变游戏中的实际可用产量。

初始工厂按 `floor(当地基础共享槽位 × 0.8)` 设置，民工、军工、船坞合计计入预算；保留已有地区类别和槽位倍率，移除514个“保住五座工厂”的补偿槽位。普通州3槽→2座、4槽→3座、5槽→4座；大城市8槽→6座；巴黎12槽→9座。因工厂必须为整数，实际比例可低于80%。无有效共享槽位的小岛不塞入工厂。初始民工/军工沿用约3:2的结构，既有初始船坞为0；本轮没有额外赠送船坞。

法国初始工厂从1640调整到810（485民工、325军工），共有0、1、2、3、4、6、9座七档。机场、港口、基础设施、铁路、补给节点、人口、胜利点、核心和归属保留。原有矿业国策及其逐级工程标记保留。开局没有工业科技或经济精神提供额外槽位；后续科技和制度可以正常扩大槽位。

新开局直接读取新版历史。采用完整旧版分散供给的存档可在“法国资源与城镇”使用“旧档资源重分配”，按州一次性应用新旧基础差额，保留已追加的矿业奖励。州级标记保护部分执行和重复执行；新档已带标记，不会再次增加资源。旧档工厂和槽位不变，80%初始配置需要新开局。更早或自行改过基础资源的存档不在差额迁移保证范围内。

旧资源修复效果已移除资源追加，保留原有城镇、机场和装备设计修复，不能重新加回低保。法国以外185州不改动。

石油盆地方向参考 [BRGM PETROVAL](https://www.brgm.fr/fr/reference-projet-acheve/petroval-potentiel-valorisation-geothermique-forages-petroliers-au-niveau)，钨矿方向参考 [BRGM 钨资源综述](https://www.mineralinfo.fr/sites/default/files/2022-12/RP-61341-FR_panorama_2011_marche_tungstene.pdf)。这些资料只用于地区方向，本版本的产量与开发时间属于架空设定。

逐州配置见 `ECONOMY-4.5.csv`；互动地图见 `previews/4.5.0/ECONOMY.html`。源码、实际脚本情景与安装校验不等于游戏实测；真实存档、资源界面和槽位显示仍待引擎验收。
'''
 (out/'ECONOMY-4.5-ZH.md').write_text(doc,encoding='utf-8',newline='\n')

def main():
 d=load();build_states(d);retire_floors(d);migration(d);documents(d)
 print(json.dumps(dict(ok=True,version=d['version'],**d['summary']),ensure_ascii=False))
if __name__=='__main__':main()
