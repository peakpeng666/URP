/** Browser-only integrity fault injection; immutable local research files are untouched. */
import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';

const base = process.argv[2] || 'http://127.0.0.1:5173';
const filter = process.argv[3] || '';
const output = path.resolve('artifacts/codex-browser/product-evidence');
await mkdir(output, { recursive: true });
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const report = { scope: 'Actual EvidenceView source preview, download and trust-boundary tests', base, filter,
  startedAt: new Date().toISOString(), trustAssumption: 'meta.json is trusted and is never intercepted',
  mutationBoundary: 'Only Playwright browser route responses; no research/public-data files are changed', checks: [] };
const browser = await chromium.launch({ headless: true });
const api = await browser.newContext();
const meta = await (await api.request.get(base + '/data/meta.json')).json();
const originalReport = await (await api.request.get(base + meta.sources['REPORT_ZH.md'].url)).body();
const originalManifest = await (await api.request.get(base + meta.sources['MANIFEST.json'].url)).body();
assert.equal(sha(originalReport), meta.sources['REPORT_ZH.md'].sha256);
assert.equal(sha(originalManifest), meta.sources['MANIFEST.json'].sha256);
const manifest = JSON.parse(originalManifest);
assert.equal(manifest.files['MANIFEST.json'], undefined, 'The immutable manifest intentionally excludes itself');
const marker = 'BPP_BROWSER_ACCEPTANCE_MODIFIED_REPORT_BYTES';
const modifiedReport = Buffer.concat([Buffer.from(marker + '\n\n'), originalReport]);
const forgedManifestObject = structuredClone(manifest);
forgedManifestObject.files['REPORT_ZH.md'] = { ...forgedManifestObject.files['REPORT_ZH.md'],
  bytes: modifiedReport.length, sha256: sha(modifiedReport) };
const forgedManifest = Buffer.from(JSON.stringify(forgedManifestObject));
report.anchors = { reportSha256: sha(originalReport), reportBytes: originalReport.length,
  manifestSha256: sha(originalManifest), manifestBytes: originalManifest.length,
  modifiedReportSha256: sha(modifiedReport), forgedManifestSha256: sha(forgedManifest) };
const catalog = await (await api.request.get(base + '/data/catalog.json')).json();
const streamA = catalog.streams.find(stream => stream.instance_id === 'confirmation_weibull_3_45_r0__descending');
const streamB = catalog.streams.find(stream => stream.split === 'confirmation' && stream.instance_id !== streamA.instance_id);
assert.ok(streamA && streamB);
const records = new Map();
for (const [stream, policy] of [[streamA, 'BF'], [streamA, 'BF_then_EoH'], [streamB, 'BF']]) {
  const descriptor = stream.runs.find(run => run.policy === policy);
  const bytes = await (await api.request.get(base + descriptor.data_url)).body();
  assert.equal(sha(bytes), descriptor.sha256);
  records.set(`${stream.instance_id}|${policy}`, JSON.parse(bytes));
}
const oldRecordRef = records.get(`${streamA.instance_id}|BF`).source.record;
const oldRecordBytes = await (await api.request.get(base + oldRecordRef.url)).body();
assert.equal(sha(oldRecordBytes), oldRecordRef.sha256);
await api.close();
const appSourcePath = path.resolve('src/views/EvidenceView.tsx');
report.applicationSourceSha256AtStart = sha(await readFile(appSourcePath));
report.replayEvidenceSourceSha256AtStart = sha(await readFile('src/views/replay/EvidenceTab.tsx'));

const fileUrl = file => `${base}/#/evidence?file=${encodeURIComponent(file)}`;
async function settled(page) {
  await page.waitForFunction(() => {
    const main = document.querySelector('main');
    const text = main?.textContent || '';
    return !!main?.querySelector('code, [role="alert"]') && /字节核对|数据加载失败|哈希不一致|停止使用|找不到/.test(text) &&
      !/下载并计算哈希|正在载入视图|载入中…/.test(text);
  }, null, { timeout: 12000 });
}
async function observed(page) {
  const mainText = await page.locator('main').innerText();
  const preview = await page.locator('main pre').allTextContents();
  return { mainText, previewHasModifiedMarker: preview.some(text => text.includes(marker)),
    previewTextSha256: preview.length ? sha(Buffer.from(preview.join('\n'))) : null,
    exactMatchBadge: await page.getByText('逐字节一致', { exact: true }).count() > 0,
    untrustedMessage: /不一致|不可信|校验失败|停止使用|停止作为可信/.test(mainText),
    displayedHashValues: await page.locator('main code').allTextContents() };
}
async function installBytes(page, urlPath, choose, trace) {
  await page.route('**' + urlPath, async route => {
    const index = trace.filter(entry => entry.path === urlPath).length + 1;
    const content = choose(index);
    const entry = { path: urlPath, requestNumber: index, method: route.request().method(),
      suppliedSha256: sha(content), suppliedBytes: content.length,
      modified: content.includes(Buffer.from(marker)) || sha(content) === sha(forgedManifest), status: 'SUPPLYING' };
    trace.push(entry);
    try {
      await route.fulfill({ status: 200, contentType: urlPath.endsWith('.json') ? 'application/json' : 'text/plain; charset=utf-8', body: content });
      entry.status = 'FULFILLED';
    } catch (error) { entry.status = 'ABORTED_OR_FAILED'; entry.error = String(error); }
  });
}
async function check(name, action) {
  if (filter && !name.includes(filter)) return;
  const context = await browser.newContext({ viewport: { width: 1366, height: 900 }, acceptDownloads: true });
  const page = await context.newPage();
  const entry = { name, status: 'RUNNING', requests: [], uncaughtErrors: [] };
  page.on('pageerror', error => entry.uncaughtErrors.push(error.message));
  try {
    entry.evidence = await action(page, entry);
    assert.equal(entry.uncaughtErrors.length, 0, 'Uncaught browser error');
    entry.status = 'PASS';
  } catch (error) {
    entry.status = 'FAIL'; entry.error = String(error.message);
    entry.finalObservation = await observed(page).catch(() => null);
  } finally {
    entry.screenshot = name + '.png';
    await page.screenshot({ path: path.join(output, entry.screenshot), fullPage: true });
    report.checks.push(entry);
    console.log(entry.status, name, entry.error || '');
    await context.close();
  }
}

await check('normal-preview-and-download-original-bytes', async (page, entry) => {
  await page.goto(fileUrl('REPORT_ZH.md'), { waitUntil: 'networkidle' });
  await settled(page);
  const state = await observed(page);
  assert.equal(state.exactMatchBadge, true, 'Original report must match its immutable hash');
  assert.equal(await page.locator('main pre').textContent(), originalReport.toString('utf8'));
  // A download must retain the already verified buffer even if the server's
  // next response for this path would have changed.
  await installBytes(page, meta.sources['REPORT_ZH.md'].url, () => modifiedReport, entry.requests);
  const [download] = await Promise.all([page.waitForEvent('download'), page.getByRole('link', { name: '下载原始字节' }).click()]);
  const bytes = await readFile(await download.path());
  assert.equal(sha(bytes), meta.sources['REPORT_ZH.md'].sha256);
  assert.deepEqual(bytes, originalReport);
  assert.equal(entry.requests.length, 0, 'Download must not refetch potentially different bytes');
  return { previewMatchesOriginalText: true, downloadFilename: download.suggestedFilename(), downloadBytes: bytes.length,
    downloadSha256: sha(bytes), hashAnchor: meta.sources['REPORT_ZH.md'].sha256, noDownloadRefetch: true };
});

await check('manifest-self-verification-uses-trusted-meta-anchor', async page => {
  await page.goto(fileUrl('MANIFEST.json'), { waitUntil: 'networkidle' });
  await settled(page);
  const state = await observed(page);
  assert.equal(state.exactMatchBadge, true,
    'MANIFEST is excluded from files, but its immutable SHA is available in meta.sources and must be used for self-verification');
  assert.ok(state.displayedHashValues.includes(meta.sources['MANIFEST.json'].sha256));
  return { trustedMetaSha256: meta.sources['MANIFEST.json'].sha256, absentFromOwnFiles: true, observation: state };
});

await check('missing-file-error-and-navigation-recovery', async page => {
  await page.goto(fileUrl('__acceptance_missing_source__.txt'), { waitUntil: 'networkidle' });
  await settled(page);
  const missing = await observed(page);
  assert.match(missing.mainText, /404|不存在|找不到|未收录|加载失败/);
  assert.equal(missing.exactMatchBadge, false);
  await page.locator('main').getByRole('link', { name: '证据', exact: true }).click();
  await page.getByRole('heading', { name: '证据与核验', exact: true }).waitFor();
  await page.locator('main').getByRole('link').filter({ hasText: 'REPORT_ZH.md' }).click();
  await page.waitForURL(url => url.hash.includes('file=REPORT_ZH.md'));
  await settled(page);
  assert.equal((await observed(page)).exactMatchBadge, true);
  return { missingShowsError: true, recoveredThroughEvidenceNavigation: true };
});

await check('valid-text-with-corrupted-source-bytes-is-untrusted', async (page, entry) => {
  await installBytes(page, meta.sources['REPORT_ZH.md'].url, () => modifiedReport, entry.requests);
  await page.goto(fileUrl('REPORT_ZH.md'), { waitUntil: 'networkidle' });
  await settled(page);
  const state = await observed(page);
  assert.equal(state.exactMatchBadge, false, 'Modified valid text must not get a trusted badge');
  assert.equal(state.untrustedMessage, true, 'The integrity failure must be visible');
  assert.equal(await page.getByRole('link', { name: '下载原始字节' }).count(), 0, 'Untrusted bytes have no verified-download action');
  return state;
});

for (const modifiedFirst of [true, false]) {
  await check(`alternating-responses-${modifiedFirst ? 'modified-first' : 'original-first'}`, async (page, entry) => {
    await installBytes(page, meta.sources['REPORT_ZH.md'].url,
      number => ((number % 2 === 1) === modifiedFirst) ? modifiedReport : originalReport, entry.requests);
    await page.goto(fileUrl('REPORT_ZH.md'), { waitUntil: 'networkidle' });
    await settled(page);
    const state = await observed(page);
    entry.evidence = state;
    // Only this actual DOM conjunction proves the split-fetch trust bug.
    // Request order by itself is deliberately not treated as a defect.
    assert.equal(state.previewHasModifiedMarker && state.exactMatchBadge, false,
      'Confirmed: the rendered report contains modified bytes while a separate fetch produces “逐字节一致”');
    return { ...state, requestOrderingAloneNotUsedAsFailure: true };
  });
}

await check('forged-manifest-and-source-rejected-by-meta-root', async (page, entry) => {
  await installBytes(page, meta.sources['MANIFEST.json'].url, () => forgedManifest, entry.requests);
  await installBytes(page, meta.sources['REPORT_ZH.md'].url, () => modifiedReport, entry.requests);
  await page.goto(fileUrl('REPORT_ZH.md'), { waitUntil: 'networkidle' });
  await settled(page);
  const state = await observed(page);
  entry.evidence = { ...state, trustedManifestSha256: meta.sources['MANIFEST.json'].sha256,
    suppliedManifestSha256: sha(forgedManifest), modifiedReportSha256: sha(modifiedReport), metaWasNotIntercepted: true };
  assert.equal(state.exactMatchBadge, false,
    'Confirmed: changing both MANIFEST and source is accepted despite the unchanged trusted meta.sources MANIFEST SHA');
  assert.equal(state.untrustedMessage, true, 'The trust-root mismatch must be visible');
  return entry.evidence;
});

const replayHash = (stream, policy) => `#/replay/${stream.instance_id}?a=${policy}&t=500&view=observed`;
const expectedPaths = (stream, policy) => {
  const source = records.get(`${stream.instance_id}|${policy}`).source;
  return [...new Set(['record', 'trajectory', 'input', 'model', 'protocol', 'freeze'].map(key => source[key]?.path).filter(Boolean))];
};
async function replayEvidence(page, stream, policy, navigate = true) {
  if (navigate) await page.goto(base + '/' + replayHash(stream, policy), { waitUntil: 'networkidle' });
  await page.getByRole('slider', { name: '回放进度（已处理项数）' }).waitFor();
  await page.getByRole('tab', { name: '证据', exact: true }).click();
  await assertPaths(page, stream, policy);
}
async function assertPaths(page, stream, policy) {
  const expected = expectedPaths(stream, policy);
  await page.waitForFunction(paths => {
    const actual = [...document.querySelectorAll('[role="tabpanel"] li code')].map(element => element.textContent);
    return JSON.stringify(actual) === JSON.stringify(paths);
  }, expected, { timeout: 12000 });
  assert.deepEqual(await page.getByRole('tabpanel').locator('li code').allTextContents(), expected);
  return expected;
}
async function verifyReplay(page, stream, policy) {
  await page.getByRole('button', { name: '在本浏览器核对全部哈希' }).click();
  const count = expectedPaths(stream, policy).length;
  await page.waitForFunction(expected => document.querySelectorAll('[role="tabpanel"] [aria-label="通过"]').length === expected, count);
  assert.equal(await page.getByRole('tabpanel').getByRole('img', { name: '失败' }).count(), 0);
  return count;
}

await check('replay-sources-follow-policy-and-stream', async page => {
  await replayEvidence(page, streamA, 'BF');
  const initial = await assertPaths(page, streamA, 'BF');
  await verifyReplay(page, streamA, 'BF');
  await page.getByRole('combobox', { name: '主运行策略' }).selectOption('BF_then_EoH');
  const changedPolicy = await assertPaths(page, streamA, 'BF_then_EoH');
  assert.notEqual(initial[0], changedPolicy[0]);
  assert.equal(await page.getByRole('tabpanel').getByRole('img', { name: '通过' }).count(), 0,
    'A completed PASS must be cleared when the selected policy changes');
  await verifyReplay(page, streamA, 'BF_then_EoH');
  // Hash navigation keeps the same application/controller instance. The new
  // stream resets its explanation tab, which we open through the real UI.
  await page.evaluate(hash => { location.hash = hash; }, replayHash(streamB, 'BF'));
  await page.getByRole('combobox', { name: '主运行策略' }).waitFor();
  await page.waitForFunction(id => document.querySelector('main')?.textContent.includes(id), streamB.instance_id);
  await replayEvidence(page, streamB, 'BF', false);
  const changedStream = await assertPaths(page, streamB, 'BF');
  assert.notEqual(changedPolicy[0], changedStream[0]);
  assert.equal(await page.getByRole('tabpanel').getByRole('img', { name: '通过' }).count(), 0);
  await verifyReplay(page, streamB, 'BF');
  return { initial, changedPolicy, changedStream, realSourcesReverified: true, stalePassCleared: true };
});

await check('replay-old-verification-cannot-mark-new-policy', async (page, entry) => {
  await replayEvidence(page, streamA, 'BF');
  let release;
  const gate = new Promise(resolve => { release = resolve; });
  let arrive;
  const arrived = new Promise(resolve => { arrive = resolve; });
  let completed;
  const completion = new Promise(resolve => { completed = resolve; });
  await page.route('**' + oldRecordRef.url, async route => {
    const request = { path: oldRecordRef.path, status: 'HELD_OLD_POLICY' };
    entry.requests.push(request);
    arrive();
    await gate;
    try {
      await route.fulfill({ status: 200, contentType: 'application/json', body: oldRecordBytes });
      request.status = 'OLD_RESPONSE_RELEASED';
    } catch { request.status = 'OLD_REQUEST_ABORTED'; }
    completed();
  });
  try {
    await page.getByRole('button', { name: '在本浏览器核对全部哈希' }).click();
    await Promise.race([arrived, new Promise((_, reject) => setTimeout(() => reject(Error('Old verification never requested its source')), 12000))]);
    await page.getByRole('combobox', { name: '主运行策略' }).selectOption('BF_then_EoH');
    await assertPaths(page, streamA, 'BF_then_EoH');
    release();
    await completion;
    await page.waitForTimeout(200); // Allow a released old fetch/hash callback to attempt publication.
    assert.equal(await page.getByRole('tabpanel').getByRole('img').count(), 0, 'Old PASS/pending/failure must not attach to the new source rows');
    await page.getByRole('button', { name: '在本浏览器核对全部哈希', exact: true }).waitFor();
    await verifyReplay(page, streamA, 'BF_then_EoH');
    return { delayedPath: oldRecordRef.path, currentPaths: expectedPaths(streamA, 'BF_then_EoH'),
      oldResultIgnored: true, newVerificationSucceeded: true };
  } finally { release(); }
});

report.applicationSourceSha256AtEnd = sha(await readFile(appSourcePath));
report.replayEvidenceSourceSha256AtEnd = sha(await readFile('src/views/replay/EvidenceTab.tsx'));
report.applicationSourceChangedDuringChecks = report.applicationSourceSha256AtStart !== report.applicationSourceSha256AtEnd ||
  report.replayEvidenceSourceSha256AtStart !== report.replayEvidenceSourceSha256AtEnd;
report.status = report.checks.length && report.checks.every(check => check.status === 'PASS') ? 'PASS' : 'FAIL';
report.finishedAt = new Date().toISOString();
await writeFile(path.join(output, filter ? `evidence-report-${filter.replace(/[^a-z0-9-]/gi, '_')}.json` : 'evidence-report.json'), JSON.stringify(report, null, 2));
await browser.close();
console.log(JSON.stringify({ status: report.status, sourceChanged: report.applicationSourceChangedDuringChecks,
  checks: report.checks.map(({ name, status, error }) => ({ name, status, error })) }, null, 2));
process.exitCode = report.status === 'PASS' ? 0 : 1;
