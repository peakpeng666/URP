# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: c-map-editor.spec.ts >> C 地图编辑器：选择对象、拖拽、撤销/重做、数值输入
- Location: tests/c-map-editor.spec.ts:2:1

# Error details

```
Error: expect(locator).toBeVisible() failed

Locator: locator('label').filter({ has: locator('span').filter({ hasText: /^X$/ }) }).locator('input[type=number]').first()
Expected: visible
Timeout: 5000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" locator('label').filter({ has: locator('span').filter({ hasText: /^X$/ }) }).locator('input[type=number]').first() with timeout 5000ms
  - waiting for locator('label').filter({ has: locator('span').filter({ hasText: /^X$/ }) }).locator('input[type=number]').first()

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
    - button "返回已有场景" [expanded]
    - region "农业任务目录":
      - paragraph: 选择农业任务并调整参数，保存后进入现有任务规划流程。
      - text: 生产环境
      - combobox "生产环境":
        - option "全部环境" [selected]
        - option "大田与旱作地"
        - option "水田"
        - option "果园"
        - option "葡萄园"
        - option "茶园"
        - option "设施温室"
        - option "苗圃"
        - option "丘陵梯田"
        - option "牧草地与牧场"
        - option "畜禽养殖设施"
        - option "农场仓储与装卸区"
        - option "多田块农场及连接路网"
        - option "水产养殖水面"
        - option "农业空域（无人机）"
      - text: 农业作业
      - combobox "农业作业":
        - option "全部作业" [selected]
        - option "耕整地"
        - option "播种"
        - option "移栽"
        - option "中耕"
        - option "植保（全田喷施）"
        - option "植保（选择性/斑块）"
        - option "植保（逐株定点）"
        - option "除草（机械）"
        - option "施肥（变量追肥）"
        - option "土壤及作物采样"
        - option "环境监测"
        - option "逐株检查"
        - option "灌溉设施巡检"
        - option "采收"
        - option "果园修剪"
        - option "接粮与运输"
        - option "联合收获"
        - option "草捆收集"
        - option "秸秆处理"
        - option "割草"
        - option "搂草"
        - option "打捆"
        - option "苗木及物料搬运"
        - option "饲喂"
        - option "推料"
        - option "圈舍清扫"
        - option "补水补药（站点补给）"
        - option "充电（充电桩调度）"
        - option "卸载（港池/粮库排队）"
        - option "入库与转场"
      - text: 模式状态
      - combobox "模式状态":
        - option "全部状态" [selected]
        - option "可构建模板"
        - option "近似模板"
        - option "提案（不可提交）"
      - paragraph: 当前 39 个模式
      - button "下载完整矩阵 JSON"
      - button "下载完整矩阵 CSV"
      - group:
        - text: 果园采收集运 · 可构建模板
        - paragraph: 采摘点（树位/行间集中点）带载果需求，车辆沿行间通道收集并卸至田头装车点，多趟往返。
        - paragraph: 采摘点是真实的带需求点集（点集 + 容量 + 卸载），不是行服务的近似；行间通行用 travel=rows 的真实通道图，地头/机耕路为开阔区。
        - paragraph: 目标：点集（可带需求） / 容量车辆路径
        - list:
          - listitem: 定义：yes · 任务、容量、卸载点、行间通行均有契约字段。
          - listitem: 编辑：yes · 任务点、车库、容量、需求在既有地图编辑器全部可改。
          - listitem: 求解：yes · fleet_routing 原生语义：点集需求 + 容量 + unload_points 卸货 + rows 通行。
          - listitem: 验算：yes · fleet.check 独立复算容量、趟次、作业位置与通行约束（rows 时重生成作物行核对路线不斜穿作物）。
          - listitem: 仿真：partial · 同构差速、无曲率约束、≤15 台时可申请进入生成的田间 Gazebo 世界（串行预约执行）；其余组合执行入口按契约返回 422。
          - listitem: 实验：no · 本版本模板尚无关联的持久化运行证据；请提交真实求解并检查独立验算结果，不将历史文案视为通过。
        - figure "36 个服务对象，1 个库点，1 个卸货点，车体半径 0.75 m。 范围 180.0 × 120.0 m。图例：圆为服务对象，方块为库点或起点，三角为卸货点，斜线填充为障碍，虚线为地块，红色和感叹号为问题。 图层":
          - img "果园采收集运 几何预览": 原点 (0,0) · x→ y↑ 50 m
          - text: 36 个服务对象，1 个库点，1 个卸货点，车体半径 0.75 m。 范围 180.0 × 120.0 m。图例：圆为服务对象，方块为库点或起点，三角为卸货点，斜线填充为障碍，虚线为地块，红色和感叹号为问题。
          - group "图层":
            - checkbox "地块" [checked]
            - text: 地块
            - checkbox "障碍" [checked]
            - text: 障碍
            - checkbox "服务对象" [checked]
            - text: 服务对象
            - checkbox "库点/卸货点" [checked]
            - text: 库点/卸货点
            - checkbox "问题标记" [checked]
            - text: 问题标记
        - group:
          - text: 田块宽度 (m)
          - spinbutton "果园采收集运 田块宽度": "180"
          - text: 田块高度 (m)
          - spinbutton "果园采收集运 田块高度": "120"
          - text: 行向角 (°)
          - spinbutton "果园采收集运 行向角": "0"
          - text: 任务点数
          - spinbutton "果园采收集运 任务点数": "36"
          - text: 单点需求
          - spinbutton "果园采收集运 单点需求": "200"
          - text: 车辆数
          - spinbutton "果园采收集运 车辆数": "3"
          - text: 单车容量
          - spinbutton "果园采收集运 单车容量": "1200"
          - text: 行驶速度 (m/s)
          - spinbutton "果园采收集运 行驶速度": "0.8"
          - text: 机器人半径 (m)
          - spinbutton "果园采收集运 机器人半径": "0.75"
          - text: 车库位置
          - combobox "果园采收集运 车库位置":
            - option "西南角" [selected]
            - option "北侧机耕路"
            - option "东侧机耕路"
          - text: 优化目标
          - combobox "果园采收集运 优化目标":
            - option "均衡完成时间" [selected]
            - option "总里程"
          - text: 田头补给/卸载点
          - checkbox "果园采收集运 田头补给/卸载点" [checked]
          - text: 内部障碍数
          - spinbutton "果园采收集运 内部障碍数": "1"
          - text: 障碍半径 (m)
          - spinbutton "果园采收集运 障碍半径": "12"
          - text: 随机种子
          - spinbutton "果园采收集运 随机种子": "42"
          - button "下载原始场景 JSON"
          - note:
            - text: 此模式上次导入为
            - link "果园采收集运":
              - /url: "#/plan/agri-orchard-harvest-tran-ad488926-0a7a-4f32-8b33-067729068dcd"
            - text: （种子 42）。再次导入会新建一个场景，不会覆盖你在地图上对那份做的手工编辑；要保留手工成果请继续编辑原场景。
          - note:
            - text: 那份场景相对生成结果有手工编辑：通道已改动；车队配置已改动。重新生成不会带上这些编辑。
            - button "用该场景的参数和种子填回表单"
          - button "清除草稿并恢复默认"
          - button "校验并导入任务规划"
        - paragraph: 保存后可继续编辑地图、选择算法并求解；仿真可用性由当前场景与车型决定。
      - group: 果园植保（离散喷施点近似） · 近似模板
      - group: 大田接粮运输（固定装载点） · 可构建模板
      - group: 土壤与作物采样 · 可构建模板
      - group: 定点变量除草 · 可构建模板
      - group: 温室采收物流 · 可构建模板
      - group: 多田块机群作业分配 · 近似模板
      - group: 牧场与草地巡检 · 可构建模板
      - group: 茶园鲜叶集运 · 近似模板
      - group: 草捆收集运输 · 可构建模板
      - group: 异构机队集运（大小车混编） · 可构建模板
      - group: 不可倒车车辆转场（Dubins 曲率约束） · 可构建模板
      - group: 大田耕整全覆盖 · 可构建模板
      - group: 含障碍田块覆盖 · 可构建模板
      - group: 无人机田区航测（平面近似） · 近似模板
      - group: 水田秧苗/稻谷转运（无下陷近似） · 近似模板
      - group: 葡萄园植保（行间近似） · 近似模板
      - group: 牛舍推料（通道近似） · 近似模板
      - group: 苗圃盆苗集运（无配对近似） · 近似模板
      - group: 梯田集运（无坡度近似） · 近似模板
      - group: 水产养殖投喂巡检（水面近似） · 近似模板
      - group: 温室轨道巡检（自由点访问代理） · 近似模板
      - group: 行服务 CARP（果树/大田逐行作业） · 提案（不可提交）
      - group: 地头转弯模式优化（B-pattern） · 提案（不可提交）
      - group: 压实约束路径（CTF 行走道） · 提案（不可提交）
      - group: 牵引机具扫掠转弯校验 · 提案（不可提交）
      - group: 斑块选择性覆盖（病虫草害） · 提案（不可提交）
      - group: 坡地与梯田风险约束路径 · 提案（不可提交）
      - group: 水田插秧行服务 · 提案（不可提交）
      - group: 并行时空冲突调度（多机共道） · 提案（不可提交）
      - group: 收割机—接粮车动态汇合 · 提案（不可提交）
      - group: 空地协同（无人机+地面车） · 提案（不可提交）
      - group: 采收时间窗（成熟度与冷链） · 提案（不可提交）
      - group: 动态任务流（病虫草情即时报送） · 提案（不可提交）
      - group: 动态障碍（牲畜/人员活动区） · 提案（不可提交）
      - group: 定时饲喂班次（TMR 配送） · 提案（不可提交）
      - group: 农场仓储出入库取送 · 提案（不可提交）
      - group: 多塘水产转场（闸口连接） · 提案（不可提交）
      - group: 无人机能耗覆盖航测 · 提案（不可提交）
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
    - paragraph: 推荐 OR-Tools 车队调度：规则建议：OR-Tools 使用路线跨度与里程的加权目标；时间为匀速代理，不含转向或交通排队
    - text: 任务点
    - strong: "36"
    - text: 车辆
    - strong: "3"
    - text: 至少需要的趟数
    - strong: "6"
    - text: 车型类别
    - strong: "1"
    - text: 障碍占地
    - strong: 2.02 %
    - text: 聚集度 R
    - strong: "0.85"
    - text: 目标
    - strong: 均衡完成时间
    - list:
      - listitem:
        - checkbox "1 OR-Tools 车队调度 OR-Tools 推荐" [checked]
        - text: 1 OR-Tools 车队调度 OR-Tools 推荐
        - paragraph: 规则建议：OR-Tools 使用路线跨度与里程的加权目标；时间为匀速代理，不含转向或交通排队
        - paragraph: 总量需要至少 6 趟，多趟往返会分配到 3 台车上
        - text: 地面风险策略
        - combobox "OR-Tools 车队调度 地面风险策略":
          - option "忽略地面风险" [selected]
          - option "风险加权与限速"
        - text: 默认 ignore · 推荐 ignore 地面风险权重（当量米/米）
        - spinbutton "OR-Tools 车队调度 地面风险权重（当量米/米）": "1"
        - text: 默认 1 · 推荐 1 · 范围 0–10
      - listitem:
        - checkbox "2 PyVRP 固定车队 PyVRP" [checked]
        - text: 2 PyVRP 固定车队 PyVRP
        - paragraph: 以总里程为搜索目标，不直接均衡各车工作量；是否更优需同实例比较
        - paragraph: 总量需要至少 6 趟，多趟往返会分配到 3 台车上
        - text: 地面风险策略
        - combobox "PyVRP 固定车队 地面风险策略":
          - option "忽略地面风险" [selected]
          - option "风险加权与限速"
        - text: 默认 ignore · 推荐 ignore 地面风险权重（当量米/米）
        - spinbutton "PyVRP 固定车队 地面风险权重（当量米/米）": "1"
        - text: 默认 1 · 推荐 1 · 范围 0–10
      - listitem:
        - checkbox "3 节约算法 + 2-opt 基线" [checked]
        - text: 3 节约算法 + 2-opt 基线
        - paragraph: 确定性构造基线，可作为改进幅度的参照；耗时以实测为准
        - text: 地面风险策略
        - combobox "节约算法 + 2-opt 地面风险策略":
          - option "忽略地面风险" [selected]
          - option "风险加权与限速"
        - text: 默认 ignore · 推荐 ignore 地面风险权重（当量米/米）
        - spinbutton "节约算法 + 2-opt 地面风险权重（当量米/米）": "1"
        - text: 默认 1 · 推荐 1 · 范围 0–10
      - listitem:
        - checkbox "4 先聚类后排程 基线"
        - text: 4 先聚类后排程 基线
        - paragraph: 按区域划分各车负责范围，便于现场分工
      - listitem:
        - checkbox "5 扫描算法 基线"
        - text: 5 扫描算法 基线
        - paragraph: 按车库方位进行扫描切分的构造基线
    - text: 时间预算
    - spinbutton "时间预算 秒/算法": "5"
    - emphasis: 秒/算法
    - text: 随机种子
    - spinbutton "随机种子 提交时冻结": "42"
    - emphasis: 提交时冻结
    - button "对比 3 个算法"
- status: 日志 opened
- alert
- group "编辑工具":
  - button "选择" [pressed]
  - button "平移"
  - button "任务点"
  - button "障碍"
  - button "地块"
  - button "车库"
  - button "补给点"
  - button "机耕道"
- button "撤销 (⌘Z)"
- button "重做 (⇧⌘Z)" [disabled]
- button "适配全图 (F)"
- text: 已保存
- application "任务地图编辑器": 地块1 · 苹果 采摘点1 采摘点2 采摘点3 采摘点4 采摘点5 采摘点6 采摘点7 采摘点8 采摘点9 采摘点10 采摘点11 采摘点12 采摘点13 采摘点14 采摘点15 采摘点16 采摘点17 采摘点18 采摘点19 采摘点20 采摘点21 采摘点22 采摘点23 采摘点24 采摘点25 采摘点26 采摘点27 采摘点28 采摘点29 采摘点30 采摘点31 采摘点32 采摘点33 采摘点34 采摘点35 采摘点36 U1 D1 20 m 180 × 120 m
- contentinfo:
  - text: 已连接 求解空闲 田间：未运行 · TB4：未运行 果园采收集运 选中：地块 P1
  - link "CVRP 数值任务":
    - /url: "#/jobs"
  - link "BPP 历史":
    - /url: "#/bpp"
```

# Test source

```ts
  1  | import { test, expect, shot, openAgriCatalog, firstRunnablePattern } from './helpers';
  2  | test('C 地图编辑器：选择对象、拖拽、撤销/重做、数值输入', async ({ page }, info) => {
  3  |   await openAgriCatalog(page);
  4  |   const { card } = await firstRunnablePattern(page);
  5  |   await card.getByRole('button', { name: '校验并导入任务规划' }).click();
  6  |   await expect(page).toHaveURL(/#\/plan\/.+/, { timeout: 60_000 });
  7  |   const map = page.locator('svg[aria-label="任务地图编辑器"]'); // FieldEditor.tsx:320-321
  8  |   await expect(map).toBeVisible({ timeout: 30_000 });
  9  |   const undo = page.getByRole('button', { name: /撤销/ }); // PlanPanels.tsx:141 (title="撤销 (⌘Z)")
  10 |   const redo = page.getByRole('button', { name: /重做/ }); // PlanPanels.tsx:142
  11 |   const box = (await map.boundingBox())!;
  12 |   await test.step('选择对象（点击地图中心附近的对象）', async () => {
  13 |     // Uncertain: no data-testid on SVG shapes; click the first task/obstacle shape in the SVG.
  14 |     const shape = map.locator('circle, polygon, path').filter({ visible: true }).nth(1);
  15 |     if (await shape.count()) await shape.click({ force: true }); else await page.mouse.click(box.x + box.width / 2, box.y + box.height / 2);
  16 |     await shot(page, info, 'selected');
  17 |   });
  18 |   const xInput = page.locator('label', { has: page.locator('span', { hasText: /^X$/ }) }).locator('input[type=number]').first(); // PlanPanels.tsx:392-397
  19 |   const before = (await xInput.count()) ? await xInput.inputValue() : null;
  20 |   await test.step('拖拽对象', async () => {
  21 |     const sel = map.locator('circle, polygon, path').filter({ visible: true }).nth(1);
  22 |     const b = await sel.boundingBox();
  23 |     if (b) { await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2); await page.mouse.down(); await page.mouse.move(b.x + b.width / 2 + 60, b.y + b.height / 2 + 30, { steps: 12 }); await page.mouse.up(); }
  24 |     await shot(page, info, 'dragged');
  25 |     await expect(undo).toBeEnabled();
  26 |   });
  27 |   await test.step('撤销', async () => { await undo.click(); await shot(page, info, 'undone'); if (before !== null) await expect(xInput).toHaveValue(before); await expect(redo).toBeEnabled(); });
  28 |   await test.step('重做', async () => { await redo.click(); await shot(page, info, 'redone'); });
  29 |   await test.step('数值输入 X', async () => {
> 30 |     await expect(xInput).toBeVisible();
     |                          ^ Error: expect(locator).toBeVisible() failed
  31 |     await xInput.fill('12.5'); await xInput.blur();
  32 |     await expect(xInput).toHaveValue('12.5');
  33 |     await shot(page, info, 'numeric');
  34 |   });
  35 | });
  36 | 
```