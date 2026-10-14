# 官方 API 与版本依据

检查日期：2026-10-14。以下资料用于编写本包，不代替实际发行版运行验收。上游分支可能继续变化，未来执行时应记录实际安装版本。

- [Gazebo Fortress ROS 2 integration](https://gazebosim.org/docs/fortress/ros2_integration/)：ROS bridge 与 Fortress 的集成入口。
- [ros_gz humble branch bridge README](https://github.com/gazebosim/ros_gz/blob/humble/ros_gz_bridge/README.md)：ROS 消息映射、YAML 的 ros_topic_name/gz_topic_name、ignition.msgs 类型及 GZ_TO_ROS/ROS_TO_GZ 方向。
- [Gazebo 6 DiffDrive source](https://github.com/gazebosim/gz-sim/blob/ign-gazebo6/src/systems/diff_drive/DiffDrive.cc)：topic/odom_topic/tf_topic、frame_id/child_frame_id、轮参数及速度/加速度约束。
- [Gazebo 6 OdometryPublisher source](https://github.com/gazebosim/gz-sim/blob/ign-gazebo6/src/systems/odometry_publisher/OdometryPublisher.cc)：基于模型 worldPose 的独立物理位姿，odom_frame、robot_base_frame、dimensions 与 odom_publish_frequency 参数。
- [Fortress sensor tutorial](https://gazebosim.org/docs/fortress/sensors/)：IMU sensor 与 Imu world system 的配置。基础验收仅采用 CPU IMU；不将 GPU lidar 的渲染依赖藏起来。
- [Gazebo Fortress project template guide](https://gazebosim.org/docs/fortress/ros_gz_project_template_guide/)：ROS/Gazebo 分层与工作空间组织参考。
- [ROS/Gazebo integration best practices, ROSCon 2022](https://download.ros.org/downloads/roscon/2022/ROS%202%20and%20Gazebo%20Integration%20Best%20Practices.pdf)：Humble/Fortress 配对与分层集成思路。实际发行版支持状态仍以当前官方安装文档为准。

实现边界：没有从泛用问答或非官方博客推断插件兼容性；没有调用 Gazebo Classic gazebo_ros_diff_drive，也没有把 Harmonic 的 gz.msgs/CLI 混进 Fortress 的现有执行链。
