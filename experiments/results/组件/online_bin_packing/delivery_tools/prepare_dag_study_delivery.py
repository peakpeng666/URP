"""Data-only publication projection. Never imports the evaluator or runs a model."""
from pathlib import Path
import collections, hashlib, json
ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/'experiments/online_bin_packing/math_dag_evolution_v1'
RUN=BASE/'runs/dag_twogen_20261004_01'
OUT=BASE/'delivery'
OUT.mkdir(exist_ok=True)
def read(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def rel(p): return str(p.relative_to(ROOT))
def write(n,o): (OUT/n).write_text(json.dumps(o,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
r=read(RUN/'report.json'); f=read(BASE/'final_freeze.json'); state=r['state']; requests=state['requests']; outer=read(BASE/'logs/formal_launch_20261004_01_outer.json')
assert sha(BASE/'final_freeze.json')=='036c265d2ba88647a66460ab816609c217d6170de7eb0348f37b73523d3bab39'
assert sha(RUN/'report.json')=='0a5fe5d469f10717fe9493fae81926124cbe24eff70a4c015447cb71b6849fea'
physical={}; compact=[]; diagnostics=[]
for arm in ['shared','evolution','control']:
 rows=[x for x in requests if x['arm']==arm]
 physical[arm]={'requests':len(rows),'input_tokens':sum(x['generation_evidence']['metadata']['tokens_evaluated'] for x in rows),'output_tokens_including_eos':sum(x['generation_evidence']['metadata']['tokens_predicted'] for x in rows),'server_cpu_seconds':sum(x['generation_evidence']['execution']['child_user_cpu_seconds']+x['generation_evidence']['execution']['child_system_cpu_seconds'] for x in rows),'summed_server_lifetime_wall_seconds':sum(x['generation_evidence']['execution']['whole_process_lifetime_wall_seconds'] for x in rows),'statuses':dict(collections.Counter(x['status'] for x in rows))}
for x in requests:
 ev=x['generation_evidence']; path=RUN/ev['directory']; raw=(path/'content.txt').read_text(); md=ev['metadata']; ex=ev['execution']; entry={k:x[k] for k in ['slot_id','arm','generation','operator','seed','status','reason','parent_source_ids']}
 entry.update(input_tokens=md['tokens_evaluated'],output_tokens_including_eos=md['tokens_predicted'],stop_type=md['stop_type'],server_cpu_seconds=ex['child_user_cpu_seconds']+ex['child_system_cpu_seconds'],server_lifetime_wall_seconds=ex['whole_process_lifetime_wall_seconds'],source_bytes=len(raw.encode()),raw_content=rel(path/'content.txt'),raw_content_sha256=sha(path/'content.txt'),raw_http=rel(path/'response_body.json'),raw_http_sha256=sha(path/'response_body.json'),request=rel(path/'request.json'),decoded=rel(path/'decoded.json'),execution=rel(path/'result.json'))
 compact.append(entry); diagnostic={'slot_id':x['slot_id'],'frozen_outcome':x['status'],'reason':x['reason'],'content_sha256':sha(path/'content.txt'),'not_scored_or_repaired':True}
 try:
  obj=json.loads(raw); diagnostic.update(whole_json_parses=True,nodes=len(obj['nodes']),constant_count=len(obj['constants']),description_chars=len(obj['description']))
  diagnostic['first_frozen_type_rejection']={'node_index':2,'node':obj['nodes'][2],'operands':'two declared i32 scalar constants; gt requires a vector operand'}
  diagnostic['additional_data_only_reference_findings']={'undefined_constant_references':sorted({a for n in obj['nodes'] for a in n[1:] if isinstance(a,str) and a.startswith('c') and a[1:].isdigit() and int(a[1:])>=len(obj['constants'])}),'note':'Secondary text diagnosis only; original admission stopped at node2 and was not rerun.'}
 except json.JSONDecodeError as e:
  diagnostic.update(whole_json_parses=False,json_error=e.msg,error_character_offset=e.pos,characters=len(raw))
 diagnostics.append(diagnostic)
write('offline_diagnosis.json',{'scope':'Whole saved content parsing and declared references only; no model call, candidate execution, repair, rescoring or retrospective admission. Limit outcomes remain unchanged.','counts':{'limit_outputs':20,'limit_outputs_incomplete_json':20,'eos_complete_json':2,'first_type_rejections':2},'requests':diagnostics})
models=[d for d in r['dispatches'] if d['kind']=='model']; scores=[d for d in r['dispatches'] if d['kind']=='score']
server_cpu=sum(v['server_cpu_seconds'] for v in physical.values()); token_cpu=sum(d['preparation']['tokenization']['worker_cpu_seconds'] for d in models); score_cpu=sum(d['worker_cpu_seconds'] for d in scores)
knownprep=r['preparation_costs']['known_cpu_seconds']+f['snapshot_hash_cpu_seconds']
summary={'schema':'urp_math_dag_study_public_v1','study_id':'p3_restricted_dag_two_generation_v1','review_state':'accepted after independent saved-output reconciliation','metric':'Seeded restricted-DAG teaching study; generation-interface feasibility and descriptive seed-inclusive selection, not evidence of evolutionary search superiority/equivalence.','source_freeze_sha256':sha(BASE/'final_freeze.json'),'report_sha256':sha(RUN/'report.json'),'state':state['state'],'started_utc':outer['started_utc'],'ended_utc':outer['ended_utc'],'counts':{'physical_model_requests':22,'shared_initialization':2,'evolution_exclusive':10,'control_exclusive':10,'opportunities_per_arm_including_shared':12,'model_limit_stops':20,'eos_type_rejections':2,'admitted_generated_graphs':0,'generated_candidate_scoring_requests':0,'scoring_requests':32,'scoring_placements':4096,'ledger_rows':208,'candidate_rows_not_run':176,'events':111,'generation2_generated_parent_inputs':0,'unknown_model_launch_states':r['unknown_model_launch_states']},'physical_exclusive_cost_groups':physical,'physical_model_totals':{'input_tokens':sum(v['input_tokens'] for v in physical.values()),'output_tokens_including_eos':sum(v['output_tokens_including_eos'] for v in physical.values()),'server_cpu_seconds':server_cpu,'summed_server_lifetime_wall_seconds':sum(v['summed_server_lifetime_wall_seconds'] for v in physical.values())},'arms':r['summary']['arms'],'fixed_comparators':r['summary']['fixed_comparators'],'pairs':r['summary']['pairs'],'requests':compact,'data':{'design_cases':4,'validation_cases':4,'unique_underlying_sequences_total':4,'unique_underlying_sequences_per_split':2,'prefix_items':128,'capacities':[100,500],'panel_sha256':f['case_panel_sha256'],'validation_scope':'Held out from this run’s fitness/selection until both winner commitments; publicly available/reused historical prefixes, not previously unseen/private data. No significance or generalization claim.'},'costs':{'formal_measured':r['costs'],'formal_worker_cpu_breakdown':{'model_servers':server_cpu,'tokenizers':token_cpu,'score_workers':score_cpu,'sum':server_cpu+token_cpu+score_cpu,'children_rusage_minus_sum_seconds':r['costs']['children_cpu_seconds']-server_cpu-token_cpu-score_cpu},'outer_launcher_wall_seconds':outer['outer_wall_seconds'],'known_preparation_cpu_including_final_freeze':knownprep,'known_preparation_wall_sum_different_scopes':r['preparation_costs']['known_wall_seconds_sum_different_scopes']+f['snapshot_hash_wall_seconds'],'measured_known_formal_plus_preparation_cpu_seconds':knownprep+r['costs']['supervisor_cpu_seconds']+r['costs']['children_cpu_seconds'],'preparation_debit':{'cpu_seconds':200,'active_wall_seconds':200},'debit_is_not_measured_cost_or_upper_bound_on_unknown_history':True,'preparation_detail':r['preparation_costs'],'final_snapshot_measured_cpu_seconds':f['snapshot_hash_cpu_seconds'],'final_snapshot_measured_wall_seconds':f['snapshot_hash_wall_seconds'],'shared_prerequisites_count_once_projectwide':True,'supervisor_peak_rss_kib':r['supervisor_peak_rss_kib'],'max_model_worker_rusage_rss_bytes':max(d['execution']['child_ru_maxrss_bytes'] for d in models),'resource_caveat':'Per-process AS and CPU limits, sampled RSS, observed/reserved aggregate budgets; not a kernel hard total-memory/process-tree budget.'},'identity':{'model':read(BASE/'protocol.json')['model'],'runtime':read(BASE/'protocol.json')['runtime'],'embedded_label_discrepancy':read(BASE/'protocol.json')['embedded_label_discrepancy'],'schema_sha256':f['schema_sha256'],'output_token_cap':384,'context':2048,'thread_scope':'2 inference/prefill threads plus1 HTTP control thread; no paid API or GPU'},'limitations':['No generated DAG was admitted; no evolutionary-versus-control heuristic quality conclusion is possible.','Both winners are the same predeclared handwritten BF seed; do not credit seed performance to the LLM.','Generation2 received no generation1-generated parent; realized adaptive feedback did not occur.','20 raw capped outputs are incomplete JSON; the2 EOS outputs violate scalar/vector typing. No output was repaired, extracted or rescored.','Five operator labels describe prompts, not demonstrated semantic mutations or novel algorithms.','22 physical requests differ from12 opportunities in each arm because two shared initializations overlap; arm subtotals cannot be added without deduplication.','Equal request counts are not equal tokens/CPU. One seeded search per arm is not independent replication.','The Qwen4B quantized local runtime is different from the original paper model and Python search space.'], 'evidence':{'full_report':rel(RUN/'report.json'),'initial_ledger':rel(RUN/'initial_ledger.json'),'journal':rel(RUN/'events.jsonl'),'winner_commitment':rel(RUN/'winner_commitment.json'),'outer_timing':rel(BASE/'logs/formal_launch_20261004_01_outer.json'),'source_freeze':rel(BASE/'final_freeze.json'),'protocol':rel(BASE/'protocol.json'),'data_provenance':rel(BASE/'DATA_PROVENANCE.md'),'offline_diagnosis':rel(OUT/'offline_diagnosis.json')}}
write('summary.json',summary)
# Publication allowlist: original evidence/source, no weights/environments/bytecode/private records.
selected=set()
def add(p):
 if p.is_file() and '__pycache__' not in p.parts and p.suffix not in ('.pyc','.so'): selected.add(p.resolve())
for name in f['files']: add(BASE/name)
for name in ['final_freeze.json','logs/formal_launch_20261004_01_outer.json','logs/formal_launch_20261004_01.log']: add(BASE/name)
for p in RUN.rglob('*'): add(p)
M=BASE.parent/'math_dag_v1'; mf=read(M/'preparation_freeze.json')
for name in mf['files']: add(M/name)
add(M/'preparation_freeze.json')
for name in mf['references']: add(Path(name))
for p in (M/'results/handwritten_20261004_01').rglob('*'): add(p)
for p in (M/'logs').rglob('*'): add(p)
# The three shared prerequisite cost originals are data evidence only.
for en in r['preparation_costs']['entries']:
 if en.get('shared_prerequisite'): add(ROOT.parent/en['source'])
add(Path(__file__))
for p in OUT.iterdir():
 if p.name!='manifest.json': add(p)
files=[{'path':rel(p),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(selected)]
assert not any(any(s in x['path'] for s in ['private_','authorization_uses','__pycache__','/vendor/']) for x in files)
manifest={'schema':'urp_public_delivery_v1','study_id':summary['study_id'],'root':'URP','files':files,'payload_files':len(files),'payload_bytes':sum(x['bytes'] for x in files),'summary':rel(OUT/'summary.json'),'historical_report_sha256':summary['report_sha256'],'frozen_study_sha256':summary['source_freeze_sha256'],'exclusions':['model weights and runtime/dependency environments','bytecode caches','run authorization records','internal review and coordination material'],'reproduction_note':'Historical evidence retained exactly. Rebuilding dependencies requires a fresh environment-specific verification snapshot and user-controlled execution authorization; old one-use execution must never be replayed.'}
write('manifest.json',manifest)
print(json.dumps({'manifest_sha256':sha(OUT/'manifest.json'),'summary_sha256':sha(OUT/'summary.json'),'files':len(files),'bytes':manifest['payload_bytes'],'summary_bytes':(OUT/'summary.json').stat().st_size}))
