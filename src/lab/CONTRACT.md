# URP Lab 集成契约（开发者用）

本文件固定科研面板各进程之间的数据结构与接口。实现必须遵守；如需改动，同步修改本文件、`src/frontend/src/lab/types.ts` 与测试。

## 0. 进程与端口

| 进程 | 解释器 / 环境 | 端口 | 说明 |
|---|---|---|---|
| 网关 `urp_lab` | `src/lab/.venv`（uv，CPython 3.12） | 127.0.0.1:4100 | 托管面板（`src/frontend/dist`）、`/lab/api/*`、反向代理 `/api/*` → 4180、SSE |
| 档案后端 | `src/backend/.venv`（3.10） | 127.0.0.1:4180 | 既有只读实验档案 API，不改其契约；由网关按需启动/停止 |
| 求解工作进程 | `src/lab/.venv` 子进程 | — | 每次求解独立子进程，带墙钟预算；项目模块通过 `sys.path` 引入 `src/research/src`，不修改研究源码 |
| 仿真会话 `urp_sim_session.py` | 系统 `/usr/bin/python3`（3.10）+ ROS 2 Humble rclpy | 127.0.0.1:4191 | 官方 TB4 + Gazebo Fortress + Nav2 + 可选 GUI/RViz；复用 `setup/2026-10-15/deployment` 的 TF 修补、GUI 插件保护、有序桥接关闭 |

ROS 环境变量通过 `bash setup/profile.sh simulation …` 设定（CycloneDDS、`ROS_DOMAIN_ID=139`、`ROS_LOCALHOST_ONLY=1`）。科研 Python 与 ROS Python 不互相导入。

运行目录：`src/lab/runtime/`（git 忽略）——`logs/`、`lab.sqlite3`、`sim/<session_id>/`、`exports/`。

## 1. 坐标系与来源（必须在数据和界面中显式区分）

- `frame.kind = "benchmark"`：基准算例坐标，**无物理单位**（`units: "unitless"`），成本单位按算例声明（如 `synthetic_integer_cost`）。不能直接送入仿真。
- `frame.kind = "map"`：ROS `map` 坐标，单位米（`units: "m"`），附官方地图（`world`、`map_yaml`）。转弯路网成本为整数厘米当量（`cost_unit: "cm_equivalent"`：路段长度 cm + 转弯惩罚 cm 当量）。
- 来源标签 `source`：`"project"`（URP 项目算法/检查器，给出文件路径）、`"third_party"`（PyVRP、OR-Tools、Fields2Cover，给出版本）、`"panel_baseline"`（面板内置的简单基线，非项目研究成果）、`"nav2"`（Nav2 自身规划/控制）。
- 仿真执行区分：`follow_path`（Nav2 控制器跟踪 **求解器几何路径**，不调用 Nav2 全局规划器）与 `nav2_waypoints`（只给出任务顺序，**路径由 Nav2 NavFn 规划**）。机器人从当前位置到路线起点的"接驳段"总是 Nav2 规划，单独记录。
- 实际轨迹：`ground_truth`（Gazebo 真值，world 坐标；官方地图与 world 对齐）与 `amcl`（定位估计，map 坐标）分开记录。

## 2. 数据模型（JSON）

### 2.1 Scenario

```jsonc
{
  "id": "farm-rows-warehouse",
  "title": "仓储货架通道 · 作物行代理",
  "summary": "…",
  "problem_class": "turn_routing" | "euclidean_cvrp" | "coverage",
  "frame": {"kind": "map", "units": "m", "world": "warehouse", "map": {"yaml": "/opt/…/warehouse.yaml", "resolution": 0.03, "origin": [-15.1,-25.0,0], "width": 1006, "height": 1674, "image": "/lab/api/maps/warehouse.png"}}
         | {"kind": "benchmark", "units": "unitless"},
  "cost_unit": "cm_equivalent" | "synthetic_integer_cost" | "euclidean" | "m",
  "provenance": {"generator": "urp_lab.scenarios.field:warehouse_rows", "params": {...}, "seed": null, "note": "…"},
  "sim": {"supported": true, "world": "warehouse", "spawn": {"x":0,"y":0,"yaw":0}, "reason": null},
  "instance": { /* problem-class payload, §2.2 */ },
  "editable": {"tasks": true, "depot": true, "capacity": true, "demands": true},
  "layers": { /* 仅用于绘制的附加几何，可选：row_polygons, headland, obstacles, field_polygon … */ }
}
```

`GET /lab/api/scenarios` 返回不含 `instance` 的摘要列表（含 `id,title,summary,problem_class,frame,sim.supported,task_count,node_count`）。

### 2.2 Instance payloads

**turn_routing**（与 `src/research/src/urp_research/turn_modes` 输入格式一致，另加几何）：
```jsonc
{"depot": 0, "capacity": 6,
 "customers": [{"id": 0, "node": 12, "demand": 1, "label": "A3"}],
 "arcs": [[u, v, cost_int]], "forbidden_turns": [[u, v, w]], "turn_penalties": [[u, v, w, penalty_int]],
 "coordinates": {"0": [x, y]},            // 键为节点 id 字符串
 "node_kinds": {"0": "depot"|"headland"|"row"|"grid"},   // 可选
 "units": "cm_equivalent", "service_heading_reset": false, "depot_reset": "between_routes_only", "fleet_limit": null}
```
**euclidean_cvrp**（与 `cvrp_selection` 一致：下标 0 为仓库）：
```jsonc
{"coordinates": [[x,y], …], "demands": [0, d1, …], "capacity": 30, "depot": 0,
 "fleet": "unlimited_identical_vehicles", "objective": "sum_unrounded_euclidean_distance", "labels": ["D", "1", …]}
```
**coverage**：
```jsonc
{"field": [[x,y], …],            // 外边界多边形（米），逆时针，不闭合
 "obstacles": [[[x,y],…]],         // 可选内部障碍
 "headland_width": 0.8, "swath_width": 0.5, "turn_radius": 0.3, "robot_width": 0.35,
 "start": [x, y], "route_pattern": "boustrophedon"|"snake"|"spiral", "angle_deg": null}
```

### 2.3 Algorithm catalog entry (`GET /lab/api/algorithms`)
```jsonc
{"id": "urp.turn_mode_dp", "name": "转弯模式分层 DP（精确）", "problem_classes": ["turn_routing"],
 "family": "exact"|"metaheuristic"|"heuristic"|"baseline"|"coverage"|"relaxation",
 "source": "project"|"third_party"|"panel_baseline", "origin": "src/research/src/urp_research/turn_modes/solver.py" | "PyVRP 0.14.0",
 "turn_aware": true, "guarantee": "optimal"|"optimal_for_relaxation"|"none",
 "limits": {"max_tasks": 12}, "available": true, "unavailable_reason": null,
 "params": [{"name": "time_limit_s", "type": "number", "default": 5, "min": 0.5, "max": 120, "label": "时间预算 (s)"}],
 "description": "…"}
```
固定 id（`pyvrp.hgs` 为历史 API 标识；已安装的 PyVRP 0.14.0 实际运行 IteratedLocalSearch，显示名和来源使用 ILS，不把它归类为 HGS）：
- turn_routing：`urp.turn_mode_dp`、`urp.reset_dp`（忽略进入方向的松弛，可能违反转弯约束）、`urp.raw_oracle`（独立原图精确搜索）、`pyvrp.hgs+urp.layered`、`ortools.gls+urp.layered`（第三方元启发式在松弛距离上给出分配与顺序，再由项目 `turn_modes/evaluate_candidate.py` 分层 DP 实现转弯可行路线）。
- euclidean_cvrp：`pyvrp.hgs`、`ortools.gls`。旧 `urp.js.*` 尚未纳入此网关目录。
- coverage：`f2c.boustrophedon`、`f2c.snake`（可选 Fields2Cover；版本和 native 指纹必须匹配 vendor 清单，否则 available=false 并说明原因）、`panel.boustrophedon`（面板基线，Shapely 实现，允许原地转向）。F2C 支持单个凸内缩作业区，采用原生 Dubins 转弯、0.02 m 离散；独立检查完整足迹、采样曲率及作业区覆盖。拒绝的几何保留在 raw_result，不能进入仿真。

### 2.4 Solve request / Solution
```jsonc
// POST /lab/api/solve
{"scenario_id": "…", "instance": {…可选：用户编辑后的 instance；省略则用场景原始 instance…},
 "algorithms": [{"id": "urp.turn_mode_dp", "params": {"time_limit_s": 10}}], "label": "可选备注"}
// → 202 {"job_id": "job_…", "runs": ["run_…", …]}
```
Solution（`GET /lab/api/runs/{run_id}`）：
```jsonc
{"run_id": "run_20261015T…_ab12", "job_id": "job_…", "scenario_id": "…", "problem_class": "…",
 "instance_sha256": "…", "frame": {…同 Scenario.frame…}, "cost_unit": "…",
 "algorithm": {"id": "…", "name": "…", "source": "…", "origin": "…", "version": "…"}, "params": {…},
 "state": "queued"|"running"|"done"|"error"|"timeout"|"canceled",
 "status": "optimal"|"feasible"|"infeasible"|"no_solution"|null,
 "objective": {"value": 1234, "unit": "cm_equivalent", "lower_bound": null},
 "routes": [{"vehicle": 0, "nodes": [0, 3, …] | null, "sequence": [task ids], "services": [{"task": 0, "position": 3}],
             "polyline": [[x,y], …], "cost": 512, "load": 4, "mode_chain": […]|null}],
 "check": {"checker": "src/research/src/urp_research/turn_modes/checker.py", "source": "project",
           "valid": true, "errors": [], "computed_cost": 1234, "details": {…}},
 "map_check": null | {"checked": true, "collision_free": true, "min_clearance_m": 0.71, "robot_radius_m": 0.175,
                      "violations": [{"route": 0, "segment": 5, "point": [x,y], "clearance_m": 0.1}]},
 "metrics": {"cost": 1234, "length": 52.3, "length_unit": "m"|"unitless", "n_routes": 2, "n_tasks": 6,
             "turns": 7, "turn_penalty_total": 300, "forbidden_turn_violations": 0, "wall_s": 0.21, "cpu_s": 0.2},
 "log": "最后 4 KB 标准错误/输出", "error": null,
 "created_utc": "…", "finished_utc": "…", "label": null}
```
规则：不可行/无解时 `routes: []`、`objective.value: null`，绝不编造路线；`check` 必须由独立检查器给出（未检查则 `check: null` 并在界面显示"未检查"）。地图坐标场景必须给出 `map_check`。

### 2.5 Recommendation（`POST /lab/api/recommend {scenario_id, instance?}`）
```jsonc
{"problem_class": "turn_routing", "policy": "rules-v1",
 "features": [{"name": "任务数", "key": "n_tasks", "value": 6, "unit": null}],
 "learned_selector": {"id": "urp.cvrp_selection.knn_crc"|"lab.cvrp.knn_crc.v1", "status": "unavailable"|"available"|"not_applicable"|"out_of_scope",
                      "reason": "训练数据未恢复：缺少 data/research/cvrp-selection-crc/data/raw.jsonl", "required": ["…路径…"], "prediction": null},
 "ranking": [{"algorithm_id": "urp.turn_mode_dp", "rank": 1, "applicable": true, "suitability": "推荐"|"可用"|"不适用",
              "reasons": ["任务数 6 ≤ 12，精确 DP 可在预算内求得最优", "…"], "suggested_params": {"time_limit_s": 10}}],
 "recommended": "urp.turn_mode_dp", "explanation": "…一句话…"}
```
默认按实例特征与算法条件使用 `rules-v1`。本地 CVRP 原型 `lab.cvrp.knn_crc.v1` 有独立的 60/30/30 训练/校准/测试记录，模型状态为 evaluated 且指纹正确时，在已评估的规模/容量/需求范围内使用 `knn-crc-local-v1`；额外返回 prediction、model_sha256、budget_s、evaluation 和 scope。范围外回退规则。测试集全部使用固定 PyVRP，零平均增益，不能声称学习推荐优于基线。原历史研究数据仍未恢复。每次 Solution 的 `recommendation_at_submission` 固化推荐快照、实际提交算法及预算匹配状态；不推断用户是否采纳。

### 2.6 Services（`GET /lab/api/services`）
```jsonc
{"services": [
  {"id": "gateway"|"archive"|"solver"|"ros"|"sim"|"rviz"|"gazebo_gui"|"fields2cover",
   "name": "档案后端", "kind": "process"|"check",
   "state": "running"|"stopped"|"starting"|"stopping"|"ready"|"degraded"|"failed"|"unavailable",
   "detail": "…", "pid": 123|null, "port": 4180|null, "url": "…"|null, "started_utc": "…"|null,
   "controls": ["start","stop","restart"], "log": "archive"|null,
   "facts": [{"label": "Python", "value": "3.12.13"}], "known_issues": ["…"]}]}
```
`POST /lab/api/services/{id}/{start|stop|restart}`（JSON body 可选，如 sim：`{"world":"warehouse","gui":true,"rviz":true}`）。
`GET /lab/api/logs/{log}?tail=400` → `{"log": "archive", "path": "…", "lines": ["…"]}`；`GET /lab/api/logs` → 可用日志列表。

### 2.7 仿真
- `GET /lab/api/sim/state` → SimState：
```jsonc
{"session_id": "sim_…"|null, "phase": "stopped"|"starting"|"undocking"|"localizing"|"nav2_starting"|"ready"|"executing"|"stopping"|"failed",
 "world": "warehouse"|null, "spawn": {…}|null, "components": {"sim": "running", "gui": "off"|"running", "rviz": "off"|"running", "localization": "active", "nav2": "active"},
 "robot": {"t_sim": 123.4, "ground_truth": [x,y,yaw]|null, "amcl": [x,y,yaw]|null, "speed": 0.2} | null,
 "execution": SimRun|null, "errors": ["…"], "warnings": ["…"], "stages": [{"name":"…","wall_s":12.3}],
 "known_issues": ["ros_gz_bridge 0.244.26 退出时间歇堆损坏（-6），见 setup/2026-10-15/deployment/REPORT.md"]}
```
- `POST /lab/api/sim/session {"world": "warehouse", "spawn": {...}?, "gui": false, "rviz": true, "localization":"amcl"}` 启动；localization 默认为 amcl，可选 ground_truth（显式的理想定位实验，AMCL 仅旁路观测，不能用于证明传感器定位能力）。`DELETE /lab/api/sim/session` 有序关闭；`POST /lab/api/sim/gui {"on": true}`，`POST /lab/api/sim/rviz {"on": true}`。
- `POST /lab/api/sim/runs {"run_id": "run_…", "mode": "follow_path"|"nav2_waypoints"}` → 202 SimRun；`GET /lab/api/sim/runs`、`GET /lab/api/sim/runs/{sim_run_id}`、`POST /lab/api/sim/runs/{id}/cancel`。不适用（基准坐标、世界不一致、地图检查不通过且模式为 follow_path）返回 422 `{"error":"not_simulatable","message":"…"}`；已运行世界不一致为 409 `world_mismatch`。
- SimRun：
```jsonc
{"sim_run_id": "sim_run_…", "run_id": "run_…", "session_id": "…", "world": "warehouse", "mode": "follow_path",
 "state": "queued"|"approach"|"executing"|"succeeded"|"failed"|"canceled",
 "localization": "amcl"|"ground_truth", "navigation_profile": {…参数文件、来源 SHA256、覆盖值与实测参数…},
 "controller": "FollowPath"|"FollowCoverage", "progress": {"leg":1,"legs_total":5},
 "sources": {"route_plan": "URP · 转弯模式分层 DP (src/research/…)", "approach": "Nav2 NavigateToPose (NavFn+DWB)", "tracking": "Nav2 FollowPath (DWB 控制器)"},
 "planned": {"path": [[x,y],…], "length_m": 52.1},
 "tasks": [{"task": 0, "label": "A3", "xy": [x,y], "state": "pending"|"reached"|"missed", "t_sim": null, "distance_m": null}],
 "actual": {"ground_truth": [[t_sim,x,y,yaw],…], "amcl": [[t_sim,x,y,yaw],…]},
 "nav2": [{"action": "follow_path", "status": 4, "status_text": "SUCCEEDED", "t_sim": 12.3}],
 "metrics": {"duration_sim_s": 210.4, "duration_wall_s": 212.0, "actual_length_m": 53.0, "cross_track_mean_m": 0.06,
             "cross_track_max_m": 0.21, "cross_track_p95_m": 0.15, "final_error_m": 0.12, "tasks_reached": 6, "tasks_total": 6},
 "error": null, "report": "src/lab/runtime/sim/<session>/runs/<id>.json", "created_utc": "…", "finished_utc": "…"}
```
任务"到达"判定：真值位置进入任务点 `task_radius_m`（默认 0.35 m）且按计划顺序；缺失数据填 null，不插值伪造。终态必须同时含 `finished_utc` 和最终指标才写入数据库，取消状态过渡期间继续轮询。metrics 额外包含 actual_map_check 和 planned_to_actual_max_m（计划几何到实际轨迹的最大距离）；覆盖任务含 actual_working_coverage_fraction、actual_field_coverage_fraction、actual_footprint_in_field、coverage_required_fraction（0.90），不以 0/0 访问任务作为成功依据。

### 2.8 SSE `GET /lab/api/events`
`event:` 类型与 `data:` JSON：`services`（完整 services 列表，状态变化时）、`job`（`{job_id, run_id, state}`）、`run`（完整 Solution，完成时）、`sim_state`（SimState，≤ 4 Hz，当前为完整状态与轨迹快照）、`sim_run`（SimRun 完成或状态变化）、`log`（`{log, lines}`；当前前端通过日志接口轮询）。心跳 `event: ping` 每 15 s。

### 2.9 其他
- `GET /lab/api/health` → `{"status":"ok","version":"0.1.0","executes_solvers":true}`
- `GET /lab/api/maps/{world}` → `{"world","resolution","origin","width","height","image":"/lab/api/maps/{world}.png"}`；`.png` 为灰度栅格（行 0 在图像顶部，对应 map y 最大处）。
- `GET /lab/api/runs?scenario_id=&limit=` → `{"runs":[Solution 摘要…]}`；`DELETE` 不提供（历史保留）。
- 导出：`GET /lab/api/runs/{run_id}/export?format=json|csv|geojson`、`GET /lab/api/sim/runs/{id}/export?format=json|csv`、`POST /lab/api/compare/export {"run_ids":[…], "format":"csv"|"json"}`。文件名带 run id 与 UTC 时间。
- 错误格式统一 `{"error": "code", "message": "中文说明"}`。网关只监听 127.0.0.1；POST 只接受 `application/json`，拒绝跨源写入（Origin 与 Host 不一致 → 403）。

## 3. Python 模块接口（网关 ↔ 核心）

```python
# urp_lab.paths
REPO, LAB, RUNTIME, RESEARCH_SRC, FRONTEND_DIST, DEPLOYMENT  # pathlib.Path
# urp_lab.scenarios
list_scenarios() -> list[dict]           # 摘要
get_scenario(scenario_id: str) -> dict   # 完整 Scenario；KeyError 若不存在
validate_instance(problem_class: str, instance: dict) -> dict   # 返回规范化 instance；ValueError(中文) 若非法
world_map(world: str) -> dict            # §2.9 元数据；map_png(world) -> bytes
# urp_lab.solvers
catalog() -> list[dict]                  # §2.3
run_algorithm(scenario: dict, instance: dict, algorithm_id: str, params: dict) -> dict
    # 在当前进程内求解+检查+地图检查，返回 Solution 中的 status/objective/routes/check/map_check/metrics/algorithm 字段
# urp_lab.worker  (python -m urp_lab.worker < request.json > result.json)，网关用子进程+墙钟预算调用 run_algorithm
# urp_lab.recommend
recommend(scenario: dict, instance: dict) -> dict   # §2.5
# urp_lab.export
export_run(solution: dict, fmt: str) -> tuple[bytes, str, str]  # (data, media_type, filename)
export_sim_run(sim_run: dict, fmt: str) -> tuple[bytes, str, str]
export_compare(solutions: list[dict], fmt: str) -> tuple[bytes, str, str]
# urp_lab.simplan
to_sim_plan(solution: dict, scenario: dict, mode: str) -> dict
    # 生成会话 /execute 负载（§4），不适用时 raise NotSimulatable(中文原因)
```

## 4. 仿真会话控制接口（网关 ↔ ROS，127.0.0.1:4191，仅本机）

启动：`bash setup/profile.sh simulation /usr/bin/python3 src/lab/ros/urp_sim_session.py --session-id ID --world warehouse --spawn X,Y,YAW --runtime DIR --port 4191 [--gui] [--rviz]`（先 `source /opt/ros/humble/setup.bash`）。默认启用 `--tf-candidate --pin-gui-plugins --ordered-bridge-stop` 等价行为；环境变量 `URP_TF_FIX=0`/`URP_GUI_FIX=0`/`URP_BRIDGE_FIX=0` 可关闭（与 `setup/run.sh navigation` 一致）。

- `GET /state` → SimState（§2.7，`execution` 为当前/最近一次运行）。
- `POST /execute`：
```jsonc
{"sim_run_id": "…", "run_id": "…", "mode": "follow_path"|"nav2_waypoints",
 "path": [[x,y],…],                      // follow_path：URP 规划折线（map 米）；网关已按 0.05 m 加密并去重
 "waypoints": [{"task": 0, "label": "A3", "x": 1.0, "y": 2.0, "yaw": null}],  // 有序任务点
 "tasks": [{"task":0,"label":"A3","xy":[x,y]}], "task_radius_m": 0.35,
 "sources": {…同 SimRun.sources…}, "planned_length_m": 52.1, "budget_s": 900}
```
→ 202 `{"accepted": true}`；正在执行时 409。
- `POST /cancel`、`POST /gui {"on":bool}`、`POST /rviz {"on":bool}`、`POST /shutdown`（有序关闭后进程退出，写 `session-report.json`）。
- `GET /runs/{sim_run_id}` → SimRun（含完整轨迹）。
- ROS 话题（供 RViz）：`/urp/planned_path`（nav_msgs/Path，transient local）、`/urp/actual_path`（真值轨迹，nav_msgs/Path）、`/urp/tasks`（visualization_msgs/MarkerArray：待访/已达/未达三色 + 标签）、`/urp/status_text`（Marker 文本）。Nav2 自身路径仍为 `/plan`，在 RViz 中用不同颜色。


## 5. 已实现的验收约束（2026-10-15）

- 默认 `maze-inspection`：官方 maze 世界，两点巡检，4.30 m 路线，490 cm_equivalent 成本。是集成验收场景，不是农业环境结论。仓库货架仅模拟静态行间通道。
- 仿真实验 JSON 导出在 SimRun 顶层增加 `planning_solution`，包含完整原始规划；CSV 仍只含实测轨迹。
- Solution 同时保留 `instance`、`scenario_snapshot`（深拷贝）、`raw_result`、`reproducibility`（Python/包版本、源文件 SHA256、种子用途、时间停止准则）、`process`（真实退出码、墙钟预算、原始日志路径）。PyVRP 使用随机种子；精确算法无随机性；此版 OR-Tools GLS 不设置随机种子。墙钟终止的启发式结果未承诺逐位复现。
- 精确求解进程有 SIGALRM 时间上限；主进程另有预算 + 2 s 墙钟看门狗，超时/取消终止其拥有的进程组。非零退出不能因 stdout 中有 JSON 而变成成功。
- 地图未知区与边界外均占据；EDT 对单元格尺寸作保守扣减，按半个栅格采样所有路径段并扣减采样间误差界。要求机器人半径 0.175 m + 0.05 m 余量，不只检查离散节点。该圆足迹用于官方 TB4；其他机器人需新的足迹及控制器适配。
- `/execute` 的 `legs` 为加密原始几何边（0.05 m），F2C 则为连续的整条作业行及随后的 Dubins 转弯（0.02 m）。拼接必须与独立检查过的 polyline 相同，禁止断开的多路线隐式跳跃。闭环不能整条直接交给 FollowPath，否则起终点相同可能立即结束。每段端点真值误差、实际到计划及计划到实际的最大距离均须 ≤0.35 m，访问任务还须按序全部到达。覆盖任务还须实际内缩作业区覆盖 ≥90%、足迹在田块内；所有类型均检查实际整段足迹与地图。允许 TB4 原地转向，不把规划曲率约束当作实机运动学验证。
- 会话复制官方导航 YAML 后施加仿真参数，不写系统目录。默认 AMCL 使用 180 束激光及低噪声里程计配置；关键参数通过 ROS 服务读取核实后才就绪。访问路径用 DWB，覆盖路径用已安装的 RPP（FollowCoverage，0.18 m lookahead，碰撞检测开启）。实际参数文件及哈希随会话归档。
- `approach_trajectory` 与 `tracking_trajectory` 分别保存，跟踪指标排除接驳段。`nav2_plans` 保存 Nav2 `/plan` 及阶段，逐点导航的成功不能解读为执行原算法几何路径。真值 Pose_V 桥接头时间为 0 时，样本取最新 `/clock`；不声称严格同步采样。AMCL 保留自身时间戳。
- SimState 有 `telemetry` 消息计数、数据年龄和 map→base_link TF 年龄；执行中时钟、scan、odom 或真值中断会失败。必需启动器退出、必需子节点提前退出（含 rc=0）、Nav2 心跳故障均导致会话失败及清理；模型 create/controller spawner 的正常一次性退出除外。窗口单独退出会告警。
- 每会话预审官方 SDF、Fuel 模型、碰撞网格与当前 Fortress 使用的材质贴图，记录文件哈希。Fuel 模型数量按规范化 owner/name 去重，mesh URL 不能重复计数。Classic 的不适用材质脚本单列 `inactive_classic_materials`，不跳过活动 PBR 贴图。实际地图/碰撞一致性仍需传感器证据，清单完整不等于地图已验收。
- 正常关闭：取消活动动作、观察停车、暂停物理、关闭 Nav2/定位生命周期、逐个桥接退出、回收本会话进程组，保存 `session-report.json`。强制终止、异常退出、生命周期未正常关闭或残留进程不得报告 PASS。桥接 `_exit` 只缓解 main 返回后的 teardown 崩溃，不修复内存根因，保留 main 返回码；库/源码指纹不符则拒绝加载。
- `POST /lab/api/shutdown {}` 为整体有序关闭；API 请求不伪造 SIGINT。Ctrl+C 使用正常信号语义，终端返回 130 表示用户中断，不代表所有子组件返回 0；以清理报告逐项判断。
- 覆盖基线分别报告内缩作业区面积、扫掠覆盖面积/比例及 `turn_radius_enforced=false`。检查器复核扫掠和连接段；路线跑完不能声称全田块覆盖。所有输出的 `.geojson` 是带本地坐标说明的几何数据，**不是 WGS84/RFC7946 经纬度文件**，不得直接用于地理定位。
- 用户入口及证据索引只维护在 `setup/README.md` 和 `setup/2026-10-15/integration/REPORT.md`；本契约不是第二份操作指南。
