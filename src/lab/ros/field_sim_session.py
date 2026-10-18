#!/usr/bin/python3
"""Multi-vehicle field task in Gazebo Fortress, driven over ROS 2 (system Python 3.10).

Gazebo runs the field world generated from the task map; one ros_gz parameter_bridge carries the
clock, ground-truth poses and every vehicle's cmd_vel / odometry. Each vehicle follows its planned
VRP route with a pure-pursuit controller that stops at each of its tasks' service positions (dwelling
for the task's service time) and records arrivals, so the executed schedule can be compared with the
plan. Sharp corners (lane entries, U-turns in a lane) are taken exactly: the vehicle drives to the
corner, turns in place and goes on, so it stays between crop rows when they are solid.
Foxglove Bridge and the Gazebo WebSocket server feed the workbench's live 3D views; RViz2 and the
Gazebo GUI can be opened as separate windows.
"""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import secrets
import signal
import socket
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
sys.path[:0] = [str(DEPLOY), str(LAB / 'ros'), str(LAB)]
from urp_lab.field_tracking import Driver, truth_time  # noqa: E402
from urp_lab.field_traffic import MissionQueue, POLICY
from bridge_runtime import bridge_environment, bridge_provenance
from processes import OwnedProcesses  # noqa: E402
from physics_runtime import audit as audit_physics_runtime, selection as physics_selection

import rclpy  # noqa: E402
from rclpy.executors import SingleThreadedExecutor  # noqa: E402
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy  # noqa: E402
from rclpy.signals import SignalHandlerOptions  # noqa: E402
from nav_msgs.msg import Odometry  # noqa: E402
from geometry_msgs.msg import Point, Twist, TransformStamped  # noqa: E402
from rosgraph_msgs.msg import Clock  # noqa: E402
from ros_gz_interfaces.msg import Contacts
from std_msgs.msg import ColorRGBA, String  # noqa: E402
from tf2_msgs.msg import TFMessage  # noqa: E402
from tf2_ros import TransformBroadcaster  # noqa: E402
from visualization_msgs.msg import Marker, MarkerArray  # noqa: E402


OPTIONAL = ('gui', 'rviz', 'foxglove', 'gazebo_web')


def now():
    return datetime.now(timezone.utc).isoformat()


def yaw_of(q):
    return math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))


def roll_pitch(q):
    return (math.atan2(2 * (q.w*q.x + q.y*q.z), 1 - 2 * (q.x*q.x + q.y*q.y)),
            math.asin(max(-1, min(1, 2 * (q.w*q.y - q.z*q.x)))))


def save(path: Path, obj):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False))
    tmp.replace(path)


def rgba(hexcolor, a=1.0):
    h = hexcolor.lstrip('#')
    return ColorRGBA(r=int(h[0:2], 16) / 255, g=int(h[2:4], 16) / 255, b=int(h[4:6], 16) / 255, a=a)


class Processes(OwnedProcesses):
    def __init__(self, env, runtime):
        super().__init__(env, 'fieldsim')
        self.runtime = runtime
        self.launch_counts = {}

    def start(self, name, command, extra_env=None):
        count = self.launch_counts.get(name, 0)
        path = self.runtime / 'logs' / f'{name}{"-" + str(count) if count else ""}.log'
        with path.open('x') as stream:
            p = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT, env={**self.env, **(extra_env or {})},
                                 start_new_session=True)
        self.children.append((name, p, path, command))
        self.launch_counts[name] = count + 1
        return path




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
        self.window_workers = {}
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
        self.bridge_env = bridge_environment()
        self.report = dict(session_id=self.plan['session_id'], started_utc=now(), world=self.world, errors=[])
        self.report['bridge_runtime'] = bridge_provenance()
        self.drivers = [Driver(v, float(self.plan['speed_mps'])) for v in self.plan['vehicles']]
        self.plan_by_name = {v['name']: v for v in self.plan['vehicles']}
        self.clock = None
        self.clock_stamp = None
        self.input_generation = 0
        self.clock_wall = None
        self.clock_progress_wall = None
        self.truth_wall = {}
        self.odom_wall = {}
        self.counts = {'clock': 0, 'truth': 0, 'odom': {d.name: 0 for d in self.drivers},
                       'contacts': {d.name: 0 for d in self.drivers}}
        self.contact_wall = {}
        self.contacts, self.contact_examples = [], []
        self.ground_contact_samples = []  # diagnostic probes only; never filtered into mission success
        self.control_traces = {d.name: [] for d in self.drivers}
        self.rigid_poses = {d.name: [] for d in self.drivers}
        self.odometry = {d.name: [] for d in self.drivers}
        self.truth_timing = {'tf_header_samples': 0, 'latest_clock_samples': 0,
                             'scope': 'Gazebo PosePublisher 每车模型姿态；源仿真时间；新会话拒绝零时间戳，不再使用接收时钟近似'}
        self.traffic = None
        self.result = None
        self.execution_started = False
        rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
        # One authoritative /clock subscription. All scheduling and published stamps
        # below use its source time explicitly; no duplicate TimeSource subscription.
        self.node = rclpy.create_node('field_fleet_session')
        self.executor = SingleThreadedExecutor()
        self.executor.add_node(self.node)
        latched = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.TRANSIENT_LOCAL)
        # These are experiment/control records, not disposable visualization samples.
        # The bridge's reliable publishers support retransmission of local DDS bursts.
        streaming = QoSProfile(depth=200, reliability=ReliabilityPolicy.RELIABLE,
                                durability=DurabilityPolicy.VOLATILE)
        clock_qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.BEST_EFFORT)
        self.node.create_subscription(Clock, '/clock', self.on_clock, clock_qos)
        self.node.create_subscription(TFMessage, '/ground_truth/poses', self.on_truth, streaming)
        for d in self.drivers:
            self.node.create_subscription(Odometry, f'/{d.name}/odom',
                                          lambda msg, name=d.name: self.on_odom(name, msg), streaming)
            self.node.create_subscription(Contacts, f'/model/{d.name}/contacts',
                                          lambda msg, name=d.name: self.on_contacts(name, msg), streaming)
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
        self.input_generation += 1
        value = msg.clock.sec + msg.clock.nanosec / 1e9
        wall = time.monotonic()
        if self.clock is not None and value < self.clock - 1e-6:
            raise RuntimeError('仿真时钟倒退，不能继续累计实验时间')
        if self.clock is None or value > self.clock:
            self.clock_progress_wall = wall
        self.clock = value
        self.clock_stamp = msg.clock
        self.counts['clock'] += 1
        if self.clock_wall:
            (c0, w0) = self.clock_wall
            if wall - w0 >= 2.0:
                self.st['real_time_factor'] = round((self.clock - c0) / (wall - w0), 2)
                self.clock_wall = (self.clock, wall)
        else:
            self.clock_wall = (self.clock, wall)
        self.st['sim_time'] = round(self.clock, 2)

    def on_odom(self, name, msg):
        self.input_generation += 1
        self.odom_wall[name] = time.monotonic()
        self.counts['odom'][name] += 1
        if self.st['phase'] == 'running':
            p, q = msg.pose.pose.position, msg.pose.pose.orientation
            stamp = msg.header.stamp.sec + msg.header.stamp.nanosec / 1e9
            self.odometry[name].append([stamp, p.x, p.y, yaw_of(q), msg.twist.twist.linear.x, msg.twist.twist.angular.z])

    def on_contacts(self, name, msg):
        self.input_generation += 1
        self.contact_wall[name] = time.monotonic()
        self.counts['contacts'][name] += 1
        for contact in msg.contacts:
            pair = [contact.collision1.name, contact.collision2.name]
            if self.plan.get('probe_ground_contacts') and self.st['phase'] == 'running' and any('ground::' in n for n in pair):
                self.ground_contact_samples.append({'t_sim': msg.header.stamp.sec + msg.header.stamp.nanosec / 1e9,
                    'collisions': pair, 'positions_m': [[p.x, p.y, p.z] for p in contact.positions]})
            if pair not in self.contact_examples and len(self.contact_examples) < 20:
                self.contact_examples.append(pair)
            # Wheel/caster-ground contacts are expected; every other external contact is a failure.
            if any('ground::' in n for n in pair) or all(f'{name}::' in n for n in pair):
                continue
            stamp = msg.header.stamp.sec + msg.header.stamp.nanosec / 1e9
            self.contacts.append({'t_sim': stamp, 'vehicle': name, 'collisions': pair,
                                  'vehicles': [d.name for d in self.drivers if any(f'{d.name}::' in n for n in pair)],
                                  'positions_m': [[p.x, p.y, p.z] for p in contact.positions],
                                  'depths_m': list(contact.depths)})
        if self.contacts:
            raise RuntimeError('Gazebo 检测到非地面接触，停止全部车辆；时间、位置及碰撞体已记录')

    def on_truth(self, msg):
        self.input_generation += 1
        names = {d.name: d for d in self.drivers}
        out = []
        for t in msg.transforms:
            d = names.get(t.child_frame_id)
            if not d:
                continue
            p = t.transform.translation
            roll, pitch = roll_pitch(t.transform.rotation)
            if self.st['phase'] in ('ready', 'running') and (max(abs(roll), abs(pitch)) > .35 or abs(p.z) > .5):
                self.report['physical_domain_violation'] = {'vehicle':d.name,
                    't_sim':t.header.stamp.sec+t.header.stamp.nanosec/1e9, 'xyz_m':[p.x,p.y,p.z],
                    'roll_rad':roll, 'pitch_rad':pitch}
                raise RuntimeError(f'{d.name} 姿态或高度超出平坦刚体模型有效域，停止全部车辆')
            pose = (p.x, p.y, yaw_of(t.transform.rotation))
            stamp = t.header.stamp.sec + t.header.stamp.nanosec / 1e9
            if stamp <= 0:
                raise RuntimeError('PosePublisher 未提供正的源仿真时间，拒绝以接收时钟代替')
            source = 'tf_header_samples' if stamp > 0 else 'latest_clock_samples'
            stamp = truth_time(stamp, self.clock)
            if stamp is None:
                continue
            self.truth_timing[source] += 1
            d.observe(pose, stamp, record_distance=self.st['phase'] == 'running')
            self.truth_wall[d.name] = time.monotonic()
            self.counts['truth'] += 1
            if self.st['phase'] == 'running' and self.clock is not None:
                if not d.samples or stamp > d.samples[-1][0]:
                    d.samples.append([stamp, *pose])
                    self.rigid_poses[d.name].append([stamp, p.x, p.y, p.z, roll, pitch, pose[2]])
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
        # Keep the node registered and drain ready callbacks before control. Repeated
        # global spin_once registers/removes the node for every single callback.
        self.executor.spin_once(timeout_sec=seconds)
        deadline = time.monotonic() + .002
        for _ in range(96):
            before = self.input_generation
            self.executor.spin_once(timeout_sec=0)
            if self.input_generation == before or time.monotonic() >= deadline:
                break
        if self.stop.is_set():
            raise KeyboardInterrupt
        with self.lock:
            pending, self.commands = self.commands, []
        for key, on in pending:
            try:
                self.window(key, on)
            except Exception as exc:
                self.st['components'][key] = 'failed'
                self.st['warnings'].append(f'{key} 窗口控制失败：{exc}')
        if self.st['phase'] in ('ready', 'running'):
            wall = time.monotonic()
            stale = []
            if self.clock_progress_wall is None or wall - self.clock_progress_wall > 3.0:
                stale.append('clock 无进展')
            for d in self.drivers:
                if wall - self.truth_wall.get(d.name, 0) > 3.0:
                    stale.append(f'{d.name} 真值')
                if wall - self.odom_wall.get(d.name, 0) > 3.0:
                    stale.append(f'{d.name} 里程计')
                if wall - self.contact_wall.get(d.name, 0) > 3.0:
                    stale.append(f'{d.name} 接触传感器')
            if stale:
                raise RuntimeError('仿真遥测中断超过 3 秒墙钟：' + '、'.join(stale))
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
        # Selection diagnostics must be visible before readiness, not only when
        # Gazebo flushes its buffered stdout on exit.
        self.processes.start('gazebo', ['stdbuf', '-oL', '-eL', 'ign', 'gazebo', '-s', '-r', '-v', '3', self.plan['sdf']])
        self.st['components']['gazebo'] = 'running'
        bridges = [dict(ros_topic_name='/clock', gz_topic_name='/clock',
                        ros_type_name='rosgraph_msgs/msg/Clock', gz_type_name='ignition.msgs.Clock',
                        direction='GZ_TO_ROS', publisher_queue=1)]
        for d in self.drivers:
            for topic, ros_topic, ros_type, gz_type, command in (
                ('cmd_vel', f'/{d.name}/cmd_vel', 'geometry_msgs/msg/Twist', 'Twist', True),
                ('pose', '/ground_truth/poses', 'tf2_msgs/msg/TFMessage', 'Pose_V', False),
                ('odometry', f'/{d.name}/odom', 'nav_msgs/msg/Odometry', 'Odometry', False),
                ('contacts', f'/model/{d.name}/contacts', 'ros_gz_interfaces/msg/Contacts', 'Contacts', False)):
                bridges.append(dict(ros_topic_name=ros_topic, gz_topic_name=f'/model/{d.name}/{topic}',
                                    ros_type_name=ros_type, gz_type_name='ignition.msgs.' + gz_type,
                                    direction='ROS_TO_GZ' if command else 'GZ_TO_ROS',
                                    publisher_queue=1 if command else 200, subscriber_queue=1 if command else 200))
        # JSON is a YAML subset accepted by this installed ros_gz_bridge release.
        # CLI topic arguments otherwise silently leave publishers at depth 10.
        config = self.runtime / 'bridge-config.json'
        save(config, bridges)
        self.report['telemetry_contract'] = {'schema': 'urp.field-transport/1',
            'clock': 'latest source /clock, depth 1; no duplicate clock subscription',
            'records': 'reliable ROS subscription and bridge history depth 200; no intentional contact decimation',
            'control_max_abs_pose_age_s': .10, 'bridges': bridges}
        bridge_env = self.bridge_env
        self.processes.start('bridge', ['ros2', 'run', 'ros_gz_bridge', 'parameter_bridge', '--ros-args',
                                       '-p', f'config_file:={config}'], bridge_env)
        self.st['components']['bridge'] = 'running'
        self.wait(lambda: self.clock is not None and all(d.pose is not None and d.name in self.odom_wall
                  and d.name in self.contact_wall for d in self.drivers), 90, 'Gazebo 时钟、车辆真值、里程计或接触传感器未就绪')
        if self.plan.get('physics'):
            # Gazebo may still be flushing startup output when telemetry starts.
            self.wait(lambda: all(physics_selection(self.runtime/'logs/gazebo.log')), 10,
                      'Gazebo 未报告碰撞检测器和约束求解器选择')
            gazebo_group = next(p.pid for name, p, *_ in self.processes.children if name == 'gazebo')
            pids = [row['pid'] for row in self.processes.sample() if row['group'] == gazebo_group]
            observed = audit_physics_runtime(self.plan['physics'], self.runtime/'logs/gazebo.log', pids)
            self.report['physics_runtime'] = observed
            if not observed['valid']:
                raise RuntimeError('；'.join(observed['errors']))
        if self.args.web:
            self.web_bridges(share)
        if self.args.gui:
            self.window('gui', True)
        if self.args.rviz:
            self.window('rviz', True)
        self.publish_static()
        self.phase('ready')

    def web_bridges(self, share):
        endpoints = {}
        fox = EXTRAS / 'lib/foxglove_bridge/foxglove_bridge'
        if fox.exists():
            env = {'LD_LIBRARY_PATH': ':'.join(filter(None, [str(EXTRAS / 'lib'), self.env.get('LD_LIBRARY_PATH')])),
                   'AMENT_PREFIX_PATH': ':'.join(filter(None, [str(EXTRAS), self.env.get('AMENT_PREFIX_PATH')]))}
            port = self.args.foxglove_port
            self.processes.start('foxglove', [str(fox), '--ros-args', '-p', f'port:={port}', '-p', 'address:=127.0.0.1',
                                              '-p', 'use_sim_time:=true'], env)
            self.st['components']['foxglove'] = 'running'
            endpoints['ros'] = ('foxglove', port, {'url': f'ws://127.0.0.1:{port}', 'protocol': 'foxglove.sdk.v1'})
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
        endpoints['gazebo'] = ('gazebo_web', port, {'url': f'ws://127.0.0.1:{port}', 'key': key, 'world': self.world, 'bounds': self.plan['bounds']})
        # Popen is not readiness. Only publish endpoints once their sockets accept connections.
        deadline = time.monotonic() + 15
        while endpoints and time.monotonic() < deadline:
            self.spin()
            for kind, (component, port, info) in list(endpoints.items()):
                if self.st['components'].get(component) == 'failed':
                    del endpoints[kind]
                    continue
                try:
                    with socket.create_connection(('127.0.0.1', port), timeout=0.1):
                        pass
                except OSError:
                    continue
                self.st['web'][kind] = info
                del endpoints[kind]
        for component, port, _ in endpoints.values():
            self.st['components'][component] = 'failed'
            self.st['warnings'].append(f'{component} 在 15 秒内未监听端口 {port}；核心仿真仍可运行')

    def window(self, key, on):
        worker = self.window_workers.get(key)
        if worker and worker.is_alive():
            if on:
                with self.lock:
                    self.commands.append((key, on))
            return
        if not on:
            chosen = [r for r in self.processes.children if r[0] == key]
            if chosen:
                # Reaping a GUI must not block the robot control loop or telemetry processing.
                owner = copy.copy(self.processes)
                owner.children, owner.resources = chosen, []
                self.processes.children = [r for r in self.processes.children if r not in chosen]
                self.st['components'][key] = 'stopping'

                def reap():
                    records = owner.cleanup()
                    with self.lock:
                        self.report.setdefault('window_cleanup', []).extend(records)
                        self.st['components'][key] = 'off'

                worker = threading.Thread(target=reap, daemon=True)
                self.window_workers[key] = worker
                worker.start()
                return
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
        m.header.stamp = self.clock_stamp if self.clock_stamp is not None else Clock().clock
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
        self.execution_started = True
        if self.plan.get('traffic', {}).get('policy') != POLICY:
            raise RuntimeError('缺少已验证的车间交通策略，拒绝执行')
        self.traffic = MissionQueue(self.drivers, self.plan['robot_radius_m'], self.clock or 0.0)
        self.st['warnings'].append('保守交通预约：整段任务依次执行，结束回独立停车位；等待计入实际用时，非并行避碰算法')
        planned = max(sum(v.get('planned_duration_s') or 0 for v in self.plan['vehicles']), 60)
        deadline = (self.clock or 0) + 2.5 * planned + 120
        last_ctrl = last_live = last_trail = -1.0
        terminal_since = None
        while not self.stop.is_set():
            self.spin(0.005)
            t = self.clock or 0.0
            if t - last_ctrl >= 0.05:
                last_ctrl = t
                self.traffic.step(t)
                for d in self.drivers:
                    previous_cte_count = len(d.cte)
                    v, w = d.step(t)
                    d.v_cmd, d.w_cmd = v, w
                    msg = Twist()
                    msg.linear.x, msg.angular.z = float(v), float(w)
                    self.cmd[d.name].publish(msg)
                    measured_cte = d.cte[-1] if len(d.cte) > previous_cte_count else None
                    self.control_traces[d.name].append([t, d.s, measured_cte, v, w, d.state,
                                                       t - d.pose_stamp if d.pose_stamp is not None else None])
                    if d.pose is not None and (not d.trail or t - d.trail[-1][0] >= 0.5):
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
                if any(d.state == 'failed' for d in self.drivers):
                    break
                if terminal_since is None:
                    terminal_since = t
                # Keep observing deceleration and contacts before certifying a final
                # trajectory; a zero command alone is not evidence of a stopped robot.
                if t - terminal_since >= 1 and all(d.speed_now < .02 and d.angular_speed_now < .05 for d in self.drivers):
                    break
                if t - terminal_since > 5:
                    raise RuntimeError('终点发出停车命令后，实测速度未在 5 秒仿真时间内稳定')
            if t > deadline:
                for d in self.drivers:
                    if d.state not in ('done', 'failed'):
                        d.state = 'failed'
                self.st['errors'].append(f'执行超时：仿真时间超过 {deadline:.0f} s')
                break
        for d in self.drivers:
            self.cmd[d.name].publish(Twist())
        self.publish_live(trails=True)
        self.finish('canceled' if self.stop.is_set() else None)

    def finish(self, outcome=None):
        if self.result is not None:
            return
        vehicles = [d.summary(self.plan_by_name.get(d.name)) for d in self.drivers]
        durations = [v['duration_s'] for v in vehicles if v['duration_s'] is not None]
        planned = self.plan.get('planned', {})
        from urp_lab.field_energy import account
        corridors = [c.get('polygon') for c in (self.plan.get('instance') or {}).get('corridors') or []]
        energy = {d.name: account(self.rigid_poses.get(d.name) or [], self.plan.get('physics'), corridors)
                  for d in self.drivers}
        metrics = {
            'tasks_total': sum(len(d.tasks) for d in self.drivers),
            'tasks_reached': sum(t['state'] == 'reached' for d in self.drivers for t in d.tasks),
            'tasks_completed': sum(t['serviced_at'] is not None for d in self.drivers for t in d.tasks),
            'vehicles_done': sum(d.state == 'done' for d in self.drivers),
            'makespan_s': max(durations) if durations and len(durations) == len(self.drivers) else None,
            'planned_makespan_s': planned.get('makespan_s'),
            'total_distance_m': round(sum(d.distance for d in self.drivers), 2),
            'planned_total_distance_m': planned.get('total_distance_m'),
            'cross_track_mean_m': round(sum(sum(d.cte) for d in self.drivers) / max(1, sum(len(d.cte) for d in self.drivers)), 4),
            'cross_track_max_m': round(max((max(d.cte) for d in self.drivers if d.cte), default=0.0), 4),
            'energy_wh': round(sum(e['energy_wh'] for e in energy.values() if e), 3),
        }
        result = dict(session_id=self.plan['session_id'], run_id=self.plan['run_id'], scenario_id=self.plan['scenario_id'],
                      algorithm=self.plan.get('algorithm'), world=self.world, finished_utc=now(), sim_time=self.clock,
                      real_time_factor=self.st.get('real_time_factor'), metrics=metrics, vehicles=vehicles,
                      tasks=[dict(vehicle=d.name, stop=list(t['goal']), requested_service_s=t['service_s'],
                                  actual_service_s=t['serviced_at'] - t['t_sim'] if t['serviced_at'] is not None else None,
                                  service_complete=t['serviced_at'] is not None,
                                  **{k: t[k] for k in ('id', 'label', 'xy', 'state', 't_sim', 'distance_m', 'serviced_at')})
                             for d in self.drivers for t in d.tasks],
                      travel=self.plan.get('travel', 'free'),
                      trails={d.name: d.samples for d in self.drivers},
                      errors=list(self.st['errors']), telemetry=copy.deepcopy(self.counts),
                      execution_provenance=self.plan.get('execution_provenance'),
                      traffic={**self.plan.get('traffic', {}), 'events': self.traffic.events if self.traffic else []},
                      contacts=self.contacts, contact_examples=self.contact_examples,
                      control_traces=self.control_traces,
                      control_trace_columns=['t_sim', 'path_s_m', 'cross_track_m', 'cmd_v_mps', 'cmd_w_radps', 'state', 'pose_age_s'],
                      truth_timing=self.truth_timing,
                      telemetry_contract=self.report.get('telemetry_contract'),
                      replay_contract={'schema': 'urp.replay/1', 'clock': 'simulation_source_time',
                                       'source': 'Gazebo PosePublisher; ground truth',
                                       'max_interpolation_gap_s': 0.25,
                                       'frame': 'local world; x/y metres; yaw radians'},
                      physics=self.plan.get('physics'), physics_audit=self.plan.get('physics_audit'),
                      physics_runtime=self.report.get('physics_runtime'),
                      execution_timing_reference=self.plan.get('execution_timing_reference'),
                      rigid_body_poses=self.rigid_poses,
                      rigid_body_pose_columns=['t_sim', 'x_m', 'y_m', 'z_m', 'roll_rad', 'pitch_rad', 'yaw_rad'],
                      energy=energy,
                      wheel_odometry=self.odometry,
                      wheel_odometry_columns=['t_sim', 'x_local_m', 'y_local_m', 'yaw_local_rad', 'v_mps', 'w_radps'],
                      execution_started_sim_s=self.traffic.started if self.traffic else None,
                      vehicle_asset=self.plan.get('vehicle_asset'),
                      state='succeeded' if metrics['tasks_reached'] == metrics['tasks_total'] and metrics['vehicles_done'] == len(self.drivers) else 'failed')
        from urp_lab.field_records import contact_metrics
        result.update(contact_metrics(result, self.plan))
        if outcome is not None:
            result['state'] = outcome
        save(self.runtime / 'result-candidate.json', result)
        if result['state'] == 'succeeded':
            try:
                # Geometry libraries stay in the locked Python 3.12 solver environment, outside ROS Python.
                checked = subprocess.run([str(LAB / '.venv/bin/python'), '-m', 'urp_lab.fieldcheck', str(self.runtime)],
                                         cwd=LAB, capture_output=True, text=True, timeout=30)
                (self.runtime / 'check.stdout').write_text(checked.stdout)
                (self.runtime / 'check.stderr').write_text(checked.stderr)
                if checked.returncode:
                    raise RuntimeError(f'轨迹检查进程退出码 {checked.returncode}')
                result['check'] = json.loads(checked.stdout)
                if not result['check']['valid']:
                    result['state'] = 'failed'
                    self.st['errors'].extend(result['check']['errors'])
            except Exception as exc:
                result['state'] = 'failed'
                self.st['errors'].append(f'实际轨迹未通过独立检查：{exc}')
        result['errors'] = list(self.st['errors'])
        self.result = result
        save(self.runtime / 'result.json', result)
        with self.lock:
            self.st.update(vehicles=vehicles, metrics=metrics, result=str(self.runtime / 'result.json'))
        self.phase({'succeeded': 'finished', 'canceled': 'stopped'}.get(result['state'], 'failed'))
        save(self.runtime / 'state.json', self.state())

    # ------------------------------------------------------------ lifecycle --
    def shutdown(self):
        cleanup_errors = []
        for d in self.drivers:
            try:
                self.cmd[d.name].publish(Twist())
            except Exception:  # noqa: BLE001 - shutting down anyway
                pass
        try:
            self.executor.shutdown()
            self.node.destroy_node()
            rclpy.shutdown()
        except Exception as exc:  # noqa: BLE001
            self.report['errors'].append(f'ROS 关闭：{exc}')
            cleanup_errors.append(f'ROS 关闭：{exc}')
        self.report['bridge_shutdown'] = self.processes.stop_bridges()
        self.report['cleanup'] = self.processes.cleanup()
        for worker in self.window_workers.values():
            worker.join(35)
            if worker.is_alive():
                cleanup_errors.append('窗口清理线程未退出')
        self.report['remaining_owned_processes'] = self.processes.sample()
        bad = []
        for child in self.report['cleanup'] + self.report.get('window_cleanup', []):
            bad.extend(dict(group=child['name'], **p) for p in child['reaped'] if p['returncode'] not in (0, -2, -15, 130, 143))
            if not child['complete'] or 'SIGKILL' in child['signals']:
                bad.append({'group': child['name'], 'forced_or_incomplete': True})
        self.report['abnormal_exits'] = bad
        bridge_bad = bool(self.report['bridge_shutdown']['still_running'])
        self.report['cleanup_status'] = 'PASS' if not (bad or bridge_bad or cleanup_errors or self.report['remaining_owned_processes']) else 'FAIL'
        self.report['status'] = 'PASS' if self.report['cleanup_status'] == 'PASS' and not self.report['errors'] and (self.result or {}).get('state') != 'failed' else 'FAIL'
        if self.st['phase'] not in ('finished', 'failed'):
            self.st['phase'] = 'stopped'
        self.report['execution_state'] = (self.result or {}).get('state')
        self.report['final_state'] = self.state()
        save(self.runtime / 'state.json', self.state())
        self.report.update(finished_utc=now(), stages=self.st['stages'], resources=self.processes.resources)
        save(self.runtime / 'session-report.json', self.report)
        print(json.dumps({'shutdown': self.report['status']}), flush=True)
        if self.st['phase'] not in ('finished', 'failed'):
            self.st['phase'] = 'stopped'
        return 0 if self.report['status'] == 'PASS' and (self.result or {}).get('state') != 'failed' else 1

    def state(self):
        with self.lock:
            st = copy.deepcopy(self.st)
        st['telemetry'] = copy.deepcopy(self.counts)
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
                if self.clock is not None:
                    self.publish_live()
        except KeyboardInterrupt:
            self.finish('canceled')
        except Exception as exc:  # noqa: BLE001
            traceback.print_exc()
            self.st['errors'].append(f'{type(exc).__name__}: {exc}')
            self.report['errors'].append(traceback.format_exc())
            self.phase('failed')
            self.finish('failed')
        finally:
            cleanup_rc = self.shutdown()
        return cleanup_rc


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


from physical_session_lock import exclusive_physics


@exclusive_physics
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
