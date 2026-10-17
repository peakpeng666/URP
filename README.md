# URP

面向农业机器人的路径规划算法库构建与智能推荐研究。项目把算法、独立验算、实验档案与仿真接口放在同一套可追溯工作流中。

**[2026-10-17 系统审查与改进](docs/20261017-system-review.md) · [CVRP 算法库与既有基线](experiments/baselines/cvrp/README.md) · [全记录重审](protocol/audits/20261017/README.md) · [现成仿真入口](src/robotics/docs/UPSTREAM_REFERENCE.md)**

## 当前能做什么

| 部分 | 已有功能与证据范围 |
|---|---|
| 路径任务工作台 | 导入 CVRP 数值任务，真实排队执行、独立验算、查看路线和成本，刷新恢复任务身份，导出完整记录，分页查看全部状态 |
| 本地后端 | SQLite 持久化、5 个受控算法入口、失败和强制退出恢复、场景版本冲突检测；查询历史实验、附件和版本化 route-scene |
| 算法库与历史实验 | 17 个配置、53 个 CVRPLIB 问题定义、51 个基础坐标/需求实例，4,505 个计划任务；另有独立的 120 项补充对照 |
| BPP 历史结果 | 原有静态结果、样本、逐步回放、风险与证据页面继续可用 |
| 仿真接入 | 官方 TurtleBot 4 Humble 1.0.3 固定版本入口、依赖预检、严格场景合同和验收判定；本轮环境未运行 ROS/Gazebo 物理任务 |

前端的 `savings / T / TRS / TSR / pyvrp` 是工程验证入口。其余配置保留在研究 CLI；每次页面提交都独立记账，不自动并入正式基线。数学可行解和 XY 访问顺序不代表米制地图中的可行驶路线。

## 启动工作台

工程执行环境使用 Linux、Python 3.12、Node.js 24 和 uv 0.12.23。第一次安装依赖需要联网；依赖和数据就绪后，本地任务服务无需云端模型。

```sh
bash tools/setup.sh --extra solvers
bash src/start.sh bootstrap       # 幂等导入仓库内的 5 个通用实验包
bash src/start.sh build
```

再开两个终端：

```sh
bash src/start.sh backend         # http://127.0.0.1:4180
bash src/start.sh frontend        # http://127.0.0.1:4173
```

打开 **http://127.0.0.1:4173/#/jobs**，点击“运行并独立验算”即可提交页面中的工程示例。开发时可把 `frontend` 换成 `dev`；BPP 原入口 `#/` 保持可用。

默认运行库为 `.local-state/research.sqlite3`。首次启动若发现历史 `data/backend/research.sqlite3`，先只读备份到独立运行库；已有运行库绝不被替换。`URP_API_DB` 可显式指定运行库，`URP_API_PORT` 可改后端端口，`URP_PYTHON` 可指定解释器。前后端都要使用同一个 `URP_API_PORT`。可从任意当前目录调用 `src/start.sh` 的绝对路径。

## 研究结果如何引用

2026-10-17 对原始压缩包的全记录重审保留了 **4,316 项可行、189 项失败、0 项未启动** 的结论。共 4,509 次记录尝试中，4 次基础设施中断作为额外尝试保留，不能重复进入 4,505 的计划分母。53 份参考解和原始坐标/路线已独立复算。

**主机证明链不完整的结果只能保留相应质量描述，不能继续视为已验证的同机耗时对照。** 新审计中，已验证同机同资源批次、相同算例/种子的差距配对行从 31,512 降为 6,618，overall 层算法 × 资源批次的 CPU 均值组从 89 降为 17；区别、依据和复查命令见[更正说明](protocol/audits/20261017/README.md)。原报告、压缩包和历史索引保留，不把新的工程环境冒充原实验环境。

## 工程检查与资料入口

```sh
bash src/start.sh check
```

每次检查写入新的 `.local-state/checks/` 子目录，保留所有通过、失败、日志哈希与明确未执行项。CI 使用同一入口。它覆盖项目自有实现和冻结 BPP 数据读回；不重跑所有历史优化实验，也不代表 75 个外部论文项目或机器人硬件全部验收。

| 内容 | 入口 |
|---|---|
| 实现、运行与接口 | [src](src/README.md) · [Jobs API](src/backend/docs/JOBS_API.md) · [前端](src/frontend/README.md) |
| 当前基线与历史目录 | [CVRPLIB 当前入口](experiments/CVRPLIB入口.md) · [历史实验总览](history/README.md) |
| 研究验收要求 | [研究结果验收](src/research/docs/RESEARCH_ACCEPTANCE.md) · [下一阶段](下一阶段.md) |
| 论文与外部代码 | [literature](literature/README.md) · [papers](papers/README.md) · [75 个外部项目](src/repos/README.md) |
| 任务材料和数据 | [materials](materials/README.md) · [data](data/README.md) · [来源记录](storage.json) |

本轮改动与新证据以本 Git 分支为准；其他位置的历史副本不代表已同步本轮改进。


