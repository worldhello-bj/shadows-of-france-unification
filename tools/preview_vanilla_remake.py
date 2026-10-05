"""Render actual native-coordinate graphs with registered native DDS assets.

No browser or engine screenshots are fabricated; conditional branches are marked.
"""
import html,json,re
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from hoi4_script import parse,one,scalar,entries
ROOT=Path(__file__).resolve().parent.parent;MOD=ROOT/'mod';OUT=ROOT/'docs/previews'/(ROOT/'VERSION').read_text(encoding='utf-8').strip()
FONT='C:/Windows/Fonts/msyh.ttc'
def font(n):return ImageFont.truetype(FONT,n)
def read(p):return p.read_text(encoding='utf-8-sig')

def main():
    OUT.mkdir(parents=True,exist_ok=True);loc={};gfx={};report=[]
    for p in (MOD/'localisation/simp_chinese').rglob('*.yml'):loc.update(re.findall(r'(?m)^\s+([^\s:]+):\d*\s+"((?:[^"\\]|\\.)*)"',read(p)))
    for p in (MOD/'interface').glob('*.gfx'):
        for g in entries(parse(read(p)),'spriteTypes'):
            for r in g.value:
                if isinstance(r.value,list) and scalar(r.value,'name'):gfx[scalar(r.value,'name').strip('"')]=r.value
    def condition(rows):
        values=[]
        for r in rows:
            if r.key=='NOT':v=not condition(r.value)
            elif r.key=='OR':v=any(condition([x]) for x in r.value)
            elif r.key=='AND':v=condition(r.value)
            elif r.key=='if':v=condition([x for x in r.value if x.key!='limit']) if condition(scalar(r.value,'limit',[])) else True
            elif r.key=='always':v=r.value=='yes'
            elif r.key=='has_dlc':v=True
            elif r.key=='has_game_rule':v=scalar(r.value,'option')=='SHOW'
            elif r.key in ['has_completed_focus','has_country_flag','has_global_flag','has_war','is_subject']:v=False
            elif r.key=='original_tag':v=r.value==tag
            else:v=False
            values.append(v)
        return all(values)
    for tag,name,donor in [('PRS','巴黎','法国'),('AJC','科西嘉','意大利')]:
        tree=one(parse(read(MOD/'common/national_focus'/('sofzh_paris.txt' if tag=='PRS' else 'sofzh_corsica.txt'))),'focus_tree').value
        nodes={scalar(n.value,'id'):n.value for n in entries(tree,'focus')};xy={}
        def coord(fid):
            if fid not in xy:
                b=nodes[fid];x,y=float(scalar(b,'x','0')),float(scalar(b,'y','0'));parent=scalar(b,'relative_position_id')
                if parent:px,py=coord(parent);x+=px;y+=py
                for o in entries(b,'offset'):
                    if condition(scalar(o.value,'trigger',[])):x+=float(scalar(o.value,'x','0'));y+=float(scalar(o.value,'y','0'))
                xy[fid]=(x,y)
            return xy[fid]
        for fid in nodes:coord(fid)
        shown={};visiting=set()
        def visible(fid):
            if fid in shown:return shown[fid]
            assert fid not in visiting,'Dependency cycle';visiting.add(fid)
            b=nodes[fid];allowed=all(condition(a.value) for a in entries(b,'allow_branch'))
            for g in entries(b,'prerequisite'):
                parents=[v.value for v in entries(g.value,'focus')]
                if parents:allowed=allowed and any(visible(p) for p in parents)
            visiting.remove(fid);shown[fid]=allowed;return allowed
        for fid in nodes:visible(fid)
        render_ids=[fid for fid in nodes if shown[fid]]
        minx,maxx=min(xy[k][0] for k in render_ids),max(xy[k][0] for k in render_ids);miny,maxy=min(xy[k][1] for k in render_ids),max(xy[k][1] for k in render_ids)
        pos={fid:(round(120+(xy[fid][0]-minx)*96),round(210+(xy[fid][1]-miny)*130)) for fid in render_ids}
        w=round((maxx-minx)*96+240);h=round((maxy-miny)*130+380)
        im=Image.new('RGB',(w,h),'#1c2328');d=ImageDraw.Draw(im)
        d.text((35,24),name+' · 原版'+donor+'国策树重制',font=font(30),fill='#efdbad')
        d.text((35,72),f'保留 {len(nodes)} 项 / 开局可见分支 {len(render_ids)} 项 / 原版结构与间距 · 本地重绘图标',font=font(18),fill='#b1c3c8')
        d.text((35,106),'源码布局审阅图；条件偏移按开局状态计算。后续分支随政治路线展开。不是游戏截图。',font=font(16),fill='#95a9b2')
        for fid in render_ids:
            x,y=pos[fid];b=nodes[fid]
            for g in entries(b,'prerequisite'):
                for v in entries(g.value,'focus'):
                    if v.value not in pos:continue
                    px,py=pos[v.value];mid=y-68
                    d.line([(px,py+52),(px,mid),(x,mid),(x,y-45)],fill='#8d967d' if len(entries(g.value,'focus'))>1 else '#596f79',width=2)
            for g in entries(b,'mutually_exclusive'):
                for v in entries(g.value,'focus'):
                    if v.value not in pos or fid>=v.value:continue
                    ex,ey=pos[v.value]
                    if ey==y:
                        for a in range(min(x,ex)+48,max(x,ex)-48,14):d.line((a,y,a+6,y),fill='#d2a251',width=2)
        for fid in render_ids:
            x,y=pos[fid];b=nodes[fid];sprite=gfx[scalar(b,'icon')];icon=Image.open(MOD/scalar(sprite,'texturefile').strip('"')).convert('RGBA');frames=int(scalar(sprite,'noOfFrames','1'))
            if frames>1:icon=icon.crop((0,0,icon.width//frames,icon.height))
            icon.thumbnail((85,80));im.paste(icon,(x-icon.width//2,y-icon.height//2),icon)
            title=loc[fid];lines=[title[i:i+7] for i in range(0,len(title),7)]
            for i,line in enumerate(lines):d.text((x,y+39+i*17),line,font=font(15),anchor='mt',fill='#e8d8b7')
        d.text((35,h-75),'未拥有地区不凭空赠送海外建筑；外交合作可拒绝；经验与工厂奖励按城市势力规模调整。',font=font(17),fill='#b1c3c8')
        im.save(OUT/(tag+'-TREE.png'),optimize=True)
        thumb=im.copy();thumb.thumbnail((1800,1400));thumb.save(OUT/(tag+'-OVERVIEW.png'),optimize=True)
        # Show the actual opening/political columns at readable native spacing.
        cropx=pos[next(k for k in render_ids if k==('SFP_devalue_the_franc' if tag=='PRS' else 'SFC_ethiopian_war_logistics_bba'))][0]
        left=max(0,cropx-600);im.crop((left,0,min(w,left+1800),min(h,1500))).save(OUT/(tag+'-OPENING.png'),optimize=True)
        collisions={}
        for k,p in pos.items():collisions.setdefault(str(p),[]).append(k)
        overlaps=[v for v in collisions.values() if len(v)>1]
        report.append(dict(tag=tag,nodes=len(nodes),opening_visible=len(render_ids),size=[w,h],exact_position_overlaps=overlaps,game_screenshot=False))
    metadata=json.loads(read(ROOT/'design/vanilla-major-remake.json'))
    style='body{background:#1c2328;color:#efdbad;font:17px Microsoft YaHei;margin:28px}p{color:#a9bec6;line-height:1.75}a{color:#c8bd91}img{max-width:100%;height:auto}article{margin:30px 0}details{border-top:1px solid #3d4b50;padding:12px 0;max-width:900px}summary{cursor:pointer}small{color:#95a9b2}'
    page=f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>巴黎与科西嘉国策重制</title><style>{style}</style><h1>巴黎与科西嘉 · 原版大国树重制</h1><p>版本 {metadata["version"]}。巴黎185项；科西嘉288项，删除26项无法迁移的教皇与内战分支。其他国家继续使用153项通用国策。以下是实际源码坐标与注册DDS图标排版，尚非游戏截图。</p><p><a href="TEXT.html">逐项查看图标、名称与中文描述</a> · <a href="../../../art/focus/review/CONTACT-96.png">查看整套重绘图标</a></p>'
    for tag,name in [('PRS','巴黎：原版法国树'),('AJC','科西嘉：原版意大利树')]:page+=f'<article><h2>{name}</h2><p><a href="{tag}-TREE.png">打开完整分辨率</a></p><img src="{tag}-OVERVIEW.png"><h3>开局局部</h3><img src="{tag}-OPENING.png"></article>'
    textpage=f'<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>两国国策名称与描述</title><style>{style}</style><h1>国策名称与描述 · {metadata["version"]}</h1><p><a href="INDEX.html">返回布局预览</a>。点击标题展开当前游戏源码中的中文描述。数值效果由游戏悬停框显示。</p>'
    for tag,name in [('PRS','巴黎'),('AJC','科西嘉')]:
        textpage+=f'<h2>{name}</h2>'
        for node in metadata['nodes']:
            if node['tag']!=tag:continue
            fid=node['id'];title=html.escape(loc[fid]);desc=html.escape(loc[fid+'_desc']).replace('\\n','<br>')
            art=node.get('art');thumb=f'<img src="../../../art/focus/exports/{art}-96.png" width="48" height="48" style="vertical-align:middle;margin-right:12px" alt="">' if art else ''
            textpage+=f'<details id="{fid}"><summary>{thumb}{title}</summary><p>{desc}</p></details>'
    (OUT/'INDEX.html').write_text(page,encoding='utf-8');(OUT/'TEXT.html').write_text(textpage,encoding='utf-8')
    (OUT/'layout.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))
if __name__=='__main__':main()
