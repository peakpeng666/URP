# 后端接口

本机 `http://127.0.0.1:4180`，JSON响应。数据位置：`../../data/packages`；数据库：`backend_data/research.sqlite3`。历史记录接口读取已有档案；新增受控CVRP任务接口调用研究runner，并保存实际结果与独立验算证据。详细输入、预算和失败口径见[任务契约](docs/JOBS_API.md)。

## HTTP

| 方法 | 路径 | 用途 |
|---|---|---|
| GET | `/api/health` | 数据API与任务模块状态；可运行时`mode=local_import_query_and_cvrp_jobs`、`executes_experiments=true`，并返回精确`execution_scope`、算法可用项与限制 |
| GET | `/api/algorithms` | 本期Jobs API注册的算法、实际安装状态、输入和预算限制 |
| POST | `/api/jobs` | 接收严格CVRP数值请求，持久化后返回202及任务身份 |
| GET | `/api/jobs?limit=100&offset=0` | 分页任务列表及覆盖全部已接收尝试的状态计数 |
| GET | `/api/jobs/{id}` | 已接受请求、不可变输入身份、执行源码身份、原runner结果与错误 |
| GET | `/api/experiments` | `experiments`数组 |
| GET | `/api/experiments/{id}?revision=1` | 完整记录；省略revision取最新 |
| GET | `/api/experiments/{id}/artifacts/{artifact_id}?revision=1` | 原字节；响应头 `X-Content-SHA256` |
| POST | `/api/import` | `{"package":"selector"}`，只能导入import-root内相对目录 |
| POST | `/api/compare` | `{"items":[{"experiment_id":"selector","metric_id":"..."},...]}` |
| GET | `/api/experiments/{id}/instances` | 任务点及原输入身份 |
| GET | `/api/experiments/{id}/runs?instance=...&solution_status=...` | 运行列表 |
| GET | `/api/experiments/{id}/runs/{run_id}` | 原run与核验语义 |
| GET | `/api/experiments/{id}/runs/{run_id}/vehicles/{vehicle_id}` | 原车辆ID、路线与逐站时间表 |
| GET | `/api/route-comparison?experiments=id1,id2&revisions=1,1&instance=...` | 同一问题合同下的路线记录比较 |

路线读取支持 `revision`，默认最新正整数版本。比较的revisions数量须等于experiments数量。所有查询拒绝未知、重复或空字段。POST仅接受application/json，正文1字节至1MiB；需要唯一Content-Length，不支持Transfer-Encoding，拒绝重复JSON键。错误响应为 `{"error":"代码","message":"说明"}`。无效字段400、非本机Host或跨源请求403、不存在404、路线写入405、身份冲突或不可比较409、正文过大413、媒体类型415、算法不可用422、队列已满或数据库暂不可用503。

仅接受服务实际端口上的`127.0.0.1`或`localhost` Host；带Origin的请求必须与该Host同源。最多16个活跃HTTP请求，读取超时10秒。浏览器前端应使用先检查本机Host/Origin再转发的同源代理，不应把公网Origin或任意Host改写成本机来源。

## 数据和比较

每包放 `experiment.json`，`schema_version=1`；字段包括 `id`、`title`、`status`、`provenance`、`counts`、`metrics`、`artifacts`、`failure_reason`、`failures`。实物示例：[selector](../../data/packages/selector/experiment.json)、[budget](../../data/packages/budget/experiment.json)。附件引用包内安全相对路径，记录SHA256，导入后原字节进入不可变版本。描述符上限1MiB，单附件32MiB、单包附件合计128MiB、最多512附件；容器类型、有限数值、凭据字段与响应媒体类型在事务前检查。Linux读取相对文件时逐层禁止符号链接，且只读取普通文件。同一实验ID的路线格式与输入身份在SQLite写事务内再次核对，避免并发导入覆盖身份。

counts必须同时声明unit和scope；fit、decision、trajectory、checkpoint和historical run不混加。未知值null，0须有真零证据。完成执行与合法全服务分开，恢复过的失败仍在failures中。

metrics比较合同须同时一致：metric、unit、direction、cohort、protocol、budget、aggregation、reference。未知值、未完成记录或不同预算不进入完整结果比较；差值只是描述性结果，不自动获得显著性结论。

## 四种显式路线源格式

```sh
.venv/bin/python -m backend import-routes /path/to/archive --format FORMAT --id independent-id
# 若需要已有授权实例，追加 --input-dir /path/to/inputs
```

| FORMAT | 对应来源和要求 |
|---|---|
| `vrptw-frozen-v1` | 冻结240-run档案；[路线合同](docs/ROUTE_API.md) |
| `vrptw-mature-solver-v1` | 成熟求解器96-run档案；[成熟格式](docs/MATURE_ROUTE_API.md) |
| `vrptw-archived-solomon-v1` | 用户存档百客户112-run档案；输入默认档案inputs，可显式指定 |
| `vrptw-solver-portfolio-v1` | 配置组合224-run档案；清洁包不带实例，须指定真实授权input-dir |

后两者详见 [公共路线合同](docs/PUBLIC_ROUTE_API.md)。导入核对冻结哈希及已返回路线，不运行solver、不下载替代输入。`no_solution`保持routes/null、vehicles/[]和问题可行性unknown；缺失或无返回不能编造路线。原车辆ID可稀疏，未使用车辆为vehicle/null；累计需求不假称物理实时载荷。用户存档56名称只有4坐标geometry groups，官方字节身份尚未证实；固定K下距离目标与官方先车辆数目标不同，BKS gap为null。

## 前端待接入

1. 用health和experiments替换静态实验入口，并明确显示experiment ID和revision。
2. 从记录渲染状态、counts、metrics、failures；附件按SHA下载，不把预算、样本单位或未知值混写。
3. 路线页接instances/runs/run/vehicle；按solution_status展示真实返回，保留时间窗、累计需求和原run身份。
4. 比较页使用后端合同；409须显示原因，不在前端忽略失败或改算跨口径排名。
5. 在Ubuntu原生外壳选定同源本机代理或原生桥接。4173与4180目前是不同源，后端未开放CORS且拒绝跨源POST；不能直接假定浏览器fetch可用。

该后端面向本机使用，当前无身份系统或公网部署合同。原生Ubuntu外壳和物理地图/车辆约束不属于本期CVRP任务契约。
