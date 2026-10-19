# CVRPLIB当前入口

更新：2026年10月14日。状态：运行前验收通过，VND来源已闭环；正式实验计划尚未冻结，正式53例多种子比较尚未启动。

2026-10-19 补充：上面两句仍是 2026-10-14 运行前验收入口，不改写成 G5 已签收。后来的冻结计划与 17 配置结果在 [protocol/formal_plan.json](../protocol/formal_plan.json) 和 [baselines/cvrp](baselines/cvrp/README.md)。李月莹 2026-10-16 的 5 算法补做是验收口径，核验见 [handoff/20261016-liyueying](baselines/cvrp/handoff/20261016-liyueying/核验与接手.md)。5 秒端到端和 1 秒搜索循环分开存放。

## 当前结果

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

## 当前版本与边界

当前取用以本页为准；过期说明和重复交付包装不再列作现用材料。需要追溯时，查看[整理前的固定Git版本](https://github.com/peakpeng666/URP/tree/ab3a6f4caee7fd961437000fb73c41286f394fd2)。原始成功、失败日志及来源证据继续保留在 acceptance/、audits/cvrplib/ 和数据目录；两份独有合同审计材料已归入 [独立审查说明](../audits/cvrplib/reviewer/README.md)。历史253 PASS和旧研究结论不改写为本轮结果。

本轮整理不新跑优化实验，不调用生成模型，不修改冻结算法。用户Ubuntu主机尚未实装，全库/前后端并未重新验收。下一步须另行冻结正式计划、算法/数据/环境哈希、种子预算、运行ID及登记表，保留未启动与失败分母。

本文件是准入状态的统一入口；实际远端提交、云盘核对及清理结果另记在项目交接索引和完成回执，不由本文件预先证明。
