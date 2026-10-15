#!/usr/bin/python3
"""Bounded official TB4 startup in the packaged, offline maze world; no motion goals."""
import json
import os
from pathlib import Path
import signal
import subprocess
import time

import rclpy
from nav_msgs.msg import Odometry
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import LaserScan
from controller_manager_msgs.srv import ListControllers
from rclpy.qos import qos_profile_sensor_data

base = Path(__file__).resolve().parent
command = ["ros2", "launch", "turtlebot4_ignition_bringup", "turtlebot4_ignition.launch.py",
           "world:=maze", "rviz:=false", "nav2:=false", "slam:=false", "localization:=false"]
environment = os.environ.copy()
environment["IGN_PARTITION"] = f"urp_setup_{os.getpid()}"
environment["IGN_HOMEDIR"] = str(base / "runtime" / "ignition-home")
environment["IGN_FUEL_CACHE_PATH"] = str(base / "cache" / "ignition-fuel")
Path(environment["IGN_FUEL_CACHE_PATH"]).mkdir(parents=True, exist_ok=True)
Path(environment["IGN_HOMEDIR"]).mkdir(parents=True, exist_ok=True)
counts = {"clock": 0, "odom": 0, "scan": 0}
clock_samples = []
report = {"command": command, "world": "official packaged maze", "motion_commands": 0}
with (base / "logs" / "turtlebot4-startup.log").open("w") as log:
    process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, env=environment, start_new_session=True)
    report["launch_pid"] = process.pid
    rclpy.init()
    node = rclpy.create_node("urp_setup_tb4_observer")
    def count(name):
        def callback(message):
            counts[name] += 1
            if name == "clock":
                clock_samples.append(message.clock.sec + message.clock.nanosec / 1e9)
        return callback
    subscriptions = [node.create_subscription(Clock, "/clock", count("clock"), qos_profile_sensor_data),
                     node.create_subscription(Odometry, "/odom", count("odom"), qos_profile_sensor_data),
                     node.create_subscription(LaserScan, "/scan", count("scan"), qos_profile_sensor_data)]
    controller_client = node.create_client(ListControllers, "/controller_manager/list_controllers")
    controller_future = None
    controllers = {}
    try:
        deadline = time.monotonic() + 45
        while time.monotonic() < deadline and process.poll() is None:
            rclpy.spin_once(node, timeout_sec=0.2)
            if controller_future is None and controller_client.service_is_ready():
                controller_future = controller_client.call_async(ListControllers.Request())
            if controller_future is not None and controller_future.done():
                controllers = {c.name: c.state for c in controller_future.result().controller}
                controller_future = None
            if all(counts.values()) and controllers.get("diffdrive_controller") == "active" and len(clock_samples) > 2 and clock_samples[-1] > clock_samples[0]:
                break
        report.update(message_counts=counts, clock_advanced=len(clock_samples) > 1 and clock_samples[-1] > clock_samples[0],
                      launch_exit_before_shutdown=process.poll(), topics=node.get_topic_names_and_types())
        report["controllers"] = controllers
        report["status"] = "PASS" if all(counts.values()) and report["clock_advanced"] and controllers.get("diffdrive_controller") == "active" else "INCOMPLETE"
    finally:
        node.destroy_node()
        rclpy.shutdown()
        if process.poll() is None:
            process.send_signal(signal.SIGINT)
        try:
            process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=5)
        report["launch_exit_after_shutdown"] = process.returncode
        # Gazebo's GUI may outlive the launch leader; this is our dedicated group.
        try:
            os.killpg(process.pid, signal.SIGTERM)
            report["residual_group_sigterm"] = True
        except ProcessLookupError:
            report["residual_group_sigterm"] = False
(base / "turtlebot4-smoke.json").write_text(json.dumps(report, indent=2))
print(json.dumps({key: report[key] for key in ("status", "message_counts", "clock_advanced", "controllers", "launch_exit_after_shutdown")}, indent=2))
