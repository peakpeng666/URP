# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: g-solve-compare.spec.ts >> G 真实小规模求解并打开比较
- Location: tests/g-solve-compare.spec.ts:2:1

# Error details

```
Error: expect(locator).not.toHaveText(expected) failed

Locator: getByText(/个已验算可行解/)
Expected pattern: not / 0 个已验算可行解/
Received string: "本批 3 次运行 · 0 个已验算可行解。最佳值仅在相同输入、目标、单位和时间预算内标记。"
Timeout: 5000ms

Call log:
  - Expect "not toHaveText" getByText(/个已验算可行解/) with timeout 5000ms
  - waiting for getByText(/个已验算可行解/)
    14 × locator resolved to <p class="_meta_185g6_5">本批 3 次运行 · 0 个已验算可行解。最佳值仅在相同输入、目标、单位和时间预算内标记。</p>
       - unexpected value "本批 3 次运行 · 0 个已验算可行解。最佳值仅在相同输入、目标、单位和时间预算内标记。"

```

```yaml
- paragraph: 本批 3 次运行 · 0 个已验算可行解。最佳值仅在相同输入、目标、单位和时间预算内标记。
```

# Test source

```ts
  1  | import { test, expect, shot, listScenarios } from './helpers';
  2  | test('G 真实小规模求解并打开比较', async ({ page }, info) => {
  3  |   const sc = (await listScenarios(page)).find((s) => /cvrp/i.test((s as any).problem_class ?? s.id)) ?? (await listScenarios(page))[0];
  4  |   test.skip(!sc, 'no scenarios');
  5  |   await page.goto(`/#/plan/${encodeURIComponent(sc.id)}`);
  6  |   // lab PlanView (求解并验算) is not mounted: App.tsx renders <Studio> for lab views; Studio solve = AdvisorPanel 对比 N 个算法.
  7  |   const solve = page.getByRole('button', { name: /^对比 \d+ 个算法$/ });
  8  |   await test.step('求解', async () => {
  9  |     await expect(solve).toBeEnabled({ timeout: 30_000 });
  10 |     await shot(page, info, 'before-solve');
  11 |     await solve.click();
  12 |     await expect(page.getByText(/本批 \d+ 次运行/)).toBeVisible({ timeout: 150_000 }); // ComparePanel PlanPanels.tsx:845
> 13 |     await expect(page.getByText(/个已验算可行解/)).not.toHaveText(/ 0 个已验算可行解/);
     |                                                 ^ Error: expect(locator).not.toHaveText(expected) failed
  14 |     await shot(page, info, 'solved');
  15 |   });
  16 |   await test.step('打开比较/运行记录', async () => {
  17 |     await page.goto('/#/runs');
  18 |     await expect(page.getByText(/显示 \d+ \/ 最近 \d+ 次/)).toBeVisible({ timeout: 30_000 }); // lab/views/Runs.tsx
  19 |     await shot(page, info, 'compare');
  20 |   });
  21 | });
  22 | 
```