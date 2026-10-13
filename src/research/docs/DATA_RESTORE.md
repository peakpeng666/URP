# 恢复与重放

从`src/research`目录执行，直接使用本地完整包。

```sh
python3 scripts/urp.py restore parent-selection --zip '../../experiments/results/搜索机制/父代选择离线回放/父代选择离线回放完整实验.zip'
python3 scripts/urp.py restore cvrp-selection-crc --zip '../../experiments/results/搜索机制/全库论文应用与两项机制验证/全库论文应用与两项机制验证_20261006.zip'
python3 scripts/urp.py restore turn-modes --zip '../../experiments/results/搜索机制/全库论文应用与两项机制验证/全库论文应用与两项机制验证_20261006.zip'
```

默认恢复到`data/research/<experiment>`。导入前检查外层/内层ZIP和白名单文件的SHA-256；已存在的目录保持原样并返回错误。来源与必要文件见[archives.json](../configs/archives.json)。

```sh
python3 scripts/urp.py verify parent-selection
python3 scripts/urp.py verify cvrp-selection-crc
python3 scripts/urp.py verify turn-modes
python3 scripts/urp.py replay parent-selection --output ../../experiments/runs/replay/parent-selection
python3 scripts/urp.py replay cvrp-selection-crc --output ../../experiments/runs/replay/cvrp-selection-crc
python3 scripts/urp.py replay turn-modes --output ../../experiments/runs/replay/turn-modes
python3 scripts/urp.py compare
```

重放输出使用新目录，默认比较根目录为`experiments/runs/replay`；可用`--data-root`、`--output-root`和`--output`指定位置。独立分发研究源码时，默认数据与输出仍在源码项目内。

比较覆盖父代4个文件、CVRP策略与校准决策、转弯36实例的路线见证与非时间指标。重新测得的运行时间单列。NAS命令见[NAS说明](NAS_FIDELITY.md)。
