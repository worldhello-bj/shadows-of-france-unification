# 两国国策图标重绘

48幅原稿使用内置imagegen逐幅生成。统一采用1930年代战略游戏的金属徽章、金色月桂、暗色主体与透明背景；经济、军种、政治和地区身份按主题区分。同主题国策共用对应图案。巴黎与科西嘉各有专属徽章，人物政策使用本地机构或路线符号。

`source/` 为未修改的生成PNG。`exports/` 为96、64、32像素PNG；实际DDS位于 `mod/gfx/interface/sof_focus/`。导出仅进行等比缩小、居中和透明留白，不重绘原稿。`review/CONTACT-96.png` 显示96像素原尺寸。

完整提示词、内置工具来源和原稿SHA256见 `design/focus-art-spec.json`；所有游戏绑定见 `design/focus-art-bindings.json`。`tools/focus_art.py` 负责技术导出与绑定，`tools/validate_focus_art.py` 检查尺寸、透明边缘、引用和美术更新前后的玩法结构。

```powershell
python tools/focus_art.py
python tools/validate.py
python tools/preview_vanilla_remake.py
```

本轮覆盖巴黎、科西嘉保留的473项国策、103项移植精神、5个修正模块及7项新增政策决议和对应分类。通用国家的国策美术继续沿用既有版本。预览与源码验证尚不能替代游戏内悬停、发光与界面缩放验收。
