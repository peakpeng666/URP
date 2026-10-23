import { test } from '@playwright/test';
const ART = process.env.ART; const S = process.env.FIX_SCENARIO;
test('mamba tabs', async ({ page }) => {
  const errs = []; page.on('console', (m) => m.type() === 'error' && errs.push(m.text().slice(0, 200)));
  await page.goto('/#/plan/' + encodeURIComponent(S)); await page.waitForTimeout(3000);
  for (const tab of ['实验结果', '方案对比', '仿真回放']) {
    const t = page.getByText(tab, { exact: true }).first(); if (!(await t.count())) continue;
    await t.click(); await page.waitForTimeout(1500);
    await page.screenshot({ path: `${ART}/shots/mamba-tab-${tab}.png`, fullPage: true });
    const tx = await page.locator('body').innerText();
    test.info().annotations.push({ type: tab, description: ['已隔离', '源码身份不符', '身份未核验', '不参与', '未纳入', '排名', '种子', '哈希', 'sha256', '版本', 'run_e2e'].map((k) => k + ':' + (tx.split(k).length - 1)).join(' ') });
    const lines = tx.split('\n').filter((l) => /隔离|身份|未纳入|不参与|排名/.test(l)).slice(0, 8);
    test.info().annotations.push({ type: tab + ' lines', description: lines.join(' || ').slice(0, 700) });
  }
  // select seeded runs on 实验结果 rows
  for (const rid of ['run_e2e_quarantined_unverified', 'run_e2e_legacy_noidentity']) {
    const row = page.getByText(rid).first();
    if (await row.count()) { await row.click().catch(() => {}); await page.waitForTimeout(1500); await page.screenshot({ path: `${ART}/shots/mamba-${rid}.png`, fullPage: true });
      const tx = await page.locator('body').innerText(); test.info().annotations.push({ type: 'select ' + rid, description: tx.split('\n').filter((l) => /隔离|身份/.test(l)).slice(0, 5).join(' || ') }); }
    else test.info().annotations.push({ type: 'select ' + rid, description: 'row not visible' });
  }
  test.info().annotations.push({ type: 'errors', description: errs.join(' | ') });
});
