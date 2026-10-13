# Published EoH 在线装箱基线来源及兼容性审查

审查日期：2026-10-07 UTC。用途：为新的前瞻确认实验准备一个可核查的 published_EoH 固定基线。

## 结论

作者公布的最终启发式可以准确取得，来源链已闭合到 ICML 2024 正式论文图 6 和作者仓库的明确命名源码。当前项目的容量 100、在线顺序、全部可行箱含空箱、按原箱索引首次 argmax 调用约定与作者评估器相符。数值和 API 兼容性经人工源码审查可支持；本次没有执行基线、候选、沙箱入口或实验，所以不能称运行准入通过。

原始文件包含顶层 `import numpy as np`，不满足本项目“恰好一个 score 函数”的准入语法。本目录保留原字节，并提供只删除该一行的适配副本和精确 diff；公式、常量、分支、运算顺序、函数体注释均未改变。该副本应标明“原论文启发式的沙箱封装适配”，后续仍须通过冻结的原准入门及独立玩具语义核查，不可为通过门禁再改公式。

## 官方来源和固定版本

- 正式论文：Fei Liu 等，Evolution of Heuristics: Towards Efficient Automatic Algorithm Design Using Large Language Model，ICML 2024，PMLR 235:32201–32223。[PMLR 正式记录](https://proceedings.mlr.press/v235/liu24bs.html)。
- 正式 PDF：[PMLR 页面直接链接的论文文件](https://raw.githubusercontent.com/mlresearch/v235/main/assets/liu24bs/liu24bs.pdf)。已下载只读核对并渲染检查第 17 页图 6；其中 EoH 区块完整表达式与作者仓库文件一致，论文展示入口叫 `heuristic`，作者仓库入口叫 `score`。图 2 说明该展示为最终种群中的最佳启发式。PDF 的第 9 页结论给出作者仓库链接。
- 作者仓库：[FeiLiu36/EoH](https://github.com/FeiLiu36/EoH)。固定提交：[472545785c936dcfc863d2bc0d6109cf23c7ce62](https://github.com/FeiLiu36/EoH/commit/472545785c936dcfc863d2bc0d6109cf23c7ce62)，提交时间 2026-08-06 16:59:10 UTC，提交消息为 update tasks used in EoH paper。本审查固定这个可取得的作者版本，不把其时间回写成 2024 年的代码封存。
- 精确源码：[examples/bp_online/evaluation/heuristic_original_EoH_paper.py](https://github.com/FeiLiu36/EoH/blob/472545785c936dcfc863d2bc0d6109cf23c7ce62/examples/bp_online/evaluation/heuristic_original_EoH_paper.py)。Git blob SHA-1：`5a7970a80551d5e124234348d449d15ddf369a0e`。本地原始字节 615 bytes，SHA-256：`f3d50f0e81ca061a0377b9fb61b75cf16ecde9f091876db0d8baca8323655995`。
- 授权：[该固定提交的 MIT LICENSE](https://github.com/FeiLiu36/EoH/blob/472545785c936dcfc863d2bc0d6109cf23c7ce62/LICENSE)，文件载明 Copyright (c) 2026。原文已保留；后续分发基线及实质性副本时保留版权与许可通知。此处仅记录仓库声明，未对旧历史提交的许可作追溯推断。
- 仓库现有 legacy `v0.1` 标签指向 `4b2338fc2317c743cec50c5c7a2e4684707af973`；它不是本次选定版本，也不能与当前固定文件身份互换。[作者 release](https://github.com/FeiLiu36/EoH/releases/tag/v0.1)。

## 哪个算法可以叫 published EoH

选定文件由作者直接命名为原论文 EoH；正式论文图 6 提供独立公式核对。本报告没有以社区复述替代源码。

作者的 [runEval.py](https://github.com/FeiLiu36/EoH/blob/472545785c936dcfc863d2bc0d6109cf23c7ce62/examples/bp_online/evaluation/runEval.py) 显式区分原论文启发式、`heuristic_EoH_by_this_code.py`、`heuristic_EoH_by_this_code_poor_generalization.py`，以及可选的新搜索产物 `heuristic.py`。后三者不能换名为本实验的 published_EoH。也不得重新运行 EoH 搜索再从结果中择优当作“已发表固定基线”。

作者的 [在线装箱说明](https://github.com/FeiLiu36/EoH/blob/472545785c936dcfc863d2bc0d6109cf23c7ce62/examples/bp_online/README.md) 记录原评估代码容量设置错误：非默认容量的五个实例中只有第一个被正确更改。已修正的容量 500 结果与原论文表不一致。本次目标为容量 100，不受该特定非默认容量错误影响；仍不能据此声称本地结果复制了旧论文数字。说明也区分重跑启发式的泛化差异。本项目确认集不得用于选 published_EoH 版本或调公式。

## 调用约定及项目对照

官方 [evaluation.py](https://github.com/FeiLiu36/EoH/blob/472545785c936dcfc863d2bc0d6109cf23c7ce62/examples/bp_online/evaluation/evaluation.py) 第 10–28、43–60 行规定：

1. 预先分配与物品数相同数量、初始剩余容量为 C 的箱子，含尚未使用的空箱。
2. 保留给定物品到达顺序；每步只传当前物品与当前可行箱的剩余容量数组。
3. 可行条件为 `bins - item >= 0`，允许恰好装满。通过非零索引保持原箱索引升序；不按剩余容量排序、不做容量归一化。
4. `score(item, bins)` 返回与可行箱数量相同的一维分数。取首次最大值，再映射回原箱索引。这里“最小”指并列最高分的最小原索引，不是最小剩余容量。
5. 分配后扣除 item，最后统计剩余容量不等于初始容量的箱数。

已获准只读比对项目 `frozen_runtime` 中相关实现：`runner.py` 564–601 行及 441–444 行具有同一分配/映射规则；`facade.py` 164–183 行给只读 int64 可行箱输入和 np.int64 当前 item，并要求有限的一维数值输出。无未来物品传入基线。

## 有限 NumPy 沙箱兼容性

人工审查所需 NumPy API 恰为 `exp`、`sqrt`、`where`；均在本项目 `manifest.py` 白名单内。函数仅有局部赋值、逐元素四则运算、一次比较和返回，不依赖排序、索引状态、随机数、文件、网络、动态 import 或写入输入。输出预期为同长度 float64 向量；只读输入不影响公式。

在本项目容量 100 整数域，令 b 为可行箱剩余量、i 为 item，则 `1 <= i <= b <= 100`，d=b-i 满足 `0 <= d <= 99`。因此 sqrt 的自变量非负，b 不为零，exp(d) 在 1 至 exp(99) 之间；`(exp(d)+0.7)*exp(d)` 至多小于 2*exp(198)，远低于 float64 最大有限数。其余乘除和加法也有界，原公式无需 epsilon、截断、nan_to_num 或溢出修复。该结论是域内解析审查，不是运行测试。不要外推成容量 500 下“无溢出”：该域可出现 exp(d) 相乘溢出，虽然项目另有受限中间异常策略。

准入唯一已知封装差异是顶层 import：`admission.py` 397–415 行不接收 Import 节点并要求唯一顶层 score 函数；`worker.py` 113 行已经注入受限 np facade。适配副本仅删除原文件第 2 行：

- 适配文件：`published_eoh_score_import_removed.py`，596 bytes。
- SHA-256：`6dd1c8929c59e75dca893d68f1e2010868bd9b6c3a61a1f3565e3b338f8eed81`。
- 精确差异：`import_removal_exact.diff`。

以上只是源级兼容判断。未运行 `validate_source`、未编译/导入/调用下载的函数、未探测 NumPy 运算、未运行测试或 pack。未来只能在现有受限 worker 内正式准入并做不含研究数据的玩具等价性核查，且记录解释器/NumPy/运行时冻结身份。

## 本次审查范围和交付

本次没有读取本项目 heldout、seed 或旧确认数据，没有安装依赖、没有上传文件、没有调用模型，也没有修改冻结运行时。仅下载官方 PDF、用官方 GitHub 只读接口取源码、保存来源与 hash，并人工比对指定的运行时文件。

现有“20 instances × EOH/IID/FF/BF/published_EoH = 100 packs”仅作为父任务提供的新修订准备背景。旧预模型确认数据封存未找到；本次 baseline 来源核对不能证明旧预注册存在，也不能补称旧确认已执行或已完成。必须把后续确认标为新修订的前瞻确认。

本目录包含：本审查报告、官方原始源码与许可、来源响应、每文件 SHA-256 与 Git blob 校验、原 import 删除适配副本及 diff、正式论文原 PDF及图 6 渲染证据。`runtime_compatibility_evidence.json` 仅记录本次实际读取的相关运行时文件 hash 和定位。未产生实验结果。
