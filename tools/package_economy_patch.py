"""Package only the approved French economy files with verified old/new hashes."""
from pathlib import Path
import json,zipfile,hashlib
ROOT=Path(__file__).resolve().parents[1];FOLDER='shadows_of_france_unification'
def sha(raw):return hashlib.sha256(raw).hexdigest()
def main():
 spec=json.loads((ROOT/'design/economy-patch-4.5.json').read_text(encoding='utf-8'));payload={};rows=[]
 assert len(spec['files'])==355
 for r in spec['files']:
  p=Path(r['relative']);assert not p.is_absolute() and '..' not in p.parts
  raw=(ROOT/'mod'/p).read_bytes();assert sha(raw)==r['sha256'],str(p)
  path=FOLDER+'/'+p.as_posix();payload[path]=raw
  rows.append(dict(path=path,bytes=len(raw),sha256=sha(raw),**({'previous_sha256':r['previous_sha256']} if r.get('previous_sha256') else {})))
 manifest=dict(format=1,kind='economy-map',version='4.5.0',folder=FOLDER,name='法兰西之影：统一战争（独立中文版）',files=rows,required_versions=['4.4.0','4.5.0'],game_engine_verified=False)
 payload['economy-manifest.json']=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
 payload['install-economy.ps1']=(ROOT/'tools/install_economy_patch.ps1').read_bytes()
 payload['README-ZH.md']=('# 法国资源与初始工业4.5.0补丁\n\n适用于已安装4.4.0。保存并关闭游戏，解压后运行 `powershell -ExecutionPolicy Bypass -File ./install-economy.ps1`。\n\n移除煤钢及战略资源低保；煤1500、钢1400、铝1100、油/钨/铬各1000、胶850。新开局按当地基础槽位80%向下取整配置工厂，移除514个旧补偿槽位。旧档用资源重分配决议，保留矿业追加及现有工厂。\n\n355文件补丁只覆盖明确清单；先核验并备份，拒绝覆盖额外修改。真实游戏界面和存档仍待引擎验收。\n').encode('utf-8')
 payload['ECONOMY-4.5.csv']=(ROOT/'docs/ECONOMY-4.5.csv').read_bytes()
 out=ROOT/'dist';out.mkdir(exist_ok=True);p=out/'shadows-of-france-economy-4.5.0.zip'
 with zipfile.ZipFile(p,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for n,b in payload.items():z.writestr(n,b)
 with zipfile.ZipFile(p) as z:
  assert z.testzip() is None
  for r in rows:assert sha(z.read(r['path']))==r['sha256']
 print(json.dumps(dict(ok=True,version='4.5.0',files=len(rows),path=str(p),bytes=p.stat().st_size,sha256=sha(p.read_bytes()))))
if __name__=='__main__':main()
