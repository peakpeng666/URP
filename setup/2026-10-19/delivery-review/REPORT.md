# 版本更新与测试结果

日期：2026-10-19  
基线提交：`23fafe4f02fe25fb48a3091a449e3bcd595037e8`

## 更新内容

- 整理项目入口，分别列出主基线、第三方补充实验和交接验收。
- Lab 增加运行库互斥锁、执行依赖指纹和默认 worker 环境检查。源码或依赖变化时，任务返回错误并清除可行性标签。
- 学习推荐按预算和距离目标检查适用范围，范围外采用规则推荐。
- 转弯精确求解器明确拒绝暂不支持的有限车队上限；无上限问题保持原有行为。
- 支持通过 `URP_ROS_MAPS` 指定官方地图副本。
- 分别说明协作者镜像和旧平台快照的内容。旧 Release 的 Fuel 缓存附件保持原样。

## 测试结果

| 检查 | 结果 | 记录 |
|---|---|---|
| 完整工程检查，串行运行 | 15/15 通过，含后端、研究组件、独立检查、前端类型检查、测试和生产构建 | [工程汇总](engineering/summary.json) |
| Lab 全量测试 | 353 passed、4 skipped、0 failed | [完整日志](logs/lab-final.log) |
| 真实田形补充测试 | 恢复 Fields2Benchmark 数据后，单独补跑 1 项，通过 | [测试日志](logs/real-field-readback-test.log) |
| 执行身份与互斥故障测试 | 8 项通过 | [核查摘要](summary.json) |

全量测试中跳过的 4 项包含上述真实田形测试，其余 3 项依赖可选 Fields2Cover 编译扩展，尚未运行。

运行环境为云端 Linux x86_64、Python 3.12.14、Node 24.19.0、npm 11.9.0。根目录与 Lab 分别使用各自锁文件安装依赖。原主机使用 Python 3.12.13。云端未安装 ROS/Gazebo 和 Fields2Cover 编译扩展；Starlette 与 Shapely 的弃用警告保留在日志中。

## 测试记录

首次工程检查为 14/15。PyVRP 的 1 秒端到端用例在时限内未产生 checkpoint；原有 12 项 JobTests 单独重跑全部通过，最终串行工程检查为 15/15。算法、时限和断言保持不变。

首次 Lab 测试为 323 passed、25 failed、4 skipped。其中 24 项缺少官方 `maze.yaml`，另 1 项因同一资源缺失返回 `invalid_world`。从现有 Release 的 `ros-gazebo-installed.tar.zst` 提取三个场景的 6 个 YAML/PGM 文件，并按已发布的 `files.jsonl.zst` 核对 SHA256，见 [地图文件清单](map-assets.json)。仅提取地图，未执行包内软件。

补齐地图后为 352 passed、1 failed、4 skipped。剩余生命周期用例模拟 ROS 就绪和子进程退出码 7，但预检仍依赖系统 world 文件。测试中补充了预检参数，使其进入目标子进程；生产 world 校验保持不变。

并行回归中，一项正常 TERM 退出用例因发出 SIGKILL 而失败。相同 27 项监督测试单独运行通过，最终串行工程检查通过。监督器和断言未变，失败日志保留；该用例需继续关注运行时序。

复审修正了三项问题：数据库符号链接别名绕过锁、默认 worker 与网关环境不一致、来源变化后仍保留可行性标签。同一虚拟环境的 python/python3 别名可正常使用；自定义 worker 的环境标记为未经核验。

## 适用范围

本次验证覆盖代码、数值求解、地图检查和前端构建。ROS/Gazebo 会话、覆盖完整路线修复后的仿真执行、容器 warehouse、原生 GUI、GPU 和实际农机效果需分别测试。

执行指纹在检查时点记录依赖状态，部署使用固定源码目录与独立运行库。它不提供不可变文件系统快照或恶意代码隔离。

原始 `data`、`protocol` 和 `experiments/results` 保持不变。选择器 120 例的胜平负由已有记录重新统计，见 [读回结果](selector-readback.json)。模型、实验参考值、预算和失败判据均未调整。
