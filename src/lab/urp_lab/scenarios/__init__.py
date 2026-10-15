"""Scenario registry (CONTRACT §2.1, §3): built-in benchmark/map scenarios plus user imports in runtime/scenarios/."""
from __future__ import annotations

import copy
import json
import re
from functools import lru_cache

from .. import paths
from . import benchmark, field, maps
from .validate import PROBLEM_CLASSES, validate_instance

__all__ = ['list_scenarios', 'get_scenario', 'validate_instance', 'world_map', 'map_png', 'import_scenario',
           'summary', 'task_count', 'node_count']

ID_RE = re.compile(r'^[a-z0-9][a-z0-9_.-]{1,63}$')


@lru_cache(maxsize=None)
def _builtin() -> dict:
    items = field.map_scenarios() + benchmark.turn_scenarios() + benchmark.cvrp_scenarios()
    out = {}
    for s in items:
        s['instance'] = validate_instance(s['problem_class'], s['instance'])
        s['origin'] = 'builtin'
        out[s['id']] = s
    return out


def _user() -> dict:
    out = {}
    if paths.USER_SCENARIOS.is_dir():
        for f in sorted(paths.USER_SCENARIOS.glob('*.json')):
            try:
                s = json.loads(f.read_text(encoding='utf-8'))
            except (OSError, json.JSONDecodeError):
                continue
            if isinstance(s, dict) and s.get('id') and s['id'] not in _builtin():
                out[s['id']] = s
    return out


def task_count(problem_class: str, inst: dict) -> int:
    if problem_class == 'turn_routing':
        return len(inst.get('customers') or [])
    if problem_class == 'euclidean_cvrp':
        return max(0, len(inst.get('coordinates') or []) - 1)
    return 0


def node_count(problem_class: str, inst: dict) -> int | None:
    if problem_class == 'turn_routing':
        return len({u for u, _, _ in inst['arcs']} | {v for _, v, _ in inst['arcs']})
    if problem_class == 'euclidean_cvrp':
        return len(inst.get('coordinates') or [])
    return None


def summary(s: dict) -> dict:
    out = {k: copy.deepcopy(s.get(k)) for k in ('id', 'title', 'summary', 'problem_class', 'frame', 'cost_unit', 'sim')}
    out['task_count'] = task_count(s['problem_class'], s['instance'])
    out['node_count'] = node_count(s['problem_class'], s['instance'])
    out['origin'] = s.get('origin', 'builtin')
    return out


def list_scenarios() -> list[dict]:
    return [summary(s) for s in list(_builtin().values()) + list(_user().values())]


def get_scenario(scenario_id: str) -> dict:
    s = _builtin().get(scenario_id) or _user().get(scenario_id)
    if s is None:
        raise KeyError(scenario_id)
    return copy.deepcopy(s)


def world_map(world: str) -> dict:
    return maps.world_map(world)


def map_png(world: str) -> bytes:
    return maps.map_png(world)


def import_scenario(obj: dict) -> dict:
    """Validate and store a user scenario; returns its summary. ValueError(中文) when invalid."""
    if not isinstance(obj, dict):
        raise ValueError('场景应为 JSON 对象')
    sid = str(obj.get('id') or '').strip().lower()
    if not ID_RE.match(sid):
        raise ValueError('场景 id 须为 2–64 位小写字母、数字、-、_、.（以字母或数字开头）')
    if sid in _builtin():
        raise ValueError(f'场景 id {sid} 与内置场景重名')
    pc = obj.get('problem_class')
    if pc not in PROBLEM_CLASSES:
        raise ValueError(f'problem_class 须为 {" / ".join(PROBLEM_CLASSES)}')
    inst = validate_instance(pc, obj.get('instance'))
    frame_in = obj.get('frame') or {'kind': 'benchmark'}
    if frame_in.get('kind') == 'map':
        world = frame_in.get('world')
        if world not in maps.known_worlds():
            raise ValueError(f'地图坐标场景须指定已知世界：{", ".join(maps.known_worlds())}')
        frame = field._frame(world)
        spawn = maps.default_spawn(world)
        sim = {'supported': True, 'world': world, 'spawn': spawn, 'reason': None,
               'start_pose_after_undock': maps.start_pose_after_undock(spawn)}
        note = '用户导入的地图坐标（米）场景：仿真使用该世界默认生成位姿；地图间隙由每次求解的 map_check 报告。'
    elif frame_in.get('kind', 'benchmark') == 'benchmark':
        frame = dict(benchmark.BENCH_FRAME)
        sim = dict(benchmark.NO_SIM)
        note = '用户导入的基准坐标（无单位）场景。'
    else:
        raise ValueError('frame.kind 须为 benchmark 或 map')
    default_unit = {'turn_routing': 'cm_equivalent' if frame['kind'] == 'map' else 'synthetic_integer_cost'}.get(pc, 'euclidean')
    scenario = {
        'id': sid, 'title': str(obj.get('title') or sid)[:80], 'summary': str(obj.get('summary') or '用户导入场景')[:400],
        'problem_class': pc, 'frame': frame, 'cost_unit': str(obj.get('cost_unit') or default_unit),
        'provenance': {'generator': 'user_import', 'params': {}, 'seed': None,
                       'note': note + (' 原始说明：' + str(obj['provenance'].get('note'))[:300]
                                       if isinstance(obj.get('provenance'), dict) and obj['provenance'].get('note') else '')},
        'sim': sim, 'instance': inst,
        'editable': {'tasks': True, 'depot': frame['kind'] != 'map', 'capacity': pc != 'coverage', 'demands': pc != 'coverage'},
        'layers': obj.get('layers') if isinstance(obj.get('layers'), dict) else {},
        'origin': 'user',
    }
    paths.USER_SCENARIOS.mkdir(parents=True, exist_ok=True)
    target = paths.USER_SCENARIOS / f'{sid}.json'
    tmp = target.with_suffix('.json.tmp')
    tmp.write_text(json.dumps(scenario, ensure_ascii=False, indent=1), encoding='utf-8')
    tmp.replace(target)
    return summary(scenario)
