"""A bounded 4.2 -> 4.3 upgrade that preserves separately edited leaders/history."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = 'shadows_of_france_unification'
BASE_FILES = ['common/national_focus/sofzh_paris.txt', 'common/national_focus/sofzh_corsica.txt',
              'common/ideas/sof_vanilla_major.txt']


def payload_paths():
    design = json.loads((ROOT / 'design/regional-manufacturers.json').read_text(encoding='utf-8'))
    files = BASE_FILES + ['common/ideas/sof_regional_manufacturers.txt',
        'common/military_industrial_organization/organizations/sof_regional_manufacturers.txt',
        'common/scripted_effects/sof_balance_430.txt', 'common/scripted_triggers/sof_balance_430.txt',
        'common/on_actions/sof_balance_430.txt', 'interface/sof_regional_manufacturers.gfx',
        'localisation/simp_chinese/replace/sof_balance_430_l_simp_chinese.yml',
        'localisation/simp_chinese/replace/sof_regional_manufacturers_l_simp_chinese.yml']
    return files + [a['destination'].removeprefix('mod/') for a in design['native_art_assets']]


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', type=Path, default=ROOT / 'dist')
    args = parser.parse_args(); version = (ROOT / 'VERSION').read_text().strip()
    assert version == '4.3.0'
    plan = json.loads((ROOT / 'design/balance-4.3.json').read_text(encoding='utf-8'))
    paths = payload_paths(); assert len(paths) == len(set(paths)) == 34
    files = {FOLDER + '/' + path: (ROOT / 'mod' / path).read_bytes() for path in paths}
    rows = []
    for name, raw in sorted(files.items()):
        row = dict(path=name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
        rel = name.removeprefix(FOLDER + '/')
        if rel in BASE_FILES:
            row['previous_sha256'] = plan['changed_files']['mod/' + rel]['before_sha256']
        rows.append(row)
    manifest = dict(format=1, kind='regional-balance', version=version, folder=FOLDER,
                    name='法兰西之影：统一战争（独立中文版）', required_versions=['4.2.0', '4.3.0'],
                    files=rows, game_engine_verified=False)
    files['gameplay-manifest.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode('utf-8')
    files['install-gameplay.ps1'] = (ROOT / 'tools/install_gameplay_patch.ps1').read_bytes()
    files['README-ZH.md'] = ('# 4.3.0 地区工业与国策平衡补丁\n\n'
        '需独立版4.2.0。保存并关闭游戏，解压后运行 '
        '`powershell -ExecutionPolicy Bypass -File ./install-gameplay.ps1`。\n\n'
        '仅更新两国国策、移植精神、新增地区制造商与平衡脚本和本地化，保留本地人物、历史、地图、473幅图标以及创意工坊ID。'
        '覆盖前生成备份，并拒绝覆盖已有额外修改的同名文件。\n\n'
        '28对兼容国策解除互斥；28项精神字段与科研奖励收束；20家地区企业使用原生军工组织，缺少AAT时进入传统设计商对应槽。'
        '旧存档按已完成国策一次性调整4个变量差额，既有科研槽与内阁保留。实机加载与长期平衡待验收。\n').encode('utf-8')
    args.output.mkdir(parents=True, exist_ok=True); output = args.output / f'shadows-of-france-gameplay-{version}.zip'
    with zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, raw in files.items(): archive.writestr(name, raw)
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        for row in rows: assert hashlib.sha256(archive.read(row['path'])).hexdigest() == row['sha256']
    print(json.dumps(dict(ok=True, version=version, path=str(output), payload_files=len(rows),
                         bytes=output.stat().st_size, sha256=hashlib.sha256(output.read_bytes()).hexdigest())))


if __name__ == '__main__':
    main()
