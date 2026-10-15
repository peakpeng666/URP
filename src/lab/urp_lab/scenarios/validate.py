"""Instance validation and normalisation (ValueError with a Chinese message when invalid)."""
from __future__ import annotations

import copy
import math

from shapely.geometry import Polygon

PROBLEM_CLASSES = ('turn_routing', 'euclidean_cvrp', 'coverage')
MAX_NODES = 5000
MAX_CVRP_TASKS = 1000


def _int(v, what: str, lo: int | None = None) -> int:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or float(v) != int(v):
        raise ValueError(f'{what} 应为整数，实际 {v!r}')
    v = int(v)
    if lo is not None and v < lo:
        raise ValueError(f'{what} 应 ≥ {lo}，实际 {v}')
    return v


def _num(v, what: str, positive: bool = False) -> float:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(float(v)):
        raise ValueError(f'{what} 应为有限数值，实际 {v!r}')
    if positive and v <= 0:
        raise ValueError(f'{what} 应为正数，实际 {v}')
    return float(v)


def _xy(p, what: str) -> list[float]:
    if not isinstance(p, (list, tuple)) or len(p) != 2:
        raise ValueError(f'{what} 应为 [x, y]')
    return [_num(p[0], what + '.x'), _num(p[1], what + '.y')]


def turn_routing(inst: dict) -> dict:
    out = copy.deepcopy(inst)
    arcs = []
    for i, a in enumerate(inst.get('arcs') or []):
        if not isinstance(a, (list, tuple)) or len(a) != 3:
            raise ValueError(f'arcs[{i}] 应为 [u, v, cost]')
        u, v, c = (_int(x, f'arcs[{i}]') for x in a)
        if c < 0:
            raise ValueError(f'arcs[{i}] 成本不能为负')
        if u == v:
            raise ValueError(f'arcs[{i}] 不能是自环')
        arcs.append([u, v, c])
    if not arcs:
        raise ValueError('转弯路网至少需要一条有向路段 arcs')
    if len({(u, v) for u, v, _ in arcs}) != len(arcs):
        raise ValueError('arcs 中存在重复的有向路段')
    nodes = {u for u, _, _ in arcs} | {v for _, v, _ in arcs}
    if len(nodes) > MAX_NODES:
        raise ValueError(f'节点数 {len(nodes)} 超过上限 {MAX_NODES}')
    depot = _int(inst.get('depot'), 'depot')
    if depot not in nodes:
        raise ValueError(f'仓库节点 {depot} 不在路网中')
    capacity = _int(inst.get('capacity'), 'capacity', 1)
    customers, seen_ids, seen_nodes = [], set(), set()
    for i, c in enumerate(inst.get('customers') or []):
        if not isinstance(c, dict):
            raise ValueError(f'customers[{i}] 应为对象')
        cid, node = _int(c.get('id'), f'customers[{i}].id', 0), _int(c.get('node'), f'customers[{i}].node')
        demand = _int(c.get('demand', 1), f'customers[{i}].demand', 1)
        if cid in seen_ids:
            raise ValueError(f'任务 id {cid} 重复')
        if node not in nodes:
            raise ValueError(f'任务 {cid} 的节点 {node} 不在路网中')
        if node == depot:
            raise ValueError(f'任务 {cid} 不能位于仓库节点')
        if node in seen_nodes:
            raise ValueError(f'节点 {node} 上有多个任务；请合并为一个任务')
        seen_ids.add(cid)
        seen_nodes.add(node)
        item = {**c, 'id': cid, 'node': node, 'demand': demand}
        item['label'] = str(c.get('label') or f'T{cid}')
        customers.append(item)
    if not customers:
        raise ValueError('至少需要一个任务')
    if len(customers) > 64:
        raise ValueError('任务数超过 64，超出面板支持范围')
    arcset = {(u, v) for u, v, _ in arcs}

    def triples(key: str, width: int) -> list:
        res = []
        for i, t in enumerate(inst.get(key) or []):
            if not isinstance(t, (list, tuple)) or len(t) != width:
                raise ValueError(f'{key}[{i}] 长度应为 {width}')
            t = [_int(x, f'{key}[{i}]') for x in t]
            if (t[0], t[1]) not in arcset or (t[1], t[2]) not in arcset:
                raise ValueError(f'{key}[{i}] {t[:3]} 引用了不存在的路段')
            if width == 4 and t[3] < 0:
                raise ValueError(f'{key}[{i}] 惩罚不能为负')
            res.append(t)
        return res

    coords = {}
    raw = inst.get('coordinates') or {}
    if raw:
        if not isinstance(raw, dict):
            raise ValueError('coordinates 应为 {节点id: [x, y]}')
        coords = {str(_int(int(k) if str(k).lstrip('-').isdigit() else k, 'coordinates 键')): _xy(v, f'coordinates[{k}]')
                  for k, v in raw.items()}
        missing = sorted(n for n in nodes if str(n) not in coords)
        if missing:
            raise ValueError(f'缺少节点坐标：{missing[:10]}')
    fleet = inst.get('fleet_limit')
    out.update(depot=depot, capacity=capacity, customers=customers, arcs=arcs,
               forbidden_turns=triples('forbidden_turns', 3), turn_penalties=triples('turn_penalties', 4),
               coordinates=coords, units=str(inst.get('units') or 'synthetic_integer_cost'),
               service_heading_reset=bool(inst.get('service_heading_reset', False)),
               depot_reset=str(inst.get('depot_reset') or 'between_routes_only'),
               fleet_limit=None if fleet is None else _int(fleet, 'fleet_limit', 1))
    if out['service_heading_reset']:
        raise ValueError('项目转弯模型要求 service_heading_reset=false（服务点不重置朝向）')
    if out['fleet_limit'] is not None:
        raise ValueError('项目转弯模型只支持不限数量的同型车辆（fleet_limit=null）')
    if isinstance(inst.get('node_kinds'), dict):
        out['node_kinds'] = {str(k): str(v) for k, v in inst['node_kinds'].items()}
    return out


def euclidean_cvrp(inst: dict) -> dict:
    out = copy.deepcopy(inst)
    coords = inst.get('coordinates')
    demands = inst.get('demands')
    if not isinstance(coords, list) or not isinstance(demands, list) or len(coords) != len(demands):
        raise ValueError('需要等长的 coordinates 与 demands 数组（下标 0 为仓库）')
    if len(coords) < 2:
        raise ValueError('至少需要一个任务点')
    if len(coords) - 1 > MAX_CVRP_TASKS:
        raise ValueError(f'任务数超过 {MAX_CVRP_TASKS}')
    coords = [_xy(p, f'coordinates[{i}]') for i, p in enumerate(coords)]
    demands = [_int(d, f'demands[{i}]', 0) for i, d in enumerate(demands)]
    if demands[0] != 0:
        raise ValueError('仓库（下标 0）的需求必须为 0')
    if any(d < 1 for d in demands[1:]):
        raise ValueError('任务需求须为正整数')
    capacity = _int(inst.get('capacity'), 'capacity', 1)
    if inst.get('depot', 0) != 0:
        raise ValueError('仓库必须是下标 0')
    fleet = inst.get('fleet', 'unlimited_identical_vehicles')
    if fleet != 'unlimited_identical_vehicles':
        raise ValueError('只支持不限数量的同型车辆（unlimited_identical_vehicles）')
    objective = inst.get('objective', 'sum_unrounded_euclidean_distance')
    if objective != 'sum_unrounded_euclidean_distance':
        raise ValueError('只支持未取整欧氏总距离目标')
    labels = inst.get('labels')
    if labels is not None and (not isinstance(labels, list) or len(labels) != len(coords)):
        raise ValueError('labels 长度应与坐标一致')
    out.update(coordinates=coords, demands=demands, capacity=capacity, depot=0, fleet=fleet, objective=objective,
               labels=[str(x) for x in labels] if labels else ['D'] + [str(i) for i in range(1, len(coords))])
    return out


def coverage(inst: dict) -> dict:
    out = copy.deepcopy(inst)
    field = [_xy(p, f'field[{i}]') for i, p in enumerate(inst.get('field') or [])]
    if len(field) < 3:
        raise ValueError('田块边界至少需要 3 个顶点')
    if field[0] == field[-1]:
        field = field[:-1]
    poly = Polygon(field)
    if not poly.is_valid or poly.area <= 0:
        raise ValueError('田块边界多边形无效（自交或面积为 0）')
    if not poly.exterior.is_ccw:
        field = field[::-1]
    obstacles = []
    for k, ob in enumerate(inst.get('obstacles') or []):
        pts = [_xy(p, f'obstacles[{k}][{i}]') for i, p in enumerate(ob)]
        if len(pts) < 3 or not Polygon(pts).is_valid:
            raise ValueError(f'障碍 {k} 多边形无效')
        obstacles.append(pts)
    swath = _num(inst.get('swath_width'), 'swath_width', True)
    head = _num(inst.get('headland_width', 0), 'headland_width')
    if head < 0:
        raise ValueError('headland_width 不能为负')
    turn = _num(inst.get('turn_radius', 0), 'turn_radius')
    width = _num(inst.get('robot_width', swath), 'robot_width', True)
    pattern = inst.get('route_pattern', 'boustrophedon')
    if pattern not in ('boustrophedon', 'snake', 'spiral'):
        raise ValueError('route_pattern 只能是 boustrophedon / snake / spiral')
    angle = inst.get('angle_deg')
    if poly.buffer(-head).is_empty:
        raise ValueError('地头宽度过大，田块内部为空')
    if poly.area / (swath * swath) > 200000:
        raise ValueError('田块相对作业幅宽过大（条带数超出面板范围）')
    out.update(field=field, obstacles=obstacles, swath_width=swath, headland_width=head, turn_radius=max(turn, 0.0),
               robot_width=width, start=_xy(inst.get('start') or field[0], 'start'), route_pattern=pattern,
               angle_deg=None if angle is None else _num(angle, 'angle_deg'))
    return out


def validate_instance(problem_class: str, instance: dict) -> dict:
    if problem_class not in PROBLEM_CLASSES:
        raise ValueError(f'未知问题类别 {problem_class!r}')
    if not isinstance(instance, dict):
        raise ValueError('instance 应为 JSON 对象')
    return {'turn_routing': turn_routing, 'euclidean_cvrp': euclidean_cvrp, 'coverage': coverage}[problem_class](instance)
