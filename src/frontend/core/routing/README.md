# 路线组件

从已有规划界面归并的六个独立模块，供当前前端的路线视图复用。

| 文件 | 作用 |
|---|---|
| `cvrp-problem.js` | 输入与任务范围检查 |
| `cvrp-input.js` | 明确字段的文本与CSV解析 |
| `cvrp-solver.js` | 最近邻与Savings构造基线 |
| `cvrp-checker.js` | 独立检查任务访问、回仓、容量和距离 |
| `cvrp-result.js` | 求解器结果文件适配 |
| `cvrp-model-result.js` | 模型结果检查与有效参考解回退 |

任务范围为无限同型车队、正整数需求、欧氏距离CVRP。模块提供CommonJS与浏览器全局接口，尚未接入React页面。

```sh
node --test tests/*.test.js
```
