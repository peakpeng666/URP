# 研究实现

当前 CLI 支持父代选择、CVRP 选择与 CRC、转弯服务 mode 的合成检查、数据恢复和结果重放，并包含 NAS 模块。本目录是实现入口，**当前成果与边界**先看 [2026-10-19 导师查看](../../docs/导师查看.md)；历史实验说明按原日期解释，不用旧状态推断正式基线尚未运行。

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

完整结果在 [experiments](../../experiments/README.md)。既有实验输入使用 `../../data/research`，新运行输出使用 `../../experiments/runs/<run_id>`。多问题生成循环仍是后续研究，不应与已完成的 CVRPLIB 主基线或已证推荐收益混称，见 [下一阶段](../../docs/下一阶段.md)。

## 独立 CVRPLIB 入口

真实 CVRPLIB 输入、统一端到端预算、恢复的经典基线及 PyVRP 0.14.0 ILS 位于 `src/urp_research/cvrplib/`。使用 `python3 scripts/cvrplib.py --help`；命令详见 [验收和复现说明](docs/CVRPLIB_READINESS.md)。**当前正式主批次已完成**：17 配置、53 问题、5 种子/重复，共 4505 项；4316 项独立验算可行、189 项无有效解，见 [基线报告](../../experiments/baselines/cvrp/README.md)和 [归档重审](../../protocol/audits/20261017/README.md)。53 问题的 51 个底本须在后续推荐实验中归组。vendor120、接手验收 742 及两批 48 项独立记账，不当作主批次追加样本。

选择器另有最新 train60/cal30/test30 实验，不能与 [较早合成 CRC 回放](docs/RESEARCH_ACCEPTANCE.md)混写；按严格成本比较，PyVRP 在训练为 51 胜 9 平、校准 23 胜 7 平、测试 27 胜 3 平，OR-Tools 0 次严格更优，测试未显示相对固定 PyVRP 的收益。当前 [冻结模型](../lab/models/cvrp-knn-v1.json)可运行，不等于已证跨预算或分布的选择收益；其评估每算法 0.25 秒、两次重复，不为工作台默认 3 秒/种子 42 背书。
