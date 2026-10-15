#!/usr/bin/python3
"""Two temporary ROS nodes; no robot commands or external services."""
import json
import os
import time

import rclpy
from rclpy.executors import SingleThreadedExecutor
from std_msgs.msg import String

rclpy.init()
publisher_node = rclpy.create_node(f"urp_setup_pub_{os.getpid()}")
subscriber_node = rclpy.create_node(f"urp_setup_sub_{os.getpid()}")
executor = SingleThreadedExecutor()
executor.add_node(publisher_node)
executor.add_node(subscriber_node)
topic = f"/urp_setup_smoke_{os.getpid()}"
received = []
publisher = publisher_node.create_publisher(String, topic, 10)
subscription = subscriber_node.create_subscription(String, topic, lambda msg: received.append(msg.data), 10)
try:
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline and not received:
        publisher.publish(String(data="urp_setup_ok"))
        executor.spin_once(timeout_sec=0.1)
    assert received and received[0] == "urp_setup_ok", "No message received within eight seconds"
    discovered = subscriber_node.get_publishers_info_by_topic(topic)
    assert discovered, "Publisher absent from ROS graph"
    print(json.dumps({"status": "PASS", "message_received": received[0], "discovered_publishers": len(discovered),
                      "domain_id": os.environ.get("ROS_DOMAIN_ID"), "localhost_only": os.environ.get("ROS_LOCALHOST_ONLY")}, indent=2))
finally:
    executor.shutdown()
    subscriber_node.destroy_node()
    publisher_node.destroy_node()
    rclpy.shutdown()
