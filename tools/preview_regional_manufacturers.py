"""Player-readable company levels and actual gameplay changes, from source data."""
import html
import json
from pathlib import Path
from PIL import Image
from build_regional_manufacturers import stats_text

ROOT = Path(__file__).resolve().parents[1]


def main():
    version = (ROOT / 'VERSION').read_text().strip()
    out = ROOT / 'docs/previews' / version; out.mkdir(parents=True, exist_ok=True)
    data = json.loads((ROOT / 'design/regional-manufacturers.json').read_text(encoding='utf-8'))
    css = 'body{background:#1b2328;color:#e2dacb;font:16px Microsoft YaHei;margin:24px auto;max-width:1300px;padding:0 24px;line-height:1.65}h1,h2{color:#d6bd88}a{color:#d9bf85}input,select{background:#29333a;color:#e5ddd0;border:1px solid #777;padding:8px;font:inherit;margin-right:12px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:18px}article{border:1px solid #656c69;background:#273138;padding:18px}img{width:64px;height:64px;float:right}small{color:#adb6b7}.level{margin:9px 0;border-left:3px solid #a78a54;padding:8px 12px;background:#202a31}.initial{border-color:#d9bb7c}.stats{color:#d8c9a6}.hidden{display:none}strong{color:#e1c993}'
    page = f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>地区制造商 · {version}</title><style>{css}</style><h1>地区制造商 · {version}</h1><p>20个大区代表国家，各有一家主打企业。原生军工组织提供起始工艺和4级成长；缺少AAT时使用传统设计商同栏位，不能同时叠加两种版本。</p><p>需要完成真实工业国策、拥有并完全控制厂址。科研+10%，初始强项通常4–6%，并有性能或造价代价。数值只作用于对应装备及承接生产线。此页为源码名录和成长预览，非游戏截图。</p><p><a href="INDEX.html">国策布局</a> · <a href="../../../docs/BALANCE-4.3-ZH.md">平衡数值说明</a></p><input id="q" placeholder="查国家、企业或装备"><select id="mode"><option value="mio">军工组织完整成长</option><option value="legacy">传统设计商起始工艺</option></select><div class="grid">'
    for row in data['manufacturers']:
        source = next(a for a in data['native_art_assets'] if a['sprite'] == 'GFX_idea_' + row['picture'])
        im = Image.open(ROOT / source['destination']).convert('RGBA')
        im.save(out / (row['tag'] + '-COMPANY.png'))
        e = html.escape
        initial = stats_text(row['initial_equipment'])
        if row['initial_production']: initial += '；' + stats_text(row['initial_production'])
        page += f'<article><img src="{row["tag"]}-COMPANY.png" alt="{e(row["name"])}"><h2>{e(row["tag"])} · {e(row["region_name"])}</h2><strong>{e(row["name"])}</strong><p>{e(row["description"])}</p><p>主打：{e(row["equipment_name"])}<br>厂址：{e(row["factory_name"])}（州{row["factory_state"]}）<br>解锁：{e(" / ".join(row["unlock_names"]))}</p><div class="level initial">起始工艺 · {e(row["initial_name"])}<div class="stats">{e(initial)}</div></div>'
        for i, trait in enumerate(row['traits']):
            values = stats_text(trait.get('equipment', {}))
            if trait.get('production'): values += ('；' if values else '') + stats_text(trait['production'])
            requirement = '通过组织经验解锁'
            if i >= 2: requirement += '，并完成' + ' / '.join(row[('specialize' if i == 2 else 'capstone') + '_names'])
            page += f'<div class="level growth">第{i+1}级 · {e(trait["name"])}<div class="stats">{e(values)}</div><small>{e(requirement)}</small></div>'
        page += '<small>传统设计商：125政治点聘用，装备工艺取起始值，专项科研+10%；失去厂址后撤销。已有装备设计的属性仍属于原装备。</small></article>'
    page += '</div><script>const q=document.querySelector("#q"),m=document.querySelector("#mode");q.oninput=()=>document.querySelectorAll("article").forEach(a=>a.classList.toggle("hidden",!a.textContent.toLowerCase().includes(q.value.toLowerCase())));m.onchange=()=>document.querySelectorAll(".growth").forEach(x=>x.classList.toggle("hidden",m.value==="legacy"));</script></html>'
    (out / 'MANUFACTURERS.html').write_text(page, encoding='utf-8', newline='\n')
    print(json.dumps(dict(companies=len(data['manufacturers']), preview=str(out / 'MANUFACTURERS.html'))))


if __name__ == '__main__':
    main()
