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

Locator: getByRole('button', { name: '打开农业任务目录' })
Expected: visible
Timeout: 30000ms
Error: element(s) not found

Call log:
  - Expect "toBeVisible" getByRole('button', { name: '打开农业任务目录' }) with timeout 30000ms
  - waiting for getByRole('button', { name: '打开农业任务目录' })

```

# Test source

```ts
  1  | import { expect, type Page, type TestInfo, test } from '@playwright/test';
  2  | export const API = '/lab/api'; // src/lab/api.ts:28, src/studio/api.ts:22
  3  | export async function shot(page: Page, info: TestInfo, name: string) {
  4  |   const path = info.outputPath(`${String(info.attachments.length).padStart(2, '0')}-${name}.png`);
  5  |   await page.screenshot({ path, fullPage: false });
  6  |   await info.attach(name, { path, contentType: 'image/png' });
  7  | }
  8  | /** Open the scenario library's agri catalog (src/studio/panels/LibraryPanels.tsx:51). */
  9  | export async function openAgriCatalog(page: Page) {
  10 |   await page.goto('/#/plan');
  11 |   const toggle = page.getByRole('button', { name: '打开农业任务目录' });
> 12 |   await expect(toggle).toBeVisible({ timeout: 30_000 });
     |                        ^ Error: expect(locator).toBeVisible() failed
  13 |   await toggle.click();
  14 |   const catalog = page.getByRole('region', { name: '农业任务目录' }); // AgriCatalog.tsx:20
  15 |   await expect(catalog).toBeVisible();
  16 |   return catalog;
  17 | }
  18 | /** First runnable (non-proposal) pattern card: has a 校验并导入任务规划 button (AgriCatalog.tsx:99). */
  19 | export async function firstRunnablePattern(page: Page) {
  20 |   const catalog = page.getByRole('region', { name: '农业任务目录' });
  21 |   const cards = catalog.locator('details');
  22 |   const n = await cards.count();
  23 |   for (let i = 0; i < n; i++) {
  24 |     const c = cards.nth(i);
  25 |     if (!(await c.isVisible())) continue;
  26 |     await c.locator('summary').click();
  27 |     if (await c.getByRole('button', { name: '校验并导入任务规划' }).count()) {
  28 |       const name = (await c.locator('summary').innerText()).split(' · ')[0].trim();
  29 |       return { card: c, name };
  30 |     }
  31 |     await c.locator('summary').click();
  32 |   }
  33 |   throw new Error('no runnable agri pattern found');
  34 | }
  35 | export async function listScenarios(page: Page): Promise<Array<{ id: string; title: string; origin?: string }>> {
  36 |   const r = await page.request.get(`${API}/scenarios`); // src/lab/api.ts:81
  37 |   expect(r.ok()).toBeTruthy();
  38 |   return (await r.json()).scenarios;
  39 | }
  40 | export { test, expect };
  41 | 
```