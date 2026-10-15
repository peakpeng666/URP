#!/usr/bin/python3
"""Bounded reproduction of parameter_bridge exit aborts (-6). Isolated ROS domain + IGN partition."""
import argparse, json, os, signal, subprocess, sys, time
from pathlib import Path
p = argparse.ArgumentParser()
p.add_argument('--cycles', type=int, default=10)
p.add_argument('--bridges', type=int, default=20)
p.add_argument('--world', default='/home/peakpeng/Desktop/URP/setup/2026-10-15/minimal-world.sdf')
p.add_argument('--world-name', default='urp_setup_smoke')
p.add_argument('--preload', default='')
p.add_argument('--label', required=True)
p.add_argument('--settle', type=float, default=3.0)
a = p.parse_args()
here = Path(__file__).resolve().parent
logs = here / 'logs' / a.label; logs.mkdir(parents=True, exist_ok=False)
env = os.environ.copy()
env.update(ROS_DOMAIN_ID='177', ROS_LOCALHOST_ONLY='1', IGN_PARTITION=f'urp_bridge_repro_{os.getpid()}',
           ROS_LOG_DIR=str(logs / 'ros-log'), IGN_HOMEDIR=str(logs / 'ign'))
(logs / 'ign').mkdir()
server = subprocess.Popen(['ign', 'gazebo', '-s', '-r', '-v', '1', a.world], env=env, start_new_session=True,
                          stdout=open(logs / 'server.log', 'w'), stderr=subprocess.STDOUT)
time.sleep(4)
topics = [f'/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock',
          f'/world/{a.world_name}/stats@ros_gz_interfaces/msg/WorldStatistics[ignition.msgs.WorldStatistics',
          f'/world/{a.world_name}/pose/info@tf2_msgs/msg/TFMessage[ignition.msgs.Pose_V',
          f'/urp_repro_cmd@geometry_msgs/msg/Twist]ignition.msgs.Twist']
results = []
bridge_env = dict(env)
if a.preload:
    bridge_env['LD_PRELOAD'] = a.preload
try:
    for c in range(a.cycles):
        procs = []
        for i in range(a.bridges):
            t = topics[i % len(topics)]
            log = open(logs / f'c{c:02d}-b{i:02d}.log', 'w')
            procs.append(subprocess.Popen(['/opt/ros/humble/lib/ros_gz_bridge/parameter_bridge', t, '--ros-args', '-r', f'__node:=repro_{c}_{i}'],
                                          env=bridge_env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True))
        time.sleep(a.settle)
        for pr in procs:
            try: pr.send_signal(signal.SIGINT)
            except ProcessLookupError: pass
        codes = []
        for pr in procs:
            try: codes.append(pr.wait(timeout=15))
            except subprocess.TimeoutExpired:
                os.killpg(pr.pid, signal.SIGKILL); codes.append('killed:' + str(pr.wait()))
        bad = [x for x in codes if x not in (0, -2, 130)]
        results.append({'cycle': c, 'codes': codes, 'abnormal': bad})
        print(c, 'abnormal', bad, flush=True)
finally:
    os.killpg(server.pid, signal.SIGINT)
    try: server.wait(timeout=15)
    except subprocess.TimeoutExpired: os.killpg(server.pid, signal.SIGKILL); server.wait()
total = sum(len(r['codes']) for r in results); bad = sum(len(r['abnormal']) for r in results)
summary = {'label': a.label, 'preload': a.preload, 'exits': total, 'abnormal': bad, 'settle_s': a.settle, 'results': results}
(logs / 'summary.json').write_text(json.dumps(summary, indent=1))
print(json.dumps({k: summary[k] for k in ('label', 'preload', 'exits', 'abnormal')}))
