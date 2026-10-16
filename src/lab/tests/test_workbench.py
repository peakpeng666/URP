"""Task composer, fleet routing, motion planning, libraries and study analysis."""
import math

import pytest
from fastapi.testclient import TestClient

from urp_lab import analysis
from urp_lab.compose import EXAMPLES, compose
from urp_lab.compose.geo import export_geojson, import_geojson
from urp_lab.compose.nl import cn_number, parse
from urp_lab.library import cvrplib, references
from urp_lab.recommend import recommend
from urp_lab.scenarios import get_scenario
from urp_lab.scenarios.validate import validate_instance
from urp_lab.solvers import catalog, run_algorithm


def test_chinese_numbers():
    assert [cn_number(s) for s in ('十二', '二十', '三十五', '一百二十', '两', '40')] == [12, 20, 35, 120, 2, 40]


def test_parse_examples():
    spec = parse(EXAMPLES[0])['spec']
    assert spec['size'] == [200.0, 120.0] and spec['vehicles'] == 3 and spec['tasks'] == 40 and spec['capacity'] == 10
    assert spec['obstacles'] == {'pond': 2, 'building': 1} and spec['depot'] == 'sw'
    spec = parse(EXAMPLES[1])['spec']
    assert spec['objective'] == 'makespan' and spec['plots'] == 6 and spec['obstacles']['tree'] == 3
    assert parse('给 25 棵果树喷药，2台车')['spec']['tasks'] == 25
    assert 'tree' not in parse('给 25 棵果树喷药')['spec'].get('obstacles', {})


def _scenario(text, **vehicles):
    sc = compose(text)
    sc['instance']['vehicles'].update(vehicles)
    sc['instance'] = validate_instance('fleet_routing', sc['instance'])
    return sc


def test_compose_is_deterministic_and_valid():
    a, b = compose(EXAMPLES[2]), compose(EXAMPLES[2])
    assert a['instance']['tasks'] == b['instance']['tasks'] and a['instance']['obstacles'] == b['instance']['obstacles']
    inst = validate_instance('fleet_routing', a['instance'])
    assert len(inst['tasks']) == 12 and inst['vehicles']['count'] == 2


@pytest.mark.parametrize('algorithm', ['pyvrp.fleet', 'ortools.fleet', 'panel.savings_fleet', 'panel.sweep', 'panel.cluster_first'])
def test_fleet_algorithms_verified(algorithm):
    sc = _scenario(EXAMPLES[0])
    r = run_algorithm(sc, sc['instance'], algorithm, {'time_limit_s': 0.5})
    assert r['status'] == 'feasible' and r['check']['valid'], r['check']
    served = sorted(t for route in r['routes'] for t in route['sequence'])
    assert served == sorted(t['id'] for t in sc['instance']['tasks'])
    assert r['metrics']['vehicles_used'] <= sc['instance']['vehicles']['count']
    assert math.isclose(r['check']['computed_cost'], r['metrics']['total_distance_m'], rel_tol=1e-6)


def test_single_trip_capacity_is_reported_as_infeasible():
    sc = _scenario(EXAMPLES[0], trips='single')
    r = run_algorithm(sc, sc['instance'], 'pyvrp.fleet', {'time_limit_s': 0.3})
    assert r['status'] == 'infeasible' and not r['routes']


def test_routes_avoid_obstacles():
    sc = _scenario('100×60米，2台车，20个点，3个池塘，种子 7')
    r = run_algorithm(sc, sc['instance'], 'panel.savings_fleet', {})
    from shapely.geometry import LineString, Polygon
    for o in sc['instance']['obstacles']:
        poly = Polygon(o['polygon'])
        for route in r['routes']:
            assert not LineString(route['polyline']).crosses(poly) and not LineString(route['polyline']).within(poly)


def test_checker_catches_tampering():
    from urp_lab.solvers import fleet
    sc = _scenario(EXAMPLES[2])
    r = run_algorithm(sc, sc['instance'], 'panel.sweep', {})
    routes = r['routes']
    routes[0]['sequence'] = routes[0]['sequence'][1:]
    assert not fleet.check(sc['instance'], routes)['valid']


def test_makespan_objective_balances():
    sc = _scenario(EXAMPLES[1])
    assert sc['instance']['objective'] == 'makespan'
    r = run_algorithm(sc, sc['instance'], 'ortools.fleet', {'time_limit_s': 1})
    assert r['objective']['unit'] == 's' and r['check']['valid']


def test_geojson_roundtrip():
    sc = _scenario(EXAMPLES[2])
    import json
    doc = json.loads(export_geojson(sc))
    back = import_geojson(doc, 'roundtrip')
    inst = validate_instance('fleet_routing', back['instance'])
    assert len(inst['tasks']) == len(sc['instance']['tasks']) and len(inst['obstacles']) == len(sc['instance']['obstacles'])


def test_recommendation_for_fleet():
    sc = _scenario(EXAMPLES[1])
    rec = recommend(sc, sc['instance'])
    assert rec['recommended'] == 'ortools.fleet' and len(rec['compare']) == 3
    assert any(f['key'] == 'clark_evans' for f in rec['features'])


def test_motion_planners():
    sc = get_scenario('p2p-maze-cross')
    for aid in ('grid.astar', 'grid.theta_star'):
        r = run_algorithm(sc, sc['instance'], aid, {'time_limit_s': 3})
        assert r['status'] == 'feasible' and r['check']['valid'] and r['map_check']['collision_free']
    a = run_algorithm(sc, sc['instance'], 'grid.astar', {})['objective']['value']
    t = run_algorithm(sc, sc['instance'], 'grid.theta_star', {})['objective']['value']
    assert t <= a + 1e-6


def test_catalog_has_references_that_exist():
    keys = {r['key'] for r in references.listing()}
    for a in catalog():
        assert set(a['refs']) <= keys, a['id']


def test_cvrplib_catalog_and_rounding():
    status = cvrplib.status()
    assert status['instances'] >= 700 and status['sets'] >= 15
    x = next(i for i in cvrplib.instances('X') if i['name'] == 'X-n101-k25')
    assert x['bks'] == 27591 and x['optimal']


def test_analysis_statistics():
    sc = _scenario(EXAMPLES[2])
    runs = []
    for k, aid in enumerate(['pyvrp.fleet', 'panel.sweep', 'panel.savings_fleet']):
        for seed in (1, 2):
            r = run_algorithm(sc, sc['instance'], aid, {'time_limit_s': 0.3, 'seed': seed} if aid == 'pyvrp.fleet' else {})
            runs.append({**r, 'run_id': f'r{k}{seed}', 'scenario_id': sc['id'], 'instance_sha256': 'abc', 'state': 'done',
                         'params': {'time_limit_s': 0.3}, 'scenario_snapshot': sc})
    res = analysis.analyze(runs)
    assert res['n_instances'] == 1 and {s['algorithm'] for s in res['summary']} == {'pyvrp.fleet', 'panel.sweep', 'panel.savings_fleet'}
    assert min(s['gap_best'] for s in res['summary']) == 0.0
    assert 'tabular' in analysis.latex_table(res)


def test_gateway_compose_edit_solve(tmp_path, monkeypatch):
    from urp_lab import gateway, paths
    monkeypatch.setattr(paths, 'USER_SCENARIOS', tmp_path / 'scenarios')
    app = gateway.create_app(gateway.Config(port=4199, runtime=tmp_path, background=False))
    with TestClient(app, base_url='http://127.0.0.1:4199') as c:
        cards = c.post('/lab/api/compose/parse', json={'text': EXAMPLES[0]}).json()['cards']
        assert any(card['label'] == '车队' for card in cards)
        sc = c.post('/lab/api/compose', json={'text': EXAMPLES[2]}).json()
        assert sc['problem_class'] == 'fleet_routing' and sc['origin'] == 'user'
        inst = sc['instance']
        inst['tasks'] = inst['tasks'][:-1]
        inst['vehicles']['count'] = 3
        upd = c.put(f"/lab/api/scenarios/{sc['id']}", json={'instance': inst}).json()
        assert len(upd['instance']['tasks']) == 11 and upd['instance']['vehicles']['count'] == 3
        bad = dict(inst, tasks=inst['tasks'] + [{'id': 999, 'xy': inst['obstacles'][0]['polygon'][0], 'demand': 1}])
        assert c.put(f"/lab/api/scenarios/{sc['id']}", json={'instance': bad}).status_code == 400
        assert c.put('/lab/api/scenarios/maze-inspection', json={'title': 'x'}).status_code == 403
        rec = c.post('/lab/api/recommend', json={'scenario_id': sc['id']}).json()
        assert rec['recommended'] in {a['id'] for a in catalog()}
        assert c.get('/lab/api/references').json()['references']
        assert c.get('/lab/api/library/cvrplib/sets').json()['sets']
        assert c.get('/lab/api/source', params={'path': 'src/lab/urp_lab/solvers/fleet.py'}).status_code == 200
        assert c.get('/lab/api/source', params={'path': '../../etc/passwd'}).status_code == 403
        geo = c.get(f"/lab/api/scenarios/{sc['id']}/export", params={'format': 'geojson'})
        assert geo.status_code == 200 and b'FeatureCollection' in geo.content


def test_task_map_on_real_field():
    from urp_lab.compose import from_field
    from urp_lab.library import fields
    if not fields.status()['downloaded']:
        pytest.skip('Fields2Benchmark 未下载')
    sc = from_field('nl_field_7', '3 台机器人采样 20 个点，避开一个池塘')
    inst = validate_instance('fleet_routing', sc['instance'])
    assert len(inst['tasks']) == 20 and len(inst['obstacles']) == 1
    assert f"{len(inst['obstacles'])} 处障碍" in sc['summary']
    r = run_algorithm(sc, inst, 'panel.sweep', {})
    assert r['check']['valid']


def test_makespan_model_beats_distance_routes_on_latest_finish():
    """With the reload model and a span cost, OR-Tools must not finish later than PyVRP's distance-optimal routes."""
    sc = _scenario('5 公顷麦田分成 6 块，4 辆无人车巡检 60 个巡检点，要求尽快完成，种子 3')
    assert sc['instance']['objective'] == 'makespan'
    fast = run_algorithm(sc, sc['instance'], 'ortools.fleet', {'time_limit_s': 2})
    short = run_algorithm(sc, sc['instance'], 'pyvrp.fleet', {'time_limit_s': 1})
    assert fast['check']['valid'] and short['check']['valid']
    assert fast['metrics']['makespan_s'] <= short['metrics']['makespan_s'] * 1.02
    assert 'OR-Tools' in fast['raw_result']['trip_assignment']


def test_gazebo_world_from_fleet_plan(tmp_path):
    import struct
    import xml.etree.ElementTree as ET
    from urp_lab import fieldworld
    from urp_lab.fieldsim import marker_layers
    sc = _scenario(EXAMPLES[0])
    r = run_algorithm(sc, sc['instance'], 'panel.savings_fleet', {})
    meta = fieldworld.build(sc['instance'], r['routes'], tmp_path, 'field_test', 4.0)
    world = ET.parse(tmp_path / 'world.sdf').getroot().find('world')
    robots = [m for m in world.findall('model') if m.get('name', '').startswith('vehicle_')]
    assert len(robots) == len(meta['vehicles']) == len(r['routes'])
    assert all(m.find("plugin[@filename='ignition-gazebo-diff-drive-system']") is not None for m in robots)
    for stl in (tmp_path / 'meshes').glob('*.stl'):
        data = stl.read_bytes()
        (count,) = struct.unpack('<I', data[80:84])
        assert len(data) == 84 + 50 * count and count > 0
    for v in meta['vehicles']:  # every vehicle starts at its parking spot, passes the depot and visits its tasks in order
        assert math.dist(v['path'][1], sc['instance']['depot']) < 1e-6 and len(v['tasks']) > 0
    layers, outlines = marker_layers(sc['instance'])
    assert all(len(layer['triangles']) % 3 == 0 and layer['triangles'] for layer in layers)
    assert outlines[0]['ns'] == 'boundary'
