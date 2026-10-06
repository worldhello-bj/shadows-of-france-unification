"""Offline interactive choropleth and exportable maps from actual state scripts."""
from pathlib import Path
from io import BytesIO
import json,base64,math
from PIL import Image,ImageDraw,ImageFont,ImageChops,ImageFilter
from hoi4_script import parse,one,scalar,entries
ROOT=Path(__file__).resolve().parents[1];MOD=ROOT/'mod'
COLORS={'coal':(218,167,93),'steel':(135,167,206),'aluminium':(202,206,218),'oil':(194,161,87),'rubber':(101,193,150),'tungsten':(137,151,220),'chromium':(197,141,208),'industry':(229,185,110)}
def font(size):
 for p in [Path('C:/Windows/Fonts/msyh.ttc'),Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')]:
  if p.exists():return ImageFont.truetype(str(p),size)
 return ImageFont.load_default()
def main():
 d=json.loads((ROOT/'design/economy-map-4.5.json').read_text(encoding='utf-8'));data=[]
 for r in d['states']:
  s=one(parse((MOD/r['path']).read_text(encoding='utf-8-sig')),'state').value;h=one(s,'history').value
  resources={n.key:int(n.value) for b in entries(s,'resources') for n in b.value}
  blocks=entries(h,'buildings');b=blocks[0].value if blocks else []
  factories={t:int(scalar(b,t,'0')) for t in ['industrial_complex','arms_factory','dockyard']}
  data.append(dict(id=r['id'],name=r['name'],region=r['region'],resources=resources,factories=factories,industry=sum(factories.values()),slots=r['slots']))
 out=ROOT/'docs/previews/4.5.0';out.mkdir(parents=True,exist_ok=True)
 mask=Image.open(ROOT/'references/economy-4.5/state-map-ids.png').convert('RGB')
 # Work at the export resolution; nearest-neighbor keeps state IDs exact.
 small=mask.copy();small.thumbnail((500,600),Image.Resampling.NEAREST)
 lookup={r['id']:r for r in data};labels=dict(d['labels'],industry='初始工厂')
 metrics=['coal','steel','aluminium','oil','rubber','tungsten','chromium','industry']
 board=Image.new('RGB',(2160,1500),(17,24,33));draw=ImageDraw.Draw(board)
 draw.text((38,22),'法兰西地区经济 · 4.5.0',font=font(33),fill=(236,213,171))
 draw.text((38,74),'真实州界源码预览  ·  80州有资源 / 262州无资源  ·  初始工厂810座 / 移除514个补偿槽位',font=font(22),fill=(174,189,199))
 for index,metric in enumerate(metrics):
  x=30+(index%4)*535;y=135+(index//4)*675
  values={r['id']:r['industry'] if metric=='industry' else r['resources'].get(metric,0) for r in data};maximum=max(values.values())
  palette={0:(13,20,30),65534:(37,44,54)};accent=COLORS[metric]
  for sid,value in values.items():
   intensity=.22+.78*math.sqrt(value/maximum) if value else 0
   palette[sid]=tuple(round(46*(1-intensity)+color*intensity) for color in accent) if value else (48,57,68)
  colors=[palette.get((r<<8)|g,(13,20,30)) for r,g,b in small.getdata()]
  pic=Image.new('RGB',small.size);pic.putdata(colors)
  gray=small.convert('L');border=ImageChops.difference(small,small.offset(1,0) if hasattr(small,'offset') else ImageChops.offset(small,1,0)).convert('L').point(lambda n:65 if n else 0)
  border2=ImageChops.difference(small,ImageChops.offset(small,0,1)).convert('L').point(lambda n:65 if n else 0)
  pic.paste((178,188,193),(0,0),ImageChops.lighter(border,border2))
  draw.text((x,y),labels[metric],font=font(27),fill=accent)
  total=sum(values.values());carriers=sum(v>0 for v in values.values())
  draw.text((x,y+39),f'基础总量 {total:,}  /  {carriers}州',font=font(19),fill=(173,190,201))
  board.paste(pic,(x,y+77))
  draw.text((x,y+625),'灰色：本项为0；亮色：集中产区',font=font(16),fill=(155,173,186))
 board.save(out/'ECONOMY-MAPS.png')
 mask_buffer=BytesIO();mask.save(mask_buffer,format='PNG')
 settings=dict(states=data,labels=labels,colors=COLORS,summary=d['summary'],profiles=d['resource_profiles'])
 payload=json.dumps(settings,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
 script='''const D=__DATA__,byId=new Map(D.states.map(s=>[s.id,s]));
const metric=document.getElementById('metric'),canvas=document.getElementById('map'),ctx=canvas.getContext('2d'),info=document.getElementById('info'),table=document.getElementById('rows'),search=document.getElementById('search');
let pixels,w,h,active=null;
const value=(s,m)=>m==='industry'?s.industry:(s.resources[m]||0);
function detail(s){active=s;info.replaceChildren();if(!s){info.textContent='将鼠标移到州上，查看资源、工厂与槽位。';return;}
 const title=document.createElement('h2');title.textContent=s.name;info.append(title);
 const lines=[`初始工厂 ${s.industry} / 基础槽位 ${s.slots}`,`民工 ${s.factories.industrial_complex} · 军工 ${s.factories.arms_factory} · 船坞 ${s.factories.dockyard}`,...Object.entries(D.labels).filter(([k])=>k!=='industry').map(([k,label])=>`${label} ${s.resources[k]||0}`)];
 for(const line of lines){const p=document.createElement('p');p.textContent=line;info.append(p);}}
function render(){if(!pixels)return;const m=metric.value,values=D.states.map(s=>value(s,m)),max=Math.max(...values),accent=D.colors[m],out=ctx.createImageData(w,h);
 for(let i=0;i<w*h;i++){let sid=(pixels[i*4]<<8)|pixels[i*4+1],s=byId.get(sid),v=s?value(s,m):0,color=s?[48,57,68]:(sid===65534?[37,44,54]:[13,20,30]);
  if(v){let t=.22+.78*Math.sqrt(v/max);color=accent.map(c=>Math.round(46*(1-t)+c*t));}
  let edge=(i%w>0&&sid!==((pixels[(i-1)*4]<<8)|pixels[(i-1)*4+1]))||(i>=w&&sid!==((pixels[(i-w)*4]<<8)|pixels[(i-w)*4+1]));
  for(let k=0;k<3;k++)out.data[i*4+k]=edge?Math.round(color[k]*.78+160*.22):color[k];out.data[i*4+3]=255;}
 ctx.putImageData(out,0,0);document.getElementById('total').textContent=values.reduce((a,b)=>a+b,0).toLocaleString();document.getElementById('carriers').textContent=values.filter(v=>v>0).length;
 document.getElementById('profile').textContent=m==='industry'?'当地基础共享槽位×80%，向下取整；取消旧补偿槽位。':D.profiles[m];renderTable();}
function renderTable(){const q=search.value.trim().toLowerCase(),m=metric.value;table.replaceChildren();
 for(const s of [...D.states].filter(s=>!q||s.name.toLowerCase().includes(q)||String(s.id)===q).sort((a,b)=>value(b,m)-value(a,m)||a.id-b.id)){const tr=document.createElement('tr');for(const text of [s.name,value(s,m),`${s.industry}/${s.slots}`]){let td=document.createElement('td');td.textContent=text;tr.append(td);}tr.tabIndex=0;tr.onclick=()=>detail(s);tr.onkeydown=e=>{if(e.key==='Enter')detail(s);};table.append(tr);}}
canvas.onmousemove=e=>{const box=canvas.getBoundingClientRect(),x=Math.floor((e.clientX-box.left)*w/box.width),y=Math.floor((e.clientY-box.top)*h/box.height),i=(y*w+x)*4;if(x>=0&&y>=0&&x<w&&y<h)detail(byId.get((pixels[i]<<8)|pixels[i+1]));};
metric.onchange=render;search.oninput=renderTable;
const img=new Image();img.onload=()=>{w=img.width;h=img.height;canvas.width=w;canvas.height=h;ctx.drawImage(img,0,0);pixels=ctx.getImageData(0,0,w,h).data;render();};img.src='data:image/png;base64,__MASK__';
detail(null);'''.replace('__DATA__',payload).replace('__MASK__',base64.b64encode(mask_buffer.getvalue()).decode('ascii'))
 options=''.join(f'<option value="{m}">{labels[m]}</option>' for m in metrics)
 html='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>法国资源与初始工业 · 4.5.0</title>
<style>*{box-sizing:border-box}body{margin:0;background:#101821;color:#d9e0e3;font:16px/1.55 "Microsoft YaHei",sans-serif}header{padding:22px 30px;border-bottom:1px solid #354351}h1{margin:0;color:#e4c691;font-size:27px}.sub{color:#9fb1be;margin:8px 0 0}main{display:grid;grid-template-columns:minmax(500px,1fr) 350px;gap:24px;padding:24px 30px}select,input{background:#202d3a;color:#e5e9eb;border:1px solid #566574;border-radius:4px;padding:9px;font:inherit}select{min-width:180px}canvas{display:block;width:100%;height:auto;background:#0d141e;border:1px solid #394959;margin-top:16px}.stats{display:flex;gap:35px;margin:15px 0;color:#9fb1be}.stats strong{font-size:29px;color:#ead3aa}#profile{min-height:50px;color:#bdcbd4}aside{min-width:0}#info{padding:18px;background:#1a2632;border-left:3px solid #cba974;min-height:300px}h2{margin:0 0 10px;color:#e2c897}#info p{margin:5px 0}input{width:100%;margin:16px 0 10px}.scroll{max-height:530px;overflow:auto}table{border-collapse:collapse;width:100%;font-size:14px}th{text-align:left;position:sticky;top:0;background:#1a2733}td,th{padding:8px;border-bottom:1px solid #2b3a48}tr:hover,tr:focus{background:#293e4d;cursor:pointer}footer{padding:16px 30px 28px;color:#90a5b5}a{color:#e1c896}@media(max-width:950px){main{grid-template-columns:1fr;padding:18px}header{padding:18px}.scroll{max-height:350px}}</style>
<header><h1>法国地区资源与初始工业 · 4.5.0</h1><p class="sub">80个资源州 · 262个无资源州 · 取消地方资源低保 · 810座初始工厂</p></header>
<main><section><select id="metric">__OPTIONS__</select><div class="stats"><span>法国基础总量<br><strong id="total">—</strong></span><span>本项产区州数<br><strong id="carriers">—</strong></span></div><p id="profile"></p><canvas id="map" aria-label="资源与初始工厂州界地图"></canvas><p class="sub">灰色：本项为0；亮色：产区集中。资源量是游戏供给，包含架空扩展。</p></section>
<aside><div id="info"></div><input id="search" placeholder="搜索州名或州ID" aria-label="搜索州"><div class="scroll"><table><thead><tr><th>地区</th><th>当前项</th><th>工厂/槽位</th></tr></thead><tbody id="rows"></tbody></table></div></aside></main>
<footer>新开局按当地基础槽位的80%配置工厂，向下取整；旧档保留已有工厂，可用决议一次性重分配资源。此图来自实际州界与源码，游戏内显示仍待验收。 <a href="ECONOMY-MAPS.png">下载总览图</a> · <a href="../../ECONOMY-4.5.csv">逐州配置</a></footer><script>__SCRIPT__</script></html>'''
 (out/'ECONOMY.html').write_text(html.replace('__OPTIONS__',options).replace('__SCRIPT__',script),encoding='utf-8',newline='\n')
 (ROOT/'dist/economy-preview-check.js').write_text(script,encoding='utf-8',newline='\n')
 print(json.dumps(dict(ok=True,states=len(data),map_size=mask.size,output=str(out))))
if __name__=='__main__':main()
