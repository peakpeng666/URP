# 当前问题

| 项目 | 已知问题 | 结果入口 |
|---|---|---|
| CodeGen排序 | 10个候选中7个未通过受限语法准入；3个准入候选在额外异常合同上有失败 | [评测](results/组件/isolated_evaluator/prospective_prompt_v4_compat/evaluation_outputs/evaluated_v4_compat_20261004_01/report.json) |
| 装箱新数据确认 | IID有缺失结果，完整EOH—IID对照均值为空；与公开EoH的20流比较完整 | [确认报告](reports/装箱演化/装箱演化与新数据验证.md) |
| 生成策略 | 公开设计集改善尚未转化为稳定的新分布收益 | [当前进度](状态.md) |
| 软件 | 前端通用API接入、同源连接、Ubuntu外壳与浏览器验收待完成 | [接口](../src/backend/api.md) |

各实验的失败记录和资源数据见对应结果包；已撤回结论见[科研勘误](research_corrections.md)。
