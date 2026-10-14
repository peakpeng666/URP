# 可选接口 fixture 验收规范与证据等级

本规范针对本目录的可丢弃合成 smoke，不是用户所需上游仿真平台的最终验收。复用网上项目后，要重新核对官方启动入口、传感器、动作接口、坐标系和平台适用性，不能直接复用成功结论。

## A. 当前已执行

- 标准库单测覆盖 scene 合同、单位/坐标语义、异常输入、显式标定与显示 frame、控制器数学逻辑、世界/插件/bridge 静态一致性。
- Python 语法编译与 shell 语法检查。
- 读取后端真实冻结合同 fixture 并通过离线解析。
- 当前云端 preflight：找不到 /opt/ros/humble/setup.bash，runtime_executed=false。没有将“缺环境”伪装成通过，也没有趁机安装额外软件。

**静态 XML 解析不等同于 libsdformat 完整校验，更不等同于 plugin load 成功。控制器理想运动学单测不等同于 Gazebo 仿真。**

## B. 未来环境执行时必须收集

1. /etc/os-release、ROS_DISTRO、已装 ros_gz_bridge 版本、ign gazebo --versions、包源码 SHA256 清单。
2. 构建日志、colcon 测试结果；通过 ign sdf -k 对 SDF 作发行版内语义检查，错误必须修复后重新验收。
3. launch.log 必须没有无法载入的 physics、DiffDrive、IMU、OdometryPublisher 插件；不能仅检查进程仍存活。
4. topic 类型与方向、frame_id/child_frame_id、时间戳与仿真时钟符合配置。
5. 完整 telemetry.jsonl 和 smoke_result.json，附当前运行的代码版本/哈希。
6. 若要求可视化交付，另收集 RViz 路线图和 Gazebo 合成车体运动截图/录屏。headless runner 成功不能取代 GUI 验收。

## C. 闭环 smoke 的硬门槛

- 15 秒内分别收到至少 5 条 odom、ground_truth、imu、clock；缺任一项不运动。
- 运行期间任一反馈超过 2 秒未到立即停止；frame 错误、非法四元数、非有限数、反向时间戳立即失败。
- wheel odom 的 parent 是 synthetic_odom，child 是 synthetic_base_footprint，表示由轮积分估计的平面轴心投影。它不是 Gazebo link 的 3D TF。
- 物理 ground_truth 的 parent 是 synthetic_world，child 是 synthetic_body，来自模型的真实仿真世界位姿；两坐标系只在起点 XY 和 yaw 对齐，不能推定未来无漂移或冒充定位。
- 控制器和真值都限制在 x∈[-1,3]、y∈[-0.8,0.8] 米的空通道；不把温室碰撞自由性推广到任意路线。
- 三个目标点全部到达；每点轮式里程计容差 0.10 m。
- 总体验收每种反馈至少 10 条，时钟前进 >1 s；轮式位移和物理真值位移均 >1.7 m；IMU 角速度绝对峰值 >0.2 rad/s。
- 返回后轮式闭合误差 ≤0.15 m，独立真值闭合误差 ≤0.25 m；末次反馈仍新鲜、无任何校验错误。
- 控制器墙钟上限默认 65 s；runner 90 s 总守护，超时后终止自己启动的进程组。非零退出码或任一 check=false 一律失败，报告包含 failed_checks；到点成功但后验检查失败时原因会显式附加失败项。

当前控制器不包含仿真端命令看门狗，进程突然崩溃时由 runner 的失败清理终止世界；不要脱离 runner 把它当长时间自主系统。runner 的保护只针对本包合成实例，不得用于真实硬件。

## D. 通过之后仍不能宣称

- 当前路线算法在真实温室中更优或可部署。
- 任意 benchmark 点列可以直接喂给 Nav2。
- 已完成导航、避障、定位、SLAM、全局/局部规划、动态障碍、真实载荷、农艺时间窗口、噪声鲁棒性或真实机器人验证。
- 存在已训练/已验证的推荐模型。

本 smoke 不检测接触事件，成功也不证明零碰撞。本 smoke 最多证明：在固定的合成米制环境里，ROS/Gazebo bridge、轮反馈控制、CPU IMU、物理位姿与有界任务终态确实连通。
