import { test, expect, shot, openAgriCatalog, firstRunnablePattern, listScenarios, API } from './helpers';
// catalog.ts:39-100 dedupes only in-flight imports in memory; a lost response + retry may duplicate on baseline.
test('D 导入幂等：丢失响应后重新导入，场景列表无重复', async ({ page }, info) => {
  const baseline = await listScenarios(page);
  await openAgriCatalog(page);
  const { card, name } = await firstRunnablePattern(page);
  await card.getByLabel(`${name} 随机种子`).fill('9091');
  await test.step('首次导入：服务端处理后丢弃响应', async () => {
    await page.route(`**${API}/scenarios`, async (route) => {
      if (route.request().method() !== 'POST') return route.fallback();
      await route.fetch(); // server commits
      await route.abort('connectionreset'); // client never sees it
    }, { times: 1 });
    await card.getByRole('button', { name: '校验并导入任务规划' }).click();
    await expect(card.getByRole('alert').first()).toBeVisible // nested alerts: AgriCatalog.tsx:171 + Notice role=alert({ timeout: 30_000 });
    await shot(page, info, 'lost-response');
  });
  await test.step('重新导入同一参数', async () => {
    await card.getByRole('button', { name: '校验并导入任务规划' }).click();
    await expect(page).toHaveURL(/#\/plan\/.+/, { timeout: 60_000 });
    await shot(page, info, 'reimported');
  });
  await test.step('查询场景列表并断言无重复', async () => {
    const after = await listScenarios(page);
    const added = after.filter((s) => !baseline.some((b) => b.id === s.id));
    const titles = added.map((s) => s.title);
    info.annotations.push({ type: 'added', description: JSON.stringify(titles) });
    expect(added.length, `new scenarios: ${titles.join(', ')}`).toBe(1);
  });
});
