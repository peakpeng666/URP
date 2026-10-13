# 固定 PyVRP 0.14.0：成熟求解器开发对照已实际运行

**504/504 次原始调用独立验收通过；加入官方成熟求解器后，原坐标目标上相对多起点 VND 的平均距离下降为 0.4991%。**

独立复核已检查原始路线、整数目标转换、车队/罚项语义、依赖/源码哈希和统计重算。这里只完成小型开发实例上的成熟库接入与固定预算对照，尚未证明整个固定库足够强，也未验证 H1/H2。

## 样本与结果

同一批 24 个开发实例（uniform/clustered × n=8/20/40 × 每格 4 个）× 3 solver seeds × 7 配置 = 504 次。独立样本仍是 24 个基础实例。两种 VND 是同一家族的配置；两个 PyVRP 距离精度也是同一个 ILS 求解器的配置。

| 配对比较 | 平均原始距离下降 | 中位数 | 更好 / 相同 / 更差（实例） |
|---|---:|---:|---:|
| PyVRP，S=10^6，相对多起点 VND | 0.4991% | 0.0000% | 9 / 15 / 0 |
| PyVRP，S=10^9，相对 S=10^6 | 0.0000% | 0.0000% | 0 / 24 / 0 |

先平均同一实例的 3 seeds，再等权汇总 24 实例。主批两个尺度的 **72/72 个 instance/seed 对原始距离相同**；这仅说明本批未观察到尺度敏感性，不能证明整数化完全不改变一般问题。

分组平均主比较降幅：uniform n=8/20/40 分别为 0.0000% / 0.1881% / 1.7938%；clustered 分别为 0.0000% / 0.1271% / 0.8857%。每格只有 4 个实例，不报告显著性或分布外结论。

| 方法 | 平均 solver CPU | 平均完整子进程 CPU | 平均单次总 wall |
|---|---:|---:|---:|
| 原 savings | 0.390 ms | 39.963 ms | 41.285 ms |
| 多起点 VND | 33.400 ms | 74.375 ms | 75.750 ms |
| PyVRP S=10^6 | 144.516 ms | 264.417 ms | 265.836 ms |
| PyVRP S=10^9 | 145.146 ms | 263.608 ms | 265.079 ms |

主 PyVRP 使用约 **4.33 倍 solver CPU**，完整进程也更贵；0.4991% 的路线收益不能直接叫“实际 selector 净收益”。全部五个旧基线配置的 **360/360** 路线/成本精确匹配已保留的 VND v2 记录。

## 明确的目标/车队适配

- 安装并锁定官方 PyPI `pyvrp==0.14.0`，它使用 **iterated local search**，不是历史 HGS 版本
- 优化代理为 q(i,j)=floor(S·d(i,j)+0.5)，主 S=10^6，敏感性 S=10^9；最终评分仍由独立 checker 从原坐标重算未取整欧氏距离
- 每条保存路线都核对 PyVRP 整数目标与独立整数边求和；144/144 通过
- 主尺度最大 |原始成本−整数成本/S| 为 **4.3195×10^-6** 坐标单位，次尺度为 **2.6348×10^-9**；144/144 均位于各自逐边误差界内
- 若路线总边数为 m，误差界为 m/(2S) 加浮点舍入余量；n=40 主尺度最保守界为 4×10^-5。这个界不是启发式最优性 gap，也不保证两目标最优解相同
- 每个客户必服务，提供 n 辆同质车，容量与原规格一致，固定车辆成本为 0，时长成本为 0，无补给；n 辆已足够表示任何非空路线集，不引入车数优先
- PyVRP v0.14 的 client 索引不含仓库，显式映射到原节点 idx+1；未知活动类型拒绝
- min/max penalty 同时乘 S，保持与目标一致的成本单位；若不缩放罚项，大尺度会暗中改变容量违约的代价

具体协议见 [PROTOCOL.md](PROTOCOL.md)，可审查适配器见 `adapter.py`。没有把缩放整数目标直接充当精确原目标。

## 预算与重放差异，完整保留

所有方法配置同一 0.25 秒 solver CPU 上限、1 秒完整 worker wall 上限。PyVRP 上限为 1,000 ILS 迭代，并保留 5 ms 返回余量；CPU 包括模型构造、量化、初始解、搜索和输出重算。导入在 solver 计时前，但计入完整进程 CPU/wall。每个尺度 48 次达到迭代上限，24 次到达 CPU 返回余量。没有记录到实际 CPU/wall 超额或自然失败。

完整重放 **504/504 可行，503/504 路线及成本完全一致**。唯一差异是 uniform n40、实例 seed 2026100410、solver seed 11、主尺度：

- 原运行在 770 次迭代停止，原始成本 962.0240271708714
- 重放在 697 次迭代停止，原始成本约 963.306391345778

两次都是 CPU 触发停止，不能承诺相同 seed 在计时截断下必然同路线。随后用宽裕预算分别固定 697/770 次迭代，**两个成本端点均复现**，完整诊断路线保存为 `replay_divergence_diagnostic.json`。原主批、原重放记录没有被替换；原 verification 未存重放路线，只存匹配标志和搜索元数据，后补诊断不会伪装成那次重放的路线。以该重放成本作描述性替换，主平均降幅约 0.4973%；它不是新的独立样本或第二套挑优结果。

## 环境、许可证、测试和成本

依赖仅装在项目隔离 venv，系统 Python 不受影响。14 个解析出的包有版本锁，官方 wheel URL/SHA-256 记录在 `install_report.json` 与 `dependency_provenance.json`；49 个已安装 PyVRP 文件哈希在前后检查中一致。PyVRP 为 MIT，原许可证和依赖通知位于 `licenses/`。未复制或修改厂商源码。交付包不包含 venv、依赖二进制或 cache。

- 同一 venv 内通过 56 个原测试、14 个 VND v2 测试、13 个新 adapter 测试
- 预检曾发现 `is_depot/is_client` 应调用为方法的错误，在首个开发 batch 冻结前修正；初次失败日志保留为 `preflight_attempt1_failures.log`
- 保存后 504/504 重新独立验收；整数/原始目标、车队/罚项、旧结果、源码/依赖哈希均经过另一路审查
- 主批 wall **55.802 秒**；父 CPU **1.404 秒**；完整子进程 CPU **55.014 秒**；不重叠 CPU 合计 **56.418 秒**
- 原完整重放另计 wall **56.974 秒**、父 CPU **1.541 秒**、子 CPU **56.155 秒**；两次固定迭代诊断另计 wall **0.723 秒**、父 CPU **0.016 秒**、子 CPU **0.718 秒**

OS `wait4` 包含解释器启动/导入/退出和被杀进程 CPU。主批成本不包括安装、测试、冻结/最终写盘、后续分析、审查、助手/人工或平台费用；这些没有被假定为零。没有实验侧模型或付费 API。只验证当前云 Debian/Python 环境，未验证 Ubuntu 22.04。合作式 CPU 检查不是操作系统硬 CPU 限制，wrapper 也不是不可信代码沙箱。

## 文件与复现

主记录位于 [runs/dev_20261004_01/](runs/dev_20261004_01/)：`freeze.json`、`source_snapshot/`、`raw.jsonl`、`raw.csv`、`results.json`、`summary.json`、`verification.json`、`adapter_verification.json`、`replay_divergence_diagnostic.json`。源码/协议先冻结、旧 pilot/VND 数据均保留，最终 holdout 未触碰。

在 `URP/experiments/vehicle_routing` 中执行；首次安装需使用授权的官方来源：

```bash
python -m venv .venv-pyvrp-0.14.0
.venv-pyvrp-0.14.0/bin/python -m pip install --index-url https://pypi.org/simple --require-hashes -r mature_pyvrp_v1/requirements.hashed.txt
.venv-pyvrp-0.14.0/bin/python -m unittest mature_pyvrp_v1.test_adapter -v
.venv-pyvrp-0.14.0/bin/python -m mature_pyvrp_v1.run_experiment --output mature_pyvrp_v1/runs/my_new_run
.venv-pyvrp-0.14.0/bin/python -m mature_pyvrp_v1.verify_run mature_pyvrp_v1/runs/my_new_run
.venv-pyvrp-0.14.0/bin/python -m mature_pyvrp_v1.analyze_results mature_pyvrp_v1/runs/my_new_run
```

锁定 wheel 针对此次 CPython 3.12/Linux x86_64。输出目录和验证记录拒绝覆盖；不同环境需建立新环境记录，不能伪称相同二进制。

## 剩余研究门槛

接入成熟库这一步已实际完成，下一步是新开发实例的更大规模/预算研究，以及多种真正强方法之间是否存在稳定互补性。当前对照没有实际 selector、选择全费用净收益、P3/P5 的生成成员谱系/费用、最终任务/代码双轴 holdout 或农业约束，H1/H2 仍未验证。
