# CVRPLIB 算法库与基线实验

本轮按老师要求，用经典CVRPLIB小、中、大规模及不同分布算例比较基础算法，再据结果选择后续改进方向。

## 入口

- [基线实验报告](results/基线实验报告.md) · [图表](results/figures/) · [逐项结果表](results/runs.csv) · [机器可读汇总](results/summary.json)。
- [使用说明](使用说明.md)：列出算法与算例、单例求解、独立验算、复现和汇总。
- [当前17配置](算法清单.json)：本轮有效入口；17个配置不等于17个独立算法家族。
- [算法全量来源](../../../algorithm_inventory.md)：已有实现、适配与补充算法的来源及边界。
- [冻结实验计划](../../../protocol/formal_plan.json) · [实验协议](../../../protocol/基线实验协议.md) · [执行分工](../../../protocol/execution_allocation_amendment.md)。
- [原始结果包](raw/) · [独立审查证据](evidence/) · [历史实验](history/)。

源码仍在 src/research，标准输入仍在 data/benchmarks/CVRPLIB。运行入口为仓库根目录下 scripts/baseline.py，避免重复维护两套算法。src/research/configs/cvrplib_algorithms.json是早期五项准入的历史记录；本轮17配置以当前清单和冻结计划为准。

## 范围与状态

主实验为53个问题、51个底本，17配置、5个种子/计时重复、每项5秒，共4505项。云端seed0/2共1802项、本机seed1/3/4共2703项已完整汇总：4316项独立验算可行，189项无有效解，无未启动项。共4509次尝试：其中4次本机基础设施中断各重试一次，中断证据保留，不增加计划项分母。

补充vendor对照120项已全部完成并独立审计：120项可行、无重复、无审计错误。见[补充汇总](native-summary.json)、[逐项记录](native-runs.csv)、[独立审计](evidence/vendor_all120_audit.json)。该对照不混入主4505项分母。

2026-10-16 李月莹在更早提交 `50b3b2c` 上另交了一份 5 算法验收包（标记 acceptance_only，PyVRP 种子 0–9，5 秒端到端）。另有沿用原 16 例输入的 1 秒搜索循环两批。两套计时分开，都不混入上面的 4505 项，也不签收 G5。核验与原始压缩包位置见 [handoff/20261016-liyueying](handoff/20261016-liyueying/核验与接手.md)。

质量按主机和资源批次分别统计；合并质量仅作异构条件描述，不跨硬件排名速度。确定性算法的重复不是独立随机搜索。GA/PSO/DE随机键+Split属于本轮标准教学适配，不冒称历史CVRP复现。

## 快速命令

在仓库根目录、已安装requirements.lock依赖的Python环境中运行：

    python scripts/baseline.py algorithms
    python scripts/baseline.py cases
    python scripts/baseline.py run --case A-n32-k5 --algorithm pyvrp --seed 0 --budget 5 --name demo-01

新调用只写独立user-runs目录，不覆盖本轮正式结果。完整4505项新复现使用reproduce子命令，默认只显示命令，明确加--execute才启动。
