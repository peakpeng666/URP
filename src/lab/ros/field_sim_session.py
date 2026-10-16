#!/usr/bin/python3
"""Multi-vehicle field task in Gazebo Fortress, driven over ROS 2 (system Python 3.10).

Gazebo runs the field world generated from the task map; one ros_gz parameter_bridge carries the
clock, ground-truth poses and every vehicle's cmd_vel / odometry. Each vehicle follows its planned
VRP route with a pure-pursuit controller that stops at each of its tasks (dwelling for the task's
service time) and records arrivals, so the executed schedule can be compared with the plan.
Foxglove Bridge and the Gazebo WebSocket server feed the workbench's live 3D views; RViz2 and the
Gazebo GUI can be opened as separate windows.
"""
from __future__ import annotations

import argparse
import bisect
import copy
from datetime import datetime, timezone
import importlib.util
import json
import math
import os
from pathlib import Path
import secrets
import signal
import subprocess
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LAB = Path(__file__).resolve().parents[1]
ROOT = LAB.parents[1]
DEPLOY = ROOT / 'setup/2026-10-15/deployment'
EXTRAS = DEPLOY / 'runtime/ros-extras/root/opt/ros/humble'
sys.path[:0] = [str(DEPLOY), str(LAB / 'ros')]
from bridge_guard import verified_bridge_guard  # noqa: E402

import rclpy  # noqa: E402
from rclpy.parameter import Parameter  # noqa: E402
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy, qos_profile_sensor_data  # noqa: E402
from rclpy.signals import SignalHandlerOptions  # noqa: E402
from geometry_msgs.msg import Point, Twist, TransformStamped  # noqa: E402
from rosgraph_msgs.msg import Clock  # noqa: E402
from std_msgs.msg import ColorRGBA, String  # noqa: E402
from tf2_msgs.msg import TFMessage  # noqa: E402
from tf2_ros import TransformBroadcaster  # noqa: E402
from visualization_msgs.msg import Marker, MarkerArray  # noqa: E402

spec = importlib.util.spec_from_file_location('nav_smoke_processes', DEPLOY / 'nav-smoke.py')
original = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original)

OPTIONAL = ('gui', 'rviz', 'foxglove', 'gazebo_web')
TASK_RADIUS = 0.45          # m: a task counts as reached inside this radius
LOOKAHEAD = 1.4             # m
FINAL = ('finished', 'failed', 'stopped')


def now():
    return datetime.now(timezone.utc).isoformat()


def yaw_of(q):
    return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))


def wrap(a):
    return (a + math.pi) % (2 * math.pi) - math.pi


def save(path: Path, obj):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False))
    tmp.replace(path)


def rgba(hexcolor, a=1.0):
    h = hexcolor.lstrip('#')
    return ColorRGBA(r=int(h[0:2], 16) / 255, g=int(h[2:4], 16) / 255, b=int(h[4:6], 16) / 255, a=a)


class Processes(original.OwnedProcesses):
    def __init__(self, env, runtime):
        super().__init__(env, 'fieldsim')
        self.runtime = runtime

    def start(self, name, command, extra_env=None):
        count = sum(n == name for n, _, _, _ in self.children)
        path = self.runtime / 'logs' / f'{name}{"-" + str(count) if count else ""}.log'
        with path.open('x') as stream:
            p = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT, env={**self.env, **(extra_env or {})},
                                 start_new_session=True)
        self.children.append((name, p, path, command))
        return path


class Driver:
    """Pure pursuit along one vehicle's planned path, stopping at each of its tasks."""

    def __init__(self, v: dict, speed: float):
        self.name, self.label, self.color = v['name'], v['label'], v['color']
        self.path = [tuple(p) for p in v['path']]
        self.cum = [0.0]
        for a, b in zip(self.path, self.path[1:]):
            self.cum.append(self.cum[-1] + math.dist(a, b))
        self.length = self.cum[-1]
        self.speed = speed
        self.tasks = [dict(t, state='pending', t_sim=None, distance_m=None) for t in v['tasks']]
        # arc length of each task along the path, in visiting order
        s_prev, idx = 0.0, 0
        for t in self.tasks:
            best = None
            for i in range(idx, len(self.path)):
                d = math.dist(self.path[i], t['xy'])
                if d < 0.05:
                    best = i
                    break
            if best is None:  # not a vertex: take the closest projection after the previous task
                best = min(range(idx, len(self.path)), key=lambda i: math.dist(self.path[i], t['xy']))
            t['s'] = max(s_prev, self.cum[best])
            s_prev, idx = t['s'], best
        self.s = 0.0
        self.state = 'waiting'
        self.pose = None
        self.dwell_until = None
        self.trail: list[list[float]] = []
        self.distance = 0.0
        self.cte: list[float] = []
        self.t_start = self.t_done = None
        self.v_cmd = self.w_cmd = 0.0
        self.speed_now = 0.0
        self.last_progress = (0.0, None)

    def point_at(self, s):
        s = max(0.0, min(self.length, s))
        i = max(1, min(len(self.cum) - 1, bisect.bisect_left(self.cum, s)))
        a, b = self.path[i - 1], self.path[i]
        seg = self.cum[i] - self.cum[i - 1]
        u = 0.0 if seg < 1e-9 else (s - self.cum[i - 1]) / seg
        return a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u

    def project(self, p):
        """Arc length and distance of the closest path point within a window ahead of the progress."""
        best = (self.s, math.inf)
        lo = max(0, bisect.bisect_left(self.cum, self.s - 2) - 1)
        hi = min(len(self.path) - 1, bisect.bisect_right(self.cum, self.s + LOOKAHEAD + 6) + 1)
        for i in range(max(1, lo), hi + 1):
            a, b = self.path[i - 1], self.path[i]
            dx, dy = b[0] - a[0], b[1] - a[1]
            den = dx * dx + dy * dy
            u = 0.0 if den < 1e-12 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / den))
            d = math.hypot(p[0] - a[0] - u * dx, p[1] - a[1] - u * dy)
            if d < best[1]:
                best = (self.cum[i - 1] + u * math.sqrt(den), d)
        return best

    def next_task(self):
        return next((t for t in self.tasks if t['state'] == 'pending'), None)

    def step(self, t_sim: float):
        """Returns (v, w) for this control tick."""
        if self.pose is None or self.state in ('done', 'failed', 'waiting'):
            return 0.0, 0.0
        x, y, yaw = self.pose
        if self.t_start is None:
            self.t_start = t_sim
        s_proj, cte = self.project((x, y))
        self.s = max(self.s, min(s_proj, self.s + LOOKAHEAD))
        self.cte.append(cte)
        task = self.next_task()
        if task and math.dist((x, y), task['xy']) <= TASK_RADIUS:
            task.update(state='reached', t_sim=t_sim, distance_m=math.dist((x, y), task['xy']))
            self.s = max(self.s, task['s'])
            if task.get('service_s', 0) > 0:
                self.state, self.dwell_until = 'servicing', t_sim + task['service_s']
            task = self.next_task()
        if self.state == 'servicing':
            if t_sim < (self.dwell_until or 0):
                return 0.0, 0.0
            self.state = 'driving'
        stop_s = min(task['s'], self.length) if task else self.length
        if not task and self.length - self.s < 0.35 and math.dist((x, y), self.path[-1]) < 0.6:
            self.state, self.t_done = 'done', t_sim
            return 0.0, 0.0
        target_s = min(self.s + LOOKAHEAD, stop_s)
        tx, ty = self.point_at(target_s)
        if math.dist((x, y), (tx, ty)) < 0.05:  # sitting on a stop point but outside the radius
            tx, ty = task['xy'] if task else self.path[-1]
        alpha = wrap(math.atan2(ty - y, tx - x) - yaw)
        to_stop = max(0.0, stop_s - self.s) + math.dist((x, y), self.point_at(self.s))
        if abs(alpha) > 0.9:
            return 0.0, max(-1.6, min(1.6, 2.2 * alpha))
        v = self.speed * max(0.3, math.cos(alpha))
        v = min(v, 0.15 + 0.7 * to_stop)
        look = max(0.4, math.dist((x, y), (tx, ty)))
        w = max(-1.8, min(1.8, 2 * v * math.sin(alpha) / look + 0.8 * alpha * (v < 0.3)))
        # stuck watchdog
        if self.last_progress[1] is None or self.s > self.last_progress[0] + 0.2:
            self.last_progress = (self.s, t_sim)
        elif t_sim - self.last_progress[1] > 60:
            self.state = 'failed'
            return 0.0, 0.0
        return v, w

    def summary(self, plan_v: dict | None):
        reached = [t for t in self.tasks if t['state'] == 'reached']
        return {
            'name': self.name, 'label': self.label, 'color': self.color, 'state': self.state,
            'pose': [round(c, 3) for c in self.pose] if self.pose else None, 'speed': round(self.speed_now, 3),
            'progress': round(self.s / self.length, 4) if self.length else 1.0,
            'distance_m': round(self.distance, 2), 'path_length_m': round(self.length, 2),
            'tasks_done': len(reached), 'tasks_total': len(self.tasks),
            'cross_track_mean_m': round(sum(self.cte) / len(self.cte), 4) if self.cte else None,
            'cross_track_max_m': round(max(self.cte), 4) if self.cte else None,
            'duration_s': round(self.t_done - self.t_start, 2) if self.t_done is not None and self.t_start is not None else None,
            'planned_length_m': (plan_v or {}).get('planned_length_m'),
            'planned_duration_s': (plan_v or {}).get('planned_duration_s'),
        }


class Session:
    def __init__(self, args):
        self.args = args
        self.runtime = Path(args.runtime)
        (self.runtime / 'logs').mkdir(parents=True, exist_ok=True)
        self.plan = json.loads((self.runtime / 'plan.json').read_text())
        self.world = self.plan['world']
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.commands = []
        self.started = time.monotonic()
        self.st = dict(session_id=self.plan['session_id'], run_id=self.plan['run_id'], scenario_id=self.plan['scenario_id'],
                       algorithm=self.plan.get('algorithm'), world=self.world, phase='starting', components={}, web={},
                       errors=[], warnings=[], stages=[], sim_time=0.0, real_time_factor=None, vehicles=[], metrics={},
                       result=None)
        self.env = dict(os.environ, ROS_HOME=str(self.runtime / 'ros'), ROS_LOG_DIR=str(self.runtime / 'ros-log'),
                        IGN_PARTITION='field_' + self.plan['session_id'], IGN_HOMEDIR=str(self.runtime / 'ignition'))
        Path(self.env['IGN_HOMEDIR']).mkdir(exist_ok=True)
        os.environ.update({k: self.env[k] for k in ('ROS_HOME', 'ROS_LOG_DIR')})
        self.processes = Processes(self.env, self.runtime)
        self.bridge_fix = verified_bridge_guard() if os.environ.get('URP_BRIDGE_FIX', '1') == '1' else None
        self.report = dict(session_id=self.plan['session_id'], started_utc=now(), world=self.world, errors=[])
        self.drivers = [Driver(v, float(self.plan['speed_mps'])) for v in self.plan['vehicles']]
        self.plan_by_name = {v['name']: v for v in self.plan['vehicles']}
        self.clock = None
        self.clock_wall = None
        rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
        self.node = rclpy.create_node('field_fleet_session', parameter_overrides=[Parameter('use_sim_time', value=True)])
        latched = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        self.node.create_subscription(Clock, '/clock', self.on_clock, qos_profile_sensor_data)
        self.node.create_subscription(TFMessage, '/ground_truth/poses', self.on_truth, qos_profile_sensor_data)
        self.cmd = {d.name: self.node.create_publisher(Twist, f'/{d.name}/cmd_vel', 10) for d in self.drivers}
        self.pub_field = self.node.create_publisher(MarkerArray, '/workbench/field', latched)
        self.pub_routes = self.node.create_publisher(MarkerArray, '/workbench/routes', latched)
        self.pub_tasks = self.node.create_publisher(MarkerArray, '/workbench/tasks', latched)
        self.pub_trails = self.node.create_publisher(MarkerArray, '/workbench/trails', 10)
        self.pub_vehicles = self.node.create_publisher(MarkerArray, '/workbench/vehicles', 10)
        self.pub_status = self.node.create_publisher(String, '/workbench/fleet_status', 10)
        self.tf = TransformBroadcaster(self.node)
        self.task_version = 0
        self.published_tasks = -1

    # ------------------------------------------------------------ inputs --
    def on_clock(self, msg):
        self.clock = msg.clock.sec + msg.clock.nanosec / 1e9
        wall = time.monotonic()
        if self.clock_wall:
            (c0, w0) = self.clock_wall
            if wall - w0 >= 2.0:
                self.st['real_time_factor'] = round((self.clock - c0) / (wall - w0), 2)
                self.clock_wall = (self.clock, wall)
        else:
            self.clock_wall = (self.clock, wall)
        self.st['sim_time'] = round(self.clock, 2)

    def on_truth(self, msg):
        names = {d.name: d for d in self.drivers}
        out = []
        for t in msg.transforms:
            d = names.get(t.child_frame_id)
            if not d:
                continue
            p = t.transform.translation
            pose = (p.x, p.y, yaw_of(t.transform.rotation))
            if d.pose is not None:
                step = math.dist(d.pose[:2], pose[:2])
                if step < 2.0 and d.state not in ('waiting',):
                    d.distance += step
            d.pose = pose
            tf = TransformStamped()
            tf.header.stamp = t.header.stamp
            tf.header.frame_id = 'map'
            tf.child_frame_id = f'{d.name}/base_link'
            tf.transform = t.transform
            out.append(tf)
        if out:
            self.tf.sendTransform(out)

    # ------------------------------------------------------------ phases --
    def phase(self, name):
        self.st['phase'] = name
        self.st['stages'].append(dict(name=name, wall_s=round(time.monotonic() - self.started, 3)))
        print(name, flush=True)

    def spin(self, seconds=0.02):
        rclpy.spin_once(self.node, timeout_sec=seconds)
        if self.stop.is_set():
            raise KeyboardInterrupt
        for name, proc, _, _ in self.processes.children:
            ended = os.waitid(os.P_PID, proc.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
            if ended:
                if name in OPTIONAL:
                    if self.st['components'].get(name) == 'running':
                        self.st['components'][name] = 'failed'
                        self.st['warnings'].append(f'{name} 进程已退出，状态 {ended.si_status}；见 logs/{name}.log')
                else:
                    raise RuntimeError(f'{name} 意外退出，状态 {ended.si_status}；见 logs/{name}.log')

    def wait(self, condition, seconds, label):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            self.spin()
            if condition():
                return
        raise TimeoutError(label)

    def startup(self):
        share = Path('/opt/ros/humble/share')
        self.processes.start('gazebo', ['ign', 'gazebo', '-s', '-r', '-v', '3', self.plan['sdf']])
        self.st['components']['gazebo'] = 'running'
        topics = [f'/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock',
                  f'/world/{self.world}/dynamic_pose/info@tf2_msgs/msg/TFMessage[ignition.msgs.Pose_V']
        remaps = ['-r', f'/world/{self.world}/dynamic_pose/info:=/ground_truth/poses']
        for d in self.drivers:
            topics += [f'/model/{d.name}/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist',
                       f'/model/{d.name}/odometry@nav_msgs/msg/Odometry[ignition.msgs.Odometry']
            remaps += ['-r', f'/model/{d.name}/cmd_vel:=/{d.name}/cmd_vel', '-r', f'/model/{d.name}/odometry:=/{d.name}/odom']
        bridge_env = {'LD_PRELOAD': str(self.bridge_fix)} if self.bridge_fix else {}
        self.processes.start('bridge', ['ros2', 'run', 'ros_gz_bridge', 'parameter_bridge', *topics, '--ros-args', *remaps], bridge_env)
        self.st['components']['bridge'] = 'running'
        self.wait(lambda: self.clock is not None and all(d.pose is not None for d in self.drivers), 90, 'Gazebo 时钟或车辆真值未就绪')
        if self.args.web:
            self.web_bridges(share)
        if self.args.gui:
            self.window('gui', True)
        if self.args.rviz:
            self.window('rviz', True)
        self.publish_static()
        self.phase('ready')

    def web_bridges(self, share):
        fox = EXTRAS / 'lib/foxglove_bridge/foxglove_bridge'
        if fox.exists():
            env = {'LD_LIBRARY_PATH': ':'.join(filter(None, [str(EXTRAS / 'lib'), self.env.get('LD_LIBRARY_PATH')])),
                   'AMENT_PREFIX_PATH': ':'.join(filter(None, [str(EXTRAS), self.env.get('AMENT_PREFIX_PATH')]))}
            port = self.args.foxglove_port
            self.processes.start('foxglove', [str(fox), '--ros-args', '-p', f'port:={port}', '-p', 'address:=127.0.0.1',
                                              '-p', 'use_sim_time:=true'], env)
            self.st['components']['foxglove'] = 'running'
            self.st['web']['ros'] = {'url': f'ws://127.0.0.1:{port}', 'protocol': 'foxglove.sdk.v1'}
        else:
            self.st['warnings'].append('Foxglove Bridge 未安装：bash src/lab/ros/native/install-ros-extras.sh')
        key = secrets.token_hex(16)
        port = self.args.gazebo_web_port
        cfg = self.runtime / 'gazebo-web.ign'
        cfg.write_text(f"""<?xml version='1.0'?>
<ignition version='1.0'>
  <plugin name="ignition::launch::WebsocketServer" filename="ignition-launch-websocket-server">
    <publication_hz>30</publication_hz>
    <port>{port}</port>
    <authorization_key>{key}</authorization_key>
    <max_connections>8</max_connections>
  </plugin>
</ignition>
""")
        # The server only hands out assets under the resource paths: the generated meshes and ROS packages.
        paths = ':'.join([str(self.runtime), str(share)])
        self.processes.start('gazebo_web', ['ign', 'launch', '-v', '3', str(cfg)],
                             {'IGN_GAZEBO_RESOURCE_PATH': paths, 'GZ_SIM_RESOURCE_PATH': paths})
        self.st['components']['gazebo_web'] = 'running'
        self.st['web']['gazebo'] = {'url': f'ws://127.0.0.1:{port}', 'key': key, 'world': self.world, 'bounds': self.plan['bounds']}

    def window(self, key, on):
        if not on:
            chosen = [r for r in self.processes.children if r[0] == key]
            if chosen:
                everything = self.processes.children
                self.processes.children = chosen
                self.report.setdefault('window_cleanup', []).extend(self.processes.cleanup())
                self.processes.children = [r for r in everything if r not in chosen]
            self.st['components'][key] = 'off'
            return
        if self.st['components'].get(key) == 'running':
            return
        if key == 'gui':
            command = ['ign', 'gazebo', '-g', '-v', '2']
        else:
            command = ['rviz2', '-d', str(self.rviz_config()), '--ros-args', '-p', 'use_sim_time:=true']
        self.processes.start(key, command)
        self.st['components'][key] = 'running'

    def rviz_config(self) -> Path:
        """Top-down RViz2 view of this field: the workbench marker topics plus the vehicle TF frames."""
        minx, miny, maxx, maxy = self.plan['bounds']
        scale = 900 / max(20.0, 1.15 * max(maxx - minx, maxy - miny))

        def markers(name, topic, latched):
            durability = 'Transient Local' if latched else 'Volatile'
            return f"""    - Class: rviz_default_plugins/MarkerArray
      Enabled: true
      Name: {name}
      Namespaces: {{}}
      Topic:
        Depth: 5
        Durability Policy: {durability}
        History Policy: Keep Last
        Reliability Policy: Reliable
        Value: {topic}
      Value: true
"""
        displays = (markers('Field', '/workbench/field', True) + markers('Planned routes', '/workbench/routes', True)
                    + markers('Tasks', '/workbench/tasks', True) + markers('Actual trails', '/workbench/trails', False)
                    + markers('Vehicles', '/workbench/vehicles', False))
        text = f"""Panels:
  - Class: rviz_common/Displays
    Name: Displays
Visualization Manager:
  Class: ""
  Displays:
    - Class: rviz_default_plugins/Grid
      Enabled: true
      Name: Grid
      Cell Size: 10
      Plane Cell Count: {int(max(maxx - minx, maxy - miny) / 10) + 4}
      Value: true
{displays}    - Class: rviz_default_plugins/TF
      Enabled: true
      Name: TF
      Show Names: false
      Marker Scale: 2
      Value: true
  Enabled: true
  Global Options:
    Background Color: 236; 238; 241
    Fixed Frame: map
    Frame Rate: 30
  Name: root
  Tools:
    - Class: rviz_default_plugins/MoveCamera
    - Class: rviz_default_plugins/Select
  Value: true
  Views:
    Current:
      Class: rviz_default_plugins/TopDownOrtho
      Name: Current View
      Angle: 0
      Scale: {scale:.3f}
      Target Frame: <Fixed Frame>
      Value: TopDownOrtho (rviz_default_plugins)
      X: {(minx + maxx) / 2:.3f}
      Y: {(miny + maxy) / 2:.3f}
    Saved: ~
Window Geometry:
  Height: 980
  Width: 1400
"""
        path = self.runtime / 'field.rviz'
        path.write_text(text)
        return path

    # ------------------------------------------------------------ markers --
    def marker(self, ns, mid, mtype, color, **kw):
        m = Marker()
        m.header.frame_id = 'map'
        m.header.stamp = self.node.get_clock().now().to_msg()
        m.ns, m.id, m.type, m.action = ns, mid, mtype, Marker.ADD
        m.pose.orientation.w = 1.0
        m.color = color
        m.scale.x = m.scale.y = m.scale.z = 1.0
        for k, v in kw.items():
            setattr(m, k, v)
        return m

    def publish_static(self):
        arr = MarkerArray()
        for i, layer in enumerate(self.plan['field_layers']):
            m = self.marker(layer['ns'], i, Marker.TRIANGLE_LIST, rgba(layer['color'], layer.get('alpha', 1.0)))
            m.pose.position.z = layer.get('z', 0.0)
            m.points = [Point(x=float(x), y=float(y), z=0.0) for x, y in layer['triangles']]
            arr.markers.append(m)
        for i, line in enumerate(self.plan['outlines']):
            m = self.marker(line['ns'], i, Marker.LINE_STRIP, rgba(line['color'], line.get('alpha', 1.0)))
            m.scale.x = line.get('width', 0.15)
            m.pose.position.z = line.get('z', 0.05)
            m.points = [Point(x=float(x), y=float(y), z=0.0) for x, y in line['points']]
            arr.markers.append(m)
        dx, dy = self.plan['depot']
        depot = self.marker('depot', 0, Marker.CUBE, rgba('#9e9e9a'))
        depot.pose.position.x, depot.pose.position.y, depot.pose.position.z = float(dx), float(dy), 0.05
        depot.scale.x = depot.scale.y = 3.0
        depot.scale.z = 0.1
        arr.markers.append(depot)
        self.pub_field.publish(arr)
        routes = MarkerArray()
        for i, d in enumerate(self.drivers):
            m = self.marker('routes', i, Marker.LINE_STRIP, rgba(d.color, 0.85))
            m.scale.x = 0.25
            m.pose.position.z = 0.12
            m.points = [Point(x=float(x), y=float(y), z=0.0) for x, y in d.path]
            routes.markers.append(m)
        self.pub_routes.publish(routes)
        self.publish_tasks()

    def publish_tasks(self):
        arr = MarkerArray()
        k = 0
        for d in self.drivers:
            for t in d.tasks:
                done = t['state'] == 'reached'
                m = self.marker('tasks', k, Marker.CYLINDER, rgba('#ffffff' if done else d.color, 1.0))
                m.pose.position.x, m.pose.position.y = float(t['xy'][0]), float(t['xy'][1])
                m.pose.position.z = 0.35
                m.scale.x = m.scale.y = 0.6 if done else 0.45
                m.scale.z = 0.7
                arr.markers.append(m)
                label = self.marker('task_labels', k, Marker.TEXT_VIEW_FACING, rgba('#1d1d1f'))
                label.pose.position.x, label.pose.position.y, label.pose.position.z = float(t['xy'][0]), float(t['xy'][1]), 1.3
                label.scale.z = 0.8
                label.text = t['label']
                arr.markers.append(label)
                k += 1
        self.pub_tasks.publish(arr)
        self.published_tasks = self.task_version

    def publish_live(self, trails=False):
        arr = MarkerArray()
        status = []
        for i, d in enumerate(self.drivers):
            if d.pose is None:
                continue
            x, y, yaw = d.pose
            body = self.marker('vehicles', i, Marker.CUBE, rgba(d.color))
            body.pose.position.x, body.pose.position.y, body.pose.position.z = x, y, 0.35
            body.pose.orientation.z, body.pose.orientation.w = math.sin(yaw / 2), math.cos(yaw / 2)
            body.scale.x, body.scale.y, body.scale.z = 0.8, 0.56, 0.3
            arr.markers.append(body)
            label = self.marker('vehicle_labels', i, Marker.TEXT_VIEW_FACING, rgba(d.color))
            label.pose.position.x, label.pose.position.y, label.pose.position.z = x, y, 1.6
            label.scale.z = 1.0
            label.text = d.label
            arr.markers.append(label)
            status.append(d.summary(self.plan_by_name.get(d.name)))
        self.pub_vehicles.publish(arr)
        self.pub_status.publish(String(data=json.dumps({'t': self.clock, 'vehicles': status}, ensure_ascii=False)))
        if trails:
            tr = MarkerArray()
            for i, d in enumerate(self.drivers):
                if len(d.trail) < 2:
                    continue
                m = self.marker('trails', i, Marker.LINE_STRIP, rgba(d.color, 1.0))
                m.scale.x = 0.12
                m.pose.position.z = 0.2
                m.points = [Point(x=p[1], y=p[2], z=0.0) for p in d.trail]
                tr.markers.append(m)
            self.pub_trails.publish(tr)

    # ------------------------------------------------------------ execute --
    def execute(self):
        self.phase('running')
        for d in self.drivers:
            d.state = 'driving'
        planned = max([v.get('planned_duration_s') or 0 for v in self.plan['vehicles']] + [60])
        deadline = (self.clock or 0) + 2.5 * planned + 120
        last_ctrl = last_live = last_trail = -1.0
        while not self.stop.is_set():
            self.spin(0.005)
            t = self.clock or 0.0
            if t - last_ctrl >= 0.05:
                last_ctrl = t
                for d in self.drivers:
                    v, w = d.step(t)
                    d.v_cmd, d.w_cmd = v, w
                    msg = Twist()
                    msg.linear.x, msg.angular.z = float(v), float(w)
                    self.cmd[d.name].publish(msg)
                    if d.pose is not None and (not d.trail or t - d.trail[-1][0] >= 0.5):
                        if d.trail:
                            dt = max(1e-6, t - d.trail[-1][0])
                            d.speed_now = math.dist(d.trail[-1][1:3], d.pose[:2]) / dt
                        d.trail.append([round(t, 2), round(d.pose[0], 3), round(d.pose[1], 3), round(d.pose[2], 4)])
                if sum(tk['state'] == 'reached' for d in self.drivers for tk in d.tasks) != self.task_version:
                    self.task_version = sum(tk['state'] == 'reached' for d in self.drivers for tk in d.tasks)
                    self.publish_tasks()
            if t - last_live >= 0.2:
                last_live = t
                self.publish_live(trails=t - last_trail >= 1.0)
                if t - last_trail >= 1.0:
                    last_trail = t
                with self.lock:
                    self.st['vehicles'] = [d.summary(self.plan_by_name.get(d.name)) for d in self.drivers]
            if all(d.state in ('done', 'failed') for d in self.drivers):
                break
            if t > deadline:
                for d in self.drivers:
                    if d.state not in ('done', 'failed'):
                        d.state = 'failed'
                self.st['errors'].append(f'执行超时：仿真时间超过 {deadline:.0f} s')
                break
        for d in self.drivers:
            self.cmd[d.name].publish(Twist())
        self.publish_live(trails=True)
        self.finish()

    def finish(self):
        vehicles = [d.summary(self.plan_by_name.get(d.name)) for d in self.drivers]
        durations = [v['duration_s'] for v in vehicles if v['duration_s'] is not None]
        planned = self.plan.get('planned', {})
        metrics = {
            'tasks_total': sum(len(d.tasks) for d in self.drivers),
            'tasks_reached': sum(t['state'] == 'reached' for d in self.drivers for t in d.tasks),
            'vehicles_done': sum(d.state == 'done' for d in self.drivers),
            'makespan_s': max(durations) if durations and len(durations) == len(self.drivers) else None,
            'planned_makespan_s': planned.get('makespan_s'),
            'total_distance_m': round(sum(d.distance for d in self.drivers), 2),
            'planned_total_distance_m': planned.get('total_distance_m'),
            'cross_track_mean_m': round(sum(sum(d.cte) for d in self.drivers) / max(1, sum(len(d.cte) for d in self.drivers)), 4),
            'cross_track_max_m': round(max((max(d.cte) for d in self.drivers if d.cte), default=0.0), 4),
        }
        result = dict(session_id=self.plan['session_id'], run_id=self.plan['run_id'], scenario_id=self.plan['scenario_id'],
                      algorithm=self.plan.get('algorithm'), world=self.world, finished_utc=now(), sim_time=self.clock,
                      real_time_factor=self.st.get('real_time_factor'), metrics=metrics, vehicles=vehicles,
                      tasks=[dict(vehicle=d.name, **{k: t[k] for k in ('id', 'label', 'xy', 'state', 't_sim', 'distance_m')})
                             for d in self.drivers for t in d.tasks],
                      trails={d.name: d.trail for d in self.drivers},
                      state='succeeded' if metrics['tasks_reached'] == metrics['tasks_total'] and metrics['vehicles_done'] == len(self.drivers) else 'failed')
        save(self.runtime / 'result.json', result)
        with self.lock:
            self.st.update(vehicles=vehicles, metrics=metrics, result=str(self.runtime / 'result.json'))
        self.phase('finished' if result['state'] == 'succeeded' else 'failed')

    # ------------------------------------------------------------ lifecycle --
    def shutdown(self):
        for d in self.drivers:
            try:
                self.cmd[d.name].publish(Twist())
            except Exception:  # noqa: BLE001 - shutting down anyway
                pass
        self.report['final_state'] = self.state()
        try:
            self.node.destroy_node()
            rclpy.shutdown()
        except Exception as exc:  # noqa: BLE001
            self.report['errors'].append(f'ROS 关闭：{exc}')
        self.report['bridge_shutdown'] = self.processes.stop_bridges()
        self.report['cleanup'] = self.processes.cleanup()
        self.report['remaining_owned_processes'] = self.processes.sample()
        bad = []
        for child in self.report['cleanup']:
            bad.extend(dict(group=child['name'], **p) for p in child['reaped'] if p['returncode'] not in (0, -2, -15, 130, 143))
            if not child['complete'] or 'SIGKILL' in child['signals']:
                bad.append({'group': child['name'], 'forced_or_incomplete': True})
        self.report['abnormal_exits'] = bad
        self.report['status'] = 'PASS' if not (bad or self.report['remaining_owned_processes']) else 'FAIL'
        self.report.update(finished_utc=now(), stages=self.st['stages'], resources=self.processes.resources)
        save(self.runtime / 'session-report.json', self.report)
        print(json.dumps({'shutdown': self.report['status']}), flush=True)
        if self.st['phase'] not in ('finished', 'failed'):
            self.st['phase'] = 'stopped'
        return 0 if self.report['status'] == 'PASS' else 1

    def state(self):
        with self.lock:
            st = copy.deepcopy(self.st)
        if not st['vehicles']:
            st['vehicles'] = [d.summary(self.plan_by_name.get(d.name)) for d in self.drivers]
        return st

    def run(self):
        try:
            self.startup()
            if self.args.autostart:
                self.execute()
            while not self.stop.is_set():
                self.spin(0.05)
                with self.lock:
                    pending, self.commands = self.commands, []
                for key, on in pending:
                    self.window(key, on)
                if self.clock is not None:
                    self.publish_live()
        except KeyboardInterrupt:
            pass
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            self.st['errors'].append(f'{type(exc).__name__}: {exc}')
            self.report['errors'].append(traceback.format_exc())
            self.phase('failed')
        finally:
            return self.shutdown()


def handler(session: Session):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass

        def answer(self, code, obj):
            body = json.dumps(obj, ensure_ascii=False, allow_nan=False).encode()
            self.send_response(code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == '/state':
                self.answer(200, session.state())
            else:
                self.answer(404, {'message': '接口不存在'})

        def do_POST(self):
            try:
                origin, host = self.headers.get('Origin'), self.headers.get('Host')
                if origin and origin not in ('http://' + host, 'https://' + host):
                    return self.answer(403, {'message': '拒绝跨源写入'})
                size = int(self.headers.get('Content-Length', '0'))
                body = json.loads(self.rfile.read(size) or b'{}') if size else {}
                if self.path == '/shutdown':
                    session.stop.set()
                    return self.answer(202, {'accepted': True})
                if self.path in ('/gui', '/rviz'):
                    with session.lock:
                        session.commands.append((self.path[1:], bool(body.get('on', True))))
                    return self.answer(202, {'accepted': True})
                self.answer(404, {'message': '接口不存在'})
            except Exception as exc:  # noqa: BLE001
                self.answer(400, {'message': f'{type(exc).__name__}: {exc}'})
    return Handler


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--runtime', required=True)
    p.add_argument('--port', type=int, default=4192)
    p.add_argument('--gui', action='store_true')
    p.add_argument('--rviz', action='store_true')
    p.add_argument('--no-web', dest='web', action='store_false')
    p.add_argument('--no-autostart', dest='autostart', action='store_false')
    p.add_argument('--foxglove-port', type=int, default=8765)
    p.add_argument('--gazebo-web-port', type=int, default=9002)
    args = p.parse_args()
    session = Session(args)
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: session.stop.set())
    server = ThreadingHTTPServer(('127.0.0.1', args.port), handler(session))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        return session.run()
    finally:
        server.shutdown()
        server.server_close()


if __name__ == '__main__':
    raise SystemExit(main())
