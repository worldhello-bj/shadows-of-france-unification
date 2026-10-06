"""Exercise the real narrow installer against workspace-local installations."""
from pathlib import Path
import hashlib,json,shutil,subprocess,time
from build_ideology_panel import ROOT,MOD,PASS,GUI_REL,SYNC_REL


def inventory(folder):
    return {p.relative_to(folder).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.rglob('*') if p.is_file()}


def main():
    if (ROOT/'design/focus-integration-4.6.json').is_file():
        from verify_focus_integration_installer import verify
        return verify()
    stage=ROOT/'dist/ideology-panel-patch';manifest=json.loads((stage/'ideology-panel-manifest.json').read_text(encoding='utf-8'))
    testroot=PASS/'installer-fixtures'/str(time.time_ns());testroot.mkdir(parents=True)
    assert testroot.resolve().is_relative_to(PASS.resolve())
    shell=shutil.which('pwsh') or shutil.which('powershell');assert shell
    installer=ROOT/'tools/install_ideology_panel.ps1';cases=[]
    def fixture(name,version='4.4.0'):
        data=testroot/name;target=data/'mod/shadows_of_france_unification';target.mkdir(parents=True)
        for rel in (GUI_REL,SYNC_REL):
            p=target/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes((ROOT/'references/ideology-panel'/rel).read_bytes())
        descriptor=f'version="{version}"\nname="法兰西之影：统一战争（独立中文版）"\nremote_file_id="publication-sentinel"\n'
        (target/'descriptor.mod').write_text(descriptor,encoding='utf-8')
        (data/'mod/shadows_of_france_unification.mod').write_text(descriptor+'path="mod/shadows_of_france_unification"\n',encoding='utf-8')
        for rel in ('common/national_focus/sof_mrs_red.txt','common/national_focus/SoF_generic.txt','gfx/interface/unrelated.dds'):
            p=target/rel;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'Unrelated 4.4 gameplay and exclusive icons sentinel\n')
        return data,target
    def run(data,package=stage):
        return subprocess.run([shell,'-NoProfile','-ExecutionPolicy','Bypass','-File',str(installer),'-UserDataPath',str(data),'-PackagePath',str(package)],capture_output=True,text=True,encoding='utf-8')
    data,target=fixture('latest-install')
    before=inventory(data/'mod');result=run(data);assert result.returncode==0,result.stderr
    receipt=json.loads(result.stdout);after=inventory(data/'mod')
    expected={r['path']:r['sha256'] for r in manifest['files']}
    assert all(after[p]==h for p,h in expected.items())
    assert all(after[p]==h for p,h in before.items() if p not in expected)
    assert receipt['installed_version']=='4.4.0' and receipt['introduced_files']==11
    assert Path(receipt['backup']).is_file()
    cases.append('Install on 4.4.0; preserve descriptors, publication identity, national focuses and unrelated icons')
    again=run(data);assert again.returncode==0,again.stderr
    assert inventory(data/'mod')==after
    cases.append('Idempotent repeat installation')
    for name,change in (
        ('modified-native',lambda data,target:(target/GUI_REL).write_bytes((target/GUI_REL).read_bytes()+b'# another chat edit\n')),
        ('conflicting-new-file',lambda data,target:write_conflict(target/'interface/sofzh_ideology_panel.gui')),
        ('descriptor-disagreement',lambda data,target:(data/'mod/shadows_of_france_unification.mod').write_text('version="4.3.3"\nname="法兰西之影：统一战争（独立中文版）"\n',encoding='utf-8')),
    ):
        data,target=fixture(name);change(data,target);before=inventory(data/'mod');result=run(data)
        assert result.returncode!=0 and inventory(data/'mod')==before,(name,result.stdout,result.stderr)
        cases.append('Reject without mutation: '+name)
    data,target=fixture('outdated-version','4.3.0');before=inventory(data/'mod');result=run(data)
    assert result.returncode!=0 and inventory(data/'mod')==before
    cases.append('Reject unsupported old version')
    for name,mutation in (
        ('escaped-path',lambda m:m['files'][0].update(path='shadows_of_france_unification/../../outside.txt')),
        ('bad-hash',lambda m:m['files'][0].update(sha256='0'*64))
    ):
        package=testroot/(name+'-package');shutil.copytree(stage,package)
        path=package/'ideology-panel-manifest.json';forged=json.loads(path.read_text(encoding='utf-8'));mutation(forged)
        path.write_text(json.dumps(forged,ensure_ascii=False),encoding='utf-8')
        data,target=fixture(name);before=inventory(data/'mod');result=run(data,package)
        assert result.returncode!=0 and inventory(data/'mod')==before,(name,result.stderr)
        cases.append('Reject malformed package: '+name)
    data,target=fixture('partial-write-rollback')
    blocker=target/'gfx/interface/sofzh_ideology_panel/segments.dds';blocker.mkdir(parents=True)
    before=inventory(data/'mod');result=run(data)
    assert result.returncode!=0 and inventory(data/'mod')==before,result.stderr
    assert blocker.is_dir() and len(list((data/'mod-backups').glob('*.zip')))==1
    cases.append('Restore original file bytes and remove only introduced files after partial write failure')
    report=dict(ok=True,cases=len(cases),scenarios=cases,fixture_root=str(testroot),game_engine_verified=False,scope='Real PowerShell installer on workspace-local fixture directories')
    (ROOT/'docs/reports/ideology-panel/installer.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


def write_conflict(path):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(b'pre-existing UI edit')


if __name__=='__main__':main()
