# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: b-draft-persistence.spec.ts >> B 草稿持久化：编辑参数后刷新页面，草稿应恢复（基线预期失败）
- Location: tests/b-draft-persistence.spec.ts:4:1

# Error details

```
Error: expect(locator).toHaveValue(expected) failed

Locator:  getByRole('region', { name: '农业任务目录' }).locator('details').filter({ has: locator('summary').filter({ hasText: '果园采收集运' }) }).first().getByLabel('果园采收集运 随机种子')
Expected: "12345"
Received: "42"
Timeout:  5000ms

Call log:
  - Expect "toHaveValue" getByRole('region', { name: '农业任务目录' }).locator('details').filter({ has: locator('summary').filter({ hasText: '果园采收集运' }) }).first().getByLabel('果园采收集运 随机种子') with timeout 5000ms
  - waiting for getByRole('region', { name: '农业任务目录' }).locator('details').filter({ has: locator('summary').filter({ hasText: '果园采收集运' }) }).first().getByLabel('果园采收集运 随机种子')
    14 × locator resolved to <input min="0" step="1" value="42" type="number" max="4294967295" aria-label="果园采收集运 随机种子" class="_input_a5ga1_358"/>
       - unexpected value "42"

```

```yaml
- spinbutton "果园采收集运 随机种子": "42"
```

# Test source

```ts
  1  | import { test, expect, shot, openAgriCatalog, firstRunnablePattern } from './helpers';
  2  | // Expected to FAIL on baseline b3e2028: PatternCard keeps values/seed in React useState only
  3  | // (AgriCatalog.tsx:43-44), nothing persists across reload. Not marked test.fail(): outcome is just recorded.
  4  | test('B 草稿持久化：编辑参数后刷新页面，草稿应恢复（基线预期失败）', async ({ page }, info) => {
  5  |   await openAgriCatalog(page);
  6  |   const { card, name } = await firstRunnablePattern(page);
  7  |   await test.step('编辑参数与种子', async () => {
  8  |     await card.getByLabel(`${name} 随机种子`).fill('12345');
  9  |     await shot(page, info, 'edited');
  10 |   });
  11 |   await test.step('刷新页面', async () => { await page.reload(); });
  12 |   await test.step('验证草稿恢复', async () => {
  13 |     const again = await openAgriCatalog(page);
  14 |     const c = again.locator('details').filter({ has: page.locator('summary', { hasText: name }) }).first();
  15 |     await c.locator('summary').click();
  16 |     await shot(page, info, 'after-reload');
> 17 |     await expect(c.getByLabel(`${name} 随机种子`)).toHaveValue('12345');
     |                                                ^ Error: expect(locator).toHaveValue(expected) failed
  18 |   });
  19 | });
  20 | 
```