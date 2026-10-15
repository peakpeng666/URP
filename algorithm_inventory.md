# 算法库完整登记与 CVRP 适用范围

当前新增统一执行候选为17个配置，不是17个独立算法家族。历史试验、当前适配、实际新运行三者分别记账。正式通过数以独立验解后的运行账本为准。

## 立即可接入的算法配置

Clarke–Wright savings；T/TRS/TSR；PyVRP ILS；NN；Sweep；完整 VND；多起点 VND；4种固定 LNS destroy/repair 配对；OR-Tools GLS；GA/PSO/DE random-key + Split。

GA/PSO/DE为本轮新明确命名的CVRP教学适配，不冒充原连续优化代码直接跑CVRP；统一pop20、固定参数、不调参。Split按固定排列求最优切分，不代表CVRP全局最优。

## 完整登记

| ID | 家族/角色 | 状态 | CVRP适用 | 说明 |
|---|---|---|---|---|
| savings | Clarke-Wright construction | historical adapter restored; new batch status in run ledger | True | T/TRS/TSR are neighborhood configurations, not independent families; PyVRP0.14 is ILS, not HGS. |
| T | VND | historical adapter restored; new batch status in run ledger | True | T/TRS/TSR are neighborhood configurations, not independent families; PyVRP0.14 is ILS, not HGS. |
| TRS | VND | historical adapter restored; new batch status in run ledger | True | T/TRS/TSR are neighborhood configurations, not independent families; PyVRP0.14 is ILS, not HGS. |
| TSR | VND | historical adapter restored; new batch status in run ledger | True | T/TRS/TSR are neighborhood configurations, not independent families; PyVRP0.14 is ILS, not HGS. |
| pyvrp | ILS | historical adapter restored; new batch status in run ledger | True | T/TRS/TSR are neighborhood configurations, not independent families; PyVRP0.14 is ILS, not HGS. |
| nearest_neighbor | nearest-neighbor construction | restored and integer-adapted; operator audit passed | True | Historical continuous metric replaced explicitly by EUC2D. multistart requests 8 starts under shared deadline, does not guarantee completion of all. |
| seeded_sweep | sweep construction | restored and integer-adapted; operator audit passed | True | Historical continuous metric replaced explicitly by EUC2D. multistart requests 8 starts under shared deadline, does not guarantee completion of all. |
| savings_vnd | VND | restored and integer-adapted; operator audit passed | True | Historical continuous metric replaced explicitly by EUC2D. multistart requests 8 starts under shared deadline, does not guarantee completion of all. |
| multistart_vnd | VND | restored and integer-adapted; operator audit passed | True | Historical continuous metric replaced explicitly by EUC2D. multistart requests 8 starts under shared deadline, does not guarantee completion of all. |
| random_cheapest | fixed destroy-repair LNS | restored adapter; unified-budget testing pending | True | random/worst removal × cheapest/regret2 repair; not adaptive ALNS; new deadline protocol differs from historical delta budget. |
| random_regret2 | fixed destroy-repair LNS | restored adapter; unified-budget testing pending | True | random/worst removal × cheapest/regret2 repair; not adaptive ALNS; new deadline protocol differs from historical delta budget. |
| worst_cheapest | fixed destroy-repair LNS | restored adapter; unified-budget testing pending | True | random/worst removal × cheapest/regret2 repair; not adaptive ALNS; new deadline protocol differs from historical delta budget. |
| worst_regret2 | fixed destroy-repair LNS | restored adapter; unified-budget testing pending | True | random/worst removal × cheapest/regret2 repair; not adaptive ALNS; new deadline protocol differs from historical delta budget. |
| ortools_gls | guided local search | historical CVRP adapter recovered; integration owned by execution lane | True | Historical9.14.6206 PCI+GLS lambda0.1,18/18 valid official3-case calls; not just VRPTW. New batch separately measured. |
| ga_random_keys | GA | implemented; Split independent audit1080 cases passed; unified batch pending | True | New transparent random-key+Split implementation, population20 fixed parameters. Not same code/results as historical continuous optimizer, no claim paper reproduction/HGS. Split optimal only for fixed ordering; reference https://arxiv.org/abs/1508.02759 |
| pso_random_keys | PSO | implemented; Split independent audit1080 cases passed; unified batch pending | True | New transparent random-key+Split implementation, population20 fixed parameters. Not same code/results as historical continuous optimizer, no claim paper reproduction/HGS. Split optimal only for fixed ordering; reference https://arxiv.org/abs/1508.02759 |
| de_random_keys | DE | implemented; Split independent audit1080 cases passed; unified batch pending | True | New transparent random-key+Split implementation, population20 fixed parameters. Not same code/results as historical continuous optimizer, no claim paper reproduction/HGS. Split optimal only for fixed ordering; reference https://arxiv.org/abs/1508.02759 |
| held_karp_capacity_partition | exact dynamic programming | historically tested; small cases only | True | Held-Karp+capacity subset DP exponential; validation oracle not large-scale general baseline. |
| capacity_partition_pruning | capacity initialization | historically tested | False | Initializer/pruning component, not independently a full routing optimizer. Preserve construction-failure vs proven infeasible distinction. |
| cvrp_selector_crc | algorithm selection | implemented/historical experiment | False | Chooses solvers; not another path solver; must not receive evaluation reference values. |
| continuous_ga_pso | continuous optimization | implemented or historical report; see evidence | False | GA/PSO historical6 aggregated rows ×20 =120 runs, not CVRP. |
| continuous_de | continuous optimization | implemented or historical report; see evidence | False | ContinuousDE/search-control study; new route decoder required. |
| deap_sphere_ga | continuous optimization | implemented or historical report; see evidence | False | Teaching sphere objective, not CVRP. |
| bin_packing_rules_eoh | online bin packing | implemented or historical report; see evidence | False | FF/BF/EoH/generated/selector variants; substantial historic experiments but different objective and feasibility. |
| sorting_generated | sorting | implemented or historical report; see evidence | False | Sorting/generated code, not CVRP. |
| nas_fidelity | neural architecture search | implemented or historical report; see evidence | False | Architecture optimization/training-fidelity, not CVRP. |
| orchard_navigation | geometric path planning | implemented or historical report; see evidence | False | Obstacle-aware local geometry differs from standard complete-graph CVRP. |
| field_visibility_dijkstra_nn | geometric task routing | implemented or historical report; see evidence | False | Visibility graph+Dijkstra+NN on real boundary with synthetic tasks, not standard CVRPLIB metric. |
| field_pyvrp_penalties | CVRP parameter study | implemented or historical report; see evidence | False | PyVRP default/fixed-capacity penalties ×E/G geometry: same implementation parameter variants, not four new algorithms. |
| vrptw_heuristics | time-window routing | implemented or historical report; see evidence | False | Distance-first/time-window-first; different model. Do not mix partial-service costs with full CVRP. |
| direct_generated_route | LLM generated route | implemented or historical report; see evidence | False | Generated outputs/admission tests not a fixed reproducible baseline unless frozen code recovered. |
| turn_service_modes | turn-aware service routing | implemented or historical report; see evidence | False | Synthetic turn-service mode solver/checker, not CVRP. |
| parent_selection | evolution control | implemented or historical report; see evidence | False | Evolution parent selection is component/control method, not CVRP solver. |
| vendor:AILS-II | ILS | compiled, technical checks passed, separate cohort frozen; formal pending | True | Seeded Java adapter, complete incumbent stream; X12 unrestricted scope, original internal route bound retained. |
| vendor:ASlibScenario | algorithm selection dataset interface | source-only for this benchmark; no new run evidence | False | algorithm selection dataset interface |
| vendor:ADAS | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:APE | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:ACCEL | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:ALE-Bench | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:CEoH | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:AlphaEvolve-Results | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:DACBench | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:AutoML-Zero | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:AnyJev | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:AutoFolio | algorithm selector | source-only for this benchmark; no new run evidence | False | algorithm selector |
| vendor:DR-ALNS | RL-controlled ALNS | source-only for this benchmark; no new run evidence | True | CVRP config and runner documented; model checkpoint, dependency and seed/distribution compatibility unverified. |
| vendor:DiscoRL | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:DACE | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:DSPy | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:DGM | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:DiscoGen | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:Fields2Cover | coverage path planning, not delivery CVRP | source-only for this benchmark; no new run evidence | False | coverage path planning, not delivery CVRP |
| vendor:EoH-S | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:EvoPrompt | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:DreamCoder | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:EoH | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:Eureka | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:FunSearch | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:G-LNS | LLM-designed LNS | source-only for this benchmark; no new run evidence | True | Generation framework and heuristic assets; freeze CVRP generated operators before evaluation, no online API generation in baseline. |
| vendor:GEPA | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:HSEvo | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:HGS-CARP | capacitated arc routing, not node CVRP | source-only for this benchmark; no new run evidence | False | capacitated arc routing, not node CVRP |
| vendor:HGS-TDCARP | time-dependent capacitated arc routing, not node CVRP | source-only for this benchmark; no new run evidence | False | time-dependent capacitated arc routing, not node CVRP |
| vendor:InstanceSpace | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:HiFo-Prompt | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:HeurAgenix | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:HpBandSter | hyperparameter optimization | source-only for this benchmark; no new run evidence | False | hyperparameter optimization |
| vendor:Hercules | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:JAIR2026-FrugalAS | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:LLaMEA | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:LLM4AD | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:JevOut | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:Jev-Mem | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:LaT | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:Lion | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:LitCEoH | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:OPRO | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:MLEvolve | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:OptiMUS-v0.3 | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:OptiMUS-v0.2 | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:OptiMUS-v0.1 | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:QD-LHD | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:QDAIF | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:OptiMUS | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:PLR | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:PyVRP | ILS/HGS version-dependent | source-only for this benchmark; no new run evidence | True | Snapshot present; active official0.14.0 wheel is ILS. Do not relabel as HGS. |
| vendor:POET | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:RLCDAlignBench | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:Reflexion | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:QUBE | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:RouteFinder | neural constructive routing | source-only for this benchmark; no new run evidence | True | Requires checkpoints, torch env, normalized-input/integer-score and scale compatibility adapter. |
| vendor:RouteLLM | LLM routing | source-only for this benchmark; no new run evidence | False | LLM routing |
| vendor:ReEvo | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:Self-Refine | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:SMAC3 | algorithm configuration | source-only for this benchmark; no new run evidence | False | algorithm configuration |
| vendor:algorithm_survival_analysis | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:Voyager | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:VRPAgent | generated heuristics | source-only for this benchmark; no new run evidence | True | Early released generated_heuristics, not complete running study. |
| vendor:ShinkaEvolve | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:autorank | statistical ranking | source-only for this benchmark; no new run evidence | False | statistical ranking |
| vendor:notes | documentation | source-only for this benchmark; no new run evidence | False | documentation |
| vendor:aslib_data | algorithm selection data | source-only for this benchmark; no new run evidence | False | algorithm selection data |
| vendor:irace | automatic parameter tuning | source-only for this benchmark; no new run evidence | False | automatic parameter tuning |
| vendor:lavoir | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:laya | decision model | source-only for this benchmark; no new run evidence | False | decision model |
| vendor:rl4co | neural routing framework | source-only for this benchmark; no new run evidence | True | Many environments/models; not one solver. Need selected pretrained model/checkpoint and CVRP adapter. |
| vendor:open-source-sisr-routing | SISR/LNS | compiled, technical checks passed, separate cohort frozen; formal pending | True | Seeded C++20 adapter, original schedule; X12 unrestricted scope and integer metrics verified. |
| vendor:online_as | algorithm-design / learning / tooling snapshot | source-only for this benchmark; no new run evidence | not established | No verified current classical-CVRP runner/checkpoint adaptation. Inventory presence is not successful reproduction. |
| vendor:typesafe-router | typed model routing | source-only for this benchmark; no new run evidence | False | typed model routing |

## 边界与下一步

- 76个外部源码目录全数列入JSON，含逐文件路径；它们不是76项成功复现。
- AILS-II和SISR是下一批成熟CVRP集成优先项；需要构建、种子控制、时间/可行解流适配再公平比较。DR-ALNS、RouteFinder、RL4CO还需冻结模型/检查点及尺度适配。
- HGS-CARP/HGS-TDCARP是弧路径问题；不能当成HGS-CVRP。当前树未定位独立HGS-CVRP实现，不以PyVRP0.14冒充。
- NN/Sweep可能在车辆上限下无解，必须保留失败分母；多起点同预算内不保证每个起点都执行。
- 旧报告/原源码快照保留，新增原始结果另存；不混用连续欧氏与EUC2D，不混用固定车数与标准CVRP。
- 每条精确证据路径、126份报告扫描索引及全部vendor文件路径见algorithm_inventory.json。
## 新增种群算法的冻结定义

三者均为透明教学级新适配，不冒充原论文复现或此前连续函数实验。客户按(random-key, customer-ID)升序解码，固定顺序Split用整数EUC2D及容量约束，超过K时执行≤K分层DP。种群20，初始key均匀[0,1]。只读问题坐标/需求/容量/K/seed/预算，不读参考解或参考成本。配置冻结后不因结果调参。

- GA：3元锦标赛，逐位0.5均匀交叉，逐位1/n均匀重置变异，保留1个精英。
- PSO：惯性0.7298，个体/群体系数均1.49618，速度截断±0.2，位置截断[0,1]；每轮固定该轮全局最佳。不是宣称逐字复现1995论文。
- DE：rand/1/bin，F=0.5、CR=0.9，强制至少1维变异，位置截断[0,1]，≤接受。实现为顺序原位/异步更新，不是整代同步版本。
- Split使用易审计的二次DP及必要时车辆维度DP，不是文献线性时间实现；仅保证给定排列的最优切分。

主要定义来源：[Split](https://arxiv.org/abs/1508.02759)、[DE原论文](https://doi.org/10.1023/A:1008202821328)、[PSO原论文](https://staff.washington.edu/paymana/swarm/kennedy95-ijcnn.pdf)。独立校验覆盖1080个小排列/车辆上限问题，逐一与全部切割枚举最优值一致；该测试不是正式CVRPLIB性能结果。

随机键编码来源：[Bean 1994](https://doi.org/10.1287/ijoc.6.2.154)。这里借用编码思想，GA算子及参数以本工程冻结定义为准，不称Bean算法逐字复现。

## Cohort B 源码接入核查（独立于已冻结17配置）

- AILS-II：已读Java入口、配置与Solution。-best参与提前停止，禁止传BKS；默认0不可被报告为已知最优值。默认new Random()未暴露种子；CLI只输出成本/进度，需完整路线输出与初始化incumbent。JRE21存在，javac当前不在PATH。适配前须检查全部随机源和车辆上下界，不替换算法本体。
- SISR：16个CVRP源码/配置/许可证已恢复，Apache2许可。g++可用，cmake未在PATH，可直接等价编译。原构造以random_device初始化，CLI没有seed/deadline；只在完整迭代结束后saveJson。须添加透明种子及incumbent观测接口，保留原迭代温度日程；退出/计时由独立主管管理。ProblemInstance使用float中间dx/dy，需逐边验证与统一整数EUC2D一致，否则不能混入同一榜单。
- 上述两个属于可适配成熟CVRP源码，不是“不适用”，也尚不能标为已经完成公平运行。编译及数值测试安排在正式17配置计时窗口外，不用背景重载污染算法时间比较。


## Cohort B 技术验收更新

AILS-II与SISR均已编译，toy完整路线验证通过；全部12个X实例整数距离逐边验证一致。AILS首次toy越界保留，采用公开参数varphi=min(40,n)修复（X12不改变默认40）。现有JVM内置编译器模块，无需安装JDK。两者正式120槽另立cohort、尚未运行，不能与17项主批混写完成状态。

Cohort B 已独立复核并冻结120行计划：seed0云端24行，seed1–4本地96行。正式执行由主批结束后的独立窗口安排；源码交付包不含二进制/JDK，具体命令见 cohort_b/README.md。此状态不等于正式120行已完成。
