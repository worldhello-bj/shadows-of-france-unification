"""Build an installable release from source using the existing verified installer."""
import argparse,hashlib,json,re,shutil,zipfile
from pathlib import Path
from validate import ROOT,MOD,validate

FOLDER='shadows_of_france_unification'
def sha(data):return hashlib.sha256(data).hexdigest()

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'dist');args=parser.parse_args()
    report=validate();assert report['ok'],report['errors']
    args.output.mkdir(parents=True,exist_ok=True)
    folder=args.output.resolve();assert folder!=ROOT.resolve(),'Output must be a separate directory'
    version=report['version'];files={FOLDER+'/'+p.relative_to(MOD).as_posix():p.read_bytes() for p in MOD.rglob('*') if p.is_file()}
    outer=(MOD/'descriptor.mod').read_text(encoding='utf-8-sig').rstrip()+f'\npath="mod/{FOLDER}"\n'
    files[FOLDER+'.mod']=outer.encode('utf-8')
    manifest=dict(format=2,kind='standalone',folder=FOLDER,name='法兰西之影：统一战争（独立中文版）',version=version,
        upstream_is_required=False,release_channel='collaboration-candidate',game_engine_verified=False,
        files=[dict(path=k,bytes=len(v),sha256=sha(v)) for k,v in sorted(files.items())])
    files['package-manifest.json']=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    files['install.ps1']=(ROOT/'install.ps1').read_bytes()
    files['README-ZH.md']=(ROOT/'README.md').read_bytes()
    files['validation.json']=(json.dumps(report,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    path=folder/f'shadows-of-france-{version}.zip'
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name,data in files.items():z.writestr(name,data)
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        for row in manifest['files']:assert sha(z.read(row['path']))==row['sha256']
    print(json.dumps(dict(ok=True,version=version,path=str(path),bytes=path.stat().st_size,sha256=sha(path.read_bytes()),payload_files=len(manifest['files'])),ensure_ascii=False))

if __name__=='__main__':main()
