# 农业目录兼容修复验收

基线：`85b085fcdd9429deeb8c11708af1851384842893`。修复复用现有 Studio、`POST /lab/api/scenarios`、推荐、求解和独立验算接口，4100 网关及部署配置保持不变。

## 使用

打开现有工作台的场景库，切换“农业目录”。按环境、作业或模式状态筛选，展开模板并调整参数、随机种子。保存后进入现有任务规划页，推荐和调用求解器。提案保留接口说明；近似模式显示实际代理模型。目录支持完整矩阵 JSON/CSV 和原始场景 JSON 下载。

## 修复

- 复用现有 FleetInstance；地块/障碍对象和整数任务 ID、xy 坐标与后端一致。
- 行向角进入真实模型；容量不足、车辆数量和几何参数错误直接返回明确错误，不静默修改实验配置。
- 导入保留生成参数、种子和原生成器，二次导入仍可追溯；执行权限继续由后端判定。
- 核对文献题录和源码引用，区分目标模型与实际近似，修正槽位、面积和费用单位。
- 原 EXP 描述已改为待按固定实例验证，运行证据另行归档。

## 实测

- 前端：TypeScript、生产构建通过；421 项测试全部通过，无跳过。
- 22 个构建器 × 3 种子：66 个真实后端输入校验通过。
- 22 个默认实例实际调用求解器：21 个可行且独立验算通过；含障碍覆盖基线返回 no_solution，保留穿障失败。
- HTTP：田间采样、果园采收运输、耕整地覆盖完成导入、恢复、推荐、求解、独立验算、运行列表与记录导出；生成参数和种子保持一致。
- 后端整套：392 通过、4 跳过；随后增加二次导入回归，导入专项 7 项通过。
- Chromium 在云端启动受到沙箱限制，浏览器交互脚本已保留；本次页面验证为 SSR/生产构建与真实 HTTP 链路。Gazebo 和 Fields2Cover 原生求解不在本次测试范围。

首次后端全测因缺官方地图失败。补充官方 TurtleBot4 humble 地图后重跑通过；maze PGM SHA256 为 `02f070e256b7f1f3842b99340a6c5a49866d1289ac4a78ca08da5f47745830cf`，与原项目记录一致。

## 重跑

```sh
(cd src/lab && uv sync --locked --inexact)
npm ci --prefix src/frontend --engine-strict --no-audit --no-fund
npm run typecheck --prefix src/frontend
npm run test:ui --prefix src/frontend
npm run build --prefix src/frontend
node src/frontend/tools/check-agri-contract.mjs /tmp/agri-contract.json
(cd src/lab && .venv/bin/python -m pytest -q tests/test_agri_import_provenance.py)
```

实际 HTTP 与浏览器验收命令见 `src/frontend/tools/check-agri-http.mjs`、`src/frontend/tools/browser/agriculture-acceptance.mjs`。仅对独立测试 runtime 运行，避免写入现有实验库。

原始响应保留在单独交付的验收记录中。求解器耗时受主机条件影响，比较实验应使用一致环境和时间预算。
