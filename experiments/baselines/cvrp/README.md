# CVRPLIB 算法库与基线实验

本轮按老师要求，用经典CVRPLIB小、中、大规模及不同分布算例比较基础算法，再据结果选择后续改进方向。

## 入口

- [基线实验报告](results/基线实验报告.md) · [图表](results/figures/) · [逐项结果表](results/runs.csv) · [机器可读汇总](results/summary.json)。
- [交付分母索引](delivery-index.json)：列出各批次、期望计数及原始证据文件 SHA-256；它是只读证据导航，不代替归档重审或新实验验收。
- [使用说明](使用说明.md)：列出算法与算例、单例求解、独立验算、复现和汇总。
- [当前17配置](算法清单.json)：本轮有效入口；17个配置不等于17个独立算法家族。
- [算法全量来源](../../../algorithm_inventory.md)：已有实现、适配与补充算法的来源及边界。
- [冻结实验计划](../../../protocol/formal_plan.json) · [实验协议](../../../protocol/基线实验协议.md) · [执行分工](../../../protocol/execution_allocation_amendment.md)。
- [原始结果包](raw/) · [独立审查证据](evidence/) · [历史实验](history/)。
- [2026-10-17主批次归档重审](../../../protocol/audits/20261017/README.md) · [机器审计结论](../../../protocol/audits/20261017/archive_review.json)：对原主机统计证明链的证据分级，以此解释早期汇总中的已验证同条件统计。

源码仍在 src/research，标准输入仍在 data/benchmarks/CVRPLIB。运行入口为仓库根目录下 scripts/baseline.py，避免重复维护两套算法。src/research/configs/cvrplib_algorithms.json是早期五项准入的历史记录；本轮17配置以当前清单和冻结计划为准。

## 范围与状态

主实验为53个问题、51个底本，17配置、5个种子/计时重复、每项5秒，共4505项。云端seed0/2共1802项、本机seed1/3/4共2703项已完整汇总：4316项独立验算可行，189项无有效解，无未启动项。共4509次尝试：其中4次本机基础设施中断各重试一次，中断证据保留，不增加计划项分母。

按客户数，小/中/大分别41/6/6例；小规模来自A/B/E/F/P，中、大均来自X，不能独立分离规模与来源效应。两个共享底本的容量/车数变体仍是不同问题，故计划分母是53问题而非51底本。[算例清单](../../../src/research/configs/cvrplib_cases.json)记录分层与同源关系。[基线报告](results/基线实验报告.md)中PyVRP为265/265有效，算例等权参考gap约0.341%；其他配置的gap必须与各自的可行覆盖率同行阅读，不把有效子集均值当全体比较。

主机证据按归档重审分级：cloud seed0的901项具VERIFIED host manifest和匹配环境哈希；cloud seed2的901项有未VERIFIED、未链接环境哈希的host manifest；ubuntu-local seed1/3/4的2703项有结果SHA绑定的FROZEN resource manifest，但缺原汇总所引host/environment核验包装。后两类不是“无任何主机资源证据”，也不因包装缺口否定可行路线与成本；但目前仅第一类支持已验证同条件资源统计，已验证配对为6618而不是原先31512。289组描述性合并质量数值经重审核对一致。若未来找回原包装，应另作派生审计，不回填冻结原始结果。

补充vendor对照120项已全部完成并独立审计：120项可行、无重复、无审计错误。见[补充汇总](native-summary.json)、[逐项记录](native-runs.csv)、[独立审计](evidence/vendor_all120_audit.json)。该对照不混入主4505项分母。

2026-10-16 李月莹在更早提交 `50b3b2c` 上另交了一份 5 算法验收包（标记 acceptance_only，PyVRP 种子 0–9，5 秒端到端）。另有沿用原 16 例输入的 1 秒搜索循环两批。两套计时分开，都不混入上面的 4505 项，也不签收 G5。核验与原始压缩包位置见 [handoff/20261016-liyueying](handoff/20261016-liyueying/核验与接手.md)。

具体为验收包742/742复算有效；16例历史r1批48项stdout与既有归档逐字节相同，不是新复现，另有新批48项；两批41/48配对成本相同。勿将这两批合成96项新增观测，也勿用验收包补主计划的种子。

质量按主机和资源批次分别统计；合并质量仅作异构条件描述，不跨硬件排名速度。确定性算法的重复不是独立随机搜索。GA/PSO/DE随机键+Split属于本轮标准教学适配，不冒称历史CVRP复现。

## 只读索引核对

从仓库根目录执行以下标准库脚本，可核对[交付分母索引](delivery-index.json)所引用的证据字节和核心计数；它不运行求解器，不重算原始路线，也不替代[独立归档重审](../../../protocol/audits/20261017/README.md)：

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

在仓库根目录、已安装requirements.lock依赖的Python环境中运行：

    python scripts/baseline.py algorithms
    python scripts/baseline.py cases
    python scripts/baseline.py run --case A-n32-k5 --algorithm pyvrp --seed 0 --budget 5 --name demo-01

新调用只写独立user-runs目录，不覆盖本轮正式结果。完整4505项新复现使用reproduce子命令，默认只显示命令，明确加--execute才启动。
