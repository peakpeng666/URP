# URP 工程基线整合 · 2026-10-30

[草稿 PR #15](https://github.com/peakpeng666/URP/pull/15) · [使用与开发](../../README.md) · [29 个分支处置](../../../docs/branches.csv) · [资产索引](../../../docs/assets/README.md)

工程基线以 main `5ddbd22` 为基础，整合 Agent、工作台与离线 evolve。生产代码验证于 `b2f79af`；入口、依赖与 CI 验证于 `cf96ed9`。后续提交补充本报告与测试记录。

## 整合结果

| 来源 | 纳入内容 | 处理依据 |
|---|---|---|
| main | 算法、独立验算、统计、执行身份、ROS/Gazebo 管理 | 保留新版实现及其回归 |
| Agent 分支 `85a7048`（#14） | 模型接口、17 个工具、会话、批准、前端面板和换行归一 | 保留三个原提交，组合测试与浏览器复核 |
| evolve `d36a7b3`、`9b020d0`（#12/#13） | 30 个离线模块、候选准入、审计、修复、动态实验及模型读取检查 | 逐提交整合，合并地图测试与数据隔离 fixture |
| workbench `c9c4bc6`、导入 `e7a6170` | 编辑器选择、校验、草稿、农业预览、幂等导入、结果追踪与图表 | 选择功能补丁；保留 main 的统计字段、执行检查与 Agent |
| editor / agriculture / results / verify 保全分支 | 独有工作由较新的 workbench 实现覆盖 | 逐分支记录 SHA 与处置，旧快照继续保留 |
| local、snapshot、paper | 研究模型、结果、失败与论文计划 | 索引原提交；已提取有效离线模块，研究结论按原版本保留 |

各分支的完整依据、与 main 的提交差异计数见 `docs/branches.csv`。算法 ID 和历史数据格式保持兼容。`analysis.py`、`jobs.py`、执行时钟和求解器继续使用 main 的实现。

## 工程整理

- 根 `requirements.lock` 从 `uv.lock` 导出，CI 核对一致性。前端与浏览器工具共 92 个下载地址统一为 npm 官方源，版本和 integrity 不变；历史实验锁文件按原环境保留。
- 新增 `lab-code` 启动入口、固定提交与 SHA256 校验的官方地图下载、真实 HTTP 小任务和源码检出清单。
- 必需地图缺失会失败；真正可选的地图用例明确跳过。进程失败、取消和普通导入测试改用不依赖 ROS 资产的数值场景。
- 相同 ID 的导入重试比较完整归一化内容，坐标系、单位、图层和来源变化均返回冲突；网关拒绝与档案后端同端口造成的自代理循环。
- 新研究 CLI 目录定点忽略，冻结实验继续跟踪。移除工作台快照中的旧 PID / 构建现场说明。
- CI 收拢为全量 Lab、工程、部署、Windows 四组；原有非理想模型、执行、Agent 和 evolve 回归进入全量 Lab。保留各原生与镜像专用工作流。
- 重写 README 和统一使用入口，建立 75 个外部源码目录的许可证据表与逐文件资料索引。核对 2439 个索引资产，Git blob 均与整理前一致。

## 本轮验证

环境：Linux、Python 3.12.14、Node 24.19.0；浏览器为 Chromium 151。以下均为本轮执行：

| 检查 | 结果 | 记录 |
|---|---|---|
| Lab 全量，固定官方地图，`--require-maps` | **858 通过，11 跳过**，36 个 subtests 通过 | [lab.log](lab.log) |
| 前端类型检查、Vitest、生产构建 | **690 通过**，类型与构建通过 | [frontend.log](frontend.log)、[工程汇总](engineering.json) |
| `tools/check_project.py` | **15/15 通过**，407 个 Python 用例 | [engineering.json](engineering.json) |
| Agent 浏览器流程，回环脚本模型 | **15/15 通过**，11 次模型请求，0 个协议错误 | [agent-browser.json](agent-browser.json) |
| 实际 HTTP 生成、推荐、求解、验算、导出、比较和关闭 | **通过**；PyVRP 与 savings 均完成且独立检查有效 | [http-smoke.json](http-smoke.json) |
| GitHub 全新稀疏源码检出，按文档安装启动 | **通过**；HTTP 流程与单例 CVRP 完成，运行前后 Git 均干净 | [clean-checkout.json](clean-checkout.json) |
| 必需地图缺失的反向检查 | **按预期失败**，退出码 1 | [required-map-negative.log](required-map-negative.log) |
| GitHub CI，提交 `cf96ed9` | **6/6 作业通过**，含 Windows、原生适配器与容器构建/服务验证 | [ci.json](ci.json) |

11 项跳过涉及可选 Fields2Cover、本机田块缓存及尚无输入的审计结果。地图依赖用例已在实际官方文件上运行。部署合约本地运行 50 项、跳过 1 项；安装器本地运行 40 项、跳过 5 项。Windows 启动与引用合约另由 GitHub Windows 作业通过。

修复前的失败记录保留：Agent 基线无地图时 **736 通过、17 失败、7 跳过**，见 [原始日志](lab-missing-maps-before.log)；后续一次组合回归暴露进程 fixture 在 exec 完成前检查身份的竞态，见 [失败日志](lab-process-race-before.log)，现已等待子进程就绪。首次工程检查漏取 BPP 的 NPZ，修正检出清单后 15 道检查全部通过。

## 接续入口

日常开发从 [setup/README.md](../../README.md) 开始。前端、Agent、求解、验算、记录与离线 evolve 在同一工程内继续推进。

真实大模型质量和 ROS/Gazebo 物理执行本轮未重跑。大文件尚未迁移，根 LICENSE 尚未代选；逐项文件、许可证文本和迁移步骤见资产索引。既有实验和失败记录保留原版本。
