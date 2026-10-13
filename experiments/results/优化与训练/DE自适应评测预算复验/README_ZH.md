# DE自适应评价预算复验阅读说明

先读REPORT_ZH.md和figures/01_confirmation_paired.png，再看figures/05_family_heterogeneity.png。总体SH较好，但优势主要来自Sphere；Ellipsoid和Rastrigin的均值更差。请勿将总体比值当成所有任务改善幅度。

这是M06/P344 Successive Halving预算机制向DE参数评价的真实迁移实验，未运行作者完整代码，也没有LLM结构生成或原论文整表复现。全部正式FE值和续训状态均已保留，参数、变换实例、种子、排序和预算在运行前冻结。失败0，失败分母和全部负结果保留。

## 文件与分包

- M06_report_code.zip：中文报告、5张PNG及SVG科研图、冻结方案、全部源代码、选择记录、统计、自检与独立审阅记录
- 原始数据24个ZIP：每次完整调参试验分train与confirm两包，文件名trial01至trial12；每包约17MB，全部约405MB
- ARCHIVE_MANIFEST.json：每个包的字节数及SHA256
- FILE_MANIFEST.json：展开后的全部正式文件SHA256
- Drive原始数据文件夹：https://drive.google.com/drive/folders/15RsBLtb6Qq14IqihLlTecvengWGlDmb-

把报告代码包与24个原始数据包解压至同一个父目录，它们会合并到independent_sh_budget_20261006目录。使用Python运行src/verify_manifest.py可在任意目录只读核验全部文件，缺包会明确列出。

## 原始记录

data/*.npz使用NumPy load(..., allow_pickle=False)读取。每文件是一段实际新增运行；state含累计FE与PCG64状态，population/fitness为恢复点，values保存该段每个FE的目标值，trace是FE/历史最优/当代最小/当代均值。sample_points与sample_values是预先固定每代一点评价复核样本；point_hashes是每代40个坐标点的字节SHA256。全部坐标点没有直接存盘，可由core.py、plan.json和随机状态重建。

results/ledger.jsonl提供分段与上一个checkpoint的对应关系。8064分段构成5376逻辑轨迹，不能把分段当独立样本。统计基本单位为12个完整候选池调参试验。

## 检查和重跑边界

正式src/core.py、run.py、audit.py、tests.py、freeze.py和plan.json均被prerun_freeze.json锁定。report.py及verify_manifest.py属于事后展示/交付检查，不影响任何实验选择。

run.py拒绝覆盖已有ledger；要重跑应复制代码、方案和冻结记录到一个新的实验目录，创建空results/data目录，不应删除或覆盖当前交付。不要重新生成plan后仍声称是在重放同一设计。正式审计audit.py包含原工作区旧DE文件的只读隔离栅栏；该检查需要原文件路径，因此异机不能直接以原审计脚本无修改跑到底。交付已附原环境审计结果；异机先用可移植的verify_manifest.py核验包，再按core.py与冻结方案重建轨迹。缺少历史源文件不能被当成已复核原包未修改。

本次未安装依赖，只使用已可信Python和NumPy；绘图另用现有matplotlib。prerun_tests.json记录非评分测试，audit.json记录全部轨迹同前缀、独立公式重算和96条赢家直跑重放。独立审核结果只代表该审核说明中列明的实际覆盖范围。

独立审阅复跑：把review/audit_sh.py复制回与independent_sh_budget_20261006同层的audit_parallel_mechanisms_20261006目录再执行；默认输入定位依据此兄弟目录约定。review中有完整独立证据及原始包核验结果。作者自检和外部审阅的重放各695040FE，分开记账。
