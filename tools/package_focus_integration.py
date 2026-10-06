"""Build the hash-bounded 4.5.1 -> 4.6.0 integration patch."""
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = 'shadows_of_france_unification'


def main():
    spec = json.loads((ROOT/'design/focus-integration-4.6.json').read_text(encoding='utf-8'))
    payload, rows, deleted = {}, [], []
    for row in spec['files']:
        rel = Path(row['relative'])
        assert rel.parts[0] == 'mod' and '..' not in rel.parts and not rel.is_absolute()
        raw = (ROOT/rel).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == row['sha256'], str(rel)
        name = FOLDER+'/'+rel.as_posix().removeprefix('mod/')
        payload[name] = raw
        rows.append(dict(path=name, bytes=len(raw), sha256=row['sha256'], previous_sha256=row['previous_sha256']))
    for row in spec['deletions']:
        assert not (ROOT/row['relative']).exists(), row['relative']
        deleted.append(dict(path=FOLDER+'/'+row['relative'].removeprefix('mod/'), previous_sha256=row['previous_sha256']))
    manifest = dict(format=2, kind='focus-integration', version='4.6.0', folder=FOLDER,
                    name='法兰西之影：统一战争（独立中文版）', files=rows, deletions=deleted,
                    required_versions=['4.5.1', '4.6.0'], game_engine_verified=False)
    assert len(rows) == 12 and len(deleted) == 2
    payload['integration-manifest.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2)+'\n').encode('utf-8')
    payload['install-focus-integration.ps1'] = (ROOT/'tools/install_focus_integration.ps1').read_bytes()
    payload['README-ZH.md'] = (ROOT/'docs/FOCUS-INTEGRATION-4.6-ZH.md').read_bytes()
    dest = ROOT/'dist/shadows-of-france-focus-integration-4.6.0.zip'
    dest.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, raw in payload.items():
            archive.writestr(name, raw)
    with zipfile.ZipFile(dest) as archive:
        assert archive.testzip() is None
        for row in rows:
            assert hashlib.sha256(archive.read(row['path'])).hexdigest() == row['sha256']
    print(json.dumps(dict(ok=True, version='4.6.0', files=len(rows), deleted=len(deleted),
                         path=str(dest), sha256=hashlib.sha256(dest.read_bytes()).hexdigest())))


if __name__ == '__main__':
    main()
