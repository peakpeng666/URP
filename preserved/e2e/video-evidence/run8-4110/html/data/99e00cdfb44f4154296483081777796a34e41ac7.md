# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: h-precheck-locate.spec.ts >> H 预检定位：点击预检问题高亮对象并聚焦表单字段
- Location: tests/h-precheck-locate.spec.ts:4:1

# Error details

```
Error: first located field focused

expect(locator).toBeFocused() failed

Locator:  locator('[data-located] input, [data-located] select').first()
Expected: focused
Received: inactive
Timeout:  5000ms

Call log:
  - first located field focused locator('[data-located] input, [data-located] select').first() with timeout 5000ms
  - waiting for locator('[data-located] input, [data-located] select').first()
    14 × locator resolved to <input min="0.2" max="1.5" step="any" value="0.6" type="number" class="_input_a5ga1_358" aria-label="行间机械除草（固定行向覆盖近似） 行距"/>
       - unexpected value "inactive"

```

```yaml
- spinbutton "行间机械除草（固定行向覆盖近似） 行距": "0.6"
```

```
Error: first located label is 地头宽

expect(locator).toContainText(expected) failed

Locator: locator('label[data-located]').first()
Expected substring: "地头宽"
Received string:    "行距 (m)相邻作物行中线距离，如玉米 0.6 m、大豆 0.45 m。"
Timeout: 5000ms

Call log:
  - first located label is 地头宽 locator('label[data-located]').first() with timeout 5000ms
  - waiting for locator('label[data-located]').first()
    14 × locator resolved to <label data-located="true" id="agri-param-row-weeding-coverage-row_spacing">…</label>
       - unexpected value "行距 (m)相邻作物行中线距离，如玉米 0.6 m、大豆 0.45 m。"

```

```yaml
- text: 行距 (m)
- spinbutton "行间机械除草（固定行向覆盖近似） 行距": "0.6"
- text: 相邻作物行中线距离，如玉米 0.6 m、大豆 0.45 m。
```

# Test source

```ts
  1  | import { test, expect, shot, openAgriCatalog } from './helpers';
  2  | // Luna 9dfd4e09: catalog precheck (no import). Click issue in ul[aria-label=预检问题] (PreviewMap.tsx:49-50) →
  3  | // target highlighted ([data-picked]) and param <label data-located> (AgriCatalog.tsx:157) input focused.
  4  | test('H 预检定位：点击预检问题高亮对象并聚焦表单字段', async ({ page }, info) => {
  5  |   const catalog = await openAgriCatalog(page);
  6  |   const card = catalog.locator('details', { has: page.locator('summary', { hasText: '行间机械除草' }) }).first();
  7  |   await card.locator('summary').click();
  8  |   await test.step('地头宽度设为小于幅宽', async () => {
  9  |     // aria-label is `${p.name} ${param.label}`; name has （固定行向覆盖近似）. 地头宽 must stay ≥ 最小转弯半径 (5 m) or the preview
  10 |     // errors out with no 预检问题 list (run8 dry-run), so widen 幅宽: 12 行 × 0.6 m = 7.2 m, 地头宽 6 m (preview.ts:82 warning).
  11 |     await card.getByLabel(/^行间机械除草.* 每趟行数$/).fill('12');
  12 |     const hw = card.getByLabel(/^行间机械除草.* 地头宽度$/);
  13 |     await hw.fill('6'); await hw.blur();
  14 |     await shot(page, info, 'headland-6m-swath-7.2m');
  15 |   });
  16 |   const issue = card.locator('ul[aria-label="预检问题"]').getByRole('button', { name: /地头宽.*小于.*幅宽/ });
  17 |   await test.step('预检问题出现', async () => { await expect(issue).toBeVisible({ timeout: 10_000 }); });
  18 |   await test.step('点击问题 → 高亮对象 + 聚焦地头宽度', async () => {
  19 |     await issue.click();
  20 |     await expect(card.locator('[data-picked]').first()).toBeAttached();
  21 |     // locateIssue focuses keys[0]=headland_width (AgriCatalog.tsx:93-98) but issueFields also marks 行距/每趟行数/机具宽度
  22 |     // (preview.ts:101), which precede 地头宽度 in DOM. Hard: focused input is 地头宽度 and is [data-located].
  23 |     const hw = card.getByLabel(/^行间机械除草.* 地头宽度$/);
  24 |     await expect(hw).toBeFocused();
  25 |     await expect(card.locator('label[data-located]', { has: page.locator('input[aria-label$=" 地头宽度"]') })).toContainText('地头宽');
  26 |     // Spec as written: the FIRST [data-located] field is focused and its label is 地头宽 — soft, so the gap is recorded.
  27 |     await expect.soft(page.locator('[data-located] input, [data-located] select').first(), 'first located field focused').toBeFocused();
> 28 |     await expect.soft(page.locator('label[data-located]').first(), 'first located label is 地头宽').toContainText('地头宽');
     |                                                                                                  ^ Error: first located label is 地头宽
  29 |     await shot(page, info, 'located');
  30 |   });
  31 |   await test.step('点击地图形状只高亮不定位', async () => {
  32 |     await page.locator('body').click({ position: { x: 1, y: 1 } });
  33 |     await card.locator('[data-target="boundary"]').click({ force: true });
  34 |     await expect(card.locator('[data-target="boundary"][data-picked]')).toBeAttached();
  35 |     await shot(page, info, 'shape-highlight');
  36 |   });
  37 | });
  38 | 
```