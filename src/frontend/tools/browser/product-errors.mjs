/** Fault-injection browser acceptance for shared product infrastructure. */
import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { zipSync, unzipSync } from 'fflate';

const base = process.argv[2] || 'http://127.0.0.1:5173';
const filter = process.argv[3] || '';
const out = path.resolve('artifacts/codex-browser/product-errors');
await mkdir(out, { recursive: true });
const report = { scope: 'Formal product routing, metadata failures and recovery', base, filter, startedAt: new Date().toISOString(), checks: [] };
const browser = await chromium.launch({ headless: true });
async function check(name, fn) {
  if (filter && !name.includes(filter)) return;
  const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });
  const errors = [];
  page.on('pageerror', e => errors.push(e.message));
  try {
    const evidence = await fn(page);
    assert.deepEqual(errors, [], 'uncaught browser errors');
    report.checks.push({ name, status: 'PASS', evidence });
    console.log('PASS', name);
  } catch (e) {
    report.checks.push({ name, status: 'FAIL', error: e.message, errors, text: await page.locator('body').innerText().catch(() => '') });
    await page.screenshot({ path: path.join(out, name + '.png'), fullPage: true });
    console.log('FAIL', name, e.message);
  } finally { await page.close(); }
}
await check('unknown-route', async page => {
  await page.goto(base + '/#/unknown-view', { waitUntil: 'networkidle' });
  assert.match(await page.locator('main').innerText(), /没有这个页面|页面不存在/);
});
await check('malformed-route', async page => {
  await page.goto(base + '/#/replay/%E0%A4%A', { waitUntil: 'networkidle' });
  assert.match(await page.locator('body').innerText(), /没有这个页面|页面不存在|无效|错误|找不到/);
});
for (const [name, response] of [
  ['meta-404', { status: 404, contentType: 'text/plain', body: 'intentional acceptance fault' }],
  ['meta-invalid-json', { status: 200, contentType: 'application/json', body: '{broken' }],
]) {
  await check(name, async page => {
    await page.route('**/data/meta.json', route => route.fulfill(response));
    await page.goto(base, { waitUntil: 'networkidle' });
    assert.match(await page.locator('main').innerText(), /找不到数据文件|不是有效 JSON|数据加载失败/);
    await page.unroute('**/data/meta.json');
    await page.getByRole('button', { name: /重试/ }).first().click();
    await page.getByRole('heading', { level: 1 }).filter({ hasText: '21.45' }).waitFor({ timeout: 10000 });
    return { recovered: true };
  });
}
await check('failed-validation-not-pending', async page => {
  await page.route('**/data/meta.json', async route => {
    const res = await route.fetch(); const data = await res.json();
    data.project_validation = { ...data.project_validation, status: 'FAIL', passed: false, failures: [{ scope: 'acceptance fixture', message: 'intentional failure' }] };
    await route.fulfill({ response: res, json: data });
  });
  await page.goto(base, { waitUntil: 'networkidle' });
  const main = await page.locator('main').innerText();
  assert.match(main, /本项目(?:数据)?核验[：:]\s*.*(?:失败|不一致)/, 'FAIL must remain a failure state');
  assert.doesNotMatch(main, /本项目(?:数据)?核验[：:]\s*进行中|本项目(?:数据)?核验[：:]\s*全量通过/);
});
await check('missing-ci-not-zero', async page => {
  await page.route('**/data/meta.json', async route => {
    const res = await route.fetch(); const data = await res.json();
    delete data.summary.confirmation.cluster_bootstrap_95_percentile_CI;
    await route.fulfill({ response: res, json: data });
  });
  await page.goto(base, { waitUntil: 'networkidle' });
  const main = await page.locator('main').innerText();
  assert.doesNotMatch(main, /\[0\.00, 0\.00\]/, 'missing CI must not become fabricated zero interval');
  assert.match(main, /缺失|未提供|不可用|未计算|无法|没有|错误|加载失败/);
});
await check('bootstrap-valid-but-corrupted-bytes', async page => {
  await page.route('**/analysis/cluster_bootstrap.npz', async route => {
    const res = await route.fetch();
    const files = unzipSync(new Uint8Array(await res.body()));
    const member = files['mean_deltas.npy'];
    assert.ok(member, 'real bootstrap member');
    const view = new DataView(member.buffer, member.byteOffset, member.byteLength);
    const offset = member[6] === 1 ? 10 + view.getUint16(8, true) : 12 + view.getUint32(8, true);
    view.setFloat64(offset, view.getFloat64(offset, true) + 100, true);
    // Re-encode a valid ZIP and NPY, so parseability alone cannot pass this check.
    await route.fulfill({ response: res, body: Buffer.from(zipSync(files)) });
  });
  await page.goto(base, { waitUntil: 'networkidle' });
  assert.match(await page.locator('main').innerText(), /哈希不一致|哈希校验失败|SHA-256.*不一致|校验失败/,
    'modified but decodable bootstrap must be rejected');
});
report.status = report.checks.every(c => c.status === 'PASS') ? 'PASS' : 'FAIL';
report.finishedAt = new Date().toISOString();
await writeFile(path.join(out, filter ? `errors-report-${filter.replace(/[^a-z0-9-]/gi, '_')}.json` : 'errors-report.json'), JSON.stringify(report, null, 2));
await browser.close();
console.log(JSON.stringify({ status: report.status, checks: report.checks.map(({ name, status, error }) => ({ name, status, error })) }, null, 2));
process.exitCode = report.status === 'PASS' ? 0 : 1;
