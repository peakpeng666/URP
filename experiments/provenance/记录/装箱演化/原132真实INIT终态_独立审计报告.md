# 原132：真实 INIT-only 恢复终态独立接受

2026-10-06。**本次真实 INIT 终态接受；不包含 GEN 激活。** 独审没有重跑恢复、原 helper、assembler 或任何科学/模型阶段。

## 核验结果

- 实际生产证据包：1,146,103 B，SHA256 `2b42199050df462751e25caa8e956f8782d46172847b2dfa713948b729f56342`。310 ZIP 成员，其中309项 manifest全部通过，无额外/重复/不安全路径。
- 实际 activation 为37,461 B，SHA `59d96a0a5deb67de3272d9991bfd4a83fb1c56844901bb512b5d73d7d917eb6b`，与父核验的离线proposal逐字节相同。相比禁用候选仅两个顶层布尔改变，原字段、旧grant全文、源pin与未知范围保留。
- 核验31个去重后的原/新源文件pin，五对原helper00–04 intent/receipt字节不变。后缀没有重跑00–04，没有新建/替换index。
- 44条实际工具返回与总transcript逐条一致：41次本地exec、2次精确index读取、1次archive create。固定14阶段都有对应before/真实动作/after，全部成功且无session遗留；只记录一次enter、一次finish、一次archive create，没有重试或额外工具路由。
- 原helper05–12和assembler形成真实base14 measurements /16 receipt引用。32条新增恢复计量与base按原样组成46条，55个handoff引用逐文件hash全部通过，finish seal与真实返回及磁盘v2一致。
- 46个稳定process身份唯一，全部SELF和本地区间实测、有限、非负，局部窗口互不重叠；各段与同池账本一致。终态副本和producer复核未见pending/HALT或GEN/bridge journal。

## 实际远端字节另证

独审随后通过只读Library head查询及受支持的精确materialization重新取得完整字节：

| 项目 | 当前真实身份/版本 | 字节与SHA |
|---|---|---|
| index | `libfile_d711508ec1888191ba87324ac424a529` / `file_00000000d48881f58e04687a2b2eb6b4`，v0 | 859 B / `83007fa4f9c1cfa8691bf23aa5f07d4a96881d356ee437197b2695774ad313c6` |
| archive | `libfile_0186168496ec8191a13d91cbc158d000` / `file_0000000092f8820cb55d553bffd3b828`，v0 | 478 B / `bb644cab41cf25559f1bdc7fe3212ccbf0d61362a16dd0f717e2c1ff3795f43f` |

index仍为 `rows=[]、archives={}`；archive CRC、成员hash与空slots检查通过。执行时两次index read的 `version_id=null` 仍如实保留，不能将它冒充为当时read提供的版本；本次新的materialization独立确认v0。

原两份commit receipt的 `remote_bytes_verified=false` 未改。新的完整远端字节证明是独立补充证据，位于 `library_readback/independent_byte_verification.json`，不是回写原receipt。导出审计包不含临时认证下载地址；相关工具响应的去除临时地址版明确标注，下载后的真实字节与原始响应hash均保留。

## 资源结论

- 真实46条观测SELF合计：2.2689399999999997 s。
- 非重叠局部inclusive wall合计：1.1660925439937273 s。
- 同一60 SELF /240 local-wall池的观测余额：57.73106 s /238.83390745600627 s，未新发预算。
- 原历史与新checkpoint后的尾部、JS/plugin/Library/provider成本仍unknown；本次证据整理、复核、Drive等开销也没有完整上界。`CPU_cap_certification=NOT_ESTABLISHED`，完整CPU上界声明false。上述余额不是完整未来可用预算保证。
- GEN、numeric标记仍false，model/candidate均0。实际GEN初始化尚未发生，不能把本次INIT终审当成GEN费用已经导入。

## 后续GEN只能绑定这些真实结果

v2 handoff：
`/workspace/original132-phase2-producer-20261006.namespace-recovery/RECONCILED_HANDOFF.v2.json`

35,587 B，SHA `2645a52293ad256e90d50729bac7fb015209d950e516035f82ebeb86253a1f66`。

base handoff：
`/workspace/original132-phase2-producer-20261006.namespace-init/INIT_RESOURCE_HANDOFF.json`

15,253 B，SHA `435415d586ec43c26814f1190a9b379e09ee0adc7a526e1d6f6bac1db7df80cb`。

reconciliation activation：
`/workspace/original132-init-only-precheck-20261006-g2uks153/INIT_ONLY_ACTIVATION.APPROVED.json`

SHA `59d96a0a5deb67de3272d9991bfd4a83fb1c56844901bb512b5d73d7d917eb6b`。

后续GEN需另审禁用候选及完整科学/资源/路径契约，再取得独立执行决定；必须将上述v2全部46条恰好一次送入 `init_final`，不可选择base v1漏掉32条恢复成本。原六个 `LOCAL_FUNCTIONS` 的路径/hash门必须保持。精确输入片段及六源/九个运行时原依赖pin见 `GEN_BINDING_INPUTS.NOT_ACTIVATION.json`，该文件明确不是激活grant。

## 边界与保留记录

独审只解析交付的实际工具返回、原始journal、源文件和终态快照，并另做真实Library只读字节核验；没有登录或修改原producer环境，不声称全OS/外部第三方排他性。断线后的只读状态检查没有触发重入。生产后首次打包因null字段处理失败的记录也保留，它没有修改已审源码或重新执行恢复，其额外成本仍unknown。

核心机器证据：`ACTUAL_TERMINAL_INDEPENDENT_VERIFICATION.json`、`verify_actual_terminal.py`、`library_readback/independent_byte_verification.json`。R1拒绝、R2离线接受、禁用候选和离线proposal均保持原样。
