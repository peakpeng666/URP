import { test, expect } from '@playwright/test';
import fs from 'fs';
const ART = process.env.ART || 'artifacts/run'; fs.mkdirSync(ART + '/shots', { recursive: true });
const SC = 'agri-orchard-harvest-tran-5b1b69a6-8206-4f72-b6ae-89b5a0c6e4bd';
test('history runs', async ({ page }) => { test.setTimeout(120000);
  await page.goto('/#/plan/' + SC); await page.waitForTimeout(2500);
  await page.getByRole('tab', { name: /方案对比/ }).first().click().catch(async () => page.getByText('方案对比').first().click());
  await page.waitForTimeout(800);
  await page.getByText(/历史运行（本场景/).first().click(); await page.waitForTimeout(1500);
  await page.screenshot({ path: ART + '/shots/history-list.png', fullPage: true });
  const body = await page.locator('body').innerText();
  for (const id of ['run_e2e_quarantined_unverified', 'run_e2e_legacy_noidentity']) test.info().annotations.push({ type: 'listed ' + id, description: String(body.includes(id)) });
  for (const id of ['run_e2e_quarantined_unverified', 'run_e2e_legacy_noidentity']) {
    const row = page.locator('tr, li').filter({ hasText: id }).first();
    await row.getByRole('button', { name: /加入比较/ }).click(); await page.waitForTimeout(800);
  }
  await page.screenshot({ path: ART + '/shots/history-added.png', fullPage: true });
  const trs = page.locator('tr[data-run="run_e2e_quarantined_unverified"]'); test.info().annotations.push({ type: 'tr count', description: String(await trs.count()) }); for (let i = 0; i < await trs.count(); i++) { await trs.nth(i).click(); await page.waitForTimeout(600); if (await page.locator('[data-selected-run="run_e2e_quarantined_unverified"]').count()) { test.info().annotations.push({ type: 'selected via', description: String(i) }); break; } }
  const sel = page.locator('[data-selected-run="run_e2e_quarantined_unverified"]');
  test.info().annotations.push({ type: 'selected banner', description: String((await sel.count()) > 0 && /已隔离/.test(await sel.first().innerText())) });
  const ov = await page.evaluate(() => [...document.querySelectorAll('*')].filter(e => e.scrollWidth > e.clientWidth + 2 && getComputedStyle(e).overflowX === 'visible' && e.clientWidth > 200).length);
  test.info().annotations.push({ type: 'overflow-visible elements', description: String(ov) });
  await page.screenshot({ path: ART + '/shots/history-selected.png', fullPage: true });
  const b2 = await page.locator('body').innerText();
  for (const t of ['已隔离 · 不适用', '未参与比较与排名', '身份未核验']) test.info().annotations.push({ type: t, description: String(b2.includes(t)) });
  await page.getByText('实验结果', { exact: true }).first().click();
  await page.waitForTimeout(1200);
  await page.screenshot({ path: ART + '/shots/history-result.png', fullPage: true });
  const b3 = await page.locator('body').innerText();
  test.info().annotations.push({ type: 'result tab has 隔离', description: String(/已隔离：/.test(b3)) });
  console.log(JSON.stringify(test.info().annotations));
});
