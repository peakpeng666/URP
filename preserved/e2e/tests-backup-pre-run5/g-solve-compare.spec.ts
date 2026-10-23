import { test, expect, shot, listScenarios } from './helpers';
test('G 真实小规模求解并打开比较', async ({ page }, info) => {
  const sc = (await listScenarios(page)).find((s) => /cvrp/i.test((s as any).problem_class ?? s.id)) ?? (await listScenarios(page))[0];
  test.skip(!sc, 'no scenarios');
  await page.goto(`/#/plan/${encodeURIComponent(sc.id)}`);
  const solve = page.getByRole('button', { name: '求解并验算' }); // PlanView.tsx:66
  await test.step('求解', async () => {
    await expect(solve).toBeEnabled({ timeout: 30_000 });
    await shot(page, info, 'before-solve');
    await solve.click();
    await expect(page.getByText('正在求解…')).toBeHidden({ timeout: 150_000 }); // PlanView.tsx:72
    await shot(page, info, 'solved');
  });
  await test.step('打开比较/运行记录', async () => {
    await page.goto('/#/runs');
    await page.waitForLoadState('networkidle');
    await shot(page, info, 'compare');
  });
});
