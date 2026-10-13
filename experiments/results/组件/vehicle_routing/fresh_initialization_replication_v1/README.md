# 新实例定向复验：初始化收益能否复现？

**600/600 次主运行均可行且满足预算；新均匀实例支持 warm-start 的收益，但旧“四例默认版全败”的排序模式并未原样泛化。**

本轮先冻结生成计划，再生成 20 个全新 n=200 开发实例：10 个 uniform、10 个 clustered，generation seeds 2026100800–2026100819。每实例使用 5 个 solver seeds（11/29/47/71/97），比较 VND、默认 random PyVRP、savings-warm PyVRP，分别给 0.25/1.0 s solver CPU 上限，共 600 次。实际独立基础实例是 20 个，不是 600 个。

算法、预算、返回余量、初始化 API、量化规则均复用已审查版本，没有根据这批新结果调参。正式最终 holdout 未读取、生成或评测。该复验由前面的开发观察引出，仍是定向开发研究，不是正式最终盲测。

## 主结果

先平均同一实例的 5 seeds，再对 20 个实例等权汇总原始未取整距离。

| 比较 | solver CPU 上限 | 平均距离下降 | 更好 / 相同 / 更差（基础实例） |
|---|---:|---:|---:|
| random PyVRP 相对 VND | 0.25 s | 0.6170% | 14 / 0 / 6 |
| warm PyVRP 相对 VND | 0.25 s | 1.0052% | 19 / 0 / 1 |
| warm 相对 random PyVRP | 0.25 s | 0.3884% | 18 / 0 / 2 |
| random PyVRP 相对 VND | 1.00 s | 1.5394% | 20 / 0 / 0 |
| warm PyVRP 相对 VND | 1.00 s | 1.7019% | 20 / 0 / 0 |
| warm 相对 random PyVRP | 1.00 s | 0.1640% | 16 / 0 / 4 |

每行有自己的分母，不能把这些相对降幅直接相加。两个 PyVRP 初始化方式属于**同一个成熟求解器家族的配置**。

### 分布差异与必须保留的限制

在 10 个新 uniform 实例上：

- 0.25 s 的 random vs VND 是 **5 胜 / 5 负**，平均距离反而短 0.1410%；因此旧四例“random 全比 VND 差”的模式没有普遍复现
- warm 在 0.25 s 对 random 和 VND 都是 **10/10 个实例均值更好**；相对 random 平均短 0.6804%，相对 VND 平均短 0.8219%
- 1 s 的 warm 对 random 仍为 10/10 更好，平均短 0.3086%

在 10 个新 clustered 实例上，warm 对 random 的平均收益仅为 0.0964%（0.25 s）和 0.0195%（1 s），分别有 2/4 个实例更差；短预算下还有一个 clustered 实例由 VND 胜过 warm。不能说 warm 普遍支配，也不能说所有互补性都消失了。

合理结论是：**初始化策略确实影响这个小预算下的比较；部分收益在新同分布开发实例上复现，但具体赢家分布仍异质。** 这不足以证明 H1 的稳定强库互补性、推荐器净收益或 H2。

## 预算增长与实际消耗

从 0.25 s 增至 1 s，random/warm 的平均距离分别继续下降 0.9263% / 0.7030%，二者在 20 个实例上均有改善。VND 的平均改善仅 **0.0000355%**，只有一个 clustered 实例极小变化，不能称为有意义的预算收益；选定重放中这一微小差别也消失。

| 配置 | CPU 上限 | 平均 solver CPU | 平均完整子进程 CPU | 平均完整调用 wall |
|---|---:|---:|---:|---:|
| VND | 0.25 s | 0.2303 s | 0.2765 s | 0.2780 s |
| random PyVRP | 0.25 s | 0.2393 s | 0.3615 s | 0.3631 s |
| warm PyVRP | 0.25 s | 0.2404 s | 0.3622 s | 0.3638 s |
| VND | 1.00 s | 0.9803 s | 1.0267 s | 1.0285 s |
| random PyVRP | 1.00 s | 0.9900 s | 1.1136 s | 1.1155 s |
| warm PyVRP | 1.00 s | 0.9913 s | 1.1150 s | 1.1170 s |

所有 600 次都因 CPU 返回余量停止，没有达到 VND 的 1,000 万次 delta 或 PyVRP 的 100 万次迭代安全上限，也没有失败/预算不合格记录。所有配对统计均使用完整 20 个实例，未排除困难失败案例。

20 ms 返回余量只扣一次；初始化和 C++ 单次搜索不可被合作式 CPU 检查抢占，仍须看实际时间。完整 worker wall 上限为 1/3 s，包含解释器启动、导入、序列化和退出。Savings warm 构造、独立验收、索引转换均计入 solver CPU，没有被免费供应。

## 事先固定的小规模重放

没有对整批盲目再算一遍。生成计划和完整主顺序冻结时，同时固定：

- 每个实例按照 manifest 序号循环选择一个 solver seed，五个 seed 各被 4 个实例选中（每分布各 2 个）
- 对这个选定 instance/seed 执行全部 3 配置 × 2 预算，共 **120 次计时重放**，所有实例都有覆盖
- 再对每分布首个实例、两种 PyVRP 初始化各做两次固定 100 次迭代诊断，共 **8 次诊断调用**；其宽裕预算与成本单独记录

这些索引在任何主结果出现前已经写入 freeze，未按错误或赢家挑选。

结果：

- 120/120 选定重放可行且 in-budget，**109/120** 路线与成本精确一致
- 8/8 固定工作量诊断通过，4/4 对路线/成本精确一致，均确实完成 100 次迭代
- 计时重放中，warm/random 的选定单 seed 比较在短/长预算下分别有 2/4 个实例方向改变；对 VND 的方向没有改变
- 保留全部重放路线和差异，没有替换主记录或挑优

**单 seed 的选定重放不是“五 seed 主均值”的第二次实验。** 其作用是诊断同一选定调用的时间截断波动，不能声称未重放的 480 条主调用都严格可复现。主报告和重放诊断没有混算成新独立样本。

## 独立检查与证据

独立复核重生成了全部 20 个输入，重建了 600 主调用、平衡的 120 个选定重放和 8 个固定工作量诊断，确认生成前 freeze、源码、快照、依赖和旧实验哈希。六个新增协议/抽样/源码一致性测试通过。

- **728/728** 保存输出（主 600 + 重放 120 + 诊断 8）均通过原坐标可行性与成本重算
- **488/488** PyVRP 输出通过独立整数目标求和、量化误差界、车队及罚项检查
- **244/244** warm 起点通过独立可行性、精确复建 savings 解、整数 incumbent 不退步及子阶段收费检查
- 最大整数代理换算误差为 **1.5004×10^-5** 坐标单位，低于 n=200 的 0.0002 最保守界（另加浮点余量）
- CSV/JSONL/JSON、主调度、选定重放索引与统计重算一致；没有更改任何旧实验原始记录

这里的整数不退步只是代理目标中的约束，不能对误差界内极小原始距离变化作更强保证。主评分始终为原始未取整欧氏距离，不是直接拿整数目标除以比例充当精确得分。

## 文件与复现

- `data_plan_freeze.json`：实际生成新实例之前冻结的生成字段、generator 和 wrapper 哈希
- `data/dev/manifest.json` 与 20 个 JSON：新开发实例与正确 seed 命名空间
- [runs/dev_20261004_01/](runs/dev_20261004_01/)：完整运行目录
- `freeze.json`：主调用、选定重放、固定迭代诊断、参数、输入和源码/旧文件哈希
- `raw.jsonl`、`raw.csv`、`results.json`、`summary.json`：600 个完整主记录
- `replay_raw.jsonl`：120 个完整选定重放
- `fixed_work_diagnostics.jsonl`：8 个完整固定工作量诊断
- `verification.json`、`analysis.json`：重算与明确限定范围的诊断

在 `URP/experiments/vehicle_routing` 执行，复用已锁定的官方 PyVRP 环境，不覆盖数据或结果：

```bash
.venv-pyvrp-0.14.0/bin/python -m unittest fresh_initialization_replication_v1.test_replication -v
.venv-pyvrp-0.14.0/bin/python -m fresh_initialization_replication_v1.experiment run --output fresh_initialization_replication_v1/runs/my_new_run
.venv-pyvrp-0.14.0/bin/python -m fresh_initialization_replication_v1.experiment verify --output fresh_initialization_replication_v1/runs/my_new_run
.venv-pyvrp-0.14.0/bin/python -m fresh_initialization_replication_v1.analyze_results fresh_initialization_replication_v1/runs/my_new_run
```

此目录的已有 generation freeze 和数据拒绝覆盖。源码沿用前面已审查的 solver/runtime，第三方二进制、venv、cache 不随成果包分发。

## 成本与剩余门槛

- 主批 wall **426.922 s**，父加完整子进程 CPU **433.063 s**
- 选定重放 wall **85.511 s**，父 CPU **1.526 s**、完整子 CPU **85.223 s**
- 固定工作量诊断 wall **2.188 s**，父 CPU **0.043 s**、完整子 CPU **2.172 s**
- 三阶段合计 wall **514.622 s**，父加子 CPU **522.027 s**

完整子进程成本由 wait4 记录，包括启动和退出。输入生成、预检、冻结、最终聚合写盘、后续分析/独立审查、助手/人工及平台费用在这些计时之外，不能当作零。没有实验侧模型或付费 API。

下一步应继续加强真正不同的成熟方法对照，并检验明确冻结的实际选择策略及全成本；不靠初始化变体数量凑家族数。本轮未做 P3/P5 生成成员实验、最终任务/代码双轴 holdout 或农业约束，H1/H2 仍未完成。
