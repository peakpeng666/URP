/** Real catalog filtering, restoration and constructed-risk browser acceptance. */
import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
const base = process.argv[2] || 'http://127.0.0.1:5173';
const filter = process.argv[3] || '';
const out = path.resolve('artifacts/codex-browser/product-browse');
await mkdir(out, { recursive: true });
const report = { scope: 'Product Samples and Risk views using real exported catalog', base, filter, startedAt: new Date().toISOString(), checks: [] };
const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });
const catalog = await (await context.request.get(base + '/data/catalog.json')).json();
const meta = await (await context.request.get(base + '/data/meta.json')).json();
async function check(name, fn) {
  if (filter && !name.includes(filter)) return;
  const page = await context.newPage();
  page.setDefaultTimeout(6000);
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  try {
    const evidence = await fn(page);
    assert.deepEqual(errors, [], 'uncaught browser errors');
    report.checks.push({ name, status: 'PASS', evidence });
    console.log('PASS', name);
  } catch (error) {
    report.checks.push({ name, status: 'FAIL', error: error.message, errors, url: page.url(), text: (await page.locator('main').innerText().catch(() => '')).slice(0, 3500) });
    await page.screenshot({ path: path.join(out, name + '.png'), fullPage: true });
    console.log('FAIL', name, error.message);
  } finally { await page.close(); }
}
const rows = page => page.locator('tbody tr');
const openFirstByKeyboard = async page => { await rows(page).first().focus(); await page.keyboard.press('Enter'); };
async function rowCount(page, expected) {
  await page.waitForFunction(n => document.querySelectorAll('tbody tr').length === n, expected, { timeout: 5000 });
  assert.equal(await rows(page).count(), expected);
}
async function filteredSample(page) {
  await page.goto(base + '/#/samples', { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: '确认', exact: true }).click();
  await page.getByRole('button', { name: '降序', exact: true }).click();
  await page.getByRole('button', { name: 'Weibull', exact: true }).click();
  const expected = catalog.streams.filter(s => s.split === 'confirmation' && s.order === 'descending' && s.family === 'weibull_3_45');
  await rowCount(page, expected.length);
  return expected;
}
await check('catalog-counts-and-training-missing-values', async page => {
  await page.goto(base + '/#/samples', { waitUntil: 'networkidle' });
  await rowCount(page, catalog.streams.length);
  await page.getByRole('button', { name: '训练', exact: true }).click();
  await rowCount(page, 144);
  const fields = await rows(page).first().locator('td').allTextContents();
  assert.equal(fields[4].trim(), '—');
  assert.equal(fields[5].trim(), '—');
  assert.equal(fields[6].trim(), '—');
  assert.equal(fields[7].trim(), '—');
  return { allStreams: 264, trainStreams: 144, trainingMissingColumns: fields.slice(4) };
});
await check('filters-real-values-search-refresh', async page => {
  const expected = await filteredSample(page);
  const id = expected[0].instance_id;
  await page.getByRole('searchbox', { name: '搜索样本' }).fill(id);
  await rowCount(page, 1);
  const cells = await rows(page).first().locator('td').allTextContents();
  const number = text => Number(text.replaceAll(',', '').replaceAll('−', '-').trim());
  assert.equal(number(cells[2]), expected[0].results.BF);
  assert.equal(number(cells[3]), expected[0].results.BF_then_EoH);
  assert.equal(number(cells[4]), expected[0].results.SELECTOR);
  assert.equal(number(cells[6]), expected[0].results.selector_minus_SBS);
  const hash = new URL(page.url()).hash;
  await page.reload({ waitUntil: 'networkidle' });
  await rowCount(page, 1);
  assert.equal(await page.getByRole('searchbox').inputValue(), id);
  assert.equal(new URL(page.url()).hash, hash);
  return { id, filteredCount: expected.length, values: cells, hash };
});
await check('training-clears-inapp-incompatible-filters', async page => {
  await page.goto(base + '/#/samples', { waitUntil: 'networkidle' });
  await page.getByRole('button', { name: '胜', exact: true }).click();
  await page.getByRole('button', { name: '训练', exact: true }).click();
  await rowCount(page, 144);
  assert.ok(!new URL(page.url()).hash.includes('outcome='));
  await page.goto(base + '/#/samples?split=train&outcome=win&branch=BF', { waitUntil: 'networkidle' });
  await rowCount(page, 144);
  return { trainWithStaleParams: 144, inappParamsCleared: true };
});
await check('selected-filter-hover-remains-readable', async page => {
  await filteredSample(page);
  const button = page.getByRole('button', { name: 'Weibull', exact: true });
  await button.hover();
  const colors = await button.evaluate(el => ({ color: getComputedStyle(el).color, background: getComputedStyle(el).backgroundColor }));
  assert.notEqual(colors.color, colors.background);
  return colors;
});
await check('browser-back-restores-filters', async page => {
  const expected = await filteredSample(page);
  const hash = new URL(page.url()).hash;
  await openFirstByKeyboard(page);
  await page.getByRole('slider').waitFor();
  await page.goBack();
  await rowCount(page, expected.length);
  assert.equal(new URL(page.url()).hash, hash);
  return { restoredHash: hash };
});
await check('in-app-samples-return-restores-filters', async page => {
  const expected = await filteredSample(page);
  const hash = new URL(page.url()).hash;
  await openFirstByKeyboard(page);
  await page.getByRole('slider').waitFor();
  await page.locator('main').getByRole('link', { name: '样本', exact: true }).click();
  await rowCount(page, expected.length);
  assert.equal(new URL(page.url()).hash, hash);
  return { restoredHash: hash };
});
await check('first-sample-row-receives-pointer', async page => {
  await filteredSample(page);
  await rows(page).first().click();
  await page.getByRole('slider').waitFor();
});
await check('empty-search-is-explicit-and-recoverable', async page => {
  await page.goto(base + '/#/samples', { waitUntil: 'networkidle' });
  await page.getByRole('searchbox').fill('nonexistent-acceptance-stream');
  await page.getByText('没有符合条件的样本', { exact: true }).waitFor();
  assert.equal(await rows(page).count(), 0);
  await page.getByRole('searchbox').fill('');
  await rowCount(page, 264);
});
await check('risk-four-groups-twelve-real-futures', async page => {
  await page.goto(base + '/#/risk', { waitUntil: 'networkidle' });
  await page.getByRole('heading', { level: 1, name: '同前缀，不同未来' }).waitFor();
  await page.getByText('前缀特征、5 个邻居、两分支预测与最终选择在三种未来下逐项一致', { exact: true }).nth(3).waitFor({ timeout: 10000 });
  const links = page.getByRole('button', { name: '回放这个未来', exact: true });
  assert.equal(await links.count(), 12);
  const text = await page.locator('main').innerText();
  assert.ok(text.includes(meta.summary.risk.summary.selector_minus_SBS_mean.toFixed(3)));
  assert.match(text, /152/);
  assert.match(text, /不并入主指标/);
  await links.first().click();
  await page.getByRole('slider').waitFor();
  const id = decodeURIComponent(new URL(page.url()).hash.split('?')[0].split('/').at(-1));
  assert.equal(catalog.streams.find(s => s.instance_id === id)?.split, 'risk');
  assert.equal(await page.getByRole('slider').getAttribute('aria-valuenow'), '500');
  return { groups: 4, futures: 12, openedRiskStream: id };
});
report.status = report.checks.length && report.checks.every(c => c.status === 'PASS') ? 'PASS' : 'FAIL';
report.finishedAt = new Date().toISOString();
await writeFile(path.join(out, filter ? `browse-report-${filter}.json` : 'browse-report.json'), JSON.stringify(report, null, 2));
await browser.close();
console.log(JSON.stringify({ status: report.status, checks: report.checks.map(({ name, status, error }) => ({ name, status, error })) }, null, 2));
process.exitCode = report.status === 'PASS' ? 0 : 1;
