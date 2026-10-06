"""Explicit replacements for world-map mechanics that do not exist in SoF.

These are hand mapped semantic adaptations, not generated generic focus chains.
The native graph, research rewards and country-spirit modifiers live in the donor.
"""
WAR = {
 'FRA_the_natural_borders_of_france':'ile-de-france',
 'FRA_bring_home_quebec':'aquitaine','FRA_expand_to_the_suez':'paca',
 'FRA_pre_empt_the_fascist_attack':'lorraine','FRA_grow_the_empire':'centre',
 'ITA_towards_a_greater_italy':'paca','ITA_bend_the_bars':'corsica',
 'ITA_subdue_the_sentinels':'paca','ITA_masters_of_the_mediterranean':'languedoc',
 'ITA_the_fourth_shore':'paca','ITA_support_albanian_irredentism':'rhone-alpes',
 'ITA_claims_on_turkey_bba':'paca','ITA_demand_balearic_islands_bba':'corsica',
 'ITA_condemn_colonialism':'paca',
}
PARTNER = {
 'FRA_reconnect_to_the_balkans':'STR','FRA_loyalty_to_moscow':'MET',
 'FRA_confirm_eastern_commitments':'MET','FRA_join_the_ententes':'ROU',
 'FRA_buy_time':'MET','FRA_concessions_to_italy':'MRS',
 'FRA_ratify_the_stresa_front':'MRS','FRA_reach_out_to_spain':'BRD',
 'FRA_compensate_italy':'MRS','FRA_intervention_in_greece':'MOP',
 'FRA_establish_spheres_of_influence':'MET','FRA_dominate_the_middle_east':'STR',
 'ITA_iberian_protection':'TOU','ITA_south_american_alliances':'NAN',
 'ITA_potential_allies_in_the_balkans':'MOP','ITA_guarantee_austrian_independence':'STR',
 'ITA_negotiate_italian_claims':'PRS','ITA_ratify_the_stresa_front':'PRS',
 'ITA_request_control_of_french_territories':'MRS','ITA_mafia_abroad':'BRD',
 'ITA_negotiations_with_albania':'MRS',
 'ITA_reestablish_old_alliances':'PRS',
}
FACTION = {'FRA_join_comintern':'sof_van_workers_front','FRA_join_germany':'sof_van_eastern_pact','FRA_the_congress_of_paris':'sof_van_paris_congress','ITA_defend_the_land':'sof_van_island_front'}
POLITICAL = {
 'FRA_form_the_popular_front':('democratic',.05),
 'FRA_revive_the_national_bloc':('neutrality',.03),
 'FRA_the_first_citizen_of_the_state':('neutrality',.05),
 'FRA_leftist_rhetoric':('communism',.02),'FRA_right_wing_rhetoric':('fascism',.02),
 'ITA_culto_del_duce':('fascism',.04),'ITA_purge_the_party':('fascism',.02),
 'ITA_the_fate_of_mussolini':('neutrality',.03),
 'ITA_a_leader_steps_forward':('communism',.03),
 'ITA_the_republics_leadership':('democratic',.04),
 'ITA_defy_the_duce':('democratic',-.05),
 'FRA_invite_communist_ministers':('communism',-.03),
}
TECH = {
 'FRA_infantry_tanks':'armor','FRA_rush_the_richelieus':'bb_tech',
 'FRA_prioritize_the_joffre':'cv_tech','ITA_combined_research_effort':'industry',
 'ITA_battaglioni_d_assalto':'infantry_weapons',
 'ITA_special_brigades':'special_forces','ITA_mobilize_the_railway_guns':'artillery',
}
SLOTS = {'FRA_slum_clearing':3,'ITA_regional_development':2,'ITA_the_southern_farmlands':2}
FORTS = {'FRA_alpine_forts','FRA_extend_the_maginot_line','ITA_vallo_alpino_del_littorio','ITA_reinforce_the_gustav_line'}
INFRA = {'ITA_libyan_railway','ITA_litoranea_balbo','ITA_via_della_vittoria'}
MILITIA = {'ITA_strengthen_ascari_corps','ITA_corpo_volontari_della_liberta','ITA_guardia_nazionale_repubblicana','ITA_integrate_polizia_dell_africa_italiana','ITA_albanian_fascist_militia','ITA_enlist_the_bashkimi_kombetar'}
COMPLIANCE = {'FRA_the_blum_viollette_proposal':10,'FRA_french_union':15,'ITA_new_roman_citizens':10,'ITA_abolish_the_colonies':15}

def actions(b,key,donor,borrowed):
    if key=='ITA_aid_for_the_spanish_republic':
        # The donor sent 10,000 volunteers through a removed SPR event chain.
        # A local training policy must not permanently destroy that manpower.
        return [a for a in borrowed if not a.startswith('add_manpower = -')]+['set_country_flag = sof_van_volunteer_program','army_experience = 20']
    if key in WAR:
        return b.goal(WAR[key])
    if key in PARTNER:return b.offer(PARTNER[key])
    if key in FACTION:
        faction=FACTION[key]
        return ['set_rule = { can_create_factions = yes }',f'if = {{ limit = {{ is_in_faction = no }} create_faction = {faction} }}','set_country_flag = sof_van_coalition_enabled']
    if key in POLITICAL:
        ideology,stability=POLITICAL[key]
        return [f'set_politics = {{ ruling_party = {ideology} elections_allowed = '+('yes' if ideology=='democratic' else 'no')+' }',f'add_popularity = {{ ideology = {ideology} popularity = 0.10 }}',f'add_stability = {stability}']+(['mark_focus_tree_layout_dirty = yes'] if donor=='italy' else [])
    if key in TECH:return [f'add_tech_bonus = {{ name = {b.namespace(key,donor)} bonus = 0.5 uses = 1 category = {TECH[key]} }}']
    if key in FORTS:return [b.building('bunker')]
    if key in INFRA:return [b.building('infrastructure')]
    if key in SLOTS:return ['random_owned_controlled_state = { limit = { sofzh_unification_french_state = yes is_fully_controlled_by = ROOT } add_extra_state_shared_building_slots = '+str(SLOTS[key])+' }']
    if key in MILITIA:
        return ['if = { limit = { NOT = { has_template = "岛内守备旅" } } division_template = { name = "岛内守备旅" regiments = { infantry = { x = 0 y = 0 } infantry = { x = 0 y = 1 } infantry = { x = 1 y = 0 } infantry = { x = 1 y = 1 } } } }','add_manpower = 800','add_equipment_to_stockpile = { type = infantry_equipment_0 amount = 200 producer = ROOT }']
    if key in COMPLIANCE:
        return ['every_owned_state = { limit = { sofzh_unification_french_state = yes is_fully_controlled_by = ROOT has_resistance = yes } add_compliance = '+str(COMPLIANCE[key])+' }','add_stability = 0.03']
    if key in ['FRA_encourage_immigration','FRA_foreign_guest_workers']:
        idea=b.import_idea('FRA_full_employment',donor)
        return ['remove_ideas = '+idea,'add_manpower = 1000']
    if key=='FRA_destroy_the_counter_revolution':return ['add_stability = -0.03','add_popularity = { ideology = communism popularity = 0.15 }','add_political_power = -25']
    if key=='FRA_force_the_issue':return ['set_politics = { ruling_party = communism elections_allowed = no }','add_stability = -0.05','remove_ideas = '+b.import_idea('FRA_disjointed_government',donor)]
    if key in ['FRA_ban_the_leagues','FRA_ban_communism']:return ['add_stability = -0.02','add_popularity = { ideology = democratic popularity = 0.05 }','add_political_power = 50']
    if key=='ITA_defense_against_capitalism':return ['add_war_support = 0.05']
    if key=='ITA_european_democracies':return b.offer('PRS')+['add_stability = 0.03']
    if key=='ITA_new_colonial_policies':return ['add_political_power = 75','every_owned_state = { limit = { sofzh_unification_french_state = yes is_fully_controlled_by = ROOT has_resistance = yes } add_compliance = 5 }']
    if key=='FRA_diplomatic_freedom':return ['set_rule = { can_create_factions = yes }','add_political_power = 75']
    if key=='FRA_invest_in_our_weaker_allies':return ['set_country_flag = sof_van_allied_investment']
    if key=='FRA_arms_purchases_in_the_us':return ['set_country_flag = sof_van_arms_market']
    if key=='FRA_intervention_in_spain':return ['set_country_flag = sof_van_volunteer_program']
    if key in ['ITA_polizia_dell_africa_italiana','ITA_organize_strikes_in_the_north']:
        return ['set_country_flag = sof_van_police_reform' if 'polizia' in key else 'set_country_flag = sof_van_strike_program']
    if key in ['ITA_independence_rds','ITA_independence_rsi']:
        return ['add_stability = 0.05','add_political_power = 50','set_rule = { can_create_factions = yes }']
    if key=='ITA_catholic_action':return ['add_stability = 0.05','add_popularity = { ideology = neutrality popularity = 0.05 }']
    if key=='ITA_peace_preservation':return ['set_country_flag = sof_van_coalition_enabled','add_war_support = -0.05','add_stability = 0.05']
    if key=='ITA_cooperatives_for_intensive_exploitation':return ['add_to_variable = { SFC_iri_local_resources_factor = 0.05 }']
    if key=='ITA_albanian_occupation':return ['set_country_flag = sof_van_police_reform','add_stability = 0.02']
    if key=='ITA_the_italian_liberation_war':return ['set_country_flag = sofzh_unification_war_ready','add_manpower = 1000','army_experience = 15']
    if key=='ITA_the_italian_social_republic':return ['set_country_flag = sofzh_unification_war_ready','add_equipment_to_stockpile = { type = infantry_equipment_0 amount = 200 producer = ROOT }','army_experience = 15']
    return borrowed
