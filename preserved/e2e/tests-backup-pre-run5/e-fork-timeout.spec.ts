import { test, expect, shot, listScenarios, API } from './helpers';
// Fork endpoint: POST /lab/api/scenarios/:id/fork (src/studio/api.ts:101-102); auto-fork on first edit of a
// built-in scenario saves as “我的场景” (src/studio/store.ts:398,428).
test('E Fork 超时重试：只生成一份“我的场景”', async ({ page }, info) => {
  const before = await listScenarios(page);
  const builtin = before.find((s) => s.origin && s.origin !== 'user') ?? before[0];
  test.skip(!builtin, 'no built-in scenario');
  let forkCalls = 0;
  await page.route(`**${API}/scenarios/*/fork`, async (route) => {
    forkCalls++;
    const res = await route.fetch();
    await new Promise((r) => setTimeout(r, 45_000)); // beyond client timeout (uncertain exact value)
    await route.fulfill({ response: res }).catch(() => {});
  });
  await page.goto(`/#/plan/${encodeURIComponent(builtin.id)}`);
  const map = page.locator('svg[aria-label="任务地图编辑器"]');
  await expect(map).toBeVisible({ timeout: 30_000 });
  await test.step('编辑内置场景触发自动另存', async () => {
    const x = page.locator('label', { has: page.locator('span', { hasText: /^X$/ }) }).locator('input[type=number]').first();
    const shape = map.locator('circle').filter({ visible: true }).first();
    if (await shape.count()) await shape.click({ force: true });
    if (await x.count()) await x.fill(String(Number(await x.inputValue()) + 1));
    await shot(page, info, 'edited-builtin');
  });
  await test.step('等待超时与重试', async () => {
    await page.waitForTimeout(60_000);
    const retry = page.getByRole('button', { name: '重试保存' }); // PlanPanels.tsx:179
    if (await retry.isVisible()) { await retry.click(); await page.waitForTimeout(50_000); }
    await shot(page, info, 'after-retry');
  });
  await test.step('断言只有一份副本', async () => {
    const after = await listScenarios(page);
    const copies = after.filter((s) => !before.some((b) => b.id === s.id) && s.origin === 'user');
    info.annotations.push({ type: 'forkCalls', description: String(forkCalls) });
    expect(copies.length).toBe(1);
  });
});
