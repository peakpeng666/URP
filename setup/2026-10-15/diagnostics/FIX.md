# TurtleBot4 验证修正（实施记录）

系统包未变更、未重装。全部 443 包沿用原安装版本，未改驱动、安全、网络或 ROS 系统配置。

原 `smoke-turtlebot4.py` 在每次 ListControllers 响应完成后立即再次发请求，没有间隔，并从控制器初始化早期开始调用。这会与官方 spawner 的启动服务请求并发。失败记录中只激活 joint_state_broadcaster，响应写入抛出 `cannot publish data`，异常经 controller_manager/rclcpp 终止 Gazebo。此前把这一失败直接概括为“官方仿真不可用”证据不足，因为观察探针本身会改变负载。

本次只修改项目内验证探针：

1. 被动等待官方 spawner 报告 diffdrive_controller 已配置并激活。
2. 仅调用一次 ListControllers，确认实际 active 状态。
3. 连续观察十秒，要求时钟前进、里程计及激光有消息。
4. 记录服务请求次数、稳定观察时长和独立运行标签；仍仅收尾本测试独立进程组。

原探针保存在 `turtlebot4-probe-before.py`，原失败日志和 JSON 保持不动。修正后的独立结果另存，见 `VALIDATION.md`。

直接异常机制是 Fast DDS 的响应 write 失败，而不是已证实的缺包或 GPU 故障。高频探针是本次已排除的干扰/触发条件；尚未定位到底层 write 失败属于哪种资源或并发情形，因此不声称修复了 Fast DDS 自身。上游 rmw_fastrtps 6.2.10 的 response 实现仅在 write 返回失败时设置同一错误：
https://raw.githubusercontent.com/ros2/rmw_fastrtps/6.2.10/rmw_fastrtps_shared_cpp/src/rmw_response.cpp
