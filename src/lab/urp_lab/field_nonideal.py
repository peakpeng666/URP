"""Non-ideal field execution: ground friction partitioning, localization observation
error model and the estimator the controller is allowed to use.

Scope declarations (these travel with every record):
- Ground zones are *Coulomb friction partitions*: thin low-grip patches on the rigid
  plane. They are a low-adhesion proxy, not a soil-mechanics model (no sinkage,
  compaction or shear-strength parameters); every μ is an uncalibrated engineering
  assumption inside literature ranges for rubber on wet/loose surfaces.
- Slip itself is *not* injected: it emerges in DART when the demanded contact force
  exceeds μ·N. Wheel odometry integrates wheel angles, so it inherits the slip error;
  no synthetic odometry noise is added on top by default.
- Absolute-position fixes are synthetic observations of the truth pose under a
  declared error model (bias + random-walk drift + noise + latency + outage
  windows). The estimator fuses wheel-odometry deltas with those fixes; the
  controller only ever sees estimator output. Truth is recorded for independent
  evaluation only and never feeds control in this mode.
"""
from __future__ import annotations

import math
import random
from xml.etree import ElementTree as ET

SCHEMA = 'urp.field-execution/1'

MU_MIN, MU_MAX = 0.03, 1.0
# Zone thickness above the ground plane: enough for reliable wheel-on-zone contact,
# small enough not to disturb the rigid-plane model (2 mm step at ≤2 m/s).
ZONE_THICKNESS_M = 0.002
PLANE_Z = -0.01                     # matches the base ground plane pose in fieldworld
MAX_FIX_GAP_S = 15.0                # controller stops after this long without a fix
SLIP_GATE_M = 0.6                   # sustained estimator innovation → slip suspicion
SLIP_SUSTAIN_S = 3.0
SLIP_CLEAR_M = 0.3
SLIP_CLEAR_S = 2.0
SLIP_CREEP_SCALE = 0.35
SLIP_CREEP_MAX_S = 30.0
CORRECTION_RAMP_S = 0.4             # spread fix corrections, like a converging filter
# Odometry trust model (declared engineering assumption, uncalibrated): between fixes
# the prediction variance grows with ~2 % of distance travelled PLUS a slip floor of
# 0.08 m/s. The floor matters: unobserved wheelspin can appear at any moment, and
# without it the fix gain collapses and the estimate lags metres behind its own fixes.
ODOM_DRIFT_RATE = 0.02
ODOM_SLIP_FLOOR_MPS = 0.08

GROUND_PRESETS = {
    'none': {'label': '均匀地面（理想参考）', 'zones': []},
    'wet_patch': {'label': '湿滑斑块 μ≈0.22', 'zones': [
        {'mu': 0.22, 'size': [9.0, 7.0], 'at': 0.5, 'label': '湿滑斑块'}]},
    'loose_strip': {'label': '松散带 μ≈0.12 ×2', 'zones': [
        {'mu': 0.12, 'size': [10.0, 6.0], 'at': 0.33, 'label': '松散带 A'},
        {'mu': 0.12, 'size': [10.0, 6.0], 'at': 0.72, 'label': '松散带 B'}]},
    'mud_extreme': {'label': '泥泞极端 μ≈0.05（压力测试）', 'zones': [
        {'mu': 0.05, 'size': [14.0, 10.0], 'at': 0.45, 'label': '泥泞区（应触发保护）'}]},
}
LOCALIZATION_PRESETS = {
    'truth': {'label': '真值定位（理想参考）', 'gnss': None},
    'light': {'label': '轻度误差：2 Hz · σ5 cm · 偏置≈15 cm', 'gnss': {
        'fix_hz': 2.0, 'noise_std_m': 0.05, 'bias_xy_m': [0.12, -0.08], 'walk_m_per_s': 0.0015,
        'latency_s': 0.1, 'outages': []}},
    'drift_outage': {'label': '中度漂移 + 10 s 失锁', 'gnss': {
        'fix_hz': 1.0, 'noise_std_m': 0.10, 'bias_xy_m': [0.25, 0.18], 'walk_m_per_s': 0.004,
        'latency_s': 0.2, 'outages': [{'t_start_s': 60.0, 'duration_s': 10.0}]}},
    'severe': {'label': '严重漂移 + 20 s 失锁（压力测试）', 'gnss': {
        'fix_hz': 1.0, 'noise_std_m': 0.25, 'bias_xy_m': [0.8, -0.6], 'walk_m_per_s': 0.01,
        'latency_s': 0.3, 'outages': [{'t_start_s': 50.0, 'duration_s': 20.0}, {'t_start_s': 130.0, 'duration_s': 8.0}]}},
    'hold': {'label': '轻度误差 + 20 s 失锁（保持路径专测）', 'gnss': {
        'fix_hz': 2.0, 'noise_std_m': 0.05, 'bias_xy_m': [0.1, -0.1], 'walk_m_per_s': 0.001,
        'latency_s': 0.1, 'outages': [{'t_start_s': 60.0, 'duration_s': 20.0}]}},
}
PROVENANCE = {
    'ground': '工程假设：橡胶—湿/松地表摩擦文献范围（约 0.05–0.35）内的低附着代理；摩擦分区非土壤力学，未对本机标定',
    'localization': '工程假设：消费级绝对定位误差量级的合成观测模型（偏置/随机游走/噪声/延迟/失锁）；未标定，不代表任何具体接收机',
    'stress': '压力测试参数：用于触发保护或失败路径，不得解读为可执行性结论',
}


def slip_experiment(execution, physics) -> bool:
    """True when a field session is outside the frozen no-slip reference: declared
    non-ideal execution, or physical parameters deviating from the reference profile
    (friction or wheel contact). Such sessions measure slip instead of gating it."""
    if (execution or {}).get('mode') == 'nonideal':
        return True
    p = physics or {}
    return (p.get('ground_friction', 1.0) != 1.0 or p.get('wheel_friction', 1.0) != 1.0
            or p.get('wheel_contact', 'sphere') != 'sphere')


def _polyline_stats(points):
    total, cum = 0.0, [0.0]
    for a, b in zip(points, points[1:]):
        total += math.dist(a, b)
        cum.append(total)
    return total, cum


def _point_at(points, cum, s):
    if not points:
        return None
    s = max(0.0, min(cum[-1], s))
    for i in range(1, len(points)):
        if cum[i] >= s or i == len(points) - 1:
            seg = cum[i] - cum[i - 1]
            u = 0.0 if seg < 1e-9 else (s - cum[i - 1]) / seg
            a, b = points[i - 1], points[i]
            return (a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u)
    return tuple(points[-1])


def _rects_overlap(a, b, tol=1e-6):
    return not (a[2] <= b[0] + tol or b[2] <= a[0] + tol or a[3] <= b[1] + tol or b[3] <= a[1] + tol)


def _place_zone(spec, routes, bounds, keep_clear):
    """Deterministic placement: centre the rectangle on the arc-length fraction of the
    longest route, nudged along +x until it clears the depot/parking discs."""
    longest = max((r.get('polyline') or [] for r in routes), key=lambda p: sum(
        math.dist(a, b) for a, b in zip(p, p[1:])), default=None)
    if not longest or len(longest) < 2:
        raise ValueError('地面分区需要至少一条含两点的路线几何')
    total, cum = _polyline_stats(longest)
    cx, cy = _point_at(longest, cum, spec['at'] * total)
    w, d = spec['size']
    minx, miny, maxx, maxy = bounds
    for _ in range(24):
        x0, y0, x1, y1 = cx - w / 2, cy - d / 2, cx + w / 2, cy + d / 2
        x0, y0 = max(minx + 0.5, x0), max(miny + 0.5, y0)
        x1, y1 = min(maxx - 0.5, x1), min(maxy - 0.5, y1)
        if x1 - x0 < 0.6 * w or y1 - y0 < 0.6 * d:
            raise ValueError('地面分区在田块边界内放不下，换更小的预设')
        rect = [x0, y0, x1, y1]
        if all(not _rects_overlap(rect, [px - r, py - r, px + r, py + r]) for px, py, r in keep_clear):
            return rect
        cx += 4.0
    raise ValueError('地面分区无法避开车库/停车位，拒绝生成')


def validate_execution(body, inst, routes):
    """Normalize the POSTed execution config; returns None for the ideal reference."""
    if body is None or body == {}:
        return None
    if not isinstance(body, dict):
        raise ValueError('execution 须为 JSON 对象')
    unknown = set(body) - {'ground_preset', 'localization_preset', 'seed', 'slip_protection'}
    if unknown:
        raise ValueError(f'execution 含未知字段：{sorted(unknown)}')
    ground_key = body.get('ground_preset', 'none')
    loc_key = body.get('localization_preset', 'truth')
    if ground_key not in GROUND_PRESETS:
        raise ValueError(f'ground_preset 仅支持 {sorted(GROUND_PRESETS)}')
    if loc_key not in LOCALIZATION_PRESETS:
        raise ValueError(f'localization_preset 仅支持 {sorted(LOCALIZATION_PRESETS)}')
    seed = body.get('seed', 20261018)
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed < 2**31:
        raise ValueError('execution.seed 须为 0–2^31-1 的整数')
    protection = body.get('slip_protection', True)
    if not isinstance(protection, bool):
        raise ValueError('execution.slip_protection 须为布尔值')
    if ground_key == 'none' and loc_key == 'truth':
        return None                       # nothing non-ideal requested

    bounds = tuple(inst['boundary'] and _bounds(inst['boundary']))
    depot = inst['depot']
    keep_clear = [(float(depot[0]), float(depot[1]), 2.5)]
    zones = []
    preset = GROUND_PRESETS[ground_key]
    for spec in preset['zones']:
        mu = spec['mu']
        if not MU_MIN <= mu <= MU_MAX:
            raise ValueError(f'地面分区 μ={mu} 超出支持范围 {MU_MIN}–{MU_MAX}')
        rect = _place_zone(spec, routes, bounds, keep_clear)
        for other in zones:
            if _rects_overlap(rect, other['rect']):
                raise ValueError('地面分区之间不允许重叠')
        zones.append({'label': spec['label'], 'mu': float(mu), 'rect': [round(c, 3) for c in rect],
                      'provenance': PROVENANCE['stress'] if mu <= 0.08 else PROVENANCE['ground']})
    gnss = LOCALIZATION_PRESETS[loc_key]['gnss']
    if gnss is not None:
        for k in ('fix_hz', 'noise_std_m', 'bias_xy_m', 'walk_m_per_s', 'latency_s'):
            if k not in gnss:
                raise ValueError(f'localization 预设缺少 {k}')
    return {
        'schema': SCHEMA,
        'mode': 'nonideal',
        'ground': {'preset': ground_key, 'preset_label': preset['label'],
                   'model': 'coulomb_friction_partition', 'zones': zones,
                   'declared_as': '低附着地面代理（摩擦分区），非土壤力学；μ 未标定',
                   'base_mu_note': '分区以外地面沿用物理配置的均匀摩擦'},
        'localization': {'preset': loc_key, 'preset_label': LOCALIZATION_PRESETS[loc_key]['label'],
                         'gnss': gnss, 'max_fix_gap_s': MAX_FIX_GAP_S,
                         'slip_gate_m': SLIP_GATE_M, 'slip_sustain_s': SLIP_SUSTAIN_S,
                         'slip_clear_m': SLIP_CLEAR_M, 'slip_clear_s': SLIP_CLEAR_S,
                         'slip_creep_scale': SLIP_CREEP_SCALE, 'slip_creep_max_s': SLIP_CREEP_MAX_S,
                         'protection': protection,
                         'declared_as': '合成误差模型绝对位置观测 + 轮式里程计融合估计；未标定',
                         'odom_noise_note': '轮式里程计不加合成噪声：滑移误差已由物理接触产生'},
        'seed': seed,
        'planner_knowledge': '求解与在线控制均不接收地面分区或定位误差参数；真值仅用于独立评价',
        'provenance': {'ground': PROVENANCE['ground'], 'localization': PROVENANCE['localization'],
                       'stress': PROVENANCE['stress']},
    }


def _bounds(boundary):
    xs = [p[0] for p in boundary]
    ys = [p[1] for p in boundary]
    return min(xs), min(ys), max(xs), max(ys)


def zone_sdf(zone, index):
    """One static low-grip box: collision sits just above the plane, visual above the
    field meshes. Both are audited."""
    x0, y0, x1, y1 = zone['rect']
    w, d = x1 - x0, y1 - y0
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    t = ZONE_THICKNESS_M
    return f"""
      <collision name='zone_{index}'><pose>{cx:.3f} {cy:.3f} {PLANE_Z + t / 2:.4f} 0 0 0</pose>
        <geometry><box><size>{w:.3f} {d:.3f} {t}</size></box></geometry>
        <surface><friction><ode><mu>{zone['mu']}</mu><mu2>{zone['mu']}</mu2></ode></friction></surface></collision>
      <visual name='zone_{index}'><pose>{cx:.3f} {cy:.3f} 0.043 0 0 0</pose>
        <geometry><box><size>{w:.3f} {d:.3f} 0.004</size></box></geometry>
        <material><ambient>0.36 0.22 0.08 0.85</ambient><diffuse>0.36 0.22 0.08 0.85</diffuse></material></visual>"""


def audit_ground_zones(sdf_path, execution):
    """Independently re-check the emitted zone boxes against the frozen execution config."""
    errors = []
    zones = (execution or {}).get('ground', {}).get('zones') or []
    root = ET.parse(sdf_path).getroot()
    world = root.find('world')
    model = world.find("model[@name='ground_zones']") if world is not None else None
    if not zones:
        if model is not None:
            errors.append('理想执行不应包含 ground_zones 模型')
        return {'valid': not errors, 'errors': errors, 'zones': 0}
    if model is None:
        return {'valid': False, 'errors': ['执行配置声明了地面分区，但 SDF 缺少 ground_zones 模型'], 'zones': len(zones)}
    link = model.find('link')
    collisions = link.findall('collision') if link is not None else []
    visuals = link.findall('visual') if link is not None else []
    if len(collisions) != len(zones) or len(visuals) != len(zones):
        errors.append('SDF 地面分区数量与执行配置不一致')
    for i, zone in enumerate(zones):
        col = next((c for c in collisions if c.get('name') == f'zone_{i}'), None)
        vis = next((v for v in visuals if v.get('name') == f'zone_{i}'), None)
        if col is None or vis is None:
            errors.append(f'地面分区 {i} 缺少碰撞或可视几何')
            continue
        x0, y0, x1, y1 = zone['rect']
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        want_pose = [cx, cy, PLANE_Z + ZONE_THICKNESS_M / 2]
        want_size = [x1 - x0, y1 - y0, ZONE_THICKNESS_M]
        pose = list(map(float, col.findtext('pose', '').split()[:3]))
        size = list(map(float, col.findtext('geometry/box/size', '').split()))
        if any(abs(a - b) > 2e-3 for a, b in zip(pose, want_pose)) or any(abs(a - b) > 2e-3 for a, b in zip(size, want_size)):
            errors.append(f'地面分区 {i} 位置或尺寸与冻结配置不一致')
        for k in ('mu', 'mu2'):
            if float(col.findtext(f'surface/friction/ode/{k}', 'nan')) != zone['mu']:
                errors.append(f'地面分区 {i} {k} 与冻结配置不一致')
        if model.findtext('static') != 'true':
            errors.append('地面分区模型必须是静态的')
    return {'valid': not errors, 'errors': errors, 'zones': len(zones),
            'scope': '分区盒的位姿/尺寸/摩擦与冻结执行配置核对；不证明摩擦值等于真实土壤'}


class LocalizationModel:
    """Synthetic absolute-position sensor: turns truth into delayed, biased, noisy,
    occasionally-dropped fixes. Deterministic under its seed."""

    def __init__(self, gnss: dict | None, seed: int):
        self.cfg = gnss
        self.rng = random.Random(seed)
        self.next_fix_t = 0.0
        self.bias = [float(gnss['bias_xy_m'][0]), float(gnss['bias_xy_m'][1])] if gnss else [0.0, 0.0]
        self.pending: list[dict] = []      # generated, waiting for availability time
        self.observations: list[list] = []  # [t_measure, t_available, x, y, delivered(0/1), reason]

    def _in_outage(self, t):
        for w in (self.cfg or {}).get('outages') or []:
            if w['t_start_s'] <= t < w['t_start_s'] + w['duration_s']:
                return True
        return False

    def on_truth(self, x, y, t):
        """Called at truth rate; generates fixes at the scheduled fix times."""
        if self.cfg is None:
            return
        hz = float(self.cfg['fix_hz'])
        while self.next_fix_t <= t + 1e-9:
            t_m = self.next_fix_t
            if t_m > 1e-9:                # no fix exactly at t=0
                dt = 1.0 / hz
                std = float(self.cfg['walk_m_per_s'])
                for i in (0, 1):           # random walk on the bias, bounded at 3× initial scale
                    self.bias[i] = max(-0.5, min(0.5, self.bias[i] + self.rng.gauss(0, std * math.sqrt(dt))))
                obs_x = x + self.bias[0] + self.rng.gauss(0, float(self.cfg['noise_std_m']))
                obs_y = y + self.bias[1] + self.rng.gauss(0, float(self.cfg['noise_std_m']))
                drop = self._in_outage(t_m)
                fix = {'t_measure': t_m, 't_available': t_m + float(self.cfg['latency_s']),
                       'x': obs_x, 'y': obs_y, 'dropped': drop, 'reason': 'outage' if drop else None,
                       '_row': len(self.observations)}
                self.observations.append([round(t_m, 4), round(fix['t_available'], 4), round(obs_x, 4),
                                          round(obs_y, 4), 0, fix['reason']])
                if not drop:
                    self.pending.append(fix)
            self.next_fix_t += 1.0 / hz

    def deliver(self, t):
        """Fixes whose availability time has passed; models transport latency."""
        out = [f for f in self.pending if f['t_available'] <= t + 1e-9]
        if out:
            self.pending = [f for f in self.pending if f['t_available'] > t + 1e-9]
            for f in out:
                self.observations[f['_row']][4] = 1
        return out

    def finalize(self, t_end):
        """At session end, still-undelivered fixes are labelled; they are neither
        delivered nor outage drops."""
        for f in self.pending:
            row = self.observations[f['_row']]
            if not row[4]:
                row[5] = 'pending_at_end'
        self.pending = []


class Estimator:
    """Wheel-odometry dead reckoning fused with delayed absolute fixes.

    Prediction composes SE(2) odometry deltas; each fix applies a scalar-gain
    correction whose display is ramped over CORRECTION_RAMP_S so downstream speed
    estimates stay smooth. Innovation (observation minus prediction) is kept for the
    online slip alarm — the controller never sees truth here.
    """

    def __init__(self, start_xy, start_yaw, gnss: dict | None):
        self.x, self.y, self.yaw = float(start_xy[0]), float(start_xy[1]), float(start_yaw)
        self.odom_prev = None
        self.ramp = None                  # (dx, dy, t_fix)
        self.cfg = gnss or {}
        self.pred_var = 0.05 ** 2
        self.last_fix_t = None
        self.innovations: list[tuple[float, float]] = []
        self.last_innovation = None

    def on_odom(self, v, w, t):
        """Body-frame twist integration. The Fortress DiffDrive odometry pose lives in a
        fixed spawn-aligned frame; its *twist* (v, w) is the body-frame velocity, which
        is what a dead-reckoning filter should compose with the map heading. Under slip
        the wheel-derived twist over-reports travel — that error enters here, once."""
        if self.odom_prev is not None and t > self.odom_prev:
            dt = t - self.odom_prev
            c, s = math.cos(self.yaw), math.sin(self.yaw)
            self.x += c * v * dt
            self.y += s * v * dt
            self.yaw = (self.yaw + w * dt + math.pi) % (2 * math.pi) - math.pi
            # Odometry trust model: distance-proportional drift plus a slip floor.
            self.pred_var += (ODOM_DRIFT_RATE * abs(v) * dt) ** 2 + (ODOM_SLIP_FLOOR_MPS * dt) ** 2
        self.odom_prev = t

    def on_fix(self, x_obs, y_obs, t):
        if self.last_fix_t is not None:
            self.pred_var += (float(self.cfg.get('walk_m_per_s', 0.002)) * max(0.0, t - self.last_fix_t)) ** 2
        r = float(self.cfg.get('noise_std_m', 0.1)) ** 2 + 1e-6
        k = self.pred_var / (self.pred_var + r)
        nu_x, nu_y = x_obs - self.x, y_obs - self.y
        self.innovations.append((t, math.hypot(nu_x, nu_y)))
        self.last_innovation = math.hypot(nu_x, nu_y)
        # Fold any unfinished display ramp, then start a new one: display stays continuous.
        dx, dy = self._display_offset(t)
        self.x += k * nu_x
        self.y += k * nu_y
        self.pred_var = (1 - k) * self.pred_var
        self.last_fix_t = t
        self.ramp = [dx - k * nu_x, dy - k * nu_y, t]

    def _display_offset(self, t):
        if self.ramp is None:
            return 0.0, 0.0
        dx, dy, t_fix = self.ramp
        frac = max(0.0, min(1.0, (t - t_fix) / CORRECTION_RAMP_S))
        return dx * (1 - frac), dy * (1 - frac)

    def pose(self, t):
        dx, dy = self._display_offset(t)
        return (self.x + dx, self.y + dy, self.yaw)

    def since_fix(self, t):
        return None if self.last_fix_t is None else t - self.last_fix_t
