"""Review every exclusive focus illustration and flag near-duplicate silhouettes."""
import html,json,hashlib,collections
from pathlib import Path
from PIL import Image
from unique_focus_art import ROOT,ART,PLAN,read,save

def dhash(im):
    small=im.convert('L').resize((9,8),Image.Resampling.LANCZOS);p=list(small.getdata())
    return sum((p[y*9+x]>p[y*9+x+1])<<(y*8+x) for y in range(8) for x in range(8))

def main():
    data=json.loads(read(PLAN));assets=data['assets'];version=(ROOT/'VERSION').read_text(encoding='utf-8').strip();out=ROOT/'docs/previews'/version;out.mkdir(parents=True,exist_ok=True)
    hashes={a['id']:dhash(Image.open(ART/'exports'/(a['key']+'.png'))) for a in assets}
    near=[]
    for i,a in enumerate(assets):
        for b in assets[i+1:]:
            distance=(hashes[a['id']]^hashes[b['id']]).bit_count()
            if distance<=4:near.append(dict(a=a['id'],b=b['id'],distance=distance))
    pixel_hashes={a['id']:hashlib.sha256(Image.open(ART/'exports'/(a['key']+'.png')).tobytes()).hexdigest() for a in assets}
    review_path=ROOT/'design/unique-focus-art-review.json'
    review=json.loads(read(review_path)) if review_path.exists() else {}
    reviewed=review.get('native_pixel_sha256')==pixel_hashes and review.get('source_sha256')=={a['id']:a['source_sha256'] for a in assets} and review.get('visual_review_complete') is True
    report=dict(version=version,focuses=len(assets),distinct_sources=len({a['source_sha256'] for a in assets}),distinct_native_pixels=len(set(pixel_hashes.values())),near_silhouette_candidates=near,threshold=4,visual_review_required=not reviewed,game_engine_verified=False)
    save(ROOT/'docs/reports'/version/'unique-art-audit.json',report)
    css='body{background:#1c2328;color:#e8d8b7;font:16px Microsoft YaHei;max-width:1350px;margin:25px auto;padding:0 20px;line-height:1.7}a{color:#cfb47e}button,input{background:#27333a;color:#e8d8b7;border:1px solid #68777d;font:inherit;padding:6px 12px;margin-right:8px}button[aria-pressed=true]{border-color:#d5bd82}.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:9px}article{background:#253039;border:1px solid #49565e;text-align:center;padding:12px 7px}article img{display:block;width:96px;height:96px;margin:0 auto 10px}article a{color:#d8c6a0;text-decoration:none}small{color:#92a7b0;display:block;font-size:11px;overflow-wrap:anywhere}.hidden{display:none}section{margin:25px 0}h2{color:#dbc58f}'
    page=f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>一项国策一幅图 · {data["version"]}</title><style>{css}</style><h1>一项国策 · 一幅独立图标</h1><p>巴黎185项，科西嘉288项，共473幅独占图标。每项有不同原稿、不同游戏贴图及不同96像素图片内容；不会以更名后的同一张图充数。游戏脚本布局、奖励与内阁保持4.1.0。</p><p>图标按游戏原尺寸96×96显示，点击可查看原稿。这是源码美术预览，尚非游戏截图。</p><p><a href="INDEX.html">国策树布局</a> · <a href="TEXT.html">国策名称与描述</a> · <a href="../4.1.0/HISTORICAL.html">历史内阁</a></p><p><button data-filter="all" aria-pressed="true">全部473项</button><button data-filter="PRS" aria-pressed="false">巴黎185项</button><button data-filter="AJC" aria-pressed="false">科西嘉288项</button><input id="search" placeholder="查国策名称或ID" aria-label="查国策名称或ID"></p>'
    for tag,name in [('PRS','巴黎'),('AJC','科西嘉')]:
        page+=f'<section><h2>{name}</h2><div class="grid">'
        for a in assets:
            if a['tag']!=tag:continue
            page+=f'<article data-country="{tag}"><a href="../../../{a["source"]}"><img src="../../../art/focus/unique/exports/{a["key"]}.png" alt="{html.escape(a["title"])}">{html.escape(a["title"])}</a><small>{a["id"]}</small></article>'
        page+='</div></section>'
    page+='<script>let filter="all";const update=()=>{const q=document.querySelector("#search").value.trim().toLowerCase();document.querySelectorAll("article").forEach(a=>a.classList.toggle("hidden",(filter!=="all"&&a.dataset.country!==filter)||!a.textContent.toLowerCase().includes(q)));document.querySelectorAll("section").forEach(s=>s.classList.toggle("hidden",!s.querySelector("article:not(.hidden)")))};document.querySelectorAll("button").forEach(b=>b.onclick=()=>{filter=b.dataset.filter;document.querySelectorAll("button").forEach(x=>x.setAttribute("aria-pressed",String(x===b)));update()});document.querySelector("#search").oninput=update;</script></html>'
    if version=='4.3.0':
        page=page.replace(data['version'],version).replace('游戏脚本布局、奖励与内阁保持4.1.0。','美术沿用4.2.0；4.3.0调整明确的互斥与奖励，布局和历史内阁保留。')
    (out/'ICONS.html').write_text(page,encoding='utf-8',newline='\n')
    print(json.dumps(dict(focuses=len(assets),distinct_sources=report['distinct_sources'],distinct_native_pixels=report['distinct_native_pixels'],near_silhouettes=len(near))))

if __name__=='__main__':main()
