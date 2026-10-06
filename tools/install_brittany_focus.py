"""Install only a reviewed Brittany overlay, with hashes and recoverable backup."""
from pathlib import Path
import argparse
import datetime
import hashlib
import json
import subprocess
import zipfile


def sha(raw):return hashlib.sha256(raw).hexdigest()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--package',type=Path)
    parser.add_argument('--target',type=Path,default=Path.home()/'Documents/Paradox Interactive/Hearts of Iron IV/mod/shadows_of_france_unification')
    args=parser.parse_args()
    script=Path(__file__).resolve()
    package=args.package or (script.parent if (script.parent/'manifest.json').exists() else script.parents[1]/'dist/brittany-expansion-package')
    package=package.resolve();target=args.target.resolve()
    assert target.is_dir() and target.name=='shadows_of_france_unification','Existing standalone mod required'
    live=(Path.home()/'Documents/Paradox Interactive/Hearts of Iron IV/mod/shadows_of_france_unification').resolve()
    if target==live:
        running=subprocess.check_output(['powershell.exe','-NoProfile','-Command',
            'Get-Process -Name hoi4 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id; exit 0'],creationflags=subprocess.CREATE_NO_WINDOW).decode('mbcs').strip()
        assert not running,'An existing HOI4 session is running; save and close it before installing.'
    manifest=json.loads((package/'manifest.json').read_text(encoding='utf-8'))
    assert manifest['kind']=='brittany-focus-overlay' and manifest['validated'] is True
    before={};after={};rows=[]
    for entry in manifest['files']:
        rel=entry['path'];p=(target/rel).resolve();src=(package/'files'/rel).resolve()
        assert p.is_relative_to(target) and src.is_relative_to(package/'files') and ':' not in rel and '\\' not in rel
        assert not any(x.is_symlink() or x.is_junction() for x in [target,p,*p.parents]),'Linked target path'
        raw=src.read_bytes();assert sha(raw)==entry['sha256'],('Unreviewed package file',rel)
        current=p.read_bytes() if p.exists() else None
        check=sha(current) if current is not None else None
        assert check in [entry['before_sha256'],entry['sha256']],('Concurrent installed edit',rel)
        before[rel]=current;after[rel]=raw;rows.append(dict(path=rel,before_sha256=check,sha256=entry['sha256']))
    other={p.relative_to(target).as_posix():sha(p.read_bytes()) for p in target.rglob('*') if p.is_file() and p.relative_to(target).as_posix() not in after}
    metadata={}
    for p in [target.parent/'shadows_of_france_unification.mod',target.parents[1]/'dlc_load.json']:
        if p.is_file():metadata[p]=p.read_bytes()
    backup_dir=package/'backups';backup_dir.mkdir(parents=True,exist_ok=True)
    backup=backup_dir/('before-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f')+'.zip')
    with zipfile.ZipFile(backup,'x',zipfile.ZIP_DEFLATED) as z:
        z.writestr('rollback-manifest.json',json.dumps(rows,indent=2))
        for rel,raw in before.items():
            if raw is not None:z.writestr('mod/'+rel,raw)
        for p,raw in metadata.items():z.writestr('metadata/'+p.name,raw)
    with zipfile.ZipFile(backup) as z:
        assert z.testzip() is None
        assert all(z.read('mod/'+rel)==raw for rel,raw in before.items() if raw is not None)
    changed=[]
    try:
        for rel,raw in after.items():
            p=target/rel
            assert (p.read_bytes() if p.exists() else None)==before[rel],('Changed during installation',rel)
            if raw!=before[rel]:
                p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw);changed.append(rel)
        assert all((target/rel).read_bytes()==raw for rel,raw in after.items())
        assert all(sha((target/rel).read_bytes())==h for rel,h in other.items()),'Another runtime file changed during installation'
        assert all(p.read_bytes()==raw for p,raw in metadata.items()),'Metadata changed during installation'
    except BaseException:
        for rel in changed:
            p=(target/rel).resolve();assert p.is_relative_to(target)
            if p.read_bytes()!=after[rel]:continue  # never overwrite another writer
            if before[rel] is None:p.unlink()
            else:p.write_bytes(before[rel])
        raise
    report=dict(ok=True,installed=True,target=str(target),files=rows,changed_files=len(changed),
                backup=str(backup),backup_verified=True,other_runtime_files_preserved=len(other),
                metadata_preserved=True,focuses=manifest['focuses'],delegates=manifest['delegates'],reserves=manifest['reserves'],home_events=manifest['home_events'],game_engine_verified=False)
    (package/'install-receipt.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='files'},ensure_ascii=False))


if __name__=='__main__':main()
