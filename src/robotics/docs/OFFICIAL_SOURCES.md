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

## 2026-10-17 补充核对

- [TurtleBot 4 官方手册](https://turtlebot.github.io/turtlebot4-user-manual/software/turtlebot4_simulator.html)：Humble 对应 Ubuntu 22.04/Fortress，以及官方 `turtlebot4_ignition.launch.py` 入口。
- [固定的 TurtleBot 4 提交](https://github.com/turtlebot/turtlebot4_simulator/tree/0ea4a60c51e49ed4a9e25b4f9971ff0f0c9a08fe)：检查时 Humble 为 1.0.3；主 launch、Ignition launch、spawn、bridge、Depot SDF 和 package.xml 的 Git blob 列在配置清单。上游 Depot 含未锁版本 Fuel URI，不将本次关键源码冻结写成完整依赖/资产冻结。
- [RViz Humble VisualizerApp](https://github.com/ros2/rviz/blob/humble/rviz_common/src/rviz_common/visualizer_app.cpp)：核对 `-f` / `--fixed-frame`，用于让显示 frame 跟随显式标定；读取到的 Git blob 为 `e84875f6793997355b3c7898aea29676d3477df0`。
- [Ignition Sensors 6 Sensor.cc](https://github.com/gazebosim/gz-sensors/blob/ign-sensors6/src/Sensor.cc) 与 [ImuSensor.cc](https://github.com/gazebosim/gz-sensors/blob/ign-sensors6/src/ImuSensor.cc)：前者读取 `ignition_frame_id`，后者将 `FrameId()` 写入消息 header。读取的 Git blob 分别为 `f9a2d5db1f2d6e6ac481dd0c195c07d28ed2a553`、`ebc0f6ab6ce5448fa840f1256dd18c628bad2b7e`。实际安装版本仍需运行预检与消息验证。
- [Nav2 Humble 的 RViz launch](https://api.nav2.org/nav2-humble/html/rviz__launch_8py_source.html)：官方示例采用 `RegisterEventHandler`、`OnProcessExit` 与 `EmitEvent(Shutdown(...))` 联动退出。本包仅将相同 ROS launch 机制用于既有 Gazebo/bridge 生命周期。
