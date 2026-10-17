# 研究实现

当前CLI支持父代选择、CVRP选择与CRC、转弯服务mode的合成检查、数据恢复和结果重放，并包含NAS模块。

```sh
python3 scripts/urp.py --help
python3 scripts/test.py
```

命令从本目录执行。核心模块使用Python标准库；NAS推断与训练需要配置中的PyTorch/NumPy依赖。

| 入口 | 内容 |
|---|---|
| `src/urp_research/` | 研究模块与CLI |
| [数据恢复](docs/DATA_RESTORE.md) | 本地实验包与校验命令 |
| [NAS](docs/NAS_FIDELITY.md) | 训练保真度、重算与训练接口 |
| [生成器](generator/README.md) | 已有装箱输入与模型执行器 |
| [进程监督](execution/README.md) | 子进程回收、资源与退出状态记录 |
| [研究结果验收](docs/RESEARCH_ACCEPTANCE.md) | 路线验算、计划分母、推荐划分与失败记账 |
| `configs/` | 输入清单、哈希和依赖 |

完整结果在[experiments](../../experiments/README.md)。既有实验输入使用`../../data/research`，新运行输出使用`../../experiments/runs/<run_id>`。多问题生成循环是下一步工作，见[下一阶段](../../docs/下一阶段.md)。

## 独立 CVRPLIB 入口

真实 CVRPLIB 输入、统一端到端预算、恢复的经典基线及 PyVRP 0.14.0 ILS 位于 `src/urp_research/cvrplib/`。使用 `python3 scripts/cvrplib.py --help`，统一状态与证据见 [CVRPLIB当前入口](../../experiments/CVRPLIB入口.md)，命令详见 [验收和复现说明](docs/CVRPLIB_READINESS.md)。这不改变历史合成 CRC 回放，也不代表已完成正式 53 例多种子实验。
