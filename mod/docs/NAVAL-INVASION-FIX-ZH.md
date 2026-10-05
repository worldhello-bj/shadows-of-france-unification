# 登陆作战上限修复 · 2.12.1

模组的运输科技仍使用旧版 naval_invasion_capacity。当前游戏将登陆能力拆成同时可规划的计划数 naval_invasion_plan_cap 和每个计划的师数 naval_invasion_division_cap，因此研究旧运输科技仍会停在默认的一个计划。

本修复逐项采用本机1.19游戏运输科技的两种上限及固定准备天数加成，保留旧计数器供引擎和AI兼容使用。没有运输科技时，基础上限仍为一个计划、每个计划四个师。

| 已研究的运输科技（累积） | 无 Man the Guns：计划数 / 每计划师数 | Man the Guns：计划数 / 每计划师数 |
| --- | --- | --- |
| 运输船 | 3 / 6 | 2 / 6 |
| 登陆艇 | 5 / 8 | 5 / 10 |
| 坦克登陆艇 | 9 / 16 | 9 / 15 |

通用、巴黎和科西嘉登陆精神、旧海军陆战队学说及登陆军官团的11处师数加成改用每计划师数上限，奖励数值保留。其他科技、精神和国策内容保留。

更新后完全退出并重新启动游戏，再载入存档；已研究运输科技的ID保留。本补丁不编辑或覆盖存档。未研究运输科技时显示一个计划属于正常规则。需要运输船、实际海上控制及准备时间才能执行登陆。

结构检查、两种DLC路线、全部六项科技与11处奖励、整包SHA-256已核对。实际游戏界面数值以实机验证记录为准。

机制来源：[官方海军开发日志](https://store.steampowered.com/news/posts/?appids=394360&enddate=1750939447&feed=steam_community_announcements)，实际数值取自本机游戏 common/technologies/naval.txt、MTG_naval_Support.txt 和 common/defines/00_defines.lua。
