"""Package only the exclusive focus icons and their two bindings."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = 'shadows_of_france_unification'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    args = parser.parse_args()
    version = (ROOT / 'VERSION').read_text().strip()
    assert version == '4.2.0'
    art = json.loads((ROOT / 'design/unique-focus-art.json').read_text(encoding='utf-8'))
    paths = ['interface/sof_focus_unique.gfx', 'common/national_focus/sofzh_paris.txt',
             'common/national_focus/sofzh_corsica.txt']
    paths += ['gfx/interface/sof_focus_unique/' + a['key'] + '.dds' for a in art['assets']]
    assert len(paths) == len(set(paths)) == 476
    files = {FOLDER + '/' + p: (ROOT / 'mod' / p).read_bytes() for p in paths}
    rows = []
    for name, data in sorted(files.items()):
        row = dict(path=name, bytes=len(data), sha256=sha(data))
        key = 'mod/' + name.removeprefix(FOLDER + '/')
        if key in art['semantic_baseline']['file_sha256']:
            row['previous_sha256'] = art['semantic_baseline']['file_sha256'][key]
        rows.append(row)
    manifest = dict(format=1, kind='exclusive-focus-art', version=version, folder=FOLDER,
                    name='法兰西之影：统一战争（独立中文版）',
                    required_versions=['4.1.0', '4.2.0'], game_engine_verified=False,
                    baseline_commit=art['semantic_baseline']['source_commit'], files=rows)
    files['focus-art-manifest.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    files['install-focus-icons.ps1'] = (ROOT / 'tools/install_focus_art_patch.ps1').read_bytes()
    files['README-ZH.md'] = (
        '# 4.2.0 独占国策图标补丁\n\n'
        '需已安装独立版4.1.0。保存并关闭HOI4后，在解压目录运行 '
        '`powershell -ExecutionPolicy Bypass -File ./install-focus-icons.ps1`。\n\n'
        '仅更新巴黎与科西嘉的两份国策图标绑定、473张DDS、一个GFX注册文件及描述文件的版本号。'
        '人物、历史、其他国策、决议和数值均保留。国策文件若有另外的改动，安装器会停止。'
        '覆盖前在HOI4用户目录的mod-backups下生成备份，备份内记录新建文件以便回退。\n\n'
        '473项国策使用473幅不同插画：118幅新生成、47幅已有独立生成稿、308幅原版筛选插画。'
        '已核验来源和96像素内容去重；引擎实机显示仍待验收。\n'
    ).encode('utf-8')
    args.output.mkdir(parents=True, exist_ok=True)
    path = args.output / f'shadows-of-france-focus-icons-{version}.zip'
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
    with zipfile.ZipFile(path) as archive:
        assert archive.testzip() is None
        for row in rows:
            assert sha(archive.read(row['path'])) == row['sha256']
    print(json.dumps(dict(ok=True, version=version, path=str(path), bytes=path.stat().st_size,
                         payload_files=len(rows), sha256=sha(path.read_bytes())), ensure_ascii=False))


if __name__ == '__main__':
    main()
