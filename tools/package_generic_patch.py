"""Offline, bounded shared-tree upgrade from the installed 4.3.3 base."""
from pathlib import Path
import json,zipfile,hashlib
ROOT=Path(__file__).resolve().parents[1];FOLDER='shadows_of_france_unification'
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
 spec=json.loads((ROOT/'design/generic-patch-4.4.json').read_text(encoding='utf-8'));rows=[];payload={}
 for row in spec['files']:
  path=Path(row['relative']);assert not path.is_absolute() and '..' not in path.parts
  raw=(ROOT/'mod'/path).read_bytes();assert sha(raw)==row['sha256'],str(path)
  name=FOLDER+'/'+path.as_posix();payload[name]=raw;r=dict(path=name,bytes=len(raw),sha256=sha(raw))
  if row.get('previous_sha256'):r['previous_sha256']=row['previous_sha256']
  rows.append(r)
 manifest=dict(format=1,kind='generic-focus',version='4.4.0',folder=FOLDER,name='法兰西之影：统一战争（独立中文版）',files=rows,required_versions=['4.3.3','4.4.0'],game_engine_verified=False)
 payload['generic-manifest.json']=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode('utf-8');payload['install-generic.ps1']=(ROOT/'tools/install_generic_patch.ps1').read_bytes()
 payload['README-ZH.md']=('# 通用国策4.4.0升级补丁\n\n适用已安装4.3.3。保存并关闭游戏，解压后运行 `powershell -ExecutionPolicy Bypass -File ./install-generic.ps1`。\n\n153项国策保持ID，重排分支，六阶行政，工业/科研改为工厂规模门槛。制造商八层和地区地形经验保留。仅替换清单中的文件；提前校验与备份，出现额外修改时拒绝覆盖。\n\n旧档只整理精神等级；不重复发放政治点、工厂、部队和科技。真实存档、游戏布局及DLC装备发放仍待游戏内验收。\n').encode('utf-8')
 output=ROOT/'dist';output.mkdir(exist_ok=True);path=output/'shadows-of-france-generic-4.4.0.zip'
 with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
  for n,b in payload.items():z.writestr(n,b)
 with zipfile.ZipFile(path) as z:
  assert z.testzip() is None
  for r in rows:assert sha(z.read(r['path']))==r['sha256']
 print(json.dumps(dict(ok=True,version='4.4.0',payload_files=len(rows),path=str(path),sha256=sha(path.read_bytes()),bytes=path.stat().st_size)))
if __name__=='__main__':main()
