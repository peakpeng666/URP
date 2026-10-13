"""Two explicit archived Solomon-candidate formats; no solver or archive code execution."""
import json
import math
import re
import tempfile
from collections import Counter
from pathlib import Path
from .store import StoreError, canonical, identifier, no_secrets, read_artifact, sha
from .routes import INDEX_ID, SEMANTICS
from .route_replay import verify_recorded
from .archived_solomon_checker import check

PUBLIC_FORMAT = 'vrptw-archived-solomon-v1'
PORTFOLIO_FORMAT = 'vrptw-solver-portfolio-v1'
FORMATS = (PUBLIC_FORMAT, PORTFOLIO_FORMAT)
PROTOCOL_HASHES = {
    PUBLIC_FORMAT: '60642717cdd150f671d8568dc8076d35ebac96b874cafa8f56f16c133fdb2c41',
    PORTFOLIO_FORMAT: '3a70a550df1d4993cf0707f9b5ca78ecf1bef0d9c884c3fd33999966d0ecc22a',
}
PARAMETER_HASHES = {
    '250ms': '463640949b5a83b29467b9dd8e80fc14fba3fdd9bafb48d5dbc5c874197c4e3c',
    '1000ms': '111843dd0a7445e8d6ca044adf330ca9a937fabee1062ba17835b1f6a7bad102',
    'pci250': '463640949b5a83b29467b9dd8e80fc14fba3fdd9bafb48d5dbc5c874197c4e3c',
    'pca250': '7bcf05ef029775928ee89c37594b85e9ead96792ab8396e3a3f1b688cfba6729',
    'sav250': '7d8790bc752417c81dbb2b869d7502170247c619dd5830b18470cdc84bca84a2',
    'pci750': '433987c5f57ee2cc67c7032e403f9e45cdbc009be5892a462016d56e9f0d6cab',
}
CHECKER_SHA256 = '67ad3171ff4a7b736313226c3e9540d40b8d5021fcbf33acd262a20c86ccf8d5'
CONFIGS = {
    'pci250': (250, 'PARALLEL_CHEAPEST_INSERTION'),
    'pca250': (250, 'PATH_CHEAPEST_ARC'),
    'sav250': (250, 'SAVINGS'),
    'pci750': (750, 'PARALLEL_CHEAPEST_INSERTION'),
}
ROUTE_SEMANTICS = {**SEMANTICS, 'coordinate_system': 'archived_benchmark_cartesian',
    'objective': 'distance_only_with_fixed_vehicle_upper_bound',
    'all_customers_required': True, 'official_byte_identity': 'unverified',
    'bks_gap': 'not applicable: official vehicles-first objective differs',
    'routes': 'returned nonempty customer sequences; native vehicle IDs are in vehicles; depots in path_node_ids'}
PROBLEM_SPEC = {'schema': 'archived-solomon-continuous-distance-only-v1',
    'semantics': ROUTE_SEMANTICS, 'start_time': 0, 'return_by_depot_due': True,
    'capacity': 'original file capacity per vehicle', 'vehicle_limit': 'original file K'}
PROBLEM_SHA256 = sha(canonical(PROBLEM_SPEC).encode())


def aid(name):
    return name.replace('/', '-').replace('.', '-')


def require(condition, code, message):
    if not condition:
        raise StoreError(code, message)


def jsonl(blob):
    lines = blob.splitlines()
    require(all(line.strip() for line in lines), 'invalid_route_source', 'JSONL 不接受空行。')
    rows = [json.loads(line) for line in lines]
    for row in rows:
        no_secrets(row)
    return lines, rows


def parse_input(blob, name, manifest):
    """Equivalent to the archived integer parser, without importing its solver module."""
    lines = blob.decode('utf-8').splitlines()
    instance_id = identifier(Path(name).stem)
    require(lines[0].strip().lower() == instance_id, 'input_identity_mismatch', '实例名与文件名不同。')
    position = next(i for i, line in enumerate(lines) if line.strip() == 'VEHICLE')
    fleet, capacity = map(int, lines[position + 2].split())
    nodes = []
    for line in lines:
        parts = line.split()
        if len(parts) == 7 and all(re.fullmatch(r'-?\d+', part) for part in parts):
            nodes.append(dict(zip(('id', 'x', 'y', 'demand', 'ready', 'due', 'service'), map(int, parts))))
    require([n['id'] for n in nodes] == list(range(101)), 'invalid_inputs', '需要按原ID排序的100客户与仓库。')
    require(fleet > 0 and capacity > 0 and all(n['demand'] >= 0 and n['demand'] <= capacity
        and 0 <= n['ready'] <= n['due'] and n['service'] >= 0 for n in nodes), 'invalid_inputs', '原始约束无效。')
    require(nodes[0]['demand'] == nodes[0]['ready'] == nodes[0]['service'] == 0,
            'unsupported_route_semantics', '需要零需求、零服务且0时刻开放的仓库。')
    family = re.fullmatch(r'(rc|r|c)([12])\d{2}', instance_id)
    require(family is not None, 'invalid_inputs', '不支持此实例命名。')
    parsed = {'id': instance_id, 'family': (family[1] + family[2]).upper(),
              'vehicles': fleet, 'capacity': capacity, 'nodes': nodes}
    require(sha(canonical(parsed).encode()) == manifest['semantic_sha256'], 'input_hash_mismatch', '解析输入哈希不同。')
    require((manifest['family'], manifest['n_customers'], manifest['vehicle_limit'], manifest['capacity'], manifest['depot_due'])
            == (parsed['family'], 100, fleet, capacity, nodes[0]['due']), 'source_mismatch', '输入manifest字段与原文不同。')
    require(encoded_hash(nodes) == manifest['encoded_sha256'], 'encoded_input_mismatch', '整数编码输入哈希不同。')
    geometry = sha(canonical({'depot': [nodes[0]['x'], nodes[0]['y']],
                'customers': sorted([n['x'], n['y']] for n in nodes[1:])}).encode())
    original = {'fleet': fleet, 'capacity': capacity,
                'nodes': {n['id']: [n[k] for k in ('x', 'y', 'demand', 'ready', 'due', 'service')] for n in nodes}}
    normalized = {**parsed, 'nodes': [{**n, 'window': [n['ready'], n['due']]} for n in nodes],
        'depart_time': 0, 'return_deadline': nodes[0]['due'], 'geometry': geometry, 'level': None, 'stratum': parsed['family'],
        'input_provenance': {'artifact_id': aid('protocol/input_manifest.json'), 'locator': name,
            'input_file_sha256': manifest['sha256'], 'instance_sha256': manifest['semantic_sha256'],
            'instance_hash_source': 'original manifest semantic_sha256, checked against parsed canonical JSON',
            'encoded_input_sha256': manifest['encoded_sha256'], 'encoded_hash_recomputed': True, 'original_input_redistributed': False,
            'official_byte_identity': 'unverified'}}
    return original, normalized


def encoded_hash(nodes):
    cost, travel = [], []
    for a in nodes:
        c, t = [], []
        for b in nodes:
            z = ((a['x']-b['x'])**2 + (a['y']-b['y'])**2) * 10**12
            s = math.isqrt(z)
            c.append(s + int(4*z >= (2*s+1)**2))
            t.append(s + int(s*s < z))
        cost.append(c); travel.append(t)
    return sha(canonical({'cost_nearest':cost,'travel_ceil':travel,
        'service_exact':[n['service']*1000000 for n in nodes]}).encode())


def objective_check(original, routes):
    """Exact integer rounding; checks archived objective, not a solver invocation."""
    objective, arcs = 0, 0
    for route in routes:
        for a, b in zip(route['nodes'], route['nodes'][1:]):
            x, y = original['nodes'][a], original['nodes'][b]
            z = ((x[0]-y[0])**2 + (x[1]-y[1])**2) * 10**12
            s = math.isqrt(z)
            objective += s + int(4*z >= (2*s+1)**2)
            arcs += 1
    return objective, arcs


def normalize_witness(instance, routes, recorded):
    """Map the original checker's result into the established route API fields."""
    nodes = {n['id']: n for n in instance['nodes']}
    seen = [n for r in routes for n in r['nodes'][1:-1]]
    missing = sorted(set(nodes) - {0} - set(seen))
    errors = recorded['errors']
    route_feasible = not any(not e.startswith('missing customers:') for e in errors)
    state = 'feasible' if recorded['valid'] else ('partial' if route_feasible else 'invalid')
    vehicles = []
    schedule_index = 0
    for source in routes:
        # The original checker omits structurally invalid route schedules. Do not shift vehicle IDs.
        if schedule_index >= len(recorded['route_audits']):
            continue
        audit = recorded['route_audits'][schedule_index]
        if source['nodes'] != audit['nodes']:
            continue
        schedule_index += 1
        load, stops = 0, []
        for sequence, step in enumerate(audit['steps'][:-1], 1):
            node = nodes[step['node']]
            before = load
            load += node['demand']
            start = step['service_start']
            stops.append({'node': node['id'], 'sequence': sequence, 'arrival': step['arrival'],
                'wait': start-step['arrival'], 'start': start, 'service_start': start,
                'depart': start+node['service'], 'window_open': node['ready'], 'window_close': node['due'],
                'lateness': max(0.0, -step['margin']), 'demand': node['demand'], 'leg_distance': step['leg'],
                'load_before': before, 'load_after': load, 'onboard_load': None})
        path = source['nodes']
        vehicles.append({'vehicle_id': source['vehicle'], 'vehicle': source['vehicle'],
            'route': path[1:-1], 'path_node_ids': path,
            'path_coordinates': [[nodes[n]['x'], nodes[n]['y']] for n in path],
            'path_semantics': 'straight Euclidean segments including depot return; not road geometry',
            'load': audit['load'], 'load_semantics': ROUTE_SEMANTICS['load'],
            'overload': max(0, audit['load']-instance['capacity']), 'distance': audit['distance'],
            'return_time': audit['return_time'], 'return_leg_distance': audit['steps'][-1]['leg'],
            'depot_lateness': max(0.0, audit['return_time']-instance['return_deadline']),
            'stops': stops, 'return_step': audit['steps'][-1],
            'encoded_cumul_ranges': source.get('encoded_cumul_ranges')})
    return state, vehicles, {'route_feasible': route_feasible, 'full_service_feasible': recorded['valid'],
        'total_distance': recorded['distance'], 'missing': missing, 'served_unique': recorded['served_unique'],
        'duplicates': sorted(n for n, count in Counter(seen).items() if count > 1),
        'violations': errors, 'schedules': vehicles}


def normalize_public(blobs, input_blobs, format):
    require(format in FORMATS, 'unsupported_route_format', '需要明确指定支持的归档格式。')
    portfolio = format == PORTFOLIO_FORMAT
    data = {n: json.loads(b) for n, b in blobs.items() if n.endswith('.json')}
    protocol, freeze, manifest, requests, evaluated = (data[n] for n in
        ('protocol/protocol.json', 'protocol/freeze.json', 'protocol/input_manifest.json',
         'protocol/requests.json', 'reports/evaluated_results.json'))
    study = 'SOLVER_PORTFOLIO_HEADROOM_ARCHIVED100_V1' if portfolio else 'ARCHIVED_SOLOMON100_DISTANCE_ONLY_FIXED_V1'
    require(protocol['study_id'] == study, 'unsupported_route_format', 'study_id 与指定适配格式不同。')
    require(sha(blobs['source/checker.py']) == CHECKER_SHA256, 'unsupported_checker', '需要原冻结checker版本。')
    require(sha(blobs['protocol/protocol.json']) == PROTOCOL_HASHES[format],
        'unsupported_route_semantics', '仅支持这两份已审阅固定协议；新协议必须显式适配。')
    required_frozen = ['source/checker.py', 'protocol/protocol.json', 'protocol/input_manifest.json',
        'protocol/requests.json', 'evidence/environment.json']
    parameter_names = [f'protocol/parameters_{c}.textproto' for c in CONFIGS] if portfolio else [
        'protocol/parameters_250ms.textproto', 'protocol/parameters_1000ms.textproto']
    for name in required_frozen + parameter_names:
        require(freeze['sha256'].get(name) == sha(blobs[name]), 'frozen_hash_mismatch', '冻结文件哈希不一致：'+name)
    for name in parameter_names:
        key = Path(name).stem.removeprefix('parameters_')
        require(sha(blobs[name]) == PARAMETER_HASHES[key], 'unsupported_parameters', '仅支持已审阅的固定算法/预算参数。')
    require(freeze['solver_calls_before_freeze'] == 0, 'invalid_freeze', '冻结时已发生求解。')
    require((protocol['encoding'] if portfolio else protocol['integer_encoding'])['scale'] == 1000000,
            'unsupported_route_semantics', '需要本格式1e6整数缩放。')
    originals, instances = {}, {}
    for m in manifest:
        name = m['name']
        require(name not in {i['id']+'.txt' for i in instances.values()}, 'duplicate_input', '重复输入。')
        blob = input_blobs[name]
        require(sha(blob) == m['sha256'] and len(blob) == m['bytes'], 'input_hash_mismatch', '原输入字节哈希不同：'+name)
        original, instance = parse_input(blob, name, m)
        originals[instance['id']] = original
        instances[instance['id']] = instance
    lines, rows = jsonl(blobs['raw/results.jsonl'])
    require(len(rows) == len(requests) == len(evaluated), 'source_mismatch', '原始、请求和评估数量不同。')
    require(len(requests) == len(instances)*(4 if portfolio else 2), 'source_mismatch', '缺少完整实例×配置请求。')
    checks = {}
    if portfolio:
        _, check_rows = jsonl(blobs['raw/continuous_checks.jsonl'])
        for row in check_rows:
            run_id = row['run_id']
            require(run_id not in checks, 'duplicate_run', '重复checker运行ID。')
            checks[run_id] = {k:v for k,v in row.items() if k != 'run_id'}
        groups = data['protocol/shared_geometry.json']['geometry_sha256']
        expected = {key: sorted(i['id'] for i in instances.values() if i['geometry'] == key)
                    for key in {i['geometry'] for i in instances.values()}}
        require({g['sha256']: sorted(g['instances']) for g in groups} == expected,
                'source_mismatch', '归档几何分组与原输入不同。')
    runs, candidates = {}, 0
    for position, (request, raw, result, line) in enumerate(zip(requests, rows, evaluated, lines)):
        require(request['sequence'] == position and all(raw.get(k) == v for k,v in request.items()),
                'source_mismatch', '请求顺序或原始请求字段不同。')
        require(all(result.get(k) == v for k,v in raw.items() if k != 'outcome'),
                'source_mismatch', '评估记录与原始记录不同。')
        for timing in (raw, raw.get('first_solution') or {}):
            for key, value in timing.items():
                if key.endswith('_s'):
                    require(type(value) in (int, float) and math.isfinite(value) and value >= 0,
                            'invalid_timing', '实际计时必须是非负有限秒数：'+key)
        run_id = identifier(raw['run_id'])
        instance = instances[raw['instance']]
        require(run_id not in runs and raw['family'] == instance['family'], 'invalid_run_identity', '运行ID重复或命名族不同。')
        ms = raw['budget_ms']
        if portfolio:
            config = raw['config_id']
            require(config in CONFIGS and (ms, raw['strategy']) == CONFIGS[config], 'invalid_budget', '配置与预算不同。')
            expected_id = instance['id']+'__'+config
            parameter = f'protocol/parameters_{config}.textproto'
            strategy = raw['strategy']
        else:
            require(type(ms) is int and ms in (250,1000), 'invalid_budget', '需要250/1000ms预算。')
            expected_id = instance['id']+f'__{ms}ms'
            config, strategy = 'pci', 'PARALLEL_CHEAPEST_INSERTION'
            parameter = f'protocol/parameters_{ms}ms.textproto'
        require(run_id == expected_id, 'invalid_run_identity', 'run_id与实例/配置不一致。')
        source_routes = raw['routes']
        saved = checks.get(run_id) if portfolio else result.get('continuous_check')
        outcome = result['outcome']
        state, audit, vehicles = 'no_solution', None, []
        if source_routes is None:
            require(raw['assignment_returned'] is False and saved is None and raw.get('objective_integer') is None,
                    'invalid_run_status', '未返回候选却带方案/审计/目标。')
            require(outcome in {'TIMEOUT','UNKNOWN','FAIL','FAIL_EXCEPTION'}, 'invalid_run_status', '无方案状态不支持。')
            require(raw['outcome'] == outcome, 'source_mismatch', '无方案状态被改写。')
            require((outcome == 'TIMEOUT') == (raw.get('ortools_status') == 4), 'invalid_run_status', '超时标签与solver状态不同。')
            if outcome in {'FAIL', 'FAIL_EXCEPTION'}:
                state = 'unknown'
        else:
            require(raw['assignment_returned'] is True and isinstance(source_routes,list), 'invalid_run_status', '候选返回标记不一致。')
            ids = [r['vehicle'] for r in source_routes]
            require(len(ids) == len(set(ids)) and all(type(v) is int and 0 <= v < instance['vehicles'] for v in ids),
                    'invalid_vehicle', '原vehicle ID重复或越界。')
            recorded = check(originals[instance['id']], source_routes)
            require(raw.get('vehicles_used') == recorded['vehicles_used'], 'source_mismatch', '用车数与原方案不同。')
            # Keep the original continuous audit fields exact. Portfolio also stores objective evidence.
            require(saved is not None, 'source_mismatch', '有方案但无原checker记录。')
            verify_recorded(recorded, {k:saved[k] for k in recorded})
            require(set(saved) == set(recorded) | ({'independent_objective_integer','reported_objective_integer',
                'rounding_error','rounding_bound','arc_count'} if portfolio and recorded['valid'] else set()),
                'source_mismatch', 'checker字段集合不符合格式。')
            if recorded['valid']:
                obj, arcs = objective_check(originals[instance['id']], source_routes)
                require(obj == raw['objective_integer'], 'objective_mismatch', '独立整数目标与原目标不同。')
                if portfolio:
                    verify_recorded({'independent_objective_integer':obj, 'reported_objective_integer':raw['objective_integer'],
                        'rounding_error':abs(obj/1e6-recorded['distance']), 'rounding_bound':0.5*arcs/1e6+1e-9,
                        'arc_count':arcs}, {k:saved[k] for k in ('independent_objective_integer','reported_objective_integer',
                        'rounding_error','rounding_bound','arc_count')})
                else:
                    verify_recorded(recorded['distance'], result['original_distance'])
                    verify_recorded(obj/1e6-recorded['distance'], result['encoding_cost_error'])
                    verify_recorded(0.5*arcs/1e6, result['encoding_cost_error_bound'])
            if portfolio:
                verify_recorded({k:v for k,v in saved.items() if k!='route_audits'},raw['check_summary'])
                require(raw['outcome'] == outcome, 'source_mismatch', '组合档案状态被改写。')
            else:
                require(raw['outcome'] == 'ASSIGNMENT_UNCHECKED', 'invalid_run_status', '基线原始候选状态不同。')
            require(outcome == ('SUCCESS' if saved['valid'] else ('FAIL_CHECKER' if portfolio else 'FAIL')),
                    'invalid_run_status', '全服务成功标签与原checker不同。')
            state, vehicles, audit = normalize_witness(instance, source_routes, recorded)
            candidates += 1
        input_ref = instance['input_provenance']
        metrics = {k:v for k,v in raw.items() if k.endswith('_s') or k in ('objective_integer','vehicles_used','first_solution')}
        metrics.update(original_distance=audit['total_distance'] if audit else None,
            full_service_distance=audit['total_distance'] if state=='feasible' else None,
            bks_gap_percent=None)
        runs[run_id] = {'run_id':run_id,'instance_id':instance['id'],'method':'ortools_routing',
            'algorithm':{'id':'ortools_routing','version':data['evidence/environment.json']['ortools_version' if portfolio else 'ortools'],
                'config_id':config,'strategy':strategy,'parameters_sha256':sha(blobs[parameter])},
            'budget':{'value':ms,'unit':'milliseconds','scope':'per_call_search_wall_clock'},
            'geometry':instance['geometry'],'level':None,'stratum':instance['family'],
            'source_status':outcome,'execution_status':'failed' if outcome in {'FAIL_EXCEPTION'} or
                (outcome=='FAIL' and source_routes is None) else 'completed',
            'solution_status':state,'full_service_success':state=='feasible','solver_error':raw.get('error'),
            'solver_status':{'code':raw.get('ortools_status'),'name':raw.get('ortools_status_name'),
                'assignment_returned':raw['assignment_returned'],'outcome':raw['outcome']},
            'problem_feasibility':{'status':'feasible' if state=='feasible' else 'unknown',
                'source':{'artifact_id':aid('raw/results.jsonl'),'locator':f'line {position+1}'},
                'interpretation':'returned full witness only; no solver timeout is a proof of infeasibility'},
            'routes':[r['nodes'][1:-1] for r in source_routes] if source_routes is not None else None,
            'source_routes':source_routes,'vehicles':vehicles,
            'unserved_task_ids':audit['missing'] if audit else None,
            'unserved_semantics':'checker missing nodes' if audit else 'no returned candidate; missing-node list is not applicable',
            'metrics':metrics,'metric_semantics':{'bks_gap_percent':'not applicable: vehicles-first official objective differs',
                'timing':'nominal search cap is budget; *_cpu_s and *_wall_s are separately measured actual seconds'},
            'encoded_cumul_semantics':'integer model feasible ranges; not observed continuous arrival/service times',
            'checker':{'status':'no_candidate' if audit is None else ('passed' if audit['route_feasible'] else 'violations'),
                'implementation_sha256':CHECKER_SHA256,'source':'vendored exact original continuous checker; never archive-code import',
                'recomputed_at_import':audit is not None, 'route_feasible':audit['route_feasible'] if audit else None,
                'full_service_feasible':state=='feasible','audit':audit,'recorded_audit':saved},
            'provenance':{'source_run_id':run_id,'run_id_source':'native run_id scoped by experiment and revision',
                'run_sha256':sha(line),'run_hash_source':'exact raw/results.jsonl line bytes excluding newline',
                'artifact_id':aid('raw/results.jsonl'),'locator':f'line {position+1}',
                'spec_id':PROBLEM_SPEC['schema'],'spec_sha256':PROBLEM_SHA256,'problem_spec_sha256':PROBLEM_SHA256,
                'problem_spec_source':'derived normalized contract; original research protocol separately retained',
                'research_protocol_id':study,'research_protocol_sha256':sha(blobs['protocol/protocol.json']),
                'input_artifact_id':input_ref['artifact_id'],'input_locator':input_ref['locator'],
                'input_file_sha256':input_ref['input_file_sha256'],'instance_sha256':input_ref['instance_sha256'],
                'instance_hash_source':input_ref['instance_hash_source'],'encoded_input_sha256':input_ref['encoded_input_sha256'],
                'official_byte_identity':'unverified'}}
    require(set(checks) == {r['run_id'] for r in runs.values() if r['routes'] is not None} if portfolio else True,
            'source_mismatch', '存在无对应返回方案的checker记录。')
    verification = data['evidence/verification.json']
    require(verification['request_count'] == verification['raw_count'] == len(runs), 'source_mismatch', '验证报告数量不同。')
    require(verification['checker_success_count' if portfolio else 'checker_passed_count'] ==
            sum(r['full_service_success'] for r in runs.values()), 'source_mismatch', '验证报告成功数量不同。')
    input_identity = [{'name':m['name'],'sha256':m['sha256']} for m in sorted(manifest,key=lambda m:m['name'])]
    return {'schema_version':1,'source_format':format,'semantics':ROUTE_SEMANTICS,'instances':instances,'runs':runs,
        'summary':{'instance_count':len(instances),'run_count':len(runs),
            'geometry_group_count':len({i['geometry'] for i in instances.values()}),
            'solution_status_counts':dict(Counter(r['solution_status'] for r in runs.values()))},
        'verification':{'recorded_report':verification,'source_artifact_id':aid('evidence/verification.json'),
            'backend_replayed_candidates':candidates,'scope':'original-checker witness replay and integer objective check; no solver execution'},
        'sources':{n:sha(b) for n,b in blobs.items()},'input_identity_sha256':sha(canonical(input_identity).encode()),
        'input_identity_hash_source':'derived sorted [{name,sha256}] of exact authorized inputs; excludes source-location metadata',
        'problem_spec_sha256':PROBLEM_SHA256,'research_protocol_sha256':sha(blobs['protocol/protocol.json'])}


def import_public(store, source, format, experiment_id=None, input_dir=None):
    require(format in FORMATS, 'unsupported_route_format', '未知的明确归档格式。')
    experiment_id = identifier(experiment_id or ('vrptw-portfolio-20261007' if format == PORTFOLIO_FORMAT else 'vrptw-archived100-20261007'))
    source = Path(source).resolve()
    input_dir = Path(input_dir).resolve() if input_dir else source/'inputs'
    try:
        freeze_blob = read_artifact(source, {'path':'protocol/freeze.json'})
        freeze = json.loads(freeze_blob)
        # Verify every frozen artifact; never execute a Python file from this archive.
        blobs = {'protocol/freeze.json':freeze_blob}
        for name, digest in freeze['sha256'].items():
            blob = read_artifact(source, {'path':name})
            require(sha(blob) == digest, 'frozen_hash_mismatch', '冻结文件哈希不同：'+name)
            blobs[name] = blob
        for name in ['raw/results.jsonl','reports/evaluated_results.json','evidence/verification.json'] + (
                ['raw/continuous_checks.jsonl'] if format == PORTFOLIO_FORMAT else []):
            blobs[name] = read_artifact(source, {'path':name})
        manifest = json.loads(blobs['protocol/input_manifest.json'])
        input_blobs = {m['name']:read_artifact(input_dir, {'path':m['name']}) for m in manifest}
        index = normalize_public(blobs, input_blobs, format)
    except (KeyError, TypeError, ValueError, IndexError, StopIteration) as exc:
        if isinstance(exc, StoreError):
            raise
        raise StoreError('invalid_route_source', '公开候选/组合归档字段无效。') from exc
    try:
        existing = store.get(experiment_id)
    except StoreError as exc:
        if exc.status != 404:
            raise
        existing = None
    if existing and (existing.get('routing',{}).get('source_format') != format or
                     existing['provenance']['input_sha256'] != index['input_identity_sha256']):
        raise StoreError('experiment_identity_mismatch', '实验ID已属于其他格式或输入集合。', 409)
    artifacts = [{'id':aid(n),'path':n,'media_type':'application/json' if n.endswith('.json') else 'text/plain; charset=utf-8',
                  'role':'source_evidence'} for n in sorted(blobs)]
    artifacts.append({'id':INDEX_ID,'path':'route-index.json','media_type':'application/json','role':'derived_read_index'})
    descriptor = {'schema_version':1,'id':experiment_id,'title':'VRPTW 用户存档百客户路线',
        'domain':'VRPTW','kind':'recorded_routes','status':'completed','started_at':None,'finished_at':None,'failure_reason':None,
        'counts':[{'unit':'instance','value':len(index['instances']),'scope':'shared_archived_input'},
                  {'unit':'run','value':len(index['runs']),'scope':'imported_route_record'}],
        'parameters':{'source_format':format,'route_semantics':ROUTE_SEMANTICS},'metrics':[],'artifacts':artifacts,
        'notes':['仅核验导入原记录，不运行solver。',f"{len(index['instances'])}命名实例仅{index['summary']['geometry_group_count']}坐标geometry groups；不当作独立几何。",
                 '官方字节同一性未证实；固定K上限距离单目标，不计算官方BKS gap。',
                 '原输入只在授权目录读取，原字节不复制进导入证据或源码包。'],
        'provenance':{'source_files':index['sources'],'input_sha256':index['input_identity_sha256'],
            'input_hash_source':index['input_identity_hash_source'],'spec_sha256':PROBLEM_SHA256,
            'research_protocol_sha256':index['research_protocol_sha256']},
        'routing':{'schema_version':1,'source_format':format,'index_artifact_id':INDEX_ID,
            'read_api':f'/api/experiments/{experiment_id}/runs','semantics':ROUTE_SEMANTICS,**index['summary']}}
    with tempfile.TemporaryDirectory(prefix='public-route-import-') as directory:
        root = Path(directory)
        for name, content in blobs.items():
            path = root/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        (root/'route-index.json').write_text(canonical(index)+'\n',encoding='utf-8')
        (root/'experiment.json').write_text(canonical(descriptor),encoding='utf-8')
        return store.import_package(root)
