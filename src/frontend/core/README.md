# 确定性回放与数据加载接口 v1

`replay.mjs` 无框架、无网络、无依赖，只消费已记录的分配。它不运行 BF/EoH、不重新训练、不生成研究数据。Node 24 与现代浏览器原生 ES module 均可使用。

```js
import { ReplayEngine, ReplayComparison } from './core/replay.mjs';
import { ReplayDataClient, fetchJSON, StaleResponseError } from './core/data-client.mjs';

const catalog = await fetchJSON('/data/catalog.json');
const stream = catalog.streams.find(s => s.split === 'confirmation');
const left = stream.runs.find(r => r.policy === 'SELECTOR');
const right = stream.runs.find(r => r.policy === 'BF_then_EoH');
const client = new ReplayDataClient(); // 每个可独立切换的回放面板一个实例
const comparison = await client.loadComparison(left, right, { processed: 500 });
const state = comparison.getState();
const bins = comparison.getBins('left', { offset: 0, limit: 80 });
const decision = comparison.getDecision('left');
```

## 输入与单位

构造器接受 `public/data/runs/<run_id>.json`：`schema_version=1`、`run_id`、`instance_id`、`policy`、`capacity`、`items`、`assignment`、`pre_remaining`、`post_remaining`、`feasible_counts`、`used_bins_after`、`remaining`。前六种轨迹数组与 `items` 等长；`remaining` 长度是槽数。正式数据均为 5000 项、5000 槽、容量 100；短序列仅用于单元测试夹具。

`assignment` 是从 0 开始的真实槽索引，可稀疏，绝不能用已用箱数作为槽索引。`remaining` 是终态残量，不能索引成逐时刻矩阵。体积与容量沿用原包数值单位；`feasible_counts` 统计包括空槽在内的所有可行槽。

可选字段：`branch`、`prefix_features`、`decision`、`selector_consumed_count`（优先）或 `switch_after`（默认 500）。`decision` 中仅复制原始 `features`、`neighbors`、`squared_distances`、`predicted_final_bins`、`selected_index` 与转换器补充的 `neighbor_rows`、`feature_names`。

## ReplayEngine

| 方法/属性 | 语义 |
| --- | --- |
| `new ReplayEngine(run, {checkpointInterval: 250})` | 复制并检查输入数组，不修改调用方数据；初始位置 0 |
| `seek(processed)` | 精确定位到已处理项数，返回状态。仅接受整数 `0..totalItems` |
| `step(delta=1)` / `reset()` | 支持正负单步，端点夹紧；重置到 0 |
| `processed`, `totalItems`, `metadata` | 当前项数、总项数、无事后结果的元数据副本 |
| `getState({retrospective:false})` | 当前状态，详见下方 |
| `snapshot()` | `{processed,remaining:Float64Array,counts:Uint32Array}`；全部真实槽的当前状态拷贝，供 Canvas 批量绘制 |
| `getBin(bin,{includeItems:true})` | 指定槽当前残量、已到达物品列表 |
| `getBins({offset:0,limit:100,usedOnly:true,includeItems:false})` | `{bins,offset,limit,total}`；按槽号递增；offset 是过滤后行偏移 |
| `getItems({start:0,limit:100,retrospective:false})` | 已到达物品片段；start 是从 0 开始的物品索引 |
| `getCurve({retrospective:false})` | `[{processed,usedBins,totalVolume}]`；包含初态点；无采样近似 |
| `getDecision({retrospective:false})` | 500 前只有 `{available:false,reason,requiredProcessed}`；500 后返回原始记录选择 |
| `getFinalResult({retrospective:false})` | 未到终点返回 null，终点返回 `{usedBins,totalVolume,totalItems}` |
| `hasSameStream(other)` | 比较 instance、容量、长度以及全部实际物品值 |

状态包含 `processed`、`usedBins`、`totalVolume`、`unusedCapacity`、`fillRatio`（初态 null）、`activeBin`（初态 null）、`current`（初态 null）、`selectedBranch`、`decisionAvailable`、`atDecisionBoundary`、`decisionBoundary`、`phase`、`finished`、`mode`，以及元数据。`current` 形如：

```js
{index: 499, itemNumber: 500, size: 20, bin: 107,
 before: 39, after: 19, feasibleSlots: 4890,
 usedBinsAfter: 114, openedBin: false}
```

以上数字仅说明字段，不是正式样本。`bin` 是原槽号；界面如显示“第 N 箱”并加一，须标明显示编号与原始索引关系。每个 bin 返回 `{bin,count,remaining,load,used,active}`；`items` 为 `{index,itemNumber,size}[]`，只包含当前已经处理的物品。

`snapshot()` 的数组按原始槽索引对齐，未用槽残量为容量、计数为 0；只含当前时刻，不暴露未来终态。数组是独立副本，可以在渲染端遍历或修改，均不会改变内核或其他快照；定位后应重新取快照。两个 5000 槽数组约 60 KB，避免每帧生成数千个 bin 对象。

在 `processed=500` 时，`current` 仍是第 500 项，选择记录刚好可见，第 501 项未到达。后退到 499 后选择重新隐藏。`published_EoH` 从第一项使用 EoH，`phase` 始终是 `full-policy`；其余策略按边界分为 `prefix` / `decision` / `continuation`，这只是时间段标签，不是算法运行日志。

回放默认不返回未来物品、未来曲线或事后终态。显式 `{retrospective:true}` 可以读取这些视图；界面必须标为“事后对照”。已下载的原始 JSON 和 catalog 汇总本身含历史结果，因此这是一条产品显示规则，不是对浏览器文件的保密机制。观察视角不能把 catalog 中的 `used_bins`、`branch` 或 results 直接混入当前回放信息。

检查点每 250 项以及选择边界惰性缓存。前进与后退都从最近可用检查点恢复；每次定位只发布完整成功状态。运行时验证当步 pre/post、容量、累计箱数与包括空槽的精确 `feasible_counts`；整数容量数据通过残量频次 Fenwick 树在 O(log capacity) 内核对可行数，树随检查点一起恢复。非整数测试数据回退逐槽计数。到终点比较全部槽残量和体积。

构造器验证数值、长度、槽范围；若提供 status 必须为 complete，steps 必须等于物品数，used_bins 必须匹配终态累计箱数。正式 5000 项 schema v1 的选择边界必须为 500。SELECTOR 必须有合法选择对象：正式 5000 项记录按冻结 v1 校验 31 维特征、5 个不重复的 0..143 训练索引、有限非负有序距离、两分支合法箱数预测、选中最低预测分支及 branch 一致。附带 neighbor_rows 时还核对索引/距离对应、训练输入标识、整数标签和预测等于邻居标签均值；prefix_features/feature_names 存在时检查维度对应。这些是加载边界的一致性检查，内核仍不代替 MANIFEST 或冻结 MODEL 的独立重算验证。

## ReplayComparison

`new ReplayComparison(leftRun,rightRun,options)` 自持两个内核。构造时逐项比较输入流，拒绝同名但不同物品或容量的比较；无独立公开引擎引用，避免外部操作造成不同步。

`seek/step/reset` 同时操作两侧，任一失败会回到原同步位置。`getState()` 返回 `{processed,totalItems,left,right,deltaUsedBins}`，差值为左减右。`getBin/getBins/getCurve/getDecision/getFinalResult` 的第一个参数为 `'left'` 或 `'right'`。`getItems` 返回共同物品流的左侧记录，因箱分配可能不同，若需要右侧当前分配应读取 `getState().right.current`。

`snapshot('left')` / `snapshot('right')` 分别返回同一已处理项数下两侧的批量槽状态副本。

## ReplayDataClient

`new ReplayDataClient({fetchImpl:fetch,cryptoImpl:crypto,verifyHashes:true})`。

`loadRun(source,{processed:0,signal,checkpointInterval:250})` 返回 `ReplayEngine`；`loadComparison(left,right,options)` 返回 `ReplayComparison`。source 可为 URL 字符串或 catalog 中的 run 对象 `{data_url,run_id,policy,sha256}`。推荐完整对象，默认使用 Web Crypto 检验原始响应字节的 SHA256，并核对 run_id/policy；未提供哈希时不会谎报已核验。`sources` 副本记录实际 `hashVerified`。

同一 client 的新请求会取消旧请求，并以请求序号检查迟到响应，即使网络层忽略 AbortSignal 也不会写入过期状态。旧 Promise 抛出 `StaleResponseError`（`code='STALE_RESPONSE'`），UI 对此静默；最新失败应显示错误及重试入口。`cancel()` 使待处理请求失效并清空 current。`status` 为 `idle/loading/ready/error`；`current` 在加载或失败时为 null；`error` 保留当前失败。

```js
try {
  const engine = await client.loadRun(selectedRun, { processed: target });
  render(engine);
} catch (error) {
  if (error instanceof StaleResponseError || error.name === 'AbortError') return;
  showLoadError(error.message);
}
```

`DataLoadError.code` 区分 `HTTP_ERROR`、`NETWORK_ERROR`、`BODY_ERROR`、`INVALID_JSON`、`HASH_MISMATCH`、`HASH_UNAVAILABLE`、`INVALID_DESCRIPTOR`、`IDENTITY_MISMATCH`。轨迹结构/状态错误为 `ReplayDataError`。Web Crypto 不可用时明确报错，不会静默跳过要求的哈希核验；本机 localhost 支持安全上下文。

## 测试

在项目根目录运行 `node --test tests/replay*.mjs`。测试覆盖全部已导出的真实 run 终态和形状、真实选择器随机定位、风险/训练/full-EoH 代表样本、稀疏槽、0/499/500/501/5000、观察边界、比较同步、异常回滚、输入不可变、HTTP/损坏 JSON/哈希错误与异步竞争。没有真实导出文件时真实数据用例明确 skip，不声称通过。
