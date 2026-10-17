# URP 集成验收记录

唯一使用入口为 [setup/README](../../README.md)。本报告按日期保留验收范围与原始证据；最新结论在最上方，历史通过不自动覆盖之后的模型或代码。迷宫巡检、仓库五任务、Fields2Cover 的限定闭环及 CVRP 学习原型评估见下方历史记录，不等于新车队功能、推荐增益或真实农业环境已验证。

## GLM 增量独立验收（2026-10-17，当前）

**结论：基础田间闭环复验通过，新增能力不予整体通过。** 基线 `056b857c302b7a04775336630c317bf84eda0ae7`，接手时工作区干净；本轮只增加独立验收证据、前端交接提示词并修正文档，未修改应用源码。354 个后端/前端源码和配置文件的起始指纹见 [takeover.json](../../2026-10-17/glm-acceptance/takeover.json)，最终核对见 [结构化汇总](../../2026-10-17/glm-acceptance/summary.json)。正式 4100 网关保持运行；仿真测试使用隔离存储、端口和 ROS 域，不覆盖用户实验。

| 独立复验 | 结果与证据 |
|---|---|
| Python 回归 | **226 passed**，3 条已有弃用警告；[原始日志](../../2026-10-17/glm-acceptance/pytest.log) |
| 前端检查 | 类型检查、42 项 UI 测试、Vite 隔离构建通过；仍有大 chunk 和静态/动态重复导入警告。[typecheck](../../2026-10-17/glm-acceptance/typecheck.log)、[测试](../../2026-10-17/glm-acceptance/frontend-tests.log)、[构建](../../2026-10-17/glm-acceptance/build.log) |
| 自由通行，2 车 8 点 | succeeded/0，8/8，实际 216.45 m、253.24 s，最大横向偏差 0.1178 m，清理 PASS、所属残留为空 |
| 行间通行，2 车 8 点 | succeeded/0，8/8，实际 369.88 m、428.01 s，最大横向偏差 0.1278 m，清理 PASS、所属残留为空 |
| 取消、时钟故障、故障后重启 | 分别 canceled/0、failed/1、succeeded/0，故障被看门狗明确记录；3 场清理均 PASS、所属残留为空。以上 5 场的[汇总](../../2026-10-17/glm-acceptance/live/summary.json)、[原始日志](../../2026-10-17/glm-acceptance/live.log)、[会话文件](../../2026-10-17/glm-acceptance/live/runtime/fieldsim/) |
| 开环物理对照 | 当前默认轮胎接触与 sphere 对照各 1 场，真实 Gazebo、正常退出、清理 PASS；[原始结果](../../2026-10-17/glm-acceptance/physics/summary.json)、[日志](../../2026-10-17/glm-acceptance/physics.log) |
| 浏览器与导出核对 | 实际打开已有实验、回放/结果界面并点击下载，确认状态文案和导出问题；[宽窗口截图](../../2026-10-17/glm-acceptance/ui-desktop.png)、[窄窗口截图](../../2026-10-17/glm-acceptance/ui-result-state.png)、[DOM](../../2026-10-17/glm-acceptance/ui-result-state.txt)。本轮没有从浏览器新建并跑完整实验；新增 5 场闭环由隔离验收脚本执行，不能替代 KIMI 的最终浏览器全流程验收。 |

本轮检查范围内有 **8 项后端/契约问题、5 项前端对接问题**；它们是当前版本的缺口，不把每项都归因于某个作者。完整定位、复现性质与修复要求见 [findings.json](../../2026-10-17/glm-acceptance/findings.json)。

| 编号/优先级 | 问题及实证 | 验收要求 |
|---|---|---|
| B1 / P1 | `fleet_engines.py:195` 提取错补给边界；ORTools 原解工期 **133.3 s**，解码路线改为趟间返库、最后绕行补给点，变成 **203.933067 s**，仍 feasible/check.valid。`fleet.py:685` 的 reload_stops 还误用了遗留变量。见 [原解与输出](../../2026-10-17/glm-acceptance/unload-free.json)。 | 原始节点映射、补给顺序、解码路径与目标一致；测试须真正使用补给点，不能以全返库代替。 |
| B2 / P1 | `fleet.py:132` 的 rows 图按 depot→unload→task 排列，求解器按 depot→task→unload 解释；合法 8 点实例所有作业位置错配并 no_solution。[复现](../../2026-10-17/glm-acceptance/unload-rows.json)。 | 统一节点映射，复验 rows/free × 单/多库 × 有/无补给。 |
| B3 / P1 | `fleet_curvature.py:13` 把共线反向也判作无穷大半径：Rmin=2 m、前进 1 m 后原线折返，0.05 m 采样，检查仍通过。[反例](../../2026-10-17/glm-acceptance/curvature-reversal.json)。 | 航向连续性、倒车语义、退化段与 SE(2) 路径证据独立检查；三点圆拟合不足以证明前进 Dubins 可行。 |
| B4 / P1 | `field_dynamics.py:33` 用缺口两端位姿相同豁免采样缺失；t=0/10/20 s 三个位姿、轮速 1 m/s，仍 valid。[反例](../../2026-10-17/glm-acceptance/telemetry-gap.json)。 | 超阈值未知区间应拒绝或有覆盖全区间的独立静止证据。此为离线检查边界反例，本轮真实成功会话最大源采样间隔约 0.02 s，未据此声称真实会话缺流。 |
| B5 / P2 | `field_energy.py:48` 按全程样本数选滤波窗。同一约 5 m 运动添加 0/120/600 s 静止尾段，能耗 **97.6458/87.9613/66.1946 J**，最后下降 **32.2%**；峰值功率也改变。[复现汇总](../../2026-10-17/glm-acceptance/reproductions.json)。 | 固定物理时间尺度，验证停车尾段/采样率不变性；当前不可用于可靠能效排序。 |
| B6 / P2 | 容量 1/10 两车、需求 1/10 两任务有可行分配，但校验要求小车也能装最大任务，整体拒绝。 | 按每任务可服务车型集合检查；不要将小车“不服务大任务”误写成“不能服务任何任务”。 |
| B7 / P2 | 异构输入仍默认比较 `panel.cluster_first`，三种构造基线 applicable=true，求解端却明确不支持。[接口复现](../../2026-10-17/glm-acceptance/frontend-contract.json)。 | 推荐、默认选择、提交准入统一；前端临时过滤须有原因及可移除条件。 |
| B8 / P2 | 默认 API 是 rigid/4，使用说明原为球面 v3；`model_contract` 仍写多库 makespan 不支持、仅返库补给。 | 本轮已修正使用说明与历史标题；后端输出契约和其他旧接口文案仍需统一，不改写历史原始记录。 |
| F1 / P1 | 车库编辑仅改 `depot`，后端按未变的 `depots[0]` 恢复旧坐标。[往返复现](../../2026-10-17/glm-acceptance/frontend-contract.json)。 | 统一编辑模型、兼容别名和保存后归一化回写，浏览器保存/重开验证。 |
| F2 / P1 | 实际 signature 函数对 service_s、第二车库、补给点、走廊、fleet 类别的变化均不变。[五类反例](../../2026-10-17/glm-acceptance/frontend-signature.json)。 | 完整规划输入稳定指纹，当前草稿与历史输入明确分开。 |
| F3 / P1 | 当前结果有串行交通与接触检查，页面仍固定写“屏蔽车间碰撞/未验收”。 | 按每个结果显示，未知与零不同，串行基线与并行避碰不同。 |
| F4 / P1 | 实际按钮下载 [schema /1](../../2026-10-17/glm-acceptance/ui-export.json)，无 integrity；[服务端 /2](../../2026-10-17/glm-acceptance/server-record.json) 完整记录 SHA256 独立复算一致。 | 下载服务端完整 envelope，保留全部会话与关闭报告；散列不是身份签名。 |
| F5 / P2 | 619 px 窗口里按钮 x=717，页面无可达横向滚动；1440×900 同按钮正常下载。 | 宽/中/窄三档窗口均能完成核心操作。 |

**物理结论的边界**：v4 默认是轮胎接触刚体模型，仍使用理想关节速度伺服与真值定位。此次轮胎开环原地转向 2.68710 rad，解析参考 2.32 rad，偏差 **0.36710 rad / 15.82%**；组合运动末端轮式里程计漂移 **1.57769 m**。sphere 对照分别为 **0.001756 rad / 0.003084 m**。两者的 `reference_conformance=true` 使用不同门槛：轮胎采用经验滑移 ≤20%，sphere 采用理想滚动误差 ≤0.15 rad。**门槛变化不证明轮胎真实度更高或接触根因已修复**，也不能将本轮各 1 次对照说成重复统计验证。自由通行实际任务两车末端轮式里程计偏差为 **11.534/6.500 m**，真值控制仍能跟踪；跟踪成功不能替代定位/轮胎模型验证。已有 GLM 敏感性及 holdout 原始报告保留，本轮未重跑其全部样本。能耗为后验代理且有 B5；没有实测轮胎/土壤校准、电池或环内力矩模型。

**可复验命令**：在 `src/lab` 使用现有 `.venv/bin/python`；输出目录必须是新的绝对路径，两个脚本顺序运行：

```bash
.venv/bin/python e2e/field_backend.py --out /一个新的绝对路径/field --cases free,rows,cancel,clock_stall,restart
.venv/bin/python e2e/physics_backend.py --out /一个新的绝对路径/physics --cases step4ms,sphere_legacy --repeats 1
```

后端最小反例脚本为 [reproduce_findings.py](../../2026-10-17/glm-acceptance/reproduce_findings.py)，前端指纹/往返探针与全部日志一并保存在该目录。三个探针均要求 `--out /新的绝对目录`，拒绝覆盖既有目录；Python 探针使用项目 `.venv/bin/python`，JS 探针使用 `node`。修复应先用这些反例证明失败，再验证真实流程，不通过修改证据或放宽门槛获得“通过”。KIMI 的完整任务提示词见 [前端交接任务](../../2026-10-17/KIMI-前端任务提示词.md)：优先 F1–F4，随后新增字段、科研状态与窄窗口；B1–B7 修复前相关能力保留限制和解释。应用源码本轮未修复，TB4/AMCL、Fuel 依赖及桥接压力试验本轮未重新执行，仍以各自历史证据为限。

## 建模与物理后端验证（2026-10-17，早期 v3 验收）

本轮只修改后端、验证工具和既有文档；接手时的 **224 个前端文件未变**。默认田间执行现在使用 `urp.field-diffdrive.rigid/3`，完整输入、参数、解析参考、源时间轨迹与实际物理库哈希随结果保存。统一入口仍为 [setup/README](../../README.md)，证据集中于 [modeling](../../2026-10-17/modeling/)，总索引为 [summary.json](../../2026-10-17/modeling/summary.json)。

**修正了模型与证据之间的实质缺口：**

- 旧的真值反馈能把路线追踪好，却掩盖轮式运动学误差。独立开环试验发现圆柱轮版本在 0.8 rad/s、3 s 转向中比解析参考多转 **0.2826 rad（约 12.2%）**；24 s 组合运动后轮式里程计末端偏差 **1.2343 m**。减小步长到 2 / 1 ms 仍有相似偏差；改 Bullet 接触又引入制动误差。保留全部[旧模型数据](../../2026-10-17/modeling/response-pilot2/)、[步长对照](../../2026-10-17/modeling/timestep-diagnosis/)、[检测器对照](../../2026-10-17/modeling/contact-detector-diagnosis/)。
- 新模型沿用[已安装版本的官方差速示例](https://github.com/gazebosim/gz-sim/blob/ignition-gazebo6_6.18.0/examples/worlds/diff_drive.sdf)的球面滚动接触抽象，显示、碰撞、惯量和规划足迹同步更新；车体仍为 0.8×0.56×0.22 m，含轮总宽 0.96 m，外接圆仍为 0.4882623 m。没有拟合轮距或追踪增益消除误差。**这是替换不符合目标运动学的模型近似，不是宣称修复了 DART 的所有轮胎接触问题。** 新模型依然是合成的理想差速平台。
- 使用每车 PosePublisher 的源仿真时间，替代零头时间的世界动态姿态话题。新田间会话拒绝零时间戳；以 50 Hz 目标频率保存完整 3D 姿态，独立检查采样缺口和二维轨迹一致性。轮式里程计只对齐首个共同姿态，不全轨迹拟合；姿态越出平地有效域就停车并留证。TB4 的旧记录时间口径不因此改变。
- 冻结质量、惯量、摩擦、步长、驱动上限和假设，先独立检查生成 SDF，再核对所属进程实际库映射与碰撞检测/约束求解器日志。库版本及 SHA256 保留，实际实现不符就拒绝就绪；日志使用行缓冲，避免等到退出才出现选择信息。默认 DART 5.4.0 接口 / DART 6.12.1 动力学、ODE 接触、Dantzig 求解。
- 规划结果增加显式模型契约：同构车队、抽象容量、瞬时返库卸载、通道停车访问代理、匀速时间代理和 LPT 启发式；未证最优。另给逐顶点停止、原地转弯、加速的解析时间参考，明确不是追踪器工期预测或上下界。推荐仍是规则建议，删除未经本项目证实的“2 秒内距 BKS 约 1%”“路线不交叉”“最快”等承诺。

| 验证 | 实测结果与原始证据 |
|---|---|
| 开环与敏感性 | 24 个真实 Gazebo 会话，每设置重复 3 次：primary 含 4/2/1 ms、+20 kg 和低摩擦；holdout 用更高直行速度、反向转弯与不同圆弧。**21 个正常/载荷试验全部通过**预定直行 0.15 m、制动 0.10 m、转向 0.15 rad 误差门槛；实际最大分别 **0.0385 m / 0.00483 m / 0.0111 rad**，组合运动末端里程计偏差最大 **0.00549 m**。[primary](../../2026-10-17/modeling/model-v3-primary/)、[独立协议](../../2026-10-17/modeling/model-v3-holdout-final/)、[CSV](../../2026-10-17/modeling/analysis/trials.csv) |
| 低摩擦负结果 | μ=0.05 的 3 次试验均明显偏离无滑移参考，末端里程计偏差约 **3.63 m**，明确记录 reference_conformance=false；不将它们计入 21 次通过。不包含真实土壤校准。[对比图](../../2026-10-17/modeling/analysis/physics-verification.png)、[分析及输入哈希](../../2026-10-17/modeling/analysis/summary.json) |
| 验证工具负对照 | 最终工具另跑旧圆柱轮和新模型 +20 kg 各 1 场：旧模型仍未通过转向参考，新模型通过；两场执行协议完成且清理 PASS。汇总只将适用的标称/载荷试验纳入通过判据，仅选择敏感性工况时返回 null。此 2 场不并入上面 24 场研究计数。[原始结果与汇总](../../2026-10-17/modeling/harness-final-check/) |
| 后端回归 | **178 passed**，3 条既有依赖弃用警告；包含配置漂移、惯量、完整足迹、真实进程和故障状态。后续推荐口径修改又运行现有相关 6 项，全部通过。[完整日志](../../2026-10-17/modeling/pytest-final.log)、[推荐复核](../../2026-10-17/modeling/pytest-recommendation.log) |
| 完整集成 | 8 场得到预期结果：自由、实体行间、取消、时钟停滞、桥接退出、真实车间接触、重启、网页桥/RViz 开关。成功场的源时间、实际库、轨迹、接触、停留和停车检查通过；取消为 canceled/0，故障为 failed/1；全部关闭 PASS、无所属残留。行间 2 车 8 点 **369.86 m / 429.18 s**。[逐场汇总](../../2026-10-17/modeling/integrated-final/summary.json)、[原始运行](../../2026-10-17/modeling/integrated-final/runtime/fieldsim/) |
| 正式页面闭环 | 页面重新比较 3 算法，将 PyVRP 行间方案交给新版后端，**8/8，298.38 m / 343.37 s，最大横向偏差 0.0969 m**。下载 JSON 与 API 指标一致，完整记录哈希一致，页面关闭 rc=0 / PASS，无残留；两车末端里程计偏差约 9.0 / 1.0 mm。[截图](../../2026-10-17/modeling/ui-completed.png)、[下载](../../2026-10-17/modeling/ui-browser-result.json)、[完整服务端记录](../../2026-10-17/modeling/ui-final-record.json)、[核验](../../2026-10-17/modeling/ui-verification.json)、[原始日志](../../2026-10-17/modeling/ui-runtime/) |

首轮种子参数不受 Fortress 支持、测试夹具缺字段，以及运行时核验遇到库别名/日志缓冲的启动失败都保留在同一证据目录，未改判成功。现在拒绝伪造 physics seed，实际库名按 Gazebo ABI 别名解析，必需选择日志未出现时等待明确期限后报错。各验证批次有源码快照；本轮未升级系统 Python、驱动、ROS 或依赖。

页面控制台本次采集为 0 条 error、2 条既有 Three.js 警告（重复导入及 Clock 弃用），保留[原文](../../2026-10-17/modeling/ui-console.json)，没有因后端验收通过而宣称前端零警告。最终证据的文件 SHA256 索引见 [manifest.json](../../2026-10-17/modeling/manifest.json)；持续运行的网关日志另行标注，不纳入不可变文件散列。

这些是**小规模、固定输入重复的仿真验证与敏感性试验**，图中误差条是观察范围，不是置信区间，也不是论文级算法优越性结论。尚未实现有限宽真实轮胎、可变形土壤/坡地、传感器噪声与状态估计、力矩/能耗模型、随任务变化的载荷、农业作业具可达性与作业质量；当前质量载荷均匀加在箱体且执行器为理想速度伺服。路线执行成功不能替代这些验证。模型接口保留扩展空间，未将库限定为该车型。

目录仅归集本轮证据并刷新[只读盘点](../../2026-10-17/modeling/folder-audit.json)，旧失败、用户研究数据、环境与未提交前端成果均保留；[224 文件指纹](../../2026-10-17/modeling/frontend-unchanged.json)。

## 后端持续优化（2026-10-17，前一轮记录）

仅改后端、测试和现有文档。接手快照中的 **224 个前端文件全部未变**，保留 Claude 未提交成果。唯一启动/停止/恢复入口仍是 [setup/README](../../README.md)，本轮证据统一在 [2026-10-17/backend](../../2026-10-17/backend/)，索引为 [summary.json](../../2026-10-17/backend/summary.json)。系统 Python、ROS 安装及既有求解环境均未替换。

已完成：

- 车型引用在求解提交时冻结，执行前核对版本、文件哈希和元数据。身份或参数漂移返回 409，未适配车型 422；不静默替换为内置机器人。
- 共用车库改为独立停车位及完整任务串行预约；开启车间物理碰撞，接触或距离不足停全车并记失败。保存接触位置/时间/车辆对、控制周期误差与指令、实际作业停留；成功还须通过连续圆足迹、同步轨迹最小车间距和传感器完整性检查。
- 修正作物行几何数量与碰撞次数混用，分别记录 `row_collision_shapes` 与 `row_collisions`；无接触观测的旧记录返回 null，原始文件不改写。速度在完成后继续随真值更新，独立检查复算里程并要求最终停止。
- 图表使用提交时实例，拒绝混入无关场景/会话或不同输入的单实例比较；内容散列缓存预算 64 MiB。误差图使用真实控制周期，地图注释索引对应原始轨迹；完成曲线按完成停留时刻计数，取消的缺失用时不伪造为零。
- `GET /lab/api/runs/{id}/record` 组装规划、场景、资产、推荐、仿真及关闭报告，返回内容 SHA256。它是完整性散列，不是身份签名；现有前端按钮暂未接此新版端点。
- 历史结果列表缓存紧凑摘要，随文件替换/删除失效。12 个真实结果、7 次重复的中位耗时 **70.91 → 0.414 ms**，摘要逐值相同；仅代表列表缓存收益，不代表求解加速。[数据与输入哈希](../../2026-10-17/backend/performance-final.json)，复测脚本为 `src/lab/e2e/result_index_benchmark.py`。

| 实测项目 | 结果与证据 |
|---|---|
| 后端回归 | **161 passed**，3 条已有依赖弃用警告；含无可行解、超时、取消、资产篡改、冻结输入、图表与缓存失效。[日志](../../2026-10-17/backend/pytest-clock-fixed.log) |
| 真实行间、自由通行、取消与恢复 | 2 车 8 任务完成；行间实际 370.59 m / 428.34 s，最小足迹净空 1.021 m；取消 canceled/0，实际重叠两车触发接触 failed/1，随后重启成功；各场关闭 PASS、无所属残留。[汇总](../../2026-10-17/backend/clock-fixed/summary.json)、[真实接触记录](../../2026-10-17/backend/clock-fixed/experiment-contact.json) |
| 时钟停滞、桥接退出与网页桥 | 故障应 failed/1，恢复成功；Foxglove 收到车辆消息，Gazebo WebSocket 返回正确世界，执行中两次 RViz 开关。[最终版本复测](../../2026-10-17/backend/final-faults/summary.json) |
| 实际前端闭环 | 页面生成 60×40 m 果园、2 车、8 点和池塘；规则推荐、三算法求解及独立验算。PyVRP 沿行间执行 **8/8、299.21 m / 342.52 s、最大横向偏差 0.0887 m**；最小足迹净空 **0.865 m**，终点速度归零。页面下载后关闭 rc=0、无残留。[截图](../../2026-10-17/backend/ui-final-success.jpg)、[结果](../../2026-10-17/backend/ui-final-result.json)、[服务端完整记录](../../2026-10-17/backend/ui-final-record.json)、[原始目录](../../2026-10-17/backend/ui-final-runtime/) |
| 页面导出 | 实验 JSON、12 张科研图的论文图包真实下载；图包含 PDF/SVG/PNG/CSV、图注和清单，ZIP 校验通过。图包基于较早同方案执行，最终执行另有结果导出。[图包](../../2026-10-17/backend/ui-figures.zip)、[清单](../../2026-10-17/backend/ui-figures-manifest.json)、[最终页面下载](../../2026-10-17/backend/ui-final-browser-result.json) |
| 网关与依赖 | 独立空闲/保持 SSE 连接的 3 次网关启停 rc=0；正式网关再次有序退出 rc=0，统一入口启动最新代码。锁文件增加已安装的直接绘图依赖；锁定离线同步未替换环境。[生命周期](../../2026-10-17/backend/gateway-lifecycle/summary.json)、[依赖检查](../../2026-10-17/backend/dependency-check.log) |

一次真实仿真回归须保留：改用 TF 头计算速度后，当前 Fortress 转换每条头时间为零，导致里程为零却通过旧检查。`settled/` 的 succeeded **不能作为有效科研里程结果**；这些隔离数据未进入正式运行库。现按收到真值时最新 `/clock` 回退，`truth_timing` 明确记录来源，属于接收时刻估计；加上里程复算和停车验收后，`clock-fixed/` 及最终页面运行通过。最初接触话题配置错误、注入位置偏离移动目标等失败同样保留，未删除或改判。

仍有关闭异常的范围限制：早期正式网关一次 API 关闭时工具收到 143，日志仅到 `Shutting down`，未取得信号来源证据。随后 3 次隔离复测及正式关闭均为 0，未复现，故不宣称该单次异常已定位根因；保留 `gateway-release.log`。该异常留下的档案服务已按本轮启动日志、命令行及启动时间核定归属后定向 SIGINT 停止（原父进程已消失，退出码未知）；网关重新启动并管理替代进程后，补验完整关闭，网关与档案服务均 rc=0。见 [定向恢复记录](../../2026-10-17/backend/archive-recovery.json)、[完整关闭日志](../../2026-10-17/backend/gateway-final.log)。桥接源码修复沿用上一轮，本轮真实会话核验其使用，但未重复 600 次压力实验。

目录沿用既有导航，仅盘点、清理白名单可重建后端缓存、归集证据与源码快照；不移动环境或删除研究结果。JDK 可选 `lib/src.zip` 断链保留，工作台不依赖它。[盘点](../../2026-10-17/backend/folder-audit.json)、[前端指纹](../../2026-10-17/backend/frontend-unchanged.json)。

边界：串行预约增加用时；规划指标不含停车接驳、转向与排队，不能直接用差值判算法优劣。碰撞结论限于当前实体世界、圆足迹及记录的分段线性时间轨迹，不证明未观测运动。异构车队、阿克曼多车曲率、通用导入车辆执行、并行多车避碰、学习推荐增益仍未交付。前端固定旧文案与新版导出接入见 [后端对接需求](../../2026-10-16/后端对接需求.md)，本轮未擅改前端。

## 桥接根因修复、后端优化与整理（2026-10-16，后续复验）

当前桥接使用源码修复，**不再加载 `_exit` 垫片**。旧说明与失败日志保留为历史证据。原版在本机重新测试 200 个独立桥接进程，9 次 SIGABRT；Memcheck 44 个进程中 2 个报告非法访问：`rclcpp::SignalHandler::deferred_signal_handler → Context::shutdown → rcl_logging_external_shutdown → spdlog::registry::drop` 访问已被主线程 `__run_exit_handlers` 释放的注册表。定位依据是释放与访问双方的调用栈，不只是 `free()` 报错位置。[原始内存检查](../../2026-10-16/hardening/memcheck-stock-repeat/)、[对照](../../2026-10-16/hardening/stock-control/summary.json)。

`spin()` 因 context 失效返回时，异步信号线程可能还在关闭日志。修复在官方 0.244.26 的 `parameter_bridge` 主函数作用域结束前调用 `rclcpp::shutdown()`，等待 context 关闭并 join 信号线程，然后正常执行静态析构。日志、异常信号和返回码保持真实。对应 [ROS 16.0.21 shutdown 源码](https://github.com/ros2/rclcpp/blob/16.0.21/rclcpp/src/rclcpp/utilities.cpp) 与 [join 实现](https://github.com/ros2/rclcpp/blob/16.0.21/rclcpp/src/rclcpp/signal_handler.cpp) 已按版本下载留证。只通过进程级 ament 前缀替换桥接可执行文件，复用系统消息转换库，不修改 `/opt/ros` 或系统 Python；源码、产物和依赖指纹都校验。

| 验证 | 结果 |
|---|---|
| 修复版退出压力 | SIGINT 400/400、SIGTERM 200/200 为 0，无强杀、启动失败或提前退出；单位是单个桥接进程，不是完整机器人会话 |
| Memcheck 修复版 | 40/40 无非法内存访问报告；这不是完整泄漏或数据竞争证明 |
| 延长日志关闭 500 ms 的因果探针 | 原版 8/8 在关闭完成前 main 已返回；修复版 8/8 先完成日志关闭再返回；探针未跳过析构或替换状态码 |
| 非法命令 | 仍返回 255，不把失败归零 |
| Python 回归 | 108 项通过，含真实父子进程单次信号转发、会话重启身份与接管失联回归；保留三个已有依赖弃用警告。[日志](../../2026-10-16/hardening/pytest-final-108.log) |
| 真实田间闭环 | 自由/行间 2 车 8 点成功；取消 canceled/0，遥测中断与桥接提前退出 failed/1，恢复重启成功，所属进程全部回收 |
| 网页桥 | 收到真实 Foxglove 遥测，Gazebo 世界查询通过；执行中两次 RViz 开关成功，最终轨迹检查通过 |
| 实际页面闭环 | 在未修改的前端选择迷宫、推荐三算法求解、查看独立验算、AMCL 下依次执行两种模式、下载两个实验 JSON、关闭；均 2/2，源码/参数/轨迹可追溯，关闭 PASS、所有退出码 0、无残留。[验算截图](../../2026-10-16/hardening/ui-maze-check.jpg)、[执行截图](../../2026-10-16/hardening/ui-maze-success.jpg)、[下载文件](../../2026-10-16/hardening/ui-evidence/) |
| 正式网关仓库长路线 | AMCL + FollowPath，5/5、16/16 路径段；实际 58.786 m、最大偏差 0.0804 m、终点误差 0.0825 m；独立地图检查通过，净空 0.760 m。377 s 实际执行后关闭 11.7 s，全部正常退出、无残留，整场 PASS。[完整结果](../../2026-10-16/hardening/warehouse-deployed/report.json)、[页面下载](../../2026-10-16/hardening/warehouse-deployed/browser-export.json)、[关闭原始报告](../../2026-10-16/hardening/deployed-sessions/sim_20261016T072343_417e5b/session-report.json)、[截图](../../2026-10-16/hardening/ui-warehouse-deployed.jpg) |

几何建图已按性能剖析改成分批 GEOS 运算。40／200／600 点中位时间分别从 14.61／138.26／1185.91 ms 降至 4.44／39.48／475.26 ms，约 3.29／3.50／2.50 倍；三个固定场景的节点、距离矩阵、路径前驱逐位相同。仅说明建图性能，不冒充整个求解器提速。[前后数据](../../2026-10-16/hardening/performance-after.json)。

目录整理将三个根目录文档归入 `docs/`，修正相关引用并检查 506 个本地链接；运行进程管理迁入 `src/lab/ros/processes.py`，不再导入日期目录的 Nav2 验收脚本。旧垫片源码、清单和二进制归档在 `hardening/retired-exit-guard/`。删除约 1.38 GB 可重建的诊断编译缓存，另按白名单清理后端 Python 缓存；保留来源与删除清单。文献、数据、未提交前端成果、历史实验与 Git 历史均保留。[目录与保留规则](../../../docs/README.md)、[迁移清单](../../2026-10-16/hardening/document-relocations.json)、[编译缓存清单](../../2026-10-16/hardening/removed-build-cache.json)、[Python 缓存清单](../../2026-10-16/hardening/cache-cleanup.json)。盘点发现独立 `baseline-worker` 中 JDK 的可选源码压缩包链接失效，未改动该研究环境；应用不依赖它。

原版 DWB 在 AMCL 连续切换执行模式时实测 90 s 无法完成后方目标；改用已安装的 RPP，并读取有效参数后才声明就绪。最新页面闭环路径跟踪为 4.100 m、最大偏差 0.0427 m；逐点导航为 4.071 m、最大偏离 0.039 m。前者传入求解器几何，后者仍由 Nav2 重规划。只改会话参数文件，没有放宽原有验收阈值。早期 `tb4-rpp` 导出中的接驳说明还写着 DWB，但有效参数已经是 RPP；网关重启后说明已纠正，原始导出不改写。

仓库长路线首轮达到 5/5、实际 58.81 m、最大偏差 0.082 m，但关闭发生 SIGTERM，整场仍判 FAIL。核对官方启动文件发现 Gazebo 通过 `shell=True` 启动，向 launch 领导进程发信号不能可靠停止其孙进程。现用 Fortress 的 `/server_control` 请求正常停止，并让 TB4 节点在其时钟和服务依赖尚在时先退出；其后回收全部进程并核验真实退出码。第一次失败保留在 [warehouse-rpp](../../2026-10-16/hardening/warehouse-rpp/report.json)，没有用改判状态掩盖它。TB4 节点那次超时的内部阻塞点未做调用栈证明，因此不宣称另一个上游缺陷已被定位。

连续启停还复现了新会话返回旧会话 ID 的网关竞态，现按当前会话身份隔离迟到响应；过期的“会话已退出”通知不能把新任务误记为失败。接管只允许同一运行目录、环境标识及进程启动时间均匹配的会话，失联及时报错；并行隔离测试网关不会再被正式网关接管。服务说明移除 `_exit` 残留引用，选择原版对照时会明确显示未修复状态。

正式网关重启后，仓库三场连续会话分别完成取消后正常关闭、桥接故障如实失败、重启后正常关闭；每场的请求 ID 与就绪 ID 一致、23 个运行桥接均为校验后的源码修复版、无 `_exit` 映射、无残留。[完整证据](../../2026-10-16/hardening/warehouse-recovery-deployed/summary.json)。最新资源核对为 warehouse 9、depot 1、maze 0 个独立 Fuel 模型，三个世界依赖完整；缓存共 13 个模型版本，其中部分并非这三个世界依赖。[当前依赖清单](../../2026-10-16/hardening/assets-current.json)、[缓存清单](../../2026-10-16/hardening/fuel-cache-inventory.json)。

交付网关已再次通过统一入口启动并加载全部修复，五算法求解、独立检查及导出复验通过，仿真保持关闭。与接手快照相比，139 个前端源码文件哈希全部相同。目录盘点、部署状态与证据索引见 [结构化汇总](../../2026-10-16/hardening/summary.json)、[部署核对](../../2026-10-16/hardening/deployed-check.json)、[重启后 API 复验](../../2026-10-16/hardening/post-restart-api/report.json)。

本轮网页探针最初把 Foxglove 二进制 Time 帧当 JSON，TB4 验收脚本最初按默认目录寻找隔离会话报告，均保留原始失败；已分别修正帧类型处理与显式 `--runtime`。浏览器观察到现有 Three.js 弃用、重复导入及模型加载警告，未改前端代码；这不等于前端零警告验收。

边界：这是已复现的桥接关闭竞态修复，不是所有 ROS/Gazebo 缺陷均已消除的声明；上游所有权循环是另一个问题，本轮未把它误称为这次非法访问的源头。TF2/GUI 的兼容覆盖仍单独存在，学习推荐收益、实机、真实农业环境与车间避碰仍不在这次验收结论内。`URP_BRIDGE_FIX=0` 选择未修复的系统桥接，供隔离对照，不会启用旧 `_exit`。

## 后端复验与修正（2026-10-16）

本轮仅修改后端、后端测试和对应文档，保留 Claude 的全部前端成果；接手快照与交付哈希核对见 [backend 证据](../../2026-10-16/backend/summary.json)。主网关已获用户授权后有序重启，仍使用唯一入口 `bash setup/run.sh lab --open`，未重建前端或更换 Python / 依赖。

修复了实际复现的问题：

- 原检查器会接受空几何/空作业清单、错误里程和不一致的分趟清单；重合任务/车库的零距离边会被稀疏图丢弃。[修复前复现](../../2026-10-16/backend/reproduced-before.json)。现逐项复算任务/分趟/作业位置顺序、真实返库卸载、容量、里程和用时；按连续路径段与原始障碍/作物多边形复核圆足迹。拒绝候选保存在 `raw_result.rejected_routes`，不再标为 feasible。
- 仿真启动重新验算保存的输入与路线；未验算、半径小于当前模型外接圆 0.4883 m、超过 15 台执行车辆（16 位碰撞掩码限制）等明确拒绝。规划仍支持通用车队规模。停车位到车库的接驳线也检查净空；树木的碰撞几何使用地图多边形，不再用等面积圆替代。
- 修复近邻/重合作业提前服务、停留时间被覆盖和长作业误触发卡住判断；保存精确路径发生位置及 `serviced_at`。取消保留 canceled 结果，真值/里程计/时钟中断以墙钟 3 s 看门狗报错；必需组件提前退出（即使 rc=0）使会话失败。最终状态落盘，网关不再把失败或失联显示成正常停止/重新启动。
- 结果增加独立实际轨迹检查；观察到的连续线段圆足迹须留在场内且避开实体障碍/作物，双向路径偏差须 ≤0.5 m（0.1 m 采样并保守加入 0.05 m 误差界），终点误差 ≤0.35 m，逐任务停留时间必须完成。使用理想真值定位，不证明传感器定位或车间避碰；轨迹采样间的未观测运动未作连续时间证明。实际里程/用时含停车位接驳与转向，规划指标从车库算起，导出明确记录此口径。
- 修复网页数据桥过早发布地址，以及重复开关窗口复用已存在日志文件的问题。窗口关闭在后台回收所属进程，执行控制继续运行。完整导出包含原规划、实际轨迹、执行配置和源码/世界哈希。`session-report.status`、`cleanup_status`、`execution_state` 分别说明会话、清理与任务结果，不能混用。

| 实际复验 | 结果与证据 |
|---|---|
| Python 回归 | 97 项通过（原 56 + 新增 41）；覆盖篡改、零距离、作业时序、非法入参、仿真准入及轨迹检查。[日志](../../2026-10-16/backend/pytest-final.log) |
| 自由通行 · 2 车 8 点 | 8/8、2 车返库；规划 209.075 m、实际 211.18 m；独立轨迹检查通过、退出 0、清理 PASS。[完整导出](../../2026-10-16/backend/live-web/experiment-free.json) |
| 行间通行 · 同一场景 | 8/8、2 车返库；规划 363.422 m、实际 364.67 m；实体作物行净空检查通过、退出 0、清理 PASS。[完整导出](../../2026-10-16/backend/live-web/experiment-rows.json) |
| 取消、遥测中断、桥接提前退出、故障后重启 | 分别为 canceled/0、failed/1、failed/1、succeeded/0；清理均 PASS、所属残留均空。桥接 SIGTERM 后实际以 0 提前退出，仍正确判会话故障。[汇总](../../2026-10-16/backend/live-final/summary.json) |
| 网页桥及原生窗口控制 | Foxglove 收到真实 `/workbench/fleet_status` 二进制消息；Gazebo WebSocket 完成授权、协议与世界查询；执行中两次打开/关闭 RViz，独立日志保留，路径仍通过，退出 0。[会话](../../2026-10-16/backend/live-web/experiment-web.json)、[Foxglove](../../2026-10-16/backend/live-web/foxglove.json)、[Gazebo](../../2026-10-16/backend/live-web/gazebo-web.json) |
| 主网关部署 | 新进程健康、0 倍速请求正确返回 400、两类仿真均已停止、前端源码哈希与接手一致。[核对](../../2026-10-16/backend/deployed-check.json) |

先前网页桥连接过早导致的一次验收失败及其 canceled 会话完整保留在 `live-final`，没有重写为成功；修正后的网页桥结果在 `live-web`。本轮使用隔离存储、ROS domain 141 和控制端口 4193；原始日志、SDF、计划、真值轨迹及清理报告位于各批 `runtime/fieldsim/`。复验脚本：[field_backend.py](../../../src/lab/e2e/field_backend.py)（从 `src/lab` 使用现有 `.venv/bin/python` 运行，`--out` 必须是新的绝对路径）。该次复验未涉及前端重新设计或浏览器交互验收，桥接退出垫片当时仍是临时缓解；后续已完成源码根因修复及实际浏览器验收，见本文最上方记录。

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

### 沿作物行间与地头通行（作物行带碰撞）

生成的农田地图现在默认按作物行通行（检查器「通行方式」可改回自由通行，导入与旧地图默认自由通行）。每块地按作物行距和行向种出作物行；行间净宽够车宽加两侧各 0.1 m 时每两行之间就是一条通道，否则每两行留出一条作业道。车辆只能沿通道中线行驶，经地头和机耕路换行，任务在离它最近的通道点作业。VRP 距离矩阵、路线和独立验算都基于这张通行图；地图编辑器淡显通道，地块检查器给出行距与通道宽度。Gazebo 世界里作物行带碰撞（下面的任务共 210 行），机器人开到急弯处原地转向。

上面那句猕猴桃园任务，同一张地图、同一 PyVRP（5 s），4× 倍速：

| 指标 | 沿行间与地头：规划 | 执行 | 自由通行：规划 | 执行 |
|---|---|---|---|---|
| 到达任务 | 48 | 48 / 48，4 车回库 | 48 | 48 / 48，4 车回库 |
| 最晚完成时间 | 951.0 s | 1 021.6 s（+7.4%） | 542.3 s | 558.5 s（+3.0%） |
| 总里程 | 3 291.1 m | 3 285.8 m（−0.2%） | 1 853.4 m | 1 856.0 m（+0.1%） |
| 绕行系数（路线 / 作业点间直线） | 1.54 | — | 1.00 | — |
| 急弯 / 行内掉头 | 107 / 28 | — | 33 / 0 | — |
| 横向偏差 | — | 均值 0.6 cm，最大 0.15 m | — | 均值 0.4 cm，最大 0.15 m |
| 车体（含轮 0.8 × 0.74 m）压到作物行的位姿 | — | 0 / 7 824，最小净距 0.19 m | — | 2 258 / 4 296 |

- 沿行间通行让规划里程多 78%、最晚完成多 75%：换行必须先出到地头或机耕路，作业点平均离通道 1.09 m（最远 2.19 m）。6 张示例地图上（PyVRP 1 s）行间与自由通行的里程比为 1.3–2.5，通行图建图 0.04–0.15 s。
- 执行比规划多出的时间主要来自急弯处原地转向（行间方案的急弯是自由通行的 3 倍多）；规划时长目前只按里程 / 车速 + 作业时间估算，还没有计入转向。
- 验算新增两项：路线经过每个任务的作业位置，且作业位置是离任务最近的可达处；按行间通行时每段路线都必须落在开阔区或通道中线上。把两站之间换成一条斜穿作物的直线，验算报「1 段路线离开行间通道和地头，斜穿了作物」。
- 控制器修正：路线在行内原路折返后会再经过同一个出入口，原先的进度投影会跳到之后那一段，现在只在当前进度前后 2 m 内投影；急弯先开到弯点再原地转向；机器人驱动轮移到车体中线，原地转向不再甩尾。自由通行用同一控制器重跑：558.5 s（之前的控制器为 552.7 s）。
- 浏览器里走一遍：检查器选「沿行间与地头」→ 对比三个算法 → 验算面板 7 项全部通过（含「只走行间通道和地头，不斜穿作物」「路线经过每个任务的作业位置」）→ 方案对比里点「Gazebo」。这次送进去的是节约 + 2-opt 方案：48 / 48，最晚完成 1 024.9 s（规划 963.7 s，+6.3%），里程 3 507.6 m（规划 3 513.7 m），车体与作物行 0 / 7 860 接触，最小净距 0.19 m；ROS 视图与 gzweb 里都能看到作物行。
- 会话：上表两次与节约方案那次 `session-report.json` 均为 PASS、无残留进程。同一行间 PyVRP 方案的前一次执行结果一致（1 021.3 s、3 285.4 m），但关闭时 Gazebo 服务端没有响应 SIGINT / SIGTERM，被 SIGKILL，那次报告为 FAIL；今天 7 次田间会话里出现 1 次，其余都在 SIGINT 后 0.2 s 内退出。

证据：[两种通行的路线图（行间](workbench/fieldsim-rows-vs-free/plan-rows.png)、[自由](workbench/fieldsim-rows-vs-free/plan-free.png)），[对比摘要、两次会话的世界 / 计划 / 结果 / 会话报告](workbench/fieldsim-rows-vs-free/)。自动检查：Python 56 通过；前端 42 通过；类型检查与生产构建通过。

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

## 桥接退出历史（2026-10-15）：当时保留临时缓解

本节保留旧结论与计数；当前源码修复和验收见本文顶部。旧实现已[归档](../../2026-10-16/hardening/retired-exit-guard/)。

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
