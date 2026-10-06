"""Build the 120-file overlay for pristine GitHub main 4.5.0 (80c4582)."""
from pathlib import Path
import hashlib,json,shutil,zipfile
from build_brittany_focus import ROOT,MOD,REPORT


def main():
    validation=json.loads((REPORT/'validation.json').read_text(encoding='utf-8'))
    art=json.loads((REPORT/'art-verification.json').read_text(encoding='utf-8'))
    assert validation['ok'] and art['ok']
    spec=json.loads((ROOT/'design/brittany-focus.json').read_text(encoding='utf-8'))
    package=ROOT/'dist/brittany-github-package';package.mkdir(parents=True,exist_ok=True)
    rows=[]
    for rel in spec['files']:
        src=MOD/rel;raw=src.read_bytes();out=package/'files'/rel
        out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(raw)
        before=ROOT/'references/brittany-github-base/mod'/rel
        rows.append(dict(path=rel,sha256=hashlib.sha256(raw).hexdigest(),before_sha256=hashlib.sha256(before.read_bytes()).hexdigest() if before.exists() else None))
    manifest=dict(format=1,kind='brittany-focus-overlay',base_version='4.5.0',base_commit='80c4582',validated=True,checks=validation['checks'],scenarios=validation['scenarios'],focuses=174,delegates=6,reserves=6,home_events=21,files=rows,game_engine_verified=False)
    (package/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    shutil.copy2(ROOT/'tools/install_brittany_focus.py',package/'install.py')
    (package/'README-ZH.md').write_text('布列塔尼议会：174项国策、100席议会、两条军事路线及专属美术。\n\n只用于 GitHub main 4.5.0（80c4582）的独立版。保存并关闭游戏后解压，在此目录执行：\n\n```powershell\npython install.py --target "你的文档目录/Paradox Interactive/Hearts of Iron IV/mod/shadows_of_france_unification"\n```\n\n安装前核验120个文件的基线或目标哈希，拒绝覆盖并发修改。自动生成可恢复备份并保留其他运行文件及模组描述。已经安装本补丁可重复运行。不能直接用于本地4.6.0，后者有单独的分层安装回执。\n\n已完成脚本、素材和安装夹具检查；原生引擎、真实旧档迁移和长期平衡尚未实测。\n',encoding='utf-8')
    archive=ROOT/'dist/brittany-github-4.5-overlay.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for p in package.rglob('*'):
            if p.is_file() and 'backups' not in p.parts and p.name!='install-receipt.json':z.write(p,p.relative_to(package).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        assert all(hashlib.sha256(z.read('files/'+r['path'])).hexdigest()==r['sha256'] for r in rows)
    report=dict(ok=True,archive=archive.relative_to(ROOT).as_posix(),sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),bytes=archive.stat().st_size,files=len(rows),base_commit='80c4582',base_version='4.5.0',game_engine_verified=False)
    (REPORT/'github-package.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report))


if __name__=='__main__':main()
