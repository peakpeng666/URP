import { test, expect, shot, listScenarios, API, openInspectorTab } from './helpers';
// Fork endpoint: POST /lab/api/scenarios/:id/fork (src/studio/api.ts:101-102); auto-fork on first edit of a
// built-in scenario saves as “我的场景” (src/studio/store.ts:398,428).
test('E Fork 超时重试：只生成一份“我的场景”', async ({ page }, info) => {
  const before = await listScenarios(page);
  // No built-in fleet_routing scenarios exist; built-in euclidean_cvrp uses GenericMap + TaskEditor (车辆容量).
  const builtin = before.find((s) => s.origin === 'builtin' && (s as any).problem_class === 'euclidean_cvrp');
  test.skip(!builtin, 'no built-in scenario');
  let forkCalls = 0;
  await page.route(`**${API}/scenarios/*/fork`, async (route) => {
    forkCalls++;
    const res = await route.fetch();
    await new Promise((r) => setTimeout(r, 45_000)); // beyond client timeout (uncertain exact value)
    await route.fulfill({ response: res }).catch(() => {});
  });
  await page.goto(`/#/plan/${encodeURIComponent(builtin.id)}`);
  await test.step('编辑内置场景触发自动另存', async () => {
    await openInspectorTab(page);
    const cap = page.getByLabel('车辆容量'); // lab/views/plan/TaskEditor.tsx:19
    await expect(cap).toBeVisible({ timeout: 30_000 });
    await cap.fill(String(Number(await cap.inputValue()) + 1));
    await cap.blur();
    await shot(page, info, 'edited-builtin');
    await expect.poll(() => forkCalls, { timeout: 20_000 }).toBeGreaterThan(0);
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
