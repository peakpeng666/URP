#!/usr/bin/python3
"""Open-loop verification maneuvers using the same world, bridge and cleanup as field execution.

No mission success is inferred. Raw source-stamped poses, odometry and command
times are saved for a separate analysis in the solver environment.
"""
import argparse
import json
import signal
import time
import traceback
from pathlib import Path
from types import SimpleNamespace

from field_sim_session import Session, Twist, save
from physical_session_lock import exclusive_physics


@exclusive_physics
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--runtime', required=True)
    args = parser.parse_args()
    session = Session(SimpleNamespace(runtime=args.runtime, web=False, gui=False, rviz=False))
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: session.stop.set())
    commands, stages = [], []
    protocols = {'primary': [('settle', 0., 0., 2.), ('straight', .8, 0., 6.), ('brake', 0., 0., 2.),
                ('rotate', 0., .8, 3.), ('rotate_stop', 0., 0., 2.),
                ('arc', .6, .35, 6.), ('arc_stop', 0., 0., 3.)],
                 'holdout': [('settle', 0., 0., 2.), ('straight', 1.4, 0., 5.), ('brake', 0., 0., 2.),
                ('rotate', 0., -1.1, 3.), ('rotate_stop', 0., 0., 2.),
                ('arc', .9, -.5, 5.), ('arc_stop', 0., 0., 3.)]}
    protocol_id = session.plan.get('probe_protocol', 'primary')
    protocol = protocols[protocol_id]
    outcome = 'failed'
    try:
        session.startup()
        session.phase('running')
        wall_deadline = time.monotonic() + 90
        for name, v, w, duration in protocol:
            begin = session.clock
            last = -1.
            while session.clock - begin < duration:
                session.spin(.002)
                if time.monotonic() > wall_deadline:
                    raise TimeoutError('physics response wall deadline')
                t = session.clock
                if t-last >= .02:
                    msg = Twist()
                    msg.linear.x, msg.angular.z = v, w
                    session.cmd['vehicle_1'].publish(msg)
                    commands.append([t, v, w])
                    last = t
            stages.append({'name': name, 'begin_s':begin, 'end_s':session.clock, 'v_mps':v, 'w_radps':w})
        outcome = 'succeeded'
    except BaseException as exc:
        session.report['errors'].append(f'{type(exc).__name__}: {exc}')
        traceback.print_exc()
    finally:
        session.result = {'state':outcome, 'protocol':'rigid-response/1'}
        session.phase('finished' if outcome == 'succeeded' else 'failed')
        data = {'schema':'urp.rigid-response/1', 'protocol':protocol_id, 'state':outcome, 'physics':session.plan['physics'],
                'physics_audit':session.plan['physics_audit'], 'stages':stages, 'commands':commands,
                'physics_runtime':session.report.get('physics_runtime'),
                'rigid_body_poses':session.rigid_poses, 'wheel_odometry':session.odometry,
                'ground_contacts':session.ground_contact_samples,
                'truth_timing':session.truth_timing, 'contacts':session.contacts,
                'telemetry':session.counts, 'errors':session.report['errors'],
                **({'torque_traces': session.torque_traces,
                    'torque_trace_columns': ['t_sim', 'omega_left_target_radps', 'omega_right_target_radps',
                                             'omega_left_meas_radps', 'omega_right_meas_radps'],
                    'actuator_note': '轮速目标与关节实测轮速；力矩由引擎内 PID 产生并受 SDF effort 限幅（指令力矩不可观测，饱和由运动响应判定）'}
                   if getattr(session, 'torque_mode', False) else {})}
        save(Path(args.runtime)/'response.json', data)
        rc = session.shutdown()
    return rc


if __name__ == '__main__':
    raise SystemExit(main())
