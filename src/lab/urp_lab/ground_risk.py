"""Ground-risk-aware planning: declared known-map ground information enters the
fleet solver's edge costs and the executed speed profile.

Semantics (versioned, one policy this round):
- The instance may declare ``ground``: axis-aligned zones with a friction
  coefficient μ and optional label, plus ``mu_reference`` (default 1.0) and a
  ``knowledge`` tag. This is *the map the planner is allowed to read* — a declared
  known-map condition, not a prediction of execution.
- With ``ground_policy='risk_adjust'`` a visible edge's solver weight becomes the
  *risk-adjusted length*:  geometric length × (1 + w · Σ fraction_in_zone · (1 - μ/μ_ref)).
  Units stay metres (equivalent metres); the geometric length is still computed and
  reported separately. This is a declared cost preference — NOT a failure
  probability and NOT an energy value.
- ``speed_policy`` maps low-friction zones to a speed cap for execution
  (v_limit while inside). Caps are engineering assumptions from friction margins
  for acceleration/turning; they are enforced on the controller, and the executed
  trajectory is checked against them.
- The world generator consumes the *same* zone rectangles as actual physics
  friction partitions, and the frozen plan records both the planner map and the
  world map so any deliberate mismatch is auditable.
"""
from __future__ import annotations

import math

from shapely.geometry import LineString, Polygon

SCHEMA = 'urp.ground-risk/1'
# Planning exposure is computed over the zone grown by the robot's half track + wheel
# radius (spherical-wheel footprint ~0.48 m): a centre line just outside a low-mu patch
# still puts wheels on it. The physics partition itself stays the declared rectangle.
RISK_MARGIN_M = 0.5
SPEED_POLICY = {'mu_threshold': 0.5, 'v_limit_mps': 0.35,
                'note': '工程假设：μ<0.5 的分区按低附着限速 0.35 m/s 通过（加减速/转向摩擦裕量），未标定'}


def normalize_ground(inst: dict) -> dict | None:
    """Validate and normalize an instance-level ground declaration (known map).

    Idempotent: an already-normalized declaration (from validate_instance) passes
    through unchanged so solver and checker share one normalized form."""
    ground = inst.get('ground')
    if not ground:
        return None
    if not isinstance(ground, dict):
        raise ValueError('ground 须为对象')
    if ground.get('schema') == SCHEMA and isinstance(ground.get('zones'), list):
        return ground
    unknown = set(ground) - {'zones', 'mu_reference', 'knowledge'}
    if unknown:
        raise ValueError(f'ground 含未知字段：{sorted(unknown)}')
    zones = ground.get('zones')
    if not isinstance(zones, list) or not zones:
        raise ValueError('ground.zones 须为非空数组')
    if len(zones) > 16:
        raise ValueError('ground.zones 至多 16 个分区')
    mu_ref = float(ground.get('mu_reference', 1.0))
    if not math.isfinite(mu_ref) or not 0.05 <= mu_ref <= 2.0:
        raise ValueError('ground.mu_reference 须在 0.05–2.0')
    bounds = Polygon(inst['boundary']).bounds
    rects = []
    for i, z in enumerate(zones):
        if not isinstance(z, dict) or set(z) - {'rect', 'mu', 'label'}:
            raise ValueError(f'ground.zones[{i}] 仅接受 rect/mu/label')
        rect = z.get('rect')
        if (not isinstance(rect, (list, tuple)) or len(rect) != 4
                or not all(isinstance(c, (int, float)) and math.isfinite(c) for c in rect)):
            raise ValueError(f'ground.zones[{i}].rect 须为 4 个有限数字 [x0,y0,x1,y1]')
        x0, y0, x1, y1 = (float(c) for c in rect)
        if x1 - x0 < 0.5 or y1 - y0 < 0.5:
            raise ValueError(f'ground.zones[{i}] 尺寸过小（每边至少 0.5 m）')
        mu = z.get('mu')
        if isinstance(mu, bool) or not isinstance(mu, (int, float)) or not math.isfinite(mu) or not 0.03 <= mu <= 1.0:
            raise ValueError(f'ground.zones[{i}].mu 须在 0.03–1.0')
        if not (bounds[0] <= x0 and bounds[1] <= y0 and x1 <= bounds[2] and y1 <= bounds[3]):
            raise ValueError(f'ground.zones[{i}] 超出田块边界')
        rect_n = [min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)]
        for other in rects:
            if not (rect_n[2] <= other[0] or other[2] <= rect_n[0] or rect_n[3] <= other[1] or other[3] <= rect_n[1]):
                raise ValueError('ground.zones 之间不允许重叠')
        depot = inst['depot']
        if x0 < depot[0] + 2.5 and x1 > depot[0] - 2.5 and y0 < depot[1] + 2.5 and y1 > depot[1] - 2.5:
            raise ValueError(f'ground.zones[{i}] 须避开车库周围 2.5 m')
        rects.append(rect_n)
    knowledge = str(ground.get('knowledge') or 'known_map_v1')
    return {'schema': SCHEMA, 'zones': [{'rect': r,
                                         'risk_rect': [r[0] - RISK_MARGIN_M, r[1] - RISK_MARGIN_M,
                                                       r[2] + RISK_MARGIN_M, r[3] + RISK_MARGIN_M],
                                         'mu': float(z['mu']),
                                         'label': str(z.get('label') or f'ground_{i + 1}')}
                                        for z, r in zip(zones, rects)],
            'mu_reference': mu_ref, 'knowledge': knowledge,
            'speed_policy': dict(SPEED_POLICY),
            'declared_as': '规划器可读的已知地面图（声明条件）；风险成本为当量米，不是失败概率'}


def exposure_line(seg, zones, footprint_aware=True):
    """In-zone length of a segment and the friction deficit. With footprint_aware,
    exposure uses the zone grown by RISK_MARGIN_M (wheels reach beyond the centre line);
    the reported `inside` stays on the physical rectangle."""
    line = LineString(seg)
    inside = 0.0
    deficit = 0.0
    for z in zones:
        x0, y0, x1, y1 = z.get('risk_rect') if footprint_aware and z.get('risk_rect') else z['rect']
        x0p, y0p, x1p, y1p = z['rect']
        part = line.intersection(Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)]))
        if not part.is_empty:
            inside += line.intersection(Polygon([(x0p, y0p), (x1p, y0p), (x1p, y1p), (x0p, y1p)])).length
            deficit += part.length * (1.0 - z['mu'])
    return inside, deficit


def risk_factor(seg, zones, mu_reference):
    """Per-metre multiplicative risk factor of a segment (>= 1 zone fraction × μ deficit)."""
    length = math.hypot(seg[1][0] - seg[0][0], seg[1][1] - seg[0][1])
    if length < 1e-9:
        return 0.0
    _inside, deficit = exposure_line(seg, zones)
    return deficit / length / max(mu_reference, 1e-6)


def speed_profile(path, zones, speed_policy, base_speed):
    """Arc-length intervals with a speed cap while the path is inside low-μ zones.

    Returns [[s0, s1, v_limit], ...] merged, ascending, v_limit <= base_speed.
    """
    threshold = float(speed_policy.get('mu_threshold', SPEED_POLICY['mu_threshold']))
    v_low = min(float(speed_policy.get('v_limit_mps', SPEED_POLICY['v_limit_mps'])), float(base_speed))
    low = [z for z in zones if z['mu'] < threshold]
    if not low or v_low >= base_speed - 1e-9:
        return []
    caps = []
    s = 0.0
    for a, b in zip(path, path[1:]):
        seg_len = math.dist(a, b)
        if seg_len < 1e-9:
            continue
        _inside, deficit = exposure_line([a, b], low)
        # a segment touching low ground at all is capped (conservative at boundaries)
        if deficit > 0 or _inside > 0:
            caps.append([round(s, 3), round(s + seg_len, 3), round(v_low, 3)])
        s += seg_len
    merged = []
    for c in caps:
        if merged and abs(merged[-1][1] - c[0]) < 1e-6 and abs(merged[-1][2] - c[2]) < 1e-9:
            merged[-1][1] = c[1]
        else:
            merged.append(c)
    return merged


def route_ground_stats(path, zones, mu_reference):
    """Geometric exposure and average friction deficit of a finished polyline."""
    inside = deficit = total = 0.0
    for a, b in zip(path, path[1:]):
        seg = math.dist(a, b)
        total += seg
        i, d = exposure_line([a, b], zones)
        inside += i
        deficit += d
    return {'geo_length_m': round(total, 3),
            'in_zone_length_m': round(inside, 3),
            'mean_mu_deficit': round(deficit / total, 4) if total > 1e-6 else 0.0,
            'risk_adjusted_length_m': round(total + deficit / max(mu_reference, 1e-6), 3)}


def resolve_policy(inst, params):
    """Validate ground-policy solver params against the instance; returns
    (policy, weight, normalized_ground_or_None). Raises ValueError with a clear
    reason when the policy is unsupported for this instance."""
    policy = str(params.get('ground_policy', 'ignore'))
    if policy not in ('ignore', 'risk_adjust'):
        raise ValueError('ground_policy 仅支持 ignore、risk_adjust')
    weight = params.get('ground_risk_weight', 1.0)
    try:
        weight = float(weight)
    except (TypeError, ValueError):
        raise ValueError('ground_risk_weight 须为数值')
    if not math.isfinite(weight) or not 0 <= weight <= 10:
        raise ValueError('ground_risk_weight 须为 0–10 的有限数值')
    ground = normalize_ground(inst) if inst.get('ground') else None
    if policy == 'risk_adjust':
        if ground is None:
            raise ValueError('ground_policy=risk_adjust 需要 instance 声明 ground（已知地面图）')
        if str(inst.get('objective') or 'total_distance') == 'makespan':
            raise ValueError('ground_policy=risk_adjust 本轮仅支持 total_distance 目标；当量米未定义时间口径，makespan 请用 ignore')
        if inst['vehicles'].get('travel') == 'rows':
            raise ValueError('ground_policy=risk_adjust 暂只支持自由通行；沿行间模式的边为固定通道，不支持绕行风险调整')
    return policy, weight, ground


def check_route_ground(route, inst, pts, errors):
    """Independent recomputation of a route's ground-risk fields for the fleet checker.
    Appends human-readable errors; returns None."""
    if not route.get('ground_risk'):
        return
    if not inst.get('ground'):
        errors.append('路线声明地面风险成本但 instance 缺少 ground 声明')
        return
    gnd = normalize_ground(inst)
    stats = route_ground_stats(pts, gnd['zones'], gnd['mu_reference'])
    for key, expected in (('geo_length_m', stats['geo_length_m']),
                          ('risk_cost', stats['risk_adjusted_length_m'])):
        value = route.get(key)
        import math as _m
        if not isinstance(value, (int, float)) or not _m.isclose(float(value), float(expected), abs_tol=5e-3):
            errors.append(f'路线的地面风险口径 {key} 与独立复算不一致')


def attach_route_ground(route, pts, ground, policy_active, base_speed):
    """Attach ground exposure stats (always, for evaluation) and the executed speed
    profile (only when the policy actually used the declared map) to a built route."""
    stats = route_ground_stats(pts, ground['zones'], ground['mu_reference'])
    route.update(geo_length_m=stats['geo_length_m'], risk_cost=stats['risk_adjusted_length_m'],
                 ground_stats=stats, ground_risk={'policy': 'risk_adjust' if policy_active else 'ignore',
                                                  'weight': 1.0, 'mu_reference': ground['mu_reference'],
                                                  'knowledge': ground['knowledge']})
    if policy_active:
        route['speed_profile'] = speed_profile(pts, ground['zones'], ground['speed_policy'], base_speed)
    return route
