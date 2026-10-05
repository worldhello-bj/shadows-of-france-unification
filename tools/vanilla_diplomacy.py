"""Native decision/event UI for mechanisms formerly implemented by foreign events."""
from build_vanilla_remake import save,baseline

def write(b):
    save('mod/events/sof_vanilla_diplomacy.txt','''add_namespace = sof_van_diplomacy
country_event = {
 id = sof_van_diplomacy.1 title = sof_van_diplomacy.1.t desc = sof_van_diplomacy.1.d
 is_triggered_only = yes
 trigger = { sofzh_unification_candidate = yes has_war = no FROM = { sofzh_unification_candidate = yes has_war = no } NOT = { tag = FROM } }
 option = { name = sof_van_accept ai_chance = { factor = 40 modifier = { factor = 2 has_government = FROM } }
  diplomatic_relation = { country = FROM relation = non_aggression_pact active = yes }
  add_stability = 0.02 FROM = { add_stability = 0.02 }
  if = { limit = { is_in_faction = no has_government = FROM FROM = { is_faction_leader = yes } } FROM = { add_to_faction = ROOT } }
 }
 option = { name = sof_van_decline ai_chance = { factor = 60 } FROM = { country_event = { id = sof_van_diplomacy.2 days = 1 } } }
}
country_event = { id = sof_van_diplomacy.2 title = sof_van_diplomacy.2.t desc = sof_van_diplomacy.2.d is_triggered_only = yes option = { name = sof_van_acknowledge } }
''')
    save('mod/common/decisions/categories/sof_vanilla_major.txt','''sof_van_native_policies = { icon = sof_cw_accord priority = 43 visible = { OR = { has_focus_tree = sofzh_paris has_focus_tree = sofzh_corsica } } }
''')
    save('mod/common/decisions/sof_vanilla_major.txt','''sof_van_native_policies = {
 sof_van_buy_arms = { icon = sof_cw_supply cost = 75 days_re_enable = 180 visible = { has_country_flag = sof_van_arms_market } available = { has_war = no is_subject = no } complete_effect = { add_equipment_to_stockpile = { type = infantry_equipment_0 amount = 200 producer = ROOT } add_equipment_to_stockpile = { type = support_equipment_1 amount = 25 producer = ROOT } } ai_will_do = { factor = 0.2 } }
 sof_van_invest_ally = { icon = sof_cw_civil cost = 75 days_re_enable = 180 visible = { has_country_flag = sof_van_allied_investment } available = { has_war = no any_other_country = { is_in_faction_with = ROOT NOT = { tag = ROOT } any_owned_state = { is_fully_controlled_by = PREV sofzh_unification_french_state = yes free_building_slots = { building = industrial_complex size > 0 } } } } complete_effect = { random_other_country = { limit = { is_in_faction_with = ROOT NOT = { tag = ROOT } any_owned_state = { is_fully_controlled_by = PREV sofzh_unification_french_state = yes free_building_slots = { building = industrial_complex size > 0 } } } random_owned_controlled_state = { limit = { is_fully_controlled_by = PREV sofzh_unification_french_state = yes free_building_slots = { building = industrial_complex size > 0 } } add_building_construction = { type = industrial_complex level = 1 instant_build = yes } } } } ai_will_do = { factor = 0.1 } }
 sof_van_train_volunteers = { icon = sof_cw_specialty cost = 50 days_re_enable = 180 visible = { has_country_flag = sof_van_volunteer_program } available = { has_equipment = { infantry_equipment > 99 } } complete_effect = { add_equipment_to_stockpile = { type = infantry_equipment amount = -100 producer = ROOT } army_experience = 15 } ai_will_do = { factor = 0.2 } }
 sof_van_local_police = { icon = sof_cw_sweep cost = 50 days_re_enable = 180 visible = { has_country_flag = sof_van_police_reform } available = { any_owned_state = { sofzh_unification_french_state = yes is_fully_controlled_by = ROOT has_resistance = yes } } complete_effect = { every_owned_state = { limit = { sofzh_unification_french_state = yes is_fully_controlled_by = ROOT has_resistance = yes } add_compliance = 5 } } ai_will_do = { factor = 0.2 } }
 sof_van_workers_settlement = { icon = sof_cw_civil cost = 50 days_re_enable = 180 visible = { has_country_flag = sof_van_strike_program } available = { has_war = no stability < 0.8 } complete_effect = { add_stability = 0.03 } ai_will_do = { factor = 0.3 } }
 sof_van_invite_neighbour = { icon = sof_cw_pact cost = 35 days_re_enable = 180 visible = { has_country_flag = sof_van_coalition_enabled } available = { has_war = no is_faction_leader = yes any_neighbor_country = { sofzh_unification_candidate = yes is_in_faction = no has_war = no has_government = ROOT NOT = { has_non_aggression_pact_with = ROOT } } } complete_effect = { random_neighbor_country = { limit = { sofzh_unification_candidate = yes is_in_faction = no has_war = no has_government = ROOT NOT = { has_non_aggression_pact_with = ROOT } } country_event = { id = sof_van_diplomacy.1 days = 1 } } } ai_will_do = { factor = 0.2 } }
 sof_van_national_assembly = { icon = sof_cw_register cost = 100 fire_only_once = yes visible = { has_country_flag = sofzh_unification_started NOT = { has_country_flag = sof_van_national_congress } } available = { is_subject = no has_war = no num_of_controlled_states > 20 } complete_effect = { set_country_flag = sof_van_national_congress add_stability = 0.03 } ai_will_do = { factor = 2 } }
}
''')
    # Keep generic-country congress gates; give the native transplants an actual
    # local assembly gate so they can still use the established proclamation.
    formable=baseline('mod/common/decisions/SOF_formable_nation_decisions.txt')
    formable=formable.replace('OR = { has_completed_focus = SOF_UNIFY_national_congress has_completed_focus = SOF_COR_national_congress has_completed_focus = SOF_PRS_national_congress }','OR = { has_completed_focus = SOF_UNIFY_national_congress has_completed_focus = SOF_COR_national_congress has_completed_focus = SOF_PRS_national_congress has_country_flag = sof_van_national_congress }')
    save('mod/common/decisions/SOF_formable_nation_decisions.txt',formable)
    b.loc.update({
     'sof_van_native_policies':'政府政策与地区合作','sof_van_native_policies_desc':'国策授权的采购、援助、治安与合作方案。费用和实际收益列于各项决议。',
     'sof_van_diplomacy.1.t':'地区合作提案','sof_van_diplomacy.1.d':'[From.GetName]提议签署互不侵犯协定。若双方政体相同且提案国领导阵营，接受提案也将加入其阵营。',
     'sof_van_diplomacy.2.t':'合作提案遭拒','sof_van_diplomacy.2.d':'[From.GetName]拒绝了我们的合作方案。外交道路仍需耐心。',
     'sof_van_accept':'接受合作','sof_van_decline':'保持独立','sof_van_acknowledge':'继续谈判',
     'sof_van_buy_arms':'向地区市场采购武器','sof_van_buy_arms_desc':'支付75政治点数，购入200件基础步兵装备和25件支援装备。每180天可执行一次。',
     'sof_van_invest_ally':'援建盟友工厂','sof_van_invest_ally_desc':'支付75政治点数，为一名阵营盟友在有空位且完整控制的法国地区建设一座民用工厂。',
     'sof_van_train_volunteers':'组织志愿军训练','sof_van_train_volunteers_desc':'投入50政治点数和100件步兵装备，获得15陆军经验。',
     'sof_van_local_police':'推行地方警务改革','sof_van_local_police_desc':'支付50政治点数，使完整控制且存在抵抗的法国地区顺从度增加5。',
     'sof_van_workers_settlement':'与工人代表和解','sof_van_workers_settlement_desc':'支付50政治点数，稳定度增加3个百分点。',
     'sof_van_invite_neighbour':'向同政体邻国提议合作','sof_van_invite_neighbour_desc':'支付35政治点数，向一名符合条件的邻国发出合作提案，对方可以拒绝。',
     'sof_van_national_assembly':'召开全国代表会议','sof_van_national_assembly_desc':'和平时控制超过20个地区后，支付100政治点数召开全国代表会议。完成后取得统一宣告的政治授权；最终宣告仍须拥有并完整控制全法国。',
     'sof_van_workers_front':'法国工人共同阵线','sof_van_eastern_pact':'法国东方协约','sof_van_paris_congress':'巴黎地区会议','sof_van_island_front':'岛内社会主义阵线',
    })
