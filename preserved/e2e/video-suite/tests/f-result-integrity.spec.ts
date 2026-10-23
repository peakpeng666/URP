import { test, expect, shot, API } from './helpers';
// Uses the real labdata test records (no stubs): run_e2e_quarantined_unverified (source_identity_verified=false)
// and run_e2e_legacy_noidentity (no identity fields). Entry: 方案对比 → HistoryRuns.tsx → 加入比较; excluded list PlanPanels.tsx:955. Selectors per Mamba 4567d161 (data-run, data-verify, data-selected-run).
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
  const hist2 = page.getByLabel('历史运行');
  // compare-table row (Mamba 4567d161: tr[data-run], verify cell td[data-verify]); history rows also carry data-run.
  const qRow = page.locator(`tr[data-run="${Q}"]`).filter({ has: page.locator('td[data-verify]') });
  await test.step('各处文字：历史资格列 / 验算列 / 未参与比较', async () => {
    await expect(hist2.locator(`tr[data-run="${Q}"]`)).toContainText('不参与排名：源码身份不符 · 已隔离');
    await expect(qRow.locator('td[data-verify="quarantined"]')).toContainText('已隔离 · 不适用');
    const qi = page.locator('li[data-exclusion="quarantined"]', { hasText: Q });
    await expect(qi).toHaveCount(1);
    await expect(qi).toContainText(Q); // full run_id
    await expect(qi).toContainText('源码身份不符 · 已隔离');
    await expect(qi.getByText(/\d+\.\d|km|\bm\b/)).toHaveCount(0); // no values for quarantined
    await shot(page, info, 'excluded');
  });
  await test.step('布局：历史表与右侧列不重叠', async () => {
    const a = (await hist2.locator('table').boundingBox())!;
    const b = (await qRow.locator('xpath=ancestor::table[1]').boundingBox())!;
    info.annotations.push({ type: 'layout', description: JSON.stringify({ history: a, compare: b }) });
    const overlap = a.x < b.x + b.width && b.x < a.x + a.width && a.y < b.y + b.height && b.y < a.y + a.height;
    expect(overlap, 'history table and right-column compare table bounding boxes intersect').toBe(false);
    // history table scrolls horizontally inside its own column: nearest overflow-x scroller is narrower than the table
    // and ends left of the right column.
    const sc = await hist2.locator('table').evaluate((t) => {
      let e: HTMLElement | null = t.parentElement;
      while (e && !(/(auto|scroll)/.test(getComputedStyle(e).overflowX) && e.scrollWidth > e.clientWidth)) e = e.parentElement;
      if (!e) return null; const r = e.getBoundingClientRect();
      return { left: r.left, right: r.right, scrollWidth: e.scrollWidth, clientWidth: e.clientWidth };
    });
    info.annotations.push({ type: 'history-scroller', description: JSON.stringify(sc) });
    expect(sc, 'history table has a horizontal scroll container').not.toBeNull();
    expect(sc!.right, 'scroller ends before right column').toBeLessThanOrEqual(b.x);
    await hist2.locator('table').scrollIntoViewIfNeeded();
    await shot(page, info, 'history-layout');
  });
  await test.step('缺字段运行：身份未核验，单独分组', async () => {
    await expect(page.locator(`tr[data-run="${L}"]`).filter({ has: page.locator('td[data-verify]') })).toContainText('身份未核验');
    await expect(page.getByText(/种比较口径（含身份未核验组）/)).toBeVisible();
    await shot(page, info, 'unverified-group');
  });
  await test.step('选中隔离运行 → 选中方案横幅 + 实验结果横幅', async () => {
    await qRow.locator('td').first().click();
    const sel = page.locator(`[data-selected-run="${Q}"]`);
    await expect(sel).toBeVisible({ timeout: 10_000 });
    await expect(sel.getByText(/已隔离：.+/).first()).toBeVisible();
    await shot(page, info, 'selected-banner');
    await page.getByRole('tab', { name: '实验结果' }).click();
    await expect(page.getByRole('tabpanel', { name: '实验结果' }).getByText(/已隔离：.+/).first()).toBeVisible({ timeout: 10_000 });
    await shot(page, info, 'result-tab');
  });
});
