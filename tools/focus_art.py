"""Bind generated focus art; technical exports preserve the generated alpha."""
import argparse,collections,hashlib,json,re
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from hoi4_script import parse,one,scalar,entries,replace,walk

ROOT=Path(__file__).resolve().parent.parent;MOD=ROOT/'mod'
ART=ROOT/'art/focus';NATIVE=MOD/'gfx/interface/sof_focus'

OVERRIDES={
 'FRA_devalue_the_franc':'currency','ITA_devaluate_the_lire':'currency',
 'FRA_the_congress_of_paris':'paris','FRA_france_first':'paris',
 'FRA_france_leads':'paris','FRA_france_undividable':'unification',
 'FRA_the_council_of_rambouillet':'crown','FRA_orleanist_restoration':'crown',
 'FRA_the_legitimate_heir':'crown','FRA_the_first_citizen_of_the_state':'crown',
 'FRA_proclaim_the_third_empire':'empire','FRA_je_suis_la_deluge':'empire',
 'FRA_firepower_kills':'artillery','FRA_methodical_battle':'army',
 'FRA_flying_artillery':'bomber','FRA_heavy_armor_focus':'armor',
 'FRA_extra_research_slot':'science','FRA_extra_research_slot_2':'science',
 'FRA_reorganize_the_aviation_industry':'engineering','ITA_new_forms_of_weaponry':'engineering',
 'FRA_slum_clearing':'social_welfare','FRA_public_welfare':'social_welfare',
 'FRA_family':'social_welfare','FRA_fatherland':'unification','FRA_work':'workers',
 'FRA_invite_communist_ministers':'workers','FRA_humanite_unie':'equality',
 'FRA_form_the_popular_front':'republic','FRA_revive_the_national_bloc':'parliament',
 'FRA_integralism':'empire','FRA_destroy_decadence':'propaganda',
 'FRA_fusiliers_marine':'landing','FRA_air_ground_cooperation':'bomber',
 'FRA_the_old_school':'battleship','FRA_the_young_school':'submarine',
 'FRA_surface_combat':'cruiser','FRA_undersea_combat':'submarine',
 'ITA_ethiopian_war_logistics_bba':'logistics','ITA_triumph_in_africa_bba':'corsica',
 'ITA_italy_first':'corsica','ITA_the_ethiopian_question':'corsica',
 'ITA_the_italian_confederation':'corsica','ITA_italia_libera':'corsica',
 'ITA_italo_balbo_focus':'army','ITA_dino_grandi_focus':'parliament',
 'ITA_depose_mussolini':'parliament','ITA_the_fate_of_mussolini':'parliament',
 'ITA_democratic_king':'crown','ITA_power_to_the_king':'crown',
 'ITA_proclaim_the_italian_empire':'empire','ITA_a_colonial_empire':'empire',
 'ITA_capo_supremo':'empire','ITA_divino_duce':'empire','ITA_bend_the_bars':'unification',
 'ITA_liberate_gramsci':'workers','ITA_a_leader_steps_forward':'workers',
 'ITA_a_new_era_for_the_red_shirts':'militia','ITA_the_garibaldi_legion':'militia',
 'ITA_gruppi_di_difesa_della_donna':'equality','ITA_the_republics_leadership':'republic',
 'ITA_a_bandits_war':'mountain','ITA_carica_di_isbuscenskij':'motorized',
 'ITA_ferrea_mole_ferreo_cuore':'armor','ITA_by_blood_alone':'army',
 'ITA_moschettieri_del_duce':'militia','ITA_banda_carita':'security','ITA_banda_koch':'security',
 'ITA_albanian_occupation':'security','ITA_cooperate_with_the_mafia':'security',
 'ITA_mafia_abroad':'diplomacy','ITA_crush_the_mafia':'security',
 'ITA_citta_dell_aria':'fighter','ITA_officers_of_the_service_role':'fighter',
 'ITA_fanti_dell_aria':'special_forces','ITA_special_brigades':'special_forces',
 'ITA_mare_nostrum_bba':'battleship','ITA_the_king_of_the_skies':'fighter',
 'ITA_decima_flottiglia_mas':'destroyer','ITA_cooperation_programs':'naval_base',
 'ITA_modern_musculus':'landing','ITA_caligulas_pride':'battleship',
 'ITA_joint_military_programs':'diplomacy','ITA_military_cooperation':'diplomacy',
 'ITA_military_agreements':'diplomacy','ITA_peace_preservation':'diplomacy',
 'ITA_defend_the_land':'unification','ITA_new_roman_citizens':'equality',
 'ITA_abolish_the_colonies':'equality','ITA_new_colonial_policies':'equality',
 'FRA_invest_in_the_metropole':'civilian_industry','FRA_global_integration':'civilian_industry',
 'FRA_aggressive_focus':'army','FRA_pre_empt_the_fascist_attack':'unification',
 'FRA_host_the_german_exiles':'social_welfare','FRA_dirigisme':'currency',
 'FRA_buy_time':'diplomacy','FRA_ratify_the_stresa_front':'diplomacy',
 'FRA_intervention_in_greece':'diplomacy','FRA_establish_spheres_of_influence':'diplomacy',
 'FRA_reorganize_the_dutch':'unification','ITA_ministry_of_italian_africa':'parliament',
 'ITA_develop_ethiopia':'civilian_industry','ITA_develop_libya':'civilian_industry',
 'ITA_develop_eritrea':'civilian_industry','ITA_develop_somaliland':'civilian_industry',
 'ITA_regional_development':'engineering','ITA_comandante_diavolo':'army',
 'ITA_refit_civilian_ships':'naval_base','ITA_solid_progress':'unification',
 'ITA_struggle_in_ethiopia':'mountain','ITA_towards_a_greater_italy':'unification',
 'ITA_masters_of_the_aegean':'coast_defense','ITA_masters_of_the_mediterranean':'battleship',
 'ITA_stop_the_squandering':'currency','ITA_the_fourth_shore':'landing',
 'ITA_economic_reforms':'currency','ITA_balkan_ambition':'unification',
 'ITA_guarantee_austrian_independence':'diplomacy','ITA_ratify_the_stresa_front':'diplomacy',
 'ITA_italys_destiny':'corsica','ITA_the_eastern_threat':'unification',
 'ITA_secret_weapons':'science','ITA_organize_strikes_in_the_north':'workers',
 'ITA_pugno_alzato':'workers','ITA_raise_the_peoples':'propaganda',
 'ITA_il_sol_dell_avvenire':'workers','ITA_bring_back_exiled_intellectuals':'science',
 'ITA_bring_down_fascist_strongholds':'unification',
 'FRA_metropolitan_france':'civilian_industry','FRA_algerie_france':'civilian_industry',
 'FRA_invest_in_the_colonies':'civilian_industry','FRA_invest_in_west_africa':'civilian_industry',
 'FRA_invest_in_indochina':'civilian_industry','FRA_invest_in_syria':'civilian_industry',
 'FRA_begin_rearmament':'military_industry','FRA_mechanized_focus':'motorized',
 'FRA_anti_fascist_coalition':'diplomacy','FRA_french_union':'unification',
 'FRA_reform_the_labour_laws':'constitution','FRA_invest_in_our_weaker_allies':'civilian_industry',
 'FRA_strengthen_government_support':'parliament','FRA_arms_purchases_in_the_us':'logistics',
 'FRA_carrier_planes':'naval_air','FRA_national_mobilization':'propaganda',
 'ITA_increase_artillery_production':'military_industry','ITA_expand_rome_flying_school':'fighter',
 'ITA_oto_naval_guns':'military_industry','ITA_expand_naval_intelligence':'communications',
 'ITA_the_man_of_providence':'propaganda','ITA_believe_obey_fight':'propaganda',
 'ITA_consolidate_power':'parliament','ITA_a_greater_purpose':'propaganda',
 'ITA_compagnie_auto_avio_sahariane':'motorized','ITA_combined_land_and_air_warfare':'bomber',
 'ITA_novus_ordo':'empire','ITA_bring_back_old_glories':'empire',
 'ITA_paramilitary_training':'militia','ITA_pact_of_steel':'diplomacy',
 'ITA_seize_old_equipment':'logistics','ITA_political_commissars':'propaganda',
 'ITA_italian_socialism':'republic','ITA_cooperatives_for_intensive_exploitation':'workers',
 'FRA_laissez_faire':'currency','FRA_loyalty_to_the_cause':'workers',
 'ITA_libyan_railway':'railway','ITA_meritocracy':'parliament',
}

# Specific subjects precede broad branch terms. Original IDs and original sprite
# subjects keep renamed local policy nodes distinguishable without foreign art.
RULES=[
 ('church',r'papal|papacy|church|christian|catholic|教会|基督|主教'),
 ('carrier',r'carrier|joffre|航母|舰载'),
 ('submarine',r'submarine|undersea|antisommer|潜艇|潜战|海狼'),
 ('destroyer',r'torpedo|screen_ship|cacciator|驱逐|护航|鱼雷'),
 ('cruiser',r'cruiser|incrociator|巡洋'),
 ('coast_defense',r'coastal|marittima_di_artiglieria|岸防'),
 ('naval_air',r'naval_bomber|naval_air|海空|海军轰炸'),
 ('battleship',r'battleship|capital_ship|richelieu|navi_da_battaglia|战列|主力舰|重型舰'),
 ('landing',r'marine|landing|fusiliers|登陆|陆战队|跨海作战'),
 ('naval_base',r'dockyard|naval_base|naval_facilit|船坞|海军基地|港口'),
 ('fighter',r'fighter|king_of_the_skies|reggiane|战斗机|战机|空中霸权'),
 ('bomber',r'bomber|cas_focus|diving|轰炸|近距支援'),
 ('communications',r'comms|radio|intelligence|informazione|通信|通讯|情报'),
 ('science',r'research|universit|scientific|大学|科研|研究|科技'),
 ('railway',r'railway|铁路|列车'),
 ('roads',r'highway|autoroute|litoranea|via_della|公路|道路|交通'),
 ('power',r'power_plant|edison|电力|发电'),
 ('fuel',r'fuel|oil|refiner|燃料|燃油|石油|炼油|精炼'),
 ('steel',r'steel|extraction|resource|钢铁|资源|采掘'),
 ('agriculture',r'agricultur|farm|grano|粮食|农业|农场|农田|土地之战'),
 ('currency',r'devalue|(?:^|_)franc(?:$|_)|(?:^|_)lire(?:$|_)|fiscal|budget|laissez|market|货币|财政|市场|投资|创业|经济分权'),
 ('military_industry',r'military_factor|munition|arsenal|arms_industry|军工|军用工厂|兵工|弹药|轻武器工业|军备市场'),
 ('civilian_industry',r'industr|production|factor|corporation|economy|工场|工业|工厂|产能|专业化|标准化'),
 ('fortification',r'fort|defensive|defense|防线|工事|防御|保卫|巩固边境'),
 ('mountain',r'alpin|mountain|山地|山岭'),
 ('special_forces',r'special_force|brigad|para|特种|航空步兵'),
 ('armor',r'tank|armor|cuirassee|铁石心|装甲|坦克'),
 ('motorized',r'motoriz|mechaniz|mobile|auto_avio|摩托|机械化|机动'),
 ('artillery',r'artillery|guns|火炮|炮阵|舰炮'),
 ('logistics',r'logistic|supply|equipment|补给|后勤|装备|军备重整'),
 ('infantry',r'infantry|rifle|bersaglieri|auxiliar|irregular|ascari|步兵|神射|辅助部队|散兵'),
 ('militia',r'volunteer|blackshirt|militia|guard|志愿|卫队|民兵|准军事|突击营|军团'),
 ('security',r'polizia|carabinieri|security|purge|conspirac|opposition|crush|查禁|取缔|清洗|治安|警务|密谋|镇压|碾碎|粉碎'),
 ('crown',r'king|crown|monarch|heir|royal|orlean|君主|立宪|王室|王朝|王冠|波拿巴|继承'),
 ('empire',r'empire|imperial|eagle|hegemony|regenerat|glor|统帅|领袖崇拜|帝国|雄鹰|霸权|民族重生|民族英雄'),
 ('equality',r'suffrage|equality|citizen|rights|liberty|liberte|妇女|公民|平等|人权|自由阵线'),
 ('workers',r'worker|union|commun|socialis|collectiv|five_year|red_shirt|gramsci|bolshev|革命|公社|工人|工会|集体|共产|社会主义|劳动|五年|生产社会'),
 ('social_welfare',r'welfare|family|stability|immigra|guest_worker|womens|公共福利|社会稳定|生育|贫民|和解|安置'),
 ('constitution',r'constitution|law|legal|revoke|repeal|education|宪法|制宪|法律|选举|教育|法案'),
 ('diplomacy',r'alliance|ally|allies|agreement|pact|entente|diplomat|cooper|befriend|invite|negotia|reconnect|concess|support|外交|和平|伙伴|盟友|同盟|盟约|协约|合作|协定|协商|邀请|联系|条约|磋商|联合'),
 ('unification',r'war_with|war_goal|war_ready|demand|unif|natural_border|liberate|战役|进军|远征|统一|战争|边界|解放|割据'),
 ('propaganda',r'rhetoric|propagand|zeal|devotion|cultura|believe|nation|动员|言论|宣传|信仰|奉献|热情|文化|天选|雄狮|相信|浪潮'),
 ('republic',r'republic|popular_front|democra|libera|自治|共和|民主|自由|进步'),
 ('army',r'army|esercito|warfare|battle|military|officer|军队|陆军|军官|作战|战略|部队'),
 ('fighter',r'air|aereo|aviation|航空|空军|天空'),
 ('battleship',r'naval|navy|marina|flott|舰队|海军|海上|海洋'),
 ('parliament',r'government|council|party|politic|government|政|委员会|议会|代表|党|执政|内阁|纲领'),
]

def family(key,title='',native_icon=''):
    if key in OVERRIDES:return OVERRIDES[key]
    # The adapted title describes the current setting. Donor IDs and sprite
    # names are fallbacks; a stock icon may describe an unrelated old subject.
    for subject in (title,key,native_icon):
        for result,pattern in RULES:
            if re.search(pattern,subject.lower()):return result
    return 'parliament'

def export(partial=False):
    spec=json.loads((ROOT/'design/focus-art-spec.json').read_text(encoding='utf-8'))
    NATIVE.mkdir(parents=True,exist_ok=True);(ART/'exports').mkdir(parents=True,exist_ok=True)
    report=[]
    for asset in spec['assets']:
        source=ART/'source'/(asset['key']+'.png')
        if not source.exists() or (partial and 'source_sha256' not in asset):
            if partial:continue
            raise FileNotFoundError(source)
        im=Image.open(source).convert('RGBA');assert im.getchannel('A').getextrema()==(0,255),source
        assert hashlib.sha256(source.read_bytes()).hexdigest()==asset['source_sha256'],source
        for role,size in [('focus',96),('idea',64),('decision',32)]:
            # Pure resizing/padding: retain the generated pixels and alpha; no
            # repainting, background extraction, or silhouette manipulation.
            fitted=im.copy();fitted.thumbnail((round(size*.9),round(size*.9)),Image.Resampling.LANCZOS)
            result=Image.new('RGBA',(size,size),(0,0,0,0));result.alpha_composite(fitted,((size-fitted.width)//2,(size-fitted.height)//2))
            result.save(ART/'exports'/f'{asset["key"]}-{size}.png');result.save(NATIVE/f'{role}_{asset["key"]}.dds')
        result=Image.new('RGBA',(52,40),(0,0,0,0));small=Image.open(ART/'exports'/f'{asset["key"]}-32.png');result.alpha_composite(small,(10,4));result.save(NATIVE/f'category_{asset["key"]}.dds')
        report.append(dict(key=asset['key'],master_sha256=asset['source_sha256'],source_size=im.size))
    contact(report,spec)
    return report

def contact(rows,spec):
    font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',14);names={a['key']:a['label'] for a in spec['assets']}
    im=Image.new('RGB',(1200,100+((len(rows)+7)//8)*146),'#1c2328');d=ImageDraw.Draw(im)
    d.text((24,22),'法兰西之影 · 国策图标重绘 · 游戏原尺寸96像素',font=ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',23),fill='#efdbad')
    for i,row in enumerate(rows):
        x=27+(i%8)*147;y=82+(i//8)*146
        icon=Image.open(ART/'exports'/f'{row["key"]}-96.png');im.paste(icon,(x+10,y),icon)
        d.text((x+58,y+101),names[row['key']],font=font,anchor='mt',fill='#d5ccac')
    (ART/'review').mkdir(parents=True,exist_ok=True);im.save(ART/'review/CONTACT-96.png')

def apply():
    spec=json.loads((ROOT/'design/focus-art-spec.json').read_text(encoding='utf-8'));keys={a['key'] for a in spec['assets']}
    export();sprites=[]
    for key in sorted(keys):
        for role,name in [('focus','GFX_sof_focus_'+key),('idea','GFX_idea_sof_focus_'+key),('decision','GFX_decision_sof_focus_'+key),('category','GFX_decision_category_sof_focus_'+key)]:
            sprites.append(f'spriteType = {{ name = "{name}" texturefile = "gfx/interface/sof_focus/{role}_{key}.dds" noOfFrames = 1 }}')
    (MOD/'interface/sof_focus_art.gfx').write_text('spriteTypes = {\n'+'\n'.join(sprites)+'\n}\n',encoding='utf-8',newline='\n')
    data=json.loads((ROOT/'design/vanilla-major-remake.json').read_text(encoding='utf-8'));records={n['id']:n for n in data['nodes']};bindings=[]
    for country in ['paris','corsica']:
        path=MOD/'common/national_focus'/f'sofzh_{country}.txt';text=path.read_text(encoding='utf-8-sig');edits=[]
        for node in entries(one(parse(text),'focus_tree').value,'focus'):
            fid=scalar(node.value,'id');r=records[fid];icon=one(node.value,'icon');choice=family(r['donor'],r['title'],icon.value);assert choice in keys
            edits.append((icon.start,icon.end,'icon = GFX_sof_focus_'+choice));bindings.append(dict(id=fid,art=choice,role='focus'));r['art']=choice
        path.write_text(replace(text,edits),encoding='utf-8',newline='\n')
    # Imported country ideas keep all modifiers and adopt a matching icon family.
    path=MOD/'common/ideas/sof_vanilla_major.txt';text=path.read_text(encoding='utf-8');edits=[]
    for node in entries(one(parse(text),'ideas').value,'country')[0].value:
        picture=one(node.value,'picture');choice=family(node.key,'',picture.value);assert choice in keys
        edits.append((picture.start,picture.end,'picture = sof_focus_'+choice));bindings.append(dict(id=node.key,art=choice,role='idea'))
    path.write_text(replace(text,edits),encoding='utf-8',newline='\n')
    dynamic={'SFC_regio_esercito_dynamic_modifier':'army','SFC_regia_marina_dynamic_modifier':'battleship','SFC_regia_aeronautica_dynamic_modifier':'fighter','SFC_ricostruzione_industriale_dynamic_modifier':'civilian_industry','SFC_military_industry_dynamic_modifier':'military_industry'}
    path=MOD/'common/dynamic_modifiers/sof_vanilla_major.txt';text=path.read_text(encoding='utf-8');edits=[]
    for node in parse(text):
        icon=one(node.value,'icon');choice=dynamic[node.key];edits.append((icon.start,icon.end,'icon = GFX_idea_sof_focus_'+choice));bindings.append(dict(id=node.key,art=choice,role='dynamic'))
    path.write_text(replace(text,edits),encoding='utf-8',newline='\n')
    policy={'sof_van_buy_arms':'logistics','sof_van_invest_ally':'civilian_industry','sof_van_train_volunteers':'militia','sof_van_local_police':'security','sof_van_workers_settlement':'workers','sof_van_invite_neighbour':'diplomacy','sof_van_national_assembly':'parliament'}
    path=MOD/'common/decisions/sof_vanilla_major.txt';text=path.read_text(encoding='utf-8');edits=[]
    for node in one(parse(text),'sof_van_native_policies').value:
        icon=one(node.value,'icon');choice=policy[node.key];edits.append((icon.start,icon.end,'icon = sof_focus_'+choice));bindings.append(dict(id=node.key,art=choice,role='decision'))
    path.write_text(replace(text,edits),encoding='utf-8',newline='\n')
    path=MOD/'common/decisions/categories/sof_vanilla_major.txt';text=path.read_text(encoding='utf-8');icon=one(one(parse(text),'sof_van_native_policies').value,'icon');path.write_text(replace(text,[(icon.start,icon.end,'icon = sof_focus_diplomacy')]),encoding='utf-8',newline='\n')
    bindings.append(dict(id='sof_van_native_policies',art='diplomacy',role='category'))
    data['art_style']='Generated local metal emblems';(ROOT/'design/vanilla-major-remake.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    out={'version':data['version'],'assets':len(keys),'bindings':bindings,'usage':dict(collections.Counter(r['art'] for r in bindings)),'game_engine_verified':False}
    (ROOT/'design/focus-art-bindings.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({'ok':True,'assets':len(keys),'bindings':len(bindings),'focuses':sum(b['role']=='focus' for b in bindings)}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--partial',action='store_true');args=parser.parse_args()
    if args.partial:print(json.dumps({'exported':len(export(True))}))
    else:apply()
