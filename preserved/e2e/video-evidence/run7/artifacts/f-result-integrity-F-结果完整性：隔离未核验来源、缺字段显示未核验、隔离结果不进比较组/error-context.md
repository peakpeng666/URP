# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: f-result-integrity.spec.ts >> F 结果完整性：隔离未核验来源、缺字段显示未核验、隔离结果不进比较组
- Location: tests/f-result-integrity.spec.ts:9:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: getByText(/显示 \d+ \/ 最近 \d+ 次/)
Expected: visible
Timeout: 30000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" getByText(/显示 \d+ \/ 最近 \d+ 次/) with timeout 30000ms
  - waiting for getByText(/显示 \d+ \/ 最近 \d+ 次/)

```

```yaml
- banner:
  - text: 农业机器人路径规划
  - textbox "任务描述":
    - /placeholder: 用一句话描述任务，例如：在 200×120 米的果园里，3 台机器人从西南角出发采样 40 个点，避开两个池塘
  - button "示例"
  - button "生成地图" [disabled]
  - button "导入"
  - group "工作区":
    - button "任务规划"
    - button "资产库"
    - button "算法实验"
    - button "仿真"
    - button "资料"
    - button "系统" [pressed]
  - button "恢复当前工作区的默认布局"
  - button "⌘K"
- region "服务":
  - tablist:
    - tab "服务" [selected]:
      - text: 服务
      - button "Close 服务"
    - tab "运行记录"
  - tabpanel "服务":
    - heading "服务与环境" [level=2]
    - paragraph: 实时
    - button "刷新全部状态": 刷新
    - button "全部日志"
    - text: 工作台网关 运行中 127.0.0.1:4100 PID 142313
    - paragraph: 127.0.0.1:4100，提供面板、/lab/api 与 /api 代理
    - term: Python
    - definition: 3.12.13
    - term: FastAPI
    - definition: 0.143.1
    - term: 运行目录
    - definition: ${USER_HOME}/urp-e2e/labdata/runtime
    - term: 前端构建
    - definition: 2026-10-22 22:45
    - term: 求解并发
    - definition: "6"
    - button "日志"
    - text: 档案后端 运行中 127.0.0.1:4180 PID 77281
    - paragraph: 外部进程（非本网关启动），网关不会停止它
    - term: 模式
    - definition: local_import_query_and_cvrp_jobs
    - term: 执行实验
    - definition: "True"
    - button "日志"
    - text: 求解环境 降级 检查项
    - paragraph: 部分算法或模块不可用，详见说明
    - term: Python
    - definition: 3.12.13
    - term: fastapi
    - definition: 0.143.1
    - term: uvicorn
    - definition: 0.54.0
    - term: pyvrp
    - definition: 0.14.0
    - term: ortools
    - definition: 9.15.6755
    - term: shapely
    - definition: 2.2.0
    - term: numpy
    - definition: 2.5.4
    - term: scipy
    - definition: 1.18.1
    - term: httpx
    - definition: 0.28.1
    - term: pillow
    - definition: 12.3.0
    - term: 研究模块
    - definition: 6/6 可导入
    - term: Node
    - definition: v24.14.0
    - term: 项目 JS 求解器
    - definition: src/frontend/core/routing/cvrp-solver.js
    - term: 可用算法
    - definition: 25/28
    - paragraph: f2c.full 不可用：可选 Fields2Cover 绑定未安装；可使用平行往复基线
    - paragraph: f2c.boustrophedon 不可用：可选 Fields2Cover 绑定未安装；可使用平行往复基线
    - paragraph: f2c.snake 不可用：可选 Fields2Cover 绑定未安装；可使用平行往复基线
    - text: Fields2Cover 不可用 检查项
    - paragraph: 不可用：可选 Fields2Cover 绑定未安装；可使用平行往复基线；覆盖任务仍可用面板基线 panel.boustrophedon
    - text: ROS 2 Humble 降级 检查项
    - paragraph: 仿真会话脚本 src/lab/ros/urp_sim_session.py 不存在
    - term: rclpy
    - definition: 可导入（humble，/usr/bin/python3）
    - term: RMW
    - definition: rmw_cyclonedds_cpp
    - term: Gazebo
    - definition: Fortress（ign gazebo 6.18.0）
    - term: ros_gz_bridge
    - definition: 0.244.26
    - term: 官方地图
    - definition: warehouse, depot, maze
    - term: 图形显示
    - definition: :0
    - term: 桥接关闭
    - definition: 已选择 parameter_bridge 源码关闭修复，启动时校验源码与依赖指纹；等待 ROS 信号线程结束后正常析构，不使用 _exit。
    - paragraph: 仿真会话脚本 src/lab/ros/urp_sim_session.py 不存在
    - text: 仿真会话 不可用 127.0.0.1:4191
    - paragraph: 仿真会话脚本 src/lab/ros/urp_sim_session.py 不存在
    - term: 桥接关闭
    - definition: 已选择 parameter_bridge 源码关闭修复，启动时校验源码与依赖指纹；等待 ROS 信号线程结束后正常析构，不使用 _exit。
    - text: RViz2 不可用
    - paragraph: 仿真会话未运行
    - text: Gazebo 界面 不可用
    - paragraph: 仿真会话未运行
    - heading "最近运行" [level=2]
    - paragraph: 最新 6 条求解记录
    - link "全部运行记录":
      - /url: "#/runs"
    - table:
      - rowgroup:
        - row "时间 场景 · 算法 状态 检查 目标值 操作":
          - columnheader "时间"
          - columnheader "场景 · 算法"
          - columnheader "状态"
          - columnheader "检查"
          - columnheader "目标值"
          - columnheader "操作"
      - rowgroup:
        - row "2026/10/22 22:34:30 agri-orchard-harvest-tran-5b1b69a6-8206-4f72-b6ae-89b5a0c6e4bd 先聚类后排程 面板基线 完成 · 可行 ✓ 通过 2,269.35s 规划 详情":
          - cell "2026/10/22 22:34:30"
          - cell "agri-orchard-harvest-tran-5b1b69a6-8206-4f72-b6ae-89b5a0c6e4bd 先聚类后排程 面板基线"
          - cell "完成 · 可行"
          - cell "✓ 通过"
          - cell "2,269.35s"
          - cell "规划 详情":
            - link "规划":
              - /url: "#/plan/agri-orchard-harvest-tran-5b1b69a6-8206-4f72-b6ae-89b5a0c6e4bd?run=run_20261022T133430_60ac15"
            - link "详情":
              - /url: "#/runs/run_20261022T133430_60ac15"
        - row "2026/10/22 22:34:30 agri-orchard-harvest-tran-5b1b69a6-8206-4f72-b6ae-89b5a0c6e4bd 先聚类后排程 面板基线 出错 – 未检查 — 规划 详情":
          - cell "2026/10/22 22:34:30"
          - cell "agri-orchard-harvest-tran-5b1b69a6-8206-4f72-b6ae-89b5a0c6e4bd 先聚类后排程 面板基线"
          - cell "出错"
          - cell "– 未检查"
          - cell "—"
          - cell "规划 详情":
            - link "规划":
              - /url: "#/plan/agri-orchard-harvest-tran-5b1b69a6-8206-4f72-b6ae-89b5a0c6e4bd?run=run_e2e_quarantined_unverified"
            - link "详情":
              - /url: "#/runs/run_e2e_quarantined_unverified"
        - row "2026/10/22 22:34:30 agri-orchard-harvest-tran-5b1b69a6-8206-4f72-b6ae-89b5a0c6e4bd 先聚类后排程 面板基线 完成 · 可行 ✓ 通过 2,269.35s 规划 详情":
          - cell "2026/10/22 22:34:30"
          - cell "agri-orchard-harvest-tran-5b1b69a6-8206-4f72-b6ae-89b5a0c6e4bd 先聚类后排程 面板基线"
          - cell "完成 · 可行"
          - cell "✓ 通过"
          - cell "2,269.35s"
          - cell "规划 详情":
            - link "规划":
              - /url: "#/plan/agri-orchard-harvest-tran-5b1b69a6-8206-4f72-b6ae-89b5a0c6e4bd?run=run_e2e_legacy_noidentity"
            - link "详情":
              - /url: "#/runs/run_e2e_legacy_noidentity"
        - row "2026/10/22 22:34:30 agri-orchard-harvest-tran-5b1b69a6-8206-4f72-b6ae-89b5a0c6e4bd 先聚类后排程 面板基线 完成 · 可行 ✓ 通过 2,269.35s 规划 详情":
          - cell "2026/10/22 22:34:30"
          - cell "agri-orchard-harvest-tran-5b1b69a6-8206-4f72-b6ae-89b5a0c6e4bd 先聚类后排程 面板基线"
          - cell "完成 · 可行"
          - cell "✓ 通过"
          - cell "2,269.35s"
          - cell "规划 详情":
            - link "规划":
              - /url: "#/plan/agri-orchard-harvest-tran-5b1b69a6-8206-4f72-b6ae-89b5a0c6e4bd?run=run_20261022T133430_8c8f89"
            - link "详情":
              - /url: "#/runs/run_20261022T133430_8c8f89"
    - heading "仿真会话" [level=2]
    - paragraph: 官方 TurtleBot4 · Gazebo Fortress · Nav2 · ROS 2 Humble
    - text: 未运行
    - term: 世界
    - definition: —
    - term: 出生点（map，m）
    - definition: —
    - term: 会话
    - definition: —
    - group "仿真世界":
      - button "warehouse" [pressed]
      - button "depot"
      - button "maze"
    - switch "Gazebo 窗口"
    - text: Gazebo 窗口
    - switch "RViz2" [checked]
    - text: RViz2
    - button "启动仿真"
    - heading "已知问题与说明" [level=2]
    - list:
      - listitem: 求解环境 f2c.full 不可用：可选 Fields2Cover 绑定未安装；可使用平行往复基线
      - listitem: 求解环境 f2c.boustrophedon 不可用：可选 Fields2Cover 绑定未安装；可使用平行往复基线
      - listitem: 求解环境 f2c.snake 不可用：可选 Fields2Cover 绑定未安装；可使用平行往复基线
      - listitem: ROS 2 Humble 仿真会话脚本 src/lab/ros/urp_sim_session.py 不存在
      - listitem: 历史数据 BPP 历史结果在「#/bpp」，原始实验数据放回 data/、experiments/ 后自动显示。
      - listitem: 仿真机器人 仿真使用官方 TurtleBot4，warehouse / depot / maze 世界里的通道对应作物行与地头。
      - listitem: 规划来源 「沿规划路径行驶」由 Nav2 控制器跟踪工作台算出的路径；「逐点导航」只用工作台给的任务顺序，每段路径由 Nav2 自己规划；从当前位置到路线起点的接驳段都由 Nav2 规划。
      - listitem: 坐标系 基准算例没有物理单位；实地坐标和仿真地图坐标都以米计，仿真地图上的方案可以直接送进仿真。
- region "日志":
  - tablist:
    - tab "日志" [selected]:
      - text: 日志
      - button "Close 日志"
  - tabpanel "日志":
    - combobox "日志":
      - option "gateway" [selected]
    - text: "2026-10-22 22:17:07,809 INFO uvicorn.error: Started server process [81515] 2026-10-22 22:17:07,809 INFO uvicorn.error: Waiting for application startup. 2026-10-22 22:17:07,867 INFO urp_lab.gateway: gateway ready on 127.0.0.1:4100 (runtime ${USER_HOME}/urp-e2e/labdata/runtime) 2026-10-22 22:17:07,868 INFO uvicorn.error: Application startup complete. 2026-10-22 22:17:07,869 INFO uvicorn.error: Uvicorn running on http://127.0.0.1:4100 (Press CTRL+C to quit) 2026-10-22 22:17:07,960 INFO urp_lab: 农业机器人路径规划工作台：http://127.0.0.1:4100/（监听 127.0.0.1，Ctrl+C 有序退出） 2026-10-22 22:26:52,212 INFO urp_lab: 收到 SIGTERM，正在有序关闭（仿真会话最长约 2.5 分钟）… 2026-10-22 22:26:52,303 INFO uvicorn.error: Shutting down 2026-10-22 22:26:52,404 INFO uvicorn.error: Waiting for application shutdown. 2026-10-22 22:26:52,406 INFO urp_lab.gateway: gateway stopped 2026-10-22 22:26:52,406 INFO uvicorn.error: Application shutdown complete. 2026-10-22 22:26:52,406 INFO uvicorn.error: Finished server process [81515] 2026-10-22 22:26:56,777 INFO uvicorn.error: Started server process [94161] 2026-10-22 22:26:56,777 INFO uvicorn.error: Waiting for application startup. 2026-10-22 22:26:56,788 INFO urp_lab.gateway: gateway ready on 127.0.0.1:4100 (runtime ${USER_HOME}/urp-e2e/labdata/runtime) 2026-10-22 22:26:56,788 INFO uvicorn.error: Application startup complete. 2026-10-22 22:26:56,788 INFO uvicorn.error: Uvicorn running on http://127.0.0.1:4100 (Press CTRL+C to quit) 2026-10-22 22:26:56,870 INFO urp_lab: 农业机器人路径规划工作台：http://127.0.0.1:4100/（监听 127.0.0.1，Ctrl+C 有序退出） 2026-10-22 22:34:05,235 INFO urp_lab: 收到 SIGTERM，正在有序关闭（仿真会话最长约 2.5 分钟）… 2026-10-22 22:34:05,274 INFO uvicorn.error: Shutting down 2026-10-22 22:34:05,374 INFO uvicorn.error: Waiting for application shutdown. 2026-10-22 22:34:05,376 INFO urp_lab.gateway: gateway stopped 2026-10-22 22:34:05,376 INFO uvicorn.error: Application shutdown complete. 2026-10-22 22:34:05,376 INFO uvicorn.error: Finished server process [94161] 2026-10-22 22:34:09,907 INFO uvicorn.error: Started server process [114122] 2026-10-22 22:34:09,907 INFO uvicorn.error: Waiting for application startup. 2026-10-22 22:34:09,918 INFO urp_lab.gateway: gateway ready on 127.0.0.1:4100 (runtime ${USER_HOME}/urp-e2e/labdata/runtime) 2026-10-22 22:34:09,918 INFO uvicorn.error: Application startup complete. 2026-10-22 22:34:09,919 INFO uvicorn.error: Uvicorn running on http://127.0.0.1:4100 (Press CTRL+C to quit) 2026-10-22 22:34:10,000 INFO urp_lab: 农业机器人路径规划工作台：http://127.0.0.1:4100/（监听 127.0.0.1，Ctrl+C 有序退出） 2026-10-22 22:34:30,143 INFO urp_lab.jobs: job job_20261022T133430_1d1ef4: panel.cluster_first 2026-10-22 22:34:30,190 INFO urp_lab.jobs: job job_20261022T133430_aa50e0: panel.cluster_first 2026-10-22 22:35:06,620 INFO urp_lab: 收到 SIGTERM，正在有序关闭（仿真会话最长约 2.5 分钟）… 2026-10-22 22:35:06,680 INFO uvicorn.error: Shutting down 2026-10-22 22:35:06,781 INFO uvicorn.error: Waiting for application shutdown. 2026-10-22 22:35:06,789 INFO urp_lab.gateway: gateway stopped 2026-10-22 22:35:06,790 INFO uvicorn.error: Application shutdown complete. 2026-10-22 22:35:06,790 INFO uvicorn.error: Finished server process [114122] 2026-10-22 22:35:12,288 INFO uvicorn.error: Started server process [116475] 2026-10-22 22:35:12,288 INFO uvicorn.error: Waiting for application startup. 2026-10-22 22:35:12,299 INFO urp_lab.gateway: gateway ready on 127.0.0.1:4100 (runtime ${USER_HOME}/urp-e2e/labdata/runtime) 2026-10-22 22:35:12,300 INFO uvicorn.error: Application startup complete. 2026-10-22 22:35:12,300 INFO uvicorn.error: Uvicorn running on http://127.0.0.1:4100 (Press CTRL+C to quit) 2026-10-22 22:35:12,380 INFO urp_lab: 农业机器人路径规划工作台：http://127.0.0.1:4100/（监听 127.0.0.1，Ctrl+C 有序退出） 2026-10-22 22:43:52,445 INFO urp_lab: 收到 SIGTERM，正在有序关闭（仿真会话最长约 2.5 分钟）… 2026-10-22 22:43:52,490 INFO uvicorn.error: Shutting down 2026-10-22 22:43:52,590 INFO uvicorn.error: Waiting for application shutdown. 2026-10-22 22:43:52,592 INFO urp_lab.gateway: gateway stopped 2026-10-22 22:43:52,592 INFO uvicorn.error: Application shutdown complete. 2026-10-22 22:43:52,592 INFO uvicorn.error: Finished server process [116475] 2026-10-22 22:43:55,268 INFO uvicorn.error: Started server process [136873] 2026-10-22 22:43:55,268 INFO uvicorn.error: Waiting for application startup. 2026-10-22 22:43:55,280 INFO urp_lab.gateway: gateway ready on 127.0.0.1:4100 (runtime ${USER_HOME}/urp-e2e/labdata/runtime) 2026-10-22 22:43:55,280 INFO uvicorn.error: Application startup complete. 2026-10-22 22:43:55,281 INFO uvicorn.error: Uvicorn running on http://127.0.0.1:4100 (Press CTRL+C to quit) 2026-10-22 22:43:55,359 INFO urp_lab: 农业机器人路径规划工作台：http://127.0.0.1:4100/（监听 127.0.0.1，Ctrl+C 有序退出） 2026-10-22 22:45:27,274 INFO urp_lab: 收到 SIGTERM，正在有序关闭（仿真会话最长约 2.5 分钟）… 2026-10-22 22:45:27,316 INFO uvicorn.error: Shutting down 2026-10-22 22:45:27,417 INFO uvicorn.error: Waiting for application shutdown. 2026-10-22 22:45:27,420 INFO urp_lab.gateway: gateway stopped 2026-10-22 22:45:27,420 INFO uvicorn.error: Application shutdown complete. 2026-10-22 22:45:27,420 INFO uvicorn.error: Finished server process [136873] 2026-10-22 22:45:30,269 INFO uvicorn.error: Started server process [142313] 2026-10-22 22:45:30,269 INFO uvicorn.error: Waiting for application startup. 2026-10-22 22:45:30,286 INFO urp_lab.gateway: gateway ready on 127.0.0.1:4100 (runtime ${USER_HOME}/urp-e2e/labdata/runtime) 2026-10-22 22:45:30,286 INFO uvicorn.error: Application startup complete. 2026-10-22 22:45:30,287 INFO uvicorn.error: Uvicorn running on http://127.0.0.1:4100 (Press CTRL+C to quit) 2026-10-22 22:45:30,357 INFO urp_lab: 农业机器人路径规划工作台：http://127.0.0.1:4100/（监听 127.0.0.1，Ctrl+C 有序退出）"
- status: 日志 opened
- alert
- contentinfo:
  - text: 已连接 求解空闲 田间：未运行 · TB4：未运行
  - link "CVRP 数值任务":
    - /url: "#/jobs"
  - link "BPP 历史":
    - /url: "#/bpp"
```

# Test source

```ts
  1  | import { test, expect, shot, API } from './helpers';
  2  | // Uses the real labdata test records (no stubs): run_e2e_quarantined_unverified (source_identity_verified=false)
  3  | // and run_e2e_legacy_noidentity (no identity fields), both in an OLDER job of their scenario.
  4  | // Studio's ComparePanel only shows the latest job (studio/store.ts:169-173 → "本批 1 次运行"); the only historical
  5  | // entry is #/runs (lab/views/Runs.tsx), whose "查看" link is #/plan/<sid>?run=<id>. Studio ignores ?run= (no
  6  | // params.get('run') in studio/), and Runs.tsx/Runs.logic.ts have no identity/quarantine handling.
  7  | // Expectations below are the spec; soft assertions so every gap is recorded.
  8  | const Q = 'run_e2e_quarantined_unverified', L = 'run_e2e_legacy_noidentity';
  9  | test('F 结果完整性：隔离未核验来源、缺字段显示未核验、隔离结果不进比较组', async ({ page }, info) => {
  10 |   const all = (await (await page.request.get(`${API}/runs?limit=200`)).json()).runs as any[];
  11 |   const q = all.find((r) => r.run_id === Q), l = all.find((r) => r.run_id === L);
  12 |   test.skip(!q || !l, 'test records missing from labdata');
  13 |   expect(q.process.source_identity_verified).toBe(false);
  14 |   await page.goto('/#/runs');
> 15 |   await expect(page.getByText(/显示 \d+ \/ 最近 \d+ 次/)).toBeVisible({ timeout: 30_000 });
     |                                                      ^ Error: expect(locator).toBeVisible() failed
  16 |   await test.step('历史入口：运行记录列出两条测试记录', async () => {
  17 |     await expect(page.getByText(Q, { exact: true })).toBeVisible();
  18 |     await expect(page.getByText(L, { exact: true })).toBeVisible();
  19 |     await shot(page, info, 'runs-history');
  20 |   });
  21 |   await test.step('运行记录中隔离/未核验标识', async () => {
  22 |     const qRow = page.locator('tr', { has: page.getByText(Q, { exact: true }) });
  23 |     const lRow = page.locator('tr', { has: page.getByText(L, { exact: true }) });
  24 |     await expect.soft(qRow.getByText(/隔离/), 'runs list marks quarantined run').toBeVisible({ timeout: 5_000 });
  25 |     await expect.soft(lRow.getByText(/未核验/), 'runs list marks legacy run 未核验').toBeVisible({ timeout: 5_000 });
  26 |   });
  27 |   await test.step('隔离结果不进入比较组', async () => {
  28 |     const ok = all.find((r) => r.scenario_id === q.scenario_id && r.job_id === q.job_id && r.run_id !== Q && r.run_id !== L);
  29 |     await page.getByLabel(`对比 ${Q}`).check();
  30 |     if (ok) await page.getByLabel(`对比 ${ok.run_id}`).check();
  31 |     await shot(page, info, 'compare-with-quarantined');
  32 |     await expect.soft(page.getByText(/隔离|源码身份不符/).first(), 'compare flags/excludes quarantined run').toBeVisible({ timeout: 5_000 });
  33 |   });
  34 |   await test.step('查看隔离运行：横幅与原因', async () => {
  35 |     await page.locator('tr', { has: page.getByText(Q, { exact: true }) }).getByRole('link', { name: '查看' }).click();
  36 |     await expect(page).toHaveURL(new RegExp(`run=${Q}`));
  37 |     await page.waitForTimeout(4_000);
  38 |     await shot(page, info, 'open-quarantined');
  39 |     await expect.soft(page.getByText(/已隔离/).first(), 'quarantine banner after 查看').toBeVisible({ timeout: 15_000 });
  40 |   });
  41 |   await test.step('查看缺字段运行：显示未核验', async () => {
  42 |     await page.goto(`/#/plan/${encodeURIComponent(l.scenario_id)}?run=${L}`);
  43 |     await page.waitForTimeout(4_000);
  44 |     await shot(page, info, 'open-legacy');
  45 |     await expect.soft(page.getByText(/身份未核验/).first(), '未核验 label after 查看').toBeVisible({ timeout: 15_000 });
  46 |   });
  47 |   // Mamba 0e8339fc history-runs entry (expected after gateway rebuild; fails on 3c0a94e5).
  48 |   await test.step('方案对比 → 历史运行（本场景）', async () => {
  49 |     const one = await page.request.get(`${API}/runs/${Q}`);
  50 |     const sid = one.ok() ? (await one.json()).scenario_id : null;
  51 |     if (!sid) {
  52 |       await page.goto('/#/runs');
  53 |       await expect(page.locator('tr', { has: page.getByText(Q, { exact: true }) }).getByText(/隔离/)).toBeVisible({ timeout: 15_000 });
  54 |       return;
  55 |     }
  56 |     await page.goto(`/#/plan/${encodeURIComponent(sid)}`);
  57 |     await page.getByText('方案对比', { exact: true }).first().click();
  58 |     const hist = page.getByRole('button', { name: '历史运行（本场景，含失败/已隔离/身份未核验）' });
  59 |     await expect.soft(hist, 'history-runs entry exists').toBeVisible({ timeout: 15_000 });
  60 |     if (!(await hist.isVisible())) { await shot(page, info, 'no-history-entry'); return; }
  61 |     await hist.click();
  62 |     for (const id of [Q, L]) {
  63 |       const row = page.locator('tr, li', { has: page.getByText(id) }).first();
  64 |       await row.getByRole('button', { name: '加入比较' }).click();
  65 |     }
  66 |     await shot(page, info, 'history-added');
  67 |     const excluded = page.getByLabel('未参与比较与排名');
  68 |     await expect.soft(excluded.getByText('已隔离 · 不适用')).toBeVisible();
  69 |     await expect.soft(excluded.getByText(/\d+\.\d|km|\bm\b/), 'no values for quarantined').toHaveCount(0);
  70 |     await expect.soft(page.getByText('身份未核验').first()).toBeVisible();
  71 |     await page.getByText('结果', { exact: true }).first().click();
  72 |     await shot(page, info, 'result-tab');
  73 |     await expect.soft(page.getByText(/已隔离：.+/).first(), 'quarantine banner + reason').toBeVisible({ timeout: 10_000 });
  74 |   });
  75 | });
  76 | 
```