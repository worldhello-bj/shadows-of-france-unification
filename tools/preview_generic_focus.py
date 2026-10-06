"""Render the actual 153-node grid, existing artwork, prerequisites and buff table."""
from pathlib import Path
from io import BytesIO
import json,re,base64,html
from PIL import Image,ImageDraw,ImageFont
from hoi4_script import parse,entries,one,scalar
ROOT=Path(__file__).resolve().parents[1];MOD=ROOT/'mod'
def font(n):return ImageFont.truetype('C:/Windows/Fonts/msyh.ttc',n)
def main():
 d=json.loads((ROOT/'design/generic-focus-4.4.json').read_text(encoding='utf-8'));nodes={scalar(n.value,'id'):n.value for n in entries(parse((MOD/'common/national_focus/sof_mrs_shared_generic.txt').read_text(encoding='utf-8-sig')),'shared_focus')}
 names={};descs={}
 for p in (MOD/'localisation/simp_chinese/replace').glob('*.yml'):
  for k,v in re.findall(r'(?m)^\s+([^\s:]+):\d*\s+"((?:[^"\\]|\\.)*)"',p.read_text(encoding='utf-8-sig')):
   if k.endswith('_desc'):descs[k[:-5]]=v
   else:names[k]=v
 sprites={}
 for p in (MOD/'interface').glob('*.gfx'):
  for group in entries(parse(p.read_text(encoding='utf-8-sig')),'spriteTypes'):
   for n in group.value:
    if isinstance(n.value,list) and scalar(n.value,'name'):sprites[scalar(n.value,'name').strip('"')]=n.value
 scale=60;row=108;left=120;top=270;w=left+max(n['x'] for n in d['focuses'].values())*scale+140;h=top+max(n['y'] for n in d['focuses'].values())*row+190
 canvas=Image.new('RGB',(w,h),'#151d25');draw=ImageDraw.Draw(canvas)
 draw.text((45,25),'通用国策 · 4.4.0',font=font(42),fill='#f1d1a1')
 draw.text((45,90),'153项国策 · 六阶行政 · 工业规模解锁 · 21 / 35 / 49 / 70日分阶段建设',font=font(24),fill='#c4d0d7')
 draw.text((45,132),'按实际脚本坐标、前置与图标绘制；非游戏截图。马赛的共享节点整体向右偏移80格。',font=font(21),fill='#91a5b3')
 coords={i:(left+p['x']*scale,top+p['y']*row) for i,p in d['focuses'].items()}
 for i,n in nodes.items():
  x,y=coords[i]
  for group in entries(n,'prerequisite'):
   for dep in entries(group.value,'focus'):
    px,py=coords[dep.value];draw.line([(px,py+44),(px,py+60),(x,y-60),(x,y-44)],fill='#5f7682',width=2)
 data=[]
 for i,n in nodes.items():
  p=d['focuses'][i];x,y=coords[i];name=re.sub('§.','',names.get(i,i));sprite=sprites[scalar(n,'icon')];texture=MOD/scalar(sprite,'texturefile').strip('"');icon=Image.open(texture).convert('RGBA');frames=int(scalar(sprite,'noOfFrames','1'));icon=icon.crop((0,0,icon.width//frames,icon.height));small=icon.resize((52,52),Image.Resampling.LANCZOS)
  draw.rounded_rectangle((x-56,y-44,x+56,y+46),radius=9,fill='#293842',outline='#8b785e' if p['section']=='行政与治理' else '#537480',width=2);canvas.paste(small,(x-26,y-40),small)
  for j,line in enumerate([name[k:k+7] for k in range(0,len(name),7)][:2]):draw.text((x-49,y+13+j*15),line,font=font(13),fill='#e1e7e9')
  draw.text((x-47,y-39),str(p['cost']*7)+'日',font=font(10),fill='#e3b773')
  buf=BytesIO();icon.save(buf,format='PNG');asset=base64.b64encode(buf.getvalue()).decode()
  data.append(dict(id=i,name=name,description=descs.get(i,''),x=p['x'],y=p['y'],section=p['section'],days=p['cost']*7,factories=p.get('factories',0),parents=[a.value for b in entries(n,'prerequisite') for a in entries(b.value,'focus')],icon='data:image/png;base64,'+asset))
 for section in d['sections']:
  if section['name']=='矿业开发':sx,sy=left+26*scale,top+15*row
  else:sx,sy=left+section['x']*scale-50,top-86
  draw.text((sx,sy),section['name'],font=font(21),fill='#e3bd83')
 output=ROOT/'docs/previews/4.4.0';output.mkdir(parents=True,exist_ok=True);canvas.save(output/'GENERIC-TREE.png')
 canvas.crop((0,0,left+20*scale+150,top+11*row+100)).save(output/'INDUSTRY.png')
 template='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>通用国策 4.4.0</title><style>
*{box-sizing:border-box}body{margin:0;background:#141c23;color:#e5eaed;font:15px 'Microsoft Yahei',sans-serif}header{height:126px;padding:18px 24px;border-bottom:1px solid #465560}h1{font-size:25px;margin:0 0 9px}p{margin:6px 0;color:#a8bbc5}button,input,select{background:#2d3a44;color:#eee;border:1px solid #627986;border-radius:5px;padding:7px;margin-right:5px}main{display:flex;height:calc(100vh - 126px)}#viewport{flex:1;overflow:auto;background:radial-gradient(ellipse at top,#28363f,#151e26);position:relative}#world{position:relative;transform-origin:0 0}svg{position:absolute;inset:0}.node{position:absolute;width:112px;min-height:88px;padding:4px;background:#283842;border:1px solid #67838e;border-radius:8px;text-align:center;cursor:pointer}.node:hover,.selected{border:2px solid #e2bc7d!important;background:#3b4c58}.node img{width:50px;height:50px;display:block;margin:auto}.node span{font-size:12px;line-height:17px;display:block}.node small{position:absolute;left:5px;top:4px;color:#e8c480;font-size:10px}.section{position:absolute;color:#e9c88c;font-size:17px;white-space:nowrap}aside{width:365px;padding:18px;overflow:auto;border-left:1px solid #405967}aside h2{font-size:21px;color:#e2bd83}aside p{line-height:1.85;white-space:pre-line}table{width:100%;font-size:12px;border-collapse:collapse}th,td{border-bottom:1px solid #40525c;padding:8px 3px;text-align:left}.muted{color:#97aab3}.badge{font-size:12px;border:1px solid #5b7480;padding:3px;display:inline-block;margin:3px}a{color:#e0be87}
</style><header><h1>通用国策 · 4.4.0</h1><p>153项国策 / 六阶行政 / 工业规模解锁 / 原有图标、永久地形经验和付费整合制度保留</p><select id="section"><option value="">导航至分支</option></select><input id="search" placeholder="搜索名称或ID"><button id="prev">−</button><button id="next">+</button><button id="reset">重置</button><a href="GENERIC-TREE.png">完整布局图</a><span class="muted">　源码预览，非游戏截图</span></header><main><div id="viewport"><div id="world"></div></div><aside><div id="detail"><h2>选择一个国策</h2><p>点击节点查看耗时、门槛和描述。可滚动查看所有分支，或使用上方导航。</p></div><h2>加成成长</h2><table><tr><th>项目</th><th>初 / 中 / 后期</th></tr><tr><td>行政稳定度</td><td>4 / 6 / 8 / 10 / 12 / 15%</td></tr><tr><td>每日政治点</td><td>0.05 → 0.20</td></tr><tr><td>军工产出</td><td>6 / 12 / 20%</td></tr><tr><td>科研速度</td><td>3 / 6 / 10%</td></tr><tr><td>船坞产出</td><td>8 / 16 / 25%</td></tr><tr><td>基建与铁路</td><td>10 / 20 / 30%</td></tr><tr><td>通用装备减价</td><td>4 / 7 / 10%</td></tr></table><p>通用与专属同类精神替换保留最高阶段。研究槽最多5个；马赛最多4个。各槽要求4 / 8 / 16座工厂。</p><p>制造商八层成长沿用4.3.2数值；装甲满层制造商与通用精神的合计减价为47%。其他独立学说、法律与国策仍会共同影响最终属性。</p></aside></main><script>const nodes=__DATA__,sections=__SECTIONS__;const world=document.getElementById('world'),view=document.getElementById('viewport');let zoom=1;const sx=60,sy=108,W=__WIDTH__,H=__HEIGHT__;world.style.width=W+'px';world.style.height=H+'px';const xy=n=>[100+n.x*sx,85+n.y*sy];const map=Object.fromEntries(nodes.map(n=>[n.id,n]));const NS='http://www.w3.org/2000/svg';let svg=document.createElementNS(NS,'svg');svg.setAttribute('width',W);svg.setAttribute('height',H);world.append(svg);for(const n of nodes){const [x,y]=xy(n);for(const id of n.parents){const [a,b]=xy(map[id]);let path=document.createElementNS(NS,'path');path.setAttribute('d',`M${a},${b+44}V${b+57}L${x},${y-57}V${y-44}`);path.setAttribute('stroke','#66818f');path.setAttribute('fill','none');svg.append(path)}}function choose(n){document.querySelectorAll('.selected').forEach(el=>el.classList.remove('selected'));document.getElementById(n.id).classList.add('selected');const box=document.getElementById('detail');box.replaceChildren();let h=document.createElement('h2');h.textContent=n.name;box.append(h);let meta=document.createElement('p');meta.textContent=n.section+' · '+n.days+'日'+(n.factories?' · ≥'+n.factories+'座工厂':'');box.append(meta);let p=document.createElement('p');p.textContent=n.description.split(String.fromCharCode(92)+'n').join(String.fromCharCode(10)).replaceAll(/§./g,'');box.append(p);let code=document.createElement('p');code.className='muted';code.textContent=n.id;box.append(code);for(const id of n.parents){let a=document.createElement('button');a.textContent='前置：'+map[id].name;a.onclick=()=>goto(map[id]);box.append(a)}}function goto(n){const [x,y]=xy(n);view.scrollTo({left:Math.max(0,(x-260)*zoom),top:Math.max(0,(y-120)*zoom),behavior:'smooth'});choose(n)}for(const n of nodes){const [x,y]=xy(n);let b=document.createElement('div');b.className='node';b.id=n.id;b.style.left=x-56+'px';b.style.top=y-44+'px';let img=document.createElement('img');img.src=n.icon;b.append(img);let s=document.createElement('span');s.textContent=n.name;b.append(s);let small=document.createElement('small');small.textContent=n.days+'日';b.append(small);b.onclick=()=>choose(n);world.append(b)}const sel=document.getElementById('section');for(const section of sections){let group=nodes.filter(n=>n.section===section.name),target=group.reduce((a,b)=>a.y<b.y?a:b);let opt=document.createElement('option');opt.value=target.id;opt.textContent=section.name;sel.append(opt);let h=document.createElement('div');h.className='section';let [x,y]=xy(target);h.style.left=x-55+'px';h.style.top=y-80+'px';h.textContent=section.name;world.append(h)}sel.onchange=()=>sel.value&&goto(map[sel.value]);document.getElementById('search').oninput=e=>{let q=e.target.value.trim().toLowerCase();if(q){let hit=nodes.find(n=>(n.name+n.id).toLowerCase().includes(q));if(hit)goto(hit)}};function scale(v){zoom=Math.min(1.75,Math.max(.5,v));world.style.zoom=zoom}document.getElementById('prev').onclick=()=>scale(zoom-.15);document.getElementById('next').onclick=()=>scale(zoom+.15);document.getElementById('reset').onclick=()=>{scale(1);view.scrollTo(0,0)};</script></html>'''
 template=template.replace('__DATA__',json.dumps(data,ensure_ascii=False).replace('</','<\\/')).replace('__SECTIONS__',json.dumps(d['sections'],ensure_ascii=False)).replace('__WIDTH__',str(w)).replace('__HEIGHT__',str(h))
 (output/'GENERIC.html').write_text(template,encoding='utf-8',newline='\n');print('Preview:',output)
if __name__=='__main__':main()
