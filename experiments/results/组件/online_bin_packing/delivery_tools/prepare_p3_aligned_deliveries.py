"""Project three accepted saved runs into public data; never import experiment code."""
from pathlib import Path
from fractions import Fraction
import collections
import hashlib
import json

U = Path(__file__).resolve().parents[3]
B = U / 'experiments/online_bin_packing'

def read(p):
    return json.loads(p.read_text())

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def rel(p):
    return str(p.resolve().relative_to(U))

def write(p, value):
    p.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False) + '\n')

def evidence(p):
    return {'path': rel(p), 'sha256': sha(p), 'bytes': p.stat().st_size}

def previous(name):
    p = B / name / 'delivery/manifest.json'
    return {U / x['path'] for x in read(p)['files']} | {p}

def finish(root, summary, selected, dependencies, reproduction):
    d = root / 'delivery'
    d.mkdir(exist_ok=True)
    summary['review_state'] = 'accepted after independent saved-evidence reconciliation'
    summary['external_dependencies'] = dependencies
    write(d / 'summary.json', summary)
    write(d / 'dependencies.json', dependencies)
    (d / 'REPRODUCE.md').write_text(reproduction + '\n')
    selected |= {d / 'summary.json', d / 'dependencies.json', d / 'REPRODUCE.md', Path(__file__)}
    selected = {p.resolve() for p in selected}
    forbidden = ('/private_', '/.authorization_uses/', '/vendor/', '/.venv/', '/__pycache__/', '/approved_run.json', '/approval_claim.json')
    for p in selected:
        if not p.is_file() or any(x in '/' + rel(p) for x in forbidden):
            raise ValueError('Invalid public payload: ' + str(p))
    files = [evidence(p) for p in sorted(selected)]
    manifest = {'schema': 'urp_public_delivery_v1', 'study_id': summary['study_id'], 'root': 'URP',
                'summary': rel(d / 'summary.json'), 'files': files, 'payload_files': len(files),
                'payload_bytes': sum(x['bytes'] for x in files),
                'report_sha256': summary['report_sha256'],
                'union_note': 'Unchanged earlier public evidence may be included for dependency closure; deduplicate by path and hash, never count it as a repeated experiment.',
                'excluded': ['private approval/use records and review notes', 'model weights, dependency environments, bytecode caches', 'superseded planning prose containing internal coordination'],
                'reproduction_note': 'Archived evidence is read-only. A relocated or rebuilt environment needs a new verified snapshot and user-controlled execution decision; no replay is performed by this projection.'}
    write(d / 'manifest.json', manifest)
    return {**evidence(d / 'manifest.json'), 'summary': evidence(d / 'summary.json'), 'payload_files': len(files), 'payload_bytes': manifest['payload_bytes']}

NUMERIC = {'python': 'Python 3.12, exact historical runtime hashes are retained in prior formula evidence; revalidate the chosen interpreter after rebuilding.',
           'numpy': '2.3.5', 'platform': 'Linux x86_64; process resource limits and POSIX process groups required',
           'install_source': 'Official PyPI for Python packages; no environment or wheel cache is included.',
           'historical_data': evidence(B / 'paper_baseline_v1/data/historical_numeric.json'),
           'data_commit': 'e4b5ddba03b2b88025747e11c6049f8b529a4368',
           'formula_commit': '472545785c936dcfc863d2bc0d6109cf23c7ce62',
           'formula_provenance': 'The official 2026 checkout labels the 615-byte file original EoH paper; its exact bytes are not established as present in 2024.'}

def design_panel():
    p = B / 'paper_design_panel_v1'
    r = read(p / 'report.json'); protocol = read(p / 'protocol_frozen.json')
    if sha(p / 'report.json') != '162a817246a79225d910464c8bcfc877d99fb5804591ad0fb1e03482a2f43b6e':
        raise ValueError('Design report changed')
    gate = read(p / 'numeric_gate.json'); g = gate['result']; post = read(p / 'postcheck.json')
    selected = previous('published_eoh_operational_v1')
    selected |= {x for x in p.iterdir() if x.is_file()}
    selected |= {B / name for name in protocol['source_hashes']}
    selected.add(B / 'published_eoh_readiness/source_provenance.json')
    summary = {'schema': 'urp_paper_design_panel_public_v1', 'study_id': 'p3-paper-design-panel-v1',
               'report_sha256': sha(p / 'report.json'), 'protocol_sha256': sha(p / 'protocol_frozen.json'),
               'counts': {'packing_slots': 15, 'completed_slots': 15, 'unique_instances': 5, 'items_per_instance': 5000,
                          'recorded_complete_assignments': 75000, 'model_requests': 0, 'numerical_gate_workers': 1},
               'data': {'set': 'historical_design_5k', 'capacity': 100, 'instances': protocol['instances'],
                        'scope': 'Full original historical design sequences in arrival order; this is a fixed-policy evaluation, not the earlier 128-item pilot or a reproduced evolutionary search.'},
               'rows': [{**x, 'observation': rel(p / x['observation'])} for x in r['rows']], 'groups': r['groups'],
               'numerical_gate': {**{k: v for k, v in g.items() if k != 'warnings'}, 'warning_count': len(g['warnings']),
                                  'formal_dtype': 'int64 item and residuals; trusted implementation changes only its scalar guard',
                                  'author_bytes_executed': 'Only the exact 615-byte pinned function in the one bounded pre-run numerical gate; formal packing used the trusted reimplementation.',
                                  'scope': 'Saved assertions compare 500 vectors / 592200 scalar pairs bitwise and by first argmax; not an exhaustive proof over all arrays or a second replay of full packing trajectories.'},
               'comparisons': {'formula_fewer_bins_than_BF': 328, 'formula_fewer_bins_than_FF': 352,
                               'formula_bins_above_L1': 68, 'known_optimum_gap': None},
               'table1_diagnostic': read(p / 'table1_mixed_capacity_diagnostic.json'),
               'costs': {'main_stage': r['cost'], 'postcheck_cpu_seconds': post['read_only_summary_cpu_seconds'],
                         'postcheck_wall_seconds': post['read_only_summary_wall_seconds'], 'final_write_reserve_seconds': 2,
                         'scope': r['cost_note'], 'outer_timestamps_and_effective_rlimits_saved': False},
               'limits': protocol['limits'],
               'limitations': ['mean(L1_i/bins_i) and ratio-of-sums L1 excess are different statistics.',
                               'L1 is a lower bound, not a known optimum.',
                               'Formula numeric parity and the design fitness rounded to 0.993 do not reproduce the original LLM search.',
                               'The mixed-capacity Table1 diagnostic recombines saved outcomes with capacities [500,100,100,100,100]; it is not a correct all-instance C500 experiment or proof of original execution bytes.',
                               'Saved assignments were independently checked; the full floating score trajectory was not independently replayed.',
                               'Source-enforced limits and recorded reaping are available, but independent PID/rlimit snapshots and outer timing were not saved.'],
               'evidence': {k: rel(p / v) for k, v in {'full_report': 'report.json', 'protocol': 'protocol_frozen.json', 'numeric_gate': 'numeric_gate.json',
                         'numeric_stdout': 'numeric_gate.stdout.json', 'postcheck': 'postcheck.json', 'source_provenance': 'source_verification.json',
                         'table1_diagnostic': 'table1_mixed_capacity_diagnostic.json', 'results_zh': 'RESULTS_ZH.md', 'runner': 'run_once.py'}.items()}}
    return finish(p, summary, selected, NUMERIC, """# 历史完整设计面板的复现边界

这是 5 条历史 5000 物品序列、容量 100 的 FF/BF/固定公式结果。原始 report、15 份完整分配、数值门槛及源码均保留。旧基线与公式公开资料作为可去重依赖同时提供，不是新运行。

依赖 Python 3.12、NumPy 2.3.5 及 Linux 进程限额。模型、虚拟环境和缓存未提供；无模型依赖。官方公式与历史数据版本分别记录于 dependencies.json。原作者精确源码只在已记录的数值门槛中运行，正式评测使用 int64 输入检查适配的可信重实现。

先按 manifest.json 核验资料。重新运行需在独立新目录重建依赖、重新核验来源及限额并明确选择执行；不要覆盖历史输出或直接重复归档的一次性入口。历史绝对路径和冻结哈希是记录，不保证迁移后原样执行。""")

def typed_tree():
    p = B / 'typed_tree_contract_v1'; run = p / 'runs/typed_tree_pilot_20261005_01'
    r = read(run / 'report.json'); old = read(run / 'summary.json'); freeze = read(p / 'final_freeze.json'); tp = read(p / 'transport_protocol.json')
    if sha(run / 'report.json') != '479e86e69e1d8cbbbaa6c77fcf9fdb1019577133d0739890152e3561a9ddaf02':
        raise ValueError('Typed-tree report changed')
    selected = previous('math_dag_interface_v2_1')
    template = (p / tp['template']['file']).resolve()
    if sha(template) != tp['template']['sha256']:
        raise ValueError('Shared embedded template changed')
    selected.add(template)
    selected |= {p / name for name in freeze['files'] if name != 'PLAN_ZH.md'}
    selected.add(p / 'final_freeze.json')
    selected |= {x for x in run.rglob('*') if x.is_file()}
    for name in freeze['assets']:
        x = Path(name).resolve()
        if x.is_relative_to(U) and '/vendor/' not in str(x) and '__pycache__' not in x.parts:
            selected.add(x)
    requests = []
    for row in r['requests']:
        q = run / row['generation_evidence']
        requests.append({**row, 'generation_evidence': rel(q), 'raw_content': rel(q / 'content.txt'),
                         'raw_http': rel(q / 'response_body.json'), 'compiled_dag': read(q / 'compiled_dag.json'),
                         'original_tree': read(q / 'content.txt'), 'interpretation': old['analytical_behavior'].get(row['id'], 'Fixed target rewritten as 0+0; structure differs, three saved score vectors match.')})
    model_cpu = sum(x['execution']['child_user_cpu_seconds'] + x['execution']['child_system_cpu_seconds'] for x in r['dispatches'] if x['kind'] == 'model')
    score_cpu = sum(x['worker_cpu_seconds'] for x in r['dispatches'] if x['kind'] == 'score')
    deps = {'model': tp['model'], 'runtime': tp['runtime'], 'embedded_label_discrepancy': tp['embedded_label_discrepancy'],
            'template': tp['template'], 'python': '3.12; exact interpreter hash in final_freeze.json', 'numpy': '2.3.5',
            'template_packages': {'Jinja2': '3.1.6', 'MarkupSafe': '3.0.2'},
            'excluded_payloads': 'Model GGUF, llama.cpp binaries/shared libraries, Python environment and package caches must be obtained from their recorded official sources and reverified.',
            'math_evaluator_freeze': freeze['math_evaluator_freeze']}
    summary = {'schema': 'urp_typed_tree_public_v1', 'study_id': 'p3-typed-tree-contract-v1', 'report_sha256': sha(run / 'report.json'),
               'freeze_sha256': sha(p / 'final_freeze.json'), 'state': r['state'],
               'counts': {'model_requests': 4, 'eos': 4, 'tree_and_dag_admissions': 4, 'finite_micro_observations': 12,
                          'packing_calls': 0, 'distinct_reaped_workers': 16, 'events': 32, 'unknown_launch_states': 0},
               'requests': requests, 'observations': [{**x, 'observation': rel(run / x['observation'])} for x in r['ledger']],
               'manual_cases': read(p / 'data/manual_cases.json'), 'contract': read(p / 'protocol.json')['decoding'],
               'fixed_transcription': {'exact_compiled_structure_match': False, 'all_three_saved_scores_match_target': True,
                                       'reason': 'The model expressed zero as 0+0; do not label this exact structural transcription.'},
               'costs': {'outer_accounting': old['outer_accounting'], 'driver_accounting': r['costs'], 'model_server_cpu_seconds': model_cpu,
                         'score_worker_cpu_seconds': score_cpu, 'children_minus_worker_cpu_seconds': r['costs']['children_cpu_seconds'] - model_cpu - score_cpu,
                         'input_tokens': sum(x['metadata']['tokens_evaluated'] for x in r['requests']),
                         'output_tokens_including_eos': sum(x['metadata']['tokens_predicted'] for x in r['requests']),
                         'preparation_charge_cpu_seconds': 100, 'preparation_charge_wall_seconds': 100,
                         'preparation_charge_is_not_measured': True},
               'limits': read(p / 'protocol.json')['settings'],
               'limitations': ['Only four model outputs and twelve handwritten micro-vectors; no historical packing or fitness evaluation.',
                               'The typed tree uses depth2, discrete coefficients, float promotion and at most6 compiled nodes. It is not the same candidate space as the earlier compact4-node JSON DAG.',
                               'Design0 and design1 prefer largest remaining capacity; design2 has BF ordering on the declared positive domain. These are formula-level interpretations, not new packing quality measurements.',
                               'Structural diversity and interface admission do not establish strategy benefit or algorithm invention.',
                               'The 118-second termination trigger and 120-second observed failure check are not hard real-time guarantees; sampled RSS is not hard total-memory isolation.',
                               'Historical prerequisite observations in the package are distinct stages and must not be pooled as new calls.'],
               'evidence': {'full_report': rel(run / 'report.json'), 'journal': rel(run / 'events.jsonl'), 'initial_ledger': rel(run / 'initial_ledger.json'),
                            'outer_accounting': rel(run / 'outer_accounting.json'), 'results_zh': rel(run / 'RESULTS_ZH.md'),
                            'protocol': rel(p / 'protocol.json'), 'source_freeze': rel(p / 'final_freeze.json'), 'compiler': rel(p / 'typed_tree.py')}}
    return finish(p, summary, selected, deps, """# 有类型树接口先导的复现边界

交付保留四份完整请求、原始 HTTP/content、编译后的 DAG、十二微例、事件和计量。原始树由固定 typed_tree.py 编译，随后使用既有固定数学解释器；公开数据中没有任意 Python 候选执行。

模型、官方 llama.cpp 运行包、Python/NumPy/Jinja2 环境不随包提供。精确官方仓库、版本、文件摘要见 dependencies.json 和冻结清单。已有源代码和历史请求可离线检查；重建后需要重新核验依赖、路径、编译器和限额，生成新的环境快照，再由使用者明确选择是否运行新的独立批次。

不要覆盖历史输出、套用旧运行许可或将此四请求并入前一研究。最终 summary 描述完成结果；部分冻结文档的 prepared 字样是运行前状态。早期草案文档未分发，其历史哈希仍可在冻结清单中看到。""")

def parameter_control():
    p = B / 'eoh_parameter_control_v1'; run = p / 'run'; r = read(run / 'report.json'); f = read(p / 'execution_freeze.json')
    if sha(run / 'report.json') != 'f0b460d791a0c27d740b52e12bbca2ccc655861d1c110134179fa9b371883d87':
        raise ValueError('Parameter report changed')
    selected = previous('paper_design_panel_v1')
    selected |= {x for x in p.iterdir() if x.is_file() and x.name not in {'approved_run.json', 'PLAN_ZH.md', 'preparation_manifest.json'}}
    selected |= {x for x in run.iterdir() if x.is_file() and x.name != 'approval_claim.json'}
    selected |= {B / name for name in f['files'] if name != 'eoh_parameter_control_v1/PLAN_ZH.md'}
    candidates = []
    for i, params in enumerate(f['candidates']):
        rows = [x for x in r['rows'] if x['stage'] == 'design' and x['candidate'] == i]
        fit = sum((Fraction(x['L1'], x['used_bins']) for x in rows), Fraction()) / 5
        paths = [run / ('design_%02d_%s.json' % (i, x['index'])) for x in rows]
        assignments = [read(q)['result']['assignment'] for q in paths]
        signature = hashlib.sha256(json.dumps(assignments, separators=(',', ':')).encode()).hexdigest()
        candidates.append({'candidate': i, 'params': params, 'rows': rows, 'sum_bins': sum(x['used_bins'] for x in rows),
                           'sum_L1': sum(x['L1'] for x in rows), 'fitness_fraction': str(fit), 'fitness': float(fit),
                           'assignment_signature': signature, 'observations': [rel(x) for x in paths]})
    best = max(Fraction(x['fitness_fraction']) for x in candidates)
    ties = [x['candidate'] for x in candidates if Fraction(x['fitness_fraction']) == best]
    if ties != [0, 13, 14]:
        raise ValueError('Unexpected tie set')
    test = [x for x in r['rows'] if x['stage'] == 'test']
    summary = {'schema': 'urp_eoh_parameter_control_public_v1', 'study_id': 'p3-eoh-parameter-control-v1',
               'report_sha256': sha(run / 'report.json'), 'freeze_sha256': sha(p / 'execution_freeze.json'), 'state': r['status'],
               'counts': {'candidates': 27, 'design_slots': 135, 'winner_test_slots': 5, 'complete_slots': 140,
                          'recorded_complete_assignments': 700000, 'model_requests': 0, 'ties_at_best_fitness': 3},
               'grid': {'threshold': [2,3,4], 'large_add': [0.6,0.8,1.0], 'exp_offset': [0.4,0.7,1.0], 'small_add_fixed': 0.3},
               'candidates': candidates, 'ties': ties, 'winner': r['winner'], 'winner_params': f['candidates'][r['winner']],
               'winner_design_bins': [x['used_bins'] for x in candidates[0]['rows']], 'winner_design_sum_bins': candidates[0]['sum_bins'],
               'winner_test_rows': test, 'winner_test_sum_bins': sum(x['used_bins'] for x in test), 'winner_test_fitness_fraction': r['test_fitness_fraction'],
               'winner_test_fitness': float(Fraction(r['test_fitness_fraction'])),
               'selection': {'metric': f['metric'], 'tie_rule': f['tie_rule'], 'winner_commit_before_all_test_calls': True,
                             'offset_0_4_assignments_equal_original': candidates[13]['assignment_signature'] == candidates[0]['assignment_signature'],
                             'offset_1_0_assignments_equal_original': candidates[14]['assignment_signature'] == candidates[0]['assignment_signature']},
               'costs': {**r['cost'], 'measured_main_cpu_excluding_preparation_charge': r['cost']['accounted_cpu_seconds'] - 10,
                         'measured_main_wall_excluding_preparation_charge': r['cost']['accounted_wall_seconds'] - 10,
                         'preparation_charge_cpu_seconds': 10, 'preparation_charge_wall_seconds': 10,
                         'slot_cpu_seconds_sum': sum(x['cpu_seconds'] for x in r['rows']),
                         'slot_cpu_scope': 'Dispatch interval includes parent work and child CPU; not pure worker CPU.',
                         'final_write_scope': r['final_snapshot_note'], 'effective_rlimits_and_distinct_pids_saved': False},
               'limits': f['limits'], 'data': {'design': f['design_set'], 'test': f['test_set'], 'capacity': 100,
                         'instances_per_split': 5, 'items_per_instance': 5000, 'test_label': r['test_label']},
               'limitations': ['This is a prespecified local numerical grid on a fixed published expression, not structure search or LLM evolution.',
                               'The original configuration wins a three-way exact fitness tie by the prespecified rule; it is not uniquely best.',
                               'The offset0.4 tied configuration has different saved assignments; offset1.0 has the same assignments as the original. Equal fitness is not universal behavioral equivalence.',
                               'Design and test data are public historical sequences already used in this project; test reuse is exploratory, not a new unbiased holdout.',
                               'The original parameter point is rerun and charged; matching old assignments is a consistency check, not independent new scientific evidence.',
                               'No parameter improvement was observed within this27-point grid; this does not establish global optimality.',
                               'Saved assignments were independently checked without a second floating-policy replay; source-enforced limits and reaping were recorded, but independent PID/rlimit snapshots were not.'],
               'evidence': {'full_report': rel(run / 'report.json'), 'winner_commitment': rel(run / 'winner_commit.json'),
                            'source_freeze': rel(p / 'execution_freeze.json'), 'source_diff': rel(p / 'SOURCE_DIFF.patch'),
                            'formula': rel(p / 'control.py'), 'runner': rel(p / 'run_once.py'), 'tests': rel(p / 'preflight_tests.log')}}
    return finish(p, summary, selected, NUMERIC, """# 固定公式参数网格的复现边界

固定原公式结构，27 组三参数在五条完整历史设计序列上评测；按精确 mean(L1_i/bins_i) 选择，原配置优先打破同分。赢家承诺写盘后，仅评五条已使用过的历史测试序列。全部 140 份分配与逐例标准输出保留。三组同分最优的完整列表和轨迹关系见 summary.json。

依赖 Python 3.12、NumPy 2.3.5 和 Linux 进程限额，不需要模型。数据、固定公式、独立分配检查器、指标、网格、平局规则及源差分均提供；环境和缓存需自行从官方来源重建。execution_freeze.json 是历史运行前的冻结证据，prepared 状态不代表本次没有执行。

早期筹备文本未分发，精确执行协议已完整保存在 execution_freeze.json。重建时在新目录核验依赖、确认限额并生成新的完整快照；由使用者明确决定是否进行新运行。不要使用历史许可或覆盖已保存的 run 目录。此交付不宣称迁移后可直接重放原冻结。""")

if __name__ == '__main__':
    print(json.dumps({'paper_design_panel_v1': design_panel(), 'typed_tree_contract_v1': typed_tree(),
                      'eoh_parameter_control_v1': parameter_control()}, ensure_ascii=False, indent=2))
