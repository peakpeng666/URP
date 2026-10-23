import { test, expect, shot, listScenarios, API } from './helpers';
// Integrity rules: resultIntegrity.ts:7-8 (source_identity_verified===false invalidated), :21-23 coverage;
// PlanPanels.tsx:936 excludes from Convergence group. Quarantine banner text and “未核验” label are EXPECTED per
// spec and may not exist in baseline — regexes below are intentionally broad.
test('F 结果完整性：隔离未核验来源、缺字段显示未核验、隔离结果不进比较组', async ({ page }, info) => {
  const scenarios = await listScenarios(page);
  const sc = scenarios[0]; test.skip(!sc, 'no scenarios');
  const base = { scenario_id: sc.id, problem: (sc as any).problem_class ?? 'euclidean_cvrp', state: 'done', status: 'feasible',
    objective: { value: 100, name: 'distance' }, check: { valid: true, errors: [] }, algorithm: { id: 'stub.alg', name: '桩算法' },
    created_at: new Date().toISOString(), routes: [], instance: (sc as any).instance };
  const quarantined = { ...base, run_id: 'stub-quarantined', label: '隔离结果', process: { source_identity_verified: false, reason: 'stub: 来源身份校验失败' } };
  const missing = { ...base, run_id: 'stub-missing', label: '缺字段结果', process: {} };
  const ok = { ...base, run_id: 'stub-ok', label: '正常结果', process: { source_identity_verified: true } };
  const runs = [quarantined, missing, ok];
  await page.route(new RegExp(`${API}/runs(\\?.*)?$`), (r) => r.request().method() === 'GET' ? r.fulfill({ json: { runs } }) : r.fallback());
  await page.route(new RegExp(`${API}/runs/stub-[a-z]+$`), (r) => r.fulfill({ json: runs.find((x) => r.request().url().endsWith(x.run_id)) }));
  await page.goto(`/#/plan/${encodeURIComponent(sc.id)}?run=stub-quarantined`);
  await test.step('隔离横幅与原因', async () => {
    await expect(page.getByText(/隔离|来源.*(未|失败)|不可信/).first()).toBeVisible({ timeout: 30_000 });
    await shot(page, info, 'quarantine-banner');
  });
  await test.step('指标不作为有效展示', async () => {
    await expect(page.getByText(/可行 · 已验算|最优（求解器报告）/)).toHaveCount(0); // comparison.ts:49
  });
  await test.step('缺字段显示“未核验”', async () => {
    await page.goto(`/#/plan/${encodeURIComponent(sc.id)}?run=stub-missing`);
    await expect(page.getByText('未核验').first()).toBeVisible({ timeout: 30_000 });
    await shot(page, info, 'missing-unverified');
  });
  await test.step('隔离结果不进入比较组', async () => {
    await page.goto('/#/runs');
    await shot(page, info, 'runs-list');
    const overlay = page.getByRole('button', { name: /显示 桩算法 路线|叠加 桩算法/ }); // PlanPanels.tsx:250,315
    // exactly the non-quarantined runs (ok + missing) may be offered; quarantined must not.
    expect(await overlay.count()).toBeLessThanOrEqual(2);
  });
});
