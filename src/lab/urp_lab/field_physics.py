"""Versioned SI model for the existing ideal-actuated, rigid-ground field robot.

These parameters define a reproducible simulation model, not a calibrated real
machine. Geometry, inertia, friction, actuator limits and assumptions travel with
every execution record. No system ROS or physics library is replaced.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from xml.etree import ElementTree as ET
from shapely.geometry import MultiPoint

MODEL = 'urp.field-diffdrive.rigid/4'
ENGINE = 'libignition-physics-dartsim-plugin.so'
BODY = (.8, .56, .22)
WHEEL_RADIUS, WHEEL_SEPARATION = .15, .66
# Finite-width rigid ring tyres (v4). The frozen hull is built from the widest supported
# tyre so collision_hull_m covers every allowed width; the projected rectangles plus the
# chassis stay inside the planner's circumscribed circle: hypot(.15, .33 + TYRE_WIDTH_MAX/2) < RADIUS.
TYRE_WIDTH = .10
TYRE_WIDTH_MAX = .16
WHEEL_WIDTH = TYRE_WIDTH
RADIUS = math.hypot(BODY[0] / 2, BODY[1] / 2)
_points = [[x, y] for x in (-BODY[0]/2, BODY[0]/2) for y in (-BODY[1]/2, BODY[1]/2)]
_points += [[x, side * WHEEL_SEPARATION/2 + y]
            for side in (-1, 1) for x in (-WHEEL_RADIUS, WHEEL_RADIUS) for y in (-TYRE_WIDTH_MAX/2, TYRE_WIDTH_MAX/2)]
FOOTPRINT = [list(p) for p in MultiPoint(_points).convex_hull.exterior.coords[:-1]]
LIMITS = {'max_speed_mps': 2.0, 'max_yaw_rate_radps': 2.0,
          'accel_mps2': 1.5, 'decel_mps2': 2.0, 'yaw_accel_radps2': 4.0}
# Post-hoc kinematic energy accounting (no battery/motor/thermal model in the loop).
ENERGY = {'model': 'kinematic_post_hoc/1', 'rolling_resistance': .06, 'drive_efficiency': .8,
          'recuperation': False}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                     ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def box_inertia(mass, size):
    x, y, z = size
    return [mass * (y*y + z*z) / 12, mass * (x*x + z*z) / 12, mass * (x*x + y*y) / 12]


def cylinder_inertia(mass, radius, width):
    cross = mass * (3 * radius**2 + width**2) / 12
    return [cross, cross, mass * radius**2 / 2]


def profile(overrides=None):
    values = {'max_step_size_s': .004, 'collision_detector': 'ode', 'ground_friction': 1.0,
              'wheel_friction': 1.0, 'payload_kg': 0.0, 'wheel_contact': 'tyre', 'tyre_width_m': TYRE_WIDTH}
    if overrides is not None:
        if not isinstance(overrides, dict) or set(overrides) - set(values):
            raise ValueError('physics 仅接受 max_step_size_s、collision_detector、ground_friction、wheel_friction、payload_kg、'
                             'wheel_contact、tyre_width_m；当前 Fortress 不支持显式引擎 seed')
        values.update(overrides)
    if values['collision_detector'] not in ('ode', 'bullet'):
        raise ValueError('physics.collision_detector 仅支持 ode、bullet')
    if values['wheel_contact'] not in ('tyre', 'sphere'):
        raise ValueError('physics.wheel_contact 仅支持 tyre（有限宽圆柱轮胎）、sphere（球面滚动，旧模型）')
    for k, (lo, hi) in {'max_step_size_s': (.0005, .01), 'ground_friction': (.01, 2),
                        'wheel_friction': (.01, 2), 'payload_kg': (0, 50),
                        # wider than the frozen hull is rejected, so collision_hull_m always covers the wheels
                        'tyre_width_m': (.04, TYRE_WIDTH_MAX)}.items():
        v = values[k]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not lo <= v <= hi:
            raise ValueError(f'physics.{k} 必须是 {lo}–{hi} 的有限数值')
        values[k] = float(v)
    if math.hypot(WHEEL_RADIUS, WHEEL_SEPARATION / 2 + values['tyre_width_m'] / 2) > RADIUS + 1e-9:
        raise ValueError('轮胎投影矩形超出规划外接圆：减小 tyre_width_m 或轮距')
    body_mass = 20 + values['payload_kg']
    tyre = values['wheel_contact'] == 'tyre'
    wheel_inertia = cylinder_inertia(2, WHEEL_RADIUS, values['tyre_width_m']) if tyre \
        else [.4 * 2 * WHEEL_RADIUS**2] * 3
    result = {'schema': MODEL, 'engine': ENGINE, **values, 'gravity_mps2': [0, 0, -9.80665],
              'body': {'size_m': list(BODY), 'mass_kg': body_mass, 'inertia_kgm2': box_inertia(body_mass, BODY)},
              'wheel': {'geometry': 'cylinder' if tyre else 'sphere', 'radius_m': WHEEL_RADIUS, 'width_m': values['tyre_width_m'],
                        'separation_m': WHEEL_SEPARATION, 'mass_kg': 2, 'inertia_kgm2': wheel_inertia},
              'caster': {'radius_m': .06, 'mass_kg': .5, 'friction': .01,
                         'inertia_kgm2': [.4 * .5 * .06**2] * 3},
              'total_mass_kg': body_mass + 5, 'collision_hull_m': copy.deepcopy(FOOTPRINT),
              'collision_radius_m': RADIUS, 'limits': dict(LIMITS), 'truth_hz': 50,
              'energy_model': dict(ENERGY),
              'assumptions': {'ground': 'flat rigid plane; Coulomb friction; no deformable soil or terrain',
                              'wheel_contact': ('rigid ring cylindrical tyres with finite contact width; no carcass flexibility, lugs or pressure effects; '
                                                'in-place rotation involves tyre scrub slip and is measured against a widened bound, not ideal rolling'
                                                if tyre else 'spherical rolling contacts as in the official differential-drive example (legacy v3 model)'),
                              'actuator': 'ideal wheel velocity servo with body speed/acceleration limits; no motor torque saturation in the loop; '
                                          'wheel torque demand is post-hoc accounting, not an enforced motor limit',
                              'energy': 'post-hoc kinematic accounting from the truth trajectory: rolling resistance, longitudinal inertia and drive '
                                        'efficiency; no battery, motor current, thermal or terrain deformation model; braking recuperation not counted',
                              'payload': 'constant mass uniformly distributed in the chassis box; task demand is abstract capacity, not kg',
                              'localization': 'exact simulator world pose with source simulation timestamp; no sensor noise or estimator',
                              'randomness': 'Fortress 6.18 CLI/control has no supported seed setter; no stochastic sensors configured; bitwise determinism is not claimed',
                              'calibration': 'synthetic parameters; no real-machine calibration; simulation verification only'}}
    result['sha256'] = digest(result)
    return result


def rest_to_rest(distance, speed, accel, decel):
    """Exact 1-D minimum time for zero endpoint speeds and bounded a/v."""
    if distance <= 0:
        return 0.0
    peak = min(speed, math.sqrt(2 * distance / (1 / accel + 1 / decel)))
    ramp_distance = peak**2 / (2 * accel) + peak**2 / (2 * decel)
    return peak / accel + peak / decel + max(0, distance - ramp_distance) / peak


def timing_reference(path, speed, service_s=0.0, limits=None):
    """Explicit stop/turn/go reference; NOT a prediction or bound on the feedback controller."""
    limits = limits or LIMITS
    points = [path[0]]
    for p in path[1:]:
        if math.dist(p, points[-1]) > 1e-9:
            points.append(p)
    lengths = [math.dist(a, b) for a, b in zip(points, points[1:])]
    angles = [math.atan2(b[1]-a[1], b[0]-a[0]) for a, b in zip(points, points[1:])]
    turns = [abs((b-a+math.pi) % (2*math.pi)-math.pi) for a, b in zip(angles, angles[1:])]
    linear = sum(rest_to_rest(d, speed, limits['accel_mps2'], limits['decel_mps2']) for d in lengths)
    angular = sum(rest_to_rest(t, limits['max_yaw_rate_radps'], limits['yaw_accel_radps2'],
                               limits['yaw_accel_radps2']) for t in turns)
    return {'model': 'stop_turn_go_reference/1', 'distance_m': sum(lengths), 'translation_s': linear,
            'rotation_s': angular, 'service_s': service_s, 'duration_s': linear + angular + service_s,
            'constant_speed_service_s': sum(lengths) / speed + service_s,
            'scope': 'zero speed at every polyline vertex, in-place turn then accelerate; no queue; not a controller-time prediction or bound'}


def audit_sdf(path, expected):
    """Inspect the emitted SDF independently before launching any physics process."""
    root = ET.parse(path).getroot()
    errors, bodies = [], []
    world = root.find('world')
    if digest({k:v for k,v in expected.items() if k != 'sha256'}) != expected['sha256']:
        errors.append('冻结物理模型内容与 SHA256 不一致')
    if list(map(float, world.findtext('gravity').split())) != expected['gravity_mps2']:
        errors.append('SDF 重力与冻结配置不一致')
    if float(world.findtext('physics/max_step_size')) != expected['max_step_size_s']:
        errors.append('SDF 物理步长与冻结配置不一致')
    if world.findtext('physics/dart/collision_detector') != expected['collision_detector']:
        errors.append('SDF 碰撞检测器与冻结配置不一致')
    if world.findtext('physics/dart/solver/solver_type') != 'dantzig':
        errors.append('SDF 约束求解器不是声明的 dantzig')
    ground = world.find("model[@name='ground']/link/collision/surface/friction/ode")
    if ground is None or any(float(ground.findtext(k, 'nan')) != expected['ground_friction'] for k in ('mu','mu2')):
        errors.append('SDF 地面摩擦与冻结配置不一致')
    engines = world.findall("plugin[@name='gz::sim::systems::Physics']/engine/filename")
    if len(engines) != 1 or engines[0].text != expected['engine']:
        errors.append('SDF 未明确选择预期物理引擎')
    for model in world.findall('model'):
        if not model.get('name', '').startswith('vehicle_'):
            continue
        links = model.findall('link')
        if {l.get('name') for l in links} != {'chassis','left_wheel','right_wheel','rear_caster','front_caster'}:
            errors.append('SDF 车辆 link 集合与声明模型不一致')
        drive = model.find("plugin[@name='gz::sim::systems::DiffDrive']")
        wanted_drive = {'wheel_radius':expected['wheel']['radius_m'], 'wheel_separation':expected['wheel']['separation_m'],
            'max_linear_velocity':expected['limits']['max_speed_mps'],
            'max_angular_velocity':expected['limits']['max_yaw_rate_radps'],
            'max_linear_acceleration':expected['limits']['accel_mps2'],
            'min_linear_acceleration':-expected['limits']['decel_mps2'],
            'max_angular_acceleration':expected['limits']['yaw_accel_radps2']}
        if drive is None or any(float(drive.findtext(k,'nan')) != val for k,val in wanted_drive.items()):
            errors.append('SDF 驱动参数与冻结配置不一致')
        mass = 0.0
        for link in links:
            part = 'wheel' if link.get('name').endswith('wheel') else 'caster' if link.get('name').endswith('caster') else 'body'
            m = float(link.findtext('inertial/mass', 'nan'))
            diag = [float(link.findtext('inertial/inertia/'+k, 'nan')) for k in ('ixx', 'iyy', 'izz')]
            if (not all(math.isfinite(x) and x > 0 for x in [m, *diag])
                    or 2 * max(diag) > sum(diag) + 1e-9):
                errors.append(f"{model.get('name')}/{link.get('name')} 惯量非物理可实现")
            shape = link.find('collision/geometry')
            if shape.find('box') is not None:
                wanted = box_inertia(m, list(map(float, shape.findtext('box/size').split())))
            elif shape.find('cylinder') is not None:
                wanted = cylinder_inertia(m, float(shape.findtext('cylinder/radius')), float(shape.findtext('cylinder/length')))
            else:
                wanted = [.4 * m * float(shape.findtext('sphere/radius'))**2] * 3
            if any(abs(a-b) > 1e-8 for a, b in zip(diag, wanted)):
                errors.append(f"{model.get('name')}/{link.get('name')} 质量/碰撞几何与均匀实体惯量不一致")
            if m != expected[part]['mass_kg'] or any(abs(a-b)>1e-8 for a,b in zip(diag, expected[part]['inertia_kgm2'])):
                errors.append(f"{model.get('name')}/{link.get('name')} 质量/惯量与冻结配置不一致")
            if any(float(link.findtext('inertial/inertia/'+k,'nan')) != 0 for k in ('ixy','ixz','iyz')):
                errors.append('声明的主惯量坐标系出现非零非对角项')
            if part != 'body':
                friction = expected['wheel_friction'] if part == 'wheel' else expected['caster']['friction']
                if any(float(link.findtext('collision/surface/friction/ode/'+k,'nan')) != friction for k in ('mu','mu2')):
                    errors.append(f'{part} 摩擦与冻结配置不一致')
            mass += m
        if abs(mass - expected['total_mass_kg']) > 1e-8:
            errors.append('SDF 总质量与冻结配置不一致')
        bodies.append({'vehicle': model.get('name'), 'mass_kg': mass})
    if not bodies:
        errors.append('SDF 未包含执行车辆')
    return {'valid': not errors, 'errors': errors, 'bodies': bodies, 'model_sha256': expected['sha256'],
            'scope': 'rigid body geometry/inertia and explicit engine configuration; not empirical physical calibration'}
