"""Inspectable source preview with real focus icons and council rules."""
from pathlib import Path
import base64
import io
import json
import html
from PIL import Image, ImageDraw, ImageFont
from hoi4_script import parse, entries, scalar
from build_brittany_focus import ROOT, MOD, REPORT


def main():
    spec=json.loads((ROOT/'design/brittany-focus.json').read_text(encoding='utf-8'))
    gfx={scalar(n.value,'name').strip('"'):n.value for g in entries(parse((MOD/'interface/sof_brittany.gfx').read_text()),'spriteTypes') for n in g.value}
    icons={}
    for name,rows in gfx.items():
        im=Image.open(MOD/scalar(rows,'texturefile').strip('"')).convert('RGBA')
        frames=int(scalar(rows,'noOfFrames','1'));im=im.crop((0,0,im.width//frames,im.height));im.thumbnail((70,70))
        b=io.BytesIO();im.save(b,format='PNG');icons[name]='data:image/png;base64,'+base64.b64encode(b.getvalue()).decode()
    nodes=spec['nodes'];pos={n['code']:(90+(n['x']-2)*74,105+n['y']*124) for n in nodes}
    width=max(p[0] for p in pos.values())+100;height=max(p[1] for p in pos.values())+85
    pieces=[f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" xmlns="http://www.w3.org/2000/svg">']
    for n in nodes:
        x,y=pos[n['code']]
        for group in n['prerequisites']:
            for pre in group:
                a,b=pos[pre];color='#506777' if len(group)==1 else '#bea161'
                pieces.append(f'<path d="M {a} {b+43} C {a} {b+80},{x} {y-80},{x} {y-43}" fill="none" stroke="{color}" stroke-width="2"/>')
    for n in nodes:
        x,y=pos[n['code']];color='#b59757' if n['code'][0]=='P' else '#657d8e'
        title=html.escape(n['name']);code=n['code']
        pieces.append(f'<g class="node" data-code="{code}" tabindex="0"><title>{title} · {n["days"]}日 · 参考{n["donor"]}</title><rect x="{x-70}" y="{y-44}" width="140" height="88" rx="10" fill="#25343e" stroke="{color}"/><image href="{icons[n["icon"]]}" x="{x-25}" y="{y-43}" width="50" height="50"/><text x="{x}" y="{y+21}" text-anchor="middle" fill="#ecede8" font-size="12">{title}</text><text x="{x}" y="{y+37}" text-anchor="middle" fill="#aab9c3" font-size="10">{code} · {n["days"]}日</text></g>')
    pieces.append('</svg>')
    table=''.join(f'<tr><td>{d["name"]}</td><td>{d["seats"]}</td><td>{d["demand"]}</td></tr>' for d in spec['delegates'])
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>布列塔尼议会国策预览</title>
<style>*{box-sizing:border-box}body{margin:0;background:#15212a;color:#e9e7da;font:16px/1.6 "Microsoft YaHei",sans-serif}header{padding:22px 30px;background:#21313d;border-bottom:1px solid #526675}h1{margin:0;color:#e0c88d;font-size:26px}p{margin:8px 0}nav{display:flex;gap:10px;flex-wrap:wrap}button{background:#3b5263;color:white;border:1px solid #6c8291;border-radius:6px;padding:8px 14px;cursor:pointer}.scroll{overflow:auto;max-height:72vh;padding:10px;scroll-behavior:smooth}.node{cursor:pointer}aside{display:flex;gap:35px;padding:20px 30px;align-items:flex-start}table{border-collapse:collapse}td,th{padding:5px 18px;border-bottom:1px solid #415462}#detail{max-width:550px;color:#becdd5}</style>
<header><h1>布列塔尼地方议会 · 174项专属国策</h1><p>六位1930年代地方政治人物及六位历史候补 · 116项军事内容 · 孤立防御 / 积极进攻互斥</p><nav>NAV</nav><p style="color:#a9bcc8;font-size:13px">按实际源码与专属图标绘制。此预览不代表游戏实测。八类成熟机构对应数值为通用成熟机构的130%；六领域委员会专项拨款另行强化。原生议会面板布局见下方。</p></header><div class="scroll" id="tree">TREE</div><aside><table><tr><th>地方代表</th><th>席位</th><th>协商诉求</th></tr>TABLE</table><div id="detail">点击国策查看前置与互斥。<p>普通法案51席 / 动员与远征预算66席 / 战争75席。法案审议45日、议员支持180日。七个家乡地区各有沦陷、攻下与收复事件，支持不会免费续期。</p></div></aside><div style="display:flex;gap:16px;flex-wrap:wrap;padding:24px"><img src="COUNCIL-1.png" width="400"><img src="COUNCIL-2.png" width="400"><img src="COUNCIL-3.png" width="400"><img src="COUNCIL-4.png" width="400"></div>
<script>const nodes=NODES;const positions=POSITIONS;const labels=Object.fromEntries(nodes.map(n=>[n.code,n.name]));document.querySelectorAll('.node').forEach(el=>el.onclick=()=>{const n=nodes.find(n=>n.code===el.dataset.code);document.getElementById('detail').innerText=n.code+' · '+n.name+'\\n耗时：'+n.days+'日\\n前置：'+(n.prerequisites.map(g=>g.map(c=>labels[c]).join(' 或 ')).join('，且 ')||'起点')+'\\n互斥：'+(n.exclusive.map(c=>labels[c]).join('、')||'无')+'\\n美国参考节点：'+n.donor;});function jump(c){const p=positions[c];document.getElementById('tree').scrollTo({left:Math.max(0,p[0]-80),top:Math.max(0,p[1]-100),behavior:'smooth'});}</script></html>'''
    nav=''.join(f'<button onclick="jump(\'{c}\')">{s}</button>' for c,s in [('P0','地方议会'),('E0','公共建设'),('I0','中立与动员'),('D0','西部协商'),('M0','陆军基础'),('A0','航空基础'),('N0','海防基础'),('B0','共同军备'),('F0','孤立防御'),('O0','积极进攻')])
    page=page.replace('NAV',nav).replace('TREE',''.join(pieces)).replace('TABLE',table).replace('NODES',json.dumps(nodes,ensure_ascii=False)).replace('POSITIONS',json.dumps(pos))
    out=ROOT/'docs/previews/brittany';out.mkdir(parents=True,exist_ok=True);(out/'INDEX.html').write_text(page,encoding='utf-8')
    # The political subtree is also readable as a static standalone preview.
    font=lambda size:ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',size)
    politics=[n for n in nodes if n['code'][0]=='P'];coordinates={n['code']:(100+(n['x']-2)*70,220+n['y']*125) for n in politics}
    im=Image.new('RGB',(2220,1640),'#15212a');draw=ImageDraw.Draw(im)
    draw.text((45,25),'布列塔尼 · 地方议会与政治互动',font=font(36),fill='#e0c88d')
    draw.text((45,85),'六位历史人物 · 有期限的联盟承诺 · 逐案审议 · 三条责任内阁路线',font=font(24),fill='#dae5e6')
    draw.text((45,133),'普通法案51席 | 修订中立与动员66席 | 战争授权75席 | 审议45日 | 承诺180日',font=font(20),fill='#aebfc9')
    for n in politics:
        x,y=coordinates[n['code']]
        for group in n['prerequisites']:
            for p in group:
                if p not in coordinates:continue
                a,b=coordinates[p];draw.line([(a,b+43),(a,b+65),(x,y-65),(x,y-43)],fill='#667f8b',width=2)
    for n in politics:
        x,y=coordinates[n['code']];draw.rounded_rectangle((x-69,y-45,x+69,y+45),radius=9,fill='#293943',outline='#a58a52',width=2)
        text=n['name'];draw.text((x-61,y-36),n['code']+' · '+str(n['days'])+'日',font=font(13),fill='#e0c88d')
        for i,chunk in enumerate([text[z:z+8] for z in range(0,len(text),8)]):draw.text((x-61,y-5+i*21),chunk,font=font(16),fill='#e9e9df')
    draw.text((45,1550),'人物身份来自地方档案、法国国民议会与参议院资料；席位与政策互动为游戏设定。',font=font(20),fill='#aebfc9')
    draw.text((45,1590),'根据实际脚本生成的布局预览。游戏内显示、真实存档迁移与长期平衡尚待实测。',font=font(19),fill='#aebfc9')
    im.save(out/'POLITICS.png');print(str(out/'INDEX.html'))


if __name__=='__main__':main()
