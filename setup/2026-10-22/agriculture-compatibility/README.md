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

- 前端：TypeScript、生产构建通过；512 项测试全部通过，无跳过。
- 22 个构建器 × 3 种子：66 个默认真实后端输入校验通过；另356个边界通过，46个固定负例按预期原因拒绝。
- 22 个默认实例实际调用求解器：21 个可行且独立验算通过；含障碍覆盖基线返回 no_solution，保留穿障失败。
- HTTP：田间采样、果园采收运输、耕整地覆盖完成导入、恢复、推荐、求解、独立验算、运行列表与记录导出；生成参数和种子保持一致。
- 后端整套：410 通过、4 跳过；导入专项12项通过。
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


## 第二轮边界与恢复检查

- 同 ID 导入返回 409，保留原场景；新建与编辑复用同一写入锁，场景从 revision 1 起步。规划页编辑继续使用原版本检查接口。
- 目录筛选保留参数草稿；进行中相同请求去重，旧请求不会在离开再返回后抢导航；冲突后保留参数，主动重试创建新 ID。
- 场景 ID 使用 `getRandomValues`，兼容局域网 HTTP，不要求改变部署协议；见 [MDN API说明](https://developer.mozilla.org/en-US/docs/Web/API/Crypto/getRandomValues)。
- 生成器版本升为 `urp.agri.builder/3`。种子边界、障碍互斥、混编车体半径与温室大半径补给点均有反例回归；覆盖率与曲率模型说明按真实计算口径修正。
- 跨语言回归：默认66/66，边界356/356；另46个固定负例按预期原因拒绝。该轮后端全套396通过、4跳过。
- 三个代表场景再次完成真实 HTTP 链；逐例重复导入409，原场景保持不变，参数、版本和种子可恢复。

## 无 ROS 工作台部署

- 地图场景按已安装资源注册。没有 ROS 地图时，数值工作台及自建农业任务正常使用；已安装但损坏的地图仍报错。
- 缺失地图的内置场景 ID 仍保留，避免用户导入占用后与恢复地图发生冲突。
- 空地图目录下完成场景列表、3个农业 HTTP 场景及部署覆盖任务的导入、重复导入409、求解、独立验算和记录恢复。
- Docker 构建检查新增 `python3 deploy/check-agriculture.py --base-url http://127.0.0.1:4100`，检验真实业务流程而非只测健康页。
- 地图专项12项、导入专项12项通过；整套后端410项通过、4项跳过。部署离线测试48项通过、1项依赖条件跳过。
- HTTP 检查脚本只输出最小验收摘要，完整 API 响应仅用于内存断言。
