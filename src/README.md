# 源码

| 目录 | 当前内容 |
|---|---|
| [research](research/README.md) | 父代选择、CVRP选择与CRC、转弯mode及NAS研究CLI；生成执行组件 |
| [backend](backend/README.md) | 本地实验包导入、SQLite记录、附件、比较、路线API；持久化CVRP任务与独立验算 |
| [frontend](frontend/README.md) | 实时路径任务和实验档案；保留BPP结果、回放、选择解释与证据面板 |
| [robotics](robotics/README.md) | 官方TurtleBot 4入口、版本预检、route-scene显示、控制反馈与验收合同 |
| [repos](repos/README.md) | 75个外部论文代码目录及来源清单 |

从URP根目录运行：

```sh
bash tools/setup.sh --extra solvers
bash src/start.sh bootstrap
bash src/start.sh build
bash src/start.sh frontend       # 127.0.0.1:4173
bash src/start.sh backend        # 127.0.0.1:4180
```

工作台：`http://127.0.0.1:4173/#/jobs`。每次页面任务保留独立身份和真实验算状态；不是正式基线批次。

全项目工程检查：`bash src/start.sh check`。当前源码的检查及实际边界见[本轮审查](../docs/20261017-system-review.md)；`checks.json`继续保留原日期的历史记录。

数据位于[../data](../data/README.md)。前端的`inputs`、`research`、`public/data`和后端的`packages`通过相对链接访问同一份数据。根目录的`pyproject.toml`、`uv.lock`固定新的工程环境，前端继续使用自身的`package-lock.json`；历史实验环境锁文件保留原样。默认运行数据库位于`.local-state`，历史数据库首次使用时仅作只读备份。

[下一阶段](../下一阶段.md) · [检查记录](checks.json) · [来源记录](sources.json)。
