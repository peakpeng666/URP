import { test, expect, shot, API } from './helpers';
// Uses the real labdata test records (no stubs): run_e2e_quarantined_unverified (source_identity_verified=false)
// and run_e2e_legacy_noidentity (no identity fields), both in an OLDER job of their scenario.
// Studio's ComparePanel only shows the latest job (studio/store.ts:169-173 → "本批 1 次运行"); the only historical
// entry is #/runs (lab/views/Runs.tsx), whose "查看" link is #/plan/<sid>?run=<id>. Studio ignores ?run= (no
// params.get('run') in studio/), and Runs.tsx/Runs.logic.ts have no identity/quarantine handling.
// Expectations below are the spec; soft assertions so every gap is recorded.
const Q = 'run_e2e_quarantined_unverified', L = 'run_e2e_legacy_noidentity';
test('F 结果完整性：隔离未核验来源、缺字段显示未核验、隔离结果不进比较组', async ({ page }, info) => {
  const all = (await (await page.request.get(`${API}/runs?limit=200`)).json()).runs as any[];
  const q = all.find((r) => r.run_id === Q), l = all.find((r) => r.run_id === L);
  test.skip(!q || !l, 'test records missing from labdata');
  expect(q.process.source_identity_verified).toBe(false);
  await page.goto('/#/runs');
  await page.getByText('运行记录', { exact: true }).first().click(); // system workspace: 运行记录 dock tab is inactive
  await expect(page.getByText(/显示 \d+ \/ 最近 \d+ 次/)).toBeVisible({ timeout: 30_000 });
  await test.step('历史入口：运行记录列出两条测试记录', async () => {
    await expect(page.getByText(Q, { exact: true })).toBeVisible();
    await expect(page.getByText(L, { exact: true })).toBeVisible();
    await shot(page, info, 'runs-history');
  });
  await test.step('运行记录中隔离/未核验标识', async () => {
    const qRow = page.locator('tr', { has: page.getByText(Q, { exact: true }) });
    const lRow = page.locator('tr', { has: page.getByText(L, { exact: true }) });
    await expect.soft(qRow.getByText(/隔离/), 'runs list marks quarantined run').toBeVisible({ timeout: 5_000 });
    await expect.soft(lRow.getByText(/未核验/), 'runs list marks legacy run 未核验').toBeVisible({ timeout: 5_000 });
  });
  await test.step('隔离结果不进入比较组', async () => {
    const ok = all.find((r) => r.scenario_id === q.scenario_id && r.job_id === q.job_id && r.run_id !== Q && r.run_id !== L);
    await page.getByLabel(`对比 ${Q}`).check();
    if (ok) await page.getByLabel(`对比 ${ok.run_id}`).check();
    await shot(page, info, 'compare-with-quarantined');
    await expect.soft(page.getByText(/隔离|源码身份不符/).first(), 'compare flags/excludes quarantined run').toBeVisible({ timeout: 5_000 });
  });
  await test.step('查看隔离运行：横幅与原因', async () => {
    await page.goto('/#/runs');
    await page.getByText('运行记录', { exact: true }).first().click();
    await page.locator('tr', { has: page.getByText(Q, { exact: true }) }).getByRole('link', { name: '查看' }).click();
    await expect(page).toHaveURL(new RegExp(`run=${Q}`));
    await page.waitForTimeout(4_000);
    await shot(page, info, 'open-quarantined');
    await expect.soft(page.getByText(/已隔离/).first(), 'quarantine banner after 查看').toBeVisible({ timeout: 15_000 });
  });
  await test.step('查看缺字段运行：显示未核验', async () => {
    await page.goto(`/#/plan/${encodeURIComponent(l.scenario_id)}?run=${L}`);
    await page.waitForTimeout(4_000);
    await shot(page, info, 'open-legacy');
    await expect.soft(page.getByText(/身份未核验/).first(), '未核验 label after 查看').toBeVisible({ timeout: 15_000 });
  });
  // Mamba 0e8339fc history-runs entry (expected after gateway rebuild; fails on 3c0a94e5).
  await test.step('方案对比 → 历史运行（本场景）', async () => {
    const one = await page.request.get(`${API}/runs/${Q}`);
    const sid = one.ok() ? (await one.json()).scenario_id : null;
    if (!sid) {
      await page.goto('/#/runs');
      await page.getByText('运行记录', { exact: true }).first().click();
      await expect(page.locator('tr', { has: page.getByText(Q, { exact: true }) }).getByText(/隔离/)).toBeVisible({ timeout: 15_000 });
      return;
    }
    await page.goto(`/#/plan/${encodeURIComponent(sid)}`);
    await page.getByText('方案对比', { exact: true }).first().click();
    const hist = page.getByRole('button', { name: '历史运行（本场景，含失败/已隔离/身份未核验）' });
    await expect.soft(hist, 'history-runs entry exists').toBeVisible({ timeout: 15_000 });
    if (!(await hist.isVisible())) { await shot(page, info, 'no-history-entry'); return; }
    await hist.click();
    for (const id of [Q, L]) {
      const row = page.getByLabel('历史运行').locator('tr', { hasText: id }).first(); // HistoryRuns.tsx:63,85
      await row.getByRole('button', { name: '加入比较' }).click();
    }
    await shot(page, info, 'history-added');
    const excluded = page.getByLabel('未参与比较的运行') /* PlanPanels.tsx:956, heading 未参与比较与排名 */;
    await expect.soft(excluded.getByText('已隔离 · 不适用')).toBeVisible();
    await expect.soft(excluded.getByText(/\d+\.\d|km|\bm\b/), 'no values for quarantined').toHaveCount(0);
    await expect.soft(page.getByText('身份未核验').first()).toBeVisible();
    await page.getByText('实验结果', { exact: true }).first().click(); // dock tab title (Studio.tsx PANELS.results)
    await shot(page, info, 'result-tab');
    await expect.soft(page.getByText(/已隔离：.+/).first(), 'quarantine banner + reason').toBeVisible({ timeout: 10_000 });
  });
});
