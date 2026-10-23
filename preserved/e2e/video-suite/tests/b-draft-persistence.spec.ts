import { test, expect, shot, openAgriCatalog, firstRunnablePattern } from './helpers';
// Expected to FAIL on baseline b3e2028: PatternCard keeps values/seed in React useState only
// (AgriCatalog.tsx:43-44), nothing persists across reload. Not marked test.fail(): outcome is just recorded.
test('B 草稿持久化：编辑参数后刷新页面，草稿应恢复（基线预期失败）', async ({ page }, info) => {
  await openAgriCatalog(page);
  const { card, name } = await firstRunnablePattern(page);
  await test.step('编辑参数与种子', async () => {
    await card.getByLabel(`${name} 随机种子`).fill('12345');
    await shot(page, info, 'edited');
  });
  await test.step('刷新页面', async () => { await page.waitForTimeout(800); await page.reload(); });
  await test.step('验证草稿恢复', async () => {
    const again = await openAgriCatalog(page);
    const c = again.locator('details').filter({ has: page.locator('summary', { hasText: name }) }).first();
    await c.locator('summary').click();
    await shot(page, info, 'after-reload');
    await expect(c.getByLabel(`${name} 随机种子`)).toHaveValue('12345');
  });
});
