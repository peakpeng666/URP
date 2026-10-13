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
| `configs/` | 输入清单、哈希和依赖 |

完整结果在[experiments](../../experiments/README.md)。恢复数据使用`../../data/research`，新运行输出使用`../../experiments/runs/<run_id>`。多问题生成循环尚待接通，见[下一阶段](../../下一阶段.md)。
