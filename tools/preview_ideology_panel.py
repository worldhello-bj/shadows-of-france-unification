"""Source-derived layout preview, using the game's actual bitmap glyphs/DDS.

This is not a game screenshot or evidence of engine execution.
"""
from pathlib import Path
import argparse,json,math,re
from PIL import Image,ImageDraw,ImageFont,ImageChops
from hoi4_script import parse,one,scalar,walk
from build_ideology_panel import ROOT,MOD,PROFILES
from validate_ideology_panel import Fixture


class BitmapFont:
    def __init__(self,game,name):
        self.glyphs={};self.atlases=[]
        prefix='hoi_16mbs' if name=='hoi_16mbs' else 'garamond_14'
        for i in range(1,5):
            stem=f'{prefix}_{i}of4'+('EX' if prefix=='hoi_16mbs' else '')
            path=game/'gfx/fonts/chinese'/stem
            texture=Image.open(path.with_suffix('.dds')).convert('RGBA')
            self.atlases.append(texture)
            for line in path.with_suffix('.fnt').read_text(encoding='utf-8').splitlines():
                if line.startswith('char id='):
                    d={k:int(v) for k,v in re.findall(r'(\w+)=(-?\d+)',line)}
                    self.glyphs[chr(d['id'])]=(texture,d)

    def text(self,text,color='#E3E0D4'):
        x=0; glyphs=[]
        for char in text:
            if char not in self.glyphs:continue
            atlas,d=self.glyphs[char]
            glyph=atlas.crop((d['x'],d['y'],d['x']+d['width'],d['y']+d['height']))
            # HOI4's font shader uses the glyph alpha; preserve the supplied mask.
            tinted=Image.new('RGBA',glyph.size,color);tinted.putalpha(ImageChops.multiply(glyph.getchannel('R'),glyph.getchannel('A')))
            glyphs.append((tinted,x+d['xoffset'],d['yoffset']))
            x+=d['xadvance']
        im=Image.new('RGBA',(max(x+2,1),24))
        for glyph,gx,gy in glyphs:im.alpha_composite(glyph,(gx,gy))
        return im


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--game',type=Path,default=Path(r'D:\steam\steamapps\common\Hearts of Iron IV'));args=parser.parse_args()
    fonts={name:BitmapFont(args.game,name) for name in ('hoi_16mbs','Main_14')}
    rows=one(one(parse((MOD/'interface/sofzh_ideology_panel.gui').read_text()),'guiTypes').value,'containerWindowType').value
    nodes={scalar(n.value,'name').strip('"'):n.value for n in walk(rows) if isinstance(n.value,list) and scalar(n.value,'name')}
    legends=nodes['sofzh_chart_legend'];lp=one(legends,'position').value
    scale=float(scalar(legends,'scale'));lx=float(scalar(lp,'x'));ly=float(scalar(lp,'y'))
    swatches=Image.open(MOD/'gfx/interface/sofzh_ideology_panel/swatches.dds').convert('RGBA')
    refresh=Image.open(MOD/'gfx/interface/sofzh_ideology_panel/refresh.dds').convert('RGBA').crop((0,0,18,18))
    facefont=ImageFont.truetype(r'C:\Windows\Fonts\msyh.ttc',20)
    smallfont=ImageFont.truetype(r'C:\Windows\Fonts\msyh.ttc',13)
    canvas=Image.new('RGBA',(1128,416),'#20262B');draw=ImageDraw.Draw(canvas)
    draw.text((20,10),'意识形态面板 · 源码布局预览（非游戏截图）',font=facefont,fill='#E9DFBC')
    draw.text((20,39),'使用实际 GUI 坐标、DDS 和游戏中文字体；原生饼图为示意绘制，需进游戏确认。',font=smallfont,fill='#A5B1B5')
    fixtures=[('马赛 · 1936年开局',Fixture((30,35,15,20),'democratic','socialism',[
        dict(ideologies=['marxism'],active=True),dict(ideologies=['despotism'],active=True)]).run()),
        ('马赛 · 先锋社会主义示例',Fixture((30,35,15,20),'communism','leninism',[
        dict(ideologies=['socialism'],active=True),dict(ideologies=['despotism'],active=True)]).run())]
    rects=[]
    for side,(label,fixture) in enumerate(fixtures):
        ox=12+side*558;oy=74
        panel=Image.new('RGBA',(550,322),'#333A3D');d=ImageDraw.Draw(panel)
        d.rectangle((5,5,544,35),fill='#464C4D',outline='#787B70')
        d.text((15,8),label,font=smallfont,fill='#EEE5CC')
        d.rectangle((175,54,535,214),fill='#2A3135',outline='#555D5C')
        # Crop coordinates correspond to the native politics window y=86..408.
        root_x=175;root_y=54
        d.text((181,root_y+114),'社会共和主义' if side==0 else '先锋社会主义',font=smallfont,fill='#DED6B7')
        d.text((186,root_y+130),'下次选举：\n1940年',font=smallfont,fill='#C8CAC6',spacing=0)
        d.text((18,222),'民族精神',font=facefont,fill='#D9D4C7')
        d.rectangle((18,252,530,302),fill='#2E3539',outline='#69716F')
        d.text((28,266),'既有民族精神栏（位置与功能保留）',font=smallfont,fill='#9FAAA9')
        title=fonts['hoi_16mbs'].text('政治光谱','#E7DFC5')
        panel.alpha_composite(title,(root_x+5,root_y))
        panel.alpha_composite(refresh,(root_x+342,root_y))
        # The game owns the native pie. This preview only illustrates its position.
        groups=['democratic','communism','fascism','neutrality']
        colors=['#0000FF','#FF0000','#964B00','#7C7C7C']
        pie=Image.new('RGBA',(64,64));pd=ImageDraw.Draw(pie);angle=-90
        for group,color in zip(groups,colors):
            weight=sum(fixture.variables['sofzh_chart_'+p[0]] for p in PROFILES if p[1]==group)
            if weight>0:pd.pieslice((3,3,60,60),angle,angle+weight*3.6,fill=color)
            angle+=weight*3.6
        pd.ellipse((2,2,61,61),outline='#CCC9B9',width=2)
        panel.alpha_composite(pie,(185,81))
        for i,p in enumerate(PROFILES):
            group_index=groups.index(p[1])
            if fixture.variables['sofzh_chart_'+p[1]+'_frame']!=i+1:continue
            ident=p[0];name=nodes['sofzh_chart_name_'+ident];np=one(name,'position').value
            x=root_x+lx+float(scalar(np,'x'))*scale
            y=root_y+ly+float(scalar(np,'y'))*scale
            text=fonts['hoi_16mbs'].text(p[2])
            text=text.resize((round(text.width*scale),round(text.height*scale)),Image.Resampling.LANCZOS)
            panel.alpha_composite(text,(round(x),round(y)))
            percentage=fonts['hoi_16mbs'].text(f"{fixture.variables['sofzh_chart_'+ident]:.1f}%")
            percentage=percentage.resize((round(percentage.width*scale),round(percentage.height*scale)),Image.Resampling.LANCZOS)
            vp=one(nodes['sofzh_chart_value_'+ident],'position').value
            right=root_x+lx+(float(scalar(vp,'x'))+48)*scale
            panel.alpha_composite(percentage,(round(right-percentage.width),round(y)))
            sp=one(nodes['sofzh_chart_swatch_'+ident],'position').value
            sx=root_x+lx+float(scalar(sp,'x'))*scale;sy=root_y+ly+float(scalar(sp,'y'))*scale
            swatch=swatches.crop((group_index*12,0,(group_index+1)*12,12))
            panel.alpha_composite(swatch,(round(sx),round(sy)))
            if fixture.variables['sofzh_chart_ruling']==i+1:
                marker=fonts['hoi_16mbs'].text('◆','#EEC923')
                marker=marker.resize((round(marker.width*scale),round(marker.height*scale)),Image.Resampling.LANCZOS)
                panel.alpha_composite(marker,(round(root_x+lx+229*scale),round(y)))
            rects.append(dict(case=label,profile=ident,label_x=x,label_y=y,label_width=text.width))
        canvas.alpha_composite(panel,(ox,oy))
    out=ROOT/'docs/previews/4.6.0/POLITICS.png';out.parent.mkdir(parents=True,exist_ok=True);canvas.convert('RGB').save(out)
    report=dict(preview=str(out),game_screenshot=False,render_basis='Actual GUI coordinates, DDS and HOI4 Chinese bitmap fonts; source-script fixture values',labels=rects)
    report_path=ROOT/'docs/reports/4.6.0/politics-preview.json';report_path.parent.mkdir(parents=True,exist_ok=True)
    report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(ok=True,path=str(out),game_screenshot=False),ensure_ascii=False))


if __name__=='__main__':main()
