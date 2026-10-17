"""Independent acceptance probes; never modifies application sources or production data.

Run from repository root with --out /a/new/absolute/directory.
The output directory must not exist, so the original evidence is never overwritten.
The profile hook only records the actual OR-Tools solution before extraction.
"""
from pathlib import Path
import argparse
import copy
import json
import math
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src/lab'))
from urp_lab.scenarios.validate import validate_instance
from urp_lab.solvers import run_algorithm
from urp_lab.solvers import fleet
from urp_lab.field_dynamics import verify
from urp_lab.field_energy import account
from urp_lab.field_physics import profile

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--out', type=Path, required=True)
OUT = parser.parse_args().out
if not OUT.is_absolute():
    parser.error('--out must be an absolute path')
OUT.mkdir(parents=True, exist_ok=False)
results = {}


def clean(value):
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    if isinstance(value, dict):
        return {str(k): clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    return value


def save(name, data):
    (OUT / name).write_text(json.dumps(clean(data), ensure_ascii=False, indent=2) + '\n')


def fixture(travel='free'):
    return validate_instance('fleet_routing', {
        'boundary': [[0, 0], [60, 0], [60, 30], [0, 30]], 'depot': [3, 15],
        'objective': 'makespan', 'unload_points': [[38, 15]],
        'tasks': [{'id': i + 1, 'xy': [45 + 4 * (i % 3), 8 + 12 * (i % 2)], 'demand': 4} for i in range(8)],
        'vehicles': {'count': 1, 'capacity': 16, 'speed_mps': 1, 'trips': 'multi', 'travel': travel},
        'robot_radius': .5})


observed = []


def capture(frame, event, arg):
    if event != 'return' or frame.f_code.co_name != 'ortools_makespan':
        return
    loc = frame.f_locals
    if loc.get('sol') is None:
        return
    routing, manager, sol, orig = (loc[k] for k in ('routing', 'manager', 'sol', 'orig'))
    vehicles = []
    for v in range(loc['K']):
        idx, nodes = routing.Start(v), []
        while True:
            node = manager.IndexToNode(idx)
            nodes.append({'model_node': node, 'graph_node': orig[node],
                          'load_before': sol.Value(loc['cap_dim'].CumulVar(idx)),
                          'time_s': sol.Value(loc['time_dim'].CumulVar(idx)) / 10})
            if routing.IsEnd(idx):
                break
            idx = sol.Value(routing.NextVar(idx))
        vehicles.append(nodes)
    observed.append({'solver_routes': vehicles, 'extracted_return': arg})


scenario = {'problem_class': 'fleet_routing', 'frame': {'kind': 'field'}, 'cost_unit': 's'}
for travel in ['free', 'rows']:
    inst = fixture(travel)
    graph = fleet.travel_graph(inst)
    sys.setprofile(capture)
    try:
        answer = run_algorithm(scenario, inst, 'ortools.fleet', {'time_limit_s': 5, 'seed': 42})
    finally:
        sys.setprofile(None)
    save(f'unload-{travel}.json', {'instance': inst, 'graph_points': graph.points,
                                  'raw_solver': observed[-1], 'result': answer})
    results[f'unload_{travel}'] = {
        'status': answer['status'], 'check': answer['check'],
        'makespan_s': answer['metrics'].get('makespan_s'),
        'model_final_time_s': max(v[-1]['time_s'] for v in observed[-1]['solver_routes']),
        'reload_stops': [r.get('reload_stops') for r in answer['routes']],
        'graph_task_1': graph.points[1], 'expected_task_1': inst['tasks'][0]['xy']}

# A forward-only vehicle cannot reverse instantaneously on a straight line with R >= 2 m.
inst = validate_instance('fleet_routing', {
    'boundary': [[-5, -5], [5, -5], [5, 5], [-5, 5]], 'depot': [0, 0],
    'tasks': [{'id': 1, 'xy': [1, 0], 'demand': 1}],
    'vehicles': {'fleet': [{'count': 1, 'capacity': 1, 'min_turn_radius_m': 2}], 'travel': 'free'},
    'robot_radius': .5})
pts = [[i / 20, 0] for i in range(21)] + [[i / 20, 0] for i in range(19, -1, -1)]
route = {'vehicle': 0, 'sequence': [1], 'trips': [[1]], 'services': [{'task': 1, 'stop': [1, 0], 'position': 20}],
         'polyline': pts, 'cost': 2, 'duration_s': 2, 'load': 1, 'min_turn_radius_m': 2}
checked = fleet.check(inst, [route])
results['curvature_reversal'] = {'expected_valid': False, 'actual': checked,
                                'sampled_radius_m': fleet.min_curvature_radius(pts)}
save('curvature-reversal.json', {'instance': inst, 'routes': [route], **results['curvature_reversal']})

# Missing observations do not prove stationarity, especially with nonzero observed odometry speed.
p = [[t, 0, 0, 0, 0, 0, 0] for t in [0, 10, 20]]
o = [[t, 0, 0, 0, 1, 0] for t in [0, 10, 20]]
sample = {'vehicles': [{'name': 'car'}], 'truth_timing': {'tf_header_samples': 3, 'latest_clock_samples': 0},
          'rigid_body_poses': {'car': p}, 'wheel_odometry': {'car': o},
          'trails': {'car': [[row[i] for i in (0, 1, 2, 6)] for row in p]}}
results['telemetry_gap'] = {'expected_valid': False, 'actual': verify(sample)}
save('telemetry-gap.json', {'input': sample, **results['telemetry_gap']})

# Same accelerate/cruise/brake movement, only a parked tail is changed.
energy = []
for parked_s in [0, 120, 600]:
    samples = []
    for k in range(round((8 + parked_s) * 50) + 1):
        t = k / 50
        x = .5 * t * t if t < 1 else t - .5 if t < 5 else 4.5 + (t - 5) - .5 * (t - 5) ** 2 if t < 6 else 5.0
        samples.append([t, x, 0, 0])
    item = account(samples, profile())
    energy.append({'parked_tail_s': parked_s, **item})
results['energy_parked_tail'] = energy

hetero = {'boundary': [[0, 0], [30, 0], [30, 30], [0, 30]], 'depot': [3, 3],
          'tasks': [{'id': 1, 'xy': [10, 10], 'demand': 1}, {'id': 2, 'xy': [20, 20], 'demand': 10}],
          'vehicles': {'fleet': [{'name': 'small', 'count': 1, 'capacity': 1},
                                 {'name': 'large', 'count': 1, 'capacity': 10}], 'travel': 'free'}, 'robot_radius': .5}
try:
    normalized = validate_instance('fleet_routing', hetero)
    results['hetero_mixed_demands'] = {'accepted': True, 'instance': normalized}
except ValueError as exc:
    results['hetero_mixed_demands'] = {'accepted': False, 'error': str(exc), 'instance': hetero}

save('reproductions.json', results)
for key, value in results.items():
    if key == 'energy_parked_tail':
        value = [{k: row[k] for k in ['parked_tail_s', 'energy_j', 'peak_power_w', 'peak_wheel_torque_nm']} for row in value]
    print(json.dumps(clean({key: value}), ensure_ascii=False))
