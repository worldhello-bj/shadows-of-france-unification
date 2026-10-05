# 协作约定

`mod/` 为当前可运行的来源，直接修改对应游戏脚本；`design/` 保存设计意图，修改国策配额或玩法方向时同步更新。`art/civilwar/source/` 为美术原稿，换图后运行 `python tools/export_art.py` 导出纹理，再检查小尺寸辨识度。

## 提交顺序

1. 从 `main` 建立分支，例如 `feat/lil-industry`、`fix/civilwar-scroll`、`art/occupation-icons`。
2. 修改脚本和对应中文文本；保持国家TAG、国策ID及事件ID稳定。
3. 运行 `python tools/validate.py`；发布或涉及安装包时再运行 `python tools/package.py`。
4. 检查实际游戏效果并记录游戏版本、剧本、国家、新档／旧档、界面比例和结果。未测试项目如实写明。
5. 推送分支并开PR，描述触发条件、改后行为和验证证据。

## 文件格式

- 本地化 `.yml` 使用UTF-8 BOM。游戏脚本和已有资源按原字节保存，避免整目录格式化。
- `.gitattributes` 禁止Git自动改写游戏数据的换行，Python、Markdown与工作流使用LF。
- 原图、DDS与地图在普通Git中跟踪；当前最大文件小于GitHub单文件100MiB限制。新增大文件前检查体积。
- `dist/`、存档、引擎日志、本机安装回执、回滚备份与缓存不提交。
- 不直接在Steam创意工坊下载目录中协作修改。使用本仓库构建包安装到自己的HOI4用户目录。

## 验收边界

4.0自动检查包括两国与原版的节点结构对照、通用树保持原样、历史树停用、奖励与中文引用、决议美术、GUI只读刷新及54组开局／旧树迁移模拟。CI需获取完整Git历史与v3.2.0标签。检查不启动游戏，也不证明真实存档兼容、战斗数值或长期AI行为。历史报告注明其检查范围；修改后应生成新的本地检查结果。

## 发布

同步修改根目录 `VERSION` 和 `mod/descriptor.mod` 的版本号，更新 `CHANGELOG.md`，执行打包并检查安装。源仓库不保存本机 `remote_file_id`；安装器可保留已有创意工坊发布身份。GitHub提交与Steam创意工坊上传是独立步骤。
