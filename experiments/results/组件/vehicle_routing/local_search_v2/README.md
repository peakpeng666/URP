# CVRP 局部搜索实验 v2：计数修订后重新运行

**最新主记录：360/360 次可行且成本一致；360/360 次重放路线与成本完全一致。质量结论与保留的 v1 一致。**

24 个既有开发实例 × 5 方法配置 × 3 solver seeds。所有方法使用相同的 0.25 秒合作式 CPU 上限与 1 秒完整 worker wall 上限。旧实例、旧 pilot、v1 冻结源码与原始结果均保留。最终 holdout 没有读取、生成或评测；没有安装包、没有实验侧模型 API、没有使用用户电脑。

## 为什么另跑 v2

v1 独立复核发现 generator 提前计算一项：15 次触发 work cap 的多起点调用实际计算 100,001 个 delta，而日志记的是 100,000 次准许比较。它没有改变返回路线，实际 CPU 也已计入多算的那一步，但“计算不超过 100,000 次”的描述不准确。

v2 在读取下一个 candidate **之前**检查上限，新增对实际 yield 次数计数的回归测试，然后将相同输入、参数和执行顺序完整重跑。v1 未被覆盖，勘误见 [v1/ERRATUM.md](../local_search_v1/ERRATUM.md)。这不是挑优重跑或配置调优，也不能把两次运行合并扩大独立样本数。

## 真实配对结果

先对各基础实例的三个 solver seeds 求均值，再对 24 个实例等权平均。seed 重复不是独立实例。

| 比较 | 平均距离下降 | 中位数 | 更好 / 相同 / 更差（实例） |
|---|---:|---:|---:|
| savings + VND 相对原 savings | 0.4396% | 0.1364% | 14 / 10 / 0 |
| 多起点 VND 相对单起点 VND | 0.7124% | 0.0000% | 10 / 14 / 0 |

两行分母不同，不能直接相加。两种 VND 是同一局部搜索家族的两种配置；多起点包含单起点流程，无退步不能当作独立互补性证据。n=8 的八个实例均无提升，但这不证明它们是全局最优。

| 方法 | 平均 solver CPU | 平均完整子进程 CPU | 平均单次总 wall |
|---|---:|---:|---:|
| 最近邻 | 0.205 ms | 40.100 ms | 41.326 ms |
| 原 savings | 0.440 ms | 40.863 ms | 42.185 ms |
| seeded sweep | 0.178 ms | 39.841 ms | 41.066 ms |
| savings + VND | 1.669 ms | 42.020 ms | 43.236 ms |
| 多起点 VND | 33.163 ms | 73.854 ms | 75.255 ms |

多起点为额外 0.7124% 的开发距离收益使用约 **19.87 倍 solver CPU**。完整进程比值较小，因为解释器启动开销占比较高。没有质量/时间折算权重、实际 selector 或其净收益结论。

更细的六个分布/规模 cell 和逐实例配对数据保存在 `summary.json`，不作显著性或分布外泛化解释。

## 搜索、预算和停止

- 单起点从 savings 解开始；邻域依次为 2-opt、intra/inter relocate、inter swap、2-opt*；best improvement 后回到首个邻域
- 多起点依次使用 savings、最近邻和十个 seeded sweep 起点；保留全部起点至今最优的完整可行解
- 两种配置每次调用均共享 100,000 次 computed move-delta 上限，预算不会按起点重置
- 单起点 72/72 完成声明邻域搜索；多起点 57/72 完成全部起点，15/72 达到 work cap 后返回 incumbent
- 360 次均未遇到实际 CPU/wall 截断或自然失败；故障注入另属测试
- 使用未取整欧氏距离、无限同质车队、整数容量；不新增路线数优先或罚项

协议与参数分别见 [PROTOCOL.md](PROTOCOL.md) 和 [protocol.json](protocol.json)。这是一类透明标准局部搜索基线，不是成熟库复现，也没有完成 P3/P5 候选生成实验。

## 检查与可复现证据

- 原有 56 个 unittest 方法已通过；原日志保留于 `../local_search_v1/legacy_tests.log`
- v2 的 14 个 unittest 方法通过，见 `preflight_tests.log`；含微型已知真值/独立穷举、逐动作 delta 与完整重算比对、局部最优检查、容量/零需求/重合点、截断 incumbent、OS CPU/超时/NaN/异常、严格 work-cap 回归
- 保存后 360/360 路线重新独立验收，360/360 同 seed 路线与成本精确重放
- 216/216 原构造法输出精确复现旧 pilot
- JSONL/JSON/CSV、执行顺序、统计重算、冻结源码快照、旧数据哈希全部通过
- v1/v2 的 360 个配对结果在路线、成本、验收与 search 元数据上相同；冻结 schedule 和实例哈希相同
- 重复指定已有输出目录被拒绝，已有文件哈希未改变

完整文件位于 [runs/dev_20261004_01/](runs/dev_20261004_01/)：`freeze.json`、`source_snapshot/`、`raw.jsonl`、`raw.csv`、`results.json`、`summary.json`、`verification.json`、`lineage_verification.json`。所有原始记录保留，v1/v2 不混合汇总。

## 成本边界

v2 主批 wall **17.568 秒**，父 CPU **0.583 秒**，完整子进程 CPU **17.041 秒**，不重叠 CPU 和 **17.623 秒**。solver CPU 合计仅 **2.567 秒**，不能用它冒充整批成本。独立 replay 另计 wall **17.687 秒**、父 CPU **0.603 秒**、子 CPU **17.158 秒**。

Linux `wait4` 记录包含解释器启动、导入、校验、求解、序列化及退出的子进程 CPU，也能记录被强制结束的子进程。主批/重放分别记录；包含已保留 v1 的两版主批和重放合计为 1,440 个进程调用（不是 1,440 个独立实例）。累计可计量阶段成本见 `lineage_verification.json`，没有删掉修错重跑的费用。

上述费用不含编写/调试、预检测试、冻结、最后聚合写盘、分析和独立审稿工作，以及助手/人工/平台费用。实验侧 API 调用为 0 不等于整个研究免费。只验证了当前 Debian/Python 云环境，未验证 Ubuntu 22.04，也没有不可信代码安全沙箱。

## 复现与剩余门槛

在父目录 `URP/experiments/vehicle_routing` 执行：

```bash
python -m unittest discover -s tests -v
python -m unittest local_search_v2.test_local_search -v
python -m local_search_v2.run_experiment --output local_search_v2/runs/my_new_run
python -m local_search_v2.verify_run local_search_v2/runs/my_new_run
```

无需安装依赖；必须保留哈希一致的父目录 `data/dev` 与 `urp_cvrp`。输出和 verification 拒绝覆盖。更改算法/协议应另立修订，保留旧证据。

本次推进了局部搜索基线与完整子进程 CPU 计费。**成熟强基线门槛仍开着**：待获准安装固定成熟求解器，冻结许可证/依赖/版本，核对整数距离适配、车队语义、微型真值和预算。之后才有条件检验固定强库的稳定互补性；实际 selector、生成成员 P3/P5、完整政策费用、双轴最终 holdout 和农业约束仍未完成。不能声称 H1/H2 已验证，也不把配置变体凑成不同家族。
