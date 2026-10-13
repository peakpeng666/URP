# VRPTW 路线记录读取扩展（2026-10-07）

## 交付边界

从最新上传底包发展出的标准库 SQLite 后端做增量。原 `backend/store.py`、`backend/adapters.py` 完全不改；五类旧实验及其 690 指标、28 附件仍走原接口。新增 `backend/routes.py`、CLI 导入分支及 GET 路由，没有前端或布局改动，没有浏览器视觉验收，也没有部署。

这是已有实验产物的数据读取层，不是路线求解 API。服务仍只监听 127.0.0.1。新增路线端点只接受 GET；原 POST `/api/import` 和 `/api/compare` 为兼容保留。没有执行候选代码、源 `checker.py`、求解器或外部模型。

## 从私有真实档案重建

VRPTW 完整实验保留在[私有归档](https://drive.google.com/file/d/1K2-CnygJC-RpODyU9u7GpQLyClXvEg4T/view)，ZIP SHA-256 为 `3069b7cc3ab97443188eabf76b34d574fcb4652c1a249e5f9eb6ccfea291547f`。用既有访问权限下载并核验后解压；不用把整份原始数据提交到 Git。

```sh
cd research_console
python3 -m backend --db backend_data/routes.sqlite3 bootstrap --package-root "$PACKAGE_ROOT"
python3 -m backend --db backend_data/routes.sqlite3 import-vrptw "$VRPTW_SOURCE_ROOT"
python3 -m backend --db backend_data/routes.sqlite3 serve --import-root "$PACKAGE_ROOT" --port 4180
```

以上命令以独立后端模块为例；完整面板源码包则先进入 `bpp-research-console`，其余命令相同。

`PACKAGE_ROOT` 是 README 中固定旧五包的实际路径。`VRPTW_SOURCE_ROOT` 是含 `inputs.json` 等文件的目录。可通过 `import-vrptw --id MY_ID` 自定义实验 ID。导入仅选择八项原产物：inputs、routes、map_backend、protocol、freeze、verification、self_check 和 checker 源文件；原字节完整留存为 SQLite 附件。另生成一份 JSON 读取索引，临时标准包经现有原子导入流程入库。

已有 DB 无须迁移表结构；新实验沿用原不可变版本机制。相同档案重复导入重用相同 revision/fingerprint；源证据变化产生新版本。索引是可重建衍生物。服务没有实时源目录扫描，导入后原文件变化不会修改已入库记录。

## GET 端点

- `/api/experiments/{experiment}/instances`：输入实例，含所有任务点、仓库、需求、时间窗、车辆数/容量及输入来源
- `/api/experiments/{experiment}/runs`：run 导航索引、状态及来源；支持 `?instance=G12_tight` 和 `?solution_status=partial`
- `/api/experiments/{experiment}/runs/{run}`：单条记录、任务点、所有车辆路径/时间表、未服务任务、独立 checker 结果及来源
- `/api/experiments/{experiment}/runs/{run}/vehicles/{vehicle}`：零起点车辆 ID；返回选中车辆、输入点、该 run 的未服务任务与 checker
- 以上均支持 `?revision=1`；省略表示最新版本

例如 run ID `G12_tight.distance_first`。这些 run ID 是明确新增的 `instance + '.' + method` 导航标识，源档案没有原生 run ID。`source_run_id` 保持 null。

常见响应：200 成功；400 无效状态/编号/revision；404 未知实验、run、车辆、版本或没有路线扩展；405 对新路线端点 POST。旧非路线实验不会凭空得到路线记录。正数 revision 与文件相对路径受基本校验；原附件拒绝符号链接、越界和常见凭据内容的规则不变。

## JSON 契约

每份响应有 schema_version、experiment_id、revision、experiment_fingerprint 和 semantics。列表与对象不依赖屏幕尺寸；手机和电脑前端可使用同一 JSON 契约，但这不表示当前 UI 已接线或完成响应式视觉验证。

`runs` 列表提供轻量导航字段，单 run 详情提供：

- `execution_status=completed`：当前格式已记录终态，不等于全服务成功
- `source_status`：原始 `complete` / `optimal` / `optimal_max_coverage` / `replayed_capacity_only_optimum` / `proven_infeasible`
- `solution_status=feasible`：checker 确认路线合法且全部任务服务；仅此时 `full_service_success=true`
- `partial`：路线合法但漏服务；`unserved_task_ids` 保留 checker 的 missing
- `infeasible`：全服务 oracle 证明无解，路线与完整目标保留 null，`solver_error=null`
- `invalid`：存在约束违规的候选路线，例如纯容量距离最优解回放后迟到
- `unknown` 是读取契约保留状态；当前冻结源格式不接受未知运行状态冒充 completed

无解 run 的车辆端点仍返回 200，但 `vehicle=null`、`checker.status=no_candidate`、`unserved_task_ids=null`。不存在候选路线时，missing 列表不适用，不能伪造为空列表或当作实际服务了零任务。候选空车则是有记录的空路线，有空 stops，并保留回仓时刻；两者不同。

车辆对象保留原 `route/load/overload/distance/stops/return_time/return_leg_distance/depot_lateness`。`path_node_ids` 和 `path_coordinates` 加入出发与返回仓库。各站保留原 arrival/wait/start/depart/window/lateness/demand/leg_distance，并新增：

- `sequence`：从 1 起的服务顺序
- `service_start`：原 start 的显式别名
- `load_before/load_after`：按路径累加的已服务需求，衍生于原 demand
- `onboard_load=null`：没有提货/配送车载货流模型，不能声称知道物理车上载荷

`semantics.distance_model=euclidean`，合成笛卡尔坐标、任意距离/时间单位、速度 1；`is_geographic=false`、`is_road_network=false`。路径是连接服务点的欧氏线段，不能作为真实道路几何、导航时长或经纬度使用。窗口约束作用于闭区间开始服务时刻，允许等待。

## 可追溯性与 checker

每个 run 的 provenance 同时包含：

- `spec_id`：原 protocol.study_id；`spec_sha256`：沿用冻结协议 SHA-256
- `input_file_sha256`：沿用冻结 inputs.json SHA-256；`input_artifact_id/input_locator` 指向输入数组
- `instance_sha256`：明确新增的单实例规范 JSON 衍生哈希，算法写在 instance_hash_source
- `run_sha256`：明确新增的 routes.jsonl 原行字节 SHA-256（不含换行）；`artifact_id/locator` 指向原附件和行号
- `source_run_id=null`，`run_id_source` 说明导航 ID 派生规则

导入核验原 freeze 的 protocol/input/checker 三项哈希、map 与 inputs/routes 全量一致、候选路线与时间表/缺失点/重复点一致、当前单位合同、验证报告记录数。源 Python 只保存为证据字节，不 import、不执行。

`checker` 保留来自既有独立 checker 的原 audit、实现哈希、route_feasible/full_service_feasible。`checker.status=passed` 仅表示候选路线约束通过，partial 仍可 passed；`full_service_success` 必须另看。归档 verification 报告作为已记录证据返回，接口不谎称每次读取重新独立计算或重新证明最优性。导入一致性验证也不是防伪签名或完整科学认证。

## 测试与复现

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
VRPTW_SOURCE_ROOT="$VRPTW_SOURCE_ROOT" RESEARCH_CONSOLE_PACKAGE_ROOT="$PACKAGE_ROOT" \
  python3 -m unittest discover -s tests -p 'integration*.py' -v
```

独立单元测试使用两输入/四记录的显式合成 fixture，未携带整份研究原始数据。集成测试需要真实档案，缺失即失败，不生成替代结果。可设置 ROUTE_INTEGRATION_DB 为不存在的新 DB 路径，ROUTE_INTEGRATION_REPORT 为 JSON 报告路径。

实测覆盖 240 run、480 车辆响应、1499 个候选服务站、原始源字段逐项相等、15 无解 null、G12 紧窗漏点、旧五包 690 指标和 28 个附件原字节 SHA-256、幂等、同口径比较、跨预算拒绝与只读路线端点。没有重跑历史实验、没有用浏览器验收、没有验证公网/多用户部署。
