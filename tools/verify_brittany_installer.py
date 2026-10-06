"""Exercise backup, idempotence and rejection against the real GitHub overlay."""
from pathlib import Path
import hashlib,json,subprocess,sys,tempfile,zipfile
from build_brittany_focus import ROOT,REPORT


def main():
    package=ROOT/'dist/brittany-github-package'
    manifest=json.loads((package/'manifest.json').read_text(encoding='utf-8'))
    with tempfile.TemporaryDirectory(prefix='sof-brittany-',dir=ROOT/'dist') as temp:
        assert Path(temp).resolve().is_relative_to((ROOT/'dist').resolve())
        target=Path(temp)/'shadows_of_france_unification';target.mkdir()
        for row in manifest['files']:
            if row['before_sha256'] is None:continue
            raw=(ROOT/'references/brittany-github-base/mod'/row['path']).read_bytes()
            assert hashlib.sha256(raw).hexdigest()==row['before_sha256']
            p=target/row['path'];p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
        sentinel=target/'other-task.txt';sentinel.write_text('Keep shared work.',encoding='utf-8')
        descriptor=target.parent/'shadows_of_france_unification.mod';descriptor.write_text('Keep existing metadata.',encoding='utf-8')
        def run():return subprocess.run([sys.executable,str(package/'install.py'),'--package',str(package),'--target',str(target)],capture_output=True,text=True,encoding='utf-8')
        first=run();assert first.returncode==0,first.stderr
        receipt=json.loads((package/'install-receipt.json').read_text(encoding='utf-8'))
        assert receipt['changed_files']==120 and receipt['backup_verified']
        with zipfile.ZipFile(receipt['backup']) as z:
            assert z.testzip() is None
            for row in manifest['files']:
                if row['before_sha256'] is not None:assert hashlib.sha256(z.read('mod/'+row['path'])).hexdigest()==row['before_sha256']
        second=run();assert second.returncode==0,second.stderr
        assert json.loads((package/'install-receipt.json').read_text(encoding='utf-8'))['changed_files']==0
        p=target/manifest['files'][0]['path'];p.write_bytes(p.read_bytes()+b'\n# Concurrent change\n')
        before={f.relative_to(target).as_posix():f.read_bytes() for f in target.rglob('*') if f.is_file()}
        conflict=run();assert conflict.returncode!=0
        assert before=={f.relative_to(target).as_posix():f.read_bytes() for f in target.rglob('*') if f.is_file()}
        assert sentinel.read_text(encoding='utf-8')=='Keep shared work.' and descriptor.read_text(encoding='utf-8')=='Keep existing metadata.'
    report=dict(ok=True,first_install_changed_files=120,idempotent_reinstall_changed_files=0,backup_verified=True,foreign_work_preserved=True,metadata_preserved=True,concurrent_edit_rejected_before_write=True,game_engine_verified=False)
    (REPORT/'github-installer-verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':main()
