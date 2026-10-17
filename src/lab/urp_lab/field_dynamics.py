"""Independent observations of rigid pose and wheel-odometry consistency.

Wheel odometry is integrated wheel kinematics, not an estimated localization
system. Its error versus truth exposes slip; it is not hidden by aligning the
entire trajectory. Only the first common pose is used for SE(2) alignment.
"""
from __future__ import annotations
import math
import numpy as np


def verify(result):
    errors, rows = [], []
    timing = result.get('truth_timing') or {}
    if timing.get('latest_clock_samples') != 0 or timing.get('tf_header_samples', 0) <= 0:
        errors.append('物理模型验收要求源仿真时间，不接受接收时间近似')
    if not result.get('vehicles'):
        errors.append('缺少待验收车辆，不能返回空集合成功')
    for v in result.get('vehicles', []):
        name = v['name']
        try:
            p = np.asarray(result.get('rigid_body_poses', {}).get(name, []), dtype=float)
            o = np.asarray(result.get('wheel_odometry', {}).get(name, []), dtype=float)
        except (ValueError, TypeError):
            errors.append(f'{name} 刚体真值或轮式里程计格式无效')
            continue
        valid = (p.ndim == o.ndim == 2 and p.shape[1:] == (7,) and o.shape[1:] == (6,)
                 and len(p) >= 2 and len(o) >= 2 and np.isfinite(p).all() and np.isfinite(o).all()
                 and (np.diff(p[:,0]) > 0).all() and (np.diff(o[:,0]) > 0).all())
        if not valid:
            errors.append(f'{name} 刚体真值或轮式里程计数据缺失/时间无效')
            continue
        # A sample gap only invalidates interpolation when motion could have happened across
        # it; gaps spanned without displacement or rotation (parked/waiting vehicles, skipped
        # identical poses) are exact to interpolate and do not hide anything.
        def moving_gaps(rows, yaw_col):
            gaps = np.diff(rows[:, 0])
            idx = np.where(gaps > .25)[0]
            return [i for i in idx
                    if math.hypot(rows[i + 1, 1] - rows[i, 1], rows[i + 1, 2] - rows[i, 2]) > .05
                    or abs((rows[i + 1, yaw_col] - rows[i, yaw_col] + math.pi) % (2 * math.pi) - math.pi) > .05]
        bad_truth, bad_odom = moving_gaps(p, 6), moving_gaps(o, 3)
        if bad_truth or bad_odom:
            errors.append(f'{name} 真值或里程计在运动中出现超过 0.25 s 的采样间断（静止期缺口不计），不能依靠跨缺口插值验收')
        if 'trails' in result:
            trail = np.asarray(result['trails'].get(name, []), dtype=float)
            if trail.shape != (len(p),4) or not np.allclose(trail, p[:,[0,1,2,6]], atol=1e-9, rtol=0):
                errors.append(f'{name} 二维轨迹与保存的刚体真值不一致')
        roll, pitch, z = np.max(np.abs(p[:,4])), np.max(np.abs(p[:,5])), np.max(np.abs(p[:,3]))
        if max(roll, pitch) > .35 or z > .5:
            errors.append(f'{name} 在平坦地面出现超出模型有效域的倾斜或高度')
        times = o[(o[:,0] >= p[0,0]) & (o[:,0] <= p[-1,0]), 0]
        if len(times) < 2:
            errors.append(f'{name} 真值与轮式里程计没有足够共同时间')
            continue
        truth = np.stack([np.interp(times, p[:,0], p[:,c]) for c in (1,2)], axis=1)
        truth_yaw = np.interp(times, p[:,0], np.unwrap(p[:,6]))
        odom = np.stack([np.interp(times, o[:,0], o[:,c]) for c in (1,2)], axis=1)
        odom_yaw = np.interp(times, o[:,0], np.unwrap(o[:,3]))
        angle = truth_yaw[0]-odom_yaw[0]
        rotation = np.array([[math.cos(angle), -math.sin(angle)], [math.sin(angle), math.cos(angle)]])
        aligned = (odom-odom[0]) @ rotation.T + truth[0]
        distance = np.linalg.norm(aligned-truth, axis=1)
        yaw_error = (odom_yaw+angle-truth_yaw+math.pi) % (2*math.pi)-math.pi
        rows.append({'vehicle':name, 'truth_samples':len(p), 'odom_samples':len(o), 'paired_samples':len(times),
                     'max_roll_rad':float(roll), 'max_pitch_rad':float(pitch), 'max_abs_z_m':float(z),
                     'odom_position_rmse_m':float(np.sqrt(np.mean(distance**2))),
                     'odom_position_final_m':float(distance[-1]), 'odom_position_max_m':float(distance.max()),
                     'odom_yaw_rmse_rad':float(np.sqrt(np.mean(yaw_error**2))),
                     'max_truth_gap_s':float(np.max(np.diff(p[:,0])))})
    return {'valid':not errors, 'errors':errors, 'vehicles':rows,
            'scope':'flat-world attitude/data checks; wheel odometry aligned only at first common timestamp; drift reported, not calibrated or suppressed',
            'thresholds':{'tilt_rad':.35, 'absolute_model_origin_z_m':.5, 'max_moving_sample_gap_s':.25,
                          'stationary_gap_displacement_m':.05, 'stationary_gap_rotation_rad':.05}}
