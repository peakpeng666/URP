import { test, expect, shot, API } from './helpers';
// Uses the real labdata test records (no stubs): run_e2e_quarantined_unverified (source_identity_verified=false)
// and run_e2e_legacy_noidentity (no identity fields). Entry: 方案对比 → HistoryRuns.tsx → 加入比较; excluded list PlanPanels.tsx:955.
const Q = 'run_e2e_quarantined_unverified', L = 'run_e2e_legacy_noidentity';
test('F 结果完整性：隔离未核验来源、缺字段显示未核验、隔离结果不进比较组', async ({ page }, info) => {
  // #/runs no longer has the "显示 N / 最近 N 次" table in the Studio shell; history entry is 方案对比 → HistoryRuns.tsx.
  const one = await page.request.get(`${API}/runs/${Q}`);
  test.skip(!one.ok(), 'test record missing from labdata');
  const q = await one.json();
  expect(q.process.source_identity_verified).toBe(false);
  await page.goto(`/#/plan/${encodeURIComponent(q.scenario_id)}`);
  await page.getByText('方案对比', { exact: true }).first().click();
  const hist = page.getByRole('button', { name: '历史运行（本场景，含失败/已隔离/身份未核验）' });
  await expect(hist).toBeVisible({ timeout: 30_000 });
  await hist.click();
  await test.step('加入比较：隔离 + 缺字段', async () => {
    for (const id of [Q, L]) {
      const row = page.getByLabel('历史运行').locator('tr', { hasText: id }).first();
      await expect(row).toBeVisible({ timeout: 15_000 });
      await row.getByRole('button', { name: '加入比较' }).click();
    }
    await shot(page, info, 'history-added');
  });
  await test.step('隔离运行在「未参与比较与排名」，无数值', async () => {
    const excluded = page.getByLabel('未参与比较的运行');
    const qi = excluded.locator('li').filter({ hasText: '已隔离' }).first();
    await expect(qi).toHaveAttribute('data-exclusion', 'quarantined');
    // Spec text「已隔离 · 不适用」: source emits it only in the table check column (PlanPanels.tsx:914); excluded <li> shows
    // `${name} · ${id.slice(0,8)} · ${resultState} · ${reason}` (PlanPanels.tsx:958). Kept as soft so the mismatch is recorded.
    await expect.soft(qi, 'excluded entry says 已隔离 · 不适用').toContainText('已隔离 · 不适用');
    await expect(qi.getByText(/\d+\.\d|km|\bm\b/)).toHaveCount(0);
    // the quarantined run is still a table row with 比较 check column「已隔离 · 不适用」(PlanPanels.tsx:914)
    await expect(page.locator('tbody tr', { has: page.locator('td', { hasText: /^已隔离 · 不适用$/ }) })).toHaveCount(1);
    await shot(page, info, 'excluded');
  });
  await test.step('缺字段运行：身份未核验，单独分组', async () => {
    await expect(page.getByText('身份未核验', { exact: true }).first()).toBeVisible();
    await expect(page.getByText(/种比较口径（含身份未核验组）/)).toBeVisible();
    await shot(page, info, 'unverified-group');
  });
  await test.step('结果：隔离横幅 + 原因', async () => {
    // ExperimentPanel shows the focused run: click the quarantined row's first cell to focus it, then open 实验结果.
    await page.locator('tbody tr', { has: page.locator('td', { hasText: /^已隔离 · 不适用$/ }) }).locator('td').first().click();
    await page.getByRole('tab', { name: '实验结果' }).click();
    await expect(page.getByText(/已隔离：.+/).first()).toBeVisible({ timeout: 10_000 });
    await shot(page, info, 'result-tab');
  });
});
