# 已撤回结论与失败边界

本页保留两条仍会影响科研解读的警示。这里只核对原始文件、静态源码及统计计算，没有重新运行旧候选、旧求解器或模型生成；旧实验不因此重新成为当前有效结果。
本地最小原证据：[research_corrections.zip](provenance/research_corrections.zip)，内含逐文件来源 ID、原字节大小/SHA-256 与静态敏感值扫描清单。已有当前原字节者只在清单引用，不重复复制。


## CodeGen：旧“禁令反噬显著”结论停止引用

范围是 2026 年 9 月旧 P2 排序实验（T1–T4 各 20 份，共 80 份），不同于当前[22 输出静态预检](results/组件/sorting_generation/README.md)和其他同名 P2 项目。

旧 harness 的 uses_builtin 用正则扫描整段源码，连 docstring 的 sorted()/arr.sort() 提及也计为调用。T4 的 s07、s14、s15、s17 实际是冒泡排序，被误标为 PASS_BUILTIN。本次取得的四份原模块及旧 evaluations.csv 均与 9 月 29 日复核证据中的 SHA-256 一致；四份 AST 的调用只有 len/range，未执行候选。

仅将这四条标签改为 PASS_NATIVE，保持旧测试通过/失败结果不变，T4 为原生 4/20、内置 4/20；T1 原生 7/20，T3 原生 4/20。T4 对 T1 的双侧 Fisher p=0.4801153511，在 T2/T3/T4 对 T1 的三个原生通过率对比组成的 BH 家族内，调整后 p 同为 0.4801153511。旧 BH p=0.0249480250 的显著性结论失效。本次独立计数及算术复核与旧复核 JSON 一致。

这属于标签勘误，仍以旧测试结果为条件，不是加强合同后的正确性重评，也不代表 harness 已修复、80 份候选已重新评测，或不显著就等效。

来源：[9/29 复核证据](https://drive.google.com/file/d/1xDbozqW0ApT5Ck0m1SuHGkJ-pLvymsLi/view)、[原评测 CSV](https://drive.google.com/file/d/1PIPeZryfqCMQWyoLFgTwaBrJp1yo-7AQ/view)、[原 harness](https://drive.google.com/file/d/1xpb_a4oOzY4gkZMkq794WDR5jA8ELiRe/view)。对应原记录 ID：1a6DCqn35KqdoQqCfNMZ1JyWyIwIgw42s。

## E0：n=48 未进入 GA，不能当作搜索难度证据

[原 nstar_results.csv](https://drive.google.com/file/d/1S6qVPICIPAnxa_rI3oCsFyRr3avRGG5a/view)共有 43 行。已测 n=12、16、20、24、32、40、42 各五个 seed 的目标值相同；n=44 的四个为 3709.86，一个为 3715.77。旧记录的 N*₀=44 只表示这组已测阶梯首次出现 seed 间目标值差异，不是普适难度阈值或全局最优证明。

n=48 的 seed 1 在 Params::preleveDonnees 阶段退出；seed 2/3 的 batch_status 显示 rc=124、墙钟 800s，三份日志均没有 Start of GA。因此这组 n=48 失败不能解释成 GA 搜索更难；旧“继续规模上探”没有取得可用于搜索比较的结果。不能将其中 ticks_total/ticks_best 直接当作墙钟、time-to-best 或算法工作量代理。

另需纠正旧 diag README 的精确耗时叙述：n44_s1.log 中 CPU Time : 765.777 seconds 位于 Start of GA 和第 0 次迭代输出之后，不能仅凭此行认定“GA 前解析耗时为 765.777s”。这些日志也不足以证明解析复杂度随弧数二次增长。

来源：[n48 seed1](https://drive.google.com/file/d/1OFjFdHERoXBbATPPBqEwIrGid42fyo9C/view)、[seed2](https://drive.google.com/file/d/1823FSY885Z2cA6KbGigqX1UasZKPH4dg/view)、[seed3](https://drive.google.com/file/d/1kyG0Xp8IAjqcbu_DmXDVLm3YuQJwFOpO/view)、[batch_status](https://drive.google.com/file/d/1QlMZcpgxha9wL5lL0-zU9MaYMzamDuyo/view)、[n44 seed1](https://drive.google.com/file/d/11tCnqyvDk1fRuaHgQNK0trSOsbLjzMSb/view)。对应原记录 ID：1IaFVBE6idoBxgxXPJ7JhRS1aC7pdJz8m。

## 相关核验边界

通用计时口径已在[论文与实现对照](../literature/笔记/10_路由模型与经典搜索/论文与实现对照.md)；BH 扫描公式/OCR 校正已在[P120 笔记](../literature/笔记/08_评测统计与程序验证/逐篇笔记/P120.md)；SISRs 章节未取得、QD-LHD 模拟 LLM/外部评价器及其他源码覆盖边界已在[代码说明](../src/repos/README.md)。目录数、ZIP 文件数、文字层可检索均不能代替依赖齐备、公式逐图核验或完整复现。
