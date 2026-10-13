# 下一步 INIT-only：最小精确绑定与只读预检

本文件是执行准备清单，**不是启用 grant，也不授权调用恢复入口**。独审没有创建 enabled grant，没有触碰原 producer namespace，没有执行真实恢复。R2 源码已经定稿；空 fixtures 目录问题仅作为文档勘误，不要求改源码。

## 精确接受的源码

- R2 ZIP：`0b8eac652f1d14290ccabf832ea3889141199cd0f64924c56bb7df9c82ba36d1`。
- R2 `FILE_MANIFEST.json` exact-file SHA：`7740fa3e61f845a4a392c5556a804c2bd8842fade2f2f8e0134b8542cc236d44`；425 成员已核验。
- 生产入口：`recoverSuffix`，来源 `src/suffix_bridge.js`，SHA `d31cd3e8de99cdc73fb715ec3d6dcfbf846684bf270d1853ec16b97ba4407209`。不使用 `recoverSuffixOfflineFixture` 或 CLI `--offline-fixture`。
- 真实本地控制 CLI：`src/recovery_cli.py`，SHA `59695355a32f72bd77532c07d19e895b921a27e6e1a771bbf6aff7924e0a2c54`。
- `src/recovery_core.py`：`101ba2facae086210c02f44882e3bc062376567a033039508a0e102dd8970fa1`。
- `src/reconciled_handoff.py`：`af79d1a8dea7b01d64bc193bce0acde04bd4e43698216b5bf8939b328b097e28`。
- `src/gen_importer_v2.py`：`024b106fcebc907b9dc449a230621f18542aa2190f71bb36418664d938a7776d`，仅作为被 pin 的依赖；本次不运行 GEN。
- `src/production_generation_entry_v2.py`：`69a6a2e06562a52c71a9c8bea5c5a4fe6f837725b36b167db570c43656f8c9a1`，同样不运行 GEN。

六个源文件在原 producer 的预期根目录为 `/workspace/original132-phase2-recovery-dev-20261006-8sdu8cov/revision2/src/`。必须由原 producer 在此真实路径再次核验。审计机器中的解压路径不可作为原 producer 的存在证明。

## 哪个 grant、哪些字段、何时重新生成

被审的禁用输入为 R2 `RECOVERY_GRANT.DEVELOPMENT.json`，exact-file SHA `c24e15941c1a9caa4c6583e3ba14e5bd9b981c9b187349b5531a24f60c7ccff8`。

当前可以安排原 producer 只读核验并形成一份单独的 INIT-only 候选绑定和预检报告。此时 `execution_granted` 保持 false，不调用 `recoverSuffix` 或 recovery CLI。

父明确接受预检并决定唯一恢复执行后，另建独立 activation 文件。代码实际要求的两项启用字段是：

- `execution_granted: true`
- `independent_review_accepted: true`

必须保持：`generation_execution_granted: false`、`numeric_execution_granted: false`、`model_requests: 0`、`candidate_executions: 0`、`new_index_create_count: 0`、`index_replace_count: 0`、`archive_create_max: 1`、`historical_index_create_count: 1`。

不要原地编辑开发 grant，不要编辑旧 INIT grant。应保全开发输入及独审证据，新的 activation 文件绑定本次已接受的 R2、通过的真实预检和精确动作范围，并由父独立核验其字节。激活文件的**路径、全文和 exact-file SHA 必须重新确定**，桥接调用必须使用这份新的路径/全文/SHA；未来 v2 的 `reconciliation_grant_ref` 自然引用该新文件，不能继续引用开发 grant hash。

若所有原路径和源字节仍与开发 grant 相同，六个 source hash 及所有原证据 pin 不应改变。不要为换一个 grant 文件重算或改写旧 receipt。若源码搬家，绝对路径绑定必须重新生成并审阅；若代码字节改变，超出本次接受范围，必须重审，不能沿用本结论。

新 activation 文件仍须保留原 `old_grant_file_text` 的确切旧字节、全部原 source/implementation/generation pin map、五对 old_five refs、原 stop/error/create/pending refs、两 blob 字节/hash、两个 run ID、四个禁止旧 Library ID、固定 suffix_actions、unknown 和原 pool。新增明确的审计/预检引用可作为外部工程绑定证据；不能用它们替换代码读取的原精确字段。

## 不新建或切换 producer namespace

继续使用唯一原 producer `/workspace/original132-phase2-producer-20261006` 与原 journal `/workspace/original132-phase2-producer-20261006.namespace-init`。

恢复实现仅允许自己的固定 journal `/workspace/original132-phase2-producer-20261006.namespace-recovery`。它在首次授权入口前必须不存在；这不是重开一套 producer/科研 namespace。任何已存在 recovery journal，即使看似空或由不同 grant 产生，也必须停止再审，不删除后重试，不换名字绕过。

## 实际生产前只读检查清单

1. 原 producer 仍是唯一操作者，无并行 INIT/恢复/GEN/Library 写入。
2. 当前五对 helper00–04 intent/receipt 与 grant pins 完全一致且 confirmed；没有05–12、额外/orphan helper、assembly、额外 payload/commit、archive retention 或其他未知活动。
3. 原 pending 的 exact SHA 仍为 `28d28fe5af6521d9e855487bdd50438fb90bcfccc0ecf871ad5099159fdd1092`，kind=index、prior=-1、新建身份 null，并绑定同一 index blob。原 commit/readback 不存在；不得手动删 pending。
4. 原 INIT grant SHA 仍为 `fd7e0df05db28dc38b14a3231662c8f775db8472d46625f3c3a02a3c6e26166e`。保全 stop ZIP `ca21bf7717fefb52d27437cd2373ac6021ea6260182a29a1d9a1a15ca287c04e`、bridge error、真实历史 create response 及其身份。
5. index 仍为859 B、SHA `83007fa4f9c1cfa8691bf23aa5f07d4a96881d356ee437197b2695774ad313c6`；Library ID `libfile_d711508ec1888191ba87324ac424a529`、backing ID `file_00000000d48881f58e04687a2b2eb6b4`、历史 create v0。archive 仍为478 B、SHA `bb644cab41cf25559f1bdc7fe3212ccbf0d61362a16dd0f717e2c1ff3795f43f`。
6. 原七个 INIT 实现、原 exporter/retention/xattrs、原 GEN dependency 和本次六个 R2 新源码均在实际绑定路径且 exact pin 一致；没有源码目录额外可执行文件。
7. recovery journal、GEN accounting、phase2 bridge journal 无已存在或未知活动；若出现任何不符，应输出只读冲突报告而非修复现场。
8. pool 仍为同一60 SELF/240 local-wall，`new_budget=false`。原五条观测 checkpoint 保留，不能重测替代。只读预检/审阅开销不能报0或伪作原 helper 测量；它并不建立完整 CPU 上界。

预检不代替恢复入口自己的新测量验证。实际执行的两次 fresh authenticated read 必须在已审计的入口/控制 journal 中发生；单独预检读或此次历史诊断读不能补成成功 stage receipt。

## 唯一执行的预算与异常停点

- 每一步仍按旧已确认 +新增 recovery +当前 guard checkpoint 入同池检查；任何未知、缺receipt、源/路径/身份/hash冲突、当前池到达阈值均停止后续动作。
- index create/replace 不可达；只首次原05/06。只有原 confirm 可写 commit 并清对应 pending。
- archive最多一次 create。普通 throw 的窄失败留存路径可以写错误证据和计量，但原helper09为unknown、HALT/pending保持，不运行helper10、assembler或v2，不重试外部写。
- helper/exec、工具返回、measurement、retention 或checkpoint状态不明时保持 durable intent，禁止启动另一个 grant 重放。已写commit但未清pending也不能手动清理。
- 完成原13 helper之后由原 assembler首次形成14/16 base，再形成实际14+k v2。独立终审之前不把INIT看作自动可激活GEN。
- 不运行 GEN 入口/模型/candidate/numeric。历史及新checkpoint尾部继续unknown，cap始终`NOT_ESTABLISHED`。

## 复现文档勘误

离线测试命令前先执行 `mkdir -p fixtures`。除此以外，本次复审未修改任何源码、测试、reference或开发 grant。
