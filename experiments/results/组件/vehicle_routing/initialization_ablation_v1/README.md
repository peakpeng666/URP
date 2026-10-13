# PyVRP 初始化策略消融：默认随机 vs savings warm-start

**288/288 次主运行与 288/288 次完整重放都可行且满足预算。Warm-start 消除了此前观察到的四个 n200 默认配置劣势，但它并非在所有实例上更好。**

本轮由前一开发实验的排序反转所启发，复用同一批 24 个开发实例（n=50/100/200，各分布/规模 4 个）和三 solver seeds。它是明确的探索性追问，不是独立确认或最终测试。正式 holdout 未触碰。

## 主结果与重放

先对每个实例平均 3 seeds，再等权汇总 24 个基础实例。正值表示 warm-start 路线更短。

| CPU 上限 | warm 相对 random 的平均距离下降 | 中位数 | 更好 / 相同 / 更差（实例） | 重放平均下降 |
|---|---:|---:|---:|---:|
| 0.25 s | 0.2595% | 0.0980% | 17 / 3 / 4 | 0.2492% |
| 1.00 s | 0.0997% | 0.0000% | 10 / 7 / 7 | 0.0846% |

两个预算下各有 2 个实例的 warm/random 方向在重放中改变；0.25 s 的合计计数相同也不等于逐实例方向全相同。1 s 重放的更好/相同/更差为 8/7/9，说明小幅近似平局会受计时截断影响；不能把总体平均优势说成逐实例支配或严格确定性。

### 关键的 uniform n200 四个实例

| 与前轮保存的 VND 原始距离比较 | 0.25 s 平均距离下降 | 四个实例的结果 |
|---|---:|---|
| 本轮默认 random PyVRP | −0.6238% | 四个均更差 |
| 本轮 savings-warm PyVRP | +0.5252% | 四个均更好 |

Warm 相对 random 在该组直接平均改善 1.1412%。全 24 实例的 warm 输出也均优于前轮 VND 保存的 seed 均值，0.25/1 s 的平均距离降幅分别为 1.8851% / 2.3289%。这是**跨批次的历史路线质量对照**，不是同批实时成本对照。重放仍保持该四例的 warm/VND 反转。

因此，此前那四个病例的“VND 与默认 PyVRP 互补”不能直接当成强固定库的稳定互补性：更强的初始化策略就去除了这组观察到的劣势。但这也不证明一般互补性不存在，更不证明 warm 普遍更优。需要另行冻结的新实例复验。

## 到底改变了什么

两组均使用官方固定 PyVRP 0.14.0、相同 ILS 参数、相同整数距离精度 10^6、罚项尺度、车队与预算：

- random：公开 API 的 initial_solution=None，执行库默认随机初始化及其初始局部搜索
- warm：使用原 savings 构造法，先由独立 checker 验证完整可行解，再以公开 Solution(data, client_index_lists) 传给公开 pyvrp.solve

没有修改/patch 上游内部代码。v0.14 客户编号不含仓库，原客户节点 k 显式转为 k−1。预检验证了 forced-singleton、已知微型最优、零迭代直接返回供应的完整 warm 路线，以及六个固定工作量下新 random 调用路径与旧 Model.solve 路径完全一致。

这是**完整初始化策略的消融**。默认随机分支会消耗 RNG 并执行初始 exhaustive local search，提供 Solution 会跳过该分支；相同 seed 不代表后续扰动轨迹完全相同。因此不能把效果纯粹归因于初始路线几何质量。

## Warm-start 不是免费信息

Savings 构造、原坐标独立验收、模型构建、索引转换、库解构造、搜索和输出重算，都在 solver CPU 时钟之内。

- 主批 warm 构造 CPU 平均 **9.826 ms**，范围 1.270–26.307 ms
- 独立 warm 验收 CPU 平均 **0.109 ms**
- 这些是 solver CPU 的子阶段，不能再与 solver CPU 相加重复计费

| 配置 | CPU 上限 | 平均 solver CPU | 平均完整子进程 CPU | 平均单次调用 wall |
|---|---:|---:|---:|---:|
| random | 0.25 s | 0.2351 s | 0.3522 s | 0.3537 s |
| warm | 0.25 s | 0.2354 s | 0.3535 s | 0.3551 s |
| random | 1.00 s | 0.9853 s | 1.1029 s | 1.1046 s |
| warm | 1.00 s | 0.9856 s | 1.1056 s | 1.1074 s |

全部主/重放调用在共同 20 ms 返回余量附近停止，没有达到 100 万次迭代安全上限，也没有实际 CPU/wall 超额。完整 worker wall 上限仍为 1/3 s，包含解释器启动、导入和退出。预算上限不是实际成本，初始化代码也并非零成本。

## 不丢失初始 incumbent 与目标口径

每个 warm 记录保存其起始完整路线、原始成本、整数成本和内部验证标志。输出必须满足整数目标不差于该可行 warm 起点；主/重放共 **288/288 个 warm 记录**均独立通过起点可行性、整数目标与 incumbent 上界检查。

最终评分仍是原坐标的未取整欧氏距离。整数代理与原目标的细小差异受显式误差界约束；整数不退步不代表界内极小原目标变化也严格不退步。全部 **576/576 个最终输出**通过整数目标求和、原始误差界、车队/罚项检查，最大代理换算误差为 1.0883×10^-5 坐标单位。

## 验证、证据及成本

- 9 个新预检测试全部通过；包括非法 warm 解在进入库前被拒绝、零迭代路线/整数成本恒等、固定工作量控制回归、单客户索引/车队边界和收费检查
- 288 保存路线全部重验；CSV/JSONL/JSON、预冻结顺序、统计重算、源码/快照、依赖和全部旧实验文件哈希均一致
- 完整重放 **267/288** 条路线与成本精确一致，21 个计时差异都保留完整原始输出，没有替换主记录或挑优
- 主批 wall **210.409 s**，父加完整子进程 CPU **213.355 s**
- 重放 wall **210.539 s**，父 CPU **3.595 s**、完整子 CPU **209.949 s**
- 两批合计 wall **420.948 s**、父加子 CPU **426.899 s**；576 调用仍对应 24 个基础实例

安装、预检、冻结、最终聚合写盘、分析、独立审查、助手/人工和平台费用在这些 batch 时钟之外，未被当作免费。没有实验侧模型或付费 API，没有新安装依赖。只验证当前云环境。

完整记录位于 [runs/dev_20261004_01/](runs/dev_20261004_01/)：`freeze.json`、`source_snapshot/`、`raw.jsonl`、`raw.csv`、`results.json`、`summary.json`、`replay_raw.jsonl`、`verification.json`、`analysis.json`。所有新旧路线均保存，源数据仍引用原 scale study 的哈希一致文件。

## 复现

在 `URP/experiments/vehicle_routing`，复用已固定的官方 PyVRP 环境：

```bash
.venv-pyvrp-0.14.0/bin/python -m unittest initialization_ablation_v1.test_ablation -v
.venv-pyvrp-0.14.0/bin/python -m initialization_ablation_v1.experiment run --output initialization_ablation_v1/runs/my_new_run
.venv-pyvrp-0.14.0/bin/python -m initialization_ablation_v1.experiment verify --output initialization_ablation_v1/runs/my_new_run
.venv-pyvrp-0.14.0/bin/python -m initialization_ablation_v1.analyze_results initialization_ablation_v1/runs/my_new_run
```

输出和重放文件拒绝覆盖。生成入口被禁用，因为本轮必须复用相同实例。依赖二进制/venv/cache 不交付；版本、wheel hashes 与许可证沿用成熟求解器阶段记录。

本轮仅比较同一求解器的两种初始化策略，不增加独立算法家族。尚无实际 selector、完整策略净收益、生成成员 P3/P5 实验、最终双轴 holdout 或农业约束，不能声称 H1/H2 已通过。
