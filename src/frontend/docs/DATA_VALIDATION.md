# 本项目数据核验

核验程序是 scripts/validate_data.py。它独立读取归档数据，不导入或执行 research/src 的实验 runner、策略评分或训练函数。原始 ZIP 和 research/ 保持不变；结果写入 artifacts/validation_report.json。

运行：

    python3 scripts/validate_data.py
    python3 -m unittest discover -s tests -p 'test_validation.py' -v
    python3 scripts/validate_data.py --research /path/to/research --output /path/to/report.json

项目环境建立后可将 python3 换成 .venv/bin/python。程序仅在全部阶段实际通过时返回 exit 0 和 status: PASS。任何异常返回 exit 1 和 FAIL，包含检查名、文件/字段/步数位置及失败原因；后续依赖阶段不再执行。已经完成的计数不会伪装成全量覆盖。

2026-10-06 实测：WSL Ubuntu 22.04、Python 3.10.12 / NumPy 1.21.5，完整数据核验 PASS（31.676 秒），12 项故障注入/语义单元测试全部通过。最新机器结果以 artifacts/validation_report.json 为准。确认集差值重算为 −21.453703703703702 箱，95% 区间 [−23.916666666666668, −19.37962962962963]，49 胜 / 56 平 / 3 负；风险集差值 +25.333333333333332 箱。

## 实际检查内容

| 范围 | 检查方式 |
|---|---|
| 完整性 | 所有 1914 个 MANIFEST 条目的字节数与 SHA256；清单中的 FREEZE 哈希；284 个冻结文件；MODEL_FREEZE 的模型哈希；协议中的固定策略源码哈希 |
| 输入 | 264 条输入 ID、协议元数据、5000 个整数物品、容量 100、顺序哈希与多重集哈希；train/confirmation/risk 的输入集合分离 |
| 分组/缺失语义 | train/confirmation 的 source_position 是 0..4999 的置换，三种到达顺序恢复相同原始序列；风险输入缺少该字段，验证其 prefix_sha256、相同前缀与相同后缀多重集；风险升降序仅约束后 4500 项 |
| 768 条轨迹 | 每条六个整数数组都是 5000 元素；逐步检查箱号范围、容量、当步 pre/post_remaining、feasible_counts、used_bins_after、累计体积；终态 remaining、总箱数与体积下界 |
| 公共前缀 | 每条流 BF 与 BF_then_EoH 的前 500 项五个逐步数组与完整前缀状态一致；有 SELECTOR 时也相同；published_EoH 从第一项开始运行，故不纳入同状态前缀要求 |
| SELECTOR | 120 条记录整条六数组轨迹等于选择的实际分支；selector_consumed_count=500；31 维特征、5 个邻居、平方距离、两分支预测、selected_index 与 branch 一致 |
| 冻结模型 | 从已记录 BF 前缀状态独立计算训练特征，核对 144 个训练 ID 顺序、两分支真实标签、mean/scale/x/y、SBS 和训练摘要；只核验已有参数，不保存新模型、不拟合调参 |
| 风险 | 四组每组三条流的前缀、状态、特征、邻居、预测、选择完全相同；逐组事后最优偏好、后悔值、是否逆转单列核对 |
| 汇总 | 全 264 行 train/confirmation/risk CSV、训练/确认/风险 SUMMARY 字段及全部 18 个确认族×顺序单元逐字段重算 |
| CPU 分项 | 逐个原始记录检查计时非负且有限，按 split/policy 重聚合核对 cpu_accounting.csv；这不等于认证历史整体 900 秒预算 |
| bootstrap | 按实际六族、每族六个多重集组计算 36 个组均值；复用 NPZ 中全部 10000×6×6 个历史抽样索引，验证每个统计量与 95% 线性分位区间；检查种子元数据，不生成新抽样 |

逐步状态检查使用**归档的 assignment** 恢复箱状态，不选择新箱、不重跑政策实验。可行数从残量频数累加，包含未用空槽；箱号与已用箱数分别处理。体积守恒通过每步严格扣除当前物品、累计检查及终态总和共同验证。时间位置 step/1 表示第一个已处理物品；界面初态 0 不在历史逐步数组内。

## 容差与报告接口

- 整数轨迹、计数、哈希、完整分支匹配以及同前缀风险一致性采用精确比较。
- 派生浮点量采用绝对容差 1e-12、相对容差 1e-12；不接受 NaN/Infinity，不通过广播掩盖形状不同。
- 31 维特征使用独立标量均值/总体标准差、显式线性分位插值，按 PROTOCOL.json.features.names 输出；近邻距离相等时保持训练行索引顺序；预测成本相等时使用训练 SBS。
- 测试夹具与研究文件分离，包含非连续箱号、空槽可行计数、六数组逐项破坏、容量越界、非法数组形状/类型、稳定距离并列、预测并列、CSV 破坏与缺失输入。测试不会写入研究目录。

validation_report.json 的 schemaVersion=1，提供：

- status、passed、generatedAt、elapsedSeconds 与执行环境；
- coverage.inputs/runs/trajectorySteps/selectorDecisions/commonPrefixes/riskGroups/confirmationCells/bootstrapReplicates/manifestEntries/freezeHashes；
- checks 每阶段状态/耗时，failures 明确位置和原因；
- sourceHashes 绑定清单、协议、模型和冻结文件；
- metrics.training/confirmation/risk 为本项目重算且核对的指标；
- tolerances 和 limitations 明确数值与覆盖边界。

## 结论边界

报告仅代表本项目只读数据核验。包内 independent_audit/FINAL_AUDIT.md 的历史科学审计 PASS 单独保留；历史整体 **900 CPU 秒预算无法认证**，原验证器中断及缓存版重新核验的事实不能省略。

本程序没有再次核对每一步策略评分的 first-argmax；包内正式标量 checker 已有该历史证据。本项目核对全部实际分配的物理合法性、记录一致性及冻结选择器算术，不声称新做了策略评分审计、算法最优性证明、信息隔离证明或历史时间戳认证。

10000 份历史 bootstrap 的重新计算仅说明本次预设合成混合下的描述性不确定性。88.17% 表示收回同 BF 前缀两分支 oracle 的可改善余地，不表示总体装箱效率提高；局部筛选不能套用全局置信区间。风险 12 流与确认 108 流分别处理。

浏览器、移动端、无障碍、真机与原生 Ubuntu 验收由工程记录单独说明，不能从本报告的 PASS 推导。
