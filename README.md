# URP

面向农业机器人任务的路径规划算法库与智能推荐研究。**给导师看当前成果与证据，先读 [导师查看：课题、现状与证据](docs/导师查看.md)**（2026-10-19）。这份现状索引区分已做成的算法基线、系统闭环、仿真代理与仍未证实的推荐收益；历史报告按各自日期保留。

## 使用与研究入口

启动、停止、恢复及演示的唯一操作说明见 **[工作台使用说明](setup/README.md)**；逐场实际验收见 [集成报告](setup/2026-10-15/integration/REPORT.md)顶部，不能把旧报告的通过当作当前提交的新验收。

**[CVRP 冻结基线](experiments/baselines/cvrp/README.md) · [算法库登记](algorithm_inventory.md) · [归档重审](protocol/audits/20261017/README.md) · [下一阶段](docs/下一阶段.md) · [按需取用](docs/按需取用.md)**

项目包含源码、论文精读、论文原文、教材、算例和实验原始记录。来源与存储范围见 [storage.json](storage.json)；本机依赖、运行数据库和大轨迹按 `.gitignore` 留在本地，Git 同步源码、可复现实验协议与验收摘要。

工作台保留农业任务地图、规划与 Gazebo 物理仿真；实际执行限已适配的同构差速车，采用串行任务预约。CVRP 数值任务在同一服务的 `#/jobs`，BPP 历史结果在 `#/bpp`，但数值任务与农业工作台是不同实验通路。CVRP 基准的访问顺序和未标定 XY 坐标不能直接当作米制机器人轨迹。

既有 CVRP 主计划包含 **4505 项终态**（4316 可行、189 无有效解），分母不因 53 问题来自 51 底本而改变；vendor120、接手验收和页面新任务分别记账。[重审](protocol/audits/20261017/README.md)保留路线质量结果，但把未完成归档主机/环境核验链的记录排除出“已验证同条件耗时比较”；这些记录并非无数据。当前 120 例学习选择器的测试尚无相对固定 PyVRP 的收益，见 [导师查看](docs/导师查看.md)。原始归档不被新工程验收改写。

| 内容 | 入口 |
|---|---|
| 论文精读与研究分析 | [literature](literature/README.md) · [综合分析](literature/综合分析.md) |
| 实验报告、源码和结果 | [experiments](experiments/README.md) · [实验目录](experiments/目录.md) |
| 研究实现与软件 | [src](src/README.md) |
| 外部论文代码 | [代码目录](src/repos/README.md) |
| 论文原文 | [papers](papers/README.md) |
| 老师指南、学习手册和项目材料 | [materials](materials/README.md) |
| 输入、算例与记录包 | [data](data/README.md) |
| 项目文档与当前交付索引 | [docs](docs/README.md) |
| 云端工程改动及其历史验证范围 | [2026-10-17 系统审查](docs/20261017-system-review.md) · [Jobs API](src/backend/docs/JOBS_API.md) |

## 本机启动

```sh
bash setup/run.sh lab --open
```

打开农业机器人路径规划工作台（http://127.0.0.1:4100）：任务地图、算法建议与对比、独立验算、已适配方案的 ROS 2 / Gazebo 执行与导出都在此入口。**推荐可运行不等于推荐有收益，仿真通过也不等于真实农机作业通过。**具体步骤及前提见 [工作台使用说明](setup/README.md)。[src/checks.json](src/checks.json) 保存 2026 年 10 月 10 日的历史检查记录。
