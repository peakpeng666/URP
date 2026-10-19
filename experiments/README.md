# 实验

**[CVRPLIB 当前入口](CVRPLIB入口.md) · [当前进度](状态.md) · [实验目录](目录.md) · [已知问题](failures.md) · [科研勘误](research_corrections.md) · [老师要求与成果](../materials/学习/老师要求与进度.md)**

CVRPLIB 当前结果见[当前入口](CVRPLIB入口.md)和[17 配置基线](baselines/cvrp/README.md)。冻结主计划为 17 配置 × 53 问题 × 5 种子，共 4505 项：4316 项独立验算有效，189 项无有效解。53 问题对应 51 个坐标需求底本，小、中、大规模分别为 41、6、6 例。补充批次单独统计，历史目录保留各时点的结论。

| 目录 | 内容 |
|---|---|
| [reports](reports/README.md) | 按研究问题组织的研究报告 |
| [results](results/) | 对应源码、输入、原始结果与权重 |
| [provenance](provenance/README.md) | 原包来源与审计证据 |

基础组件位于 `results/组件`；独立实验按问题分组。新实验使用 `runs/<run_id>` 保存配置、候选和原始输出，结果写入对应主题报告。

原包身份、来源 ID 和字节核验见[来源核验清单](provenance/reconciliation.json)。

