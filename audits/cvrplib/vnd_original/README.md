# VND 原始归档来源补充核验

核验日期：2026-10-14 UTC。结果：PASS，10/10 成员通过。

本补充证据关闭此前准入发布包中明确披露的“VND 原始ZIP未能独立取回”来源保证缺口。旧发布包在其生成时的描述仍真实，因此不改写旧包、旧日志或旧结论；本文件是后续新增证据。

## 核验结果

- 原始归档：公共新16例算子顺序迁移.zip。
- 实际大小：1,296,035字节，与固定清单一致。
- 实际SHA256：4ac6eca8206577329f074d8aa57274202ce591681f9daeb939671ff8c302dbca，与固定清单一致。
- 从已交付 src/research/configs/cvrplib_sources.json 精确选出10个VND成员，成员在ZIP中均仅出现一次。
- 逐成员同时比对：原ZIP成员字节、清单声明的SHA256/大小、已封存交付目录中的实际文件字节。全部10项完全一致，无替换、修复或重生成。

完整逐文件证据见 vnd_original_verification.json，执行摘要见 verification.log。verify_vnd_original.py 仅用Python标准库，只读归档、源码清单和已交付源码；只写新的核验报告。

## 复现

从可访问相关文件的环境执行，替换三个路径：

    python verify_vnd_original.py --archive /path/to/original.zip --root /path/to/delivery-root --output /path/to/new-verification.json

脚本对归档SHA/大小、成员数、唯一性、逐字节及哈希/大小任一不符返回非零。输出时间戳会变化，核验对象和哈希不变。

## 结论边界

这次只补来源字节证明，没有修改算法、测试、旧交付包，也没有运行任何优化实验。此前PyVRP原归档成员已独立验证，现VND十个成员也完成原归档比对。正式比较是否启动及其调度冻结状态不由本补充核验改变。
