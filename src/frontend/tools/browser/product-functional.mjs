import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';

// Run against Vite while authoring; pass the built preview URL for final UI acceptance.
// An explicit unfinished ReplayView is PENDING, never treated as an acceptance failure.
const base = process.argv[2] || 'http://127.0.0.1:4173';
const development = new URL(base).port === '5173';
const uiReady = !development || process.argv.includes('--ui-ready');
const onlyUI = process.argv.includes('--only-ui');
const nameFilter = process.argv.find((value) => value.startsWith('--match='))?.slice('--match='.length) ?? null;
const output = path.resolve('artifacts/codex-browser');
await mkdir(output, { recursive: true });
const report = {
  scope: 'Claude product replay: browser functional acceptance (separate from reference preview)',
  base, build: development ? 'Vite development/StrictMode' : 'built preview',
  testFilter: nameFilter, completeUISuite: nameFilter === null,
  startedAt: new Date().toISOString(), checks: [], controllerChecks: [], screenshots: [],
  limitations: ['Headless Chromium; physical phones not tested', 'Direct controller probes run only on Vite and are distinguished from UI acceptance'],
};
try {
  const mainSource = await readFile(path.resolve('src/main.tsx'));
  const text = mainSource.toString('utf8');
  const devExplicitlyUnwrapped = /import\.meta\.env\.DEV\s*\?\s*\(\s*<App\s*\/>/.test(text);
  report.source = { mainSha256: createHash('sha256').update(mainSource).digest('hex'), devStrictMode: !devExplicitlyUnwrapped && /<StrictMode[\s>]/.test(text), containsStrictMode: /<StrictMode[\s>]/.test(text), collectedAt: new Date().toISOString() };
} catch { report.source = { unavailable: true }; }
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });
await page.addInitScript(() => {
  // Observe actual Canvas drawing without altering the renderer or research data.
  const traces = new WeakMap();
  window.__bppCanvasTraces = traces;
  const originalClear = CanvasRenderingContext2D.prototype.clearRect;
  const originalFill = CanvasRenderingContext2D.prototype.fillRect;
  CanvasRenderingContext2D.prototype.clearRect = function (x, y, width, height) {
    traces.set(this.canvas, { clearedArea: { x, y, width, height }, bars: [] });
    return originalClear.call(this, x, y, width, height);
  };
  CanvasRenderingContext2D.prototype.fillRect = function (x, y, width, height) {
    traces.get(this.canvas)?.bars.push({ x, y, width, height });
    return originalFill.call(this, x, y, width, height);
  };
});
const pageErrors = [], consoleErrors = [];
page.on('pageerror', (error) => pageErrors.push(error.message));
page.on('console', (message) => { if (message.type() === 'error') consoleErrors.push(message.text()); });
const collect = async (list, name, fn) => {
  const begin = performance.now();
  try {
    const evidence = await fn();
    list.push({ name, status: 'PASS', durationMs: Math.round(performance.now() - begin), evidence });
    console.log(`PASS ${name}`);
  } catch (error) {
    const diagnostic = list === report.checks ? {
      url: page.url(),
      sliderNow: await page.getByRole('slider', { name: '回放进度（已处理项数）' }).getAttribute('aria-valuenow', { timeout: 500 }).catch(() => null),
      body: (await page.locator('body').innerText()).slice(0, 2500),
    } : undefined;
    list.push({ name, status: 'FAIL', durationMs: Math.round(performance.now() - begin), error: error.stack, diagnostic });
    console.log(`FAIL ${name}: ${error.message}`);
  }
};
const check = (name, fn) => nameFilter && !name.includes(nameFilter) && !name.startsWith('real product replay loads')
  ? Promise.resolve() : collect(report.checks, name, fn);
const response = await page.request.get(`${base}/data/catalog.json`);
assert.equal(response.status(), 200, 'Catalog must be available');
const catalog = await response.json();
const candidates = catalog.streams.filter((stream) => stream.split === 'confirmation');
const [streamA, streamB] = candidates;
const runA = await (await page.request.get(`${base}${streamA.runs.find((run) => run.policy === 'SELECTOR').data_url}`)).json();
const runB = await (await page.request.get(`${base}${streamA.runs.find((run) => run.policy === 'BF_then_EoH').data_url}`)).json();
const replayHash = (stream, t = 0, view = 'observed') => `#/replay/${encodeURIComponent(stream.instance_id)}?a=SELECTOR&b=BF_then_EoH&t=${t}&view=${view}`;

if (development && !onlyUI) {
  for (const scenario of ['normal', 'dispose-remount', 'A-B-A']) {
    await collect(report.controllerChecks, `browser controller ${scenario}`, async () => {
      const context = await browser.newContext();
      const target = await context.newPage();
      try {
        await target.goto(`${base}/`, { waitUntil: 'networkidle' });
        const evidence = await target.evaluate(async ({ streamA, streamB, scenario }) => {
          const { ReplayController } = await import('/src/replay/controller.ts');
          const controller = new ReplayController();
          if (scenario === 'normal') {
            await controller.load(streamA, 'SELECTOR', 'BF_then_EoH', 0);
            const states = [];
            for (const t of [0, 499, 500, 501, 5000, 71, 0]) {
              controller.seek(t);
              const a = controller.state('a');
              const b = controller.state('b');
              states.push({ t, aProcessed: a?.processed, bProcessed: b?.processed, aBins: a?.usedBins, bBins: b?.usedBins, decision: controller.decision('a')?.available });
            }
            const snapshot = controller.getSnapshot();
            controller.dispose();
            return { snapshot, states };
          }
          const first = controller.load(streamA, 'SELECTOR', 'BF_then_EoH', 500);
          if (scenario === 'dispose-remount') {
            // The same ref survives React StrictMode's effect cleanup/re-setup.
            controller.dispose();
            await Promise.allSettled([first, controller.load(streamA, 'SELECTOR', 'BF_then_EoH', 500)]);
          } else {
            const second = controller.load(streamB, 'SELECTOR', 'BF_then_EoH', 500);
            const third = controller.load(streamA, 'SELECTOR', 'BF_then_EoH', 500);
            await Promise.allSettled([first, second, third]);
          }
          const snapshot = controller.getSnapshot();
          const loadedStream = controller.stream?.instance_id;
          controller.dispose();
          return { snapshot, loadedStream };
        }, { streamA, streamB, scenario });
        assert.equal(evidence.snapshot.status, 'ready', JSON.stringify(evidence));
        if (scenario === 'normal') {
          for (const state of evidence.states) {
            assert.equal(state.aProcessed, state.t);
            assert.equal(state.bProcessed, state.t);
            assert.equal(state.aBins, state.t ? runA.used_bins_after[state.t - 1] : 0);
            assert.equal(state.bBins, state.t ? runB.used_bins_after[state.t - 1] : 0);
            assert.equal(state.decision, state.t >= 500);
          }
        } else assert.equal(evidence.loadedStream, streamA.instance_id);
        return evidence;
      } finally { await context.close(); }
    });
  }
}

if (uiReady) await page.goto(`${base}/${replayHash(streamA)}`, { waitUntil: 'networkidle' });
const placeholder = uiReady ? await page.getByText('回放视图正在建设中。', { exact: true }).count() : 0;
const slider = page.getByRole('slider', { name: '回放进度（已处理项数）' });
if (!uiReady || placeholder > 0) {
  report.checks.push({ name: 'ReplayView integration', status: 'PENDING', reason: !uiReady
    ? 'Development UI construction is ongoing. Pass --ui-ready only after frontend handoff; controller probes are separate.'
    : 'ReplayView explicitly remains a construction placeholder; no UI acceptance claimed.' });
  report.uiStatus = 'PENDING';
} else {
  const waitTime = async (t) => {
    await slider.waitFor({ timeout: 15000 });
    await page.waitForFunction((expected) => document.querySelector('[role="slider"][aria-label="回放进度（已处理项数）"]')?.getAttribute('aria-valuenow') === String(expected), t, { timeout: 5000 });
  };
  const seek = async (t) => {
    const input = page.getByRole('spinbutton', { name: '已处理' });
    await input.fill(String(t));
    await input.press('Tab');
    await waitTime(t);
  };
  await check('real product replay loads without perpetual StrictMode loading', async () => {
    await waitTime(0);
    assert.equal(await page.getByText('回放视图正在建设中。', { exact: true }).count(), 0);
    return { stream: streamA.instance_id, phase: development ? 'development StrictMode' : 'production preview' };
  });
  if (await slider.count() === 0 || !await slider.isVisible()) {
    const filename = 'product-functional-ui-loading-blocked.png';
    await page.screenshot({ path: path.join(output, filename), fullPage: true });
    report.screenshots.push(filename);
    report.checks.push({ name: 'dependent replay interactions', status: 'NOT_RUN', reason: 'Replay control did not become available; downstream tests would repeat the same blocker.', evidence: await page.locator('main').innerText() });
    report.uiStatus = 'FAIL';
  } else {
  await check('product boundaries and decision visibility honor observed-only knowledge', async () => {
    const evidence = [];
    for (const t of [0, 499, 500, 501, 5000]) {
      await seek(t);
      await page.getByRole('tab', { name: '第 500 项决策', exact: true }).click();
      const decision = page.getByRole('heading', { name: '5 个训练邻居', exact: true });
      assert.equal(await decision.count(), t >= 500 ? 1 : 0);
      const canvases = await page.locator('canvas[role="img"]').evaluateAll((elements) => elements.map((element) => element.getAttribute('aria-label')));
      assert.ok(canvases.length >= 2, 'Both policy shelves must be rendered');
      const normalized = canvases.map((text) => text.replaceAll(',', ''));
      assert.ok(normalized.every((text) => text.includes(`已处理 ${t} 项`)), JSON.stringify(canvases));
      const expectedBins = [t ? runA.used_bins_after[t - 1] : 0, t ? runB.used_bins_after[t - 1] : 0];
      for (let i = 0; i < 2; i += 1) assert.match(normalized[i], new RegExp(`(?:已用\\s*${expectedBins[i]}\\s*箱|已开\\s*${expectedBins[i]}\\s*个?箱)`), `stale shelf text at ${t}: ${normalized[i]}`);
      evidence.push({ t, expectedBins, canvasLabels: canvases, decisionVisible: t >= 500 });
    }
    return evidence;
  });
  await check('product random seeks, keyboard single-step, Home and End remain synchronized', async () => {
    const positions = [3071, 17, 500, 4999, 888, 501];
    for (const t of positions) await seek(t);
    await slider.focus();
    await page.keyboard.press('ArrowLeft');
    await waitTime(500);
    await page.keyboard.press('ArrowRight');
    await waitTime(501);
    await page.keyboard.press('Home');
    await waitTime(0);
    await page.keyboard.press('End');
    await waitTime(5000);
    return { positions, keyboard: ['ArrowLeft', 'ArrowRight', 'Home', 'End'] };
  });
  await check('product canvas includes the final active slot within a reachable drawing region', async () => {
    await seek(5000);
    await page.waitForFunction((expected) => [...document.querySelectorAll('canvas[role="img"]')].slice(0, 2)
      .every((canvas, i) => window.__bppCanvasTraces.get(canvas)?.bars.length === expected[i]), [runA.used_bins, runB.used_bins], { timeout: 5000 });
    const canvases = await page.locator('canvas[role="img"]').evaluateAll((elements) => elements.map((element) => ({
      label: element.getAttribute('aria-label'), width: element.getBoundingClientRect().width,
      height: element.getBoundingClientRect().height, backingWidth: element.width, backingHeight: element.height,
      parentOverflowY: getComputedStyle(element.parentElement).overflowY,
      parentHeight: element.parentElement.clientHeight, parentScrollHeight: element.parentElement.scrollHeight,
      trace: window.__bppCanvasTraces.get(element),
    })));
    const evidence = canvases.slice(0, 2).map((canvas, i) => {
      const run = i === 0 ? runA : runB;
      const maxSlot = Math.max(...run.assignment);
      const lastSlot = run.assignment.at(-1);
      const { trace, ...geometry } = canvas;
      const clippedBars = trace.bars.filter((bar) => bar.x < 0 || bar.y < 0
        || bar.x + bar.width > trace.clearedArea.width + 0.01 || bar.y + bar.height > trace.clearedArea.height + 0.01);
      return { ...geometry, maxSlot, lastSlot, usedBins: run.used_bins,
        drawnBins: trace.bars.length, clearedArea: trace.clearedArea,
        clippedBarCount: clippedBars.length, maximumDrawnY: Math.max(...trace.bars.map((bar) => bar.y + bar.height)) };
    });
    const filename = 'product-functional-canvas-endpoint.png';
    await page.screenshot({ path: path.join(output, filename), fullPage: true });
    report.screenshots.push(filename);
    assert.ok(evidence.every((canvas) => canvas.drawnBins === canvas.usedBins && canvas.clippedBarCount === 0), JSON.stringify(evidence));
    assert.ok(evidence.every((canvas) => canvas.height <= canvas.parentHeight || /auto|scroll/.test(canvas.parentOverflowY)), 'All canvas rows must be directly visible or scrollable');
    return evidence;
  });
  await check('product observed/hindsight route switch gates decision and restores position', async () => {
    await seek(499);
    await page.getByRole('group', { name: '信息视角' }).getByRole('button', { name: '当时已知', exact: true }).click();
    await page.getByRole('tab', { name: '第 500 项决策', exact: true }).click();
    await page.getByRole('heading', { name: '5 个训练邻居', exact: true }).waitFor({ state: 'hidden', timeout: 5000 });
    assert.equal(await page.getByRole('heading', { name: '5 个训练邻居', exact: true }).count(), 0);
    await page.getByRole('group', { name: '信息视角' }).getByRole('button', { name: '事后对照', exact: true }).click();
    await waitTime(499);
    await page.getByRole('heading', { name: '5 个训练邻居', exact: true }).waitFor();
    await page.getByRole('group', { name: '信息视角' }).getByRole('button', { name: '当时已知', exact: true }).click();
    await waitTime(499);
    await page.getByRole('heading', { name: '5 个训练邻居', exact: true }).waitFor({ state: 'hidden', timeout: 5000 });
    assert.equal(await page.getByRole('heading', { name: '5 个训练邻居', exact: true }).count(), 0);
    await page.reload({ waitUntil: 'networkidle' });
    await waitTime(499);
    return { restored: 499, decisionObserved: false, decisionHindsight: true };
  });
  await check('product same-stream hash positions and browser Back/Forward restore without seek loops', async () => {
    await seek(503);
    const runRequests = [];
    const trackRequest = (request) => { if (request.url().includes('/data/runs/')) runRequests.push(request.url()); };
    page.on('request', trackRequest);
    await page.evaluate(() => {
      const probe = { hashChanges: 0, positionChanges: [] };
      window.__bppHistoryProbe = probe;
      window.addEventListener('hashchange', () => { probe.hashChanges += 1; });
      const slider = document.querySelector('[role="slider"][aria-label="回放进度（已处理项数）"]');
      const observer = new MutationObserver(() => probe.positionChanges.push(slider.getAttribute('aria-valuenow')));
      observer.observe(slider, { attributes: true, attributeFilter: ['aria-valuenow'] });
      window.__bppHistoryObserver = observer;
    });
    const sequence = [];
    const capture = async (expected) => {
      await waitTime(expected);
      await page.waitForFunction((expected) => new URLSearchParams(location.hash.split('?')[1] ?? '').get('t') === String(expected), expected, { timeout: 5000 });
      sequence.push({ processed: Number(await slider.getAttribute('aria-valuenow')), url: page.url() });
    };
    try {
      await page.evaluate((hash) => { location.hash = hash; }, replayHash(streamA, 500));
      await capture(500);
      await page.evaluate((hash) => { location.hash = hash; }, replayHash(streamA, 501));
      await capture(501);
      await page.goBack();
      await capture(500);
      await page.goForward();
      await capture(501);
      await page.goBack();
      await capture(500);
      const beforeSettling = await page.evaluate(() => ({ ...window.__bppHistoryProbe, positionChanges: [...window.__bppHistoryProbe.positionChanges] }));
      await page.waitForTimeout(250);
      const afterSettling = await page.evaluate(() => ({ ...window.__bppHistoryProbe, positionChanges: [...window.__bppHistoryProbe.positionChanges] }));
      assert.equal(await slider.getAttribute('aria-valuenow'), '500');
      assert.deepEqual(afterSettling, beforeSettling, 'URL and seek must settle without continued updates');
      assert.ok(afterSettling.positionChanges.length <= 7, JSON.stringify(afterSettling));
      assert.deepEqual(runRequests, [], 't-only history changes must reuse the same loaded trajectory');
      return { initial: 503, sequence, ...afterSettling, reloadedRunRequests: runRequests.length, settledForMs: 250 };
    } finally {
      page.off('request', trackRequest);
      await page.evaluate(() => window.__bppHistoryObserver?.disconnect());
    }
  });
  await check('product A-to-B-to-A route switching resolves latest run', async () => {
    await page.evaluate(({ a, b }) => {
      location.hash = b;
      setTimeout(() => { location.hash = a; }, 0);
    }, { a: replayHash(streamA, 501), b: replayHash(streamB, 500) });
    await waitTime(501);
    assert.ok(page.url().includes(streamA.instance_id));
    const text = await page.locator('main').innerText();
    assert.ok(!text.includes('加载失败'), text.slice(-300));
    const filename = 'product-functional-replay-desktop.png';
    await page.screenshot({ path: path.join(output, filename), fullPage: true });
    report.screenshots.push(filename);
    return { final: streamA.instance_id, processed: 501 };
  });
  await check('product same-prefix risk comparisons have identical observed-only Y-axis scale', async () => {
    const risk = catalog.streams.filter((stream) => stream.split === 'risk');
    const group = risk.filter((stream) => stream.group_id === risk[0].group_id);
    const axes = [];
    for (const stream of group) {
      await page.evaluate((hash) => { location.hash = hash; }, replayHash(stream, 500));
      await waitTime(500);
      const curve = page.locator('figure').filter({ has: page.locator('figcaption').filter({ hasText: '累计箱数' }) });
      axes.push({ instance: stream.instance_id, labels: await curve.locator('svg text[text-anchor="end"]').allTextContents() });
    }
    assert.equal(axes.length, 3);
    assert.ok(axes[0].labels.length > 0, 'Y-axis labels must be found');
    assert.deepEqual(axes[1].labels, axes[0].labels, 'same observed prefix cannot use different future-derived scale');
    assert.deepEqual(axes[2].labels, axes[0].labels, 'same observed prefix cannot use different future-derived scale');
    return axes;
  });
  await check('product training policy picker offers only recorded branches', async () => {
    const train = catalog.streams.find((stream) => stream.split === 'train');
    const hash = `#/replay/${encodeURIComponent(train.instance_id)}?a=BF&b=BF_then_EoH&t=500&view=observed`;
    await page.evaluate((hash) => { location.hash = hash; }, hash);
    await waitTime(500);
    const options = await page.getByRole('combobox', { name: '主运行策略', exact: true }).locator('option').evaluateAll((options) => options.map((option) => ({ value: option.value, disabled: option.disabled, label: option.textContent })));
    const availablePolicies = options.filter((option) => !option.disabled).map((option) => option.value);
    assert.ok(!availablePolicies.includes('SELECTOR'), 'training has no selectable SELECTOR run');
    assert.ok(!availablePolicies.includes('published_EoH'), 'training has no selectable published_EoH run');
    assert.ok(availablePolicies.includes('BF') && availablePolicies.includes('BF_then_EoH'));
    for (const unavailable of options.filter((option) => ['SELECTOR', 'published_EoH'].includes(option.value))) {
      assert.equal(unavailable.disabled, true);
      assert.match(unavailable.label, /未运行|不存在|不可用/);
    }
    return { instance: train.instance_id, availablePolicies, options };
  });
  await check('product injected HTTP404/hash corruption refuses data and recovers on retry', async () => {
    const evidence = [];
    for (const kind of ['404', 'hash']) {
      const context = await browser.newContext({ viewport: { width: 1366, height: 900 } });
      const target = await context.newPage();
      let inject = true;
      try {
        await target.route('**/data/runs/*__SELECTOR.json', async (route) => {
          if (!inject) return route.continue();
          return route.fulfill(kind === '404'
            ? { status: 404, contentType: 'text/plain', body: 'intentional browser-test missing file' }
            : { status: 200, contentType: 'application/json', body: '{"schema_version":1,"corrupt":true}' });
        });
        await target.goto(`${base}/${replayHash(streamA, 500)}`, { waitUntil: 'networkidle' });
        const retry = target.getByRole('button', { name: '重试', exact: true });
        await retry.waitFor({ timeout: 15000 });
        const errorText = await target.getByRole('alert').innerText();
        assert.match(errorText, kind === '404' ? /找不到数据文件|HTTP 404/ : /哈希不一致|SHA256 mismatch/);
        assert.equal(await target.getByRole('slider', { name: '回放进度（已处理项数）' }).count(), 0);
        inject = false;
        await retry.click();
        await target.getByRole('slider', { name: '回放进度（已处理项数）' }).waitFor({ timeout: 15000 });
        const recoveredProcessed = Number(await target.getByRole('slider', { name: '回放进度（已处理项数）' }).getAttribute('aria-valuenow'));
        assert.equal(recoveredProcessed, 500, 'Retry must retain the requested replay position');
        assert.equal(await target.getByRole('alert').count(), 0);
        evidence.push({ kind, errorText, recovered: true, requestedProcessed: 500, recoveredProcessed, requestedPositionPreserved: recoveredProcessed === 500 });
      } finally { await context.close(); }
    }
    return evidence;
  });
  await check('product reset control, speed and decision-boundary automatic pause operate', async () => {
    await page.evaluate((hash) => { location.hash = hash; }, replayHash(streamA, 499));
    await waitTime(499);
    await page.getByRole('button', { name: '500×', exact: true }).click();
    await page.getByRole('button', { name: '播放', exact: true }).click();
    await waitTime(500);
    await page.getByRole('button', { name: '播放', exact: true }).waitFor();
    await page.waitForTimeout(150);
    assert.equal(await slider.getAttribute('aria-valuenow'), '500');
    await page.getByRole('button', { name: '重置到开始', exact: true }).click();
    await waitTime(0);
    return { boundaryPause: 500, reset: 0 };
  });
  await check('product normal functional flow has no runtime errors', async () => {
    assert.deepEqual(pageErrors, []);
    assert.deepEqual(consoleErrors, []);
    return { pageErrors, consoleErrors };
  });
  report.uiStatus = report.checks.every((item) => item.status === 'PASS') ? 'PASS' : 'FAIL';
  }
}

report.runtime = { pageErrors, consoleErrors };
try {
  const currentMain = await readFile(path.resolve('src/main.tsx'));
  report.source.mainSha256AtFinish = createHash('sha256').update(currentMain).digest('hex');
  report.source.changedDuringRun = report.source.mainSha256AtFinish !== report.source.mainSha256;
} catch { /* Preserve the initial source observation. */ }
report.finishedAt = new Date().toISOString();
report.controllerStatus = report.controllerChecks.length === 0 ? (onlyUI ? 'NOT_REPEATED_KNOWN_FINDINGS' : 'NOT_RUN_ON_BUILD')
  : report.controllerChecks.every((item) => item.status === 'PASS') ? 'PASS' : 'FAIL';
report.status = report.uiStatus === 'PENDING' ? 'PENDING_UI'
  : report.uiStatus === 'PASS' && report.controllerStatus !== 'FAIL' ? 'PASS' : 'FAIL';
await writeFile(path.join(output, 'product-functional.json'), `${JSON.stringify(report, null, 2)}\n`);
await browser.close();
console.log(JSON.stringify({ status: report.status, uiStatus: report.uiStatus, controllerStatus: report.controllerStatus }, null, 2));
process.exitCode = report.status === 'FAIL' || report.controllerStatus === 'FAIL' ? 1 : 0;
