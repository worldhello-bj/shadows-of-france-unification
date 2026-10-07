"""Package only the display patch; preserve the installed gameplay version."""
from pathlib import Path
import hashlib,json,zipfile
from build_ideology_panel import ROOT,MOD,PASS
from validate_ideology_panel import audit


def main():
    if (ROOT/'design/focus-integration-4.6.json').is_file():
        from package_focus_integration import main as package_integration
        return package_integration()
    errors=[];audit(lambda ok,message:errors.append(message) if not ok else None)
    assert not errors,errors
    data=json.loads((ROOT/'design/ideology-panel.json').read_text(encoding='utf-8'))
    folder='shadows_of_france_unification'
    files={folder+'/'+p:(MOD/p).read_bytes() for p in data['files']}
    manifest=dict(format=1,kind='ideology-panel',profiles=12,folder=folder,name='法兰西之影：统一战争（独立中文版）',
                  display_only=True,game_engine_verified=False,minimum_version='4.3.3',files=[])
    for name,raw in sorted(files.items()):
        rel=name[len(folder)+1:]
        manifest['files'].append(dict(path=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),previous_sha256=data['source_before'].get(rel)))
    files['ideology-panel-manifest.json']=(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n').encode('utf-8')
    files['install-ideology-panel.ps1']=(ROOT/'tools/install_ideology_panel.ps1').read_bytes()
    files['README-ZH.md']=('''# 十二种细分意识形态面板

适用于4.3.3及以上独立版。关闭游戏，解压后运行 `powershell -ExecutionPolicy Bypass -File ./install-ideology-panel.ps1`。

政治面板用12种不同颜色显示现有细分路线，列出一位小数的百分比、路线说明和执政标记。支持率按各党当前领袖路线映射；没有党派采用的路线显示0%，不虚构同一党内的派系票数。每天自动刷新；暂停时可点政治光谱旁的刷新按钮。

只安装13个界面、显示缓存和纹理文件。保留当前版本、国策、人物、政体判定、党派支持率与已有加成。写入前备份并检查原文件；有额外改动时停止。安装和静态检查不能证明实机显示。

分段饼图技术参考并感谢 Yard1 的 [HoI4-Scripted-GUI-Pie-Chart](https://github.com/Yard1/HoI4-Scripted-GUI-Pie-Chart)。本补丁的纹理、数据适配和布局为当前项目生成。
''').encode('utf-8')
    stage=ROOT/'dist/ideology-panel-patch';stage.mkdir(parents=True,exist_ok=True)
    for name,raw in files.items():
        path=stage/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(raw)
    output=ROOT/'dist/shadows-of-france-ideology-panel.zip'
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as archive:
        for name,raw in files.items():archive.writestr(name,raw)
    with zipfile.ZipFile(output) as archive:
        assert archive.testzip() is None
        for row in manifest['files']:assert hashlib.sha256(archive.read(row['path'])).hexdigest()==row['sha256']
    receipt=dict(ok=True,path=str(output),stage=str(stage),payload_files=13,profiles=12,bytes=output.stat().st_size,sha256=hashlib.sha256(output.read_bytes()).hexdigest())
    (PASS/'package-receipt.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(receipt,ensure_ascii=False))


if __name__=='__main__':main()
