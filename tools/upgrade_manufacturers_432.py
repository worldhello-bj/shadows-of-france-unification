"""Author the eight-tier extension from the immutable 4.3.0 manufacturer design."""
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASELINE = '191dfc9a1b131337e4c3de8de1c27cdb91ceab1a'
TAIL_NAMES = {
    'PRS': ['均质装甲轧制', '重载悬挂总成', '弹道铸件试验', '比扬古装甲平台'],
    'LIL': ['矿尘密封总成', '重载反坦克炮架', '煤钢耐磨结构', '北方重械车辆谱系'],
    'MET': ['高压炮膛冶炼', '破片弹道试验', '长炮管精锻', '洛林精密火炮'],
    'STR': ['耐久枪机锁闭', '精密穿甲瞄具', '稳固射击支架', '莱茵守备军械'],
    'ROU': ['深弹投送装置', '海峡听音阵列', '反潜射控协同', '塞纳护航猎手'],
    'LYO': ['高压柴油喷射', '传动总成寿命', '长途燃油试验', '罗讷柴油车队'],
    'MRS': ['高速船体线型', '盐雾密封设备', '近海推进试验', '地中海巡护轮机'],
    'BRD': ['海面攻击校准', '大西洋导航系统', '对舰投弹挂架', '阿基坦海航体系'],
    'TOU': ['远程油箱配置', '协同攻击挂架', '长航时机体结构', '南方远程航空'],
    'NAN': ['表面硬化舰甲', '耐久主机总成', '分段装甲连接', '彭奥埃重舰平台'],
    'REN': ['深水耐压试验', '鱼雷发射总成', '轴系密封维护', '布列塔尼深海潜航'],
    'CFR': ['高原耐磨胎面', '低滚阻车轮', '复合橡胶配方', '米其林军用轮胎'],
    'DIJ': ['装甲列车防空阵列', '防护车厢结构', '列车射控协同', '勃艮第军运平台'],
    'BES': ['密封测量装置', '轻便仪器壳体', '精密校验台架', '汝拉军用仪器'],
    'TRS': ['模块化运输底盘', '长途燃油过滤', '民用部件军需化', '卢瓦尔运输平台'],
    'AMI': ['冲压军需组件', '耐久维修套件', '统一供给规格', '皮卡第军需体系'],
    'CHL': ['炮座稳定锚定', '精密射角调节', '高强度支撑机构', '香槟纵深炮械'],
    'MOP': ['防潮通信接插件', '轻型接收机壳', '密封电台检验', '南岸军用通信'],
    'POI': ['枪械冲压夹具', '耐久枪机试验', '军械装配协同', '沙泰勒罗制式武器'],
    'AJC': ['海岛防潮枪机', '山地守备枪架', '密封枪械导轨', '科西嘉山地军械'],
}


def build_design():
    raw = subprocess.check_output(['git', '-c', 'safe.directory=' + ROOT.as_posix(),
        'show', BASELINE + ':design/regional-manufacturers.json'], cwd=ROOT)
    data = json.loads(raw)
    data.update(schema_version=2, version='4.3.2', tier_count=8, traits_per_company=16,
        research_bonus=.15, task_capacity=3, baseline_commit=BASELINE,
        initial_organization={'military_industrial_organization_funds_gain': .25},
        numeric_caps={'equipment': .45, 'equipment_cost': .30, 'production': .20},
        vanilla_reference='design/vanilla-mio-growth-reference.json',
        old_save_compatibility='Organization IDs and trait_1 through trait_4 are retained; new tokens are appended.')
    for row in data['manufacturers']:
        initial = row['initial_equipment']
        main, old = next(iter(initial.items()))
        sign = -1 if main in ['build_cost_ic', 'fuel_consumption'] else 1
        initial[main] = sign * (.08 if abs(old) == .04 else .10)
        old_traits = row['traits']
        secondary, secondary_old = next(iter(old_traits[2]['equipment'].items()))
        for i, trait in enumerate(old_traits):
            trait.update(token_suffix=i+1, tier=i+1, branch='quality', parents=[i] if i else [])
            if i in [0, 3]:
                trait['equipment'][main] = sign * (.03 if main == 'build_cost_ic' else .05)
            if i == 1:
                trait['production']['production_efficiency_gain_factor'] = .06
            if i == 2:
                trait['equipment'][secondary] = round(secondary_old * 2, 6)
            if i == 3:
                trait['production']['production_resource_need_factor'] = -.04
            if i >= 2:
                trait['gate'] = 'specialize'
        for i, name in enumerate(TAIL_NAMES[row['tag']]):
            effects = [
                {main: sign * (.04 if main == 'build_cost_ic' else .08)},
                {secondary: -.04 if secondary == 'build_cost_ic' else (-.06 if secondary_old < 0 else .06)},
                {main: sign * (.04 if main == 'build_cost_ic' else .07)},
                {main: sign * (.03 if main == 'build_cost_ic' else .05),
                 secondary: -.03 if secondary == 'build_cost_ic' else (-.04 if secondary_old < 0 else .04)},
            ][i]
            old_traits.append(dict(name=name, token_suffix=i+5, tier=i+5, branch='quality',
                parents=[i+4], gate='specialize' if i == 0 else 'capstone',
                icon='GFX_sof_reg_trait_reliability' if secondary == 'reliability' else 'GFX_sof_reg_trait_production_capacity',
                equipment=effects))
        names = ['订单统筹', '专用装配线', '材料回收协作', '工场扩建融资',
                 '熟练工人培训', '批量采购合同', '连续生产调度', '工业研究中心']
        production = [{'production_cost_factor': -.04}, {'production_efficiency_cap_factor': .06},
            {'production_resource_need_factor': -.04}, {}, {'production_efficiency_gain_factor': .06},
            {'production_cost_factor': -.04}, {'production_efficiency_cap_factor': .06}, {'production_cost_factor': -.04}]
        for i, name in enumerate(names):
            trait = dict(name=row['factory_name'] + name, token_suffix=i+9, tier=i+1,
                branch='production', parents=[i+8] if i else [], icon='GFX_sof_reg_trait_efficiency_gain')
            if production[i]:
                trait['production'] = production[i]
            if i == 3:
                trait['organization'] = {'military_industrial_organization_funds_gain': .25}
            if i == 7:
                trait['organization'] = {'military_industrial_organization_research_bonus': .05,
                                         'military_industrial_organization_task_capacity': 1}
            if i >= 2:
                trait['gate'] = 'specialize' if i < 5 else 'capstone'
            old_traits.append(trait)
    path = ROOT / 'design/regional-manufacturers.json'
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(dict(companies=20, tiers=8, traits=320, version=data['version'])))


if __name__ == '__main__':
    build_design()
