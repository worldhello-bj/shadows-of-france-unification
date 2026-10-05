"""Show the actual eight-tier native company graph and its cumulative rewards."""
import html
import json
from pathlib import Path
from PIL import Image
from build_regional_manufacturers import stats_text, totals

ROOT = Path(__file__).resolve().parents[1]


def main():
    data = json.loads((ROOT / 'design/regional-manufacturers.json').read_text(encoding='utf-8'))
    version = data['version']
    out = ROOT / 'docs/previews' / version
    out.mkdir(parents=True, exist_ok=True)
    css = '''body{background:#1b2328;color:#e2dacb;font:16px "Microsoft YaHei",sans-serif;margin:24px auto;max-width:1380px;padding:0 24px;line-height:1.65}h1,h2{color:#d6bd88}a{color:#d9bf85}input,select{background:#29333a;color:#e5ddd0;border:1px solid #777;padding:9px;font:inherit;margin:0 12px 14px 0}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(540px,100%),1fr));gap:20px;align-items:start}article{border:1px solid #656c69;background:#273138;padding:20px}img{width:64px;height:64px;float:right}small{color:#aeb9bd}.stats{color:#e9ce9c}.initial,.full{border-left:3px solid #cfb579;background:#202a31;padding:12px;margin:12px 0}.full{border-color:#87b99f}strong{color:#e1c993}summary{cursor:pointer;color:#d9bf85;padding:12px 0}.tier,.tree-head{display:grid;grid-template-columns:25px 1fr 1fr;gap:12px}.tier{padding:13px 0;align-items:stretch}.tier-no{color:#b8ab91;font-weight:bold;padding-top:10px}.node{background:#1c282d;border:1px solid #697470;padding:12px;position:relative;min-width:0;font-size:14px}.node small{display:block;margin-top:7px}.node:not(.last):after{content:"↓";position:absolute;bottom:-24px;left:50%;color:#ae9565}.production{border-color:#668798}.hidden{display:none}.tree-head{color:#d6bd88;font-weight:bold;font-size:14px}@media(max-width:550px){body{padding:0 12px}.tier,.tree-head{gap:7px;grid-template-columns:18px 1fr 1fr}.node{padding:8px;font-size:12px}}'''
    e = html.escape
    page = f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>地区制造商 · {version}</title><style>{css}</style><h1>地区制造商 · {version}</h1><p>20家企业，每家8层、两条可兼修成长线、16项特质。沿用原版军工组织经验和点数；第3–5层要求先进工业，第6–8层要求后续军工建设，各国实际国策名称列在节点下方。</p><p>起始专长8–10%；满成长主打性能通常38–40%。专项科研15%→20%，组织经费获取+25%→+50%，并行任务3→4。制造商只影响承接的装备、生产线与自身组织。此页为源码预览，非游戏截图。</p><p><a href="../4.3.0/INDEX.html">国策布局</a> · <a href="../../MANUFACTURERS-4.3.2-ZH.md">强化数值与原版参照</a></p><input id="q" placeholder="查国家、企业或装备" aria-label="筛选制造商"><select id="mode" aria-label="制造商版本"><option value="mio">军工组织完整成长</option><option value="legacy">无AAT：传统设计商起始工艺</option></select><div class="grid">'''
    for row in data['manufacturers']:
        source = next(a for a in data['native_art_assets'] if a['sprite'] == 'GFX_idea_' + row['picture'])
        Image.open(ROOT / source['destination']).convert('RGBA').save(out / (row['tag'] + '-COMPANY.png'))
        initial = stats_text(row['initial_equipment'])
        full = totals(row, data)
        full_summary = '；'.join(stats_text(full[g]) for g in ['equipment','production'])
        page += f'''<article><img src="{row['tag']}-COMPANY.png" alt="{e(row['name'])}"><h2>{row['tag']} · {e(row['region_name'])}</h2><strong>{e(row['name'])}</strong><p>{e(row['description'])}</p><p>主打：{e(row['equipment_name'])}<br>厂址：{e(row['factory_name'])}（州{row['factory_state']}）<br>解锁：{e(' / '.join(row['unlock_names']))}</p><div class="initial">起始工艺<div class="stats">{e(initial)}</div><small>专项科研+15%；军工组织另有经费获取+25%、3项并行任务。</small></div><div class="full growth">满成长合计<div class="stats">{e(full_summary)}</div><small>专项科研+20% · 经费获取+50% · 4项并行任务</small></div><details class="growth" {'open' if row['tag']=='PRS' else ''}><summary>展开8层成长 · 16项特质</summary><div class="tree-head"><span></span><span>地方工程</span><span>工场协作</span></div>'''
        for tier in range(1,9):
            page += f'<section class="tier"><span class="tier-no">{tier}</span>'
            for branch in ['quality','production']:
                trait = next(t for t in row['traits'] if t['tier']==tier and t['branch']==branch)
                values = '；'.join(stats_text(trait[g]) for g in ['equipment','production','organization'] if trait.get(g))
                requirement = '通过组织经验与特质点解锁'
                if trait.get('gate'):
                    requirement += '，并完成' + ' / '.join(row[trait['gate'] + '_names'])
                page += f'<div class="node {branch} {"last" if tier==8 else ""}"><strong>{e(trait["name"])}</strong><div class="stats">{e(values)}</div><small>{e(requirement)}</small></div>'
            page += '</section>'
        page += '</details><small>传统设计商：125政治点聘用，专项科研+15%，装备工艺取起始值，失去厂址后撤销。旧组织ID及已选的四个旧特质token保留；真实旧档与原生详情页仍待实机验收。</small></article>'
    page += '''</div><script>const q=document.querySelector('#q'),m=document.querySelector('#mode');q.oninput=()=>document.querySelectorAll('article').forEach(a=>a.classList.toggle('hidden',!a.textContent.toLowerCase().includes(q.value.toLowerCase())));m.onchange=()=>document.querySelectorAll('.growth').forEach(x=>x.classList.toggle('hidden',m.value==='legacy'));</script></html>'''
    (out / 'MANUFACTURERS.html').write_text(page, encoding='utf-8', newline='\n')
    print(json.dumps(dict(companies=20, tiers=8, traits=320, preview=str(out/'MANUFACTURERS.html'))))


if __name__ == '__main__':
    main()
