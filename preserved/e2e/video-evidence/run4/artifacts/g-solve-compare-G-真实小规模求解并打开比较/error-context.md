# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: g-solve-compare.spec.ts >> G 真实小规模求解并打开比较
- Location: tests/g-solve-compare.spec.ts:2:1

# Error details

```
Error: expect(locator).toBeEnabled() failed

Locator: getByRole('button', { name: '求解并验算' })
Expected: enabled
Timeout: 30000ms
Error: element(s) not found

Call log:
  - Expect "toBeEnabled" getByRole('button', { name: '求解并验算' }) with timeout 30000ms
  - waiting for getByRole('button', { name: '求解并验算' })

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
    - text: 导入 GeoJSON / 场景 JSON 我的任务地图 · 8
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
    - paragraph: 推荐 PyVRP 迭代局部搜索：CVRP 迭代局部搜索对照；相对最优已知解的差距由本次求解实测，不预设性能数字
    - text: 客户数
    - strong: "10"
    - text: 容量
    - strong: "8"
    - text: 最少车辆
    - strong: "3"
    - list:
      - listitem:
        - checkbox "1 PyVRP 迭代局部搜索 PyVRP 推荐" [checked]
        - text: 1 PyVRP 迭代局部搜索 PyVRP 推荐
        - paragraph: CVRP 迭代局部搜索对照；相对最优已知解的差距由本次求解实测，不预设性能数字
      - listitem:
        - checkbox "2 OR-Tools 引导局部搜索 OR-Tools" [checked]
        - text: 2 OR-Tools 引导局部搜索 OR-Tools
        - paragraph: 稳健的对照求解器
      - listitem:
        - checkbox "3 Clarke–Wright 节约算法 本项目" [checked]
        - text: 3 Clarke–Wright 节约算法 本项目
        - paragraph: 节约算法构造基线（≤ 100 客户），耗时以实测为准
      - listitem:
        - checkbox "4 最近邻构造 本项目"
        - text: 4 最近邻构造 本项目
        - paragraph: 最近邻构造基线，成本经独立验算
    - text: 时间预算
    - spinbutton "时间预算 秒/算法": "3"
    - emphasis: 秒/算法
    - text: 随机种子
    - spinbutton "随机种子 提交时冻结": "42"
    - emphasis: 提交时冻结
    - button "对比 3 个算法"
- status: 日志 opened
- alert
- text: 官方 depot 地图左侧开阔地面 10 个任务点，仓库 = 机器人起点；直线段经地图间隙检查（可能穿过柱子，会如实报告）。
- button "经典视图"
- application "场景地图。拖动平移，滚轮或双指缩放，加减号缩放，0 适应内容。":
  - text: 2 m
  - button "放大"
  - button "缩小"
  - button "适应内容"
- contentinfo:
  - text: 已连接 求解空闲 田间：未运行 · TB4：未运行 车间空地 · 欧氏 CVRP
  - link "CVRP 数值任务":
    - /url: "#/jobs"
  - link "BPP 历史":
    - /url: "#/bpp"
```

# Test source

```ts
  1  | import { test, expect, shot, listScenarios } from './helpers';
  2  | test('G 真实小规模求解并打开比较', async ({ page }, info) => {
  3  |   const sc = (await listScenarios(page)).find((s) => /cvrp/i.test((s as any).problem_class ?? s.id)) ?? (await listScenarios(page))[0];
  4  |   test.skip(!sc, 'no scenarios');
  5  |   await page.goto(`/#/plan/${encodeURIComponent(sc.id)}`);
  6  |   const solve = page.getByRole('button', { name: '求解并验算' }); // PlanView.tsx:66
  7  |   await test.step('求解', async () => {
> 8  |     await expect(solve).toBeEnabled({ timeout: 30_000 });
     |                         ^ Error: expect(locator).toBeEnabled() failed
  9  |     await shot(page, info, 'before-solve');
  10 |     await solve.click();
  11 |     await expect(page.getByText('正在求解…')).toBeHidden({ timeout: 150_000 }); // PlanView.tsx:72
  12 |     await shot(page, info, 'solved');
  13 |   });
  14 |   await test.step('打开比较/运行记录', async () => {
  15 |     await page.goto('/#/runs');
  16 |     await page.waitForLoadState('networkidle');
  17 |     await shot(page, info, 'compare');
  18 |   });
  19 | });
  20 | 
```