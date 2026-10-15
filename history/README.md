# 历史实验

本目录汇总已有实验，供算法接入、结果引用和中期材料整合使用。原始代码、数据、结果和报告沿用仓库原路径，不重复复制。

- [成果摘要](成果与边界.md)：代表性结果、实验条件和引用范围。
- [完整实验索引](experiment_groups.md) / [CSV](experiment_groups.csv)：160 个结果目录或归档、9 个规范数据组，共 169 个取用单元。
- [原实验目录](../experiments/目录.md)：按研究方向查阅报告。
- [接入说明](接入说明.md)：算法入口、数据导入和环境恢复。
- [资产清单](inventory_summary.json) / [文件清单](manifests/)：7,274 项研究资产的路径、大小和 Git 对象标识。
- [失败记录](../experiments/failures.md) / [勘误](../experiments/research_corrections.md)：随结果保留，引用时一并核对。

## 与本轮 CVRP 基线的关系

历史结果与本轮新实验分开记录。此前已完成公共 CVRP 小规模与大 X 算例基线、VRPTW、农业路径、装箱和基础优化等实验；本目录提供它们的原始入口。本轮统一协议下的算法比较以分支主入口及新结果为准，不将不同预算、硬件或任务合同的旧结果直接并入新排名。

## 版本与范围

历史底本：`50b3b2c2cc7377e1f13dcaeebce09abf5619dbf8`。交付分支：`cvrp-baselines`。

索引覆盖底本中的全部结果分组，并整理 126 份研究报告。169 是取用单元数，不是独立实验次数；共享对照、增量实验与重分析按原报告解释。归档内的代码和结果从原包取用。外部代码见 [来源清单](vendor_sources.csv)，其收录状态不代表复现完成。

Drive 与 Git 的 experiments 目录共 1,079 个文件，路径和记录大小一致，核对记录见 [source_reconciliation.json](source_reconciliation.json)。本目录没有重新执行历史实验，也不包含底本之外的本机开发改动。

完整检出后运行 `python history/verify_assets.py` 可核对清单中的文件与 Git blob 标识。该检查用于资产完整性，不替代实验复现。
