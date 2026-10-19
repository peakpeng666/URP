# CVRPLIB 算法库与基线实验

本轮按老师要求，使用经典 CVRPLIB 的小、中、大规模及不同分布算例比较基础算法，据此选择后续改进方向。

## 入口

- [基线实验报告](results/基线实验报告.md) · [图表](results/figures/) · [逐项结果表](results/runs.csv) · [机器可读汇总](results/summary.json)。
- [交付分母索引](delivery-index.json)：各批次的期望计数及原始证据文件 SHA-256，供只读核对。
- [使用说明](使用说明.md)：算法与算例、单例求解、独立验算、复现和汇总。
- [当前 17 配置](算法清单.json)：本轮配置清单，包含同一算法家族的不同变体。
- [算法全量来源](../../../algorithm_inventory.md)：实现、适配与补充算法的来源及适用范围。
- [冻结实验计划](../../../protocol/formal_plan.json) · [实验协议](../../../protocol/基线实验协议.md) · [执行分工](../../../protocol/execution_allocation_amendment.md)。
- [原始结果包](raw/) · [独立审查证据](evidence/) · [历史实验](history/)。
- [2026-10-17 主批次归档重审](../../../protocol/audits/20261017/README.md) · [机器审计结论](../../../protocol/audits/20261017/archive_review.json)：主机证据分级及已验证同条件统计的适用范围。

源码位于 src/research，标准输入位于 data/benchmarks/CVRPLIB，统一运行入口为仓库根目录下的 scripts/baseline.py。src/research/configs/cvrplib_algorithms.json 保留早期五项准入记录；本轮 17 配置见当前清单和冻结计划。

## 范围与状态

主实验包含 53 个问题、51 个底本，17 配置、5 个种子/计时重复、每项 5 秒，共 4505 项。云端 seed0/2 的 1802 项与本机 seed1/3/4 的 2703 项均已汇总：4316 项独立验算可行，189 项无有效解，未启动 0 项。共 4509 次尝试，其中 4 次本机基础设施中断各重试一次；原中断记录保留，计划分母仍为 4505 项。

按客户数，小/中/大规模分别为 41/6/6 例。小规模来自 A/B/E/F/P，中、大规模均来自 X，规模与来源效应存在混杂。共享底本的两对容量/车数变体分别计为不同问题，计划分母为 53 问题、51 底本。分层与同源关系见[算例清单](../../../src/research/configs/cvrplib_cases.json)。[基线报告](results/基线实验报告.md)中，PyVRP 为 265/265 有效，算例等权参考 gap 约 0.341%；各配置的 gap 均为有效子集统计，须与可行覆盖率一并比较。

归档重审按主机证据分为三类：

- cloud seed0：901 项具备 VERIFIED host manifest 和匹配的环境哈希，支持已验证同条件资源统计。
- cloud seed2：901 项具备 host manifest，状态未 VERIFIED，未链接环境哈希。
- ubuntu-local seed1/3/4：2703 项具备绑定结果 SHA 的 FROZEN resource manifest，缺少原汇总引用的 host/environment 核验包装。

三类记录均保留路线可行性与成本的验算结果。已验证配对数由原汇总的 31512 修订为 6618；289 组描述性合并质量数值经重审核对一致。后续找回的原包装另作派生审计，冻结原始结果保持不变。

vendor 补充对照 120 项已完成独立审计：120 项可行，无重复或审计错误，单独统计。见[补充汇总](native-summary.json)、[逐项记录](native-runs.csv)、[独立审计](evidence/vendor_all120_audit.json)。主计划分母保持 4505 项。

2026-10-16，李月莹基于更早提交 `50b3b2c` 交付 5 算法验收包，标记为 acceptance_only；其中 PyVRP 使用种子 0–9，预算为 5 秒端到端。另有沿用原 16 例输入的 1 秒搜索循环旧、新两批。两套计时合同分开统计，均不计入主计划 4505 项或 G5 签收。核验记录与原始压缩包见[handoff/20261016-liyueying](handoff/20261016-liyueying/核验与接手.md)。

验收包 742/742 项复算有效。16 例历史 r1 批的 48 项 stdout 与既有归档逐字节一致，新批另有 48 项；两批配对成本相同的有 41/48。共 96 项记录，其中 48 项为新增观测；验收包种子与主计划分开。

质量按主机和资源批次分别统计，合并结果用于描述异构条件下的质量表现；速度仅在同硬件下比较。确定性算法的重复属于计时重复。GA/PSO/DE 随机键+Split 为本轮教学适配，区别于历史 CVRP 算法复现。

## 只读索引核对

从仓库根目录执行以下标准库脚本，核对[交付分母索引](delivery-index.json)引用的证据字节和核心计数。脚本仅检查索引，不运行求解器或重算路线；路线与归档结论见[独立归档重审](../../../protocol/audits/20261017/README.md)：

```sh
python - <<'PY'
import hashlib, json
from pathlib import Path

index = json.loads(Path('experiments/baselines/cvrp/delivery-index.json').read_text())
sources = {}
for name, item in index['sources'].items():
    raw = Path(item['path']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == item['sha256'], name
    sources[name] = json.loads(raw)
plan, cases = sources['plan'], sources['cases']
audit, vendor, handoff = (sources[k] for k in ('main_reaudit', 'vendor_audit', 'handoff_audit'))
main = index['main']
assert (len(plan['algorithms']), len(plan['case_ids']), plan['seeds'], len(plan['schedule'])) == (main['configuration_count'], main['case_count'], main['seeds'], main['planned_unique_keys'])
assert (cases['case_count'], cases['base_count'], cases['strata']) == (main['case_count'], main['base_count'], main['size_strata_cases'])
assert len({c['case_id'] for c in cases['cases']}) == main['case_count']
assert len({c['base_id'] for c in cases['cases']}) == main['base_count']
assert all(audit['denominator'][k] == main[k] for k in ('terminal_results', 'not_started', 'recorded_attempts_including_interrupted_claims'))
assert audit['denominator']['planned'] == main['planned_unique_keys']
assert audit['quality']['independently_eligible'] == main['independently_eligible']
assert audit['quality']['failed_terminal_results'] == main['without_valid_solution']
assert audit['provenance']['level_counts'] == main['provenance_levels']
assert (vendor['planned'], vendor['attempted'], vendor['not_started']) == (120, 120, 0)
assert len(vendor['rows']) == sum(r['has_valid_on_time_solution'] for r in vendor['rows']) == index['separate_cohorts']['vendor']['independently_eligible']
assert handoff['valid_53'] == index['separate_cohorts']['liyueying_handoff']['independently_valid']
loop = index['separate_cohorts']['sixteen_case_search_loop']
assert handoff['summary_16']['batches']['group_r1_20261009']['valid'] == loop['historical_r1']['valid'] == 48
assert handoff['summary_16']['batches']['bridge_20261016']['valid'] == loop['new_bridge']['valid'] == 48
assert handoff['summary_16']['identical_costs'] == loop['equal_cost_pairs'] == 41
print('delivery index matches cited archived JSON')
PY
```

## 快速命令

在仓库根目录、已安装 requirements.lock 依赖的 Python 环境中运行：

    python scripts/baseline.py algorithms
    python scripts/baseline.py cases
    python scripts/baseline.py run --case A-n32-k5 --algorithm pyvrp --seed 0 --budget 5 --name demo-01

单次运行写入独立 user-runs 目录，正式结果保持不变。完整 4505 项复现使用 reproduce 子命令；默认显示命令，加--execute 后启动。
