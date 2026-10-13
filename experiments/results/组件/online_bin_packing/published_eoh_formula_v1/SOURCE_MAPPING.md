# 固定公式逐行重实现与静态测试计划

状态：只完成手写源码、边界推导和前瞻测试计划；没有导入 NumPy、运行数值扫描、作者源字节、重实现公式或正式装箱槽位。

## 来源与对应

原始固定文件为 615 字节、15 行，SHA256 `f3d50f0e81ca061a0377b9fb61b75cf16ecde9f091876db0d8baca8323655995`，Git blob `5a7970a80551d5e124234348d449d15ddf369a0e`。来源为 FeiLiu36/EoH commit `472545785c936dcfc863d2bc0d6109cf23c7ce62` 的 `examples/bp_online/evaluation/heuristic_original_EoH_paper.py`。原文件仅作为只读对照；不会动态导入、eval、exec 或编译为执行入口。

|作者源码行|本手写实现|保持的性质|
|---|---|---|
|4|diff = bins - item|int64 可行箱减 np.int32 标量物品|
|5|exp = np.exp(diff)|NumPy 指数，binary64|
|6|sqrt = np.sqrt(diff)|NumPy 平方根，binary64|
|7|ulti = 1 - diff / bins|先除后减，不化简成 item/bins|
|8|comb = ulti * sqrt|保持乘法顺序|
|9|adjust = np.where(diff > item*3, comb+.8, comb+.3)|严格大于；两分支先求值|
|11|denominator = (exp+.7)*exp；hybrid_exp = bins/denominator|仅给原中间量命名，不重算、不平方或指数化简|
|13|scores = hybrid_exp + adjust|保持加法及结果 dtype|
|15|返回 scores|校验最终值为有限 float64；trace 仅用于边界证据|

`src/formula.py` 是公式重实现，不是原程序逐字节执行或新算法创新。没有第二份手写代码冒充独立证明；独立复核应检查源公式对应和下述边界推导。

## 有界输入与非有限中间值

物品为 np.int32、1..100；可行箱为一维 np.int64，item..500、长度1..10000。diff 在0..499，指数本身有限。分母等于实数意义的 exp(2d)+0.7exp(d)，binary64 最大值位于整数 d=354、355 之间，因此预期 d>=355 溢出为正无穷，有限正数除它为正零。最终调整项及分数仍有限。该推导尚未被本轮数值执行验证。

精确填满 diff=0 时，exp=1、sqrt=0、comb=0，阈值分支取+.3；不添加“精确填满必胜”规则。diff=3*item 恰等时也取+.3。最终 NaN/Inf、错误 dtype 或非法输入均应失败。

## 警告、异常与传输

计划固定 NumPy 错误策略 divide/over/invalid 为 warn，under 为 ignore，与已查默认行为一致。每个警告通过有界 journal 保存原文、类别、来源行和每次出现位置；不静默丢弃重复警告，不吞异常。最多12000次、32种、每条1024字节，超界标注证据不完整并失败。预期只有 denominator 的 multiply overflow；未知警告需停止处置。

未来 launcher 必须独立限流 stdout(JSON，400000字节)与 stderr(诊断，16384字节)，不得使用 FF/BF 旧版的合流方式。`tests/numeric_gate.py` 的异常同时产生非零退出/失败字段和 stderr traceback。该文件尚未执行；配套 `launch_numeric_gate.py` 已准备为固定单次数值门槛入口，独立限流 stdout/stderr，需精确冻结及单独授权才可启动；完整正式30槽位 runner 尚未实现/授权。

## 待授权的数值门槛

按实际 np.int32 标量逐个扫描100个 item，与连续1D int64可行箱形成45050个合法数值对。记录每个中间量的 dtype、分类、原始二进制哈希，不输出全部数组。覆盖 diff0、3*item±1/恰等、354/355，以及1/2/17/1000/10000长度、反向与相等箱。若同一实现跨布局产生位模式差异，记录并停下审查，不默增容差。只称源公式对应、解析边界与属性验证，不称作者字节执行对照。

所有微型装箱、warning/transport故障测试及数值扫描均待协调CPU窗口与明确授权。视频转录期间不启动。静态准备不消耗正式30槽位。

## 许可证

公式出处的 MIT License 原文另存 `LICENSE.source`，Copyright (c) 2026；重实现保留来源与许可说明。
