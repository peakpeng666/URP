import { test, expect } from '@playwright/test';
import fs from 'node:fs';
const ART = process.env.ART || 'artifacts/run';
const shots = ART + '/shots'; fs.mkdirSync(shots, { recursive: true });
const log = {};
function watch(page, key) {
  const r = log[key] = { console: [], failed: [], http: [] };
  page.on('console', (m) => { if (m.type() === 'error') r.console.push(m.text().slice(0, 300)); });
  page.on('pageerror', (e) => r.console.push('pageerror: ' + e.message.slice(0, 300)));
  page.on('requestfailed', (q) => r.failed.push(q.method() + ' ' + q.url() + ' ' + q.failure()?.errorText));
  page.on('response', (s) => { if (s.status() >= 400) r.http.push(s.status() + ' ' + s.request().method() + ' ' + s.url()); });
  return r;
}
test.afterAll(() => fs.writeFileSync(ART + '/errors.json', JSON.stringify(log, null, 2)));
for (const [name, hash] of [['home', '#/'], ['plan', '#/plan'], ['assets', '#/assets'], ['sim', '#/sim'], ['jobs', '#/jobs'], ['bpp', '#/bpp']]) {
  test('route ' + name, async ({ page }) => {
    const r = watch(page, name);
    await page.goto('/' + hash); await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    await page.waitForTimeout(1500);
    await page.screenshot({ path: `${shots}/${name}.png`, fullPage: true });
    expect(r.console.filter((t) => t.startsWith('pageerror')), 'uncaught page errors').toEqual([]);
  });
}
async function openCatalog(page) {
  await page.goto('/#/'); await page.reload(); await page.getByRole('button', { name: '打开农业任务目录' }).click();
  await page.locator('details').first().waitFor();
}
const cardWith = (page, suffix) => page.locator('details').filter({ has: page.locator(`input[aria-label$=" ${suffix}"]`) }).first();
test('agri catalog + flow', async ({ page }) => { test.setTimeout(240000);
  const r = watch(page, 'agri');
  await openCatalog(page); await page.screenshot({ path: `${shots}/agri-catalog.png`, fullPage: true });
  const card = cardWith(page, '任务点数'); await card.evaluate(d => { d.open = true; });
  await card.screenshot({ path: `${shots}/agri-card-open.png` });
  const preview = card.getByRole('img', { name: /几何预览/ });
  const hasPreview = await preview.count();
  test.info().annotations.push({ type: 'preview', description: String(hasPreview) });
  if (hasPreview) {
    await expect(preview).toContainText('原点 (0,0)'); await expect(preview).toContainText(/\d+ m/);
    await expect(card.getByRole('group', { name: '图层' }).locator('input[type=checkbox]')).toHaveCount(5);
    await expect(card.locator('figcaption')).toContainText('图例');
    await card.getByRole('group', { name: '图层' }).getByLabel('服务对象').uncheck();
    await card.screenshot({ path: `${shots}/agri-preview-layer-off.png` });
    await card.getByRole('group', { name: '图层' }).getByLabel('服务对象').check();
  }
  // draft
  const nm = (await card.locator('input[aria-label$=" 任务点数"]').getAttribute('aria-label')).replace(/ 任务点数$/, '');
  await card.locator('input[aria-label$=" 任务点数"]').fill('7');
  await card.locator('input[aria-label$=" 随机种子"]').fill('123');
  await page.waitForTimeout(800);
  await page.reload(); await page.goto('/#/plan'); await page.waitForTimeout(500);
  await openCatalog(page);
  const c2 = page.locator('details').filter({ has: page.locator(`input[aria-label="${nm} 任务点数"]`) }).first();
  await c2.evaluate(d => { d.open = true; });
  const restoredN = await c2.locator(`input[aria-label="${nm} 任务点数"]`).inputValue();
  const restoredSeed = await c2.locator(`input[aria-label="${nm} 随机种子"]`).inputValue();
  test.info().annotations.push({ type: 'draft-restored', description: `${restoredN}/${restoredSeed}` });
  await c2.screenshot({ path: `${shots}/agri-draft-restored.png` });
  const reset = c2.getByRole('button', { name: '清除草稿并恢复默认' });
  if (await reset.count()) {
    await reset.click();
    test.info().annotations.push({ type: 'after-reset', description: `${await c2.locator(`input[aria-label="${nm} 任务点数"]`).inputValue()}/${await c2.locator(`input[aria-label="${nm} 随机种子"]`).inputValue()}` });
    await c2.screenshot({ path: `${shots}/agri-draft-reset.png` });
  }
  // import + solve
  await c2.getByRole('button', { name: '校验并导入任务规划', exact: true }).click();
  await page.waitForURL((u) => u.hash.startsWith('#/plan/agri-'), { timeout: 20000 });
  const id = decodeURIComponent(new URL(page.url()).hash.slice('#/plan/'.length));
  await page.waitForTimeout(2000); await page.screenshot({ path: `${shots}/agri-imported-plan.png`, fullPage: true });
  const solve = page.getByRole('button', { name: /求解|运行/ }).first();
  test.info().annotations.push({ type: 'scenario', description: id });
  if (await solve.count()) {
    await solve.click(); await page.waitForTimeout(15000);
    await page.screenshot({ path: `${shots}/agri-after-solve.png`, fullPage: true });
  } else test.info().annotations.push({ type: 'solve', description: 'no solve button found' });
  // last-import link
  await openCatalog(page);
  const c3 = page.locator('details').filter({ has: page.locator(`input[aria-label="${nm} 任务点数"]`) }).first();
  await c3.evaluate(d => { d.open = true; });
  const notice = c3.getByText(/上次导入为/);
  test.info().annotations.push({ type: 'last-import-notice', description: String(await notice.count()) });
  if (await notice.count()) {
    await expect(c3.getByText(/再次导入会新建一个场景/)).toBeVisible();
    const href = await c3.locator(`a[href="#/plan/${encodeURIComponent(id)}"]`).count();
    test.info().annotations.push({ type: 'last-import-link-matches', description: String(href) });
  }
  await page.waitForTimeout(1500);
  test.info().annotations.push({ type: 'manual-edit-diff', description: (await c3.getByText(/手工编辑/).allInnerTexts()).join(' | ').slice(0, 400) });
  const refill = c3.getByRole('button', { name: '用该场景的参数和种子填回表单' });
  test.info().annotations.push({ type: 'refill-button', description: String(await refill.count()) });
  if (await refill.count()) { await refill.click(); await page.waitForTimeout(300);
    test.info().annotations.push({ type: 'after-refill', description: `${await c3.locator(`input[aria-label="${nm} 任务点数"]`).inputValue()}/${await c3.locator(`input[aria-label="${nm} 随机种子"]`).inputValue()}` }); }
  await c3.screenshot({ path: `${shots}/agri-last-import.png` });
  // preflight: coverage headland < swath
  const cov = cardWith(page, '地头宽度'); await cov.evaluate(d => { d.open = true; });
  await cov.locator('input[aria-label$=" 地头宽度"]').fill('1');
  await page.waitForTimeout(500);
  const issues = cov.getByRole('list', { name: '预检问题' }).getByRole('button');
  test.info().annotations.push({ type: 'coverage-issues', description: (await issues.allInnerTexts()).join(' | ') });
  if (await issues.count()) await issues.first().click();
  await cov.screenshot({ path: `${shots}/agri-preflight-headland.png` });
  // preflight: obstacle radius huge in a fleet card
  const ob = cardWith(page, '障碍半径'); await ob.evaluate(d => { d.open = true; });
  await ob.locator('input[aria-label$=" 障碍半径"]').fill('40'); await page.waitForTimeout(500);
  const iss2 = ob.getByRole('list', { name: '预检问题' }).getByRole('button');
  test.info().annotations.push({ type: 'obstacle-issues', description: (await iss2.allInnerTexts()).join(' | ').slice(0, 400) });
  if (await iss2.count()) { await iss2.first().click(); await page.waitForTimeout(300);
    test.info().annotations.push({ type: 'issue-click-status', description: (await ob.getByRole('status').allInnerTexts()).join(' | ') }); }
  await ob.screenshot({ path: `${shots}/agri-preflight-obstacle.png` });
  const built = await ob.getByText(/当前参数无法生成预览/).allInnerTexts();
  if (built.length) test.info().annotations.push({ type: 'obstacle-build-error', description: built.join(' ') });
});
