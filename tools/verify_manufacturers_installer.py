"""Exercise the Windows upgrade installer against isolated fixtures, never the game mod."""
import hashlib
import json
import os
import subprocess
import uuid
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = 'shadows_of_france_unification'
from package_manufacturers_patch import PAYLOAD


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def inventory(root):
    return {p.relative_to(root).as_posix(): digest(p.read_bytes())
            for p in root.rglob('*') if p.is_file()}


def verify():
    if os.name != 'nt':
        raise SystemExit('Windows PowerShell is required for installer fixtures.')
    package = ROOT / 'dist/shadows-of-france-manufacturers-4.3.2.zip'
    stage = ROOT / 'dist' / ('manufacturers-installer-fixtures-' + uuid.uuid4().hex)
    extracted = stage / 'package'
    with zipfile.ZipFile(package) as archive:
        assert archive.testzip() is None
        for item in archive.infolist():
            target = (extracted / item.filename).resolve()
            assert target.is_relative_to(extracted.resolve()), item.filename
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(item))
    manifest = json.loads((extracted / 'manufacturer-manifest.json').read_text(encoding='utf-8'))
    plan = json.loads((ROOT / 'design/regional-manufacturers.json').read_text(encoding='utf-8'))
    git = ['git', '-c', 'safe.directory=' + ROOT.as_posix()]

    def fixture(name):
        user_data = stage / name
        for relative in ['mod/' + path for path in PAYLOAD]:
            raw = subprocess.check_output(git + ['show', plan['baseline_commit'] + ':' + relative], cwd=ROOT)
            dest = user_data / 'mod' / FOLDER / relative.removeprefix('mod/')
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(raw)
        descriptor = subprocess.check_output(git + ['show', plan['baseline_commit'] + ':mod/descriptor.mod'], cwd=ROOT)
        descriptor += b'\npublishedfileid="3813153193"\npicture="Thumbnail-workshop.jpg"\n'
        (user_data / 'mod' / FOLDER / 'descriptor.mod').write_bytes(descriptor)
        (user_data / 'mod' / (FOLDER + '.mod')).write_bytes(descriptor)
        sentinel = user_data / 'mod' / FOLDER / 'common/characters/local-collaboration.txt'
        sentinel.parent.mkdir(parents=True, exist_ok=True)
        sentinel.write_bytes(b'# Another task owns this file.\n')
        return user_data

    def install(user_data, source=extracted, success=True):
        process = subprocess.run(['powershell.exe', '-NoProfile', '-ExecutionPolicy', 'Bypass',
            '-File', str(source / 'install-manufacturers.ps1'), '-UserDataPath', str(user_data),
            '-PackagePath', str(source)], capture_output=True)
        stdout = process.stdout.decode('utf-8', errors='replace')
        stderr = process.stderr.decode('utf-8', errors='replace')
        assert (process.returncode == 0) == success, stdout + stderr
        return json.loads(stdout) if success else stderr

    good = fixture('positive')
    before = inventory(good / 'mod')
    receipt = install(good)
    assert receipt['payload_files'] == 3 and receipt['introduced_files'] == 0
    for row in manifest['files']:
        assert digest((good / 'mod' / row['path']).read_bytes()) == row['sha256']
    sentinel = FOLDER + '/common/characters/local-collaboration.txt'
    assert inventory(good / 'mod')[sentinel] == before[sentinel]
    for name in [FOLDER + '/descriptor.mod', FOLDER + '.mod']:
        content = (good / 'mod' / name).read_text(encoding='utf-8')
        assert 'version="4.3.2"' in content
        assert 'publishedfileid="3813153193"' in content and 'picture="Thumbnail-workshop.jpg"' in content
    with zipfile.ZipFile(receipt['backup']) as backup:
        assert backup.testzip() is None
        assert all(digest(backup.read(name)) == sha for name, sha in before.items() if name != sentinel)
    updated = inventory(good / 'mod')
    repeat = install(good)
    assert repeat['introduced_files'] == 0 and inventory(good / 'mod') == updated

    modified = fixture('modified-core')
    focus = modified / 'mod' / FOLDER / 'common/ideas/sof_regional_manufacturers.txt'
    focus.write_bytes(focus.read_bytes() + b'\n# Local change must not be overwritten.\n')
    untouched = inventory(modified)
    error = install(modified, success=False)
    assert 'refusing to overwrite' in error and inventory(modified) == untouched

    traversal = fixture('traversal')
    bad_package = stage / 'traversal-package'
    bad_package.mkdir(parents=True)
    (bad_package / 'install-manufacturers.ps1').write_bytes((extracted / 'install-manufacturers.ps1').read_bytes())
    bad_manifest = json.loads(json.dumps(manifest))
    bad_manifest['files'][0]['path'] = '../../outside.txt'
    (bad_package / 'manufacturer-manifest.json').write_text(json.dumps(bad_manifest, ensure_ascii=False), encoding='utf-8')
    untouched = inventory(traversal)
    error = install(traversal, bad_package, success=False)
    assert 'Unexpected or repeated payload' in error and inventory(traversal) == untouched

    result = dict(ok=True, version='4.3.2', payload_files=3,
        scenarios=['4.3.0 upgrade with verified rollback backup', 'other-task file and workshop metadata preserved',
                   'repeat upgrade is byte-stable', 'modified core rejected before mutation',
                   'path traversal rejected before mutation'], game_engine_verified=False)
    output = ROOT / 'docs/reports/4.3.2/installer-fixtures.json'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(result))


if __name__ == '__main__':
    verify()
