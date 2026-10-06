"""Render the actual new focus coordinates for source layout review."""
from pathlib import Path
import json,re
from PIL import Image,ImageDraw,ImageFont
from hoi4_script import parse,entries,scalar

ROOT=Path(__file__).resolve().parents[1];MOD=ROOT/'mod'
def font(n):return ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',n)

def main():
    nodes=json.loads((ROOT/'design/marseille-red-route.json').read_text(encoding='utf-8'))['nodes']
    gfx={}
    for p in (MOD/'interface').glob('*.gfx'):
        for group in entries(parse(p.read_text(encoding='utf-8-sig')),'spriteTypes'):
            for r in group.value:
                if isinstance(r.value,list) and scalar(r.value,'name'):gfx[scalar(r.value,'name').strip('"')]=r.value
    focuses={scalar(n.value,'id'):n.value for t in entries(parse((MOD/'common/national_focus/sof_mrs_red.txt').read_text()),'focus_tree') for n in entries(t.value,'focus')}
    positions={r['code']:(125+r['x']*54,240+r['y']*122) for r in nodes}
    height=470+max(r['y'] for r in nodes)*122
    im=Image.new('RGB',(3270,height),'#172128');draw=ImageDraw.Draw(im)
    draw.text((46,28),'红色马赛 · 共产主义专属线路',font=font(42),fill='#f1d6a0')
    draw.text((46,94),'52项新国策｜中央与工会组织 · 五年计划 · 红军改革 · 地中海协约 · 法国统一',font=font(24),fill='#d0dde0')
    draw.text((46,137),'按实际脚本坐标与独立DDS绘制；全树205项图像无重复。通用153项国策位于右侧。非游戏截图。',font=font(20),fill='#98abb2')
    for r in nodes:
        x,y=positions[r['code']]
        for group in r['prerequisites']:
            for source in group:
                px,py=positions[source]
                draw.line([(px,py+52),(px,py+64),(x,y-64),(x,y-52)],fill='#6c818e',width=3)
        other=r.get('exclusive')
        if other and r['code']<other:
            ox,oy=positions[other]
            draw.line((x+74,y,ox-74,oy),fill='#d86d6d',width=4)
    for r in nodes:
        x,y=positions[r['code']];box=(x-75,y-52,x+75,y+52)
        draw.rounded_rectangle(box,radius=12,fill='#29363f',outline='#96724f' if r['code'][0] in 'AP' else '#667d83',width=2)
        sprite=gfx[scalar(focuses[r['id']],'icon')]
        texture=MOD/scalar(sprite,'texturefile').strip('"')
        icon=Image.open(texture).convert('RGBA')
        frames=int(scalar(sprite,'noOfFrames','1'));icon=icon.crop((0,0,icon.width//frames,icon.height)).resize((42,42),Image.Resampling.LANCZOS)
        im.paste(icon,(x-64,y-43),icon)
        draw.text((x-12,y-39),r['code']+' · '+str(r['days'])+'日',font=font(14),fill='#e1bd7f')
        chunks=[r['name'][i:i+8] for i in range(0,len(r['name']),8)]
        for i,title in enumerate(chunks[:3]):draw.text((x-67,y+2+i*19),title,font=font(16),fill='#e5eaec')
    draw.text((45,height-95),'关键门槛：政权交接50%支持｜整编140日｜计划验收365日｜危机警告90日｜联邦谈判180日',font=font(24),fill='#dec296')
    draw.text((45,height-50),'统一沿用339州条件与占领整合制度；同类精神替换升级，国策奖励使用独立领取记录。',font=font(20),fill='#a8bcc4')
    path=ROOT/'docs/MARSEILLE-RED-PREVIEW.png';im.save(path);print(str(path))

if __name__=='__main__':main()
