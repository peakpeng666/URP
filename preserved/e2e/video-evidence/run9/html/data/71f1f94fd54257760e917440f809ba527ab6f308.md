# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: f-result-integrity.spec.ts >> F 结果完整性：隔离未核验来源、缺字段显示未核验、隔离结果不进比较组
- Location: tests/f-result-integrity.spec.ts:5:1

# Error details

```
Error: excluded entry says 已隔离 · 不适用

expect(locator).toContainText(expected) failed

Locator: getByLabel('未参与比较的运行').locator('li').filter({ hasText: '已隔离' }).first()
Expected substring: "已隔离 · 不适用"
Received string:    "先聚类后排程 · run_e2e_ · 出错 · 源码身份不符 · 已隔离"
Timeout: 5000ms

Call log:
  - excluded entry says 已隔离 · 不适用 getByLabel('未参与比较的运行').locator('li').filter({ hasText: '已隔离' }).first() with timeout 5000ms
  - waiting for getByLabel('未参与比较的运行').locator('li').filter({ hasText: '已隔离' }).first()
    14 × locator resolved to <li data-exclusion="quarantined">…</li>
       - unexpected value "先聚类后排程 · run_e2e_ · 出错 · 源码身份不符 · 已隔离"

```

```yaml
- listitem: 先聚类后排程 · run_e2e_ · 出错 · 源码身份不符 · 已隔离
```

# Test source

```ts
  1  | import { test, expect, shot, API } from './helpers';
  2  | // Uses the real labdata test records (no stubs): run_e2e_quarantined_unverified (source_identity_verified=false)
  3  | // and run_e2e_legacy_noidentity (no identity fields). Entry: 方案对比 → HistoryRuns.tsx → 加入比较; excluded list PlanPanels.tsx:955.
  4  | const Q = 'run_e2e_quarantined_unverified', L = 'run_e2e_legacy_noidentity';
  5  | test('F 结果完整性：隔离未核验来源、缺字段显示未核验、隔离结果不进比较组', async ({ page }, info) => {
  6  |   // #/runs no longer has the "显示 N / 最近 N 次" table in the Studio shell; history entry is 方案对比 → HistoryRuns.tsx.
  7  |   const one = await page.request.get(`${API}/runs/${Q}`);
  8  |   test.skip(!one.ok(), 'test record missing from labdata');
  9  |   const q = await one.json();
  10 |   expect(q.process.source_identity_verified).toBe(false);
  11 |   await page.goto(`/#/plan/${encodeURIComponent(q.scenario_id)}`);
  12 |   await page.getByText('方案对比', { exact: true }).first().click();
  13 |   const hist = page.getByRole('button', { name: '历史运行（本场景，含失败/已隔离/身份未核验）' });
  14 |   await expect(hist).toBeVisible({ timeout: 30_000 });
  15 |   await hist.click();
  16 |   await test.step('加入比较：隔离 + 缺字段', async () => {
  17 |     for (const id of [Q, L]) {
  18 |       const row = page.getByLabel('历史运行').locator('tr', { hasText: id }).first();
  19 |       await expect(row).toBeVisible({ timeout: 15_000 });
  20 |       await row.getByRole('button', { name: '加入比较' }).click();
  21 |     }
  22 |     await shot(page, info, 'history-added');
  23 |   });
  24 |   await test.step('隔离运行在「未参与比较与排名」，无数值', async () => {
  25 |     const excluded = page.getByLabel('未参与比较的运行');
  26 |     const qi = excluded.locator('li').filter({ hasText: '已隔离' }).first();
  27 |     await expect(qi).toHaveAttribute('data-exclusion', 'quarantined');
  28 |     // Spec text「已隔离 · 不适用」: source emits it only in the table check column (PlanPanels.tsx:914); excluded <li> shows
  29 |     // `${name} · ${id.slice(0,8)} · ${resultState} · ${reason}` (PlanPanels.tsx:958). Kept as soft so the mismatch is recorded.
> 30 |     await expect.soft(qi, 'excluded entry says 已隔离 · 不适用').toContainText('已隔离 · 不适用');
     |                                                            ^ Error: excluded entry says 已隔离 · 不适用
  31 |     await expect(qi.getByText(/\d+\.\d|km|\bm\b/)).toHaveCount(0);
  32 |     // the quarantined run is still a table row with 比较 check column「已隔离 · 不适用」(PlanPanels.tsx:914)
  33 |     await expect(page.locator('tbody tr', { has: page.locator('td', { hasText: /^已隔离 · 不适用$/ }) })).toHaveCount(1);
  34 |     await shot(page, info, 'excluded');
  35 |   });
  36 |   await test.step('缺字段运行：身份未核验，单独分组', async () => {
  37 |     await expect(page.getByText('身份未核验', { exact: true }).first()).toBeVisible();
  38 |     await expect(page.getByText(/种比较口径（含身份未核验组）/)).toBeVisible();
  39 |     await shot(page, info, 'unverified-group');
  40 |   });
  41 |   await test.step('结果：隔离横幅 + 原因', async () => {
  42 |     // ExperimentPanel shows the focused run: click the quarantined row's first cell to focus it, then open 实验结果.
  43 |     await page.locator('tbody tr', { has: page.locator('td', { hasText: /^已隔离 · 不适用$/ }) }).locator('td').first().click();
  44 |     await page.getByRole('tab', { name: '实验结果' }).click();
  45 |     await expect(page.getByText(/已隔离：.+/).first()).toBeVisible({ timeout: 10_000 });
  46 |     await shot(page, info, 'result-tab');
  47 |   });
  48 | });
  49 | 
```