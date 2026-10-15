#!/usr/bin/env bash
# A bounded, non-GUI verification after the user installs the system packages.
set -eo pipefail
setup_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source /opt/ros/humble/setup.bash
set -u
export ROS_HOME="$setup_dir/runtime/ros-home"
export ROS_LOG_DIR="$setup_dir/runtime/ros-log"
export ROS_DOMAIN_ID=139
export ROS_LOCALHOST_ONLY=1
mkdir -p "$setup_dir/runtime" "$setup_dir/logs"
for package in rviz2 nav2_bringup turtlebot4_ignition_bringup ros_gz_bridge; do
  ros2 pkg prefix "$package"
done
python3 "$setup_dir/smoke-ros.py" > "$setup_dir/ros-smoke-after-install.json"
ign gazebo --versions > "$setup_dir/logs/gazebo-version.log" 2>&1
timeout --signal=INT --kill-after=5s 20s ign gazebo -s -r --iterations 5 \
  "$setup_dir/minimal-world.sdf" > "$setup_dir/logs/gazebo-minimal.log" 2>&1
ros2 pkg executables rviz2 > "$setup_dir/logs/rviz-executable.log"
ros2 launch turtlebot4_ignition_bringup turtlebot4_ignition.launch.py --show-args \
  > "$setup_dir/logs/turtlebot4-launch-arguments.log" 2>&1
printf 'Non-GUI checks passed. RViz rendering and the full TurtleBot4 simulation still require a graphical session.\n'
