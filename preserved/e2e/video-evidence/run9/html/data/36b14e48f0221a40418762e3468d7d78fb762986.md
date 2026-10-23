# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: k-generated-from.spec.ts >> K 生成来源：参数化 → 手工编辑 → 回到目录改参数
- Location: tests/k-generated-from.spec.ts:14:1

# Error details

```
Error: expect(locator).toHaveAttribute(expected) failed

Locator:  getByRole('region', { name: '生成来源' }).or(locator('section[aria-label="生成来源"]')).first()
Expected: "parametric"
Received: "manual"
Timeout:  5000ms

Call log:
  - Expect "toHaveAttribute" getByRole('region', { name: '生成来源' }).or(locator('section[aria-label="生成来源"]')).first() with timeout 5000ms
  - waiting for getByRole('region', { name: '生成来源' }).or(locator('section[aria-label="生成来源"]')).first()
    14 × locator resolved to <section aria-label="生成来源" data-generated="manual">…</section>
       - unexpected value "manual"

```

```yaml
- region "生成来源":
  - heading "生成来源：果园采收集运" [level=4]
  - paragraph: 种子 7；田块宽度 180 m，田块高度 120 m，行向角 0 °，任务点数 36，单点需求 200，车辆数 3，单车容量 1200，行驶速度 0.8 m/s，机器人半径 0.75 m，车库位置 sw，优化目标 makespan，田头补给/卸载点 true，内部障碍数 1，障碍半径 12 m
  - status: 手工编辑：通道已改动；车队配置已改动。回到目录改参数重新生成会得到新场景，这些手工编辑只留在本场景。
  - button "回到目录改参数"
```

# Test source

```ts
  1  | // Luna 260abc42 (workbench 7c8a6f65): 生成来源 section (studio/agri/GeneratedFrom.tsx) inside ScenarioInfo (PlanPanels.tsx:632,654,
  2  | // shown in the 检查器 dock tab). data-generated = parametric | manual | unknown. 回到目录改参数 → #/archive, catalog card reopened
  3  | // with the scenario's params + seed (AgriCatalog.tsx:60-89).
  4  | import { test, expect, shot, openAgriCatalog, firstRunnablePattern, openInspectorTab } from './helpers';
  5  | async function readForm(card: any, name: string) {
  6  |   const out: Record<string, string> = {};
  7  |   const fields = card.locator(`fieldset [aria-label^="${name} "]`);
  8  |   for (let i = 0; i < (await fields.count()); i++) {
  9  |     const f = fields.nth(i); const k = (await f.getAttribute('aria-label'))!;
  10 |     out[k] = (await f.getAttribute('type')) === 'checkbox' ? String(await f.isChecked()) : await f.inputValue();
  11 |   }
  12 |   return out;
  13 | }
  14 | test('K 生成来源：参数化 → 手工编辑 → 回到目录改参数', async ({ page }, info) => {
  15 |   await openAgriCatalog(page);
  16 |   const { card, name } = await firstRunnablePattern(page);
  17 |   await card.getByLabel(`${name} 随机种子`).fill('7');
  18 |   const form = await readForm(card, name);
  19 |   expect(form[`${name} 随机种子`]).toBe('7');
  20 |   await card.getByRole('button', { name: '校验并导入任务规划' }).click();
  21 |   await expect(page).toHaveURL(/#\/plan\/.+/, { timeout: 60_000 });
  22 |   const map = page.locator('svg[aria-label="任务地图编辑器"]');
  23 |   await expect(map).toBeVisible({ timeout: 30_000 });
  24 |   await openInspectorTab(page);
  25 |   const scenarioBtn = page.getByRole('group', { name: '检查器' }).getByRole('button', { name: '场景', exact: true }); // fleet inspector: 车队/选中/场景 (PlanPanels.tsx:399)
  26 |   if (await scenarioBtn.count()) await scenarioBtn.click();
  27 |   const gen = page.getByRole('region', { name: '生成来源' }).or(page.locator('section[aria-label="生成来源"]')).first();
  28 |   await test.step('导入后：参数化生成', async () => {
  29 |     await expect(gen).toBeVisible({ timeout: 15_000 });
> 30 |     await expect(gen).toHaveAttribute('data-generated', 'parametric');
     |                       ^ Error: expect(locator).toHaveAttribute(expected) failed
  31 |     await expect(gen).toContainText('种子 7');
  32 |     await shot(page, info, 'parametric');
  33 |   });
  34 |   await test.step('拖动任务点 → 手工编辑并列出变化', async () => {
  35 |     const t = (await map.locator('g[data-hit="task"]').first().boundingBox())!;
  36 |     await page.mouse.move(t.x + t.width / 2, t.y + t.height / 2); await page.mouse.down();
  37 |     await page.mouse.move(t.x + t.width / 2 + 60, t.y + t.height / 2 + 30, { steps: 12 }); await page.mouse.up();
  38 |     await openInspectorTab(page);
  39 |     if (await scenarioBtn.count()) await scenarioBtn.click();
  40 |     await expect(gen).toHaveAttribute('data-generated', 'manual', { timeout: 10_000 });
  41 |     await expect(gen.getByRole('status')).toContainText(/手工编辑.*：.+/);
  42 |     await shot(page, info, 'manual');
  43 |   });
  44 |   await test.step('回到目录改参数 → 卡片展开，参数与种子一致', async () => {
  45 |     await gen.getByRole('button', { name: '回到目录改参数' }).click();
  46 |     await expect(page).toHaveURL(/#\/archive/);
  47 |     const catalog = page.getByRole('region', { name: '农业任务目录' });
  48 |     await expect(catalog).toBeVisible({ timeout: 15_000 });
  49 |     const back = catalog.locator('details', { has: page.locator('summary', { hasText: name }) }).first();
  50 |     await expect(back).toHaveAttribute('open', '');
  51 |     await expect(back.getByLabel(`${name} 随机种子`)).toHaveValue('7');
  52 |     expect(await readForm(back, name)).toEqual(form);
  53 |     await shot(page, info, 'back-to-catalog');
  54 |   });
  55 | });
  56 | 
```