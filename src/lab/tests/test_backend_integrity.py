"""Backend regressions: dishonest witnesses, repeated visits, dwell timing and field admission."""
import copy
import json
import math
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from urp_lab import fieldworld
from urp_lab.field_tracking import Driver
from urp_lab.gateway import Config, create_app
from urp_lab.scenarios import validate_instance
from urp_lab.solvers import fleet


def instance():
    return validate_instance('fleet_routing', {
        'boundary': [[0, 0], [30, 0], [30, 25], [0, 25]], 'depot': [5, 5],
        'tasks': [{'id': 1, 'xy': [10, 5]}, {'id': 2, 'xy': [15, 5]}],
        'vehicles': {'count': 1, 'capacity': 2, 'travel': 'free', 'speed_mps': 1}})


def solution():
    inst = instance()
    routes, check, metrics, raw, status, trace = fleet.solve({}, inst, 'panel.sweep', {})
    assert check['valid']
    return {'run_id': 'test_field', 'scenario_id': 'test', 'problem_class': 'fleet_routing', 'state': 'done',
            'status': status, 'instance': inst, 'routes': routes, 'check': check, 'metrics': metrics}


@pytest.mark.parametrize('mutation', ['no_geometry', 'no_services', 'distance', 'duration', 'trip_members', 'unknown_task', 'service_order'])
def test_checker_rejects_inconsistent_witness(mutation):
    run = solution()
    r = run['routes'][0]
    if mutation == 'no_geometry':
        r['polyline'] = []
    elif mutation == 'no_services':
        r['services'] = []
    elif mutation == 'distance':
        r['cost'] = 0
    elif mutation == 'duration':
        r['duration_s'] = 0
    elif mutation == 'trip_members':
        r['trips'] = [[r['sequence'][0]]]
    elif mutation == 'unknown_task':
        r['sequence'].append(999)
        r['trips'][0].append(999)
    else:
        r['services'].reverse()
    assert not fleet.check(run['instance'], run['routes'])['valid']


def test_reload_requires_real_depot_return():
    run = solution()
    inst, r = run['instance'], run['routes'][0]
    inst['vehicles']['capacity'] = 1
    r.update(trips=[[1], [2]], sequence=[1, 2], load=1)
    # Merely declaring two trips on a path visiting both tasks before returning is not unloading.
    r['polyline'] = [inst['depot'], [10, 5], [15, 5], inst['depot']]
    r['services'] = [{'task': 1, 'stop': [10, 5]}, {'task': 2, 'stop': [15, 5]}]
    assert not fleet.check(inst, [r])['valid']


def test_invalid_heuristic_candidate_is_not_reported_feasible():
    inst = instance()
    inst['tasks'].append(dict(inst['tasks'][0], id=3))
    for t in inst['tasks']:
        t['demand'] = 6
    inst['vehicles'].update(capacity=10, count=2, trips='single')
    routes, check, metrics, raw, status, _ = fleet.solve({}, inst, 'panel.savings_fleet', {})
    assert not routes and status == 'no_solution' and not check['valid']
    assert len(raw['rejected_routes']) == 3


@pytest.mark.parametrize('kind', ['row_angle', 'vehicle_object', 'travel_mode', 'nonfinite_id'])
def test_malformed_fleet_settings_are_validation_errors(kind):
    inst = instance()
    if kind == 'row_angle':
        inst['plots'] = [{'polygon': inst['boundary'], 'rows_deg': 'nan'}]
    elif kind == 'vehicle_object':
        inst['vehicles'] = [1]
    elif kind == 'travel_mode':
        inst['vehicles']['travel'] = 'fly'
    else:
        inst['tasks'][0]['id'] = float('inf')
    with pytest.raises(ValueError):
        validate_instance('fleet_routing', inst)


@pytest.mark.parametrize('travel', ['free', 'rows'])
def test_colocated_tasks_and_depot_have_zero_distance(travel):
    inst = instance()
    inst['vehicles']['travel'] = travel
    for t in inst['tasks']:
        t['xy'] = inst['depot'][:]
    g = fleet.travel_graph(inst)
    assert (g.D == 0).all()
    routes, check, *_ = fleet.solve({}, inst, 'panel.sweep', {})
    assert check['valid'] and routes[0]['cost'] == 0


def test_footprint_detects_between_points_and_rounded_obstacle_corner():
    run = solution()
    inst, r = run['instance'], run['routes'][0]
    # The old 4-segment circular inflation underestimates a corner by about 1 cm.
    inst['obstacles'] = [{'polygon': [[12, 6], [14, 6], [14, 8], [12, 8]]}]
    p = [12 - 0.495 * math.cos(math.pi / 16), 6 - 0.495 * math.sin(math.pi / 16)]
    r['polyline'] = [[5, 5], p, [5, 5]]
    assert not fleet.check(inst, [r])['valid']


def driver(tasks, path=None):
    d = Driver({'name': 'v', 'label': '车', 'color': '#007aff',
                'path': path or [[0, 0], [1, 0], [0, 0]], 'tasks': tasks}, 1.0)
    d.state = 'driving'
    d.pose = (0, 0, 0)
    return d


def task(tid, seconds=0, **kw):
    return {'id': tid, 'label': str(tid), 'xy': [0, 0], 'service_s': seconds, **kw}


def test_colocated_services_get_full_sequential_dwell_times():
    d = driver([task(1, 10), task(2, 20)])
    assert d.step(0) == (0, 0) and d.state == 'servicing'
    assert d.step(9) == (0, 0) and d.tasks[1]['state'] == 'pending'
    assert d.step(10) == (0, 0) and d.tasks[0]['serviced_at'] == 10
    assert d.step(29) == (0, 0) and d.tasks[1]['serviced_at'] is None
    d.step(30)
    assert d.tasks[1]['serviced_at'] == 30


def test_long_service_does_not_trigger_stuck_watchdog():
    d = driver([task(1, 120)])
    d.last_progress = (0, 0)
    d.step(0)
    d.step(120)
    assert d.state == 'driving' and d.failure is None


def test_later_visit_to_same_position_is_not_served_at_start():
    d = driver([task(1, path_s=2)])
    d.step(0)
    assert d.tasks[0]['state'] == 'pending' and d.s == 0


def test_unreachable_service_is_not_projected_to_nearest_vertex():
    with pytest.raises(ValueError):
        driver([task(1, xy=[0, 20])])


@pytest.mark.parametrize('value', [0, -1, 21, True, None, 'fast', 'NaN'])
def test_fieldsim_rejects_invalid_speed_as_client_error(tmp_path, value):
    app = create_app(Config(runtime=tmp_path, background=False, archive_autostart=False, extra_hosts={'testserver'}))
    app.state.lab.store.put_run(solution())
    with TestClient(app) as c:
        res = c.post('/lab/api/fieldsim', json={'run_id': 'test_field', 'real_time_factor': value})
        assert res.status_code == 400 and res.json()['error'] == 'invalid_rtf'


@pytest.mark.parametrize('mutation', ['check_missing', 'check_failed', 'tampered_geometry', 'tampered_cost'])
def test_fieldsim_admission_rechecks_before_any_process_starts(tmp_path, mutation):
    app = create_app(Config(runtime=tmp_path, background=False, archive_autostart=False, extra_hosts={'testserver'}))
    run = solution()
    if mutation == 'check_missing':
        run['check'] = None
    elif mutation == 'check_failed':
        run['check']['valid'] = False
    elif mutation == 'tampered_geometry':
        run['routes'][0].update(polyline=[], services=[])
    else:
        run['routes'][0]['cost'] = 0
    app.state.lab.store.put_run(run)
    with TestClient(app) as c:
        res = c.post('/lab/api/fieldsim', json={'run_id': 'test_field'})
        assert res.status_code == 422
        assert app.state.lab.fieldsim.proc is None
        assert not (tmp_path / 'fieldsim').exists()


def test_dead_session_returns_persisted_failure_even_after_requested_stop(tmp_path):
    app = create_app(Config(runtime=tmp_path, background=False, archive_autostart=False))
    m = app.state.lab.fieldsim
    m.meta = {'session_id': 'field_test', 'dir': str(tmp_path)}
    m.last = {'session_id': 'field_test', 'phase': 'running', 'errors': []}
    m.proc = SimpleNamespace(alive=False, returncode=7, stop_requested=True)
    (tmp_path / 'state.json').write_text(json.dumps({'session_id': 'field_test', 'phase': 'failed', 'errors': ['clock stalled']}))
    st = m.state()
    assert st['phase'] == 'failed' and st['returncode'] == 7 and st['errors'][0] == 'clock stalled'
    assert len(m.state()['errors']) == len(st['errors'])
    app.state.lab.store.close()


def test_simulation_rejects_unsupported_footprint_and_fleet(tmp_path):
    run = solution()
    inst = copy.deepcopy(run['instance'])
    inst['robot_radius'] = 0.1
    with pytest.raises(ValueError, match='半径'):
        fieldworld.build(inst, run['routes'], tmp_path, 'field_test')
    with pytest.raises(ValueError, match='验收范围'):
        fieldworld.build(run['instance'], run['routes'] * 16, tmp_path, 'field_test')


def test_tree_collision_uses_exact_map_polygon(tmp_path):
    import xml.etree.ElementTree as ET
    run = solution()
    polygon = [[20, 10], [28, 10], [28, 11], [20, 11]]
    run['instance']['obstacles'] = [{'kind': 'tree', 'polygon': polygon}]
    fieldworld.build(run['instance'], run['routes'], tmp_path, 'field_test')
    tree = ET.parse(tmp_path / 'world.sdf').find(".//model[@name='obstacle_1']")
    center = [float(x) for x in tree.find('pose').text.split()[:2]]
    local = [[float(x) for x in p.text.split()] for p in tree.findall('.//collision/geometry/polyline/point')]
    assert [[p[0] + center[0], p[1] + center[1]] for p in local] == polygon


def test_parking_requires_clear_connection_to_depot():
    from shapely.geometry import LineString, Polygon
    run = solution()
    obstacle = [[4.15, 4], [4.25, 4], [4.25, 6], [4.15, 6]]
    run['instance']['obstacles'] = [{'polygon': obstacle}]
    vehicles = fieldworld.plan_vehicles(run['instance'], run['routes'])
    for v in vehicles:
        assert LineString(v.path[:2]).distance(Polygon(obstacle)) >= run['instance']['robot_radius']


def test_legacy_multitrip_plan_preserves_reload_before_repeated_stop():
    inst = instance()
    inst['vehicles']['capacity'] = 1
    inst['tasks'][1]['xy'] = inst['tasks'][0]['xy'][:]
    routes, check, *_ = fleet.solve({}, inst, 'panel.sweep', {})
    assert check['valid']
    for sv in routes[0]['services']:
        sv['position'] = None  # old stored results have no explicit vertex positions
    v = fieldworld.plan_vehicles(inst, routes)[0]
    assert v.tasks[1]['path_s'] - v.tasks[0]['path_s'] == pytest.approx(10)


@pytest.mark.parametrize('failure', [None, 'footprint', 'skipped_path', 'short_service', 'no_telemetry'])
def test_actual_trajectory_is_independently_verified(failure):
    from urp_lab.fieldcheck import verify
    inst = instance()
    v = {'name': 'v', 'label': '车', 'path': [[5, 5], [15, 5], [15, 15], [5, 5]],
         'tasks': [{'id': 1, 'service_s': 10}]}
    plan = {'instance': inst, 'vehicles': [v], 'travel': 'free', 'robot_radius_m': 0.49}
    result = {'trails': {'v': [[t, *xy, 0] for t, xy in enumerate(v['path'])]},
              'tasks': [{'vehicle': 'v', 'id': 1, 'state': 'reached', 't_sim': 3, 'serviced_at': 13}]}
    if failure == 'footprint':
        inst['obstacles'] = [{'polygon': [[9, 4.6], [11, 4.6], [11, 4.7], [9, 4.7]]}]
    elif failure == 'skipped_path':
        result['trails']['v'] = [[0, 5, 5, 0], [1, 5, 5, 0]]
    elif failure == 'short_service':
        result['tasks'][0]['serviced_at'] = 4
    elif failure == 'no_telemetry':
        result['trails']['v'] = []
    assert verify(plan, result)['valid'] is (failure is None)
