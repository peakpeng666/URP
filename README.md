# URP

面向农业机器人的路径规划算法库构建与智能推荐研究，以老师的LLM自动算法设计指南为主线。

## 本机使用

科研面板、二维路线与 ROS 仿真的统一入口见 **[本机使用说明](setup/README.md)**；实际测试结果见 [集成验收报告](setup/2026-10-15/integration/REPORT.md)。

**[CVRP 基线与算法库](experiments/baselines/cvrp/README.md) · [历史实验重审](protocol/audits/20261017/README.md) · [CVRPLIB 当前入口](experiments/CVRPLIB入口.md) · [下一阶段](docs/下一阶段.md) · [按需取用](docs/按需取用.md)**

项目包含源码、论文精读、论文原文、教材、算例和实验原始记录。来源与存储范围见 [storage.json](storage.json)；本机依赖、运行数据库和大轨迹按 `.gitignore` 留在本地，Git 同步源码、可复现实验协议与验收摘要。

工作台保留农业任务地图、规划与真实 Gazebo 仿真；GitHub 分支的 CVRP 数值任务已接在同一入口的 `#/jobs`，BPP 历史结果为 `#/bpp`。CVRP 基准的访问顺序和未标定 XY 坐标不能直接当作米制机器人轨迹。

既有 CVRP 计划包含 4,505 项终态（4,316 可行、189 无有效解），与新页面任务分别记账；[重审](protocol/audits/20261017/README.md)保留质量结果，但将缺乏主机证明链的记录排除出已验证的同机耗时比较。原始归档不被新工程验收改写。

| 内容 | 入口 |
|---|---|
| 论文精读与研究分析 | [literature](literature/README.md) · [综合分析](literature/综合分析.md) |
| 实验报告、源码和结果 | [experiments](experiments/README.md) · [实验目录](experiments/目录.md) |
| 研究实现与软件 | [src](src/README.md) |
| 外部论文代码 | [代码目录](src/repos/README.md) |
| 论文原文 | [papers](papers/README.md) |
| 老师指南、学习手册和项目材料 | [materials](materials/README.md) |
| 输入、算例与记录包 | [data](data/README.md) |
| 项目文档与目录维护 | [docs](docs/README.md) |
| 云端工程改动及其历史验证范围 | [2026-10-17 系统审查](docs/20261017-system-review.md) · [Jobs API](src/backend/docs/JOBS_API.md) |

## 本机启动

```sh
bash setup/run.sh lab --open
```

打开农业机器人路径规划工作台（http://127.0.0.1:4100）：一句话生成任务地图、编辑、推荐算法、多车对比、验算，以及在 Gazebo 田间世界里让多车经 ROS 2 执行方案，都在这里，详见 [本机使用说明](setup/README.md)。[src/checks.json](src/checks.json) 保存 2026 年 10 月 10 日的历史检查记录。
