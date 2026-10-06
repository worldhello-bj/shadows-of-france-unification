"""Chinese descriptions derived from the actual ideology idea modifiers."""
from decimal import Decimal
from hoi4_script import parse, one

LABELS = {
    'research_speed_factor': '科研速度',
    'production_speed_industrial_complex_factor': '民用工厂建设速度',
    'line_change_production_efficiency_factor': '更换生产线效率保留',
    'consumer_goods_factor': '消费品工厂系数',
    'stability_factor': '稳定度', 'political_power_gain': '每日政治点数',
    'required_garrison_factor': '驻军需求',
    'production_factory_start_efficiency_factor': '初始生产效率',
    'conscription_factor': '适役人口系数', 'industrial_capacity_factory': '工厂产出',
    'casualty_trickleback': '伤兵回归', 'industry_repair_factor': '工业修复速度',
    'mobilization_speed': '动员速度',
    'production_speed_arms_factory_factor': '军用工厂建设速度',
    'experience_gain_army_factor': '陆军经验获取',
    'political_power_factor': '政治点数获取',
    'production_factory_efficiency_gain_factor': '生产效率增长',
    'planning_speed': '计划速度', 'supply_consumption_factor': '补给消耗',
    'army_morale_factor': '陆军组织度恢复', 'war_support_factor': '战争支持度',
    'army_attack_factor': '陆军攻击', 'conscription': '适役人口',
    'army_org_factor': '陆军组织度',
    'production_factory_max_efficiency_factor': '生产效率上限',
    'industrial_capacity_dockyard': '船坞产出',
    'command_power_gain_mult': '指挥点数增长', 'land_reinforce_rate': '增援率',
    'production_speed_infrastructure_factor': '基础设施建设速度',
    'compliance_gain': '每日顺从度增长',
}


def bonuses(mod, ident):
    text = (mod / 'common/ideas/sofzh_ideologies.txt').read_text(encoding='utf-8-sig')
    country = one(one(parse(text), 'ideas').value, 'country').value
    rows = one(one(country, 'sofzh_ideology_' + ident).value, 'modifier').value
    result = []
    for row in rows:
        value = Decimal(row.value)
        raw = row.key in ('political_power_gain', 'compliance_gain')
        number = format(abs(value if raw else value * 100), 'f')
        if '.' in number:
            number = number.rstrip('0').rstrip('.')
        unit = '个百分点' if row.key in ('conscription', 'casualty_trickleback', 'land_reinforce_rate', 'compliance_gain') else '' if raw else '%'
        result.append(f'{LABELS[row.key]} {"+" if value >= 0 else "−"}{number}{unit}')
    assert len(result) == 4
    return '；'.join(result) + '。'
