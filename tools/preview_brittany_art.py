"""Artwork gallery and native-size contact sheet; no original image retouch."""
import html
import json
from PIL import Image, ImageDraw, ImageFont
from brittany_art import ROOT, ROUTES, ROLES, load_art


def main():
    out=ROOT/'docs/previews/brittany';out.mkdir(parents=True,exist_ok=True)
    labels=dict(parliament='地方议会',defence='孤立防御',offence='积极进攻',home_loss='家乡沦陷',home_recovery='家乡恢复',seal='白鼬议会印记')
    role_labels=dict(command='指挥',land='陆军',air='航空',sea='海军',supply='后勤')
    route_labels=dict(service='共同整备',defence='孤立防御',offence='积极进攻')
    canvas=Image.new('RGB',(1500,1570),'#12272e');draw=ImageDraw.Draw(canvas)
    font=lambda size:ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',size)
    draw.text((45,22),'布列塔尼 · 议会与三军美术',font=font(34),fill='#e6ce97')
    draw.text((46,75),'黄铜 · 珐琅 · 黑白纹章 | 21张原画 · 原生DDS已接入',font=font(19),fill='#b8c9c5')
    canvas.paste(load_art('parliament',(1410,470)).convert('RGB'),(45,115))
    for row,route in enumerate(ROUTES):
        y=610+row*171
        draw.text((45,y+40),route_labels[route],font=font(24),fill='#d4c399')
        for col,role in enumerate(ROLES):
            x=250+col*235
            art=load_art(route+'_'+role,(112,112));canvas.paste(art,(x,y),art)
            draw.text((x+25,y+121),role_labels[role],font=font(18),fill='#d8e0d7')
    for i,key in enumerate(['home_loss','home_recovery']):
        x=45+i*725;y=1140
        canvas.paste(load_art(key,(685,230)).convert('RGB'),(x,y))
        draw.text((x,y+244),labels[key],font=font(22),fill='#d5c499')
    draw.text((45,1450),'插画与作者布局预览；不是游戏实测截图。PNG原图与提示词均已保留。',font=font(20),fill='#a4bdb8')
    canvas.save(out/'ART-BOARD.png')
    generated=json.loads((ROOT/'art/brittany/generation-prompts.json').read_text(encoding='utf-8'))['assets']
    cards=[]
    for r in generated:
        key=r['key'];label=labels.get(key)
        if not label:
            route,role=key.split('_');label=route_labels[route]+' · '+role_labels[role]
        wide=not r['transparent'];cards.append('<figure class="'+('wide' if wide else '')+'"><a href="../../../'+r['file']+'"><img src="../../../'+r['file']+'" loading="lazy"></a><figcaption>'+html.escape(label)+'</figcaption></figure>')
    page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>布列塔尼美术素材</title>
<style>*{box-sizing:border-box}body{margin:0;background:#10262e;color:#e1e6d9;font:16px/1.7 "Microsoft YaHei",sans-serif}header{padding:28px 5vw;border-bottom:1px solid #947e51;background:#1e353d}h1{color:#e2c487;margin:0}a{color:#ddc58d}.gallery{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:18px;padding:26px 5vw}figure{margin:0;padding:15px;border:1px solid #68746a;background:linear-gradient(135deg,#263e46,#172b31)}figure.wide{grid-column:1/-1}figure img{width:100%;height:205px;object-fit:contain}.wide img{height:auto;max-height:450px;object-fit:contain}figcaption{text-align:center;color:#d6c69f}.previews{display:flex;gap:20px;flex-wrap:wrap;padding:30px 5vw}.previews img{width:min(100%,510px);height:auto;align-self:flex-start}</style>
<header><h1>布列塔尼 · 议会与三军美术</h1><p>21张原画：五幅场景、十五枚军种与路线徽章、一枚议会印记。黄铜、墨绿与铜红珐琅统一风格。</p><p><a href="INDEX.html">完整国策树</a> · <a href="../../../art/brittany/generation-prompts.json">原图清单与全部生成提示词</a> · <a href="../../../design/brittany-art.json">游戏导出清单</a></p><p>内置 image_gen 生成，原图完整保存；下方界面为实际素材与作者布局的示例预览，尚未验证游戏引擎显示。</p></header><section class="gallery">CARDS</section><section class="previews"><img src="COUNCIL-1.png"><img src="COUNCIL-3.png"><img src="COUNCIL-4.png"></section></html>'''
    (out/'ART.html').write_text(page.replace('CARDS',''.join(cards)),encoding='utf-8')
    print(out/'ART.html')


if __name__=='__main__':main()
