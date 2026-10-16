# URP 集成验收记录 · 2026-10-15

**迷宫巡检、仓库五任务和 Fields2Cover 覆盖闭环均已实测通过，可从面板操作。** 唯一使用入口为 [setup/README](../../README.md)。保留现有研究源码、前端外壳、环境与官方仿真组件，补齐缺失集成，并处理了实测暴露的问题。范围是本机仿真研究平台；不包含实机或真实农业环境验证。学习原型已训练并独立留出评估，但未证明推荐增益；Fields2Cover 已完成限定范围的曲率几何与仿真验收。

## 工作台（2026-10-16）

面板改成多面板工作台：任务规划、算法实验、仿真、资料、系统五个工作区，面板可拖动、合并、拆分、浮动，⌘K 命令面板。主流程「一句话描述 → 生成地图 → 手动调整 → 推荐 → 多车分工与彩色路线 → 验算对比」逐步实测：

| 步骤 | 实测 | 截图 / 记录 |
|---|---|---|
| 描述任务 | 「在 240×160 米的猕猴桃园里，4 台机器人从西南角车库出发给 48 个点采样，每台最多装 12 个样本，避开一个池塘和一栋温室」输入时即解析成作业、场地、任务点、车队、容量、障碍、车库 | [flow-1](workbench/flow-1-describe.png)、[另一句](workbench/plan-compose.png) |
| 生成地图 | 4 块地、池塘、温室、48 个点、西南角车库；推荐 PyVRP 固定车队，至少 4 趟，聚集度 R=0.91 | [flow-2](workbench/flow-2-generated.png) |
| 多车路线与对比 | PyVRP 1 853.4 m、OR-Tools 1 904.4 m、节约 + 2-opt 1 943.8 m，均 4 车各 12 点；按车着色、方向箭头、访问序号、图例、同步回放 | [flow-3](workbench/flow-3-solved.png) |
| 验算 | 三个方案独立复算全部通过：每点恰好一次、每趟载重、车辆数、避障不出界、车库往返、里程复算一致 | [flow-4](workbench/flow-4-verify.png) |
| 手动调整 | 拖动任务点后结果标为过期并自动保存、画池塘、删点、⌘Enter 重算（39 点，PyVRP 1 021.7 m） | [plan-fleet](workbench/plan-fleet.png)、[验算](workbench/plan-fleet-verify.png) |
| 其他问题类 | CVRPLIB X-n101-k25：PyVRP 27 710，比 BKS 27 591 高 0.43%；Dubins 仓库：BIT* 31.35 m；爱沙尼亚真实田块 5：Fields2Cover 全流程 3 759.91 m | [CVRPLIB](workbench/plan-cvrplib.png)、[运动规划](workbench/plan-motion.png)、[覆盖](workbench/plan-coverage.png) |
| 算法实验 | X 集 4 例 × PyVRP / OR-Tools / 节约 × 2 种子共 17 次：PyVRP 平均差距 0.31% ± 0.41，OR-Tools 4.75% ± 1.14（节约算法超 100 客户的 3 例跳过）；性能剖面、差距分布、收敛曲线、LaTeX 表 | [课题](workbench/experiments.png)、[图表](workbench/experiments-charts.png) |
| 仿真 | 迷宫对角穿越 Theta* 11.85 m 送进 TurtleBot4：沿路径行驶成功，实际 11.77 m，横向偏差均值 0.016 m、最大 0.100 m，终点 0.105 m，仿真 55.4 s，会话 rc=0 关闭、无残留 | [e2e 记录](workbench/e2e-p2p-maze-cross/) |
| 其余工作区 | 资料（CVRPLIB 732 例、真实田块、文献、算法库与源码）、系统（服务、日志）、仿真 | [资料](workbench/library.png)、[系统](workbench/system.png)、[仿真](workbench/sim.png) |

### 多车方案在 Gazebo 田间世界里执行（ROS 2）

上表猕猴桃园任务的 PyVRP 方案（4 车 × 12 点）送进按任务地图生成的 Gazebo Fortress 世界：田块与作物行、池塘、温室、车库、按车辆着色的任务标记，每车一台差速机器人（官方 DiffDrive 系统），经一个 ros_gz 桥沿规划路线行驶、逐点到达。

| 指标 | 规划 | 执行（2× 与 5.9× 两次） |
|---|---|---|
| 到达任务 | 48 | 48 / 48，4 车全部回到车库 |
| 最晚完成时间 | 542.3 s | 552.7 s（+1.9%，两次一致） |
| 总里程 | 1 853.4 m | 1 858.3 m（+0.3%） |
| 横向偏差 | — | 均值 1.3–1.5 cm，最大 0.41–0.42 m（转角处） |

会话停止时 Gazebo、桥、Foxglove Bridge、Gazebo WebSocket 服务都在 SIGINT 后以 0 退出，`session-report.json` 为 PASS、无残留进程。浏览器里同时看到：ROS 视图（Foxglove Bridge → R3F，田块 / 规划路线 / 实际轨迹 / 任务 / 车辆）、Gazebo 场景（gzweb 直接渲染运行中的世界）、遥测（uPlot：各车速度、完成度、横向偏差）。证据：[世界、计划、结果、会话报告](workbench/fieldsim-4veh-48tasks/)。

同一句「5 公顷麦田分成 6 块，4 辆无人车巡检 60 个巡检点，要求尽快完成」：目标自动识别为尽快完成，推荐 OR-Tools；改用带车库卸载点和时间跨度代价的 OR-Tools 模型后，最晚完成 658.9 s，PyVRP 的最短里程方案为 745.5 s，各车负担的变异系数 0.101 对 0.189。

本轮实测中修掉的问题：

- 仿真修补库目录被清理后会话起不来 → 新增 `src/lab/ros/native/rebuild-ros-overlays.sh`，按原命令重建，产物与验收时逐字节一致（TF 1b530ae8…、GUI 49bd20b8…），`lab` 入口缺失时自动重建。
- 连续打开多个页面后请求全部挂起：每个页面的事件流各占一条连接，浏览器对同一主机只开 6 条 HTTP/1.1 连接。现在页面隐藏或进入往返缓存时关闭事件流，回到前台再连上并刷新。
- 地图在面板尺寸变化后不再重新适配 → 未手动平移缩放前随面板自动适配。
- 真实田块显示「无量纲」比例尺 → 实地坐标按米显示；统计图图例改用算法名、同一算法各图同色，时间轴按 ms / s 标注；课题矩阵显示场景与算法名称。

- 「尽快完成」目标下 OR-Tools 原先因多趟模式用了任务数个虚拟车而没有加时间跨度代价，结果与最短里程方案一样；现在按真实车数建模，允许回车库卸载，最小化最晚完成时间。
- gzweb 通过 WebSocket 取 OBJ 网格时把字节直接交给文本解析器，改为二进制 STL；Fortress 的 WebSocket 服务只发资源路径内的文件，会话把世界目录加进资源路径。
- 界面与日志不再带「URP」：应用名为「农业机器人路径规划工作台」，算法来源标为「本项目 / 基线 / 第三方库名」，ROS 话题改为 `/workbench/*`、`/ground_truth/poses`。

自动检查：Python 52 通过；前端 42 通过；类型检查与生产构建通过。

## 交付状态

| 部分 | 结论 |
|---|---|
| 场景 → 推荐 → 求解 → 独立检查 → 二维图 | 已通过前端及 API 实测；10 个可用算法适配，来源与保证分开标注 |
| URP 路径跟踪 / Nav2 逐点导航 | 两种模式分别实测，接驳、几何计划、重规划和实际轨迹分开记录 |
| 导出与回看 | JSON 包含当时输入、版本/源文件哈希、参数、原始结果、检查；仿真实验 JSON 同时嵌入规划结果 |
| ROS 生命周期与失败恢复 | 正常关闭、移动中取消、导航失败、必需服务退出、失败后重启、重复会话均实测 |
| Gazebo / RViz2 | 原生窗口实际启动，日志确认渲染/地图加载，随会话干净关闭；未通过原生截图工具独立验收像素外观 |
| 仓库/农业代理 | 完整官方世界、默认五任务长路线在 AMCL 下通过两种模式；仍只是静态行间通道代理 |
| 覆盖 / 学习推荐 / 历史 BPP | Fields2Cover 两种顺序可用、往复式实际覆盖通过；规则及限定范围学习原型可用；缺失 BPP 归档保持空数据 |

交付时面板在 `127.0.0.1:4100`，档案后端由网关管理，仿真已关闭。当前工作区仍为未提交成果，没有覆盖既有未提交改动或创建“最终版”分支。

## 扩展验收（在首轮核心闭环之后）

| 验收 | 实测结果 | 原始证据 |
|---|---|---|
| 仓库五任务 · AMCL 路径跟踪 | 5/5，计划 58.96 m，实际 59.460 m；最大偏差 0.3175 m，终点 0.0769 m，实际地图净空 0.760 m | [完整闭环](extended/api-loops/20261015T091612Z/report.json)、[跟踪](extended/api-loops/20261015T091612Z/sim-follow_path.json) |
| 仓库五任务 · Nav2 逐点导航 | 5/5，实际 51.223 m；相对原路线最大偏离 1.691 m；保存重规划，不称为严格执行原几何 | [导航](extended/api-loops/20261015T091612Z/sim-nav2_waypoints.json)、[双向距离补查](extended/warehouse-reverse-distance.json) |
| 前端 Fields2Cover 全流程 | 地头 0.6 m 的路径因足迹越界被拒绝；恢复 0.8 m 求解、比较、启动、执行、下载、关闭 | [实际下载](extended/ui-coverage-experiment.json)、[逐项核对](extended/ui-coverage-verification.json)、[完成截图](extended/ui-coverage-success.jpg)、[重启后回看](extended/ui-delivery.jpg)、[轨迹 CSV](extended/ui-coverage-trajectory.csv)、[对比截图](extended/ui-compare.jpg)、[CSV](extended/ui-compare.csv) |
| 实际覆盖与几何跟踪 | 5/5 路径段；内缩作业区 98.52%，全田块 57.84%；实际 27.747 m，最大偏差 0.0793 m，反向距离/终点误差 0.1040 m；足迹在田块内且地图检查通过 | [会话与清理](extended/sessions/sim_20261015T093550_c82812/session-report.json)，1904 个真值点；约 207 s，包括接驳用时 |
| 理想定位隔离模式 | 独立迷宫测试 2/2、最大偏差 0.209 m；确认 AMCL tf_broadcast=false、仅真值生成定位 TF；正常关闭 PASS | [完整报告](extended/api-loops/20261015T094608Z/report.json)（与 AMCL 验收分列） |
| 限定范围学习推荐 | 120 个不同实例、480 次真实求解，60/30/30 拆分；测试集全部选择固定 PyVRP，替代次数 0、平均改善 0% | [预定协议](extended/selector-study/protocol.json)、[逐实例原始结果](extended/selector-study/)、[独立评估](extended/selector-study/evaluation.json)、[审计及种子说明](extended/selector-study/audit.json)、[前端呈现](extended/ui-learned-evidence.jpg)、[真实下载](extended/ui-learned-solution.json) |
| 故障恢复复验 | 更新控制参数后 18 项再次通过；正常/故障退出均保留真实结果，失败清理与重启均无所属残留 | [结果](extended/api-loops/edge-cases-20261015T094147180059Z/edge-cases.json)、[日志](extended/edge-cases-final.log) |
| 最终自动检查 | Python 30 通过；前端 40 通过、2 个原有跳过；类型检查与生产构建通过 | [Python](extended/pytest-final.log)、[前端](extended/frontend-tests-final.log)、[锁定恢复及最终构建](extended/setup-locked-final.log)、[最终浏览器无错误/警告](extended/ui-console-final.json) |

仓库前几次失败原样保留：旧默认 AMCL 在长通道累计漂移；第一次参数适配误用了 launch 参数名；一次 Humble 不支持的 Python 客户端导入在控制 HTTP 启动前失败。定位 launch 使用 `params`，导航 launch 使用 `params_file`，现已分别适配，并通过 ROS 服务读取有效参数后才就绪。前端此后实际切换 CVRP 发现旧实例残留造成渲染错误，现按场景/历史记录隔离编辑状态，并对 JSON 结构做渲染保护；无效结构禁用求解，不能伪装成空场景。

核对已安装源码及 [PyVRP 0.14.0 官方实现](https://raw.githubusercontent.com/PyVRP/PyVRP/v0.14.0/pyvrp/solve.py) 后，将沿用的 HGS 显示名更正为 **ILS**。`pyvrp.hgs` 仍为兼容旧记录的 API 标识，实际运行的是 IteratedLocalSearch；旧结果不改写，审计文件明确纠正名称。

新的导航参数仅写入本会话目录，不修改 `/opt/ros`。AMCL 控制为默认：180 束、仿真低噪声里程计、0.06 m 控制器目标容差；覆盖用已安装 RPP，0.18 m lookahead，碰撞检测开启。验收阈值仍为 0.35 m，未通过放宽阈值制造成功。`ground_truth` 为显式理想定位隔离实验，不能混入 AMCL 结果。

Fields2Cover 复用已有 2.1.0 wheel，两个顺序分别调用真实原生 swath 排序与 Dubins 转弯，再由 Shapely 整段足迹及三点曲率独立检查。默认计划 27.742 m、最大采样曲率 3.333332 /m、内缩作业区几何覆盖 100%。支持单个凸内缩区，不支持未分解的凹形/孔洞；默认地头 0.8 m。规划覆盖只计直作业行，实际覆盖假设作业具沿整个跟踪轨迹持续开启，因此全田块比例不能直接与规划比例混作同一指标。最小转弯半径只约束规划几何；差速 TB4 可原地旋转，不证明农业车辆运动学可行。

学习原型复用原研究的特征与校准逻辑，但使用独立命名的本地实验。模型、归一化和固定算法只在训练集拟合，校准集只设门控，测试集只报告；篡改全部测试标签后模型与门控仍完全相同。预算为每算法 0.25 s、两次重复；PyVRP 种子 11/29，OR-Tools 不使用种子。研究分布为 [0,100] 均匀/聚簇合成数据，20/50/100 客户、容量 50、需求 1–10；现有面板基准与编辑输入可能有分布差异，模型界面明确外推未验证。**本次结果没有证明智能推荐相对固定 PyVRP 的收益，也没有证明普遍零风险。** 历史研究原始数据未恢复；新模型不冒充原研究结论。

两次完整网关启动/关闭由独立父进程直接 `waitpid` 记录，返回码均为 **0**，关闭后端口释放；此前执行工具外层终端曾返回 143，不能把外层状态当作网关真实码。[直接捕获记录](extended/gateway-lifecycle.json)、[可重复脚本](extended/check-gateway-lifecycle.py)。仿真会话的清理 PASS 与路线执行成功是两个不同状态；开发诊断中路线失败而清理正常的会话全部保留。

## 首轮核心验收结果

| 验收 | 实测结果 | 原始证据 |
|---|---|---|
| 最终前端全流程 | 真实点击场景、求解、启动、执行、下载、关闭；成本 490、到达 2/2；页面/网关/下载内容逐项相符 | [核对结果](acceptance/ui-verification.json)、[下载的完整实验](acceptance/ui-final-experiment.json)、[截图](acceptance/ui-final-success.jpg) |
| 四算法 API 闭环 | DP、独立原图 Oracle、PyVRP+分层、OR-Tools+分层：均为 490、检查通过；两种执行模式成功；总计 82.2 s，清理 PASS | [报告](acceptance/api-loops/20261015T080750Z/report.json)、[完整算法结果](acceptance/api-loops/20261015T080750Z/solutions.json)、[原始控制日志](acceptance/full-loop-final.log) |
| URP 跟踪误差 | API 闭环：均值 0.0598 m，最大 0.2201 m；最终 UI 独立再跑：最大 0.195 m，终点误差 0.206 m，257 个真值点 | [API 跟踪记录](acceptance/api-loops/20261015T080750Z/sim-follow_path.json)、[UI 核对](acceptance/ui-verification.json) |
| Nav2 逐点导航 | 2/2 到达；相对 URP 几何路径最大偏离 0.1077 m；保存 `/plan` 实际重规划输出，不宣称严格跟踪 | [导航记录](acceptance/api-loops/20261015T080750Z/sim-nav2_waypoints.json) |
| 故障与恢复 | 18 项断言通过：真实无解、精确求解超时、取消、工作进程异常、不安全路径拒绝、Nav2 不可达、取消/失败后再执行、必需服务终止与重启 | [结构化结果](acceptance/edge-cases.json)、[日志](acceptance/edge-cases.log)、[脚本](../../../src/lab/e2e/edge_cases.py) |
| 仓库短程 | 完整官方世界；节点 0→8→0，计划 4 m，任务 1/1，最大偏差 0.2954 m，正常关闭 rc=0 | [记录](acceptance/warehouse-smoke.json)、[原始日志](acceptance/warehouse-smoke.log) |
| 自动检查 | Python 23 通过；前端 38 通过、2 个原有跳过；TypeScript/Vite 构建通过；最终浏览器无控制台错误 | [pytest](acceptance/pytest-final.log)、[前端测试](acceptance/frontend-tests.log)、[构建](acceptance/build-final.log)、[浏览器](acceptance/ui-console-errors.json) |

首轮六个正常完整会话（独立初测、带窗口前端、故障后重启、四算法闭环、仓库短程、最终前端）均有 PASS 清理报告；另外保留三个 FAIL 会话，分别为修复前服务监控漏报、监控将一次性 spawner 误判退出的开发诊断、以及验收中主动终止规划服务。**这些失败未改写成成功，也没有从证据中删除。** 所有已结束会话的 `remaining_owned_processes` 均为空；各组件真实返回码、关闭信号与资源采样见 [会话目录](acceptance/sessions/)。正常 SIGINT 关闭允许相应子进程报告 -2/130，不能据此声称所有子进程均返回 0。

UI 正常结束后，「未运行」与禁用的关闭按钮见 [关闭截图](acceptance/ui-stopped.jpg)；无解显示空成本/未检查见 [无解截图](acceptance/ui-infeasible.jpg)；网关关闭后的断连与操作禁用见 [断连截图](acceptance/ui-disconnected.jpg)。

## 修复了什么

- 接手时没有仍在运行的 Claude/编译/仿真任务；两次 58 文件快照无变化，保留原有 Git 差异与未跟踪成果，[接手记录](acceptance/takeover-stability.json)。现有独立环境和契约在，但核心求解适配、推荐、导出、ROS 会话和两个主视图尚未形成可运行闭环。
- 接上既有转弯 DP/Oracle/原图检查器，适配已安装 PyVRP 0.14 的新 Route/Activity API，添加真实 OR-Tools 调用及独立重算；没有改写原研究求解源码。工作进程不再把非零退出或半截 JSON 当成功。
- 添加真实 ROS 会话，复用既有进程回收、TF 与 GUI 兼容代码。将闭合路径按原几何边交给 FollowPath，避免起终点相同被控制器立即判到达。
- 修复取消终态过早缓存，保证停止观察和指标完成后才持久化；启动恢复会从会话最终文件补齐数据库。修复求解取消与创建子进程的竞争窗口。
- 实测发现 planner_server 收到 SIGTERM 后会正常 rc=0 退出，而 launch 仍存活。现在将必需子节点提前退出及 Nav2 心跳故障视为会话故障；create/spawner 一次性正常退出除外。失败后清理、再次启动与执行已验证。
- 面板恢复历史实验的输入快照；明确规则推荐、算法来源、不可用模块、未检查/无解/失败/断连；仿真结果直接显示本次实际模式，避免下拉选项切换后误读历史执行。
- 整体 API 关闭不再伪造 SIGINT；`lab-stop` 经实测使网关以 0 退出，组件失败仍保留在清理报告与真实返回码中。正常 Ctrl+C 仍遵循中断返回码语义。

## 地图、资源与研究口径

- 物理坐标为 **map 米**，官方配对世界按 `world = map` 使用，没有把 benchmark 无量纲数值直接映射为米。整数转弯成本为路径厘米数 + 厘米当量惩罚；默认路线 4.30 m，对应成本 430+60=490。第三方求解优化整数代理成本，检查器重新计算并记录真实定义的成本。
- 机器人按 0.175 m 圆足迹 + 0.05 m 安全余量验证。未知区/地图外视为障碍，检查每条线段，保守扣减栅格和采样误差；不是仅检查节点。
- 有限段扫描核验：maze 620/640 有效回波端点全部距配对地图障碍 ≤0.15 m，warehouse 466 个有效端点也全部满足。激光安装 TF 纳入计算，没有调整世界坐标以追求通过。[迷宫记录](acceptance/maze-map-consistency.json)、[仓库记录](acceptance/warehouse-map-consistency.json)、[原始扫描](acceptance/warehouse-scan.json)。仅覆盖已测静止姿态及短程路线，不证明整幅地图/所有碰撞网格完全等价。桥接真值头时间为 0，轨迹使用最新仿真时钟，未宣称硬同步。
- [资源清单](acceptance/world-assets.json) 按模型 owner/name 去重：warehouse **9** 个 Fuel 模型、depot **1** 个，当前缓存 **12** 个模型版本。之前“12/13”混合了缓存数、原始 URI 数及 mesh 文件引用，不能当成验收数量。缺失的 Casual female 模型已经从官方 Fuel 补齐，[下载日志](acceptance/fuel-missing-model.log)。
- 活动依赖检查覆盖 SDF、网格、DAE/OBJ 材质及 PBR 贴图，并保存哈希。Classic material scripts 对 Fortress 不适用，逐项保存在 `inactive_classic_materials`；Table 的实际 PBR 贴图已核验。依据 [Gazebo Fortress 官方功能说明](https://gazebosim.org/docs/fortress/comparison/)。没有删除障碍或改动官方世界来通过检查。
- 跟踪成功要求任务按序进入 0.35 m 半径、各段终点误差和实际最大横向偏差均 ≤0.35 m。扩展验收又加入计划到实际的反向最大距离 ≤0.35 m，避免跳过部分计划仍判成功；覆盖实际作业区比例须 ≥90%、足迹留在田块内。控制器容差会使实际长度小于计划长度；不等于逐点精确重放。Nav2 逐点导航仅验收任务顺序/到达，并单独记录偏离原路线的程度。
- 访问任务、几何跟踪和覆盖率是不同指标。覆盖基线只评价内缩作业区域、允许原地转向，不满足 Dubins 最小转弯半径；路线完成不代表全田块覆盖。架构的场景/求解/检查与 ROS 会话分开；当前执行适配器为 TB4，更换机器人需相应足迹与控制器适配。

## 桥接退出：保留临时缓解，根因未解决

[原始计数复核](acceptance/bridge-evidence-audit.json) 与 [恢复的原始日志](bridge-exit/recovered-raw-logs/) 对应：

| 条件 | 批次 | 单个 parameter_bridge 退出数 | 异常 |
|---|---:|---:|---:|
| baseline-a | 8 | 160 | 7 ABRT |
| trace-a | 8 | 160 | 3 ABRT + 1 SEGV |
| trace-b | 12 | 240 | 9 ABRT |
| guard-a | 20 | 400 | 0 |

因此是未加垫片 **560 次单进程退出中 20 次异常**、加垫片 **400 次未观察到异常**，不是 560/400 个完整 TB4 会话。它们是此前压力测试的原始证据，本轮未重复宣称重新跑过同样规模。

`src/lab/ros/native/bridge_exit_guard.c` 只作用于指定 parameter_bridge 可执行文件，在真实 main 返回后 flush C 标准流并调用 `_exit(main返回码)`。加载前验证源码、二进制构建清单及目标链接库指纹；不替换系统库。新的完整 TB4 会话确认了命令转发、clock/TF/scan/odom/真值、到达、取消、失败恢复和反复关闭。

**free() 检测位置不是内存破坏起源；退出绕过不是根因修复。** `_exit` 跳过析构/atexit，不能声称那些退出钩子或其日志已验证；已捕获 stdout/stderr 原样保留，非零码、强杀和残留不吞掉。`URP_BRIDGE_FIX=0` 可关闭受控对比；桥接根因追查仍是独立未完成事项。TF/GUI 保护也只在已验证指纹的本次子进程内生效。

## 尚未完成与已知限制

- 学习原型样本小、算法组合窄，独立测试未观察到优于固定 PyVRP 的收益；跨分布、跨预算与跨机器的泛化未验证。
- Fields2Cover 限定为单个凸作业区；已有 wheel 和 native 二进制均锁定哈希，但原 C++ 构建命令/源码提交未恢复，未宣称从源码逐位重建。缺失或不匹配时可回退 Shapely 基线。
- 默认仓库五任务和指定 depot 田块已通过；不同机器人、所有通道/田块、动态障碍、长期稳定性和大规模跨场景评估未验收，仓库代理不是农业实证。
- depot 五个端点扫描中，首姿态有 27/507 个远处回波与地图障碍距离 >0.15 m，主要位于作业矩形外 y≈5.7–7.1 m；4 m 内局部回波 p95 ≤0.08 m。[原始比较](extended/depot-map-consistency.json)。没有修改地图或移除障碍来通过；局部路线通过不证明整个世界地图等价，远处差异根因仍待进一步核验。
- 原生 GUI 日志仍有上游 HMI/QML/图形警告，未发现本轮窗口异常退出；不将“窗口启动”当成视觉质量保证。
- 测试使用现有环境，Starlette 对其 httpx TestClient 有弃用警告；未为消除警告擅自升级依赖。墙钟截止启发式即使固定种子，也不保证不同机器/负载逐位相同。

## 复验与证据保存

先按唯一使用说明启动面板，然后在根目录运行（每个脚本拥有独立的会话，勿同时执行）：

```bash
src/lab/.venv/bin/python src/lab/e2e/full_loop.py --scenario maze-inspection --algorithms urp.turn_mode_dp,urp.raw_oracle,pyvrp.hgs+urp.layered,ortools.gls+urp.layered --modes follow_path,nav2_waypoints --budget 240
src/lab/.venv/bin/python src/lab/e2e/edge_cases.py
src/lab/.venv/bin/python src/lab/e2e/full_loop.py --scenario farm-rows-warehouse --algorithms urp.turn_mode_dp --modes follow_path,nav2_waypoints --budget 900
src/lab/.venv/bin/python src/lab/e2e/full_loop.py --scenario field-coverage-depot --algorithms f2c.boustrophedon --modes follow_path --budget 600
```

`edge_cases.py` 会明确终止它自行启动、且带匹配 URP 归属标记的 planner_server，以验证故障处理；不会关闭未知 ROS 任务。复验脚本将新结果写入 `src/lab/runtime/e2e/<带时间戳目录>/`，不覆盖本次 acceptance 证据。首次失败的原始记录也在 acceptance 中，包括修复前监控遗漏、spawner 误判和测试输入重复节点被正确拒绝的诊断。无解、超时与取消是预期结果，不计为成功求解。

[环境及锁文件哈希](acceptance/environment.json)、[ROS 包版本](acceptance/ros-versions.txt)、[证据 SHA256 索引](acceptance/manifest-sha256.json)、[机器可读汇总](acceptance/summary.json)。求解原始请求/stdout/stderr 位于 [solver-processes](acceptance/solver-processes/)，每次会话原始启动日志、资源清单、执行数据和清理报告位于 [sessions](acceptance/sessions/)。现场完整数据库仍保留在 `src/lab/runtime/`，没有用测试桩或人工数据冒充实验成果。

扩展证据：[环境/锁文件](extended/environment.json)、[SHA256 索引](extended/manifest-sha256.json)、[机器可读汇总](extended/summary.json)、[会话原始日志](extended/sessions/)。旧 acceptance 证据保持原样；不以新结果覆盖旧失败。
