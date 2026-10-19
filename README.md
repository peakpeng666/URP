# URP

面向农业机器人任务的路径规划算法库与智能推荐研究。

项目已建立 CVRP 算法基线，并实现限定车型和场景下的规划、独立验算、物理仿真与结果导出。当前进展、主要结果和待完成工作见 [导师查看：课题、现状与证据](docs/导师查看.md)（2026-10-19）。

## 使用与研究入口

启动、停止、恢复和演示步骤统一见 [工作台使用说明](setup/README.md)；逐场验收结果及其对应版本见 [集成报告](setup/2026-10-15/integration/REPORT.md)顶部。

[CVRP 冻结基线](experiments/baselines/cvrp/README.md) · [算法库登记](algorithm_inventory.md) · [归档重审](protocol/audits/20261017/README.md) · [下一阶段](docs/下一阶段.md) · [按需取用](docs/按需取用.md)

项目包含源码、论文精读、论文原文、教材、算例和实验原始记录。来源与存储范围见 [storage.json](storage.json)。Git 同步源码、可复现实验协议和验收摘要；本机依赖、运行数据库和大轨迹按 `.gitignore` 保留在本地。

## 工作台与实验

农业工作台支持任务地图、路径规划和 Gazebo 物理仿真。实际执行目前限于已适配的同构差速车，多车任务采用串行预约。

同一服务的 `#/jobs` 提供 CVRP 数值任务，`#/bpp` 展示 BPP 历史结果。它们与农业工作台分别执行、验算和记录。CVRP 基准记录访问顺序和未标定 XY 坐标，机器人执行所需的米制轨迹须另行生成与验证。

CVRP 主计划共 **4505 项终态结果：4316 项可行，189 项无有效解**。53 个问题来自 51 个底本，统计仍以 53 个问题计；vendor120、接手验收和页面新任务各自记账。

[归档重审](protocol/audits/20261017/README.md)保留了路线质量结果。部分记录尚缺完整的主机与环境核验链，其耗时可作描述性汇总，暂不纳入已验证的同条件耗时比较。当前 120 例选择器实验中的 30 例测试集相对固定 PyVRP 的平均收益为 0，详见 [导师查看](docs/导师查看.md)。历史实验结果与后续工程验收分别保留。

| 内容 | 入口 |
|---|---|
| 论文精读与研究分析 | [literature](literature/README.md) · [综合分析](literature/综合分析.md) |
| 实验报告、源码和结果 | [experiments](experiments/README.md) · [实验目录](experiments/目录.md) |
| 研究实现与软件 | [src](src/README.md) |
| 外部论文代码 | [代码目录](src/repos/README.md) |
| 论文原文 | [papers](papers/README.md) |
| 老师指南、学习手册和项目材料 | [materials](materials/README.md) |
| 输入、算例与记录包 | [data](data/README.md) |
| 项目文档与交付索引 | [docs](docs/README.md) |
| 系统审查与接口说明 | [2026-10-17 系统审查](docs/20261017-system-review.md) · [Jobs API](src/backend/docs/JOBS_API.md) |

## 本机启动

```sh
bash setup/run.sh lab --open
```

工作台地址：http://127.0.0.1:4100。任务地图、算法建议与对比、独立验算、已适配方案的 ROS 2 / Gazebo 执行和导出均从此进入。

推荐收益仍需实验验证；现有物理执行证据限于仿真环境，真实农机作业效果尚未验证。启动前提和操作步骤见 [工作台使用说明](setup/README.md)。[src/checks.json](src/checks.json) 保存 2026 年 10 月 10 日的历史检查记录。
