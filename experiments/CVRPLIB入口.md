# CVRPLIB当前入口

更新：2026年10月19日。先看[现用17配置基线](baselines/cvrp/README.md)、[冻结计划](../protocol/formal_plan.json)、[基线报告](baselines/cvrp/results/基线实验报告.md)和[归档独立重审](../protocol/audits/20261017/README.md)。导师要求的不同规模、分布基础算法对照已有冻结的描述性结果；新的研究命题和验收不能仅靠修改文档宣称完成。

## 现用结论与分母

| 批次 | 已归档状态 | 不可混用的原因 |
|---|---|---|
| [主17配置](baselines/cvrp/README.md) | 17配置 × 53问题 × 5种子 × 每项5秒 = 4505个唯一计划项；4316有效解、189无有效解、未启动0；4509次尝试含4次中断后的原项重试 | 主分母；53问题对应51个底本，不删去容量/车数不同的两对问题 |
| [vendor补充](baselines/cvrp/evidence/vendor_all120_audit.json) | AILS-II/SISR，X集合12例 × 5种子 = 120项，120项独立验算有效 | 补充对照，不扩成主计划19配置，也不把共享墙钟下的资源效率直接比较 |
| [李月莹验收](baselines/cvrp/handoff/20261016-liyueying/核验与接手.md) | 更早提交 `50b3b2c` 的5算法、53例、5秒端到端；742/742复算有效，均为 `acceptance_only` | 算法和种子合同不同，不补主表，也不据此签收G5 |
| [16例旧/新两批](baselines/cvrp/handoff/20261016-liyueying/independent_verification.json) | 1秒搜索循环，旧r1批48项逐字节沿用既有记录，新批48项；41/48成本相同 | 不是96项新增复现，更不等于5秒端到端记录 |

主批次按客户数的小/中/大规模为41/6/6例，中大型均来自X集合；大小与来源不能完全解耦。[算例清单](../src/research/configs/cvrplib_cases.json)和[报告](baselines/cvrp/results/基线实验报告.md)提供分层口径。PyVRP为265/265有效、算例等权参考gap约0.341%，质量均值只能与可行覆盖率一起看，不能用条件均值掩盖失败。17配置包含相近变体，并非17个独立算法家族。CVRPLIB的成本与容量合同不包含农田障碍、地头、覆盖、车辆动力学或实际执行轨迹。

归档重审将主机/环境证据分为cloud seed0的901项已验证包装、cloud seed2的901项有未VERIFIED且未链接环境哈希的host manifest、ubuntu-local seed1/3/4的2703项有结果SHA绑定的FROZEN resource manifest而缺原host/environment核验包装。它们均有路线质量记录；仅901项支持现有归档意义的“已验证同条件”统计。不能跨硬件排速度，也不能将种子/主机混杂当成独立算法波动。[审计JSON](../protocol/audits/20261017/archive_review.json)与[重审说明](../protocol/audits/20261017/README.md)是该分级依据。

## 2026-10-14运行前验收（历史时点，不是当前批次结论）

当时运行前验收通过、VND来源闭环，但正式实验计划尚未冻结、正式53例多种子比较尚未启动。此句只记录当时时点；后续主4505项、补充批次及重审以上述现用材料为准，不反向改写运行前验收为G5已签收。

## 当时的运行前结果

- 99项核心回归在最终测试夹具上连续三轮通过，另有主任务第四轮复核；15项独立故障检查通过。
- 53项参考解与车队合同验算通过，100项历史原文件哈希一致，6份补充参考解来源与验算齐全；53个问题对应51个坐标需求底本。
- 10次构造小例与7次公共算例smoke均保存原输出和独立评分，只证明运行前能力，不证明算法优越性。
- PyVRP原归档/依赖与VND原ZIP及10个成员均完成独立核验。PyVRP固定0.14.0，使用ILS。
- 保留98/99首次失败、夹具前置条件修正记录，以及旧监督器24/25首次失败和无源码修改后的复跑；不删除失败，不宣称消除了偶发时序风险。

## 取用

- [安装与运行](../src/research/docs/CVRPLIB_READINESS.md)：完整research基线与新CVRPLIB入口在 src/research/，生产源码保持本轮最终验收字节。
- [当前协议](protocols/CVRPLIB_READINESS_PROTOCOL_20261014.md)：输入合同、预算、失败分母与正式冻结边界。
- [独立数据审计](../audits/cvrplib/README.md)：53例参考解、底本、距离与来源证据。
- [VND来源核验](../audits/cvrplib/vnd_original/当前核验.md)：原ZIP、10个成员、脚本和复核日志。
- [原始验收记录](../acceptance/)：20261014T084727Z 与 20261014T085915Z-test-hardening，包括全部失败记录。
- [输入与参考解](../data/benchmarks/CVRPLIB/)：53份VRP、53份SOL及独立的6份补充来源说明。
- [离线依赖](../runtime/cvrplib/)：Linux x86_64、Python 3.12；其他平台不直接适用。恢复方式见该目录的复现说明。
- [覆盖清单](../evidence/cvrplib_release/COVERAGE_MANIFEST.json)：本轮文件映射、SHA256、历史保留与依赖恢复映射；它不是全仓库重新验收声明。

## 运行前版本与边界

2026-10-14 的运行前材料以本节列出的入口追溯；过期说明和重复交付包装不再列作现用材料。需要追溯时，查看[整理前的固定Git版本](https://github.com/peakpeng666/URP/tree/ab3a6f4caee7fd961437000fb73c41286f394fd2)。原始成功、失败日志及来源证据继续保留在 acceptance/、audits/cvrplib/ 和数据目录；两份独有合同审计材料已归入 [独立审查说明](../audits/cvrplib/reviewer/README.md)。历史253 PASS和旧研究结论不改写为本轮结果。

2026-10-14 整理没有新跑优化实验、调用生成模型或修改冻结算法；当时用户Ubuntu主机尚未实装，全库/前后端不在该次验收范围。后续正式计划与归档已形成，但不能以本页文字代替新的代码或现场验收。

本文件只统一科研批次和历史准入入口；实际远端提交、云盘核对及清理结果另记在项目交接索引和完成回执，不由本文件预先证明。
