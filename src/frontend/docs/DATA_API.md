# 静态数据接口 v1

所有路径相对站点根路径，数据为本地 ZIP 的派生视图。`python scripts/convert_data.py` 生成 `public/data/`。前端可直接 `fetch('/data/catalog.json')`，无需服务器 API 或云服务。正式页面只用这些真实记录。

- `/data/meta.json`：schema_version、counts、summary（原 SUMMARY）、protocol（精简）、model（冻结 k/mean/scale/x/y/sbs_index）、training_rows、import_validation、project_validation（全量检查未完成时明确 PENDING）、historical_audit、sources。
- `/data/catalog.json`：`{schema_version:1, streams:[...]}`。每流 instance_id/group_id/family/split/order/n/capacity/multiset_sha256、results（CSV 数值）、runs 数组。每个 run 含 run_id/policy/branch/used_bins/status/data_url/sha256/source。训练流只列真实两策略。SBS 与 oracle 为角色/事后汇总，不添加 run。
- `/data/runs/<run_id>.json`：原 JSON 字段 + schema_version/run_id/capacity/items + assignment/pre_remaining/post_remaining/feasible_counts/used_bins_after/remaining 数组（各5000）+ source。包含 decision 的记录额外提供 feature_names、neighbor_rows；所有选择字段为历史事实，不是实时推理。
- `/data/decisions/<instance_id>.json`：selector 决策，features、feature_names、neighbors（0基训练行索引）、squared_distances、predicted_final_bins（BF/BF_then_EoH顺序）、selected_index、neighbor_rows（训练流信息/两分支标签）、selector_consumed_count=500、source。
- `/data/inputs/<instance_id>.json`：输入与来源；大整数 seed 转字符串避免 JavaScript 精度丢失。
- `/data/cells.json`：18个确认 family × order 汇总，`{schema_version:1, cells:[...]}`。
- `/data/evidence/<原包相对路径>`：原始字节的只读复制，可按 source.url 查看/下载，sha256 对应原 MANIFEST。不会加载或执行研究 Python 源码。

`run_id = instance_id + '__' + policy`；policy 枚举 BF、BF_then_EoH、published_EoH、SELECTOR。`null` 表示原记录未提供/该角色不适用，不能当0。每个 source 含 path（原包内相对位置）、url、sha256、bytes。

回放内核在 `core/replay.mjs`，框架无关。时间=已处理项数，0是初态；索引/assignment为0基，UI可加1显示。remaining只表示终态。pre/post_remaining只指当步箱。feasible_counts包含未使用槽。容量和物品量无物理单位，计数单位为箱/项。

当时已知模式：500之前隐藏 decision/最终 branch/事后结果；曲线截到已处理项，不显示下一物品；500时可显示冻结选择及训练邻居，两分支最终结果仅在显式事后模式显示。完整汇总页属于历史视角。训练记录无SELECTOR。

区间是全局确认集的族内多重集组bootstrap（组三种顺序共同抽取）；筛选均值不继承全局区间。风险单列。headroom_recovered_fraction是收回同前缀两分支可改善余地的比例。

## 本项目全量核验结构

`/data/validation.json` 与 `meta.project_validation` 是相同报告：`schemaVersion:1, status:'PASS'|'FAIL'|'PENDING', passed:boolean, generatedAt:UTC ISO字符串, environment:{python,numpy,platform}, coverage:{inputs,runs,trajectorySteps,selectorDecisions,commonPrefixes,riskGroups,confirmationCells,bootstrapReplicates,manifestEntries,freezeHashes}, checks:[{name,status,seconds}], failures:[{check,location,message,type}], sourceHashes, metrics, tolerances, limitations, elapsedSeconds`。PENDING阶段可能只有status/scope，UI须兼容字段缺失；整数/哈希精确比较，浮点绝对/相对容差均1e-12。科学核验不包含浏览器验收，也不认证历史CPU预算。完整说明见 DATA_VALIDATION.md。

性能接口：`ReplayEngine.snapshot()` 及 `ReplayComparison.snapshot(side)` 提供当前时刻 `{processed, remaining, counts}` 数组副本，适合 Canvas 整体渲染；不包含未来数据。数据对象不可直接以最终 remaining 绘制中间状态。
