import { test, expect, shot, listScenarios, API } from './helpers';
import type { Page } from '@playwright/test';
// Mamba: "0 个已验算可行解" can be correct (e.g. cvrp-depot-floor runs fail map_check.collision_free). Assert the summary
// count is consistent with the table (check column 通过, PlanPanels.tsx:855,914) once no row is 排队中/计算中.
test('G 真实小规模求解并打开比较', async ({ page }, info) => {
  const all = await listScenarios(page);
  const sc = all.find((s) => s.id === 'bench-cvrp-uniform-n20') ?? all.find((s) => (s as any).problem_class === 'euclidean_cvrp');
  test.skip(!sc, 'no scenarios');
  await page.goto(`/#/plan/${encodeURIComponent(sc!.id)}`);
  const solve = page.getByRole('button', { name: /^对比 \d+ 个算法$/ });
  const summary = page.getByText(/本批 \d+ 次运行 · \d+ 个已验算可行解/);
  await test.step('求解', async () => {
    await expect(solve).toBeEnabled({ timeout: 30_000 });
    await shot(page, info, 'before-solve');
    await solve.click();
    await expect(summary).toBeVisible({ timeout: 150_000 });
    // wait until the batch settles: status bar 求解空闲 (Studio.tsx:432) and no 排队中/计算中 cell (run8 v1 counted too early)
    // (v2 rerun showed 求解空闲 matched before the batch registered → wait for the batch to appear first, then settle)
    const pending = page.locator('td').filter({ hasText: /排队中|计算中/ });
    await expect(page.getByText(/^求解 \d+$/).or(pending.first())).toBeVisible({ timeout: 30_000 }).catch(() => {});
    await expect(pending).toHaveCount(0, { timeout: 150_000 });
    await expect(page.getByText('求解空闲', { exact: true })).toBeVisible({ timeout: 30_000 });
    await expect(summary).toBeVisible();
    const m = (await summary.innerText()).match(/本批 (\d+) 次运行 · (\d+) 个已验算可行解/)!;
    const passed = await page.locator('tbody tr').filter({ has: page.locator('td', { hasText: /^\s*通过\s*$/ }) }).filter({ hasNot: page.locator('td', { hasText: /检查未通过|待检查/ }) }).count() /* 检查 column (PlanPanels.tsx:914) only reflects r.check; map_check failure shows in 状态 as 检查未通过 (comparison.ts:91) */;
    info.annotations.push({ type: 'solve-summary', description: `${m[0]}; table rows with 通过=${passed}; scenario=${sc!.id}` });
    await shot(page, info, 'solved');
    expect(Number(m[2]), 'map_check-clean scenario yields verified-feasible solutions').toBeGreaterThan(0);
    const verify = page.locator('tr[data-run] td[data-verify]'); // Mamba 4567d161
    await expect(verify).toHaveCount(Number(m[1]));
    for (let i = 0; i < Number(m[1]); i++) { await expect(verify.nth(i)).toHaveAttribute('data-verify', 'pass'); await expect(verify.nth(i)).toContainText('通过'); }
    expect(Number(m[2]), 'summary verified count == rows with check 通过').toBe(passed);
  });
});

async function solveAndSettle(page: Page) {
  const solve = page.getByRole('button', { name: /^对比 \d+ 个算法$/ });
  const summary = page.getByText(/本批 \d+ 次运行 · \d+ 个已验算可行解/);
  await expect(solve).toBeEnabled({ timeout: 30_000 });
  await solve.click();
  await expect(summary).toBeVisible({ timeout: 150_000 });
  const pending = page.locator('td').filter({ hasText: /排队中|计算中/ });
  await expect(page.getByText(/^求解 \d+$/).or(pending.first())).toBeVisible({ timeout: 30_000 }).catch(() => {});
  await expect(pending).toHaveCount(0, { timeout: 150_000 });
  await expect(page.getByText('求解空闲', { exact: true })).toBeVisible({ timeout: 30_000 });
  const m = (await summary.innerText()).match(/本批 (\d+) 次运行 · (\d+) 个已验算可行解/)!;
  return { runs: Number(m[1]), verified: Number(m[2]), passed: await page.locator('tbody tr').filter({ has: page.locator('td', { hasText: /^\s*通过\s*$/ }) }).filter({ hasNot: page.locator('td', { hasText: /检查未通过|待检查/ }) }).count() /* 检查 column (PlanPanels.tsx:914) only reflects r.check; map_check failure shows in 状态 as 检查未通过 (comparison.ts:91) */ };
}
// Mamba: on cvrp-depot-floor every run fails map_check.collision_free (straight segments cross map pillars) → 0 verified is
// correct. Collision report (Mamba 04f4e381, MapExclusionNote.tsx) is enforced from a74d5479 on.
test('G2 cvrp-depot-floor：0 个已验算可行解为预期，并显示碰撞报告', async ({ page }, info) => {
  await page.goto('/#/plan/cvrp-depot-floor');
  const t0 = new Date().toISOString();
  const r = await solveAndSettle(page);
  await shot(page, info, 'solved-floor');
  info.annotations.push({ type: 'solve-summary', description: `本批 ${r.runs} 次运行 · ${r.verified} 个已验算可行解; 通过=${r.passed}` });
  expect(r.verified, '0 verified-feasible expected on cvrp-depot-floor').toBe(0);
  expect(r.passed).toBe(0);
  const runs = ((await (await page.request.get(`${API}/runs?limit=200`)).json()).runs as any[])
    .filter((x) => x.scenario_id === 'cvrp-depot-floor' && (x.created_utc ?? '') >= t0);
  info.annotations.push({ type: 'map_check', description: JSON.stringify(runs.map((x) => ({ id: x.run_id, state: x.state, check: x.check?.valid, map_check: x.map_check }))).slice(0, 2000) });
  expect(runs.length, 'API has the new runs').toBeGreaterThan(0);
  for (const x of runs) expect(x.map_check?.collision_free, `${x.run_id} map_check.collision_free`).toBe(false);
  await test.step('验算：地图净空未通过', async () => {
    await page.getByRole('tab', { name: '验算' }).click();
    await expect(page.locator('li[data-bad]', { hasText: '地图净空' }).first()).toBeVisible({ timeout: 10_000 }); // PlanPanels.tsx:1062
    await shot(page, info, 'verify-tab');
  });
  await test.step('碰撞报告（Mamba 04f4e381 selectors；未构建时 pending）', async () => {
    await page.getByRole('tab', { name: '方案对比' }).click();
    const summaryBox = page.locator('[data-exclusion-summary="map_check"]');
    await expect(summaryBox, 'Mamba 04f4e381 map_check summary (PlanPanels.tsx:860)').toBeVisible({ timeout: 10_000 });
    // scoped to the summary: the same note also renders in RunTrace (本运行) and in the excluded list (碰撞明细) — 10 page-wide in run10-4110
    const excl = summaryBox.locator('[data-exclusion="map_collision"]');
    await expect(excl).toHaveCount(r.runs);
    const ids = new Set<string>();
    const full = new Set(runs.map((x) => x.run_id));
    for (let i = 0; i < r.runs; i++) {
      const id = (await excl.nth(i).getAttribute('data-run-id')) ?? '';
      expect(full.has(id), `data-run-id ${id} is a full run_id of this batch`).toBe(true);
      ids.add(id);
      await expect(excl.nth(i)).toContainText(id); // full id shown (4567d161)
      await expect(excl.nth(i)).toHaveAttribute('data-violation-count', /^[1-9]\d*$/);
    }
    expect(ids.size, 'collision notes have distinct run ids').toBe(r.runs);
    const verify = page.locator('tr[data-run] td[data-verify]');
    await expect(verify).toHaveCount(r.runs);
    for (let i = 0; i < r.runs; i++) { await expect(verify.nth(i)).toHaveAttribute('data-verify', 'map_collision'); await expect(verify.nth(i)).toContainText(/未通过（地图碰撞 \d+ 处）/); }
    const v = summaryBox.locator('li[data-map-violation="true"]');
    await expect(v.first()).toBeVisible();
    await expect(v.first()).toHaveAttribute('data-route', /.+/);
    await expect(v.first()).toHaveAttribute('data-segment', /.+/);
    await expect(page.getByText(/本批 \d+ 次运行 · 0 个已验算可行解/)).toBeVisible();
    info.annotations.push({ type: 'collision-note', description: (await summaryBox.innerText()).slice(0, 1500) });
    info.annotations.push({ type: 'violations', description: JSON.stringify(await v.evaluateAll((els) => els.map((e) => ({ route: e.getAttribute('data-route'), segment: e.getAttribute('data-segment'), text: e.textContent })))).slice(0, 1500) });
    await shot(page, info, 'collision-report');
  });
});
