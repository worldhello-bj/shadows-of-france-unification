"""Review native portrait crops, focus gates and actual cabinet bonuses."""
import base64,html,io,json,re
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from hoi4_script import parse,one,scalar

ROOT=Path(__file__).resolve().parent.parent;MOD=ROOT/'mod'
LABELS={'stability_factor':'稳定度','political_power_factor':'政治点数获取','consumer_goods_factor':'消费品工厂系数','production_factory_efficiency_gain_factor':'生产效率增长','army_org_factor':'陆军组织度','compliance_gain':'每日顺从度','required_garrison_factor':'驻军需求','army_defence_factor':'陆军防御','dig_in_speed_factor':'堑壕速度','army_attack_factor':'陆军攻击','planning_speed':'计划速度','max_planning_factor':'最大计划','war_support_factor':'战争支持度','improve_relations_maintain_cost_factor':'改善关系花费','production_speed_industrial_complex_factor':'民用工厂建设','industrial_capacity_factory':'工厂产出','production_factory_max_efficiency_factor':'生产效率上限','production_speed_arms_factory_factor':'军用工厂建设','industrial_capacity_dockyard':'船厂产出','navy_org_factor':'海军组织度','naval_coordination':'海军协调','research_speed_factor':'研究速度','industrial_research_speed_factor':'工业研究','air_attack_factor':'空军攻击','air_mission_efficiency':'空军任务效率','mobilization_speed':'动员速度','resistance_target':'抵抗目标','production_speed_infrastructure_factor':'基建速度','supply_consumption_factor':'补给消耗','army_morale_factor':'陆军恢复速度','training_time_army_factor':'陆军训练时间','electronics_research_speed_factor':'电子研究','research_sharing_per_country_bonus_factor':'每国研究共享比例'}

def bonus(k,v):return LABELS[k]+' '+(f'{v:+.3f}' if k=='compliance_gain' else f'{v:+.0%}')

def main():
    data=json.loads((ROOT/'design/historical-cabinet.json').read_text(encoding='utf-8'));out=ROOT/'docs/previews'/data['version'];out.mkdir(parents=True,exist_ok=True)
    loc=dict(re.findall(r'(?m)^\s+([^\s:]+):\d*\s+"((?:[^"\\]|\\.)*)"',(MOD/'localisation/simp_chinese/replace/sof_vanilla_major_l_simp_chinese.yml').read_text(encoding='utf-8-sig')))
    css='body{background:#182025;color:#e4dbc4;margin:24px auto;max-width:1280px;font:16px Microsoft YaHei;line-height:1.7;padding:0 22px}h1,h2{color:#d8bd78}p,small{color:#a9b8bb}a{color:#d8bd78}button,input{font:inherit;background:#29343b;color:#e4dbc4;border:1px solid #57636a;padding:7px 14px;margin-right:8px}button[aria-pressed=true]{border-color:#d8bd78;color:#d8bd78}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(355px,1fr));gap:14px}article{border:1px solid #46545b;padding:16px;background:#222d33}article img{width:65px;height:67px;float:left;margin:0 14px 8px 0}h3{margin:0;color:#ead6a9;font-size:18px}.route{clear:both;font-size:14px}.bonus{color:#8cc89c;font-size:15px}.hidden{display:none}'
    page=f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>历史内阁 · {data["version"]}</title><style>{css}</style><h1>巴黎与科西嘉 · 历史内阁</h1><p>版本 {data["version"]} · 40位历史成员 · 八个原生政治栏位。画像为本机原版人物资产，按原生顾问尺寸65×67排版。此页展示实际源码配置，尚非游戏截图。</p><p>普通任命125政治点数，同栏一人，调整冷却90天。领袖国策免费任命行政首席。执政方向不符、被清洗或退休后退出内阁。</p><p><a href="INDEX.html">国策布局</a> · <a href="TEXT.html">国策解锁描述</a> · <a href="HISTORICAL.png">画像与职位总览</a></p><p><button data-filter="all" aria-pressed="true">全部</button><button data-filter="FRA" aria-pressed="false">巴黎11位</button><button data-filter="ITA" aria-pressed="false">科西嘉29位</button><input id="search" placeholder="查姓名、职位或解锁国策" aria-label="查姓名、职位或解锁国策"></p>'
    gov={'democratic':'民主','neutrality':'中立','fascism':'法西斯','communism':'共产主义'}
    report=['# 历史内阁迁移 · '+data['version'],'','40位成员沿用原版姓名与肖像，进入现有八个政治栏位。其他国家的24位通用成员与153项通用国策继续保留。普通任命125政治点数，同栏互换，冷却90天。','', '| 国家 | 成员 | 职位 | 解锁国策 | 执政方向 | 专长 |','|---|---|---|---|---|---|']
    for slot,slotname in data['slots'].items():
        page+=f'<section><h2>{slotname}</h2><div class="grid">'
        for p in [x for x in data['members'] if x['slot']==slot]:
            country='巴黎' if p['source'].startswith('FRA_') else '科西嘉';pre='SFP_' if country=='巴黎' else 'SFC_';routes=' / '.join(loc[pre+x] for x in p['focuses']);governments='、'.join(gov[x] for x in p['governments']) or '不限';bonuses='；'.join(bonus(k,v) for k,v in p['modifiers'].items())
            im=Image.open(MOD/p['portrait']);buf=io.BytesIO();im.save(buf,format='PNG');encoded=base64.b64encode(buf.getvalue()).decode('ascii')
            page+=f'<article data-country="{p["source"][:3]}"><img src="data:image/png;base64,{encoded}" alt="{html.escape(p["name"])}"><h3>{html.escape(p["name"])}</h3><small>{country} · {slotname} · {governments}</small><p class="route">解锁：{html.escape(routes)}</p><p class="bonus">{html.escape(bonuses)}</p>'
            if p['retired']:page+='<p class="route">退出条件：完成'+html.escape(' / '.join(loc[pre+x] for x in p['retired']))+'</p>'
            page+='</article>'
            report.append(f'| {country} | {p["name"]} | {slotname} | {routes} | {governments} | {bonuses} |')
        page+='</div></section>'
    page+='<script>let filter="all";const update=()=>{let query=document.querySelector("#search").value.trim().toLowerCase();document.querySelectorAll("article").forEach(a=>a.classList.toggle("hidden",(filter!=="all"&&a.dataset.country!==filter)||!a.textContent.toLowerCase().includes(query)));document.querySelectorAll("section").forEach(s=>s.classList.toggle("hidden",!s.querySelector("article:not(.hidden)")))};document.querySelectorAll("button").forEach(b=>b.onclick=()=>{filter=b.dataset.filter;document.querySelectorAll("button").forEach(x=>x.setAttribute("aria-pressed",String(x===b)));update()});document.querySelector("#search").oninput=update;</script></html>'
    (out/'HISTORICAL.html').write_text(page,encoding='utf-8',newline='\n')
    image=Image.new('RGB',(1320,1530),'#182025');d=ImageDraw.Draw(image);font=lambda s:ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',s)
    for i,p in enumerate(data['members']):
        x=i%4*330;y=i//4*153;d.rectangle((x+5,y+5,x+325,y+147),fill='#222d33',outline='#46545b');im=Image.open(MOD/p['portrait']).convert('RGBA');image.paste(im,(x+17,y+20),im)
        name=p['name'];lines=[name[j:j+11] for j in range(0,len(name),11)]
        for j,line in enumerate(lines):d.text((x+95,y+17+j*24),line,font=font(17),fill='#ead6a9')
        d.text((x+95,y+73),('巴黎' if p['source'].startswith('FRA_') else '科西嘉')+' · '+data['slots'][p['slot']],font=font(15),fill='#afbdbe')
        key,v=next(iter(p['modifiers'].items()));d.text((x+17,y+113),bonus(key,v),font=font(16),fill='#8cc89c')
    image.save(out/'HISTORICAL.png')
    report+=['','12项领袖国策使用独立人物定义并实际任命；领袖角色不再额外叠加同一内阁加成。旧4.0存档按照已完成国策一次性补发，保留原有动态数值和永久地形经验。','','修复两个空军事精神：东方威胁给予陆军攻击+10%；反对集权主义给予陆军攻击+5%、防御+15%，保留原国策期限。四项战役动员领取后等待战争，参战后的和平或统一完成时撤销；两项联邦领导精神要求至少一个附属国。','','地区科研合作组提供每名掌握技术的伙伴15%基础追赶加成，合作精神将该比例提高25%；盟友自动加入，退出阵营时撤销本组成员资格和本组精神。','','移除不会触发原版事件的空“政治暴力”开局标记；支援共和国国策改为解锁志愿军训练与20陆军经验，删除未投送给伙伴却扣除10000人力的旧效果。','','原版大国布局、48幅重绘国策徽章、永久地形经验、通用决议界面保留。源码与状态迁移测试通过；游戏加载、实际旧存档和长期平衡尚需实机验收。']
    target=ROOT/'docs/reports'/data['version'];target.mkdir(parents=True,exist_ok=True);(target/'HISTORICAL-MIGRATION.md').write_text('\n'.join(report)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(ok=True,members=len(data['members']),preview=str(out/'HISTORICAL.html')),ensure_ascii=False))

if __name__=='__main__':main()
