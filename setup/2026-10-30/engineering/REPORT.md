# URP 工程基线整合 · 2026-10-30

[PR #15（已合并）](https://github.com/peakpeng666/URP/pull/15) · [使用与开发](../../README.md) · [29 个分支处置](../../../docs/branches.csv) · [资产索引](../../../docs/assets/README.md)

工程基线以 main `5ddbd22` 为基础，整合 Agent、工作台与离线 evolve。第一轮生产代码验证于 `b2f79af`，入口与 CI 验证于 `cf96ed9`；第一轮最终提交为 `aab3b42`。下面先记录在同一 PR 继续推进的第二轮结果。

## 第二轮 refresh：入口与数据契约

基线为已合并 PR #18 的 `d3f0c03a`（tree `34aff046caa8c41815bf6b9e10535700bc329f46`）。本批修改统计、Agent、启动、交付检查、导出和当前导航；冻结研究记录与原始资产不变。

- 分析以完整比较身份合并场景别名；推断资格依据实际完整比较块的来源分组。未知独立单位保留描述统计并说明所缺声明，不生成显著性结论。
- 条件质量曲线列出有效轨迹、终态成功率、逐时刻观测分母与排除原因；首次遥测前未知，不补值。实例空间按任务特征 schema、预算、目标与版本分面，面板与图表导出采用同一合同。
- Agent 复用场景类型，保留参数枚举与随机性元数据；Study 依实际种子支持展开，界面计数和 Agent 分析摘要同步。
- 启动与状态诊断共用解释器解析；`lab` / `lab-code` 每次构建前端。镜像 PR 检查覆盖所有提交，双服务回归包含坏解释器、真实任务、导出、停止重启及端口释放；显式 Lab-only 模式单独解释健康状态。
- 原几何 CSV 保持兼容，新增任务/趟次 CSV。资产恢复联合视图按内容验证为 Space 4、Drive 0；未将缺失路径推断为迁移事件。

最终稳定源码验证（2026-10-30 20:01 UTC）：

| 检查 | 结果 | 云端原始记录 |
|---|---|---|
| Lab 全量，含固定地图 | **968 passed、11 skipped、36 subtests passed** | `.local-state/refresh2/lab-full.log` |
| 前端全量、类型、生产构建 | **716 passed**；类型与构建通过 | `.local-state/refresh2/frontend-{full,typecheck,build}.log` |
| 工程门禁 | **15/15 passed**，438 个 Python 用例 | `.local-state/refresh2/engineering/summary.json` |
| 双服务 HTTP、启动失败注入、真实任务与生命周期 | **passed** | `.local-state/refresh2/dual-service-final/summary.json` |
| 当前入口本地链接 | **131 个路径通过** | `.local-state/refresh2/doc-links.json` |

独立审查的完整块过度禁用、历史摘要地图语义误合并、非法 incumbent 轨迹与旧图表消费者问题均已加反例修复。并发修改期间一次 Agent 扩大回归触发源码身份保护，该失败日志保留；稳定源码全量回归通过，未绕过保护。

此次双服务使用新运行库；云端未检出原 `data/backend/research.sqlite3`，清单记录为缺失，不声称已验证该文件哈希。浏览器、ROS 和容器未在本机重跑；容器验证由本批 PR 工作流执行。测试中的模型为脚本或 mock，本批没有科研实验或真实模型调用。

## 全量整理与错误处理修订

以已合并的 `8885ef6` 为基线，统一当前入口、31 分支快照、16 模块职责、五项交付、研究地图和资产核验队列。PR #12、#13 的改动已由 #15 整合，旧 PR 已关闭，来源分支保留。

- Lab：模型响应按契约解析；空结果不记成功；显式 null 参数与非法道路宽度报错；种子 0 原样使用；几何与 RNG 初始化错误直接暴露。
- 场景生成：保留请求，卡片显示实际数量，未满足项以 partial 状态及摘要列出。
- 求解轨迹：读取失败的 makespan 样本单独记账，不用代理目标替代；有效解保持。
- 前端：修复跨场景、会话与研究课题的迟到响应覆盖；显式呈现轮询及部分加载错误；提交锁按场景代次隔离。
- 档案与验算：非法求解器结果仅终止对应尝试；审计输入和终态一致性明确校验；审计输出采用新文件，避免覆盖历史。

验证：Lab **932 passed / 11 skipped / 36 subtests passed**；前端 **709 passed**、类型检查及生产构建通过；工程 **15/15**，其中 Python 用例 **422**；当前文档 **116** 个本地链接路径通过。HTTP 端到端完成生成、推荐、PyVRP 与节约法求解、独立验算、导出和比较。模型、原始实验和冻结研究定义保持不变。

保留的失败记录：第一轮 Lab 915 项通过；扩展修订后一次 931 通过、1 项模块行数门禁失败，随后将 makespan 遥测提取到 `fleet_trace.py`，门禁不变，最终全量通过。浏览器检查在 Chromium 启动阶段被进程 socket 权限阻塞；标准权限提升路径又被执行环境只读目录阻塞，没有完成视觉检查。原日志保存在 `.local-state/refresh/`。

资产核验覆盖 2,439 项路径和 Git blob；外部恢复验证及大文件迁移均为 0。根许可证与具体分发范围见 [资产处理队列](../../../docs/assets/rights-review.md)。

## 第二轮收尾

开始时远端与本地均为 `aab3b42`，工作区干净，没有并行提交。重新核对 29 个来源分支的 SHA，均与分支表一致。

- 修复取消时迟到的最终答复或接口错误覆盖 `canceled` 状态；请求尝试计入模型调用次数。
- 关闭网关会结束运行中及等待批准的轮次，取消旧批准，迟到结果不再写入已关闭的数据库；重启读取状态不自动请求模型。
- 继续会话时记录模型配置变化；接口错误摘要剔除已知密钥。新增配置后只读访问的反例测试，确认没有模型请求。
- 系统提示升级为 `urp.agent.system/2`，直述结果与依据，取消固定“局限”模板。旧会话保留原提示快照。
- 修正 DEPLOY 的失效章节链接、前后端 README 和后续计划中的旧入口，补齐实际停止语义。
- 资产索引读取副本登记，重新生成不会把未恢复副本当作已验证，也不会丢掉已验证副本字段；来源 Git blob 不匹配时拒绝登记。

| 本轮检查 | 结果 | 记录 |
|---|---|---|
| 全量 Lab，含 21 项 Agent 测试 | **868 通过、11 跳过**，36 个 subtests 通过 | [lab-round2.log](lab-round2.log) |
| 工程门禁、类型检查、前端与生产构建 | **15/15 通过**；410 个 Python 用例、690 个前端用例 | [engineering-round2.json](engineering-round2.json) |
| Agent 浏览器，脚本模型 | **15/15 通过** | [browser-round2.json](browser-round2.json) |
| 副本登记、源版本与元数据验证测试 | **3/3 通过**，已包含在工程门禁 | `tools/tests/test_index_assets.py` |

修复前新增反例为 5 失败、1 通过，见 [agent-before-round2.log](agent-before-round2.log)。浏览器首次发生 `Target crashed`，独立复跑通过；[首次日志](browser-crash-round2.log)保留，未将原因归为已证实的代码或资源问题。当前提交的远端检查见 [PR #15](https://github.com/peakpeng666/URP/pull/15)。

资产核验的实际结果：私有 Drive 文件夹可读写，已上传一份 826 字节的基线 JSON，并确认文件大小、父目录与原权限；已登记五份既有候选。下载既有私有 papers ZIP 到云端时，代理返回 `URLError: Tunnel connection failed: 403 Forbidden`，未完成内容恢复验证。因此 **已验证大文件迁移 0、移出跟踪 0**。具体文件 ID、状态、错误与逐类方案见 [副本登记](../../../docs/assets/copies.json)和[资产说明](../../../docs/assets/README.md)。

本轮不发起真实收费模型请求或物理仿真长跑。测试中的模型为脚本、回环服务和 `MockTransport`。

## 第一轮整合记录

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
