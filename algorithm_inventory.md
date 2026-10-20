# 算法库登记与 CVRP 适用范围

更新于 2026-10-19。[主计划](protocol/formal_plan.json)包含 17 个配置，涵盖算法家族及其邻域、参数或编码配置。4505 个唯一终态已完成，独立重审确认 4316 项可行、189 项无有效解，详见 [基线入口](experiments/baselines/cvrp/README.md)与 [归档重审](protocol/audits/20261017/README.md)。53 个问题来自 51 个底本，正式计划仍按 53 个问题计数。

主计划、[AILS-II / SISR vendor 120 项](experiments/baselines/cvrp/evidence/vendor_all120_audit.json)、[接手验收 742 项与旧 / 新各 48 项](experiments/baselines/cvrp/handoff/20261016-liyueying/核验与接手.md)按各自预算和目的独立记账。研究进展见 [2026-10-19 交付索引](docs/导师查看.md)，源码接入过程保留在本页历史记录中。

现有基线用于路线质量比较与描述性统计。cloud seed0 的 901 项具备归档 VERIFIED 主机链；cloud seed2 的 901 项已有尚未 VERIFIED 的 host manifest；本机 2703 项已有绑定结果哈希的 FROZEN resource manifest，待找回原汇总引用的主机与环境包装。其余 3604 项保留路线质量与描述性汇总价值，同条件耗时统计按 [重审](protocol/audits/20261017/README.md)规定的证明等级报告。

算法选择器负责从候选求解器中选择算法。[当前冻结模型](src/lab/models/cvrp-knn-v1.json)对应独立的 train60/cal30/test30 实验：严格成本比较中，PyVRP 在训练集为 51 胜 9 平、校准集为 23 胜 7 平、测试集为 27 胜 3 平；OR-Tools 严格更优 0 次。测试尚未显示相对固定 PyVRP 的选择收益。`cvrp_selector_crc` 的早期离线回放与这批 120 项实验分别归档。

## 主基线算法配置

Clarke–Wright savings；T / TRS / TSR；PyVRP ILS；NN；Sweep；完整 VND；多起点 VND；4 种固定 LNS destroy / repair 配对；OR-Tools GLS；GA / PSO / DE random-key + Split。

T / TRS / TSR 是 VND 的邻域配置。NN、Sweep 与 VND 的基线距离统一为整数 EUC2D，历史连续欧氏距离结果单独保留。4 种 LNS 采用固定破坏—修复配对，本轮按截止时间控制预算，历史 delta 预算结果分别记录。

GA / PSO / DE 是本轮新增的 CVRP 教学适配，统一使用种群 20 和预先固定的参数。它们与历史连续优化实现分别登记。Split 求给定排列的最优切分，具体定义见下文。

## 完整登记

本表按当前 CVRPLIB 基线登记各项目。“源码登记”表示已收录源码或资料快照，运行证据由对应实验提供；CVRP 适用性与运行状态分别列示。表中“接入待核验”指经典 CVRP 入口与检查点适配。

| ID | 家族 / 角色 | 状态 | CVRP 适用 | 说明 |
|---|---|---|---|---|
| savings | Clarke–Wright 构造 | 主基线已完成 | 是 | Clarke–Wright savings 构造。 |
| T | VND | 主基线已完成 | 是 | VND 的 T 邻域配置。 |
| TRS | VND | 主基线已完成 | 是 | VND 的 TRS 邻域配置。 |
| TSR | VND | 主基线已完成 | 是 | VND 的 TSR 邻域配置。 |
| pyvrp | ILS | 主基线已完成 | 是 | PyVRP 0.14.0 ILS。 |
| nearest_neighbor | 最近邻构造 | 主基线已完成 | 是 | 最近邻构造，距离统一为整数 EUC2D。 |
| seeded_sweep | Sweep 构造 | 主基线已完成 | 是 | Sweep 构造，距离统一为整数 EUC2D。 |
| savings_vnd | VND | 主基线已完成 | 是 | Savings 初始化与完整 VND，距离统一为整数 EUC2D。 |
| multistart_vnd | VND | 主基线已完成 | 是 | 请求 8 个起点，共享截止时间；实际完成起点数随预算记录，距离统一为整数 EUC2D。 |
| random_cheapest | 固定破坏—修复 LNS | 主基线已完成 | 是 | 随机移除 + 最便宜插入；固定算子配对。 |
| random_regret2 | 固定破坏—修复 LNS | 主基线已完成 | 是 | 随机移除 + regret-2 修复；固定算子配对。 |
| worst_cheapest | 固定破坏—修复 LNS | 主基线已完成 | 是 | 最差移除 + 最便宜插入；固定算子配对。 |
| worst_regret2 | 固定破坏—修复 LNS | 主基线已完成 | 是 | 最差移除 + regret-2 修复；固定算子配对。 |
| ortools_gls | 引导局部搜索 | 主基线已完成 | 是 | 历史版本 9.14.6206，PCI + GLS，lambda = 0.1；3 个官方案例的 18/18 次调用有效。新批次独立测量。 |
| ga_random_keys | GA | 主基线完成；Split 校验 1080 例通过 | 是 | 随机键 + Split 教学实现；种群 20，参数固定。Split 求给定排列的最优切分，见 [定义来源](https://arxiv.org/abs/1508.02759)。 |
| pso_random_keys | PSO | 主基线完成；Split 校验 1080 例通过 | 是 | 随机键 + Split 教学实现；种群 20，参数固定。Split 求给定排列的最优切分，见 [定义来源](https://arxiv.org/abs/1508.02759)。 |
| de_random_keys | DE | 主基线完成；Split 校验 1080 例通过 | 是 | 随机键 + Split 教学实现；种群 20，参数固定。Split 求给定排列的最优切分，见 [定义来源](https://arxiv.org/abs/1508.02759)。 |
| held_karp_capacity_partition | 精确动态规划 | 已有小规模历史测试 | 是 | Held–Karp 与容量子集 DP，复杂度为指数级，用于小规模精确校验。 |
| capacity_partition_pruning | 容量初始化 | 已有历史测试 | 否 | 容量初始化与剪枝组件；构造失败和已证明不可行分别记录。 |
| cvrp_selector_crc | 算法选择 | 已实现；已有历史实验 | 否 | 根据实例选择求解器，输入与评价参考值隔离。 |
| continuous_ga_pso | 连续优化 | 已实现或有历史报告 | 否 | 历史连续优化实验：6 行汇总 × 20 次，共 120 次运行。 |
| continuous_de | 连续优化 | 已实现或有历史报告 | 否 | 连续 DE 与搜索控制研究；CVRP 使用需另配路线解码器。 |
| deap_sphere_ga | 连续优化 | 已实现或有历史报告 | 否 | 以 sphere 函数为目标的教学实现。 |
| bin_packing_rules_eoh | 在线装箱 | 已实现或有历史报告 | 否 | 包含 FF、BF、EoH、生成规则与选择器变体，按在线装箱的目标和可行性条件评价。 |
| sorting_generated | 排序 | 已实现或有历史报告 | 否 | 排序算法与生成代码。 |
| nas_fidelity | 神经架构搜索 | 已实现或有历史报告 | 否 | 架构优化与训练保真度研究。 |
| orchard_navigation | 几何路径规划 | 已实现或有历史报告 | 否 | 考虑障碍物的局部几何规划，按相应几何输入评价。 |
| field_visibility_dijkstra_nn | 几何任务路由 | 已实现或有历史报告 | 否 | 真实边界与合成任务上的可视图 + Dijkstra + NN，采用几何任务距离。 |
| field_pyvrp_penalties | CVRP 参数研究 | 已实现或有历史报告 | 否 | 同一 PyVRP 实现的默认 / 固定容量惩罚 × E / G 几何参数配置。 |
| vrptw_heuristics | 带时间窗路由 | 已实现或有历史报告 | 否 | 距离优先与时间窗优先启发式，按时间窗及实际服务范围记录成本。 |
| direct_generated_route | LLM 路线生成 | 已实现或有历史报告 | 否 | LLM 生成路线与准入测试；固定基线需归档冻结代码。 |
| turn_service_modes | 转弯感知服务路由 | 已实现或有历史报告 | 否 | 合成转弯服务任务的求解器与验算器。 |
| parent_selection | 演化控制 | 已实现或有历史报告 | 否 | 演化流程的父代选择组件。 |
| vendor:AILS-II | ILS | vendor 120 项完成并审计 | 是 | Java 种子适配器与完整 incumbent 流；X12 按 unrestricted 范围评价，保留原内部路线界限。 |
| vendor:ASlibScenario | 算法选择数据接口 | 源码登记 | 否 | 算法选择数据接口。 |
| vendor:ADAS | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:APE | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:ACCEL | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:ALE-Bench | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:CEoH | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:AlphaEvolve-Results | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:DACBench | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:AutoML-Zero | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:AnyJev | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:AutoFolio | 算法选择器 | 源码登记 | 否 | 算法选择器。 |
| vendor:DR-ALNS | 强化学习控制的 ALNS | 源码登记 | 是 | 已记录 CVRP 配置与入口；模型检查点、依赖及种子 / 分布兼容性待验证。 |
| vendor:DiscoRL | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:DACE | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:DSPy | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:DGM | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:DiscoGen | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:Fields2Cover | 覆盖路径规划 | 源码登记 | 否 | 覆盖路径规划。 |
| vendor:EoH-S | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:EvoPrompt | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:DreamCoder | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:EoH | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:Eureka | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:FunSearch | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:G-LNS | LLM 设计的 LNS | 源码登记 | 是 | 生成框架与启发算法资料；CVRP 算子在评价前冻结，基线阶段使用冻结算子。 |
| vendor:GEPA | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:HSEvo | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:HGS-CARP | 容量受限弧路径规划 | 源码登记 | 否 | 容量受限弧路径问题。 |
| vendor:HGS-TDCARP | 时变容量受限弧路径规划 | 源码登记 | 否 | 时变容量受限弧路径问题。 |
| vendor:InstanceSpace | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:HiFo-Prompt | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:HeurAgenix | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:HpBandSter | 超参数优化 | 源码登记 | 否 | 超参数优化。 |
| vendor:Hercules | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:JAIR2026-FrugalAS | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:LLaMEA | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:LLM4AD | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:JevOut | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:Jev-Mem | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:LaT | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:Lion | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:LitCEoH | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:OPRO | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:MLEvolve | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:OptiMUS-v0.3 | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:OptiMUS-v0.2 | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:OptiMUS-v0.1 | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:QD-LHD | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:QDAIF | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:OptiMUS | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:PLR | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:PyVRP | ILS / HGS（按版本） | 源码登记 | 是 | 已收录源码快照；主基线使用官方 0.14.0 wheel，对应 ILS。 |
| vendor:POET | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:RLCDAlignBench | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:Reflexion | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:QUBE | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:RouteFinder | 神经网络构造式路由 | 源码登记 | 是 | 需配套检查点、PyTorch 环境，以及归一化输入、整数计分和尺度适配。 |
| vendor:RouteLLM | LLM 路由 | 源码登记 | 否 | LLM 路由。 |
| vendor:ReEvo | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:Self-Refine | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:SMAC3 | 算法配置 | 源码登记 | 否 | 算法配置。 |
| vendor:algorithm_survival_analysis | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:Voyager | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:VRPAgent | 生成式启发算法 | 源码登记 | 是 | 已收录早期发布的 generated_heuristics，完整运行研究待验证。 |
| vendor:ShinkaEvolve | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:autorank | 统计排序 | 源码登记 | 否 | 统计排序。 |
| vendor:notes | 文档 | 源码登记 | 否 | 文档资料。 |
| vendor:aslib_data | 算法选择数据 | 源码登记 | 否 | 算法选择数据。 |
| vendor:irace | 自动调参 | 源码登记 | 否 | 自动调参。 |
| vendor:lavoir | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:laya | 决策模型 | 源码登记 | 否 | 决策模型。 |
| vendor:rl4co | 神经路由框架 | 源码登记 | 是 | 包含多种环境与模型；接入需选定预训练模型、检查点及 CVRP 适配器。 |
| vendor:open-source-sisr-routing | SISR / LNS | vendor 120 项完成并审计 | 是 | C++20 种子适配器，保留原日程；X12 unrestricted 范围与整数距离已验证。 |
| vendor:online_as | 算法设计、学习与工具快照 | 源码登记 | 待核实 | 接入待核验。 |
| vendor:typesafe-router | 类型化模型路由 | 源码登记 | 否 | 类型化模型路由。 |

## 接入范围与后续安排

- `src/repos/` 共登记 76 个目录项，其中 `notes` 为资料目录；源码目录数为 75，目录项总数为 76。复现状态按各项目的运行与验算记录统计。详见 [外部代码目录](src/repos/README.md)。
- AILS-II 与 SISR 已完成独立 vendor 120 项对照和验算，其并发验算方式与预算按该批次记录。主计划维持 17 配置及原分母，各批耗时分别统计。DR-ALNS、RouteFinder 与 RL4CO 的后续接入需冻结模型、检查点及尺度适配。
- HGS-CARP 与 HGS-TDCARP 面向弧路径问题。独立 HGS-CVRP 实现尚待定位；当前 PyVRP 0.14 按 ILS 登记。
- NN / Sweep 在车辆上限下的构造失败保留在统计分母中。多起点共享预算，并记录实际完成的起点数。
- 旧报告与原源码快照继续归档，新增原始结果另存。连续欧氏与 EUC2D、固定车数与标准 CVRP 分别按各自合同评价。
- 精确证据路径、126 份报告扫描索引及全部 vendor 文件路径见 `algorithm_inventory.json`。

## 新增种群算法的冻结定义

GA、PSO 与 DE 均为本轮新增的教学实现，参数与算子按本节冻结定义执行，与历史连续函数实验分别归档。

客户节点按 `(random-key, customer-ID)` 升序解码。固定顺序 Split 使用整数 EUC2D 和容量约束；超过 K 时，执行最多 K 辆车的分层 DP。种群为 20，初始 key 在 [0,1] 上均匀生成。算法输入限定为问题坐标、需求、容量、K、seed 与预算，参考解和参考成本与求解过程隔离。配置在实验前冻结。

- **GA：** 3 元锦标赛，逐位 0.5 均匀交叉，逐位 1/n 均匀重置变异，保留 1 个精英。
- **PSO：** 惯性 0.7298，个体与群体系数均为 1.49618，速度截断为 ±0.2，位置截断为 [0,1]；每轮使用该轮固定的全局最佳。
- **DE：** rand/1/bin，F = 0.5、CR = 0.9，强制至少 1 维变异，位置截断为 [0,1]，以 ≤ 作为接受条件，采用顺序原位 / 异步更新。
- **Split：** 使用二次 DP，必要时加入车辆维度 DP，求给定排列的最优切分。

主要定义来源：[Split](https://arxiv.org/abs/1508.02759)、[DE 原论文](https://doi.org/10.1023/A:1008202821328)、[PSO 原论文](https://staff.washington.edu/paymana/swarm/kennedy95-ijcnn.pdf)。本工程的算子、参数与更新顺序以以上定义为准。

Split 独立校验覆盖 1080 个小排列与车辆上限问题，逐一与全部切割枚举的最优值一致。这组测试用于检验解码正确性，正式 CVRPLIB 性能结果另行报告。

随机键编码参考 [Bean 1994](https://doi.org/10.1287/ijoc.6.2.154)，GA 算子与参数采用本工程冻结定义。

## Cohort B 源码接入核查

以下记录正式批次启动前的源码与环境检查。后续适配及 120 项实验状态见下一节和 vendor 审计。

- **AILS-II：** 当时已检查 Java 入口、配置与 Solution。`-best` 参与提前停止，适配要求将 BKS 与该参数隔离，并将默认 0 按默认值记录。原实现的 `new Random()` 未暴露种子，CLI 仅输出成本与进度，接入需补充完整路线和初始 incumbent 输出。当时环境有 JRE 21，javac 未在 PATH；适配范围包括全部随机源和车辆上下界，保留算法本体。
- **SISR：** 当时已恢复 16 个 CVRP 源码、配置与许可证文件，采用 Apache 2 许可。g++ 可用，cmake 未在 PATH，可直接等价编译。原构造使用 `random_device` 初始化，CLI 缺少 seed / deadline 接口，仅在完整迭代结束后调用 `saveJson`。接入要求增加透明种子和 incumbent 观测接口，保留原迭代温度日程，由独立主管管理退出与计时。`ProblemInstance` 的中间 dx / dy 使用 float，整数 EUC2D 一致性通过逐边验证确认。
- 两者均按成熟 CVRP 源码进行适配。编译与数值测试安排在正式 17 配置计时窗口之外，以隔离背景负载。

## Cohort B 技术验收与实验完成情况

AILS-II 与 SISR 均已编译，toy 完整路线验证通过，全部 12 个 X 实例的整数距离逐边验证一致。AILS 首次 toy 越界记录保留，随后采用公开参数 `varphi = min(40,n)` 修复；X12 继续使用默认值 40。编译使用现有 JVM 的内置编译器模块。

Cohort B 独立冻结了 120 行计划：seed0 云端 24 行，seed1–4 本地 96 行。截至 2026-10-19，该批次已独立完成并审计，结果见 [vendor 审计](experiments/baselines/cvrp/evidence/vendor_all120_audit.json)。主批次与 Cohort B 分别记账。

源码交付包不含二进制或 JDK。构建与运行命令见 [cohort_b/README.md](cohort_b/README.md)。
