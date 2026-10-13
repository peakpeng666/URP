# BPP前缀安全选择原型

容量100、5000项、BF前500项，31个前缀/状态特征，固定k=5代价回归。训练144流，确认108流，风险12流；总共768次完整policy×流。所有数值代码、输入和源在FREEZE.json冻结。模型在确认运行前单独冻结。

完整重跑需复制sources、src、evidence和EVIDENCE_TO_DESIGN.md到一个新的空目录，建立inputs/raw/analysis/figures四目录，并执行以下步骤。prepare.py按自己的父目录定位，所有文件拒绝覆盖。Python须有numpy、matplotlib及Noto Sans CJK SC字体。无需API、模型或新生成候选。

1. OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 python src/prepare.py
2. OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 python src/run.py
3. OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 python src/check_cached.py
4. OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 OMP_NUM_THREADS=1 python src/analyze.py

对应CPU硬上限600/240/40秒，合计预留在900秒总预算内。失败保留日志/部分轨迹，不以成功数据替换。运行器仅加载两个固定SHA256许可源，不是任意生成代码沙箱。

主指标：确认集selector−训练SBS箱数差。branch oracle是相同BF前缀后的两分支最优值；full-run oracle仅是另一启动状态的说明性参照。确认集按同multiset三顺序分组、族内bootstrap；构造风险流不混入主指标。

## 验证器的事后纯I/O修订

正式768次策略执行均成功，未重跑。首次check.py在循环中重复解压NPZ数组，完成26条轨迹后人工停止；原日志和冻结源保留。check_cached.py仅改为每份轨迹一次加载全部数组，检查断言、数学评分与指标完全不变，由独立审阅员核对差异后从头验证全部768条。首次中断使外层CPU精确记录缺失，账本按其240秒硬上限保守占用；成功验证与其他阶段使用外层进程实测CPU。复跑使用缓存版，不必重复这次无效I/O开销。
