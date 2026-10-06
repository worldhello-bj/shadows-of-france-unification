"""Exercise the real narrow Windows installer, including deleted-file rollback."""
import hashlib
import json
import os
import re
import shutil
import subprocess
import uuid
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = 'shadows_of_france_unification'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def inventory(root):
    return {p.relative_to(root).as_posix(): sha(p.read_bytes()) for p in root.rglob('*') if p.is_file()}


def verify():
    assert os.name == 'nt', 'Windows PowerShell is required.'
    stage = ROOT/'dist'/('integration-fixtures-'+uuid.uuid4().hex)
    extracted = stage/'package'
    with zipfile.ZipFile(ROOT/'dist/shadows-of-france-focus-integration-4.6.0.zip') as z:
        assert z.testzip() is None
        for name in z.namelist():
            target = (extracted/name).resolve()
            assert target.is_relative_to(extracted.resolve())
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(z.read(name))
    manifest = json.loads((extracted/'integration-manifest.json').read_text(encoding='utf-8'))
    spec = json.loads((ROOT/'design/focus-integration-4.6.json').read_text(encoding='utf-8'))
    # History is fetched by CI and is immutable; no duplicate 13MB atlas in source.
    git_root = ROOT
    while not (git_root/'.git').exists():
        assert git_root.parent != git_root
        git_root = git_root.parent
    baseline = {}
    for row in manifest['files']+manifest['deletions']:
        rel = 'mod/'+row['path'].removeprefix(FOLDER+'/')
        raw = subprocess.check_output(['git', '-c', 'safe.directory='+git_root.as_posix(),
              'show', spec['baseline_commit']+':'+rel], cwd=git_root)
        assert sha(raw) == row['previous_sha256']
        baseline[row['path']] = raw

    def fixture(name):
        user = stage/name
        for relative, raw in baseline.items():
            dest = user/'mod'/relative
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
        desc = re.sub(br'(?m)^version="[^"]+"', b'version="4.5.1"', (ROOT/'mod/descriptor.mod').read_bytes())
        desc += b'\nremote_file_id="3813153193"\npicture="Thumbnail-workshop.jpg"\n'
        for rel in [FOLDER+'/descriptor.mod', FOLDER+'.mod']:
            (user/'mod'/rel).write_bytes(desc)
        sentinel = user/'mod'/FOLDER/'common/characters/other-task.txt'
        sentinel.parent.mkdir(parents=True, exist_ok=True)
        sentinel.write_bytes(b'# Preserve another task\n')
        return user

    def install(user, package=extracted, success=True):
        result = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                 '-File', str(package/'install-focus-integration.ps1'), '-UserDataPath', str(user),
                 '-PackagePath', str(package)], capture_output=True)
        out = result.stdout.decode('utf-8', errors='replace')
        err = result.stderr.decode('utf-8', errors='replace')
        assert (result.returncode == 0) == success, out+err
        return json.loads(out) if success else err

    user = fixture('upgrade')
    before = inventory(user/'mod')
    receipt = install(user)
    assert receipt['payload_files'] == 12 and receipt['obsolete_texture_paths'] == 2
    for row in manifest['files']:
        assert sha((user/'mod'/row['path']).read_bytes()) == row['sha256']
    for row in manifest['deletions']:
        assert not (user/'mod'/row['path']).exists()
    for rel in [FOLDER+'/descriptor.mod', FOLDER+'.mod']:
        content = (user/'mod'/rel).read_text(encoding='utf-8')
        assert 'version="4.6.0"' in content
        assert 'remote_file_id="3813153193"' in content and 'picture="Thumbnail-workshop.jpg"' in content
    sentinel = FOLDER+'/common/characters/other-task.txt'
    assert inventory(user/'mod')[sentinel] == before[sentinel]
    with zipfile.ZipFile(receipt['backup']) as z:
        assert z.testzip() is None
        assert all(sha(z.read(rel)) == digest for rel, digest in before.items() if rel != sentinel)
    after = inventory(user/'mod')
    install(user)
    assert inventory(user/'mod') == after

    for name, relative in [('modified-cabinet', manifest['files'][1]['path']),
                           ('modified-obsolete', manifest['deletions'][0]['path'])]:
        user = fixture(name)
        path = user/'mod'/relative
        path.write_bytes(path.read_bytes()+b'\n# Local edit\n')
        unchanged = inventory(user)
        err = install(user, success=False)
        assert 'refusing to' in err and inventory(user) == unchanged

    for name, mutation in [('traversal', lambda m: m['files'][0].update(path='../../outside.txt')),
                           ('bad-hash', lambda m: m['files'][0].update(sha256='0'*64))]:
        package = stage/(name+'-package')
        shutil.copytree(extracted, package)
        forged = json.loads(json.dumps(manifest))
        mutation(forged)
        (package/'integration-manifest.json').write_text(json.dumps(forged, ensure_ascii=False), encoding='utf-8')
        user = fixture(name)
        unchanged = inventory(user)
        install(user, package, success=False)
        assert inventory(user) == unchanged

    # Inject a fixture-only I/O failure after removal. The shipped script is intact.
    package = stage/'rollback-package'
    shutil.copytree(extracted, package)
    path = package/'install-focus-integration.ps1'
    text = path.read_text(encoding='utf-8-sig')
    assert '# integration-deletions-complete' in text
    path.write_text(text.replace('# integration-deletions-complete', "throw 'Fixture failure after deletion'"), encoding='utf-8-sig')
    user = fixture('rollback')
    unchanged = inventory(user/'mod')
    install(user, package, success=False)
    assert inventory(user/'mod') == unchanged
    assert len(list((user/'mod-backups').glob('*.zip'))) == 1
    report = dict(ok=True, version='4.6.0', payload_files=12, obsolete_textures=2,
        scenarios=['upgrade with hash-verified backup', 'repeat upgrade is byte-stable',
                   'other-task file and workshop metadata preserved', 'modified cabinet rejected',
                   'modified obsolete texture rejected', 'path traversal rejected', 'bad hash rejected',
                   'partial failure restores deleted textures and every changed file'], game_engine_verified=False)
    out = ROOT/'docs/reports/4.6.0/installer-fixtures.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report))


if __name__ == '__main__':
    verify()
