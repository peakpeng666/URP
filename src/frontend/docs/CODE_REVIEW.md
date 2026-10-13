# 独立代码复核记录

2026-10-06，核验子代理只读审阅 scripts/import_data.py、scripts/convert_data.py、core/replay.mjs、core/data-client.mjs。未修改上述文件或原始研究数据。本记录不取代全量数据核验或浏览器验收。

## 四项发现均已修复并复核

1. **已解决，原 P1：旧 PASS 未绑定当前数据。** 转换器现在先运行 verified_sources；拒绝 FAIL/未知状态，要求 PASS 的 passed=true，并逐一核对 MANIFEST/FREEZE/MODEL/MODEL_FREEZE/PROTOCOL 五个 sourceHashes。未核验时仅允许明确 PENDING。原始清单 SHA256 固定为已验证 ZIP 中的值，无法通过替换清单沿用不相干的科学记录。

2. **已解决，原 P1：消费未列入清单的额外记录。** verified_sources 现在要求实际全部文件集合精确等于清单加 MANIFEST 自身；拒绝额外/缺失文件、路径穿越和符号链接。source() 除清单本身外不再提供未列入清单文件的哈希后备。上述检查在任何导出写入之前完成；派生目录也不能位于不可变研究目录内部。转换器的三项信任边界测试已通过，覆盖旧 PASS、FAIL、额外文件和修改清单。

3. **已解决，原 P2：回放 API 未重核可行数。** 构造器要求首项可行数包含全部空槽；每步通过残量频数树独立计算实际可行槽数，普通非整数夹具则扫描槽状态。复核使用真实 SELECTOR 内存副本分别破坏第 1 项和第 500 项 feasible_counts，两次均明确拒绝；未修改研究或导出文件。

4. **已解决，原 P2：回放 API 接受失败状态及畸形决策。** 构造器现在检查提供的 status 与终态 used_bins。SELECTOR 校验特征维数、近邻数量/索引/唯一性、距离非负/排序、预测范围、选择与 branch 的对应、前缀特征，以及 enriched neighbor_rows 与预测均值的一致性。原来四个真实记录内存副本错误分别设置 status='failed'、used_bins=-100、neighbors=[999999]、predicted_final_bins=[0,0]，修复后均已实际复核为拒绝。

以上第 3/4 项的六种破坏与 observed 模式端点检查使用 Node 24 实际执行。真实样本在 0/499/500/501/5000 并后退的过程中，边界前没有决策泄漏、曲线仅包含已处理项、未结束时不返回最终结果。未改写 public/data/、research/ 或验证报告。

## 全量导出一致性复核

新增 tests/test_export_parity.py，只使用真实研究数据；缺少数据直接报错，不跳过、不使用夹具替代。WSL 的项目 .venv、NumPy 2.2.6 实测 3 项测试全部 PASS，19.169 秒：

- 264 份输入分片与 catalog 的 ID/分组/顺序/原始字段逐值一致；大整数 seed 严格按接口约定字符串保存；全部 CSV 结果和真实策略集合一致。
- 768 个导出 JSON 的字节 SHA256 与 catalog 描述符一致；原始 JSON 所有字段（包括 prefix_features/decision/CPU/状态）保持一致；每条六个 5000 整数数组逐元素等于原始 NPZ。
- 120 个决策分片和训练邻居增强字段对应 MODEL_FREEZE/MODEL/原始输入；所有引用的 evidence 复制件与原始 MANIFEST 字节长度和 SHA256 一致。
- meta/model/protocol/summary/cells、历史审计及全量科学核验报告一致；PASS 报告的来源哈希再次匹配当前原始文件。

## 已确认的良好行为

- importer 将 ZIP SHA256 与任务书固定值比较，先验证全部成员/清单再写入；拒绝重复成员、路径穿越、反斜杠、绝对路径、符号链接和已有不一致文件。
- converter 保留多重集/顺序元数据，大整数种子转为字符串；SBS/oracle 留在结果角色中，没有伪造新增运行；训练流仅导出现存两策略。
- 回放默认 observed 视角，未到边界时不公开 SELECTOR 选择和决策；getItems/getCurve 限于已处理项，getFinalResult 在结束前返回 null。未来视角需要显式 retrospective=true。
- 箱号保留真实 slot index，usedBins 独立计数；比较器核对完整物品序列、容量和 ID，并同步进度。
- seek 使用临时状态并在成功后提交，损坏中途不会留下部分回放状态；比较器第二路失败时恢复第一路原进度。
- DataClient 使用修订号和 AbortController 防止旧响应覆盖新请求；完整 descriptor 默认进行 SHA256 验证，并检查 run_id/policy。

## 暂未覆盖

本次审阅时 src/ 尚未出现，前端科学措辞、默认视角、图表模式和 provenance 展示仍待读源码与浏览器验收。历史策略评分正确性的已归档审计与本项目整数轨迹/模型算术核验分开保留。
