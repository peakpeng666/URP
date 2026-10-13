# 外部论文代码

75个代码目录：15个Git仓库、60个快照或子树。按论文和用途保留；不同论文实现和方法分支分别登记。

[本地提交](REPOSITORIES.md) · [快照文件核对](论文配套快照核查_20260928.json) · [方法与代码分析](../../materials/代码评议/README.md) · [实验进度](../../experiments/状态.md)。

当前已用于项目实验的工具包括CodeGen、DEAP、EoH固定公式、PyVRP、OR-Tools和PyTorch。论文代码阅读与数值复现状态见上述分析和实验记录。

| 目录 | 论文或用途 |
|---|---|
| [HGS-CARP](HGS-CARP/) | Thibaut Vidal 的容量弧路由混合遗传搜索算法（含转弯惩罚 NEARP-TP 支持）。 |
| [HGS-TDCARP](HGS-TDCARP/) | Vidal 的时变代价弧路由 HGS 扩展（2020 定版，存量代码）。 |
| [EoH](EoH/) | Evolution of Heuristics 官方实现（大模型思路与代码双轨演化）。 |
| [ReEvo](ReEvo/) | ReEvo 官方实现（带反思机制的 LLM 超启发式算法）。 |
| [LLM4AD](LLM4AD/) | LLM4AD 官方平台。统一自动算法设计平台。 |
| [LitCEoH](LitCEoH/) | Contextual Evolution of Heuristics 文献增强版实现。 |
| [CEoH](CEoH/) | Contextual Evolution of Heuristics 基础开源实现。 |
| [G-LNS](G-LNS/) | LLM 与大邻域搜索共进化 destroy/repair 算子 |
| [DR-ALNS](DR-ALNS/) | 深度强化学习在线控制 ALNS（ICAPS 2024，H2 直接同型工作官方代码）。 |
| [HeurAgenix](HeurAgenix/) | 微软 LLM 启发式生成智能体框架（含 Streamlit 演示与 HF 配套数据集）。 |
| [PyVRP](PyVRP/) | 高性能 VRP 求解器包源码 |
| [rl4co](rl4co/) | 组合优化强化学习训练/评测统一库 |
| [ShinkaEvolve](ShinkaEvolve/) | Sakana AI 的 AlphaEvolve 精简开源复现。 |
| [LLaMEA](LLaMEA/) | LLM 进化生成元启发式框架（活跃维护）。 |
| [autorank](autorank/) | 跨数据集统计比较 + 临界差图工具（Demšar 协议执行级实现，方案第 18 章）。 |
| [AILS-II](AILS-II/) | AILS-II (Máximo et al 2024) |
| [MLEvolve](MLEvolve/) | MLEvolve (Du et al 2026) |
| [VRPAgent](VRPAgent/) | VRPAgent (Hottung et al 2025)：本地是生成启发式与样本种群，未含完整代理生成管线 |
| [RouteFinder](RouteFinder/) | RouteFinder (Berto et al 2025) |
| [HiFo-Prompt](HiFo-Prompt/) | HiFo-Prompt (Chen et al 2026) |
| [EoH-S](EoH-S/) | EoH-S (Liu et al) |
| [QUBE](QUBE/) | QUBE (Chen et al 2025) |
| [HSEvo](HSEvo/) | HSEvo (Dat et al 2025) |
| [LaT](LaT/) | LaT (Wang et al 2026) |
| [DiscoGen](DiscoGen/) | DiscoGen (Goldie et al 2026) |
| [OptiMUS](OptiMUS/) | OptiMUS (AhmadiTeshnizi et al) |
| [DreamCoder](DreamCoder/) | DreamCoder (Ellis et al) |
| [APE](APE/) | APE (Zhou et al 2022) |
| [EvoPrompt](EvoPrompt/) | EvoPrompt (Guo et al 2024) |
| [DGM](DGM/) | Darwin Gödel Machine (Zhang et al 2025) |
| [DSPy](DSPy/) | DSPy (Khattab et al)；DSP 已并入 |
| [ALE-Bench](ALE-Bench/) | ALE-Bench (Imajuku et al 2025) |
| [irace](irace/) | irace (López-Ibáñez et al 2016) |
| [SMAC3](SMAC3/) | SMAC (Hutter et al 2010) |
| [HpBandSter](HpBandSter/) | BOHB (Falkner et al 2018) |
| [PLR](PLR/) | Prioritized Level Replay (Jiang et al 2021) |
| [POET](POET/) | POET (Wang et al 2019) |
| [Voyager](Voyager/) | Voyager (Wang et al 2023) |
| [Eureka](Eureka/) | Eureka (Ma et al 2023) |
| [ADAS](ADAS/) | Automated Design of Agentic Systems (Hu et al 2024) |
| [QDAIF](QDAIF/) | Quality-Diversity through AI Feedback (Bradley et al 2023) |
| [Self-Refine](Self-Refine/) | Self-Refine (Madaan et al 2023) |
| [Reflexion](Reflexion/) | Reflexion (Shinn et al 2023) |
| [GEPA](GEPA/) | GEPA (Agrawal et al) |
| [FunSearch](FunSearch/) | FunSearch (Romera-Paredes et al 2024) |
| [OPRO](OPRO/) | OPRO (Yang et al 2023) |
| [Lion](Lion/) | Lion (Chen et al 2023) 与 Hero 搜索空间 |
| [DiscoRL](DiscoRL/) | DiscoRL (Oh et al 2025) |
| [ACCEL](ACCEL/) | ACCEL (Parker-Holder et al 2022) |
| [Hercules](Hercules/) | Hercules (Wu et al 2025) |
| [AlphaEvolve-Results](AlphaEvolve-Results/) | AlphaEvolve (Novikov et al 2025) |
| [AutoML-Zero](AutoML-Zero/) | AutoML-Zero (Real et al 2020) |
| [OptiMUS-v0.1](OptiMUS-v0.1/) · [OptiMUS-v0.2](OptiMUS-v0.2/) · [OptiMUS-v0.3](OptiMUS-v0.3/) | OptiMUS 三版 (AhmadiTeshnizi et al) |
| [RouteLLM](RouteLLM/) | RouteLLM (Ong et al 2025) |
| [Jev-Mem](Jev-Mem/) | Jev-Mem (Jiang et al 2026) |
| [RLCDAlignBench](RLCDAlignBench/) | Just Ask Jev (Guo et al 2026) |
| [typesafe-router](typesafe-router/) | Jev 决策模型路由官方示例 |
| [InstanceSpace](InstanceSpace/) | 实例空间分析工具（库内 Instance Space Analysis） |
| [ASlibScenario](ASlibScenario/) | ASlib 基准工具 |
| [aslib_data](aslib_data/) | ASlib 场景数据 |
| [AutoFolio](AutoFolio/) | AutoFolio (Lindauer et al 2015) |
| [Fields2Cover](Fields2Cover/) | Fields2Cover (Mier et al 2023) |
| [DACBench](DACBench/) | 动态算法配置基准（条件性） |
| [algorithm_survival_analysis](algorithm_survival_analysis/) | Run2Survive (Tornede et al 2020) |
| [JAIR2026-FrugalAS](JAIR2026-FrugalAS/) | Frugal Algorithm Selection (Kus et al 2026)，含随文数据（24.9 万文件，1.27 GB） |
| [lavoir](lavoir/) | LAVOIR (Yilmaz et al 2026)；权重 1.6 GB 在 HuggingFace 未取 |
| [laya](laya/) | Laya：与 Jev 同类的开放决策模型 |
| [DACE](DACE/) | DACE (Wang et al 2025) |
| [online_as](online_as/) | 在线算法选择与截尾反馈 (Tornede et al 2022) |
| [AnyJev](AnyJev/) | AnyJev：开放 LLM 结构化决策实现（选项处理与校准） |
| [JevOut](JevOut/) | JevOut (Xu 2026) 官方代码 |
| [open-source-sisr-routing](open-source-sisr-routing/) | SISRs 开源实现论文配套（Pajerský et al 2026，CPAIOR，LNCS 16595）：main 与 cvrp/vrptw/pdptw/top/toptw/ctop 共七分支；1,074/1,074 文件与固定提交相同；章节正文未取得 |
| [QD-LHD](QD-LHD/) | Illuminating Heuristic Design（Chen & Liu 2026）第 15 页指向的参考实现；23 文件 ZIP 与公开文件接口逐字节一致；包含模拟 LLM 演示，实际评价器须自行提供；不等于完整实验资产 |

## 配套状态

LaT原始LFS数据、DreamCoder/Reflexion/irace所需子模块已在库。QUBE为占位材料，AlphaEvolve为结果与验证材料，QD-LHD为参考实现，VRPAgent含生成启发式与样本种群；完整搜索系统的可用性按各目录内容判断。

尚缺的正文、附件和实现统一记在[待补文献与配套材料](../../literature/待补文献.md)。算例位于[data/benchmarks](../../data/benchmarks/)，Solomon实例位于其`Solomon/instances/In/`目录。

许可证以各目录附带文件为准；代码评议保留了核对时的[许可文件](../../materials/代码评议/algorithm_design/delivery_licenses/)。[notes](notes/)记录外部基线问题与补丁。
