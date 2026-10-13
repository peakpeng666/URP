import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const base = process.argv[2] || 'http://127.0.0.1:4174';
const output = path.resolve('artifacts/codex-browser');
await mkdir(output, { recursive: true });
const report = {
  scope: 'Codex independent reference/data acceptance preview ONLY; not Claude product frontend acceptance',
  base, startedAt: new Date().toISOString(), checks: [], screenshots: [], errors: [],
  limitations: ['Headless Chromium only', 'Viewport and touch emulation; no physical phone', 'CSS 200% zoom, not operating-system/browser toolbar zoom', 'Main product frontend acceptance is separate'],
};
const browser = await chromium.launch({ headless: true });
const check = async (name, fn) => {
  const start = performance.now();
  try {
    const evidence = await fn();
    report.checks.push({ name, status: 'PASS', durationMs: Math.round(performance.now() - start), evidence });
    console.log(`PASS ${name}`);
  } catch (error) {
    report.checks.push({ name, status: 'FAIL', durationMs: Math.round(performance.now() - start), error: error.stack });
    console.log(`FAIL ${name}: ${error.message}`);
  }
};
const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });
const jsErrors = [], consoleErrors = [], requestFailures = [];
page.on('pageerror', (error) => jsErrors.push(error.message));
page.on('console', (message) => { if (message.type() === 'error') consoleErrors.push(message.text()); });
page.on('requestfailed', (request) => requestFailures.push({ url: request.url(), error: request.failure()?.errorText }));
const ready = async (target = page) => {
  await target.locator('#timeline:not([disabled])').waitFor({ timeout: 15000 });
  await target.waitForFunction(() => document.querySelector('#replay-loading')?.textContent.includes('SHA256 已核对'));
};
const setTime = async (n, target = page) => {
  await target.locator('#timeline').evaluate((element, value) => {
    element.value = String(value);
    element.dispatchEvent(new Event('input', { bubbles: true }));
  }, n);
  assert.equal((await target.locator('#processed').innerText()).replaceAll(',', ''), String(n));
};
const stats = async (target = page) => Promise.all(['left', 'right'].map(async (side) =>
  Number((await target.locator(`#${side}-stats strong`).first().innerText()).replaceAll(',', ''))));
const getJSON = async (url) => {
  const response = await page.request.get(`${base}${url}`);
  assert.equal(response.status(), 200, url);
  return response.json();
};
let catalog, initialStream, leftRun, rightRun;

await check('load real catalog and paired SHA256-checked trajectories', async () => {
  await page.goto(`${base}/?view=replay`, { waitUntil: 'networkidle' });
  await ready();
  catalog = await getJSON('/data/catalog.json');
  assert.equal(catalog.streams.length, 264);
  const id = await page.locator('#instance').inputValue();
  initialStream = catalog.streams.find((stream) => stream.instance_id === id);
  const leftPolicy = await page.locator('#left-policy').inputValue();
  const rightPolicy = await page.locator('#right-policy').inputValue();
  leftRun = await getJSON(initialStream.runs.find((run) => run.policy === leftPolicy).data_url);
  rightRun = await getJSON(initialStream.runs.find((run) => run.policy === rightPolicy).data_url);
  assert.equal(leftRun.instance_id, rightRun.instance_id);
  assert.equal(leftPolicy, 'SELECTOR');
  assert.equal(rightPolicy, 'BF_then_EoH');
  return { instance: id, policies: [leftPolicy, rightPolicy], streamCount: catalog.streams.length };
});

await check('known-only boundaries 0/499/500/501/5000 match recorded counts and hide item501 at500', async () => {
  const evidence = [];
  for (const n of [0, 499, 500, 501, 5000]) {
    await page.locator(`[data-seek="${n}"]`).click();
    const actual = await stats();
    assert.deepEqual(actual, [n ? leftRun.used_bins_after[n - 1] : 0, n ? rightRun.used_bins_after[n - 1] : 0]);
    const decision = await page.locator('#decision').innerText();
    assert.equal(decision.includes('尚未到达选择时刻'), n < 500);
    assert.equal(await page.locator('#decision tbody tr').count(), n < 500 ? 0 : 36);
    const current = await page.locator('#current-item').innerText();
    if (n === 0) assert.match(current, /没有物品到达/);
    else assert.match(current, new RegExp(`第 ${n} 项 · 大小 ${leftRun.items[n - 1]}`));
    if (n === 500) assert.ok(!current.includes('501'));
    assert.match(await page.locator('#curve-text').innerText(), new RegExp(`曲线显示至第 ${n} 项`));
    evidence.push({ processed: n, usedBins: actual, decisionVisible: n >= 500 });
  }
  return evidence;
});

await check('nonmonotonic random seeking and two-policy synchronization match raw run arrays', async () => {
  const positions = [3459, 123, 4999, 2048, 17, 888, 500, 0, 5000, 3021];
  for (const n of positions) {
    await setTime(n);
    assert.deepEqual(await stats(), [n ? leftRun.used_bins_after[n - 1] : 0, n ? rightRun.used_bins_after[n - 1] : 0]);
    assert.match(await page.locator('#curve-text').innerText(), new RegExp(`当前第 ${n} 项`));
    if (n) {
      const current = await page.locator('#current-item').innerText();
      assert.ok(current.includes(`左侧放入箱 #${leftRun.assignment[n - 1] + 1}`));
      assert.ok(current.includes(`右侧放入箱 #${rightRun.assignment[n - 1] + 1}`));
    }
  }
  return { positions, verifiedAgainst: [leftRun.run_id, rightRun.run_id] };
});

await check('retrospective opt-in, return to observed mode, bin detail, play/pause, keyboard', async () => {
  await setTime(499);
  await page.locator('#retrospective').check();
  assert.match(await page.locator('#curve-text').innerText(), /曲线显示至第 5000 项/);
  assert.equal(await page.locator('#decision .prediction').count(), 2);
  await page.locator('#retrospective').uncheck();
  assert.match(await page.locator('#curve-text').innerText(), /曲线显示至第 499 项/);
  await page.locator('[data-active="left"]').click();
  assert.match(await page.locator('#left-detail').innerText(), new RegExp(`第499项\\(${leftRun.items[498]}\\)`));
  await page.locator('#timeline').focus();
  await page.keyboard.press('ArrowRight');
  assert.equal(await page.locator('#timeline').inputValue(), '500');
  await page.locator('#step').focus();
  await page.keyboard.press('Enter');
  assert.equal(await page.locator('#timeline').inputValue(), '501');
  await page.locator('#play').click();
  await page.waitForFunction(() => Number(document.querySelector('#timeline').value) > 501);
  await page.locator('#play').click();
  const stopped = await page.locator('#timeline').inputValue();
  await page.waitForTimeout(220);
  assert.equal(await page.locator('#timeline').inputValue(), stopped);
  const focus = await page.locator('#play').evaluate((element) => ({ outline: getComputedStyle(element).outlineStyle, active: document.activeElement === element }));
  return { pausedAt: stopped, keyboardRangeAndButton: true, focus };
});

await check('training filters expose only actual policies; empty result and refresh persistence recover', async () => {
  await page.locator('#split').selectOption('train');
  await ready();
  assert.deepEqual(await page.locator('#left-policy option').evaluateAll((options) => options.map((option) => option.value)), ['BF', 'BF_then_EoH']);
  assert.match(await page.locator('#decision').innerText(), /没有 SELECTOR 决策记录/);
  await page.locator('#family').selectOption('uniform_1_100');
  await page.locator('#order').selectOption('descending');
  await ready();
  const selected = await page.locator('#instance').inputValue();
  await setTime(501);
  await page.reload({ waitUntil: 'networkidle' });
  await ready();
  assert.equal(await page.locator('#instance').inputValue(), selected);
  assert.equal(await page.locator('#family').inputValue(), 'uniform_1_100');
  assert.equal(await page.locator('#timeline').inputValue(), '501');
  await page.locator('#search').fill('no-such-scientific-instance');
  await page.waitForFunction(() => document.querySelector('#replay-loading').textContent.includes('没有符合条件'));
  assert.equal(await page.locator('#timeline').isDisabled(), true);
  await page.locator('#search').fill('');
  await ready();
  await page.locator('#family').selectOption('');
  await page.locator('#order').selectOption('');
  await page.locator('#split').selectOption('confirmation');
  await ready();
  return { trainingPolicies: ['BF', 'BF_then_EoH'], persistedInstance: selected, emptyRecovery: true };
});

await check('repeated quick switching leaves only latest selected stream visible', async () => {
  const ids = await page.locator('#instance option').evaluateAll((options) => options.slice(0, 5).map((option) => option.value));
  const order = [ids[1], ids[2], ids[3], ids[4], ids[0], ids[2]];
  for (const id of order) await page.locator('#instance').selectOption(id);
  await ready();
  assert.equal(await page.locator('#instance').inputValue(), ids[2]);
  assert.ok((await page.locator('#replay-loading').innerText()).includes(ids[2]));
  assert.equal(await page.locator('#timeline').inputValue(), '0');
  return { switches: order, final: ids[2] };
});

await check('injected HTTP404 and byte corruption show honest failure then retry recovers', async () => {
  const evidence = [];
  for (const kind of ['HTTP404', 'SHA256 corruption']) {
    const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });
    const target = await context.newPage();
    let injected = false;
    await target.route('**/data/runs/*__SELECTOR.json', async (route) => {
      if (injected) return route.continue();
      injected = true;
      await route.fulfill(kind === 'HTTP404' ? { status: 404, contentType: 'text/plain', body: 'injected test failure' } : { status: 200, contentType: 'application/json', body: '{"schema_version":1,"corrupt":true}' });
    });
    await target.goto(`${base}/?view=replay`, { waitUntil: 'networkidle' });
    await target.locator('#retry').waitFor();
    const error = await target.locator('#replay-loading').innerText();
    assert.match(error, kind === 'HTTP404' ? /HTTP 404/ : /SHA256 mismatch/);
    assert.equal(await target.locator('#timeline').isDisabled(), true);
    await target.screenshot({ path: path.join(output, `reference-failure-${kind === 'HTTP404' ? '404' : 'hash'}.png`), fullPage: true });
    await target.locator('#retry').click();
    await ready(target);
    assert.equal(await target.locator('#retry').count(), 0);
    evidence.push({ injected: kind, error, recovered: true });
    await context.close();
  }
  return evidence;
});

await check('delayed obsolete response cannot overwrite a newer browser selection', async () => {
  const context = await browser.newContext();
  const target = await context.newPage();
  await target.goto(`${base}/?view=replay`, { waitUntil: 'networkidle' });
  await ready(target);
  const ids = await target.locator('#instance option').evaluateAll((options) => options.slice(0, 3).map((option) => option.value));
  let delayed = 0;
  const late = [];
  await target.route(`**/data/runs/${ids[1]}__*.json`, async (route) => {
    delayed += 1;
    await new Promise((resolve) => setTimeout(resolve, 550));
    try { await route.continue(); } catch (error) { late.push(error.message); }
  });
  await target.locator('#instance').selectOption(ids[1]);
  await target.locator('#instance').selectOption(ids[2]);
  await ready(target);
  await target.waitForTimeout(700);
  assert.equal(await target.locator('#instance').inputValue(), ids[2]);
  assert.ok((await target.locator('#replay-loading').innerText()).includes(ids[2]));
  assert.equal(await target.locator('#timeline').isDisabled(), false);
  await context.close();
  return { delayedRequests: delayed, finalStream: ids[2], obsoleteRequestExceptions: late };
});

await check('reference responsive screenshots and viewport overflow at six sizes', async () => {
  const viewports = [
    { width: 360, height: 800, mobile: true }, { width: 390, height: 844, mobile: true },
    { width: 430, height: 932, mobile: true }, { width: 844, height: 390, mobile: true },
    { width: 1366, height: 900, mobile: false }, { width: 1920, height: 1080, mobile: false },
  ];
  const evidence = [];
  for (const viewport of viewports) {
    const context = await browser.newContext({ viewport: { width: viewport.width, height: viewport.height }, isMobile: viewport.mobile, hasTouch: viewport.mobile, reducedMotion: 'reduce' });
    const target = await context.newPage();
    const errors = [];
    target.on('pageerror', (error) => errors.push(error.message));
    await target.goto(`${base}/?view=replay&t=500`, { waitUntil: 'networkidle' });
    await ready(target);
    if (viewport.mobile) await target.locator('[data-seek="501"]').tap();
    else await target.locator('[data-seek="501"]').click();
    assert.equal(await target.locator('#timeline').inputValue(), '501');
    await target.locator('[data-seek="500"]').click();
    await target.evaluate(() => scrollTo(0, 0));
    const measurements = await target.evaluate(() => ({
      width: innerWidth, documentWidth: document.documentElement.scrollWidth,
      reducedMotion: matchMedia('(prefers-reduced-motion: reduce)').matches,
      touchPoints: navigator.maxTouchPoints,
      visibleCriticalControls: ['play', 'step', 'reset', 'timeline'].every((id) => {
        const box = document.getElementById(id).getBoundingClientRect();
        return box.width > 0 && box.height > 0 && box.left >= 0 && box.right <= innerWidth + 1;
      }),
    }));
    const filename = `reference-replay-${viewport.width}x${viewport.height}.png`;
    await target.screenshot({ path: path.join(output, filename), fullPage: true });
    report.screenshots.push(filename);
    evidence.push({ viewport, ...measurements, errors });
    await context.close();
  }
  for (const item of evidence) {
    assert.ok(item.documentWidth <= item.width + 1, `Horizontal page overflow at ${item.viewport.width}: ${item.documentWidth}`);
    assert.equal(item.visibleCriticalControls, true, `Control clipping at ${item.viewport.width}`);
    assert.deepEqual(item.errors, []);
    assert.equal(item.reducedMotion, true);
  }
  return evidence;
});

await check('CSS200% zoom reference retains operable controls without horizontal page overflow', async () => {
  await page.goto(`${base}/?view=replay&t=500`, { waitUntil: 'networkidle' });
  await ready();
  await page.evaluate(() => { document.documentElement.style.zoom = '2'; });
  await page.locator('#step').click();
  assert.equal(await page.locator('#timeline').inputValue(), '501');
  await page.evaluate(() => scrollTo(0, 0));
  const measurements = await page.evaluate(() => ({
    viewportWidth: innerWidth, rootVisualWidth: document.documentElement.getBoundingClientRect().width,
    bodyVisualWidth: document.body.getBoundingClientRect().width, scrollWidth: document.documentElement.scrollWidth,
    zoom: getComputedStyle(document.documentElement).zoom,
  }));
  const filename = 'reference-replay-csszoom200.png';
  await page.screenshot({ path: path.join(output, filename), fullPage: true });
  report.screenshots.push(filename);
  assert.ok(measurements.bodyVisualWidth <= measurements.viewportWidth + 1);
  await page.evaluate(() => { document.documentElement.style.zoom = '1'; });
  return measurements;
});

await check('overview/risk/evidence render current data with original-source links', async () => {
  const evidence = [];
  for (const view of ['overview', 'risk', 'evidence']) {
    await page.locator(`[data-tab="${view}"]`).click();
    assert.equal(await page.locator(`#${view}`).isVisible(), true);
    const text = await page.locator(`#${view}`).innerText();
    if (view === 'overview') {
      assert.match(text, /49 \/ 56 \/ 3/);
      assert.match(text, /−?21\.45|-21\.45/);
    }
    if (view === 'risk') { assert.match(text, /25\.33/); assert.match(text, /152/); }
    if (view === 'evidence') {
      assert.match(text, /900 CPU 秒预算无法认证/);
      assert.ok(await page.locator('#evidence a[href^="/data/evidence/"]').count() > 0);
    }
    const filename = `reference-${view}-1366.png`;
    await page.screenshot({ path: path.join(output, filename), fullPage: true });
    report.screenshots.push(filename);
    evidence.push({ view, heading: await page.locator(`#${view} h1`).innerText() });
  }
  return evidence;
});

report.console = { jsErrors, consoleErrors, requestFailures };
await check('no unexpected runtime exceptions or console errors in normal reference flow', async () => {
  assert.deepEqual(jsErrors, []);
  assert.deepEqual(consoleErrors, []);
  const unexpected = requestFailures.filter((failure) => failure.error !== 'net::ERR_ABORTED');
  assert.deepEqual(unexpected, []);
  return { expectedAbortedRequests: requestFailures.length };
});
report.finishedAt = new Date().toISOString();
report.status = report.checks.every((item) => item.status === 'PASS') ? 'PASS' : 'FAIL';
await writeFile(path.join(output, 'reference-check.json'), `${JSON.stringify(report, null, 2)}\n`);
console.log(JSON.stringify({ status: report.status, checks: report.checks.length, failed: report.checks.filter((item) => item.status === 'FAIL').map((item) => item.name) }, null, 2));
await browser.close();
process.exitCode = report.status === 'PASS' ? 0 : 1;
