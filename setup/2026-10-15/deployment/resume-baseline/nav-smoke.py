#!/usr/bin/python3
"""Bounded official Nav2 integration check. No URP research algorithms are evaluated."""
import argparse
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import re
import signal
import subprocess
import time
import traceback

import rclpy
from rclpy.action import ActionClient
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data, QoSProfile, DurabilityPolicy, ReliabilityPolicy
from action_msgs.msg import GoalStatus
from controller_manager_msgs.srv import ListControllers
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped, Twist
from irobot_create_msgs.action import Undock
from irobot_create_msgs.msg import DockStatus
from nav2_msgs.action import NavigateToPose
from nav2_msgs.srv import ManageLifecycleNodes
from nav_msgs.msg import Odometry, Path as NavPath
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import LaserScan
from tf2_msgs.msg import TFMessage
from tf2_ros import Buffer, TransformListener, TransformException
from rcl_interfaces.srv import GetParameters

BASE = Path(__file__).resolve().parent


class OwnedProcesses:
    """One-shot Linux subreaper: signal/reap only child groups created here."""
    def __init__(self, env, label):
        if ctypes.CDLL(None, use_errno=True).prctl(36, 1, 0, 0, 0):
            raise OSError(ctypes.get_errno(), 'PR_SET_CHILD_SUBREAPER failed')
        self.env, self.label, self.children = env, label, []
        self.peak_rss_kib = 0
        self.last_sample = 0

    def start(self, name, command):
        log = BASE / 'logs' / f'{self.label}-{name}.log'
        with log.open('x') as stream:
            p = subprocess.Popen(command, stdout=stream, stderr=subprocess.STDOUT,
                                 env=self.env, start_new_session=True)
        self.children.append((name, p, log, command))
        return log

    def sample(self):
        ids = {p.pid for _, p, _, _ in self.children}
        rss, rows = 0, []
        for path in Path('/proc').glob('[0-9]*/stat'):
            try:
                raw = path.read_text(); f = raw[raw.rfind(')') + 2:].split()
                if int(f[2]) in ids:
                    rows.append({'pid': int(path.parent.name), 'group': int(f[2]),
                                 'state': f[0], 'start_ticks': int(f[19])})
                    rss += int(f[21]) * os.sysconf('SC_PAGE_SIZE') // 1024
            except (OSError, ValueError):
                continue
        self.peak_rss_kib = max(self.peak_rss_kib, rss)
        return rows

    def cleanup(self):
        results = []
        for name, p, log, command in reversed(self.children):
            start = time.monotonic(); records = []; signals = []
            complete = False
            for sig, grace in [(signal.SIGINT, 12), (signal.SIGTERM, 5), (signal.SIGKILL, 3)]:
                try:
                    # WNOWAIT keeps a child identity reserved until after signaling.
                    os.waitid(os.P_PGID, p.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
                except ChildProcessError:
                    complete = True; break
                try:
                    os.killpg(p.pid, sig); signals.append(sig.name)
                except ProcessLookupError:
                    pass
                deadline = time.monotonic() + grace
                while time.monotonic() < deadline:
                    try:
                        pid, status, usage = os.wait4(-p.pid, os.WNOHANG)
                    except ChildProcessError:
                        complete = True; break
                    if pid:
                        rc = os.waitstatus_to_exitcode(status)
                        if pid == p.pid: p.returncode = rc
                        records.append({'pid': pid, 'returncode': rc,
                                        'cpu_seconds': usage.ru_utime + usage.ru_stime,
                                        'peak_rss_kib': usage.ru_maxrss})
                    else:
                        time.sleep(.05)
                if complete: break
            results.append({'name': name, 'group': p.pid, 'command': command,
                            'signals': signals, 'reaped': records, 'complete': complete,
                            'seconds': time.monotonic() - start})
        return results


def yaw(q):
    return math.atan2(2 * (q.w*q.z + q.x*q.y), 1 - 2*(q.y*q.y + q.z*q.z))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--label', required=True)
    parser.add_argument('--gui', action='store_true')
    parser.add_argument('--hold', type=float, default=30)
    parser.add_argument('--debug-nav', action='store_true', help='Diagnostic GDB child wrappers; not a performance run')
    args = parser.parse_args()
    if not re.fullmatch('[a-z0-9-]+', args.label): raise ValueError('Invalid label')
    report_path = BASE / f'{args.label}.json'
    if report_path.exists(): raise FileExistsError(report_path)
    runtime = BASE / 'runtime' / args.label; runtime.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env.update(ROS_DOMAIN_ID=env.get('ROS_DOMAIN_ID','139'), ROS_LOCALHOST_ONLY='1',
               ROS_HOME=str(runtime / 'ros'), ROS_LOG_DIR=str(runtime / 'ros-log'),
               IGN_PARTITION=f'urp_nav_{os.getpid()}', IGN_HOMEDIR=str(runtime / 'ignition'),
               IGN_FUEL_CACHE_PATH=str(BASE.parent / 'cache/ignition-fuel'))
    Path(env['IGN_HOMEDIR']).mkdir(parents=True)
    os.environ.update({k:env[k] for k in ('ROS_DOMAIN_ID','ROS_LOCALHOST_ONLY','ROS_HOME','ROS_LOG_DIR')})
    manager = OwnedProcesses(env, args.label)
    report = {'label': args.label, 'gui': args.gui, 'official_world': 'maze',
              'rmw_implementation': env.get('RMW_IMPLEMENTATION','rmw_fastrtps_cpp'),
              'ros_domain_id':env['ROS_DOMAIN_ID'],
              'official_map': '/opt/ros/humble/share/turtlebot4_navigation/maps/maze.yaml',
              'algorithm_scope': 'Official Nav2 NavFn + DWB; no URP research solver',
              'status': 'INCOMPLETE', 'goals': [], 'stages': [], 'errors': []}
    source = Path(__file__).read_bytes()
    (BASE/'logs'/f'{args.label}-harness.py').write_bytes(source)
    report['harness_sha256'] = hashlib.sha256(source).hexdigest()
    start = time.monotonic()
    counts = dict(clock=0, odom=0, scan=0, ground_truth=0, amcl=0, plan=0, cmd_vel=0, dock=0)
    latest = {}; last_at = {}; ground_frames = set(); actions = []; active_goals = []
    def stage(name):
        report['stages'].append({'name': name, 'wall_seconds': time.monotonic()-start})
        print(name, flush=True)
    rclpy.init()
    node = rclpy.create_node('urp_nav_validation', parameter_overrides=[Parameter('use_sim_time', value=True)])
    tf_buffer = Buffer(node=node)
    tf_listener = TransformListener(tf_buffer,node)
    subscriptions = []
    def observe(name):
        def callback(msg):
            counts[name] += 1; latest[name] = msg; last_at[name] = time.monotonic()
        return callback
    for name, cls, topic in [('clock',Clock,'/clock'),('odom',Odometry,'/odom'),
                             ('scan',LaserScan,'/scan'),('plan',NavPath,'/plan'),
                             ('cmd_vel',Twist,'/cmd_vel'),('dock',DockStatus,'/dock_status')]:
        subscriptions.append(node.create_subscription(cls, topic, observe(name), qos_profile_sensor_data))
    def gt(msg):
        for t in msg.transforms:
            ground_frames.add(t.child_frame_id)
            if t.child_frame_id == 'turtlebot4': observe('ground_truth')(t)
    subscriptions.append(node.create_subscription(TFMessage, '/urp_ground_truth', gt, qos_profile_sensor_data))
    amcl_qos = QoSProfile(depth=1, reliability=ReliabilityPolicy.RELIABLE, durability=DurabilityPolicy.TRANSIENT_LOCAL)
    subscriptions.append(node.create_subscription(PoseWithCovarianceStamped, '/amcl_pose', observe('amcl'), amcl_qos))
    initial_pub = node.create_publisher(PoseWithCovarianceStamped, '/initialpose', 1)
    def spin_until(condition, seconds, description):
        end = time.monotonic()+seconds
        while time.monotonic() < end:
            rclpy.spin_once(node, timeout_sec=.05)
            if condition(): return
            if time.monotonic()-manager.last_sample>=1:
                manager.sample(); manager.last_sample=time.monotonic()
        raise TimeoutError(description)
    def result(future, seconds=20):
        spin_until(future.done, seconds, 'ROS response timeout')
        return future.result()
    def action(cls, topic, goal, timeout):
        client = ActionClient(node, cls, topic); actions.append(client)
        spin_until(client.server_is_ready, 30, f'{topic} not available')
        handle = result(client.send_goal_async(goal))
        if not handle.accepted: raise RuntimeError(f'{topic} rejected')
        reply = result(handle.get_result_async(), timeout)
        return reply
    def position():
        t = latest.get('ground_truth'); a = latest.get('amcl')
        out = {}
        if t: out['ground_truth'] = [t.transform.translation.x,t.transform.translation.y,yaw(t.transform.rotation)]
        if a: out['amcl'] = [a.pose.pose.position.x,a.pose.pose.position.y,yaw(a.pose.pose.orientation)]
        try:
            t=tf_buffer.lookup_transform('map','base_link',rclpy.time.Time()).transform
            out['localized_tf']=[t.translation.x,t.translation.y,yaw(t.rotation)]
        except TransformException:
            pass
        return out
    try:
        command = ['ros2','launch','turtlebot4_ignition_bringup','turtlebot4_ignition.launch.py',
                   'world:=maze','rviz:=false','nav2:=false','localization:=false','slam:=false']
        # Keep the official server independent of GUI startup/shutdown.
        command.append('gz_args:=maze.sdf -s -r -v 3')
        log = manager.start('sim', command); stage('sim-started')
        manager.start('truth', ['ros2','run','ros_gz_bridge','parameter_bridge',
                               '/world/maze/dynamic_pose/info@tf2_msgs/msg/TFMessage[ignition.msgs.Pose_V',
                               '--ros-args','-r','/world/maze/dynamic_pose/info:=/urp_ground_truth'])
        def spawner_ready():
            text = re.sub(r'\x1b\[[0-9;]*m', '', log.read_text(errors='replace'))
            if 'process has died' in text:
                raise RuntimeError('Official simulator process exited during startup; see sim log')
            return any('Configured and activated' in line and 'diffdrive_controller' in line for line in text.splitlines())
        spin_until(lambda: spawner_ready() and all(counts[k] for k in ['clock','scan','odom']), 65, 'controller/sensor readiness')
        client = node.create_client(ListControllers,'/controller_manager/list_controllers')
        spin_until(client.service_is_ready, 5, 'controller service')
        controllers = result(client.call_async(ListControllers.Request()),10)
        report['controllers'] = {c.name:c.state for c in controllers.controller}
        if report['controllers'].get('diffdrive_controller') != 'active': raise RuntimeError('controller not active')
        stage('controllers-and-sensors-ready')
        if args.gui:
            share=Path('/opt/ros/humble/share')
            env['IGN_GUI_PLUGIN_PATH']=':'.join(str(share/pkg/'lib') for pkg in ['turtlebot4_ignition_gui_plugins','irobot_create_ignition_plugins'])
            env['IGN_GAZEBO_RESOURCE_PATH']=':'.join([str(share/'turtlebot4_ignition_bringup/worlds'),str(share/'irobot_create_ignition_bringup/worlds'),str(share)])
            manager.start('gui',['ign','gazebo','-g','-v','3','--gui-config',str(share/'turtlebot4_ignition_bringup/gui/standard/gui.config')])
            stage('gui-started')
        spin_until(lambda: counts['dock']>=2 and latest['dock'].is_docked,15,'initial dock state')
        report['undock_status'] = action(Undock,'/undock',Undock.Goal(),45).status
        if report['undock_status'] != GoalStatus.STATUS_SUCCEEDED: raise RuntimeError('undock failed')
        stage('undocked')
        spin_until(lambda: counts['ground_truth'] > 0, 8, f'ground truth unavailable: {sorted(ground_frames)}')
        manager.start('localization',['ros2','launch','turtlebot4_navigation','localization.launch.py',
                                     'use_sim_time:=true','map:='+report['official_map']])
        spin_until(lambda: initial_pub.get_subscription_count()>0, 30, 'initialpose subscriber')
        end = time.monotonic()+35; next_publish = 0
        while not counts['amcl'] and time.monotonic()<end:
            if time.monotonic() >= next_publish:
                msg = PoseWithCovarianceStamped(); msg.header.frame_id='map'; msg.header.stamp=node.get_clock().now().to_msg()
                t=latest['ground_truth'].transform
                msg.pose.pose.position.x=t.translation.x; msg.pose.pose.position.y=t.translation.y; msg.pose.pose.orientation=t.rotation
                msg.pose.covariance[0]=.05; msg.pose.covariance[7]=.05; msg.pose.covariance[35]=.05
                initial_pub.publish(msg); next_publish=time.monotonic()+1
            rclpy.spin_once(node,timeout_sec=.1)
        if not counts['amcl']: raise TimeoutError('AMCL pose')
        report['initial_position']=position(); stage('localized')
        nav_command=['ros2','launch','turtlebot4_navigation','nav2.launch.py','use_sim_time:=true']
        if args.debug_nav:
            nav_command=['ros2','launch',str(BASE/'navigation-debug.launch.py'),
                         'use_sim_time:=true','params_file:=/opt/ros/humble/share/turtlebot4_navigation/config/nav2.yaml']
        nav_log = manager.start('nav',nav_command)
        nav = ActionClient(node,NavigateToPose,'/navigate_to_pose'); actions.append(nav)
        spin_until(nav.server_is_ready, 45, 'Nav2 action server')
        spin_until(lambda:'Managed nodes are active' in nav_log.read_text(errors='replace'), 60, 'Nav2 lifecycle activation')
        stage('nav2-ready')
        report['node_clock_parameters'] = {}
        for name in ('controller_server','local_costmap/local_costmap','planner_server','amcl'):
            c=node.create_client(GetParameters,'/'+name+'/get_parameters')
            spin_until(c.service_is_ready,5,'parameter service '+name)
            q=GetParameters.Request();q.names=['use_sim_time']
            report['node_clock_parameters'][name]=[v.bool_value for v in result(c.call_async(q),5).values]
            node.destroy_client(c)
        def navigate(x,y,heading,cancel=False):
            target = NavigateToPose.Goal(); target.pose=PoseStamped(); target.pose.header.frame_id='map'
            # A map-frame destination is time independent; ask TF for the latest transform.
            target.pose.pose.position.x=float(x); target.pose.pose.position.y=float(y)
            target.pose.pose.orientation.z=math.sin(heading/2); target.pose.pose.orientation.w=math.cos(heading/2)
            began=time.monotonic(); before=counts.copy(); feedback=[]
            handle=result(nav.send_goal_async(target, feedback_callback=lambda m: feedback.append(m.feedback.distance_remaining)))
            if not handle.accepted: raise RuntimeError('Nav2 rejected target')
            future=handle.get_result_async()
            active_goals.append((handle,future))
            row={'target':[x,y,heading], 'cancel_requested':cancel}; report['goals'].append(row)
            if cancel:
                spin_until(lambda: (counts['plan']>before['plan'] and len(feedback)>2 and time.monotonic()-began>=1) or future.done(),15,'cancellation goal planned')
                if future.done(): raise RuntimeError('goal finished before cancellation')
                cancel_reply=result(handle.cancel_goal_async(),10)
                row['cancel_accepted']=bool(cancel_reply.goals_canceling)
            if not cancel:
                spin_until(lambda:len(feedback)>10 or future.done(),10,'navigation feedback')
            try:
                reply=result(future,60 if not cancel else 15)
            except Exception:
                row.update(position=position(),wall_seconds=time.monotonic()-began,
                           new_plan_messages=counts['plan']-before['plan'],new_velocity_messages=counts['cmd_vel']-before['cmd_vel'])
                raise
            row.update(status=reply.status,wall_seconds=time.monotonic()-began,position=position(),
                       last_amcl_update_age_seconds=time.monotonic()-last_at.get('amcl',start),
                       new_plan_messages=counts['plan']-before['plan'],new_velocity_messages=counts['cmd_vel']-before['cmd_vel'],
                       feedback_count=len(feedback), last_feedback_distance=feedback[-1] if feedback else None)
            for source, p in row['position'].items():
                row[source+'_distance_error_m']=math.hypot(p[0]-x,p[1]-y)
                row[source+'_yaw_error_rad']=abs(math.atan2(math.sin(p[2]-heading), math.cos(p[2]-heading)))
            expected=GoalStatus.STATUS_CANCELED if cancel else GoalStatus.STATUS_SUCCEEDED
            if reply.status!=expected: raise RuntimeError(f'Nav2 status {reply.status}, expected {expected}')
            if not cancel and row.get('ground_truth_distance_error_m',math.inf)>.35:
                raise RuntimeError('Actual arrival error exceeds 0.35 m')
            stage('navigation-canceled' if cancel else 'navigation-succeeded')
        navigate(-1.5,0,math.pi)
        navigate(-4.,0,math.pi,cancel=True)
        before=counts.copy(); clock_before=latest['clock'].clock
        observation_start=time.monotonic()
        spin_until(lambda:time.monotonic()-observation_start>=args.hold,args.hold+2,'sustained observation')
        clock_after=latest['clock'].clock
        report['observation']={'wall_seconds':time.monotonic()-observation_start,
            'simulation_seconds':clock_after.sec-clock_before.sec+(clock_after.nanosec-clock_before.nanosec)/1e9,
            'messages':{k:counts[k]-before[k] for k in counts},
            'age_seconds':{k:time.monotonic()-v for k,v in last_at.items()}}
        report['observation']['final_odometry_speed_m_s']=math.hypot(latest['odom'].twist.twist.linear.x,latest['odom'].twist.twist.linear.y)
        report['observation']['final_odometry_yaw_rate_rad_s']=abs(latest['odom'].twist.twist.angular.z)
        if any(report['observation']['age_seconds'].get(k,math.inf)>2 for k in ['clock','odom','scan','ground_truth']):
            raise RuntimeError('Sensor stream stalled')
        if report['observation']['final_odometry_speed_m_s']>.02 or report['observation']['final_odometry_yaw_rate_rad_s']>.02:
            raise RuntimeError('Robot did not stop after cancellation')
        report['status']='PASS'; stage('observation-complete')
    except BaseException as exc:
        report['errors'].append({'type':type(exc).__name__,'message':str(exc),'traceback':traceback.format_exc()})
        print(traceback.format_exc(),flush=True)
    finally:
        report['counts']=counts; report['ground_truth_frames']=sorted(ground_frames)
        report['position_before_shutdown']=position(); report['peak_simultaneous_tree_rss_kib']=manager.peak_rss_kib
        # The installed Fortress crashes in EventManager::Emit when /server_control
        # stop is used. Signal our entire private group so the shell/ruby wrapper
        # cannot leave its server child running after the ROS launch leader exits.
        report['lifecycle_shutdown'] = {}
        for handle, future in active_goals:
            if not future.done():
                try:
                    result(handle.cancel_goal_async(),5)
                    result(future,5)
                except Exception as exc: report['errors'].append({'cancel_on_exit':str(exc)})
        # Quiesce sensor production before costmap subscriptions are destroyed.
        try:
            paused=subprocess.run(['ign','service','-s','/world/maze/control',
                '--reqtype','ignition.msgs.WorldControl','--reptype','ignition.msgs.Boolean',
                '--timeout','2000','--req','pause: true'],env=env,capture_output=True,text=True,timeout=4)
            report['pause_before_cleanup']={'returncode':paused.returncode,'stdout':paused.stdout,'stderr':paused.stderr}
        except Exception as exc:report['pause_before_cleanup']={'error':str(exc)}
        for name in ('navigation', 'localization'):
            client = node.create_client(ManageLifecycleNodes, f'/lifecycle_manager_{name}/manage_nodes')
            if client.service_is_ready():
                try:
                    request = ManageLifecycleNodes.Request(); request.command = ManageLifecycleNodes.Request.SHUTDOWN
                    report['lifecycle_shutdown'][name] = result(client.call_async(request), 12).success
                except Exception as exc:
                    report['lifecycle_shutdown'][name] = str(exc)
            node.destroy_client(client)
        for client in actions: client.destroy()
        tf_listener.unregister()
        node.destroy_node(); rclpy.shutdown()
        report['cleanup']=manager.cleanup(); report['remaining_owned_processes']=manager.sample()
        report['forced_exit_logs'] = [str(log.relative_to(BASE)) for _,_,log,_ in manager.children
                                     if 'SIGKILL' in log.read_text(errors='replace')]
        report['shutdown_quality'] = 'forced_bounded' if report['forced_exit_logs'] else 'signal_exit_no_sigkill'
        if report['status']=='PASS' and (report['forced_exit_logs'] or
                report['lifecycle_shutdown'].get('navigation') is not True or
                report['lifecycle_shutdown'].get('localization') is not True):
            report['status']='DEGRADED_SHUTDOWN'
        report['simulated_robot_only'] = True
        if not all(r['complete'] for r in report['cleanup']) or report['remaining_owned_processes']:
            report['status']='FAIL_CLEANUP'
        report['total_wall_seconds']=time.monotonic()-start
        report_path.write_text(json.dumps(report,indent=2)+'\n')
        print(json.dumps({'report':str(report_path),'status':report['status'],'counts':counts},indent=2),flush=True)
    return 0 if report['status']=='PASS' else 1


if __name__=='__main__': raise SystemExit(main())
