# 用户存档百客户与配置组合路线接入

本次为现有 GET route API 增加两个明确档案适配器，不创建求解服务：

- `vrptw-archived-solomon-v1`：已有 public_vrptw_benchmark 归档，56输入 × 250/1000ms，112已记录结果。
- `vrptw-solver-portfolio-v1`：已有 solver_portfolio_headroom 归档，56输入 × PCI250/PCA250/SAV250/PCI750，224已记录请求，217合法全服务、7 PCA250无方案超时。

两包使用相同56个授权原文件。第一包112全部合法，合计329合法见证、7无方案，共336个新run。原240+96运行和48逻辑输入不改变；四档案合计672运行、104不同逻辑输入。按原实验与revision分别存储，不混成独立实验重复数。

## 命令与输入

从 `research_console/` 执行，标准库即可；不需要 OR-Tools、联网、API密钥或安装依赖。

```sh
python3 -m backend --db backend_data/research.sqlite3 import-routes /path/to/public_vrptw_benchmark_20261007 --format vrptw-archived-solomon-v1 --input-dir /path/to/authorized/inputs
python3 -m backend --db backend_data/research.sqlite3 import-routes /path/to/solver_portfolio_headroom_20261007 --format vrptw-solver-portfolio-v1 --input-dir /path/to/authorized/inputs
python3 -m backend --db backend_data/research.sqlite3 serve --port 4180
```

缺省输入目录是归档下 `inputs/`。组合归档清洁包不带原始实例，所以必须明确指定已有授权输入目录。输入缺失、字节SHA不同或解析/整数编码SHA不同即拒绝，不下载、不搜索替代文件。

默认experiment ID分别为 `vrptw-archived100-20261007` 与 `vrptw-portfolio-20261007`，可通过 `--id` 指定独立ID。同ID同内容幂等；不能用已属于其他格式/输入集合的ID覆盖。输入的原始文件只读取，解析后的节点会保存在本地数据库的派生索引以支持路线API；原始实例字节不复制为数据库附件，也不放入源码或核验证据交付ZIP。

## 支持边界与核验

这是两份现有固定归档的显式适配。生产代码固定已审阅 `protocol.json`、参数textproto和checker SHA；修改协议/算法参数需要另立版本和适配，不接受仅重算freeze便换语义。

导入会：

1. 验证每个freeze引用文件原字节SHA，不执行档案中的Python。
2. 检查输入原字节、解析语义与完整整数编码（nearest cost / ceil travel / exact service）SHA。
3. 对齐request顺序、原run ID、完整raw与evaluated记录；拒绝缺少结果、重复ID及错配。run ID含预算或配置，实验ID/revision形成外层身份。
4. 使用已审阅且逐字节复制的原 `source/checker.py` 实现重新检查全部返回方案；原文件SHA为 `67ad3171ff4a7b736313226c3e9540d40b8d5021fcbf33acd262a20c86ccf8d5`。只导入后端中固定的 `archived_solomon_checker.py`，不会动态执行来源包源码。
5. 比对连续距离、逐站arrival/service start、返仓、容量、覆盖、原checker完整字段及integer objective。组合记录的原50位Decimal证据保留；后端额外用精确isqrt整数中点判断复核目标。
6. 验证实际计时字段为有限非负秒数；不要求wall和CPU严格有序，因为归档原测量分辨率与边界不同。

没有运行solver、生成候选或再次做实验。完整来源证据作为本地数据库的不可变附件保留；这不是来源真实性的外部公证，也没有给出最优性证明。

## 公共API映射

继续使用原接口，全部GET：

- `/api/experiments/{id}/instances`
- `/api/experiments/{id}/runs`，支持 `instance` 与 `solution_status` 查询
- `/api/experiments/{id}/runs/{run_id}`
- `/api/experiments/{id}/runs/{run_id}/vehicles/{vehicle_id}`
- `/api/route-comparison?experiments={id1},{id2}`

车辆ID使用OR-Tools原ID，允许稀疏，例如只返回2号车时不改成0号。只生成实际返回的非空车辆对象；未使用但在K范围内的车辆GET返回 `vehicle:null`。`routes` 为返回顺序的客户节点数组，`vehicles[].vehicle_id`保持原ID，`path_node_ids`含出发与返回仓库；`source_routes`保留原depot闭环和encoded cumul。`stops`只含客户，返仓单独在 `return_step`。

`checker.audit`提供统一的 `route_feasible`、`full_service_feasible`、`total_distance`、`missing`、`schedules`；`checker.recorded_audit`完整保存原格式核验记录。`vehicles[].stops`给出arrival、wait、service_start、depart、window、lateness、demand与累计服务需求。`load_before/load_after/load`都是累计服务需求或总需求，`onboard_load`为null，未把未知物理实时载荷变成已知量。

状态分开保存：

- `execution_status`表明请求执行是否完成/异常。
- `source_status`保留原evaluated结论，`solver_status`保留原OR-Tools结果。
- `solution_status=feasible`才是合法全服务；partial和invalid独立保留，不把完成执行当全服务成功。
- TIMEOUT无方案映射 `no_solution`，`routes:null`、`vehicles:[]`、`checker.audit:null`、`unserved_task_ids:null`、全服务距离null；`problem_feasibility=unknown`。没有假路线，也没有声称原问题不可行。

## 科学口径与provenance

输入只是用户存档的Solomon命名候选，未获得官方字节同一性证明。56名称仅4坐标geometry groups，不当成56个独立几何样本；两个新档案相同输入也不当成112个新输入。

目标固定为原K上限内距离单目标、全客户必服务。官方SINTEF为车辆数优先再距离，不能跨目标解释gap；`bks_gap_percent:null`并写明不适用。路网/经纬度均false，坐标为存档笛卡尔值，Euclidean distance=time，速度1，闭区间开始服务窗。

250/750/1000ms是名义每次search wall cap。`metrics.solve_cpu_s`、`solve_wall_s`、`model_*`、`total_*`、组合包的 `parse_*`、`check_*` 与 `request_accounted_*`保留原实际秒数。名义750与250×3不被描述为等实际CPU或等总算力。

provenance保留原line SHA及locator、native run ID、输入原字节/解析/编码SHA、原研究协议SHA、参数SHA、checker SHA。两个新归档的共同问题spec与排序输入集合SHA明确标注为派生合同哈希；原协议和原manifest仍是独立来源附件。跨新两包的读取比较可返回336条/56输入/6算法预算组；旧合成48输入与新56输入混合比较会409拒绝。最短已返回合法见证只是所选记录中的描述性参照，不是BKS或最优解。

## 可复验测试与迁移

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
PUBLIC_VRPTW_SOURCE_ROOT=/path/to/public PORTFOLIO_VRPTW_SOURCE_ROOT=/path/to/portfolio VRPTW_SOURCE_ROOT=/path/to/old48 MATURE_VRPTW_SOURCE_ROOT=/path/to/mature48 PUBLIC_VRPTW_INPUT_DIR=/path/to/authorized/inputs python3 -m unittest discover -s tests -p integration_public_routes.py -v
```

新增单测fixture是无solver生成的100节点合成数据，测试通过局部mock替换协议/参数SHA，只在测试过程中生效，不是生产导入开关。真实集成缺数据即失败。另附独立核验脚本与报告，逐项比对329方案、2,842原vehicle、32,900客户站，以及旧336完整字段/API fingerprint。

Ubuntu22.04/Python3.10仍为迁移目标。本轮实际测试是dot云端Linux/CPython3.12.14，仅做Python3.10语法与标准库使用静态兼容检查；没有Ubuntu22.04或Python3.10实机通过声明。未改前端、无浏览器/视觉QA、无部署/上传/push。
