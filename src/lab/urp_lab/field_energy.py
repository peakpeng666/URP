"""Post-hoc energy and wheel-torque accounting from the recorded truth trajectory.

This is a kinematic bookkeeping model evaluated on simulator ground truth, not a
battery, motor-current or thermal model inside the loop. Traction work is the
longitudinal inertial force plus a rolling-resistance term; braking is dissipative
and never recuperated. Every number travels with the versioned parameters that
produced it.
"""
from __future__ import annotations

import math

GRAVITY = 9.80665


def account(samples: list, physics: dict) -> dict | None:
    """Energy and peak torque demand of one vehicle from [[t, x, y, ...]] truth samples."""
    import numpy as np
    p = np.asarray(samples, dtype=float)
    if p.ndim != 2 or len(p) < 3 or not np.isfinite(p).all() or (np.diff(p[:, 0]) <= 0).any():
        return None
    model = (physics or {}).get('energy_model') or {}
    crr = float(model.get('rolling_resistance', .06))
    eta = float(model.get('drive_efficiency', .8))
    mass = float((physics or {}).get('total_mass_kg', 25))
    wheel_r = float(((physics or {}).get('wheel') or {}).get('radius_m', .15))
    t, x, y = p[:, 0], p[:, 1], p[:, 2]
    # Central-difference velocity; a short moving average keeps the second derivative usable
    # at 50 Hz without inventing dynamics the controller did not command.
    dt = np.gradient(t)
    v = np.hypot(np.gradient(x) / dt, np.gradient(y) / dt)
    if len(v) > 10:
        kernel = max(3, 2 * round(len(v) * 0.01) | 1)      # ~1% of the run, odd length
        pad = kernel // 2
        padded = np.concatenate((np.full(pad, v[0]), v, np.full(pad, v[-1])))
        v = np.convolve(padded, np.ones(kernel) / kernel, mode='valid')
    a = np.gradient(v) / dt
    moving = v > 1e-3
    force = mass * a + crr * mass * GRAVITY * moving        # rolling resistance only while rolling
    power = np.maximum(force * v, 0.0) / eta                # discharge-only; no recuperation
    energy_j = float(np.trapezoid(power, t)) if hasattr(np, 'trapezoid') else float(np.trapz(power, t))
    peak_force = float(np.max(np.abs(force))) if len(force) else 0.0
    return {'schema': 'urp.field-energy.post_hoc/1',
            'distance_m': float(np.trapezoid(v, t) if hasattr(np, 'trapezoid') else np.trapz(v, t)),
            'moving_s': float(moving.sum() * float(np.median(dt))),
            'energy_j': energy_j, 'energy_wh': energy_j / 3600.0,
            'mean_power_w': energy_j / max(t[-1] - t[0], 1e-9),
            'peak_power_w': float(np.max(power)) if len(power) else 0.0,
            'peak_wheel_torque_nm': peak_force * wheel_r / 2.0,
            'peak_longitudinal_force_n': peak_force,
            'model': {'rolling_resistance': crr, 'drive_efficiency': eta, 'mass_kg': mass,
                      'wheel_radius_m': wheel_r, 'recuperation': False,
                      'derivation': 'central differences on 50 Hz truth poses; velocity smoothed over ~1% of the run',
                      'scope': 'kinematic accounting on simulator truth; not motor current, battery state, thermal or terrain-deformation physics'}}
