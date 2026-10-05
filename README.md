# 法兰西之影：统一战争

《钢铁雄心 IV》独立中文模组的协作源码。当前候选版本 **4.1.0**，适配游戏 **1.19.***。巴黎直接移植原版法国的185项国策；科西嘉以原版意大利314项为底稿，删除26项无法迁移的内战与教皇分支后保留288项。两国国策采用48幅新绘制的本地主题徽章，并加入40位历史内阁、12项实际领袖任命及精神生命周期修复；其他国家继续使用原有153项通用国策。永久小幅地形经验、通用内战决议GUI和生成美术继续保留。

[查看两国布局预览](docs/previews/4.1.0/INDEX.html) · [历史内阁画像与数值](docs/previews/4.1.0/HISTORICAL.html) · [重制范围与适配说明](docs/VANILLA-REMAKE-ZH.md) · [重绘图标原尺寸预览](art/focus/review/CONTACT-96.png)

![内战界面设计预览](docs/previews/GUI-READY-CONTEXT.png)

## 开始开发

需要Git与Python 3.12以上。检查与打包不需要游戏安装；实机验收需要本地HOI4。

```powershell
git clone https://github.com/anothercoder-code/shadows-of-france-unification.git
cd shadows-of-france-unification
python -m pip install -r requirements.txt
python tools/validate.py --output dist/validation.json
python tools/package.py
```

`dist/shadows-of-france-4.1.0.zip` 是独立候选安装包。解压后运行其中的 `install.ps1`；安装器会先备份原有独立版文件，再核验安装哈希，并保留已有创意工坊ID和封面。更新安装前应保存并关闭游戏。启用“法兰西之影：统一战争（独立中文版）”即可。

## 编辑入口

| 路径 | 用途 |
|---|---|
| `mod/` | 游戏实际加载的完整源码与纹理，是协作修改的主入口 |
| `mod/common/national_focus/sofzh_paris.txt`、`sofzh_corsica.txt` | 两棵原版大国国策移植 |
| `mod/common/national_focus/SoF_generic.txt` | 其他国家使用的原有通用树，文件内容未修改 |
| `mod/common/national_focus/sof20_*.txt`、`*_legacy.txt` | 停用的历史树，仅保留脚本引用与旧档迁移兼容 |
| `mod/common/decisions/` | 内战、占领治理和各国地方协作决议 |
| `mod/interface/sof_civilwar.gui` | 通用内战面板的原生布局 |
| `mod/common/scripted_guis/sof_civilwar_gui.txt` | 数据绑定、动态旗帜列表及刷新操作 |
| `mod/gfx/interface/sof_civilwar/` | 背景、衬板、32像素决议图标及52×40分类徽章 |
| `art/civilwar/` | 12张美术原稿、PNG尺寸导出及完整生成提示词 |
| `art/focus/` | 48幅重绘国策原稿、96/64/32像素导出及原尺寸预览 |
| `design/focus-art-spec.json`、`focus-art-bindings.json` | 完整生成提示词、原稿哈希和逐项图标绑定 |
| `design/vanilla-major-remake.json` | 两国原版节点对照、奖励适配、原文与来源哈希 |
| `design/country-design.json` | 3.x历史设计数据；已不决定4.0的国策选择 |
| `references/vanilla/` | 本机1.19.3原版底稿，供对照与重建 |
| `tools/` | 可移植的检查、纹理导出与打包脚本 |
| `docs/` | GUI规范、协作约定、历史检查报告和预览 |

## 当前版本行为

- 六类地形经验为永久修正，同类只授予一次，统一后保留。数值见[GUI设计说明](docs/CIVILWAR-DESIGN-ZH.md)。
- 内战面板适用于法国首都、独立且未投降的国家；显示当前阶段、稳定度、完整控制的法国地区数、邻接势力及经验状态。
- 11种透明图标覆盖132条决议和21个分类。正文使用原版中文字体，内容区510×500像素。
- 边境战役仍需25政治点数、45天冷却及扩张授权。美术更新不改变现有决议费用、条件、奖励或AI。

## 协作与验证

从 `main` 建立功能分支，提交后开Pull Request。按[CONTRIBUTING.md](CONTRIBUTING.md)记录修改、检查结果与实机范围。GitHub Actions在推送和PR时执行源码／美术检查并打包候选产物；流程依据[GitHub官方Python工作流文档](https://docs.github.com/en/actions/tutorials/build-and-test-code/python)。

4.1.0已通过源码、原版结构对照、54组原有迁移模拟、40位内阁的锁定与替换、12项领袖旧档补发、战役精神结束及科研阵营同步检查；记录在 `docs/reports/4.1.0/`。**GUI实机显示、两个剧本开局、真实旧档迁移及长期平衡仍待验证。** 预览为实际源码排版图，不是游戏截图。历史报告保留在对应版本目录。
