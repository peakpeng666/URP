"""Read-only route-scene v1: visit-order geometry, never a robot trajectory.

The immutable RouteReader snapshot is the only input. No solver, recommender,
physical-map inference, network call, or robot control is performed here.
"""
from copy import deepcopy
import math
from urllib.parse import quote

from .routes import RouteReader
from .store import StoreError, canonical

SECOND_METRICS = {'cpu_seconds', 'solve_wall_s', 'solve_cpu_s', 'model_wall_s',
                  'model_cpu_s', 'total_wall_s', 'total_cpu_s'}
RECORDED_METRICS = SECOND_METRICS | {
    'full_oracle_objective', 'full_gap_percent', 'same_served_mask_optimum',
    'same_served_mask_gap_percent', 'coverage_shortfall', 'full_gap_original_percent',
    'objective_integer', 'vehicles_used', 'original_distance', 'full_service_distance',
    'bks_gap_percent',
}


def _number(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _point(node):
    if (type(node.get('id')) is not int or not _number(node.get('x'))
            or not _number(node.get('y'))):
        raise StoreError('invalid_route_scene', '路线场景需要整数节点ID和有限XY坐标。', 409)
    return {'node_id': node['id'], 'x': node['x'], 'y': node['y'],
            'demand': node.get('demand'), 'service_duration': node.get('service'),
            'time_window': deepcopy(node.get('window'))}


def route_scene(store, experiment_id, run_id, revision=None):
    """Export one selected recorded run. Absent evidence stays absent/null.

    Even a valid solution is not simulation-ready: current source adapters have
    no physical map, metric transform, robot footprint or collision evidence.
    A query parameter cannot grant physical meaning to benchmark coordinates.
    """
    reader = RouteReader(store, experiment_id, revision)
    return scene_from_reader(reader, run_id)


def scene_from_reader(reader, run_id):
    run = reader.get_run(run_id)
    instance = reader.index['instances'][run['instance_id']]
    semantics = deepcopy(reader.index['semantics'])
    points = [_point(node) for node in instance['nodes']]
    by_id = {point['node_id']: point for point in points}
    if len(by_id) != len(points) or 0 not in by_id:
        raise StoreError('invalid_route_scene', '路线场景节点重复或缺少仓库0。', 409)
    vehicles = []
    for vehicle in run['vehicles']:
        ids = vehicle['path_node_ids']
        coordinates = vehicle['path_coordinates']
        if (not isinstance(ids, list) or len(ids) < 2 or ids[0] != 0 or ids[-1] != 0
                or any(type(node_id) is not int or node_id not in by_id for node_id in ids)
                or coordinates != [[by_id[n]['x'], by_id[n]['y']] for n in ids]):
            raise StoreError('invalid_route_scene', '路线节点与源XY坐标不一致。', 409)
        vehicles.append({'vehicle_id': vehicle['vehicle_id'],
                         'visit_node_ids': deepcopy(ids),
                         'polyline': deepcopy(coordinates),
                         'metrics': {'distance': vehicle.get('distance'),
                                     'return_time': vehicle.get('return_time'),
                                     'cumulative_served_demand': vehicle.get('load')},
                         'stops': deepcopy(vehicle.get('stops', []))})
    record = reader.record
    revision = record['revision']
    base = '/api/experiments/' + quote(record['id'], safe='')
    index_id = record['routing']['index_artifact_id']
    artifact = next(a for a in record['artifacts'] if a['id'] == index_id)
    audit = run['checker'].get('audit')
    distance = audit.get('total_distance') if audit is not None else None
    recorded = {key: deepcopy(value) for key, value in run.get('metrics', {}).items()
                if key in RECORDED_METRICS}
    if any(value is not None and not _number(value) for value in recorded.values()):
        raise StoreError('invalid_route_scene', '记录指标必须是有限数值或null，不能把布尔值或文本当作数值。', 409)
    scene = {
        'schema_version': 1,
        'scene_type': 'route_scene',
        'experiment_id': record['id'],
        'revision': revision,
        'experiment_fingerprint': record['fingerprint'],
        'run_id': run['run_id'],
        'instance_id': run['instance_id'],
        'geometry_kind': 'visit_order_polyline',
        'simulation_ready': False,
        'frame': {
            'id': 'benchmark_xy',
            'coordinate_system': semantics.get('coordinate_system'),
            'axis_order': ['x', 'y'],
            'is_geographic': semantics.get('is_geographic'),
            'is_road_network': semantics.get('is_road_network'),
            'physical_frame_id': None,
            'meters_per_coordinate_unit': None,
        },
        'units': {
            'coordinate': semantics.get('distance_unit'),
            'distance': semantics.get('distance_unit'),
            'schedule_time': semantics.get('time_unit'),
            'compute_time': ('seconds' if any(recorded.get(key) is not None
                                            for key in SECOND_METRICS) else None),
            'demand': None,
        },
        'semantics': semantics,
        'depot': by_id[0],
        'task_nodes': [point for point in points if point['node_id'] != 0],
        'vehicles': vehicles,
        'metrics': {
            'total_distance': distance,
            'full_service_distance': distance if run['full_service_success'] else None,
            'served_task_count': audit.get('served_unique') if audit is not None else None,
            'task_count': len(points) - 1,
            'recorded': recorded,
        },
        'status': {key: run[key] for key in (
            'execution_status', 'source_status', 'solution_status', 'full_service_success')},
        'unserved_task_ids': deepcopy(run['unserved_task_ids']),
        'recommendation': {
            'status': 'not_available',
            'selected_run_id': None,
            'evidence': None,
            'reason': 'No linked recommendation evidence is exported by route-scene v1; '
                      'displaying a selected run or descriptive shortest result is not a learned recommendation.',
        },
        'provenance': {
            'run': deepcopy(run['provenance']),
            'input': deepcopy(instance['input_provenance']),
            'index_artifact': {
                'id': index_id, 'sha256': artifact['sha256'],
                'url': base + '/artifacts/' + quote(index_id, safe='') + f'?revision={revision}',
            },
            'source_run_url': base + '/runs/' + quote(run['run_id'], safe='') + f'?revision={revision}',
        },
        'limitations': [
            'Visit-order straight segments only; not obstacle-aware, drivable or road-network geometry.',
            'Benchmark XY and schedule units are not meters, seconds of physical motion, or a ROS map frame.',
            'No physical map, metric transform, robot footprint, kinematic or collision validation is supplied.',
            'Only available normalized vehicle geometry is exported; malformed source routes may be absent.',
            'For invalid candidates, unserved IDs are normalized source data, not validated coverage; omission does not prove service.',
            'Stops are checker schedules, not observed robot telemetry; onboard load remains unknown.',
            'Missing metrics remain null; recorded metrics retain their original scopes and names.',
            'Feasibility and recorded oracle values do not add an optimality proof or recommendation evidence.',
        ],
    }
    scene['status']['has_candidate'] = run['routes'] is not None
    try:
        canonical(scene)
    except (TypeError, ValueError) as exc:
        raise StoreError('invalid_route_scene', '场景含非JSON或非有限数值，停止导出。', 409) from exc
    return scene
