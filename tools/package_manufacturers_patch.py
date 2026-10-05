"""Package only the three manufacturer runtime files for the eight-tier upgrade."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FOLDER = 'shadows_of_france_unification'
PAYLOAD = ['common/ideas/sof_regional_manufacturers.txt',
           'common/military_industrial_organization/organizations/sof_regional_manufacturers.txt',
           'localisation/simp_chinese/replace/sof_regional_manufacturers_l_simp_chinese.yml']


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, default=ROOT/'dist')
    args = parser.parse_args()
    design = json.loads((ROOT/'design/regional-manufacturers.json').read_text(encoding='utf-8'))
    version = design['version']
    assert version == '4.3.2' and design['tier_count'] == 8
    files = {}; rows = []
    compatibility = json.loads((ROOT/'design/manufacturer-upgrade-compatibility.json').read_text(encoding='utf-8'))
    for rel in PAYLOAD:
        raw = (ROOT/'mod'/rel).read_bytes()
        name = FOLDER+'/'+rel
        files[name] = raw
        rows.append(dict(path=name, bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
                         previous_sha256=compatibility['baseline_payload_sha256'][rel],
                         compatible_sha256=compatibility['approved_payload_sha256'].get(rel, [])))
    manifest = dict(format=1, kind='regional-manufacturers', version=version, folder=FOLDER,
        name='法兰西之影：统一战争（独立中文版）', required_versions=['4.3.0','4.3.1','4.3.2'],
        files=rows, game_engine_verified=False)
    files['manufacturer-manifest.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2)+'\n').encode('utf-8')
    files['install-manufacturers.ps1'] = (ROOT/'tools/install_manufacturers_patch.ps1').read_bytes()
    files['README-ZH.md'] = ('# 4.3.2 制造商八层成长\n\n'
        '需要已安装4.3.0或4.3.1的地区制造商。保存并关闭HOI4，解压后运行 '
        '`powershell -ExecutionPolicy Bypass -File ./install-manufacturers.ps1`。\n\n'
        '20家制造商各有8层、两条成长线、16项特质。强化起始与成长加成，保留旧组织及四个旧特质ID。'
        '只覆盖组织、传统设计商和中文本地化三份文件，更新描述文件版本；其他人物、历史、国策、地图和美术保留。'
        '先核验已安装内容、生成可校验备份，遇到同名文件额外修改则停止覆盖。引擎实机验收待完成。\n').encode('utf-8')
    args.output.mkdir(parents=True, exist_ok=True)
    output = args.output/f'shadows-of-france-manufacturers-{version}.zip'
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED,compresslevel=6) as archive:
        for name,raw in files.items():
            archive.writestr(name,raw)
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        for row in rows:
            assert hashlib.sha256(archive.read(row['path'])).hexdigest() == row['sha256']
    print(json.dumps(dict(ok=True, version=version, payload_files=3, bytes=output.stat().st_size,
                         sha256=hashlib.sha256(output.read_bytes()).hexdigest(), path=str(output))))


if __name__ == '__main__':
    main()
