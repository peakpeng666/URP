# CVRPLIB 修复包独立对抗审查

日期：2026-10-14 UTC。状态：ACCEPTANCE_RELEASE_READY，故障夹具前置条件修正后复核通过；正式实验计划NOT_FROZEN、正式批次NOT_STARTED。VND原archive独立取回复核仍是明确的来源保证限制，不称已闭环。

## 已闭环证据

1. 按交付README重新执行独立数据审计：53个输入、53份参考均通过；100个原始文件匹配固定提交来源清单，6个新增参考匹配单独来源记录。参考只是“固定版本且独立验算合格”，没有把路线验算等同最优性证明或当前最新BKS。
2. 实测41/6/6例；A13/B13/P11/E2/F2/X12；客户18–523；53约束算例、51底本。E51/P51与E76/P76容量变体为两个重复底本组。原小16 TASKS与原ZIP逐字节相同，SHA256 da287cfafa7024606eab8a4e02948b7144dc72163861a7164cfca9980f341753。
3. 原论文§2确认传统非X固定K约定，41例均满足ceil(总需求/Q)=K，故本面板至多K与恰好K等价。X按§3.3.2不固定路线数。不是简单把文件名K当上限。
4. 六个PyVRP冻结成员逐一对原强基线ZIP比SHA通过，见 audits/cvrplib/reviewer/pyvrp_archive_member_comparison.json；不能只把恢复清单的自洽称原始archive复核。
5. 独立复跑7项精确边长测试，全部通过。数据同事另给全矩阵交叉核验1,350,504有向单元、0差异，证据 audits/cvrplib/recovered_comparison.json（不同于7个单元测试）。

## 对抗发现及修复

审查不可变恢复版时，7个probe有5通过、1失败、1异常；保留 audits/cvrplib/reviewer/recovered_adversarial_before.log。

- 先提交有效解与done再自行SIGKILL的worker，旧版被错误标OK。修复先辨识清理前退出状态，真实资源终止/崩溃不被done或late事件覆盖。
- 缺error_type的合法JSON error事件会导致监督器KeyError。修复事件结构验证，转API_ERROR而不是丢失整次记录。
- 后验score原先只验路线，没有验证候选时间证据及实例/payload身份。现核输入哈希、payload摘要、预算时钟关系以及对应接收事件。
- 将无解和返回非法解明确分为NO_SOLUTION、INVALID_SOLUTION，不宣称数学不可行。

最终15项独立测试全部通过，见 audits/cvrplib/reviewer/adversarial_fixture_v2.log：
- 晚交付但回填早时间戳、未来时间戳、截断JSON、畸形error、SIGKILL假成功、late掩盖crash、成功checkpoint后crash、空结果、非法checkpoint整次失效、参考字段白名单，共10项监督器/接口检查。
- 后验score合法证据、晚时间、错误实例、错误payload、缺收到的事件，共5项。

测试只使用微型人为数值和故障worker，不把任何fixture当公共实验结果。可复现命令在 audits/cvrplib/reviewer/README.md。

## 运行语义与边界

预算真正起点在监督器请求序列化前，包含启动、IPC、导入、建模、初始化、搜索及解交付；文件读取在外，独立checker在后。只接收起点到截止之间发出且收到的checkpoint，后续清理输出不追认。process_wall包含清理，不能当纯搜索时间；CPU是wait4 worker范围，后代和checker另列。超时保留合法incumbent，任何非法checkpoint按预定完整性策略使整次失败，原记录保留。

只支持Linux串行监督，不能并发调用改动同一父进程subreaper状态。只清理同进程组后代，已审查worker禁止Python进程创建；这不是防恶意原生代码/逃逸setsid的系统沙箱。solver收不到名称/COMMENT/BKS/参考路线或manifest，参考只在外部评价器中；导入阶段允许文件读取的边界已披露。

## 科学局限，不是软件故障

- 规模与来源混杂，不能把small对medium/large解释成纯规模效应。
- 公开小16已经使用，其他例历史使用不明，不能说严格未见最终测试集。
- 确定性savings/VND臂的五seed仅是重复运行标签，非五条随机轨迹；不能把种子当独立实例。
- 在当前面板可比较可行率、同合同质量和端到端成本，不能凭这些小例验收声称算法优劣。

## 最终准入证据及尚未执行范围

- 核心99项曾通过，随后主审复跑98/99：畸形输出测试在0.2秒预算得到TIMEOUT_NO_SOLUTION而非预期API_ERROR。该次没有保存子进程阶段原始记录，因此调度/启动延迟是解释而非已证事实；真正缺陷是语义测试假定短预算内必能进入注入点。修订将语义故障预算改5秒，初始化超时测试要求INITIALIZATION_ENTERED标记，独立reviewer晚交付测试要求READY_FOR_DELAY；未修改生产时钟或状态判定。原失败保留，见 acceptance/20261014T085915Z-test-hardening/root-regression-failure-preserved.log。
- 最终核心99项连续完整复跑3次均通过（99个唯一测试，不是297个不同测试），见该目录final-core-repeat-1/2/3.log；独立15项夹具v2再次全部通过。20个生产源码SHA仍与既存smoke相同，新增测试源码和日志哈希已绑定到 audits/cvrplib/reviewer/final_source_binding.json。12项generator测试通过。已有execution supervisor首次24/25，保留一项时序敏感失败；不改源码的单测、完整25/25以及固定底版25/25复查随后通过。它不是新CVRPLIB监督器，不能删掉初始失败或将所有尝试说成一次全绿。日志在 acceptance/20261014T084727Z/。
- 10次人为微型算例调用覆盖五臂×1/5秒，全部可行；7次公开smoke覆盖3例，不是正式统计比较。审查者仅对这7份既存结果重新后验评分，全部与原记录一致，没有重跑优化，见 audits/cvrplib/reviewer/public_smoke_score_recheck.json。
- 最终15项独立对抗复跑所审20个源码文件与smoke所记录SHA完全一致，见 audits/cvrplib/reviewer/final_source_binding.json。逐臂参数与算子顺序在 src/research/configs/cvrplib_algorithms.json，离线环境/实际命令见 src/research/docs/CVRPLIB_READINESS.md。
- PyVRP六个原archive成员及离线轮子已独立核对；VND十个交付成员匹配恢复清单，但原始ZIP未能独立取回，不能声称原archive逐成员验证完成。已定位原ZIP大小1,296,035字节、预期SHA256 4ac6eca8206577329f074d8aa57274202ce591681f9daeb939671ff8c302dbca；这些元数据不是字节复核替代物。
- 可以锁定这份“修复代码+准入证据”发布包；正式530次/臂设计、调度和新run_id须另行冻结，不因本轮修复自动启动。所有科学限制仍适用。

来源：https://galgos.inf.puc-rio.br/cvrplib/en/instances ；https://optimization-online.org/wp-content/uploads/2014/10/4597.pdf 。
