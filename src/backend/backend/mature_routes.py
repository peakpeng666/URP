"""Explicit vrptw-mature-solver-v1 archive adapter; source archives stay unchanged."""
import json
import tempfile
from collections import Counter
from pathlib import Path
from .store import StoreError, canonical, identifier, no_secrets, read_artifact, sha
from .routes import INDEX_ID, SEMANTICS, import_vrptw
from .route_replay import replay, verify_recorded, vehicles_from_audit

FORMAT = 'vrptw-mature-solver-v1'
FILES = ('inputs.json','results.jsonl','evaluated_results.json','map_backend.json','protocol.json',
    'freeze.json','verification.json','checker_tests.json','checker.py','environment.json','requests.json',
    'encoded_inputs.json','parameters_250ms.textproto','parameters_1000ms.textproto',
    'reference/inputs.json','reference/protocol.json','reference/freeze.json','reference/routes.jsonl')
OUTCOMES = {'find','no_solution_in_budget','fail_timeout','error','find_but_checker_rejected'}


def aid(name):return name.replace('/','-').replace('.','-')
def jsonl(data):
    lines=data.splitlines()
    if any(not line.strip() for line in lines):raise StoreError('invalid_route_source','JSONL 不接受空行。')
    values=[json.loads(line) for line in lines]
    for value in values:no_secrets(value)
    return lines,values


def normalize_mature(blobs):
    data={n:json.loads(b) for n,b in blobs.items() if n.endswith('.json')}
    source_map, inputs, protocol, freeze = (data[n] for n in ['map_backend.json','inputs.json','protocol.json','freeze.json'])
    lines, results = jsonl(blobs['results.jsonl'])
    _, references = jsonl(blobs['reference/routes.jsonl'])
    input_hash=sha(blobs['inputs.json'])
    if source_map.get('schema')!=FORMAT:raise StoreError('unsupported_route_format','需要 vrptw-mature-solver-v1 格式。')
    if source_map.get('synthetic_coordinates') is not True or source_map.get('distance_time_units')!='Arbitrary Euclidean units; speed1; not real latitude/longitude, road travel or traffic':
        raise StoreError('unsupported_route_semantics','当前格式仅支持合成欧氏坐标和速度1。')
    if (source_map['source_input_sha256']!=input_hash or blobs['inputs.json']!=blobs['reference/inputs.json']
            or data['reference/freeze.json']['sha256']['inputs.json']!=input_hash
            or data['verification.json']['original_input_sha256']!=input_hash):
        raise StoreError('input_hash_mismatch','新档、参考问题和地图的输入身份不一致。')
    for name,digest in freeze['sha256'].items():
        if name in blobs and sha(blobs[name])!=digest:raise StoreError('frozen_hash_mismatch',f'冻结哈希不一致：{name}')
    for name in ['protocol.json','inputs.json','checker.py','requests.json','encoded_inputs.json','environment.json','parameters_250ms.textproto','parameters_1000ms.textproto']:
        if freeze['sha256'].get(name)!=sha(blobs[name]):raise StoreError('frozen_hash_mismatch',f'缺失或不同的冻结身份：{name}')
    problem_hash=sha(blobs['reference/protocol.json'])
    if data['reference/freeze.json']['sha256']['protocol.json']!=problem_hash:
        raise StoreError('frozen_hash_mismatch','参考问题协议哈希不一致。')
    reference_protocol=data['reference/protocol.json']
    if (reference_protocol['input']['distance']!='Euclidean in arbitrary distance units; speed=1; no rounding during optimization'
            or reference_protocol['input']['time_window_semantics']!='Inclusive bounds on START OF SERVICE; wait allowed; travel/service nonnegative; all routes return to depot'):
        raise StoreError('unsupported_route_semantics','参考问题不符合连续欧氏距离合同。')
    if [i['input'] for i in source_map['instances']]!=inputs:
        raise StoreError('source_mismatch','地图输入与 inputs.json 不一致。')
    mapped=sorted([r for i in source_map['instances'] for r in i['runs']],key=lambda r:r['sequence'])
    evaluated=data['evaluated_results.json']
    if mapped!=evaluated or len(results)!=len(evaluated):raise StoreError('source_mismatch','地图、评估记录与原始记录不一致。')
    requests=data['requests.json']
    if len(requests)!=len(results):raise StoreError('source_mismatch','请求数与结果数不一致。')
    instances={}
    for i,item in enumerate(inputs):
        instance_id=identifier(item['id'])
        if instance_id in instances:raise StoreError('duplicate_input','输入 ID 重复。')
        instances[instance_id]={**item,'input_provenance':{'artifact_id':'inputs-json','locator':f'/{i}',
            'input_file_sha256':input_hash,'instance_sha256':sha(canonical(item).encode()),
            'instance_hash_source':'derived: SHA256 of canonical UTF-8 JSON (sorted keys, compact separators, ensure_ascii=False)'}}
    oracle={}
    for i,row in enumerate(references,1):
        if row['method']=='oracle_full':
            if row['instance'] in oracle:raise StoreError('duplicate_reference','重复的参考 oracle 记录。')
            if row['status'] not in {'optimal','proven_infeasible'}:raise StoreError('invalid_reference','参考 oracle 状态不支持。')
            if row['instance'] not in instances:raise StoreError('invalid_reference','参考 oracle 输入未知。')
            if row['status']=='proven_infeasible':
                if row['routes'] is not None or row['audit'] is not None or row['full_oracle_objective'] is not None:
                    raise StoreError('invalid_reference','无解 oracle 记录必须没有路线、审计和目标。')
            else:
                if row['routes'] is None or row['audit'] is None or row['full_oracle_objective'] is None:
                    raise StoreError('invalid_reference','可行 oracle 缺少完整路线见证。')
                reference_audit=replay(instances[row['instance']],row['routes'])
                verify_recorded(reference_audit,row['audit'],'reference.audit')
                if not reference_audit['full_service_feasible']:raise StoreError('invalid_reference','参考 oracle 不是合法全服务见证。')
                verify_recorded(reference_audit['total_distance'],row['full_oracle_objective'],'reference.objective')
            oracle[row['instance']]={'feasible':row['status']=='optimal','objective':row['full_oracle_objective'],
                'source':{'artifact_id':'reference-routes-jsonl','locator':f'line {i}'}}
    if set(oracle)!=set(instances):raise StoreError('source_mismatch','参考 oracle 与输入集合不同。')
    for item in source_map['instances']:
        if item['reference_oracle_full_feasible'] is not oracle[item['input']['id']]['feasible']:
            raise StoreError('source_mismatch','地图的原问题可行性与参考 oracle 不同。')
    runs={};replayed=0
    for i,(row,enriched,request,line) in enumerate(zip(results,evaluated,requests,lines),1):
        if any(enriched.get(k)!=v for k,v in row.items()) or any(row.get(k)!=v for k,v in request.items()):
            raise StoreError('source_mismatch','原始结果、请求或评估记录不一致。')
        run_id=identifier(row['run_id']);instance_id=identifier(row['instance'])
        if run_id in runs or instance_id not in instances:raise StoreError('invalid_run_identity','运行 ID 重复或输入未知。')
        instance=instances[instance_id];reference=oracle[instance_id]
        if enriched['reference_oracle_full_feasible'] is not reference['feasible']:
            raise StoreError('source_mismatch','新记录的原问题可行性与参考 oracle 不同。')
        budget=row['budget_ms']
        if isinstance(budget,bool) or budget not in protocol['budgets_ms'] or budget not in {250,1000}:
            raise StoreError('invalid_budget','预算不属于本格式冻结的 250/1000ms 两档。')
        outcome=row['outcome'];routes=row['routes'];saved=row['audit']
        if outcome not in OUTCOMES:raise StoreError('invalid_run_status','未支持的成熟求解器 outcome。')
        audit=None
        if routes is None:
            if saved is not None or row['assignment_returned'] is not False or outcome in {'find','find_but_checker_rejected'}:
                raise StoreError('invalid_run_status','无候选结果与 assignment/outcome 不一致。')
            state='no_solution' if outcome!='error' else 'unknown'
        else:
            if row['assignment_returned'] is not True or outcome not in {'find','find_but_checker_rejected'}:
                raise StoreError('invalid_run_status','有候选结果与 assignment/outcome 不一致。')
            audit=replay(instance,routes);verify_recorded(audit,saved);replayed+=1
            state='feasible' if audit['full_service_feasible'] else ('partial' if audit['route_feasible'] else 'invalid')
            if (outcome=='find') != audit['full_service_feasible']:
                raise StoreError('invalid_run_status','find 只能代表经独立回放验证的全服务方案。')
        if audit and audit['full_service_feasible'] and not reference['feasible']:
            raise StoreError('reference_conflict','合法全服务见证与参考 oracle 不可行标签冲突。')
        expected_gap=(audit['total_distance']/reference['objective']-1)*100 if audit and audit['full_service_feasible'] and reference['objective'] is not None else None
        verify_recorded(expected_gap,enriched['full_gap_original_percent'],'full_gap_original_percent')
        input_ref=instance['input_provenance']
        runs[run_id]={'run_id':run_id,'instance_id':instance_id,'method':'ortools_routing',
            'algorithm':{'id':'ortools_routing','version':data['environment.json']['ortools'],
                'parameters_sha256':freeze['sha256'][f'parameters_{budget}ms.textproto']},
            'budget':{'value':budget,'unit':'milliseconds','scope':'per_call_search_wall_clock'},
            'geometry':instance['geometry'],'level':instance['level'],'stratum':instance['stratum'],
            'source_status':outcome,'execution_status':'failed' if outcome=='error' else 'completed',
            'solution_status':state,'full_service_success':state=='feasible',
            'solver_error':row.get('error') if outcome=='error' else None,
            'solver_status':{'code':row['ortools_status'],'name':row['ortools_status_name'],
                             'assignment_returned':row['assignment_returned'],'outcome':outcome},
            'problem_feasibility':{'status':'feasible' if reference['feasible'] else 'infeasible',
                'source':reference['source'],'interpretation':'reference exact oracle, not a solver FAIL inference'},
            'routes':routes,'vehicles':vehicles_from_audit(instance,audit),
            'unserved_task_ids':audit['missing'] if audit else None,
            'unserved_semantics':'checker missing nodes' if audit else 'no returned candidate; missing-node list is not applicable',
            'metrics':{**{k:row[k] for k in ['solve_wall_s','solve_cpu_s','model_wall_s','model_cpu_s','total_wall_s','total_cpu_s','objective_integer']},
                'full_gap_original_percent':enriched['full_gap_original_percent'],
                'full_oracle_objective':reference['objective']},
            'encoded_cumul_ranges':row['encoded_cumul_ranges'],
            'encoded_cumul_semantics':'integer model feasible ranges; not observed continuous arrival/service times',
            'checker':{'status':'no_candidate' if audit is None else ('passed' if audit['route_feasible'] else 'violations'),
                'source':'backend continuous replay verified against recorded independent checker',
                'implementation_sha256':freeze['sha256']['checker.py'],
                'replay_implementation':'backend.route_replay-v1','recomputed_at_import':audit is not None,
                'route_feasible':audit['route_feasible'] if audit else None,
                'full_service_feasible':audit['full_service_feasible'] if audit else False,'audit':audit,'recorded_audit':saved},
            'provenance':{'source_run_id':run_id,'run_id_source':'native results.jsonl run_id, scoped to experiment',
                'run_sha256':sha(line),'run_hash_source':'derived: exact results.jsonl line bytes excluding newline',
                'artifact_id':'results-jsonl','locator':f'line {i}',
                'spec_id':reference_protocol['study_id'],'spec_sha256':problem_hash,'problem_spec_sha256':problem_hash,
                'research_protocol_id':protocol['study_id'],'research_protocol_sha256':sha(blobs['protocol.json']),
                'encoded_input_sha256':freeze['sha256']['encoded_inputs.json'],
                'input_artifact_id':'inputs-json','input_locator':input_ref['locator'],
                'input_file_sha256':input_hash,'instance_sha256':input_ref['instance_sha256'],
                'instance_hash_source':input_ref['instance_hash_source']}}
    verification=data['verification.json']
    if verification['records_checked']!=len(runs) or verification['returned_solutions_independently_replayed']!=replayed:
        raise StoreError('source_mismatch','验证报告数量与已导入/回放数量不一致。')
    return {'schema_version':1,'source_format':FORMAT,'semantics':SEMANTICS,'instances':instances,'runs':runs,
        'summary':{'instance_count':len(instances),'run_count':len(runs),
            'solution_status_counts':dict(Counter(r['solution_status'] for r in runs.values()))},
        'verification':{'recorded_report':verification,'source_artifact_id':'verification-json',
            'backend_replayed_candidates':replayed,'scope':'continuous witness replay only; no solver execution or optimality/infeasibility proof'},
        'sources':{n:sha(b) for n,b in blobs.items()},
        'problem_spec_sha256':problem_hash,'input_file_sha256':input_hash,
        'research_protocol_sha256':sha(blobs['protocol.json'])}


def import_mature(store, source, experiment_id='vrptw-mature-20261007'):
    identifier(experiment_id);source=Path(source).resolve()
    blobs={n:read_artifact(source,{'path':n}) for n in FILES}
    try:index=normalize_mature(blobs)
    except (KeyError,TypeError,ValueError) as exc:
        if isinstance(exc,StoreError):raise
        raise StoreError('invalid_route_source','成熟求解器档案字段无效。') from exc
    # Prevent an unrelated dataset being silently substituted under an existing ID.
    try:existing=store.get(experiment_id)
    except StoreError as exc:
        if exc.status!=404:raise
        existing=None
    if existing and (existing.get('routing',{}).get('source_format')!=FORMAT or existing['provenance']['input_sha256']!=index['input_file_sha256']):
        raise StoreError('experiment_identity_mismatch','此实验 ID 已属于其他格式或输入集合；请使用独立 ID。',409)
    artifacts=[{'id':aid(n),'path':n,'media_type':'application/json' if n.endswith('.json') else 'text/plain; charset=utf-8','role':'source_evidence'} for n in FILES]
    artifacts.append({'id':INDEX_ID,'path':'route-index.json','media_type':'application/json','role':'derived_read_index'})
    descriptor={'schema_version':1,'id':experiment_id,'title':'VRPTW 成熟求解器冻结实验','domain':'VRPTW','kind':'recorded_routes',
        'status':'completed','started_at':None,'finished_at':None,'failure_reason':None,
        'counts':[{'unit':'instance','value':len(index['instances']),'scope':'shared_frozen_input'},
                  {'unit':'run','value':len(index['runs']),'scope':'imported_route_record'}],
        'parameters':{'route_semantics':SEMANTICS,'source_format':FORMAT},'metrics':[],'artifacts':artifacts,
        'notes':['只导入原档并重算连续路线见证；不运行求解器。','no_solution 不等于原问题不可行。','整数模型范围不当作实际到达时刻。'],
        'provenance':{'source_files':index['sources'],'input_sha256':index['input_file_sha256'],
            'spec_sha256':index['problem_spec_sha256'],'research_protocol_sha256':index['research_protocol_sha256']},
        'routing':{'schema_version':1,'source_format':FORMAT,'index_artifact_id':INDEX_ID,
            'read_api':f'/api/experiments/{experiment_id}/runs','semantics':SEMANTICS,**index['summary']}}
    with tempfile.TemporaryDirectory(prefix='mature-route-import-') as directory:
        root=Path(directory)
        for name,content in blobs.items():
            path=root/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(content)
        (root/'route-index.json').write_text(canonical(index)+'\n',encoding='utf-8')
        (root/'experiment.json').write_text(canonical(descriptor),encoding='utf-8')
        return store.import_package(root)


def import_route_archive(store, source, format, experiment_id=None, input_dir=None):
    from .public_routes import FORMATS, import_public
    if format in FORMATS:return import_public(store,source,format,experiment_id,input_dir)
    if format=='vrptw-frozen-v1':return import_vrptw(store,source,experiment_id or 'vrptw-20261007')
    if format==FORMAT:return import_mature(store,source,experiment_id or 'vrptw-mature-20261007')
    raise StoreError('unsupported_route_format','未知的明确档案格式。')
