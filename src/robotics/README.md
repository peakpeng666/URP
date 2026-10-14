# 路线显示与仿真接口接入包（可选 smoke fixture）

## 最新范围修正：主方案直接复用网上的仿真

用户明确的“仿真”是直接使用现成网上项目。**本目录的自建差速车/合成温室只是已准备的、可丢弃的接口 smoke fixture，不是主仿真方案，不是最终场景，也不是机器人选型建议。停止扩展它。** 后续主路线应选择有上游维护和可复现版本的现成机器人/世界/导航工程，再用可替换 adapter 连接本项目。

保留本包是因为 route-scene→RViz、单位校验、frame、单向 bridge 与验收器仍有复用价值。主项目选好后，应复用官方模型、世界、传感器和启动入口；不要把本 fixture 的运行记录当作该上游平台的测试通过。

## 先说现在做到了哪一步

本包包含两条严格分离的链路：

1. **研究结果展示**：后端 route-scene v1 → 本地 JSON → ROS 2 MarkerArray → RViz2。只展示访问顺序与坐标关系，不发导航路径或运动命令。
2. **独立合成机器人场景**：自建 12 × 8 米温室、差速车、惯性传感器、轮式里程计、独立物理位姿真值 → ROS/Gazebo 单向桥 → 有界闭环控制与验收报告。

当前已在 dot 云端通过纯 Python/静态检查。**当前云端没有 ROS 2 Humble 或 Gazebo Fortress，因此 ROS 节点、RViz 图形、SDF 物理装载、桥接、闭环运动均未执行验证。** 不把静态世界文件、理想运动学单测或发布里程计本身称为“真实仿真跑通”。

用户当前要求先做当前云端可做的部分；本包没有安装软件、创建额外执行环境或使用用户电脑。以下命令是未来获准且具备环境后的部署说明，不代表已经运行。

## 版本只选一条

当前实现针对 **Ubuntu 22.04 + ROS 2 Humble + Gazebo Fortress（Gazebo Sim 6）**：

- ROS 软件包是 ros_gz_bridge，不使用已结束支持的 Gazebo Classic 11 的 gazebo_ros 插件。
- 仿真命令是 ign gazebo。
- Fortress 的 SDF 插件库采用 ignition-gazebo-…-system，插件类采用 ignition::gazebo::systems::…。
- 桥接消息是 ignition.msgs.…；YAML 的方向名仍然是 GZ_TO_ROS、ROS_TO_GZ。
- 没有假装本包兼容 Jazzy/Harmonic。若未来选 Ubuntu 24.04 + Jazzy + Harmonic，应另行切换 CLI 到 gz sim、插件库到 gz-sim-…-system、类到 gz::sim::systems::…、消息到 gz.msgs.…，再完整重跑验收；不能仅替换发行版名。

API 核对与版本来源见 [OFFICIAL_SOURCES.md](docs/OFFICIAL_SOURCES.md)。

## 无 ROS 的当前云端检查

```sh
cd robotics
PYTHONPATH=urp_route_sim python3 -m unittest discover -s urp_route_sim/test -v
python3 -m compileall -q urp_route_sim scripts
bash -n scripts/run_smoke.sh
scripts/check_scene.py urp_route_sim/config/route_scene_synthetic_fixture.json
```

最后一项只校验合同与显示语义。增加 --require-metric 时，对缺少真实标定的 benchmark JSON 必须拒绝。该测试 fixture 来源于后端的合成合同测试，不是研究结果、更不是温室地图。

## 研究路线到 RViz

先由既有后端导出对应版本的 JSON：

```text
GET /api/v1/experiments/{experiment_id}/runs/{run_id}/route-scene?revision=N
```

将响应存为本地 scene.json，然后在已构建的 ROS 工作空间：

```sh
export ROS_LOCALHOST_ONLY=1
ros2 launch urp_route_sim route_view.launch.py scene_file:=/absolute/path/scene.json
```

- 默认 fixed frame 是 benchmark_xy，画面常驻提示“arbitrary units, NOT metres / navigation”；不连接 map、odom 或机器人 TF。
- RViz 配置不启用米制网格。显示尺度只影响画面大小，不改变数据单位。
- 折线是 visit_order_polyline，节点文字是源 node_id。保留车辆 ID、顺序与重复访问，红色表示未服务节点，仓库为方块。
- 该节点只发布 /urp_routes/markers 的 visualization_msgs/MarkerArray；不发布 nav_msgs/Path、cmd_vel、导航 goals 或机器人 TF。
- JSON 中的求解时间、时间窗和服务时刻不会被转成真实机器人时间；服务累计需求也不被解释为车上实时载重。
- “选择了某条路线”或“显示当前最短路线”不等于已有学习型推荐系统。
- 采用 snapshot 文件而非联网拉取，避免节点在后台访问外部服务，也确保演示固定在同一 revision。

### 可选物理显示标定并不是导航许可

只有得到实际测绘、单位约定和标定依据后才可提供独立 calibration JSON：

```json
{
  "source_frame": "benchmark_xy",
  "source_units": "arbitrary_distance_units",
  "target_frame": "survey_map",
  "meters_per_unit": 0.01,
  "yaw_radians": 0.0,
  "translation_m": [0.0, 0.0],
  "calibrated": true,
  "calibration_evidence": "填入实际标定记录的标识与依据，不能照抄本示例"
}
```

上面是格式示例，**0.01 不是真实比例，没有默认标定文件**。数学约定是 p_target = scale × R(yaw) × p_source + translation，平移单位为米，旋转为弧度，XY 顺序不交换。程序验证字段完整性、有限值、正比例、源 frame/单位匹配和证据非空，但不能自动证明人工输入的标定真实正确。映射后仍只展示访问顺序，不宣称可行驶。传入 calibration_file:=… 后须在 RViz 将 Fixed Frame/Target Frame 改为显式 target_frame；程序不虚构两个 frame 之间的 TF。

## 可选、可丢弃的合成 smoke fixture（非主仿真）

- 世界：SYNTHETIC，长度 12 m、宽度 8 m；墙体、地板、两排作物床均为本地 SDF 几何，无在线模型下载。
- 机器人：差速驱动，轮半径 0.10 m、轮距 0.38 m、最大线速度 0.25 m/s、最大角速度 0.7 rad/s。
- CPU 传感器：50 Hz IMU，避免将 GPU/图形驱动当作无头服务器的基础验收依赖。**未提供激光雷达、相机或避障。**
- 验收路线：沿空旷通道由 (0,0) 到 (1,0)、(2,0)，再转向返回 (0,0)，单位为米。由本包硬编码的合成工程任务定义，不读取 CVRPLIB、Solomon 或研究路线 JSON。
- 控制反馈：轮里程计驱动转向和前进；到点停止，转向时先原地旋转。独立物理位姿检验车体确实移动，IMU 检验真实角速度，不仅看轮子转动。
- 安全边界：控制器不接受任意话题、机器人、世界或路线文件参数。只用 /urp_synthetic/cmd_vel，必须是 ROS_LOCALHOST_ONLY=1、ROS_DOMAIN_ID=71、IGN_IP=127.0.0.1、唯一 urp_synthetic_* transport partition，且显式设置 URP_ALLOW_SYNTHETIC_COMMANDS=1。
- 仿真启动本身不启动控制器。闭环 runner 才进入运动测试；feedback 失效、非有限数据、frame 错误、越界或超时均停止。结束时发送多次零速度并终止自己启动的仿真进程组。
- 上述约束降低误接风险，**不构成物理机器人的安全认证，也不得部署到有真实机器人控制桥的环境**。

### 构建和启动（未来获准环境）

先在官方来源提供的 Ubuntu 22.04/Humble/Fortress 环境准备 ROS 2、ros_gz_bridge、RViz2、colcon 与 Gazebo；本包不附带自动安装脚本。检查实际软件包版本，不混入 Gazebo Classic 或 Harmonic。

```sh
mkdir -p ~/urp_sim_ws/src
# 将本目录中的 urp_route_sim 复制到 ~/urp_sim_ws/src/，保持结构完整。
source /opt/ros/humble/setup.bash
cd ~/urp_sim_ws
colcon build --packages-select urp_route_sim --symlink-install
source install/setup.bash
```

仅打开仿真与 ROS bridge，不运动：

```sh
export ROS_LOCALHOST_ONLY=1 ROS_DOMAIN_ID=71 IGN_IP=127.0.0.1
export IGN_PARTITION=urp_synthetic_manual
ros2 launch urp_route_sim synthetic_fortress.launch.py rviz:=true
```

默认启动 headless server。需要 Gazebo GUI 的已获准图形环境，可在另一个终端设置**相同 IGN_PARTITION 和 IGN_IP** 后执行 ign gazebo -g；不要误连其他分区。RViz 用于观察轮里程计与 TF，Gazebo GUI 用于观察世界和车体。

### 可执行闭环验收

关闭手动实例后，使用完整部署包中的 runner；它自行选择唯一分区、启动 headless server，并清理自己的子进程。

```sh
source /opt/ros/humble/setup.bash
source ~/urp_sim_ws/install/setup.bash
/path/to/robotics/scripts/run_smoke.sh /absolute/path/to/new_evidence_dir
```

该命令不安装软件。缺依赖时写 preflight.json 并退出 2；存在依赖且开始执行后，终态由 smoke_result.json 与退出码共同判定，详细要求见 [ACCEPTANCE.md](docs/ACCEPTANCE.md)。既有 evidence/preflight_current_cloud/preflight.json 是当前未执行的确凿记录，不可覆盖或改成成功。

## 实验链路与未来衔接

现状及每阶段门槛见 [INTEGRATION_ROADMAP.md](docs/INTEGRATION_ROADMAP.md)。短期交付可以包含二维研究路线、来源证据、严格版本化 scene 导出和上游仿真接入计划；可选合成 smoke 仅供检查接口；不能把机器人演示表现用于证明当前研究算法在真实温室中有效。
