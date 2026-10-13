# P3：2024 年作者仓库数据上的 FF/BF 更正重评分

当前状态：准备与手写验证阶段。正式 60 个槽位尚未运行，需精确冻结、独立复核后进行一次明确授权。

## 来源与研究边界

本阶段回答一个具体问题：在可追溯的 EoH 历史测试序列、全部可行箱接口及正确容量设置下，手写 First Fit / Best Fit 能否得到完整可验的基线结果。

- 历史数据固定在作者仓库 commit `e4b5ddba03b2b88025747e11c6049f8b529a4368`（2024-07-27）。1k、5k、10k 三个 pickle，各 5 个实例的 Git blob 已在 2024-05-14 提交 `a27784a071fd86bd3de14fe60cea00b38bce3b0a` 出现，并持续到 2026 年替换前版本。原始字节、Git blob SHA1、SHA256、历史记录和 MIT 2023 许可证保留在 `upstream/historical/`
- 这是“ICML 2024 时期作者仓库实例”身份的证据，不能独立证明论文某次 Table 1 运行具体读取过同一字节文件
- 官方当前 commit `472545785c936dcfc863d2bc0d6109cf23c7ce62` 在 2026 年数值重建了测试集。其 1k/5k/10k 序列与历史序列不同。当前版原始字节及安全提取结果保留作来源比较，未混入正式 60 槽位
- FF/BF 分数定义依据当前官方 `heuristic_first_fit.py` 的负可行箱索引、`heuristic_best_fit.py` 的负放入后余量；本实现是手写整数值与稳定平局规则等价版本，不直接导入作者文件，不将执行时间称为官方 NumPy 实现速度
- 不执行论文 EoH 函数、不生成程序、不做 thought/code 演化。即使本阶段完成，也只补齐基线重评分，不能称完整 EoH 复现

来源：[历史仓库](https://github.com/FeiLiu36/EoH/tree/e4b5ddba03b2b88025747e11c6049f8b529a4368/examples/bp_online/evaluation)、[当前更正说明](https://github.com/FeiLiu36/EoH/tree/472545785c936dcfc863d2bc0d6109cf23c7ce62/examples/bp_online)、[ICML 2024 论文](https://proceedings.mlr.press/v235/liu24bs.html)

## 数据安全与重合检查

`extract_historical_data.py` 只识别固定 pickle opcode 文法，把 `GLOBAL`、`REDUCE`、`BUILD` 等作为惰性语法标记核对；不解析为函数、不查找全局对象、不调用 reducer，不使用 pickle.load。唯一数值操作是 4 字节小端有符号整数转换。原始元素是 NumPy int32（`<i4`），JSON 中保留 dtype 元数据并转为精确 Python int。元素范围及本轮容量保证 FF/BF 的比较/减法没有整数溢出；这不构成任意 NumPy 程序接口等价声明。

内嵌设计数据从源码 AST 中只提取封闭字面量，不导入/运行作者模块。历史设计 5k、历史 evaluation 内嵌 5k、当前内嵌设计 5k 的物品序列完全相同；历史 1k/5k/10k 测试序列与设计序列没有完整实例相同，也没有完整短序列前缀相同。当前 `training_dataset_5k.pkl` 与内嵌设计不同，不能根据文件名把它当成历史 EoH 实际训练数据。逐项证据见 `data/historical_data_audit.json`。

没有整序列重合不等于证明统计独立。数据公开且已用于复算设计；两方法与两容量复用同一序列，不能把 60 个槽位当作 60 个独立样本或新盲测。

## 冻结协议

`prepared_plan.json` 列出所有 60 槽位：3 规模 × 5 实例 × 2 容量 × 2 基线。顺序按规模 1k/5k/10k、原实例顺序、容量 100/500、FF/BF。前 20 个 1k 槽位计入同一次实验，用于观察成本，之后不调整来源、规则或预算。

每次预置 n 个容量相同的空箱，逐物品筛选所有可行箱，包含未用箱；按原索引稳定选择最大分数。该接口暴露预置箱向量长度（即总物品数），不能称未知总长度的更严格在线模型。当前物品以原序到达，已放物品不移动。

容量 500 使用原绝对物品大小，不缩放；每个实例都应用所请求容量。历史代码只更新首个实例容量的缺陷不作为主实验。若将来用已完成的容量 100/500 输出作历史混合容量算术对照，应另标推导结果，不能计为新调用或独立样本。

独立 `checker.py` 从原始物品及完整分配重算负载、可行性、非空箱数、L1。L1 为总大小除容量向上取整；主统计每 5 实例采用 `(sum(used)-sum(L1))/sum(L1)`。逐实例 excess 均值和强化下界只作单独诊断，均不得叫作真实最优差距。

## 有界执行与成本口径

- 只接受冻结的手写 FF/BF 方法名，不接受源码、插件或研究函数；这是可信原生基线运行器，不是任意程序安全沙箱
- 单线程、每槽位一个全新 worker；每 worker 硬 RLIMIT_AS 2 GiB、CPU 20 秒、外部墙钟 30 秒、最多 1 秒清理；输出最多 400,000 字节，输入最多 100,000 字节
- supervisor 硬 RLIMIT_AS 2 GiB、自身 CPU 300 秒；任一时刻最多一个 worker。每进程 AS 不等于整个进程树 RSS
- 全批目标上限为已观测 worker CPU 加 supervisor CPU 300 秒、墙钟 600 秒。每次完整预留 20 CPU 秒和 31 墙钟秒，完整冻结校验后再检查，不给后续槽位缩小预算
- 聚合、最终校验和首轮报告写入计入观测预算；最终有界记账快照/控制台输出位于最后测量点之后。记录超出和清理成本；不把观测/预留式批次上限称作内核聚合配额或数学上无开销的 600 秒杀进程硬截止
- 完成认证必须全 60 槽位有效且无来源、基础设施、资源或预算问题；任一失败即停止，保留失败与未运行槽位，不自动重试
- 外部 API/LLM/GPU 调用为 0；无需安装依赖。云 CPU 实际货币费用未知

## 验证与复算

从本目录运行手写测试：

```sh
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -v
```

数据准备脚本不会调用求解器。历史 pickle 解码脚本可对保存原始字节重新做纯数据提取；来源不同应另建目录和新冻结，不覆盖本轮历史证据。

正式运行入口 `src/run_batch.py` 要求精确 `preparation_freeze.json` SHA256、一份用户明确批准的独立 JSON（scope、freeze_sha256、max_requests=60、authorized=true、唯一 run_id）和不存在的输出目录。每个 run_id 以排他文件记录一次使用。复制审批文件不能重用同一 run_id。没有对应批准时不运行正式槽位。

`results/preparation/draft_current_data/` 是发现 2026 数据替换前的未运行草案，只作准备轨迹；实际冻结以顶层 protocol/prepared_plan 和 historical_numeric 为准。初次从错误目录启动测试的 import 错误、历史静态检测误将 json.loads 当 pickle.loads 的失败断言均保留，纠正后重测；均非正式实例求解失败。
