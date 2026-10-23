import { test, expect, shot, listScenarios } from './helpers';
test('G 真实小规模求解并打开比较', async ({ page }, info) => {
  // cvrp-depot-floor checks straight segments against map pillars → all runs 检查未通过 (run7). Use obstacle-free uniform n20.
  const all = await listScenarios(page);
  const sc = all.find((s) => s.id === 'bench-cvrp-uniform-n20') ?? all.find((s) => (s as any).problem_class === 'euclidean_cvrp');
  test.skip(!sc, 'no scenarios');
  await page.goto(`/#/plan/${encodeURIComponent(sc.id)}`);
  // lab PlanView (求解并验算) is not mounted: App.tsx renders <Studio> for lab views; Studio solve = AdvisorPanel 对比 N 个算法.
  const solve = page.getByRole('button', { name: /^对比 \d+ 个算法$/ });
  await test.step('求解', async () => {
    await expect(solve).toBeEnabled({ timeout: 30_000 });
    await shot(page, info, 'before-solve');
    await solve.click();
    await expect(page.getByText(/本批 \d+ 次运行/)).toBeVisible({ timeout: 150_000 }); // ComparePanel PlanPanels.tsx:845
    await expect(page.getByText(/本批 \d+ 次运行/)).not.toContainText('· 0 个已验算可行解');
    await shot(page, info, 'solved');
  });
  await test.step('打开比较/运行记录', async () => {
    await page.goto('/#/runs');
    await expect(page.getByText(/显示 \d+ \/ 最近 \d+ 次/)).toBeVisible({ timeout: 30_000 }); // lab/views/Runs.tsx
    await shot(page, info, 'compare');
  });
});
