"""Package the reviewed script repairs as an old/new-hash bounded upgrade."""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = 'shadows_of_france_unification'


def main():
    spec = json.loads((ROOT / 'design/script-repairs-4.5.1.json').read_text(encoding='utf-8'))
    payload = {}
    rows = []
    for row in spec['files']:
        if not row['relative'].startswith('mod/'):
            continue
        relative = Path(row['relative'])
        assert not relative.is_absolute() and '..' not in relative.parts
        raw = (ROOT / relative).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == row['sha256']
        path = FOLDER + '/' + relative.as_posix().removeprefix('mod/')
        payload[path] = raw
        entry = dict(path=path, bytes=len(raw), sha256=row['sha256'])
        if row['previous_sha256']:
            entry['previous_sha256'] = row['previous_sha256']
        if row.get('compatible_sha256'):
            entry['compatible_sha256'] = row['compatible_sha256']
        rows.append(entry)
    manifest = dict(format=1, kind='script-repairs', version='4.5.1', folder=FOLDER,
                    name='法兰西之影：统一战争（独立中文版）', files=rows,
                    required_versions=['4.5.0', '4.5.1'], game_engine_verified=False)
    payload['repairs-manifest.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2)+'\n').encode('utf-8')
    payload['install-repairs.ps1'] = (ROOT / 'tools/install_script_repairs.ps1').read_bytes()
    payload['README-ZH.md'] = (ROOT / 'docs/SCRIPT-REPAIRS-4.5.1-ZH.md').read_bytes()
    dest = ROOT / 'dist/shadows-of-france-script-repairs-4.5.1.zip'
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, raw in payload.items():
            archive.writestr(name, raw)
    with zipfile.ZipFile(dest) as archive:
        assert archive.testzip() is None
        for row in rows:
            assert hashlib.sha256(archive.read(row['path'])).hexdigest() == row['sha256']
    print(json.dumps(dict(ok=True, version='4.5.1', files=len(rows), path=str(dest),
                         sha256=hashlib.sha256(dest.read_bytes()).hexdigest())))


if __name__ == '__main__':
    main()
