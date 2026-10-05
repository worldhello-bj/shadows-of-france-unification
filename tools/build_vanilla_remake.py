"""Transplant local vanilla France/Italy focus graphs and adapt their rewards to SoF."""
import argparse,collections,hashlib,json,re,shutil,subprocess
from pathlib import Path
from hoi4_script import parse,one,scalar,entries,walk,replace
import vanilla_local_policy as policy
import vanilla_naming as naming

ROOT=Path(__file__).resolve().parent.parent;MOD=ROOT/'mod'
VERSION='4.2.0'
BASE_EOL={}

def save(rel,text,bom=False):
    p=ROOT/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text.rstrip()+'\n',encoding='utf-8-sig' if bom else 'utf-8',newline=BASE_EOL.get(rel,'\n'))
def baseline(rel):
    raw=subprocess.check_output(['git','show','v3.2.0:'+rel],cwd=ROOT);BASE_EOL[rel]='\r\n' if b'\r\n' in raw else '\n'
    return raw.decode('utf-8-sig').replace('\r\n','\n')
def emit(rows):
    return ' '.join((r.key+' '+(r.operator or '=')+' ' if r.key else '')+('{ '+emit(r.value)+' }' if isinstance(r.value,list) else r.value) for r in rows)
def read(p):return p.read_text(encoding='utf-8-sig').replace('\r\n','\n')
def sha(b):return hashlib.sha256(b).hexdigest()

REPLACE_PLACES={
 'france':{'阿尔及利亚':'卢瓦尔地区','印度支那':'诺曼底','西非':'布列塔尼','叙利亚':'香槟','苏伊士':'罗讷河口','中东':'法国东部','魁北克':'阿基坦','马其诺':'首都防卫','比利时':'北方大区','德国':'洛林','英国':'诺曼底','葡萄牙':'南特','罗马尼亚':'勃艮第','南斯拉夫':'阿尔萨斯','波兰':'梅斯','苏联':'东方协作联盟','莫斯科':'东方盟友','芬兰':'北方市镇','希腊':'地中海伙伴','西班牙':'西南伙伴','意大利':'南方大区','荷兰':'皮卡第','博罗季诺':'洛林','色当':'阿登','滑铁卢':'北方','欧洲':'法兰西','殖民地':'地方大区','殖民':'地区'},
 'italy':{'意大利':'科西嘉','罗马':'阿雅克肖','埃塞俄比亚':'岛内','阿比西尼亚':'岛内','厄立特里亚':'巴拉涅','索马里兰':'萨尔泰讷','索马里':'萨尔泰讷','利比亚':'普罗旺斯','的黎波里':'大陆桥头堡','阿尔巴尼亚':'尼斯','巴尔干':'南方大区','爱琴海':'第勒尼安海','西班牙':'西南法国','英国':'诺曼底','法国领土':'大陆领土','德国':'洛林','土耳其':'马赛','葡萄牙':'波尔多','日本':'大西洋船厂','希腊':'南方海岸','苏联':'南方工人联盟','斯大林':'集权主义','南美':'大西洋','奥地利':'阿尔萨斯','蒂奇诺':'萨瓦','福贾':'科尔特','特尔尼':'巴斯蒂亚','米兰':'阿雅克肖','布雷西亚':'巴拉涅','安萨尔多':'岛内兵工','菲亚特':'工场','墨索里尼':'领袖','法西斯大委员会':'岛内委员会','领袖崇拜':'统帅崇拜','教皇':'主教会议','黑衫军':'岛内卫队','非洲':'南方','殖民地':'地区','殖民':'地区','古罗马':'波拿巴','罗马帝国':'法兰西帝国'}
}
TITLE_OVERRIDES={
 'FRA_franco_soviet_treaty':'首都与东方盟约','ITA_moschettieri_del_duce':'统帅亲卫队','ITA_albanian_fascist_militia':'大陆地区卫队','ITA_secret_weapons':'秘密武器','ITA_independence_rsi':'巩固共和国独立','ITA_the_fight_against_stalinism':'反对集权主义',
 'FRA_france_first':'巴黎优先','FRA_go_with_britain':'与诺曼底协作','FRA_join_comintern':'工人共同阵线','FRA_join_germany':'与洛林结盟','FRA_the_natural_borders_of_france':'法国统一边界','FRA_devalue_the_franc':'统一首都货币',
 'ITA_ethiopian_war_logistics_bba':'岛内战役后勤','ITA_the_ethiopian_question':'科西嘉统一问题','ITA_the_abyssinian_fiasco':'岛内战争的教训','ITA_struggle_in_ethiopia':'岛内攻坚','ITA_triumph_in_africa_bba':'统一科西嘉',
 'ITA_litoranea_balbo':'科西嘉环岛公路','ITA_via_della_vittoria':'大陆胜利道路','ITA_the_fourth_shore':'大陆桥头堡','ITA_war_with_france':'登陆法国大陆','ITA_the_italian_liberation_war':'岛内解放战争','ITA_the_italian_social_republic':'科西嘉社会共和国',
 'ITA_culto_del_duce':'统帅崇拜','ITA_undermine_the_duce':'制衡岛内统帅','ITA_defy_the_duce':'拒绝独裁','ITA_depose_mussolini':'罢免岛内领袖','ITA_the_fate_of_mussolini':'领袖的命运','ITA_convene_the_grand_council':'召集岛内委员会',
 'ITA_power_to_the_king':'波拿巴委任','ITA_monarchia_d_italia':'科西嘉君主政体','ITA_gloria_al_regno_d_italia':'帝国复兴','ITA_proclaim_the_italian_empire':'宣告法兰西帝国','ITA_the_new_emperor_of_ethiopia':'岛内统一的统帅',
 'ITA_the_papacy_reborn':'主教会议的复兴','ITA_the_king_of_the_skies':'天空的主宰','ITA_caligulas_pride':'大型战舰计划','ITA_modern_musculus':'现代登陆舰队','ITA_the_italian_confederation':'科西嘉联邦','ITA_italia_libera':'自由科西嘉'
}
TITLE_OVERRIDES.update(naming.TITLES)
REPLACE_PLACES['france'].update({'巴尔干':'法国东部','德意志':'洛林','美国':'地区市场','斯特雷萨':'南方协约','马奇诺':'首都'})
REPLACE_PLACES['italy'].update({'意属':'岛内','意式':'科西嘉式','维托里奥·埃马努埃莱三世':'王朝委任','翁贝托二世':'立宪王室','巴尔博':'岛内总督','格兰迪':'文官领袖','格拉姆西':'工人代表','格拉齐亚尼':'岛内指挥部','博塔伊':'教育部门','阿尔法·罗密欧':'机械工场','爱迪生':'电力署','科赫':'反间谍处','阿姆哈拉':'岛内割据','德意志':'洛林','对德':'对梅斯','对日':'对南特','英意':'岛内与诺曼底','法意':'岛内与巴黎','西意':'岛内与波尔多','斯特雷萨':'地区协约','巴利阿里':'科西嘉周边','教廷':'岛内教会'})
WAR_REGIONS={
 'FRA_avenge_waterloo':'nord','FRA_retribution_for_sedan':'champagne','FRA_return_to_borodino':'lorraine','FRA_disunite_germany':'lorraine','FRA_align_belgium':'nord','FRA_split_belgium':'picardie','FRA_reorganize_the_dutch':'picardie',
 'FRA_carry_the_revolution_east':'lorraine','FRA_carry_the_revolution_north':'nord','FRA_carry_the_revolution_south':'paca','FRA_carry_the_revolution_west':'normandie','FRA_secure_the_crown_of_spain':'aquitaine','FRA_dismantle_the_democracies':'rhone-alpes',
 'ITA_war_with_france':'paca','ITA_war_with_greece':'languedoc','ITA_war_with_the_uk':'normandie','ITA_demand_ticino':'rhone-alpes','ITA_balkan_ambition':'paca','ITA_masters_of_the_aegean':'paca','ITA_liberate_the_workers_of_africa':'languedoc','ITA_the_holy_lands':'paca','ITA_deus_vult':'paca'
}
PARTNERS={
 'FRA_go_with_britain':'ROU','FRA_franco_soviet_treaty':'MET','FRA_revive_the_franco_polish_alliance':'MET','FRA_invite_romania':'DIJ','FRA_invite_yugoslavia':'STR','FRA_invite_portugal':'NAN','FRA_woo_italy':'MRS','FRA_host_the_german_exiles':'STR','FRA_coordinate_rearmament':'LYO',
 'ITA_german_military_cooperation':'MET','ITA_befriend_greece':'MRS','ITA_befriend_japan':'NAN','ITA_befriend_portugal':'BRD','ITA_befriend_turkey':'TOU','ITA_franco_italian_pact':'PRS','ITA_anglo_italian_pact':'ROU','ITA_anglo_italian_agreements':'ROU','ITA_treaty_with_germany':'MET','ITA_pact_of_steel':'MET','ITA_spanish_italian_alliance':'BRD','ITA_invite_france_to_military_partnership':'PRS','ITA_military_agreements':'MRS','ITA_military_cooperation':'TOU','ITA_seek_british_military_cooperation':'ROU','ITA_joint_military_programs':'LYO'
}

class Builder:
    def __init__(self,game):
        self.game=game;self.loc={};self.native_loc={};self.effects=[];self.idea_code={};self.used_ideas=set();self.dynamic=[];self.dvars={};self.art={};self.records=[];self.textures={};self.adaptations=[]
        self.native_ideas={};self.native_gfx={};self.native_dm={};self.skipped_native=[]
        for p in (game/'localisation/simp_chinese').rglob('*.yml'):
            for k,v in re.findall(r'(?m)^\s+([^\s:]+):\d*\s+"((?:[^"\\]|\\.)*)"',read(p)):self.native_loc[k]=v
        for p in (game/'common/ideas').glob('*.txt'):
            try:parsed=parse(read(p))
            except AssertionError as ex:
                self.skipped_native.append(dict(path=p.relative_to(game).as_posix(),error=str(ex)));continue
            for root in entries(parsed,'ideas'):
                for country in entries(root.value,'country'):
                    for row in country.value:self.native_ideas[row.key]=row.value
        for p in (game/'common/dynamic_modifiers').glob('*.txt'):
            for r in parse(read(p)):self.native_dm[r.key]=r.value
        for p in list((game/'interface').rglob('*.gfx'))+sorted((game/'dlc').glob('*/interface/*.gfx')):
            try:rows=parse(read(p))
            except (AssertionError,UnicodeError):continue
            for group in entries(rows,'spriteTypes'):
                for r in group.value:
                    if isinstance(r.value,list) and scalar(r.value,'name'):self.native_gfx[scalar(r.value,'name').strip('"')]=r.value
        for p in (MOD/'interface').rglob('*.gfx'):
            for group in entries(parse(read(p)),'spriteTypes'):
                for r in group.value:
                    if isinstance(r.value,list) and scalar(r.value,'name'):self.native_gfx.setdefault(scalar(r.value,'name').strip('"'),r.value)

    def title(self,key,donor):
        value=TITLE_OVERRIDES.get(key,self.native_loc.get(key,key))
        for _ in range(4):
            if re.fullmatch(r'\$[^$]+\$',value):value=self.native_loc.get(value.strip('$'),value)
            else:break
        for old,new in REPLACE_PLACES[donor].items():value=value.replace(old,new)
        if '[' in value:value=TITLE_OVERRIDES.get(key,key.replace('ITA_','').replace('_',' '))
        return value

    def namespace(self,text,donor):
        prefix='FRA_' if donor=='france' else 'ITA_';dest='SFP_' if donor=='france' else 'SFC_'
        text=re.sub(r'\b'+prefix+r'[A-Za-z0-9_]+\b',lambda m:dest+m[0][4:],text)
        return text

    def art_copy(self,gfx):
        if gfx in self.art:return self.art[gfx]
        if gfx not in self.native_gfx:raise AssertionError('Missing original sprite '+gfx)
        data=self.native_gfx[gfx];tex=scalar(data,'texturefile','').strip('"');src=self.game/tex
        if not src.is_file():src=MOD/tex
        if not src.is_file():
            candidates=sorted((self.game/'dlc').glob('*/'+tex));assert candidates,(gfx,tex)
            src=candidates[-1]
        assert src.is_file(),(gfx,tex)
        key='GFX_sof_van_'+gfx.removeprefix('GFX_');dest='gfx/interface/sof_vanilla/'+Path(tex).name
        if (MOD/dest).exists() and (MOD/dest).read_bytes()!=src.read_bytes():dest='gfx/interface/sof_vanilla/'+gfx.removeprefix('GFX_')+src.suffix
        (MOD/dest).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,MOD/dest)
        frames=scalar(data,'noOfFrames','1');self.art[gfx]=key;self.textures[gfx]=dest
        self.effects_art.append(f'spriteType = {{ name = "{key}" texturefile = "{dest}" noOfFrames = {frames} }}')
        return key

    def import_idea(self,key,donor):
        if key not in self.native_ideas:return None
        dest='sof_van_'+('prs_' if donor=='france' else 'cor_')+key.lower()
        if dest in self.idea_code:return dest
        original=self.native_ideas[key];fields=[]
        for r in original:
            if r.key in ['modifier','equipment_bonus','research_bonus']:
                value=self.namespace(emit([r]),donor)
                value=re.sub(r'custom_modifier_tooltip = \w+','',value)
                fields.append(value)
        pic=scalar(original,'picture','generic_production_bonus').strip('"')
        sprite='GFX_idea_'+pic
        if sprite in self.native_gfx:
            newgfx=self.art_copy(sprite);picture=newgfx.removeprefix('GFX_idea_') if newgfx.startswith('GFX_idea_') else 'sof_van_'+pic
            # Idea lookup expects exactly GFX_idea_<picture>.
            texrow=self.effects_art[-1] if newgfx==self.art[sprite] else ''
            newname='GFX_idea_'+dest
            target=self.textures[sprite]
            self.effects_art.append(f'spriteType = {{ name = "{newname}" texturefile = "{target}" noOfFrames = 1 }}');picture=dest
        else:picture='sofzh_spirit_v1_sofzh_reward_civil_industry_1'
        self.idea_code[dest]=f'{dest} = {{ allowed = {{ always = no }} allowed_civil_war = {{ always = no }} removal_cost = -1 picture = {picture} '+ ' '.join(fields)+' }'
        self.loc[dest]=self.title(key,donor);self.loc[dest+'_desc']=self.title(key,donor)+'。具体修正见下方效果。'
        return dest

    def import_dynamics(self):
        self.effects_art=[]
        names=['ITA_regio_esercito_dynamic_modifier','ITA_regia_marina_dynamic_modifier','ITA_regia_aeronautica_dynamic_modifier','ITA_ricostruzione_industriale_dynamic_modifier','ITA_military_industry_dynamic_modifier']
        for old in names:
            if old not in self.native_dm:continue
            fields=[]
            for r in self.native_dm[old]:
                if isinstance(r.value,str) and r.value.startswith('ITA_'):
                    var=self.namespace(r.value,'italy');fields.append(r.key+' = '+var);self.dvars[r.value]=var
            if not fields:continue
            new=self.namespace(old,'italy');icon=scalar(self.native_dm[old],'icon','GFX_idea_generic_production_bonus').strip('"')
            if icon in self.native_gfx:icon=self.art_copy(icon)
            self.dynamic.append(new+' = { enable = { always = yes } icon = '+icon+' '+ ' '.join(fields)+' }')
            self.loc[new]={'ITA_regio_esercito_dynamic_modifier':'科西嘉陆军','ITA_regia_marina_dynamic_modifier':'科西嘉舰队','ITA_regia_aeronautica_dynamic_modifier':'岛内航空兵','ITA_ricostruzione_industriale_dynamic_modifier':'岛内工业重建署','ITA_military_industry_dynamic_modifier':'科西嘉军工体系'}[old]

    def building(self,kind):
        cap=5 if kind=='infrastructure' else 10 if kind in ['air_base','naval_base','bunker','coastal_bunker'] else 20
        tests=f'sofzh_unification_french_state = yes is_fully_controlled_by = ROOT {kind} < {cap}'
        if kind in ['dockyard','naval_base','coastal_bunker']:tests+=' is_coastal = yes'
        slots='add_extra_state_shared_building_slots = 1 ' if kind in ['industrial_complex','arms_factory','dockyard','synthetic_refinery'] else ''
        province=' province = { all_provinces = yes'+(' limit_to_coastal = yes' if kind=='coastal_bunker' else '')+' }' if kind in ['bunker','coastal_bunker'] else ''
        build=f'add_building_construction = {{ type = {kind} level = 1 instant_build = yes{province} }}'
        if slots:build=f'if = {{ limit = {{ free_building_slots = {{ building = {kind} size > 0 }} }} {build} }} else = {{ ROOT = {{ add_political_power = 40 }} }}'
        return f'if = {{ limit = {{ any_owned_state = {{ {tests} }} }} random_owned_controlled_state = {{ limit = {{ {tests} }} {slots}{build} }} }} else = {{ add_political_power = 40 }}'

    def local_limit(self,rows,donor):
        """Keep executable local conditions; never flatten both arms of a branch."""
        output=[]
        for r in rows:
            key=r.key or ''
            if key.upper() in ['AND','OR','NOT']:
                child=self.local_limit(r.value,donor)
                if child is None:return None
                output.append(key+' = { '+child+' }')
            elif key in ['always','has_dlc','has_government','is_subject','has_war','has_capitulated','amount_research_slots','has_tech','has_template']:
                output.append(emit([r]))
            elif key=='has_completed_focus':output.append(self.namespace(emit([r]),donor))
            elif key=='has_idea':
                idea=self.import_idea(r.value,donor)
                if not idea:return None
                output.append('has_idea = '+idea)
            else:return None
        return ' '.join(output)

    def harvest(self,rows,donor):
        builds=set()
        simple={'add_political_power','add_stability','add_war_support','add_manpower','army_experience','navy_experience','air_experience','add_popularity','add_tech_bonus','add_doctrine_cost_reduction','add_mastery_bonus','add_breakthrough_progress','set_politics','add_command_power','add_max_command_power','set_convoys','set_technology'}
        def collect(body,state=False):
            result=[];i=0
            while i<len(body):
                r=body[i];i+=1;key=r.key or '';low=key.lower()
                if low=='if':
                    chain=[r]
                    while i<len(body) and (body[i].key or '').lower() in ['else_if','else']:
                        chain.append(body[i]);i+=1
                    limits=[self.local_limit(scalar(a.value,'limit',[]),donor) if (a.key or '').lower()!='else' else '' for a in chain]
                    if all(lim is not None for lim in limits) and not state:
                        parts=[]
                        for a,lim in zip(chain,limits):
                            code=collect([v for v in a.value if v.key!='limit'],state)
                            if code:parts.append(a.key.lower()+' = { '+('limit = { '+lim+' } ' if a.key.lower()!='else' else '')+' '.join(code)+' }')
                            elif a.key.lower()=='if':parts.append('if = { limit = { '+lim+' } }')
                        result.extend(parts)
                    else:
                        # A foreign-war/event predicate has no equivalent on this map.
                        # Select one usable arm, never run mutually exclusive rewards twice.
                        for a in chain:
                            code=collect([v for v in a.value if v.key!='limit'],state)
                            if code:result.extend(code);break
                    continue
                if low=='hidden_effect' or key=='ROOT':result.extend(collect(r.value,state));continue
                if low=='effect_tooltip':continue
                if low in ['random_owned_state','random_owned_controlled_state','every_owned_state','random_core_state','capital_scope','random_state','every_state','every_controlled_state','every_core_state','random_neighbor_state'] or key.isdigit():
                    result.extend(collect([v for v in r.value if v.key not in ['limit','prioritize']],True));continue
                if key=='add_building_construction':
                    kind=scalar(r.value,'type')
                    if kind not in builds:builds.add(kind);result.append(self.building(kind))
                elif key=='add_extra_state_shared_building_slots':
                    if 'slots' not in builds:
                        builds.add('slots');size=min(int(r.value),3)
                        result.append('random_owned_controlled_state = { limit = { sofzh_unification_french_state = yes is_fully_controlled_by = ROOT } add_extra_state_shared_building_slots = '+str(size)+' }')
                elif key=='add_compliance':
                    result.append('every_owned_state = { limit = { sofzh_unification_french_state = yes is_fully_controlled_by = ROOT has_resistance = yes } add_compliance = '+r.value+' }')
                elif key=='add_resource':
                    kind=scalar(r.value,'type');amount=scalar(r.value,'amount','0')
                    if kind and re.fullmatch(r'\d+',amount):result.append('random_owned_controlled_state = { limit = { sofzh_unification_french_state = yes is_fully_controlled_by = ROOT } add_resource = { type = '+kind+' amount = '+str(min(int(amount),4))+' } }')
                elif key=='division_template':
                    template=[v for v in r.value if v.key not in ['division_names_group','override_model','is_locked','template_counter']]
                    name=scalar(template,'name');result.append('if = { limit = { NOT = { has_template = '+name+' } } division_template = { '+emit(template)+' } }')
                elif not state and key in simple:
                    code=self.namespace(emit([r]),donor)
                    if key in ['army_experience','navy_experience','air_experience'] and isinstance(r.value,str):code=key+' = '+str(min(float(r.value),25))
                    if key=='add_manpower' and isinstance(r.value,str):code=key+' = '+str(min(float(r.value),1500))
                    result.append(code)
                elif key=='set_rule' and 'can_create_factions' in emit([r]):result.append('set_rule = { can_create_factions = yes }')
                elif not state and key in ['add_ideas','remove_ideas']:
                    keys=[r.value] if isinstance(r.value,str) else [v.value for v in r.value]
                    for old in keys:
                        if old.endswith('_no_lar') or '_hidden_' in old:continue
                        new=self.import_idea(old,donor)
                        if new:result.append(key+' = '+new)
                elif not state and key=='add_timed_idea':
                    new=self.import_idea(scalar(r.value,'idea'),donor)
                    if new:result.append(f'add_timed_idea = {{ idea = {new} days = {scalar(r.value,"days",180)} }}')
                elif not state and key=='swap_ideas':
                    old=self.import_idea(scalar(r.value,'remove_idea'),donor);new=self.import_idea(scalar(r.value,'add_idea'),donor)
                    if old and new:result.append(f'if = {{ limit = {{ has_idea = {old} }} swap_ideas = {{ remove_idea = {old} add_idea = {new} }} }} else = {{ add_ideas = {new} }}')
                elif not state and key=='add_to_variable':
                    for v in r.value:
                        if v.key in self.dvars and isinstance(v.value,str):result.append('add_to_variable = { '+self.dvars[v.key]+' = '+v.value+' }')
                elif not state and key=='add_research_slot':result.append('if = { limit = { amount_research_slots < 5 } add_research_slot = 1 } else = { add_political_power = 75 }')
                elif not state and key=='add_equipment_to_stockpile':
                    kind=scalar(r.value,'type');amount=scalar(r.value,'amount','0')
                    if re.fullmatch(r'-?\d+(?:\.\d+)?',amount):result.append(f'add_equipment_to_stockpile = {{ type = {kind} amount = {min(float(amount),200):g} producer = ROOT }}')
            return list(dict.fromkeys(result))
        return collect(rows)

    def goal(self,region):
        effect='sof_van_goal_'+region.replace('-','_')
        if effect not in self.goal_names:
            self.goal_names.add(effect);self.effects.append(effect+' = { random_other_country = { limit = { sofzh_unification_legal_target = yes sofzh_unification_is_in_'+region+' = yes NOT = { ROOT = { has_wargoal_against = PREV } } } ROOT = { create_wargoal = { type = annex_everything target = PREV expire = 730 } } } }')
        return ['set_country_flag = sofzh_unification_war_ready',effect+' = yes']

    def offer(self,target):
        return [f'if = {{ limit = {{ country_exists = {target} {target} = {{ sofzh_unification_candidate = yes has_war = no NOT = {{ has_war_with = ROOT }} }} has_war = no }} {target} = {{ country_event = {{ id = sof_van_diplomacy.1 days = 1 }} }} }} else = {{ add_political_power = 40 }}']

    def special(self,key,donor):
        if key in WAR_REGIONS:
            return self.goal(WAR_REGIONS[key])
        if key in PARTNERS:
            return self.offer(PARTNERS[key])
        if key in ['FRA_begin_rearmament','ITA_ethiopian_war_logistics_bba']:
            return ['set_country_flag = sofzh_unification_started','set_country_flag = sofzh_unification_war_ready','sofzh_unification_grant_border_goals = yes']
        if key in ['ITA_the_ethiopian_question','ITA_struggle_in_ethiopia','ITA_topple_amhara_rulers']:return ['sofzh_corsica_island_goals = yes']
        if key in ['ITA_triumph_in_africa_bba','ITA_proclaim_the_italian_empire']:return ['sofzh_corsica_integrate_island = yes','add_stability = 0.04']
        if key=='ITA_divisioni_alpine':return ['sof20_learn_mountain = yes','army_experience = 10']
        if key in ['FRA_fusiliers_marine','ITA_forza_navale_especiale']:return ['sof20_learn_coast = yes','navy_experience = 10']
        if key=='FRA_battle_of_maneuver':return ['sof20_learn_plain = yes','army_experience = 10']
        return []

    def tree(self,donor,tag):
        source=self.game/'common/national_focus'/f'{donor}.txt';original=read(source);tree=one(parse(original),'focus_tree');foci=entries(tree.value,'focus');mapping={scalar(n.value,'id'):self.namespace(scalar(n.value,'id'),donor) for n in foci}
        save(f'references/vanilla/{donor}-1.19.3.txt',original)
        originals={scalar(n.value,'id'):n.value for n in foci};removed=naming.removed_nodes(originals,donor)
        nodes=[];empty=[];self.goal_names=getattr(self,'goal_names',set())
        shape_keys={'x','y','relative_position_id','prerequisite','mutually_exclusive','cost','offset','search_filters'}
        for focus in foci:
            b=focus.value;old=scalar(b,'id');new=mapping[old];title=self.title(old,donor);self.loc[new]=title
            if old in removed:
                self.loc.pop(new,None);continue
            icon=scalar(b,'icon');icon=next(r.key for r in icon if r.key and r.key.startswith('GFX_')) if isinstance(icon,list) else icon
            icon=self.art_copy(icon)
            shape=[]
            for r in b:
                if r.key not in shape_keys:continue
                if r.key in ['prerequisite','mutually_exclusive']:
                    keep=[v for v in r.value if v.key!='focus' or v.value not in removed]
                    if not keep:continue
                    code=r.key+' = { '+emit(keep)+' }'
                else:code=emit([r])
                code=self.namespace(code,donor)
                for gone in removed:code=code.replace('has_completed_focus = '+mapping[gone],'always = no')
                shape.append(code)
            shape=[re.sub(r'tag = ITA\b','original_tag = AJC',s).replace('tag = RDS','has_completed_focus = SFC_unite_the_opposition').replace('tag = RSI','has_completed_focus = SFC_defy_the_duce') for s in shape]
            allow=[]
            for r in entries(b,'allow_branch'):
                code=self.namespace(emit([r]),donor)
                if 'ITA_the_papacy_reborn'==old:code='allow_branch = { has_completed_focus = SFC_strengthen_the_papacy }'
                if old=='ITA_the_italian_liberation_war':code='allow_branch = { has_completed_focus = SFC_defy_the_duce }'
                if old=='ITA_the_italian_social_republic':code='allow_branch = { has_completed_focus = SFC_culto_del_duce has_war = yes }'
                # The transplant exposes expansion routes independently of DLC ownership;
                # vanilla obsolete-branch visibility and focus conditions stay intact.
                code=re.sub(r'has_dlc = "[^"]+"','always = yes',code)
                for gone in removed:code=code.replace('has_completed_focus = '+mapping[gone],'always = no')
                allow.append(code)
            borrowed=self.harvest(one(b,'completion_reward').value,donor)
            adapted=policy.actions(self,old,donor,borrowed)
            actions=self.special(old,donor)+adapted+self.historical.actions(old)
            for gone in removed:actions=[a.replace('has_completed_focus = '+mapping[gone],'always = no') for a in actions]
            actions=list(dict.fromkeys(actions))
            if adapted!=borrowed:self.adaptations.append(old)
            if not actions:empty.append(old)
            reward=' '.join(actions)
            nodes.append('focus = {\n id = '+new+' icon = '+icon+'\n '+'\n '.join(shape+allow)+'\n available = { is_subject = no has_capitulated = no } cancel_if_invalid = yes continue_if_invalid = no\n completion_reward = { '+reward+' }\n ai_will_do = { factor = 1 }\n}')
            story=naming.STORIES.get(old)
            if story is None:
                if any(v in old for v in ['industry','industrial','production','factories','arsenal','farm','extraction','refiner','corporation']):story=f'{title}将决定'+('首都' if donor=='france' else '岛内')+'工场能否承担统一战争的需求。把分散的产能组织起来，让投入形成稳定的供应。'
                elif any(v in old for v in ['army','tank','armor','artillery','infantry','gun','brigad','battalion','regiment','warfare']):story=f'{title}需要明确的训练和装备标准。'+('巴黎' if donor=='france' else '科西嘉')+'军队将据此调整编制与作战方式。'
                elif any(v in old for v in ['air','fighter','bomber','aviation','aereo']):story=f'{title}是建立本地航空力量的一环。统一设计、训练与后勤，使航空兵能够配合地面和海上行动。'
                elif any(v in old for v in ['naval','navy','marina','carrier','ship','submarine','flott','torpedo']):story=f'{title}将为'+('法国海军重建' if donor=='france' else '科西嘉跨海行动')+'准备基础。有限的船厂和人员应当围绕明确的任务安排。'
                else:story=f'{title}关系到'+('巴黎' if donor=='france' else '科西嘉')+'政府下一步的方向。把这一主张落实为政策，为后续建设、治理与地区合作创造条件。'
            self.loc[new+'_desc']=story+'\\n\\n'+self.description(actions,donor)+self.historical.description(old)
            self.records.append(dict(tag=tag,donor=old,id=new,title=title,actions=actions,empty=not actions,original_reward=emit(one(b,'completion_reward').value),original_title=self.native_loc.get(old),original_description=self.native_loc.get(old+'_desc')))
        selector='original_tag = PRS' if tag=='PRS' else 'OR = { original_tag = AJC original_tag = BST original_tag = CLV original_tag = COR original_tag = SRT }'
        ident='sofzh_paris' if tag=='PRS' else 'sofzh_corsica';start='SFP_devalue_the_franc' if tag=='PRS' else 'SFC_ethiopian_war_logistics_bba'
        panel_y=2200 if tag=='PRS' else 2750
        text=f'focus_tree = {{ id = {ident} country = {{ factor = 0 modifier = {{ add = 1000 {selector} }} }} default = no reset_on_civilwar = no initial_show_position = {{ focus = {start} }} continuous_focus_position = {{ x = 50 y = {panel_y} }}\n'+'\n'.join(nodes)+'\n}'
        save('mod/common/national_focus/'+ident+'.txt',text)
        return dict(tag=tag,donor=donor,source_sha256=sha(source.read_bytes()),original_nodes=len(foci),nodes=len(nodes),removed=removed,id_map=mapping,unadapted=empty)

    def description(self,actions,donor):
        text=[]
        script=' '.join(actions)
        policies={'sof_van_arms_market':'地区军备采购','sof_van_allied_investment':'盟友工业援建','sof_van_volunteer_program':'志愿军训练','sof_van_police_reform':'地方警务改革','sof_van_strike_program':'工人和解'}
        for flag,label in policies.items():
            if 'set_country_flag = '+flag in script:text.append('解锁“'+label+'”决议。')
        if 'add_building_construction' in script:text.append('在实际拥有并完整控制的法国地区进行建设，空间不足时提供财政补助。')
        if 'add_extra_state_shared_building_slots' in script:text.append('为实际控制区增加建设空间。')
        if 'add_resource' in script:text.append('改善实际控制区的资源供应。')
        if 'add_tech_bonus' in script:text.append('集中工程与科研力量，获得对应技术研究加成。')
        if 'add_to_variable' in script:text.append('改善对应军队或工业体系，修正累积计入组织能力。')
        if 'add_ideas' in script or 'swap_ideas' in script:text.append('实施本项政策并调整对应民族精神。')
        if 'country_event' in script:text.append('向地区伙伴提议合作；对方可以拒绝。')
        if 'sof_van_goal_' in script or 'island_goals' in script:text.append('取得指定地区的战役授权；正式领土整合仍需另行登记。')
        if 'learn_' in script:text.append('获得永久的小幅地形经验，同类经验只获得一次。')
        if 'set_politics' in script:text.append('调整政府的执政方向，具体政体与支持度变化见效果。')
        if 'create_faction' in script:text.append('建立地区合作阵线，伙伴加入仍需另行协商。')
        if 'add_compliance' in script:text.append('改善已经控制地区的地方合作与治理。')
        if 'add_research_slot' in script:text.append('扩大科研组织，研究槽总数上限为五槽。')
        if 'division_template' in script:text.append('建立新的部队编制，征募与训练由本地军队执行。')
        return ''.join(text) or '通过具体的财政、训练与社会措施完成本项改革。'

    def output(self,reports):
        save('mod/common/ideas/sof_vanilla_major.txt','ideas = { country = {\n'+'\n'.join(self.idea_code.values())+'\n} }')
        save('mod/common/dynamic_modifiers/sof_vanilla_major.txt','\n'.join(self.dynamic))
        save('mod/common/scripted_effects/sof_vanilla_major.txt','\n'.join(self.effects))
        save('mod/interface/sof_vanilla_major.gfx','spriteTypes = {\n'+'\n'.join(self.effects_art)+'\n}')
        save('mod/localisation/simp_chinese/replace/sof_vanilla_major_l_simp_chinese.yml','l_simp_chinese:\n'+'\n'.join(' '+k+':0 "'+v.replace('"','\\"')+'"' for k,v in self.loc.items()),True)
        save('design/vanilla-major-remake.json',json.dumps(dict(version=VERSION,donors=reports,nodes=self.records,imported_ideas=list(self.idea_code),dynamic_variables=self.dvars,semantic_replacements=self.adaptations,skipped_native=self.skipped_native,game_engine_verified=False),ensure_ascii=False,indent=2))

def disable_generated_trees():
    for p in sorted((MOD/'common/national_focus').glob('sof20_*.txt')):
        text=baseline('mod/'+p.relative_to(MOD).as_posix());tree=one(parse(text),'focus_tree');field=one(tree.value,'country')
        save('mod/'+p.relative_to(MOD).as_posix(),replace(text,[(field.start,field.end,'country = { factor = 0 } # Legacy saved-game compatibility only; generic tree wins new games.')]))
    save('mod/common/on_actions/sof20_startup.txt','on_actions = { on_startup = { effect = { every_country = { limit = { sofzh_unification_candidate = yes } sof20_migrate_terrain = yes } } } }')
    ai=baseline('mod/common/ai_strategy_plans/sof20_regions.txt');ai=re.sub(r'allowed = \{ original_tag = [A-Z]+ \}','allowed = { always = no }',ai)
    save('mod/common/ai_strategy_plans/sof20_regions.txt',ai)
    categories=baseline('mod/common/decisions/categories/sof20_regions.txt');rows=parse(categories);changes=[]
    for group in rows:
        original=one(group.value,'allowed');tag=scalar(original.value,'original_tag');changes.append((original.start,original.end,f'allowed = {{ original_tag = {tag} has_focus_tree = sof20_{tag} }}'))
    save('mod/common/decisions/categories/sof20_regions.txt',replace(categories,changes))
    for tree in ['sofzh_paris','sofzh_corsica']:
        text=baseline('mod/common/national_focus/'+tree+'.txt');block=one(parse(text),'focus_tree');selector=one(block.value,'country');ident=one(block.value,'id')
        text=replace(text,[(selector.start,selector.end,'country = { factor = 0 }'),(ident.start,ident.end,'id = '+tree+'_legacy')])
        save('mod/common/national_focus/'+tree+'_legacy.txt',text)
        catpath='mod/common/decisions/categories/'+tree+'.txt'
        if (ROOT/catpath).exists():
            data=baseline(catpath);rows=parse(data);edits=[]
            for row in rows:
                if not isinstance(row.value,list):continue
                gates=entries(row.value,'allowed')
                if gates:
                    gate=gates[0];edits.append((gate.start,gate.end,'allowed = { '+emit(gate.value)+' has_focus_tree = '+tree+'_legacy }'))
                else:edits.append((row.end-1,row.end-1,' allowed = { has_focus_tree = '+tree+'_legacy } '))
            save(catpath,replace(data,edits))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--game',type=Path,default=Path('D:/steam/steamapps/common/Hearts of Iron IV'));parser.add_argument('--apply',action='store_true');args=parser.parse_args()
    if not args.apply:parser.error('--apply required; use a working branch')
    from vanilla_historical import Historical
    b=Builder(args.game);b.import_dynamics();b.historical=Historical(b);reports=[b.tree('france','PRS'),b.tree('italy','AJC')]
    disable_generated_trees()
    import vanilla_startup,vanilla_diplomacy
    startup=vanilla_startup.write(b);vanilla_diplomacy.write(b);b.historical.write()
    b.output(reports)
    save('design/vanilla-startup.json',json.dumps(startup,ensure_ascii=False,indent=2))
    save('VERSION',VERSION);save('mod/descriptor.mod',baseline('mod/descriptor.mod').replace('version="3.2.0"',f'version="{VERSION}"'))
    from focus_art import apply as apply_art
    apply_art()
    print(json.dumps(dict(ok=True,countries=[dict(tag=r['tag'],nodes=r['nodes'],unadapted=r['unadapted']) for r in reports],ideas=len(b.idea_code),dynamics=len(b.dynamic),art=len(b.art)),ensure_ascii=False))

if __name__=='__main__':main()
