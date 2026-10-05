"""Historical cabinets, isolated characters, and local spirit lifecycle migration.

Cabinet members are ordinary ideas in the existing eight political law slots.
Native characters are copied only for head-of-government changes: no dependency
on FRA/ITA character ownership, balance of power, or donor events remains.
"""
import json,re
from collections import defaultdict
from PIL import Image,ImageOps
from hoi4_script import parse,one,scalar,entries,walk,replace

SLOTS={'executive':'行政首席','interior':'内政','treasury':'财政','industry':'工业','defence':'陆军','naval':'海军','science':'科研','foreign':'外交'}

# source, slot, qualifying focus(es), government(s), retired by focus(es), bonuses
PROFILES=[
 ('FRA_leon_blum','executive','form_the_popular_front','democratic','',{'stability_factor':.12,'political_power_factor':.20,'consumer_goods_factor':-.03}),
 ('FRA_rene_nicod','executive','anti_fascist_coalition loyalty_to_the_cause','communism','',{'political_power_factor':.20,'production_factory_efficiency_gain_factor':.20,'army_org_factor':.08}),
 ('FRA_charles_maurras','interior','integralism orleanist_restoration','neutrality fascism','',{'stability_factor':.12,'compliance_gain':.02,'required_garrison_factor':-.12}),
 ('FRA_maxime_weygand','defence','defensive_focus','','',{'army_defence_factor':.20,'army_org_factor':.10,'dig_in_speed_factor':.20}),
 ('FRA_maurice_gamelin','defence','aggressive_focus','','',{'army_attack_factor':.18,'planning_speed':.25,'max_planning_factor':.12}),
 ('FRA_rene_massigli','foreign','confirm_eastern_commitments','democratic','',{'war_support_factor':.12,'political_power_factor':.15,'improve_relations_maintain_cost_factor':-.30}),
 ('FRA_georges_bonnet','foreign','buy_time','democratic','',{'stability_factor':.12,'improve_relations_maintain_cost_factor':-.40,'consumer_goods_factor':-.02}),
 ('FRA_vincent_auriol','treasury','devalue_the_franc','','',{'consumer_goods_factor':-.06,'production_speed_industrial_complex_factor':.20,'political_power_factor':.10}),
 ('FRA_louis_renault','industry','industrial_expansion','','',{'industrial_capacity_factory':.20,'production_factory_max_efficiency_factor':.12,'production_speed_arms_factory_factor':.20}),
 ('FRA_francois_darlan','naval','naval_rearmament','','',{'industrial_capacity_dockyard':.20,'navy_org_factor':.15,'naval_coordination':.15}),
 ('FRA_irene_joliot_curie','science','extra_research_slot','','',{'research_speed_factor':.12,'industrial_research_speed_factor':.15}),
 ('ITA_italo_balbo','executive','italo_balbo_focus','fascism','',{'air_attack_factor':.15,'air_mission_efficiency':.15,'political_power_factor':.15}),
 ('ITA_dino_grandi','executive','believe_obey_fight dino_grandi_focus','fascism neutrality','',{'stability_factor':.12,'political_power_factor':.22,'improve_relations_maintain_cost_factor':-.25}),
 ('ITA_vittorio_emanuele_iii','executive','power_to_the_king democratic_king','neutrality democratic','the_italian_republic',{'stability_factor':.15,'army_org_factor':.12,'political_power_factor':.15}),
 ('ITA_alcide_de_gasperi','executive','revoke_the_acerbo_law disband_the_blackshirts common_ground christian_democracy','democratic neutrality','',{'stability_factor':.15,'political_power_factor':.25,'consumer_goods_factor':-.03}),
 ('ITA_ivanoe_bonomi','executive','unite_the_opposition defy_the_duce italian_socialism','democratic','',{'stability_factor':.12,'political_power_factor':.20,'compliance_gain':.016}),
 ('ITA_antonio_gramsci','executive','liberate_gramsci','communism','',{'research_speed_factor':.08,'production_factory_efficiency_gain_factor':.20,'political_power_factor':.20}),
 ('ITA_amadeo_bordiga','executive','unite_the_opposition defy_the_duce the_popular_front','communism','',{'industrial_capacity_factory':.18,'mobilization_speed':.25,'political_power_factor':.15}),
 ('ITA_pietro_d_acquarone','interior','convene_the_grand_council','neutrality fascism','',{'political_power_factor':.20,'stability_factor':.10,'required_garrison_factor':-.12}),
 ('ITA_achille_starace','interior','army_leaders','fascism','disband_the_blackshirts',{'war_support_factor':.15,'mobilization_speed':.30,'stability_factor':.08}),
 ('ITA_renato_ricci','interior','security_militias','fascism','disband_the_blackshirts',{'resistance_target':-.08,'required_garrison_factor':-.15,'compliance_gain':.012}),
 ('ITA_adelchi_serena','interior','culto_del_duce','fascism','disband_the_blackshirts',{'stability_factor':.12,'political_power_factor':.20,'mobilization_speed':.20}),
 ('ITA_mario_scelba','interior','christian_democracy common_ground','democratic neutrality','',{'stability_factor':.12,'compliance_gain':.022,'resistance_target':-.06}),
 ('ITA_luigi_einaudi','treasury','revoke_the_acerbo_law common_ground','democratic neutrality','',{'consumer_goods_factor':-.06,'production_speed_industrial_complex_factor':.22,'stability_factor':.06}),
 ('ITA_alberto_de_stefani','treasury','cooperate_with_moderates power_to_the_king','neutrality fascism','',{'consumer_goods_factor':-.05,'industrial_capacity_factory':.15,'production_speed_infrastructure_factor':.20}),
 ('ITA_guido_jung','treasury','new_industrialization_program','fascism neutrality','pact_of_steel',{'consumer_goods_factor':-.05,'production_speed_industrial_complex_factor':.18,'production_factory_efficiency_gain_factor':.15}),
 ('ITA_antonio_pesenti','treasury','common_ground the_popular_front','communism','',{'industrial_capacity_factory':.18,'production_speed_arms_factory_factor':.20,'consumer_goods_factor':-.03}),
 ('ITA_giovanni_duca','industry','meritocracy common_ground','neutrality democratic','',{'production_factory_efficiency_gain_factor':.25,'industrial_capacity_factory':.18,'production_factory_max_efficiency_factor':.10}),
 ('ITA_fausto_gullo','industry','common_ground the_popular_front','communism','',{'production_speed_industrial_complex_factor':.22,'production_speed_infrastructure_factor':.25,'consumer_goods_factor':-.04}),
 ('ITA_vittorio_emanuele_orlando','executive','meritocracy monarchia_d_italia common_ground','neutrality democratic','',{'political_power_factor':.25,'stability_factor':.10,'compliance_gain':.012}),
 ('ITA_alberto_pariani','defence','a_bandits_war','','',{'army_org_factor':.15,'army_attack_factor':.10,'supply_consumption_factor':-.15}),
 ('ITA_randolfo_pacciardi','defence','common_ground italian_socialism','democratic','',{'army_org_factor':.15,'army_defence_factor':.15,'army_morale_factor':.20}),
 ('ITA_luigi_longo','defence','common_ground the_popular_front','communism','',{'army_attack_factor':.15,'army_org_factor':.12,'training_time_army_factor':-.15}),
 ('ITA_giuseppe_bottai','science','legge_bottai','','',{'research_speed_factor':.10,'industrial_research_speed_factor':.15,'production_factory_efficiency_gain_factor':.10}),
 ('ITA_guido_de_ruggiero','science','cooperate_with_moderates common_ground','neutrality democratic communism','',{'research_speed_factor':.12,'stability_factor':.08,'political_power_factor':.10}),
 ('ITA_enrico_fermi','science','combined_research_effort','','',{'research_speed_factor':.12,'electronics_research_speed_factor':.20}),
 ('ITA_curzio_malaparte','foreign','cooperate_with_moderates','neutrality democratic','',{'improve_relations_maintain_cost_factor':-.35,'political_power_factor':.20,'stability_factor':.08}),
 ('ITA_gian_galeazzo_ciano','foreign','foreign_affairs','fascism neutrality','',{'political_power_factor':.15,'improve_relations_maintain_cost_factor':-.40,'war_support_factor':.08}),
 ('ITA_alberto_tarchiani','foreign','common_ground italian_socialism','democratic','',{'improve_relations_maintain_cost_factor':-.40,'political_power_factor':.20,'research_sharing_per_country_bonus_factor':.25}),
 ('ITA_domenico_cavagnari','naval','supermarina','','',{'navy_org_factor':.18,'naval_coordination':.18,'industrial_capacity_dockyard':.20}),
]

LEADERS={
 'FRA_form_the_popular_front':('FRA_leon_blum','socialism','democratic'),
 'FRA_anti_fascist_coalition':('FRA_rene_nicod','marxism','communism'),
 'FRA_loyalty_to_the_cause':('FRA_rene_nicod','marxism','communism'),
 'ITA_depose_mussolini':('ITA_grand_council','fascism_ideology','fascism'),
 'ITA_italo_balbo_focus':('ITA_italo_balbo','fascism_ideology','fascism'),
 'ITA_dino_grandi_focus':('ITA_dino_grandi','fascism_ideology','fascism'),
 'ITA_christian_democracy':('ITA_alcide_de_gasperi','conservatism','democratic'),
 'ITA_democratic_king':('ITA_vittorio_emanuele_iii','conservatism','democratic'),
 'ITA_liberate_gramsci':('ITA_antonio_gramsci','marxism','communism'),
 'ITA_the_italian_republic':('ITA_ivanoe_bonomi','liberalism','democratic'),
 'ITA_the_popular_front':('ITA_amadeo_bordiga','marxism','communism'),
 'ITA_italian_socialism':('ITA_ivanoe_bonomi','liberalism','democratic'),
}

CAMPAIGN=['ITA_cooperation_of_the_bourgeoisie','ITA_seizing_old_equipment','ITA_the_garibaldi_legion_ns','ITA_aiding_the_spanish_republic']

def idea_id(source):return 'sof_hist_'+source.lower()
def char_id(source):return 'sof_hist_character_'+source.lower()
def prefix(source):return source[:4]
def donor(source):return 'france' if source.startswith('FRA_') else 'italy'
def unlocks(p):return [prefix(p['source'])+x for x in p['focuses']]

def person_name(b,source):
    name=b.native_loc.get(source,source)
    for _ in range(6):
        if re.fullmatch(r'\$[^$]+\$',name):name=b.native_loc.get(name.strip('$'),name)
        else:break
    return name

class Historical:
    def __init__(self,b):
        self.b=b;self.members=[];self.native={};self.by_focus=defaultdict(list)
        for name in ['FRA','ITA']:
            root=one(parse((b.game/f'common/characters/{name}.txt').read_text(encoding='utf-8-sig')),'characters')
            self.native.update({r.key:r.value for r in root.value})
        source_ids={scalar(n.value,'id') for name in ['france','italy'] for n in entries(one(parse((b.game/f'common/national_focus/{name}.txt').read_text(encoding='utf-8-sig')),'focus_tree').value,'focus')}
        for source,slot,focuses,gov,retired,mods in PROFILES:
            assert source in self.native,source
            p=dict(source=source,id=idea_id(source),slot=slot,focuses=focuses.split(),governments=gov.split(),retired=retired.split(),modifiers=mods,cost=125)
            for fid in unlocks(p)+[prefix(source)+x for x in p['retired']]:assert fid in source_ids,fid
            name=scalar(self.native[source],'name',source);p['name']=person_name(b,name)
            assert re.search('[\u4e00-\u9fff]',p['name']),p['name']
            self.members.append(p)
            for fid in unlocks(p):self.by_focus[fid].append(p)
            pics=one(self.native[source],'portraits').value
            small=[r.value.strip('"') for r in walk(pics) if r.key=='small'];large=[r.value.strip('"') for r in walk(pics) if r.key=='large']
            gfx=(small or large)[0];b.art_copy(gfx);p['portrait_source']=b.textures[gfx]
            from build_vanilla_remake import MOD
            p['portrait']='gfx/interface/sof_historical/'+p['id']+'.dds'
            target=MOD/p['portrait'];target.parent.mkdir(parents=True,exist_ok=True)
            im=Image.open(MOD/p['portrait_source']).convert('RGBA')
            ImageOps.fit(im,(65,67),method=Image.Resampling.LANCZOS,centering=(.5,.15)).save(target)
            b.effects_art.append(f'spriteType = {{ name = "GFX_idea_{p["id"]}" texturefile = "{p["portrait"]}" noOfFrames = 1 }}')
            b.loc[p['id']]=p['name']
            names=' / '.join(b.title(fid,donor(source)) for fid in unlocks(p))
            govnames={'democratic':'民主','neutrality':'中立','fascism':'法西斯','communism':'共产主义'}
            req=('；执政方向：'+'、'.join(govnames[g] for g in p['governments'])) if p['governments'] else ''
            stop=('；完成“'+'、'.join(b.title(prefix(source)+x,donor(source)) for x in p['retired'])+'”后退出内阁') if p['retired'] else ''
            b.loc[p['id']+'_desc']=f'历史内阁 · {SLOTS[slot]}\\n解锁国策：{names}{req}{stop}。\\n任命消耗125政治点数；替换本栏现任成员，任期调整冷却90天。'
            b.loc[p['id']+'_unlock_tt']=f'解锁历史{SLOTS[slot]}：§Y{p["name"]}§!。执政条件与任命费用见政治界面内阁列表。'
            b.loc[p['id']+'_requirements_tt']='已完成以下国策之一：'+names+req+stop+'。'
        self.by_id={p['id']:p for p in self.members}

    def ready(self,p,completed=True):
        text='has_focus_tree = '+('sofzh_paris' if donor(p['source'])=='france' else 'sofzh_corsica')+' '
        if completed:text+='OR = { '+' '.join('has_completed_focus = '+self.b.namespace(x,donor(p['source'])) for x in unlocks(p))+' } '
        if p['governments']:text+='OR = { '+' '.join('has_government = '+x for x in p['governments'])+' } '
        for x in p['retired']:text+='NOT = { has_completed_focus = '+self.b.namespace(prefix(p['source'])+x,donor(p['source']))+' } '
        return text

    def leader_action(self,old):
        source,ideology,gov=LEADERS[old];cid=char_id(source)
        # Characters have no advisor role: hiring remains in the eight cabinet
        # slots, with one bonus payload; government portraits carry no extra buff.
        code=f'if = {{ limit = {{ NOT = {{ has_character = {cid} }} }} recruit_character = {cid} }} '
        code+=f'set_politics = {{ ruling_party = {gov} elections_allowed = '+('yes' if gov=='democratic' else 'no')+' } '
        code+=f'if = {{ limit = {{ {cid} = {{ has_ideology = {ideology} }} }} remove_country_leader_role = {{ character = {cid} ideology = {ideology} }} }} '
        code+=f'add_country_leader_role = {{ character = {cid} promote_leader = yes country_leader = {{ ideology = {ideology} expire = "1965.1.1.1" }} }} '
        pid=idea_id(source)
        if pid in self.by_id:code+='add_ideas = '+pid+' '
        if old=='ITA_the_italian_republic':code+=f'if = {{ limit = {{ has_character = {char_id("ITA_vittorio_emanuele_iii")} }} retire_character = {char_id("ITA_vittorio_emanuele_iii")} }} remove_ideas = {idea_id("ITA_vittorio_emanuele_iii")} '
        return code

    def actions(self,old):
        result=['custom_effect_tooltip = '+p['id']+'_unlock_tt' for p in self.by_focus[old]]
        if old in LEADERS:
            effect='sof_hist_complete_'+old.lower();self.b.effects.append(effect+' = { '+self.leader_action(old)+' set_country_flag = '+effect+'_done }');result.append(effect+' = yes')
        if old=='ITA_scientific_cooperation':result+=['set_country_flag = sof_van_science_host','sof_van_reward_sync = yes']
        if old in ['ITA_disband_the_blackshirts','ITA_pact_of_steel','ITA_the_italian_republic']:
            result += ['remove_ideas = '+p['id'] for p in self.members if old[4:] in p['retired']]
        return result

    def description(self,old):
        text=''
        if self.by_focus[old]:text+='\\n解锁历史内阁：'+'、'.join(p['name']+'（'+SLOTS[p['slot']]+'）' for p in self.by_focus[old])+'。'
        if old in LEADERS:
            s=LEADERS[old][0];n=person_name(self.b,s);text+='\\n由'+n+'出任政府领袖。'
            if idea_id(s) in self.by_id:text+='同时免费任命其为行政首席；替换本栏现任成员。'
        if old=='ITA_scientific_cooperation':text+='\\n建立地区科研合作组：本国及同阵营成员共享已研究技术的追赶加成，每名已掌握技术的伙伴提供基础15%加成；合作精神使该比例增加25%。离开阵营时退出合作组。'
        return text

    def write(self):
        from build_vanilla_remake import save,baseline,emit,ROOT,MOD,VERSION
        b=self.b;groups=defaultdict(list)
        for p in self.members:groups[p['slot']].append(p)
        text=baseline('mod/common/ideas/sofzh_cabinet.txt');edits=[]
        for cat in one(parse(text),'ideas').value:
            if not cat.key.startswith('sofzh_cabinet_'):continue
            slot=cat.key.removeprefix('sofzh_cabinet_');members=groups[slot];generic=[f'sofzh_minister_{slot}_{n}' for n in [1,2,3]];ids=generic+[p['id'] for p in members]
            for n in cat.value:
                if n.key not in generic:continue
                onadd=one(n.value,'on_add');clean=' '.join('remove_ideas = '+x for x in ids if x!=n.key)
                edits.append((onadd.end-1,onadd.end-1,' '+clean+' '))
                ai=one(n.value,'ai_will_do');gate=one(one(ai.value,'modifier').value,'OR')
                edits.append((gate.end-1,gate.end-1,' '+' '.join('has_idea = '+p['id'] for p in members)+' '))
            code=[]
            for p in members:
                pid=p['id'];clean=' '.join('remove_ideas = '+x for x in ids if x!=pid)
                available=f'{pid}_available = yes'
                mods={k:v for k,v in p['modifiers'].items() if not k.endswith('_research_speed_factor')}
                research={k.removesuffix('_research_speed_factor').replace('industrial','industry'):v for k,v in p['modifiers'].items() if k.endswith('_research_speed_factor')}
                bonus=(' research_bonus = { '+' '.join(k+' = '+str(v) for k,v in research.items())+' }') if research else ''
                code.append(f'{pid} = {{ allowed = {{ always = yes }} visible = {{ sofzh_cabinet_country = yes has_focus_tree = '+('sofzh_paris' if donor(p['source'])=='france' else 'sofzh_corsica')+f' }} available = {{ {available} }} cost = 125 removal_cost = -1 picture = {pid} cancel_if_invalid = no cancel = {{ NOT = {{ '+self.ready(p)+' } } on_add = { '+clean+f' set_country_flag = {{ flag = sofzh_cabinet_{slot}_cooldown days = 90 }} }} ai_will_do = {{ factor = 6 modifier = {{ OR = {{ '+' '.join('has_idea = '+x['id'] for x in members)+f' }} factor = 0 }} }} modifier = {{ '+' '.join(k+' = '+str(v) for k,v in mods.items())+' }'+bonus+' }')
            edits.append((cat.end-1,cat.end-1,'\n'+'\n'.join(code)+'\n'))
        save('mod/common/ideas/sofzh_cabinet.txt',replace(text,edits))
        triggers=baseline('mod/common/scripted_triggers/sofzh_cabinet.txt')
        for slot,ps in groups.items():
            old='OR = { '+' '.join(f'has_idea = sofzh_minister_{slot}_{n}' for n in [1,2,3])+' }'
            triggers=triggers.replace(old,old[:-1]+' '.join('has_idea = '+p['id']+' ' for p in ps)+'}')
        for p in self.members:
            pid=p['id'];slot=p['slot']
            triggers+=f'\n{pid}_available = {{ sofzh_cabinet_country = yes custom_trigger_tooltip = {{ tooltip = {pid}_requirements_tt '+self.ready(p)+f' }} custom_trigger_tooltip = {{ tooltip = sofzh_compact_minister_not_current_tt NOT = {{ has_idea = {pid} }} }} custom_trigger_tooltip = {{ tooltip = sofzh_compact_minister_cooldown_tt NOT = {{ has_country_flag = sofzh_cabinet_{slot}_cooldown }} }} custom_trigger_tooltip = {{ tooltip = sofzh_compact_pp_125_tt has_political_power > 124.99 }} }}'
        # Membership follows the actual owner of the Corsican tree, including
        # regional starts where AJC is annexed; there is no fixed foreign tag.
        # PREV is the tested member in both global startup loops and country
        # weekly pulses; ROOT need not be that member in a global action.
        qualified='has_focus_tree = sofzh_corsica OR = { has_completed_focus = SFC_scientific_cooperation has_country_flag = sof_van_science_host }'
        partner='OR = { AND = { '+qualified+' } any_other_country = { '+qualified+' is_in_faction_with = PREV } }'
        triggers+='\nsof_van_science_partner = { '+partner+' }'
        save('mod/common/scripted_triggers/sofzh_cabinet.txt',triggers)
        chars=[]
        for source in sorted({x[0] for x in LEADERS.values()}):
            pics=one(self.native[source],'portraits');pict=emit([pics])
            for r in walk(pics.value):
                if r.key in ['small','large']:
                    original=r.value.strip('"');pict=pict.replace(r.value,'"'+b.art_copy(original)+'"')
            cid=char_id(source);chars.append(f'{cid} = {{ name = {cid} can_be_captured = no '+pict+' }');b.loc[cid]=person_name(b,source)
        save('mod/common/characters/sof_vanilla_historical.txt','characters = {\n'+'\n'.join(chars)+'\n}')
        # Completed foci in 4.0 saves get their missing appointments exactly once.
        # Process in native branch order, so the final political choice wins.
        ordered=[n for n in b.records if n['donor'] in LEADERS]
        migrate=['remove_ideas = sof_van_prs_fra_political_violence']
        for n in ordered:
            old=n['donor'];effect='sof_hist_complete_'+old.lower()
            migrate.append(f'if = {{ limit = {{ has_completed_focus = {n["id"]} NOT = {{ has_country_flag = {effect}_done }} }} {effect} = yes }}')
        migrate.append('set_country_flag = sof_hist_migrated_410')
        b.effects.append('sof_hist_setup = { if = { limit = { OR = { has_focus_tree = sofzh_paris has_focus_tree = sofzh_corsica } NOT = { has_country_flag = sof_hist_migrated_410 } } '+' '.join(migrate)+' } }')
        sync=[]
        for old in CAMPAIGN:
            pid='sof_van_cor_'+old.lower();flag=pid+'_saw_war'
            sync.append(f'if = {{ limit = {{ has_idea = {pid} has_war = yes }} set_country_flag = {flag} }}')
        sci='sof_van_cor_ita_scientific_cooperation_ns';group='sof_van_scientific_cooperation'
        sync.append(f'if = {{ limit = {{ sof_van_science_partner = yes }} if = {{ limit = {{ NOT = {{ is_in_tech_sharing_group = {group} }} }} add_to_tech_sharing_group = {group} }} if = {{ limit = {{ NOT = {{ has_idea = {sci} }} }} add_ideas = {sci} }} set_country_flag = sof_van_science_managed }} else_if = {{ limit = {{ OR = {{ has_country_flag = sof_van_science_managed is_in_tech_sharing_group = {group} }} }} remove_from_tech_sharing_group = {group} remove_ideas = {sci} clr_country_flag = sof_van_science_managed }}')
        # cancel = handles appointed members on regime changes, too; pulse is
        # also explicit, so weekly saves cannot retain disbanded old ministers.
        for p in self.members:sync.append('if = { limit = { has_idea = '+p['id']+' NOT = { '+self.ready(p)+' } } remove_ideas = '+p['id']+' }')
        b.effects.append('sof_van_reward_sync = { '+' '.join(sync)+' }')
        save('mod/common/technology_sharing/sof_vanilla_major.txt',f'technology_sharing_group = {{ id = {group} name = {group}_name desc = {group}_desc picture = GFX_technology_sharing_default research_sharing_per_country_bonus = 0.15 available = {{ sof_van_science_partner = yes }} }}')
        b.loc[group+'_name']='地区科研协作网络';b.loc[group+'_desc']='科西嘉与同阵营伙伴交换科研成果。每名已经掌握所研究技术的成员提供15%基础追赶加成。'
        # Native trigger is is_in_tech_sharing_group (the engine docs' example
        # uses an obsolete longer spelling; actual donor scripts use this one).
        b.idea_code[sci]=b.idea_code[sci][:-1]+f' do_effect = {{ is_in_tech_sharing_group = {group} }} cancel = {{ NOT = {{ sof_van_science_partner = yes }} }} }}'
        repaired=[]
        for old,mods in [('ITA_the_eastern_threat_ns',{'army_attack_factor':.10}),('ITA_the_fight_against_stalinism',{'army_attack_factor':.05,'army_defence_factor':.15})]:
            pid='sof_van_cor_'+old.lower();text=b.idea_code[pid];original=parse(text)[0];m=entries(original.value,'modifier')
            if m:text=replace(text,[(m[0].start,m[0].end,'')])
            b.idea_code[pid]=text[:-1]+' modifier = { '+' '.join(k+' = '+str(v) for k,v in mods.items())+' } }'
            b.loc[pid+'_desc']='用于本地统一战争的军事政策。原版针对外国的修正改为本国部队修正，保留国策所给持续时间。';repaired.append(pid)
        for old in CAMPAIGN:
            pid='sof_van_cor_'+old.lower();flag=pid+'_saw_war'
            b.idea_code[pid]=b.idea_code[pid][:-1]+f' on_add = {{ clr_country_flag = {flag} }} cancel = {{ OR = {{ has_country_flag = sofzh_unification_complete AND = {{ has_country_flag = {flag} has_war = no }} }} }} }}'
            b.loc[pid+'_desc']='统一战争的阶段性动员。领取后等待下一场战争；参战后的和平或完成全国统一时撤销，国策规定的期限仍然生效。'
        for old in ['ITA_italian_confederation_leader','ITA_italian_confederation_leader_improved']:
            pid='sof_van_cor_'+old.lower();b.idea_code[pid]=b.idea_code[pid][:-1]+' cancel = { num_subjects < 1 } }'
            b.loc[pid+'_desc']='联邦领导者的组织优势。仅在拥有至少一个附属国期间生效；失去全部附属国时撤销。'
        save('design/historical-cabinet.json',json.dumps(dict(version=VERSION,members=self.members,leader_changes=LEADERS,repaired_empty_spirits=repaired,campaign_spirits=CAMPAIGN,slots=SLOTS,game_engine_verified=False),ensure_ascii=False,indent=2))
        on='mod/common/on_actions/sof20_startup.txt';text=(ROOT/on).read_text(encoding='utf-8-sig')
        text=text.replace('sof_van_setup = yes','sof_van_setup = yes sof_hist_setup = yes')
        # on_weekly country scope must synchronize all partners, not just the
        # historical tree's owner. Startup does the same for already saved wars.
        rows=parse(text);actions=one(rows,'on_actions');edits=[]
        for action in actions.value:
            effect=one(action.value,'effect');suffix=' every_country = { sof_van_reward_sync = yes } ' if action.key=='on_startup' else ' sof_van_reward_sync = yes '
            edits.append((effect.end-1,effect.end-1,suffix))
        save(on,replace(text,edits))
