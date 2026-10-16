#!/usr/bin/python3
"""Owned, persistent official TB4 simulation. ROS runs only in the system 3.10 environment."""
from __future__ import annotations
import argparse
import copy
from datetime import datetime, timezone
import importlib.util
import json
import math
import os
from pathlib import Path
import queue
import re
import secrets
import signal
import subprocess
import sys
import threading
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

LAB=Path(__file__).resolve().parents[1]
ROOT=LAB.parents[1]
DEPLOY=ROOT/'setup/2026-10-15/deployment'
# Foxglove Bridge unpacked without sudo by src/lab/ros/native/install-ros-extras.sh
EXTRAS=DEPLOY/'runtime/ros-extras/root/opt/ros/humble'
# Components a session survives losing: native windows and the browser bridges.
OPTIONAL=('gui','rviz','foxglove','gazebo_web')
sys.path[:0]=[str(DEPLOY),str(LAB)]
from tf_overlay import verified_candidate, verified_gui_lifetime
from bridge_guard import verified_bridge_guard
from navigation_profile import create_profile
from urp_lab.worlds import inspect_world, CACHE
from urp_lab.process_health import unexpected_launch_exit

import rclpy
from rclpy.action import ActionClient
from rclpy.parameter import Parameter, parameter_value_to_python
from rcl_interfaces.srv import GetParameters
from rclpy.signals import SignalHandlerOptions
from rclpy.qos import qos_profile_sensor_data, QoSProfile, DurabilityPolicy, ReliabilityPolicy
from geometry_msgs.msg import PoseStamped, PoseWithCovarianceStamped, Twist, TransformStamped
from nav_msgs.msg import Odometry, OccupancyGrid, Path as NavPath
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import LaserScan
from tf2_msgs.msg import TFMessage
from tf2_ros import Buffer, TransformListener, TransformBroadcaster
from irobot_create_msgs.action import Undock
from irobot_create_msgs.msg import DockStatus
from nav2_msgs.action import NavigateToPose, FollowPath
from nav2_msgs.srv import ManageLifecycleNodes
from visualization_msgs.msg import Marker, MarkerArray

spec=importlib.util.spec_from_file_location('urp_existing_nav_smoke',DEPLOY/'nav-smoke.py')
original=importlib.util.module_from_spec(spec); spec.loader.exec_module(original)
FINAL={'succeeded','failed','canceled'}
def now(): return datetime.now(timezone.utc).isoformat()
def yaw(q): return math.atan2(2*(q.w*q.z+q.x*q.y),1-2*(q.y*q.y+q.z*q.z))
def stamp(t): return t.sec+t.nanosec/1e9
def save(path,obj):
    tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False)); tmp.replace(path)

class Interrupted(Exception): pass

class Processes(original.OwnedProcesses):
    def __init__(self, env, runtime):
        super().__init__(env,'session'); self.runtime=runtime
    def start(self,name,command,extra_env=None):
        count=sum(n==name for n,_,_,_ in self.children)
        path=self.runtime/'logs'/f'{name}{"-"+str(count) if count else ""}.log'
        with path.open('x') as stream:
            p=subprocess.Popen(command,stdout=stream,stderr=subprocess.STDOUT,env={**self.env,**(extra_env or {})},start_new_session=True)
        self.children.append((name,p,path,command)); return path

class Session:
    def __init__(self,args):
        self.args=args; self.runtime=Path(args.runtime); (self.runtime/'logs').mkdir(parents=True,exist_ok=True); (self.runtime/'runs').mkdir(exist_ok=True)
        self.lock=threading.RLock(); self.stop=threading.Event(); self.cancel=threading.Event(); self.commands=queue.Queue()
        self.shutting=False; self.started=time.monotonic(); self.execution=None; self.runs={}; self.goal=None
        self.st=dict(session_id=args.session_id,phase='starting',world=args.world,spawn=args.spawn,components={},robot=None,
                     execution=None,errors=[],warnings=[],stages=[],web={},known_issues=['parameter_bridge 退出时堆损坏（上游问题）；退出垫片以 main 的返回码直接退出来绕开，URP_BRIDGE_FIX=0 可关闭。'])
        self.env=dict(os.environ,ROS_HOME=str(self.runtime/'ros'),ROS_LOG_DIR=str(self.runtime/'ros-log'),
                      IGN_PARTITION='urp_'+args.session_id,IGN_HOMEDIR=str(self.runtime/'ignition'),IGN_FUEL_CACHE_PATH=str(CACHE))
        Path(self.env['IGN_HOMEDIR']).mkdir(exist_ok=True)
        os.environ.update({k:self.env[k] for k in ('ROS_HOME','ROS_LOG_DIR')})
        self.processes=Processes(self.env,self.runtime)
        self.tf_fix=self.option('URP_TF_FIX',verified_candidate)
        self.gui_fix=self.option('URP_GUI_FIX',verified_gui_lifetime)
        self.bridge_fix=self.option('URP_BRIDGE_FIX',verified_bridge_guard)
        self.report=dict(session_id=args.session_id,started_utc=now(),world=args.world,spawn=args.spawn,errors=[],
                         compatibility={k:str(v) if v else None for k,v in [('tf',self.tf_fix),('gui',self.gui_fix),('bridge_exit',self.bridge_fix)]})
        self.report['navigation_profile']=create_profile(self.runtime,args.localization)
        self.st['localization']=args.localization
        self.counts={}; self.latest={}; self.at={}; self.last_sample=0.; self.last_trace=0.; self.subs=[]; self.actions=[]
        self.log_offsets={}; self.log_fragments={}
        rclpy.init(signal_handler_options=SignalHandlerOptions.NO)
        self.node=rclpy.create_node('workbench_sim_session',parameter_overrides=[Parameter('use_sim_time',value=True)])
        self.buffer=Buffer(node=self.node); self.listener=TransformListener(self.buffer,self.node)
        self.ideal_tf=TransformBroadcaster(self.node) if args.localization=='ground_truth' else None
        qos=QoSProfile(depth=1,reliability=ReliabilityPolicy.RELIABLE,durability=DurabilityPolicy.TRANSIENT_LOCAL)
        for key,typ,topic in [('clock',Clock,'/clock'),('odom',Odometry,'/odom'),('scan',LaserScan,'/scan'),
                              ('cmd_vel',Twist,'/cmd_vel'),('dock',DockStatus,'/dock_status'),('nav2_plan',NavPath,'/plan'),
                              ('local_map',OccupancyGrid,'/local_costmap/costmap'),('global_map',OccupancyGrid,'/global_costmap/costmap'),
                              ('amcl',PoseWithCovarianceStamped,'/amcl_pose')]:
            self.subs.append(self.node.create_subscription(typ,topic,lambda msg,k=key:self.observe(k,msg),qos if key in ('amcl','local_map','global_map') else qos_profile_sensor_data))
        self.subs.append(self.node.create_subscription(TFMessage,'/ground_truth/poses',self.truth,qos_profile_sensor_data))
        self.initial=self.node.create_publisher(PoseWithCovarianceStamped,'/initialpose',1)
        self.cmd=self.node.create_publisher(Twist,'/cmd_vel',10)
        self.plan_pub=self.node.create_publisher(NavPath,'/workbench/planned_path',qos)
        self.actual_pub=self.node.create_publisher(NavPath,'/workbench/actual_path',qos)
        self.task_pub=self.node.create_publisher(MarkerArray,'/workbench/tasks',qos)
        self.text_pub=self.node.create_publisher(Marker,'/workbench/status_text',qos)

    def option(self,key,fn):
        val=os.environ.get(key,'1')
        if val not in ('0','1'): raise ValueError(f'{key} 必须为 0/1')
        return fn() if val=='1' else None

    def observe(self,key,msg):
        self.counts[key]=self.counts.get(key,0)+1; self.latest[key]=msg; self.at[key]=time.monotonic()
        if key=='amcl' and self.execution and self.execution['state'] not in FINAL:
            p=msg.pose.pose
            self.execution['actual']['amcl'].append([stamp(msg.header.stamp),p.position.x,p.position.y,yaw(p.orientation)])
        if key=='nav2_plan' and self.execution and self.execution['state'] not in FINAL:
            self.execution.setdefault('nav2_plans',[]).append(dict(t_sim=self.sim_time(),phase=self.execution['state'],path=[[p.pose.position.x,p.pose.position.y] for p in msg.poses]))

    def sim_time(self):
        return stamp(self.latest['clock'].clock) if 'clock' in self.latest else 0.

    def truth(self,msg):
        for t in msg.transforms:
            if t.child_frame_id=='turtlebot4': self.observe('ground_truth',t)
        if 'ground_truth' not in self.latest:return
        t=self.latest['ground_truth'].transform; pos=[t.translation.x,t.translation.y,yaw(t.rotation)]
        amcl=self.latest.get('amcl'); estimate=None
        if amcl:
            p=amcl.pose.pose; estimate=[p.position.x,p.position.y,yaw(p.orientation)]
        odom=self.latest.get('odom'); speed=math.hypot(odom.twist.twist.linear.x,odom.twist.twist.linear.y) if odom else None
        self.st['robot']=dict(t_sim=self.sim_time(),ground_truth=pos,amcl=estimate,speed=speed)
        if odom:
            p=odom.pose.pose
            self.st['robot']['odom']=[stamp(odom.header.stamp),p.position.x,p.position.y,yaw(p.orientation)]
            if self.ideal_tf:
                # T_map_odom = T_world_base * inverse(T_odom_base), with world=map.
                # Explicit ideal localization experiment; never fed back into AMCL.
                a=pos[2]-yaw(p.orientation)
                msg=TransformStamped();msg.header.frame_id='map';msg.child_frame_id='odom';msg.header.stamp=odom.header.stamp
                msg.transform.translation.x=pos[0]-(math.cos(a)*p.position.x-math.sin(a)*p.position.y)
                msg.transform.translation.y=pos[1]-(math.sin(a)*p.position.x+math.cos(a)*p.position.y)
                msg.transform.rotation.z=math.sin(a/2);msg.transform.rotation.w=math.cos(a/2)
                self.ideal_tf.sendTransform(msg)
        try:
            tf=self.buffer.lookup_transform('map','base_link',rclpy.time.Time())
            p=tf.transform
            self.st['robot']['localized']=[stamp(tf.header.stamp),p.translation.x,p.translation.y,yaw(p.rotation)]
        except Exception: pass
        if self.execution and self.execution['state'] not in FINAL and time.monotonic()-self.last_trace>=.1:
            ex=self.execution; sample=[self.sim_time(),*pos]; ex['actual']['ground_truth'].append(sample)
            (ex['approach_trajectory'] if ex['state']=='approach' else ex['tracking_trajectory']).append(sample)
            self.last_trace=time.monotonic()
            if ex['state']=='executing':
                task=next((t for t in ex['tasks'] if t['state']=='pending'),None)
                if task:
                    dist=math.dist(pos[:2],task['xy'])
                    if dist<=ex['task_radius_m']: task.update(state='reached',t_sim=self.sim_time(),distance_m=dist)
            ex['metrics']['tasks_reached']=sum(t['state']=='reached' for t in ex['tasks'])
            self.actual_pub.publish(self.path_msg([s[1:3] for s in ex['actual']['ground_truth']]))
            self.markers()

    def phase(self,phase):
        self.st['phase']=phase; self.st['stages'].append(dict(name=phase,wall_s=round(time.monotonic()-self.started,3)));print(phase,flush=True)

    def state(self):
        with self.lock:
            st=copy.deepcopy(self.st); st['execution']=copy.deepcopy(self.execution)
            st['telemetry']=dict(counts=dict(self.counts),age_s={k:round(time.monotonic()-v,3) for k,v in self.at.items()})
            st['telemetry']['map_base_tf_age_s']=self.tf_age
            return st

    tf_age=None
    def spin(self,seconds=.05,allow_stop=False):
        rclpy.spin_once(self.node,timeout_sec=seconds)
        if not self.shutting and self.stop.is_set() and not allow_stop:raise Interrupted('会话停止请求')
        if time.monotonic()-self.last_sample>=1:
            self.processes.sample(); self.last_sample=time.monotonic()
            if not self.shutting:
                for name,proc,log,_ in self.processes.children:
                    ended=os.waitid(os.P_PID,proc.pid,os.WEXITED|os.WNOHANG|os.WNOWAIT)
                    if ended:
                        if name in OPTIONAL:
                            self.st['components'][name]='failed'
                            warning=f'{name} 进程已退出，状态 {ended.si_status}；见组件日志'
                            if warning not in self.st['warnings']:self.st['warnings'].append(warning)
                        else:raise RuntimeError(f'关键服务 {name} 意外退出，状态 {ended.si_status}')
                    if name in ('sim','nav','localization','truth'):
                        # Launch can stay alive after one of its required nodes
                        # dies. Report that failure instead of leaving "ready".
                        with log.open('rb') as stream:
                            stream.seek(self.log_offsets.get(str(log),0))
                            fresh=stream.read();self.log_offsets[str(log)]=stream.tell()
                        data=self.log_fragments.get(str(log),'')+fresh.decode(errors='replace')
                        complete,_,partial=data.rpartition('\n');self.log_fragments[str(log)]=partial
                        bad=unexpected_launch_exit(name,complete)
                        if bad:raise RuntimeError(f'{name} 的子节点意外退出：{bad}；详见 {log.name}')
            try:
                t=self.buffer.lookup_transform('map','base_link',rclpy.time.Time())
                self.tf_age=self.sim_time()-stamp(t.header.stamp)
            except Exception: self.tf_age=None

    def wait(self,condition,seconds,label,allow_cancel=False):
        end=time.monotonic()+seconds
        while time.monotonic()<end:
            self.spin()
            if condition():return
            if allow_cancel and self.cancel.is_set():raise Interrupted('执行取消请求')
        raise TimeoutError(label)

    def future(self,f,seconds=15):
        self.wait(f.done,seconds,'ROS 响应超时');return f.result()

    def action(self,typ,topic,goal,seconds,record=True):
        client=ActionClient(self.node,typ,topic);self.actions.append(client)
        self.wait(client.server_is_ready,25,f'{topic} 动作服务不可用')
        feedback=[]
        handle=self.future(client.send_goal_async(goal,feedback_callback=lambda m:feedback.append(str(m.feedback))))
        if not handle.accepted:raise RuntimeError(f'{topic} 拒绝目标')
        future=handle.get_result_async();self.goal=(handle,future);end=time.monotonic()+seconds;cancel_sent=False;cancel_time=None
        while not future.done():
            if (self.cancel.is_set() or self.stop.is_set() or time.monotonic()>end) and not cancel_sent:
                response=self.future(handle.cancel_goal_async(),8);cancel_sent=True;cancel_time=time.monotonic()
                if not response.goals_canceling:raise RuntimeError(f'{topic} 未确认取消')
            if cancel_sent and time.monotonic()-cancel_time>12:raise TimeoutError('动作取消未收敛')
            # Shutdown is checked here so cancellation can complete before shutdown begins.
            self.spin(allow_stop=True)
            if not self.shutting and not cancel_sent and topic in ('/follow_path','/navigate_to_pose'):
                if any(time.monotonic()-self.at.get(k,0)>3 for k in ('clock','scan','odom','ground_truth')):
                    raise RuntimeError('执行中传感器/时钟数据超时')
        reply=future.result();self.goal=None
        if record and self.execution:
            self.execution['nav2'].append(dict(action=topic,status=reply.status,status_text={4:'SUCCEEDED',5:'CANCELED',6:'ABORTED'}.get(reply.status,str(reply.status)),t_sim=self.sim_time(),feedback_count=len(feedback),cancel_accepted=cancel_sent))
        if self.stop.is_set() or self.cancel.is_set():raise Interrupted('会话停止请求' if self.stop.is_set() else '执行取消请求')
        if time.monotonic()>end:raise TimeoutError(f'{topic} 执行预算耗尽')
        if reply.status!=4:raise RuntimeError(f'{topic} 状态 {reply.status}，未到达')
        return reply

    def startup(self):
        assets=inspect_world(self.args.world);save(self.runtime/'world-assets.json',assets);self.report['assets']=assets
        if not assets['complete']:raise RuntimeError('世界依赖缺失：'+'; '.join(assets['missing']))
        s=self.args.spawn;world=self.args.world
        command=['ros2','launch','turtlebot4_ignition_bringup','turtlebot4_ignition.launch.py',f'world:={world}',
                 'rviz:=false','nav2:=false','localization:=false','slam:=false',f'x:={s["x"]}',f'y:={s["y"]}',f'yaw:={s["yaw"]}',f'gz_args:={world}.sdf -s -r -v 3']
        bridge_env={'LD_PRELOAD':str(self.bridge_fix)} if self.bridge_fix else {}
        log=self.processes.start('sim',command,bridge_env);self.st['components']['sim']='running'
        topic=f'/world/{world}/dynamic_pose/info'
        self.processes.start('truth',['ros2','run','ros_gz_bridge','parameter_bridge',topic+'@tf2_msgs/msg/TFMessage[ignition.msgs.Pose_V','--ros-args','-r',topic+':=/ground_truth/poses'],bridge_env)
        def ready():
            txt=log.read_text(errors='replace')
            if 'process has died' in txt or 'Unable to find uri' in txt:raise RuntimeError('官方仿真启动错误，详见 sim.log')
            return 'Configured and activated' in txt and all(self.counts.get(k,0)>2 for k in ('clock','odom','scan','dock','ground_truth'))
        self.wait(ready,90,'控制器/传感器未就绪')
        if self.args.web:self.web_bridges()
        self.wait(lambda:self.latest['dock'].is_docked,15,'初始充电座状态不可用')
        self.phase('undocking');self.action(Undock,'/undock',Undock.Goal(),50,False)
        self.phase('localizing')
        tf_env={'LD_PRELOAD':str(self.tf_fix)} if self.tf_fix else {}
        self.processes.start('localization',['ros2','launch','turtlebot4_navigation','localization.launch.py','use_sim_time:=true',f'map:=/opt/ros/humble/share/turtlebot4_navigation/maps/{world}.yaml',f'params:={self.runtime}/localization.yaml'],tf_env)
        self.wait(lambda:self.initial.get_subscription_count()>0,30,'initialpose 订阅者不可用')
        end=time.monotonic()+40;next_pub=0
        while not self.counts.get('amcl') and time.monotonic()<end:
            if time.monotonic()>next_pub:
                t=self.latest['ground_truth'].transform;m=PoseWithCovarianceStamped();m.header.frame_id='map';m.header.stamp=self.node.get_clock().now().to_msg()
                m.pose.pose.position.x=t.translation.x;m.pose.pose.position.y=t.translation.y;m.pose.pose.orientation=t.rotation
                m.pose.covariance[0]=m.pose.covariance[7]=m.pose.covariance[35]=.0025
                self.initial.publish(m);next_pub=time.monotonic()+1
            self.spin()
        if not self.counts.get('amcl'):raise TimeoutError('AMCL 初始定位超时')
        self.verify_parameters('amcl',{'tf_broadcast':self.args.localization=='amcl','max_beams':180,'alpha1':.02})
        self.st['components']['localization']='active';self.phase('nav2_starting')
        nav=self.processes.start('nav',['ros2','launch','turtlebot4_navigation','nav2.launch.py','use_sim_time:=true',f'params_file:={self.runtime}/nav2.yaml'],tf_env)
        self.wait(lambda:'Managed nodes are active' in nav.read_text(errors='replace'),70,'Nav2 生命周期未激活')
        self.verify_parameters('controller_server',{'general_goal_checker.xy_goal_tolerance':.06,'FollowCoverage.lookahead_dist':.18})
        self.wait(lambda:all(self.counts.get(k) for k in ('global_map','local_map')) and self.tf_age is not None and abs(self.tf_age)<2,20,'代价地图/TF 未就绪')
        self.st['components']['nav2']='active'
        for k in ('gui','rviz'): self.st['components'][k]='off'
        if self.args.gui:self.window('gui',True)
        if self.args.rviz:self.window('rviz',True)
        self.report['initial_state']=self.state();self.phase('ready')

    def verify_parameters(self,node,expected):
        client=self.node.create_client(GetParameters,'/'+node+'/get_parameters')
        self.wait(client.service_is_ready,15,f'{node} 参数服务未就绪')
        future=client.call_async(GetParameters.Request(names=list(expected)))
        self.wait(future.done,10,f'{node} 参数读取超时')
        values=[parameter_value_to_python(v) for v in future.result().values]
        actual=dict(zip(expected,values));self.report.setdefault('effective_parameters',{})[node]=actual
        self.node.destroy_client(client)
        if actual!=expected:raise RuntimeError(f'{node} 实际参数未应用：{actual} != {expected}')

    def web_bridges(self):
        """Browser views of the live simulation: Foxglove Bridge streams ROS 2 topics (map, scan, TF,
        Nav2 plans, robot_description) and the Gazebo WebSocket server streams the scene for gzweb."""
        fox=EXTRAS/'lib/foxglove_bridge/foxglove_bridge'
        if fox.exists():
            env={'LD_LIBRARY_PATH':':'.join(filter(None,[str(EXTRAS/'lib'),self.env.get('LD_LIBRARY_PATH')])),
                 'AMENT_PREFIX_PATH':':'.join(filter(None,[str(EXTRAS),self.env.get('AMENT_PREFIX_PATH')]))}
            port=self.args.foxglove_port
            self.processes.start('foxglove',[str(fox),'--ros-args','-p',f'port:={port}','-p','address:=127.0.0.1','-p','use_sim_time:=true'],env)
            self.st['components']['foxglove']='running';self.st['web']['ros']={'url':f'ws://127.0.0.1:{port}','protocol':'foxglove.sdk.v1'}
        else:
            self.st['warnings'].append('Foxglove Bridge 未安装，浏览器里的 ROS 视图不可用：bash src/lab/ros/native/install-ros-extras.sh')
        key=secrets.token_hex(16);port=self.args.gazebo_web_port
        cfg=self.runtime/'gazebo-web.ign'
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
        share=Path('/opt/ros/humble/share')
        paths=':'.join([str(share/'turtlebot4_ignition_bringup/worlds'),str(share/'irobot_create_ignition_bringup/worlds'),str(share)])
        self.processes.start('gazebo_web',['ign','launch','-v','3',str(cfg)],{'IGN_GAZEBO_RESOURCE_PATH':paths,'GZ_SIM_RESOURCE_PATH':paths,'IGN_FILE_PATH':paths})
        self.st['components']['gazebo_web']='running';self.st['web']['gazebo']={'url':f'ws://127.0.0.1:{port}','key':key,'world':self.args.world}

    def window(self,key,on):
        if key not in ('gui','rviz'):raise ValueError('窗口类型无效')
        if not on:
            # Preserve the same owned-process cleanup semantics for a window toggle.
            chosen=[r for r in self.processes.children if r[0]==key]
            if chosen:
                all_children=self.processes.children;self.processes.children=chosen
                self.report.setdefault('window_cleanup',[]).extend(self.processes.cleanup());self.processes.children=[r for r in all_children if r not in chosen]
            self.st['components'][key]='off';return
        if self.st['components'].get(key)=='running':return
        extra={'LD_PRELOAD':str(self.gui_fix)} if self.gui_fix else {}
        share=Path('/opt/ros/humble/share')
        if key=='gui':
            extra['IGN_GUI_PLUGIN_PATH']=':'.join(str(share/p/'lib') for p in ('turtlebot4_ignition_gui_plugins','irobot_create_ignition_plugins'))
            extra['IGN_GAZEBO_RESOURCE_PATH']=':'.join([str(share/'turtlebot4_ignition_bringup/worlds'),str(share/'irobot_create_ignition_bringup/worlds'),str(share)])
            command=['ign','gazebo','-g','-v','3','--gui-config',str(share/'turtlebot4_ignition_bringup/gui/standard/gui.config')]
        else:
            if self.tf_fix:extra['LD_PRELOAD']=':'.join(filter(None,[str(self.tf_fix),extra.get('LD_PRELOAD')]))
            command=['rviz2','-d',str(LAB/'ros/workbench.rviz'),'--ros-args','-p','use_sim_time:=true']
        self.processes.start(key,command,extra);self.st['components'][key]='running'

    def path_msg(self,pts):
        msg=NavPath();msg.header.frame_id='map';msg.header.stamp=self.node.get_clock().now().to_msg()
        for i,p in enumerate(pts):
            q=pts[min(i+1,len(pts)-1)];a=math.atan2(q[1]-p[1],q[0]-p[0]) if q!=p else (math.atan2(p[1]-pts[i-1][1],p[0]-pts[i-1][0]) if i else 0)
            pose=PoseStamped();pose.header=msg.header;pose.pose.position.x=float(p[0]);pose.pose.position.y=float(p[1]);pose.pose.orientation.z=math.sin(a/2);pose.pose.orientation.w=math.cos(a/2);msg.poses.append(pose)
        return msg

    def markers(self):
        if not self.execution:return
        arr=MarkerArray()
        for i,t in enumerate(self.execution['tasks']):
            m=Marker();m.header.frame_id='map';m.ns='tasks';m.id=i;m.type=Marker.SPHERE;m.action=Marker.ADD
            m.pose.position.x=float(t['xy'][0]);m.pose.position.y=float(t['xy'][1]);m.pose.position.z=.15;m.pose.orientation.w=1.;m.scale.x=m.scale.y=m.scale.z=.2
            m.color.a=1.;m.color.g=1. if t['state']=='reached' else .3;m.color.r=.2 if t['state']=='reached' else 1.;arr.markers.append(m)
            label=copy.deepcopy(m);label.ns='task_labels';label.type=Marker.TEXT_VIEW_FACING
            label.text=t['label'];label.pose.position.z=.45;label.scale.z=.18;arr.markers.append(label)
        self.task_pub.publish(arr)
        status=Marker();status.header.frame_id='map';status.ns='status';status.id=0;status.type=Marker.TEXT_VIEW_FACING
        status.pose.position.z=1.;status.pose.orientation.w=1.;status.scale.z=.2;status.color.a=1.;status.color.r=status.color.g=status.color.b=1.
        status.text=f"{self.execution['mode']} · {self.execution['state']} · {sum(t['state']=='reached' for t in self.execution['tasks'])}/{len(self.execution['tasks'])}"
        self.text_pub.publish(status)

    def navigate(self,xy,heading=0):
        goal=NavigateToPose.Goal();goal.pose=PoseStamped();goal.pose.header.frame_id='map'
        goal.pose.pose.position.x=float(xy[0]);goal.pose.pose.position.y=float(xy[1]);goal.pose.pose.orientation.z=math.sin(heading/2);goal.pose.pose.orientation.w=math.cos(heading/2)
        self.action(NavigateToPose,'/navigate_to_pose',goal,min(90,max(1,self.exec_end-time.monotonic())))

    def execute(self,plan):
        ex=self.execution;begin=time.monotonic();sim_begin=self.sim_time();self.exec_end=begin+plan['budget_s']
        ex['state']='approach';self.phase('executing');self.plan_pub.publish(self.path_msg(plan['path']))
        try:
            first=plan['path'][0];heading=math.atan2(plan['path'][1][1]-first[1],plan['path'][1][0]-first[0])
            if math.dist(self.st['robot']['ground_truth'][:2],first)>.15:self.navigate(first,heading)
            ex['state']='executing'
            if plan['mode']=='follow_path':
                for i,leg in enumerate(plan['legs']):
                    if self.cancel.is_set():raise Interrupted('执行取消请求')
                    ex['progress']=dict(leg=i+1,legs_total=len(plan['legs']))
                    goal=FollowPath.Goal();goal.path=self.path_msg(leg);goal.controller_id='FollowCoverage' if plan['problem_class']=='coverage' else 'FollowPath';goal.goal_checker_id='general_goal_checker'
                    ex['controller']=goal.controller_id
                    self.action(FollowPath,'/follow_path',goal,max(.1,self.exec_end-time.monotonic()))
                    endpoint_error=math.dist(self.st['robot']['ground_truth'][:2],leg[-1])
                    ex.setdefault('leg_results',[]).append(dict(leg=i+1,target=leg[-1],robot=copy.deepcopy(self.st['robot']),endpoint_error_m=endpoint_error))
                    scan=self.latest.get('scan')
                    if scan:
                        save(self.runtime/f'scan-{ex["sim_run_id"]}-leg-{i+1}.json',dict(robot=copy.deepcopy(self.st['robot']),
                            scan_time=stamp(scan.header.stamp),frame=scan.header.frame_id,angle_min=scan.angle_min,angle_increment=scan.angle_increment,
                            ranges=[r if math.isfinite(r) else None for r in scan.ranges]))
                    if endpoint_error>.35:raise RuntimeError(f'第 {i+1} 段控制器到达，但真值端点误差 {endpoint_error:.3f} m 超过 0.35 m')
            else:
                for t in plan['tasks']:self.navigate(t['xy'])
                self.navigate(plan['path'][-1])
            self.settle()
            if any(t['state']!='reached' for t in ex['tasks']):raise RuntimeError('动作完成，但实际轨迹未按序到达全部任务')
            ex['state']='succeeded'
        except Interrupted as exc:ex.update(state='canceled',error=str(exc));self.settle()
        except Exception as exc:
            traceback.print_exc();ex.update(state='failed',error=f'{type(exc).__name__}: {exc}')
            self.cancel_active();self.settle()
        finally:
            for t in ex['tasks']:
                if t['state']=='pending':t['state']='missed'
            trace=ex['tracking_trajectory'];planned=plan['path'];distances=[self.distance_to_path(p[1:3],planned) for p in trace]
            ordered=sorted(distances)
            ex['metrics'].update(duration_sim_s=self.sim_time()-sim_begin,duration_wall_s=time.monotonic()-begin,
                actual_length_m=sum(math.dist(a[1:3],b[1:3]) for a,b in zip(trace,trace[1:])),
                cross_track_mean_m=sum(distances)/len(distances) if distances else None,cross_track_max_m=max(distances) if distances else None,
                cross_track_p95_m=ordered[min(len(ordered)-1,int(.95*len(ordered)))] if ordered else None,
                final_error_m=math.dist(self.st['robot']['ground_truth'][:2],planned[-1]),tasks_reached=sum(t['state']=='reached' for t in ex['tasks']))
            if ex['state']=='succeeded' and plan['mode']=='follow_path' and (not distances or max(distances)>.35):
                ex.update(state='failed',error='实际路径跟踪偏差超过 0.35 m 或缺少真值轨迹')
            try:
                checked=subprocess.run([str(LAB/'.venv/bin/python'),'-m','urp_lab.execution_check'],cwd=LAB,
                    input=json.dumps(dict(plan=plan,execution=ex,world=self.args.world)),text=True,capture_output=True,timeout=30)
                if checked.returncode:raise RuntimeError(checked.stderr)
                ex['metrics'].update(json.loads(checked.stdout))
                mc=ex['metrics'].get('actual_map_check')
                if ex['state']=='succeeded' and (not mc or not mc['collision_free']):
                    ex.update(state='failed',error='实际轨迹的整段地图/足迹检查未通过')
                if ex['state']=='succeeded' and plan['mode']=='follow_path' and ex['metrics'].get('planned_to_actual_max_m',float('inf'))>.35:
                    ex.update(state='failed',error='原规划中存在未被实际轨迹覆盖的部分，距离超过 0.35 m')
                if ex['state']=='succeeded' and plan.get('coverage_instance'):
                    if ex['metrics'].get('actual_working_coverage_fraction',0)<.90 or not ex['metrics'].get('actual_footprint_in_field'):
                        ex.update(state='failed',error='实际内缩作业区覆盖低于 90% 或机器人足迹越出田块')
            except Exception as exc:
                ex['metrics']['execution_check_error']=str(exc)
                if ex['state']=='succeeded':ex.update(state='failed',error='独立执行检查失败：'+str(exc))
            ex['finished_utc']=now();ex['report']=str(self.runtime/'runs'/f'{ex["sim_run_id"]}.json')
            ex['telemetry_at_finish']=self.state()['telemetry'];save(Path(ex['report']),ex);self.runs[ex['sim_run_id']]=copy.deepcopy(ex)
            if not self.stop.is_set():self.phase('ready')

    @staticmethod
    def distance_to_path(p,pts):
        best=math.inf
        for a,b in zip(pts,pts[1:]):
            dx,dy=b[0]-a[0],b[1]-a[1];den=dx*dx+dy*dy
            t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den)) if den else 0
            best=min(best,math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy))
        return best

    def cancel_active(self):
        if self.goal:
            h,f=self.goal
            if not f.done():
                try:self.future(h.cancel_goal_async(),5);self.future(f,8)
                except Exception as exc:self.st['errors'].append('取消活动目标失败：'+str(exc))
            self.goal=None

    def settle(self):
        end=time.monotonic()+1.0
        while time.monotonic()<end:
            self.cmd.publish(Twist());rclpy.spin_once(self.node,timeout_sec=.05)
        odom=self.latest.get('odom')
        if odom and (abs(odom.twist.twist.linear.x)>.02 or abs(odom.twist.twist.angular.z)>.02):
            self.st['errors'].append('停车观察速度未收敛')

    def shutdown(self):
        self.shutting=True;self.phase('stopping');self.cancel_active();self.settle()
        try:
            p=subprocess.run(['ign','service','-s',f'/world/{self.args.world}/control','--reqtype','ignition.msgs.WorldControl','--reptype','ignition.msgs.Boolean','--timeout','2000','--req','pause: true'],env=self.env,capture_output=True,text=True,timeout=4)
            self.report['pause']=dict(returncode=p.returncode,stdout=p.stdout,stderr=p.stderr)
        except Exception as exc:self.report['pause']={'error':str(exc)}
        self.report['lifecycle_shutdown']={}
        for name in ('navigation','localization'):
            c=self.node.create_client(ManageLifecycleNodes,f'/lifecycle_manager_{name}/manage_nodes')
            if c.service_is_ready():
                try:
                    req=ManageLifecycleNodes.Request();req.command=ManageLifecycleNodes.Request.SHUTDOWN
                    self.report['lifecycle_shutdown'][name]=self.future(c.call_async(req),12).success
                except Exception as exc:self.report['lifecycle_shutdown'][name]=str(exc)
            self.node.destroy_client(c)
        self.report['final_state']=self.state()
        for a in self.actions:a.destroy()
        self.listener.unregister();self.node.destroy_node();rclpy.shutdown()
        self.report['bridge_shutdown']=self.processes.stop_bridges()
        self.report['cleanup']=self.processes.cleanup();self.report['remaining_owned_processes']=self.processes.sample()
        bad=[]
        for child in self.report['cleanup']:
            bad.extend(dict(group=child['name'],**p) for p in child['reaped'] if p['returncode'] not in (0,-2,130))
            if not child['complete'] or 'SIGKILL' in child['signals']:bad.append({'group':child['name'],'forced_or_incomplete':True})
        for name,_,log,_ in self.processes.children:
            txt=log.read_text(errors='replace');codes=[int(c) for c in re.findall(r'exit code (-?\d+)',txt)]
            if any(c not in (0,-2,130) for c in codes) or any(s in txt for s in ('SIGKILL','corrupted unsorted','Segmentation fault')):bad.append(dict(group=name,codes=codes,log=str(log)))
        self.report['abnormal_exits']=bad
        for name,component in [('navigation','nav2'),('localization','localization')]:
            if self.st['components'].get(component)=='active' and self.report['lifecycle_shutdown'].get(name) is not True:
                bad.append({'lifecycle_shutdown_failed':name})
        self.report['status']='PASS' if not (bad or self.report['remaining_owned_processes'] or self.report['errors'] or self.st['errors']) else 'FAIL'
        self.report.update(finished_utc=now(),counts=self.counts,stages=self.st['stages'],resources=self.processes.resources)
        save(self.runtime/'session-report.json',self.report);print(json.dumps({'shutdown':self.report['status'],'report':str(self.runtime/'session-report.json')}),flush=True)
        self.st['phase']='stopped' if self.report['status']=='PASS' else 'failed'
        return 0 if self.report['status']=='PASS' else 1

    def run(self):
        try:
            self.startup()
            while not self.stop.is_set():
                self.spin()
                try:kind,body=self.commands.get_nowait()
                except queue.Empty:continue
                if kind=='execute':self.execute(body)
                else:self.window(kind,body['on'])
        except Interrupted:pass
        except Exception as exc:
            traceback.print_exc();self.st['errors'].append(f'{type(exc).__name__}: {exc}');self.report['errors'].append(traceback.format_exc());self.phase('failed')
        finally:return self.shutdown()

def handler(session):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,fmt,*args):pass
        def answer(self,code,obj):
            b=json.dumps(obj,ensure_ascii=False,allow_nan=False).encode();self.send_response(code);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(b)));self.end_headers();self.wfile.write(b)
        def do_GET(self):
            if self.path=='/state':self.answer(200,session.state())
            elif self.path.startswith('/runs/'):
                rid=self.path.split('/')[-1];r=session.runs.get(rid)
                self.answer(200 if r else 404,r or {'message':'运行不存在'})
            else:self.answer(404,{'message':'接口不存在'})
        def do_POST(self):
            try:
                origin=self.headers.get('Origin');host=self.headers.get('Host')
                if origin and origin not in ('http://'+host,'https://'+host):return self.answer(403,{'message':'拒绝跨源写入'})
                if self.headers.get('Content-Type','').split(';')[0]!='application/json':return self.answer(415,{'message':'仅接受 JSON'})
                size=int(self.headers.get('Content-Length','0'))
                if size>8*1024*1024:return self.answer(413,{'message':'正文过大'})
                body=json.loads(self.rfile.read(size) or b'{}')
                if self.path=='/shutdown':session.stop.set();return self.answer(202,{'accepted':True})
                if self.path=='/cancel':session.cancel.set();return self.answer(202,{'accepted':True})
                if self.path in ('/gui','/rviz'):
                    session.commands.put((self.path[1:],body));return self.answer(202,{'accepted':True})
                if self.path=='/execute':
                    with session.lock:
                        if session.st['phase']!='ready' or (session.execution and session.execution['state'] not in FINAL):return self.answer(409,{'message':'会话未就绪或正在执行'})
                        if body.get('mode') not in ('follow_path','nav2_waypoints') or len(body.get('path',[]))<2:return self.answer(422,{'message':'路径或模式无效'})
                        ex=dict(sim_run_id=body['sim_run_id'],run_id=body['run_id'],session_id=session.args.session_id,world=session.args.world,mode=body['mode'],
                            state='queued',sources=body['sources'],planned={'path':body['path'],'length_m':body['planned_length_m']},
                            tasks=[dict(**t,state='pending',t_sim=None,distance_m=None) for t in body['tasks']],actual={'ground_truth':[],'amcl':[]},
                            approach_trajectory=[],tracking_trajectory=[],task_radius_m=body['task_radius_m'],nav2=[],metrics={'tasks_total':len(body['tasks']),'tasks_reached':0},
                            error=None,created_utc=now(),finished_utc=None,report=None)
                        ex['localization']=session.args.localization
                        ex['navigation_profile']=session.report['navigation_profile']
                        session.execution=ex;session.cancel.clear();session.commands.put(('execute',body))
                    return self.answer(202,{'accepted':True})
                self.answer(404,{'message':'接口不存在'})
            except Exception as exc:self.answer(400,{'message':f'{type(exc).__name__}: {exc}'})
    return Handler

def main():
    p=argparse.ArgumentParser();p.add_argument('--session-id',required=True);p.add_argument('--world',choices=['maze','warehouse','depot'],required=True)
    p.add_argument('--localization',choices=['ground_truth','amcl'],default='amcl')
    p.add_argument('--spawn',default='0,0,0');p.add_argument('--runtime',required=True);p.add_argument('--port',type=int,default=4191);p.add_argument('--gui',action='store_true');p.add_argument('--rviz',action='store_true')
    p.add_argument('--no-web',dest='web',action='store_false',help='不启动浏览器视图用的 Foxglove Bridge / Gazebo WebSocket')
    p.add_argument('--foxglove-port',type=int,default=8765);p.add_argument('--gazebo-web-port',type=int,default=9002);args=p.parse_args()
    values=[float(v) for v in args.spawn.split(',')]
    if len(values)!=3 or not all(math.isfinite(v) for v in values):raise ValueError('出生点需为有限 x,y,yaw')
    args.spawn=dict(zip(('x','y','yaw'),values));session=Session(args)
    for sig in (signal.SIGINT,signal.SIGTERM):signal.signal(sig,lambda *_:session.stop.set())
    server=ThreadingHTTPServer(('127.0.0.1',args.port),handler(session));threading.Thread(target=server.serve_forever,daemon=True).start()
    result=session.run();server.shutdown();server.server_close();return result

if __name__=='__main__':raise SystemExit(main())
