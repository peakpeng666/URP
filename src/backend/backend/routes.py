"""Read-only VRPTW archive adapter. Imports evidence; never imports source Python."""
from __future__ import annotations
import json
import tempfile
from collections import Counter
from pathlib import Path
from .store import StoreError, canonical, identifier, no_secrets, read_artifact, sha

SOURCE_FILES = ('inputs.json', 'routes.jsonl', 'map_backend.json', 'protocol.json',
                'freeze.json', 'verification.json', 'self_check.json', 'checker.py')
INDEX_ID = 'route-index-json'
SOLUTION_STATES = {'feasible', 'partial', 'infeasible', 'invalid', 'unknown', 'no_solution'}
SEMANTICS = {
    'coordinate_system': 'synthetic_cartesian',
    'distance_model': 'euclidean',
    'distance_unit': 'arbitrary_distance_units',
    'time_unit': 'arbitrary_time_units',
    'speed': 1,
    'is_geographic': False,
    'is_road_network': False,
    'time_window': 'inclusive_service_start',
    'load': 'cumulative_served_demand; physical onboard load is unknown',
}


def artifact_id(name):
    return name.replace('.', '-')


def solution_status(row):
    """Execution completion is deliberately separate from solution feasibility."""
    if row['status'] == 'proven_infeasible':
        return 'infeasible'
    audit = row.get('audit')
    if audit is None:
        return 'unknown'
    if audit['full_service_feasible'] is True:
        return 'feasible'
    if audit['route_feasible'] is True:
        return 'partial'
    return 'invalid'


def normalize(blobs):
    parsed = {name: json.loads(blobs[name]) for name in SOURCE_FILES if name.endswith('.json')}
    inputs, map_data, freeze = parsed['inputs.json'], parsed['map_backend.json'], parsed['freeze.json']
    lines = blobs['routes.jsonl'].splitlines()
    rows = [json.loads(line) for line in lines if line.strip()]
    if len(rows) != len(lines):
        raise StoreError('invalid_routes', 'routes.jsonl 不接受空行。')
    if map_data.get('schema_version') != 1 or map_data['instances'] != inputs or map_data['solutions'] != rows:
        raise StoreError('source_mismatch', '地图、输入与路线记录不一致。')
    if (map_data.get('coordinate_system') != 'synthetic Cartesian, not longitude/latitude; not road travel'
            or map_data.get('time_window_semantics') != 'inclusive service-start'
            or map_data.get('units') != 'arbitrary distance/time, speed1'
            or map_data.get('objective') != 'total Euclidean route distance, full service required'
            or parsed['protocol.json'].get('input', {}).get('distance') != 'Euclidean in arbitrary distance units; speed=1; no rounding during optimization'
            or parsed['protocol.json'].get('input', {}).get('time_window_semantics') != 'Inclusive bounds on START OF SERVICE; wait allowed; travel/service nonnegative; all routes return to depot'):
        raise StoreError('unsupported_route_semantics', '此适配器仅支持已声明的合成 Euclidean / 开始服务时间窗合同。')
    # Check existing frozen identities; do not substitute newly derived hashes for them.
    for name in ('protocol.json', 'inputs.json', 'checker.py'):
        if freeze.get('sha256', {}).get(name) != sha(blobs[name]):
            raise StoreError('frozen_hash_mismatch', f'冻结哈希不一致：{name}')
    instances = {}
    for index, item in enumerate(inputs):
        instance_id = identifier(item['id'])
        if instance_id in instances or not isinstance(item['vehicles'], int) or item['vehicles'] < 1:
            raise StoreError('invalid_inputs', '实例 ID 重复或车辆数无效。')
        nodes = item['nodes']
        if len({n['id'] for n in nodes}) != len(nodes) or not any(n['id'] == 0 for n in nodes):
            raise StoreError('invalid_inputs', '任务点重复或缺少仓库。')
        instances[instance_id] = {**item, 'input_provenance': {
            'artifact_id': 'inputs-json', 'locator': f'/{index}',
            'input_file_sha256': freeze['sha256']['inputs.json'],
            'instance_sha256': sha(canonical(item).encode()),
            'instance_hash_source': 'derived: SHA256 of canonical UTF-8 JSON (sorted keys, compact separators, ensure_ascii=False)',
        }}
    runs = {}
    for line_number, (row, line) in enumerate(zip(rows, lines), 1):
        instance = instances.get(row['instance'])
        if instance is None:
            raise StoreError('invalid_routes', '路线引用了未知输入。')
        run_id = identifier(f"{row['instance']}.{row['method']}")
        if run_id in runs:
            raise StoreError('invalid_routes', '实例与方法组合重复。')
        audit, routes = row.get('audit'), row.get('routes')
        if row['status'] not in {'complete', 'optimal', 'optimal_max_coverage', 'replayed_capacity_only_optimum', 'proven_infeasible'}:
            raise StoreError('invalid_routes', '此版本未支持的源运行状态，不能推断为已完成。')
        if row['status'] == 'proven_infeasible':
            if row['method'] != 'oracle_full' or routes is not None or audit is not None or row['full_oracle_objective'] is not None:
                raise StoreError('invalid_routes', '无解记录必须保留空路线、空审计及 null 全服务目标。')
        elif routes is None or audit is None:
            raise StoreError('invalid_routes', '当前 VRPTW 格式的非无解记录缺少路线或独立审计。')
        vehicles = []
        if audit is not None:
            if not isinstance(audit['route_feasible'], bool) or not isinstance(audit['full_service_feasible'], bool):
                raise StoreError('invalid_routes', '独立 checker 可行性字段必须是布尔值。')
            schedules = audit['schedules']
            if len(routes) != instance['vehicles'] or len(schedules) != len(routes):
                raise StoreError('invalid_routes', '路线及时间表车辆数量不一致。')
            known_nodes = {n['id']: n for n in instance['nodes']}
            served = [n for route in routes for n in route]
            expected_missing = sorted(set(known_nodes) - {0} - set(served))
            expected_duplicates = sorted(n for n, count in Counter(served).items() if count > 1)
            if audit['duplicates'] != expected_duplicates or audit['unknown'] != sorted(set(served) - (set(known_nodes) - {0})):
                raise StoreError('invalid_routes', '独立审计的重复或未知任务点与路线不一致。')
            if sorted(audit['missing']) != expected_missing or audit['served_unique'] != len(set(served) - {0}):
                raise StoreError('invalid_routes', '独立审计的已服务和未服务点与路线不一致。')
            if audit['route_feasible'] and (audit['violations'] or audit['duplicates'] or audit['unknown']):
                raise StoreError('invalid_routes', '存在违规时不能声明路线合法。')
            if audit['full_service_feasible'] and (not audit['route_feasible'] or expected_missing or audit['duplicates'] or audit['unknown']):
                raise StoreError('invalid_routes', '部分服务或非法路线不能声明全服务成功。')
            for vehicle, (route, schedule) in enumerate(zip(routes, schedules)):
                if schedule['vehicle'] != vehicle or schedule['route'] != route or [s['node'] for s in schedule['stops']] != route:
                    raise StoreError('invalid_routes', '车辆路径与逐站时间表不一致。')
                if any(n not in known_nodes for n in route):
                    raise StoreError('invalid_routes', '路径点没有坐标。')
                load, stops = 0, []
                for order, stop in enumerate(schedule['stops'], 1):
                    if stop['demand'] != known_nodes[stop['node']]['demand']:
                        raise StoreError('invalid_routes', '时间表与原任务需求不一致。')
                    before = load
                    load += stop['demand']
                    stops.append({**stop, 'sequence': order, 'service_start': stop['start'],
                        'load_before': before, 'load_after': load, 'onboard_load': None})
                if load != schedule['load']:
                    raise StoreError('invalid_routes', '逐站累计需求与车辆载重约束值不一致。')
                vehicles.append({**schedule, 'vehicle_id': vehicle, 'stops': stops,
                    'path_node_ids': [0, *route, 0],
                    'path_coordinates': [[known_nodes[n]['x'], known_nodes[n]['y']] for n in [0, *route, 0]],
                    'path_semantics': 'straight Euclidean segments including depot return; not road geometry',
                    'load_semantics': SEMANTICS['load']})
        state = solution_status(row)
        runs[run_id] = {
            'run_id': run_id, 'instance_id': row['instance'], 'method': row['method'],
            'geometry': row['geometry'], 'level': row['level'], 'stratum': row['stratum'],
            'source_status': row['status'], 'execution_status': 'completed',
            'solution_status': state, 'full_service_success': state == 'feasible',
            'solver_error': None,
            'routes': routes, 'vehicles': vehicles,
            'unserved_task_ids': audit['missing'] if audit is not None else None,
            'unserved_semantics': 'checker missing nodes' if audit is not None else 'no candidate route exists; missing-node list is not applicable',
            'metrics': {k: row[k] for k in ('cpu_seconds', 'full_oracle_objective', 'full_gap_percent',
                'same_served_mask_optimum', 'same_served_mask_gap_percent', 'coverage_shortfall')},
            'checker': {'status': 'no_candidate' if audit is None else ('passed' if audit['route_feasible'] else 'violations'),
                'source': 'recorded independent checker; not rerun by this data API',
                'implementation_sha256': freeze['sha256']['checker.py'],
                'route_feasible': audit['route_feasible'] if audit is not None else None,
                'full_service_feasible': audit['full_service_feasible'] if audit is not None else False,
                'audit': audit},
            'provenance': {'source_run_id': None,
                'run_id_source': 'derived: instance + dot + method; source archive has no run ID',
                'run_sha256': sha(line), 'run_hash_source': 'derived: exact routes.jsonl line bytes excluding newline',
                'artifact_id': 'routes-jsonl', 'locator': f'line {line_number}',
                'spec_id': parsed['protocol.json'].get('study_id'),
                'spec_sha256': freeze['sha256']['protocol.json'],
                'input_artifact_id': 'inputs-json',
                'input_locator': instance['input_provenance']['locator'],
                'input_file_sha256': instance['input_provenance']['input_file_sha256'],
                'instance_sha256': instance['input_provenance']['instance_sha256'],
                'instance_hash_source': instance['input_provenance']['instance_hash_source']},
        }
    verification = parsed['verification.json']
    if verification.get('record_count') != len(rows):
        raise StoreError('source_mismatch', '验证报告的记录数与路线数不一致。')
    return {'schema_version': 1, 'semantics': SEMANTICS,
        'instances': instances, 'runs': runs,
        'summary': {'instance_count': len(instances), 'run_count': len(runs),
                    'solution_status_counts': dict(Counter(r['solution_status'] for r in runs.values()))},
        'verification': {'recorded_report': verification, 'source_artifact_id': 'verification-json',
                         'scope': 'imported archive verification evidence; no solver or source checker executed at import'},
        'sources': {name: sha(data) for name, data in blobs.items()}}


def import_vrptw(store, source, experiment_id='vrptw-20261007'):
    """Build a temporary standard package, then use the existing atomic version store."""
    identifier(experiment_id)
    source = Path(source).resolve()
    blobs = {name: read_artifact(source, {'path': name}) for name in SOURCE_FILES}
    try:
        for line in blobs['routes.jsonl'].splitlines():
            no_secrets(json.loads(line))
        index = normalize(blobs)
    except (KeyError, TypeError, ValueError) as exc:
        if isinstance(exc, StoreError):
            raise
        raise StoreError('invalid_route_source', 'VRPTW 原始文件字段无效。') from exc
    try: existing = store.get(experiment_id)
    except StoreError as exc:
        if exc.status != 404: raise
        existing = None
    if existing and (existing.get('routing', {}).get('source_format', 'vrptw-frozen-v1') != 'vrptw-frozen-v1'
                     or existing['provenance']['input_sha256'] != index['sources']['inputs.json']):
        raise StoreError('experiment_identity_mismatch', '此实验 ID 已属于其他格式或输入集合；请使用独立 ID。', 409)
    index_bytes = (canonical(index) + '\n').encode()
    artifacts = [{'id': artifact_id(name), 'path': name,
        'media_type': 'application/json' if name.endswith('.json') else 'text/plain; charset=utf-8',
        'role': 'source_evidence'} for name in SOURCE_FILES]
    artifacts.append({'id': INDEX_ID, 'path': 'route-index.json', 'media_type': 'application/json', 'role': 'derived_read_index'})
    descriptor = {'schema_version': 1, 'id': experiment_id, 'title': 'VRPTW 合成时间窗路线实验',
        'domain': 'VRPTW', 'kind': 'recorded_routes', 'status': 'completed',
        'started_at': None, 'finished_at': None, 'failure_reason': None,
        'counts': [{'unit': 'instance', 'value': len(index['instances']), 'scope': 'imported_input'},
                   {'unit': 'run', 'value': len(index['runs']), 'scope': 'imported_route_record'}],
        'parameters': {'route_semantics': SEMANTICS}, 'metrics': [], 'artifacts': artifacts,
        'notes': ['实验记录完成不等于全服务成功。partial、infeasible 和 invalid 独立保留。',
                  '只读取既有档案，不运行求解器、候选代码或源 checker。',
                  '合成坐标与 Euclidean 距离，不代表真实道路或经纬度。'],
        'provenance': {'source_label': 'VRPTW frozen archive', 'source_files': index['sources'],
                       'spec_sha256': index['sources']['protocol.json'], 'input_sha256': index['sources']['inputs.json']},
        'routing': {'schema_version': 1, 'index_artifact_id': INDEX_ID,
                    'read_api': f'/api/experiments/{experiment_id}/runs', 'semantics': SEMANTICS,
                    **index['summary']}}
    with tempfile.TemporaryDirectory(prefix='vrptw-import-') as directory:
        root = Path(directory)
        for name, data in blobs.items():
            (root / name).write_bytes(data)
        (root / 'route-index.json').write_bytes(index_bytes)
        (root / 'experiment.json').write_text(canonical(descriptor), encoding='utf-8')
        return store.import_package(root)


class RouteReader:
    def __init__(self, store, experiment_id, revision=None):
        self.record = store.get(experiment_id, revision)
        routing = self.record.get('routing')
        if not routing:
            raise StoreError('routes_not_available', '此实验没有结构化路线数据。', 404)
        _, data = store.artifact(experiment_id, routing['index_artifact_id'], self.record['revision'])
        self.index = json.loads(data)
        self.context = {'schema_version': 1, 'experiment_id': experiment_id,
            'revision': self.record['revision'], 'experiment_fingerprint': self.record['fingerprint'],
            'semantics': self.index['semantics']}

    def instances(self):
        return {**self.context, 'instances': list(self.index['instances'].values())}

    def runs(self, instance=None, status=None):
        if instance is not None and identifier(instance) not in self.index['instances']:
            raise StoreError('not_found', '实例不存在。', 404)
        if status is not None and status not in SOLUTION_STATES:
            raise StoreError('invalid_status', '路线状态无效。')
        keys = ('run_id', 'instance_id', 'method', 'source_status', 'execution_status',
                'solution_status', 'full_service_success', 'unserved_task_ids', 'provenance')
        keys += ('algorithm', 'budget', 'solver_status', 'problem_feasibility')
        items = [{k: r[k] for k in keys if k in r} for r in self.index['runs'].values()
                 if (instance is None or r['instance_id'] == instance) and (status is None or r['solution_status'] == status)]
        return {**self.context, 'runs': items, 'count': len(items),
                'summary': self.index['summary'], 'verification': self.index['verification']}

    def get_run(self, run_id):
        run_id = identifier(run_id)
        run = self.index['runs'].get(run_id)
        if run is None:
            raise StoreError('not_found', '运行记录不存在。', 404)
        return run

    def run(self, run_id):
        run = self.get_run(run_id)
        return {**self.context, **run, 'input': self.index['instances'][run['instance_id']]}

    def vehicle(self, run_id, vehicle_id):
        run = self.get_run(run_id)
        if not isinstance(vehicle_id, int) or vehicle_id < 0:
            raise StoreError('invalid_vehicle', '车辆编号必须是非负整数。')
        instance = self.index['instances'][run['instance_id']]
        if vehicle_id >= instance['vehicles']:
            raise StoreError('not_found', '车辆不存在。', 404)
        vehicle = next((v for v in run['vehicles'] if v['vehicle_id'] == vehicle_id), None)
        return {**self.context, 'run_id': run_id, 'instance_id': run['instance_id'],
            'vehicle_id': vehicle_id, 'solution_status': run['solution_status'],
            'full_service_success': run['full_service_success'], 'vehicle': vehicle,
            'unserved_task_ids': run['unserved_task_ids'], 'unserved_semantics': run['unserved_semantics'],
            'checker': run['checker'], 'provenance': run['provenance'],
            'input': instance,
            **{k:run[k] for k in ('algorithm','budget','solver_status','problem_feasibility','execution_status','source_status') if k in run}}
