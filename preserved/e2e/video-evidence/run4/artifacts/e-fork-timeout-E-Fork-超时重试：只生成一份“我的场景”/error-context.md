# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: e-fork-timeout.spec.ts >> E Fork 超时重试：只生成一份“我的场景”
- Location: tests/e-fork-timeout.spec.ts:4:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('svg[aria-label="任务地图编辑器"]')
Expected: visible
Timeout: 30000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" locator('svg[aria-label="任务地图编辑器"]') with timeout 30000ms
  - waiting for locator('svg[aria-label="任务地图编辑器"]')

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
    - button "任务规划" [pressed]
    - button "资产库"
    - button "算法实验"
    - button "仿真"
    - button "资料"
    - button "系统"
  - button "恢复当前工作区的默认布局"
  - button "⌘K"
- region "场景库":
  - tablist:
    - tab "场景库" [selected]:
      - text: 场景库
      - button "Close 场景库"
  - tabpanel "场景库":
    - button "打开农业任务目录"
    - textbox "搜索场景"
    - text: 导入 GeoJSON / 场景 JSON 我的任务地图 · 6
    - list:
      - listitem:
        - button "果园采收集运 多车任务 · 实地坐标 · 米 · 36 个任务"
      - listitem:
        - button "果园采收集运 多车任务 · 实地坐标 · 米 · 36 个任务"
      - listitem:
        - button "果园采收集运 多车任务 · 实地坐标 · 米 · 36 个任务"
      - listitem:
        - button "果园采收集运 多车任务 · 实地坐标 · 米 · 36 个任务"
      - listitem:
        - button "果园采收集运 多车任务 · 实地坐标 · 米 · 36 个任务"
      - listitem:
        - button "果园采收集运 多车任务 · 实地坐标 · 米 · 36 个任务"
    - text: 仿真地图 · 8
    - list:
      - listitem:
        - button "官方迷宫 · 双点巡检闭环 转弯约束路网 · 仿真地图 · maze · 2 个任务"
      - listitem:
        - button "仓储货架通道 · 作物行代理 转弯约束路网 · 仿真地图 · warehouse · 5 个任务"
      - listitem:
        - button "车间空地 · 欧氏 CVRP 车辆路径 CVRP · 仿真地图 · depot · 10 个任务"
      - listitem:
        - button "车间空地 · 内缩作业区覆盖 覆盖作业 · 仿真地图 · depot"
      - listitem:
        - button "仓库 · 跨通道到达 点到点规划 · 仿真地图 · warehouse"
      - listitem:
        - button "仓库 · 农机转弯半径 点到点规划 · 仿真地图 · warehouse"
      - listitem:
        - button "迷宫 · 对角穿越 点到点规划 · 仿真地图 · maze"
      - listitem:
        - button "车间 · 可倒车泊位 点到点规划 · 仿真地图 · depot"
    - text: 基准算例 · 26
    - list:
      - listitem:
        - button "转弯路网 g3x3_s8000_uturn 转弯约束路网 · 基准算例 · 5 个任务"
      - listitem:
        - button "转弯路网 g3x3_s8001_left_cost 转弯约束路网 · 基准算例 · 5 个任务"
      - listitem:
        - button "转弯路网 g3x3_s8002_left_ban 转弯约束路网 · 基准算例 · 5 个任务"
      - listitem:
        - button "转弯路网 g3x3_s8003_uturn 转弯约束路网 · 基准算例 · 5 个任务"
      - listitem:
        - button "转弯路网 g3x3_s8004_left_cost 转弯约束路网 · 基准算例 · 5 个任务"
      - listitem:
        - button "转弯路网 g3x3_s8005_left_ban 转弯约束路网 · 基准算例 · 5 个任务"
      - listitem:
        - button "转弯路网 g3x3_s10000_uturn 转弯约束路网 · 基准算例 · 5 个任务"
      - listitem:
        - button "转弯路网 g3x3_s10000_left_cost 转弯约束路网 · 基准算例 · 5 个任务"
      - listitem:
        - button "转弯路网 g3x3_s10000_left_ban 转弯约束路网 · 基准算例 · 5 个任务"
      - listitem:
        - button "转弯路网 g3x4_s10000_uturn 转弯约束路网 · 基准算例 · 6 个任务"
      - listitem:
        - button "转弯路网 g3x4_s10000_left_cost 转弯约束路网 · 基准算例 · 6 个任务"
      - listitem:
        - button "转弯路网 g3x4_s10000_left_ban 转弯约束路网 · 基准算例 · 6 个任务"
      - listitem:
        - button "转弯路网 g4x4_s10000_uturn 转弯约束路网 · 基准算例 · 7 个任务"
      - listitem:
        - button "转弯路网 g4x4_s10000_left_cost 转弯约束路网 · 基准算例 · 7 个任务"
      - listitem:
        - button "转弯路网 g4x4_s10000_left_ban 转弯约束路网 · 基准算例 · 7 个任务"
      - listitem:
        - button "夹具 dead_end_infeasible 转弯约束路网 · 基准算例 · 1 个任务"
      - listitem:
        - button "夹具 single_customer_cycle 转弯约束路网 · 基准算例 · 1 个任务"
      - listitem:
        - button "夹具 g3x3_s7000_none 转弯约束路网 · 基准算例 · 4 个任务"
      - listitem:
        - button "欧氏 CVRP · 均匀分布 n=20 车辆路径 CVRP · 基准算例 · 20 个任务"
      - listitem:
        - button "欧氏 CVRP · 均匀分布 n=50 车辆路径 CVRP · 基准算例 · 50 个任务"
      - listitem:
        - button "欧氏 CVRP · 均匀分布 n=100 车辆路径 CVRP · 基准算例 · 100 个任务"
      - listitem:
        - button "欧氏 CVRP · 均匀分布 n=200 车辆路径 CVRP · 基准算例 · 200 个任务"
      - listitem:
        - button "欧氏 CVRP · 聚簇分布 n=20 车辆路径 CVRP · 基准算例 · 20 个任务"
      - listitem:
        - button "欧氏 CVRP · 聚簇分布 n=50 车辆路径 CVRP · 基准算例 · 50 个任务"
      - listitem:
        - button "欧氏 CVRP · 聚簇分布 n=100 车辆路径 CVRP · 基准算例 · 100 个任务"
      - listitem:
        - button "欧氏 CVRP · 聚簇分布 n=200 车辆路径 CVRP · 基准算例 · 200 个任务"
- region "地图":
  - tablist:
    - tab "地图" [selected]:
      - text: 地图
      - button "Close 地图"
  - tabpanel "地图"
- region "方案对比":
  - tablist:
    - tab "方案对比" [selected]:
      - text: 方案对比
      - button "Close 方案对比"
    - tab "验算"
    - tab "实验结果"
    - tab "仿真回放"
    - tab "科研图表"
    - tab "日志"
  - tabpanel "方案对比":
    - paragraph: 还没有方案
    - paragraph: 在“推荐与求解”里勾选算法后点击对比，结果会出现在这里。
- region "推荐与求解":
  - tablist:
    - tab "推荐与求解" [selected]:
      - text: 推荐与求解
      - button "Close 推荐与求解"
    - tab "检查器"
    - tab "决策记录"
  - tabpanel "推荐与求解":
    - heading "推荐算法" [level=3]
    - button "重新分析"
    - paragraph: 推荐 转弯模式分层 DP：任务数 2 ≤ 12：优先尝试精确分层 DP，是否证最优以终态和预算为准
    - text: 任务数
    - strong: "2"
    - text: 禁止转弯
    - strong: "0"
    - text: 转弯惩罚
    - strong: "3"
    - list:
      - listitem:
        - checkbox "1 转弯模式分层 DP 本项目 推荐" [checked]
        - text: 1 转弯模式分层 DP 本项目 推荐
        - paragraph: 任务数 2 ≤ 12：优先尝试精确分层 DP，是否证最优以终态和预算为准
      - listitem:
        - checkbox "2 PyVRP + 转弯分层补全 PyVRP" [checked]
        - text: 2 PyVRP + 转弯分层补全 PyVRP
        - paragraph: 规模较大时的首选：PyVRP 定顺序，项目分层 DP 补全转弯可行路径
      - listitem:
        - checkbox "3 OR-Tools GLS + 转弯分层补全 OR-Tools" [checked]
        - text: 3 OR-Tools GLS + 转弯分层补全 OR-Tools
        - paragraph: 与 PyVRP 方案互为对照
      - listitem:
        - checkbox "4 原图状态精确搜索 本项目"
        - text: 4 原图状态精确搜索 本项目
        - paragraph: 小规模时可用独立精确搜索交叉验证最优值
      - listitem:
        - checkbox "5 方向松弛 DP 本项目"
        - text: 5 方向松弛 DP 本项目
        - paragraph: 只作下界参考：忽略进入方向，路线可能违反转弯规则
    - text: 时间预算
    - spinbutton "时间预算 秒/算法": "3"
    - emphasis: 秒/算法
    - text: 随机种子
    - spinbutton "随机种子 提交时冻结": "42"
    - emphasis: 提交时冻结
    - button "对比 3 个算法"
- status: 日志 opened
- alert
- text: 4.3 m 往返路网、两个访问任务，用于集成验收；不是农业场景验证。
- button "经典视图"
- application "场景地图。拖动平移，滚轮或双指缩放，加减号缩放，0 适应内容。":
  - text: 20 cm
  - button "放大"
  - button "缩小"
  - button "适应内容"
- contentinfo:
  - text: 已连接 求解空闲 田间：未运行 · TB4：未运行 官方迷宫 · 双点巡检闭环
  - link "CVRP 数值任务":
    - /url: "#/jobs"
  - link "BPP 历史":
    - /url: "#/bpp"
```

# Test source

```ts
  1  | import { test, expect, shot, listScenarios, API } from './helpers';
  2  | // Fork endpoint: POST /lab/api/scenarios/:id/fork (src/studio/api.ts:101-102); auto-fork on first edit of a
  3  | // built-in scenario saves as “我的场景” (src/studio/store.ts:398,428).
  4  | test('E Fork 超时重试：只生成一份“我的场景”', async ({ page }, info) => {
  5  |   const before = await listScenarios(page);
  6  |   const builtin = before.find((s) => s.origin && s.origin !== 'user') ?? before[0];
  7  |   test.skip(!builtin, 'no built-in scenario');
  8  |   let forkCalls = 0;
  9  |   await page.route(`**${API}/scenarios/*/fork`, async (route) => {
  10 |     forkCalls++;
  11 |     const res = await route.fetch();
  12 |     await new Promise((r) => setTimeout(r, 45_000)); // beyond client timeout (uncertain exact value)
  13 |     await route.fulfill({ response: res }).catch(() => {});
  14 |   });
  15 |   await page.goto(`/#/plan/${encodeURIComponent(builtin.id)}`);
  16 |   const map = page.locator('svg[aria-label="任务地图编辑器"]');
> 17 |   await expect(map).toBeVisible({ timeout: 30_000 });
     |                     ^ Error: expect(locator).toBeVisible() failed
  18 |   await test.step('编辑内置场景触发自动另存', async () => {
  19 |     const x = page.locator('label', { has: page.locator('span', { hasText: /^X$/ }) }).locator('input[type=number]').first();
  20 |     const shape = map.locator('circle').filter({ visible: true }).first();
  21 |     if (await shape.count()) await shape.click({ force: true });
  22 |     if (await x.count()) await x.fill(String(Number(await x.inputValue()) + 1));
  23 |     await shot(page, info, 'edited-builtin');
  24 |   });
  25 |   await test.step('等待超时与重试', async () => {
  26 |     await page.waitForTimeout(60_000);
  27 |     const retry = page.getByRole('button', { name: '重试保存' }); // PlanPanels.tsx:179
  28 |     if (await retry.isVisible()) { await retry.click(); await page.waitForTimeout(50_000); }
  29 |     await shot(page, info, 'after-retry');
  30 |   });
  31 |   await test.step('断言只有一份副本', async () => {
  32 |     const after = await listScenarios(page);
  33 |     const copies = after.filter((s) => !before.some((b) => b.id === s.id) && s.origin === 'user');
  34 |     info.annotations.push({ type: 'forkCalls', description: String(forkCalls) });
  35 |     expect(copies.length).toBe(1);
  36 |   });
  37 | });
  38 | 
```