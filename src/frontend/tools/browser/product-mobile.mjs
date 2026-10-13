/** Touch and responsive acceptance for the real product replay only. */
import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';

const base = process.argv[2] || 'http://127.0.0.1:5173';
const filter = process.argv[3] || '';
const checkFilter = process.argv[4] || '';
const includesCheck = name => !checkFilter || checkFilter.split(',').some(part => name.includes(part));
const output = path.resolve('artifacts/codex-browser/product-mobile');
await mkdir(output, { recursive: true });
const report = {
  scope: checkFilter ? `Subset only: ${checkFilter}; other prior touch checks were not rerun`
    : 'Actual product replay touch, synchronized real branch counts, responsive layout and reduced motion',
  base, filter, checkFilter, startedAt: new Date().toISOString(), checks: [], screenshots: [],
  driverIsolation: 'Raw CDP slider gestures use a separate page from Playwright touchscreen taps',
  limitations: ['Chromium touch emulation; not a physical phone',
    'This suite covers replay touch controls and responsive layout only; other views use separate acceptance suites',
    'Canvas coverage, curve information boundaries and keyboard behavior are checked by separate targeted suites'],
};
const browser = await chromium.launch({ headless: true });
const api = await browser.newContext();
const catalog = await (await api.request.get(base + '/data/catalog.json')).json();
const sample = catalog.streams.find(stream => stream.split === 'confirmation' && stream.family === 'weibull_3_45' && stream.order === 'descending');
assert.ok(sample, 'Real confirmation sample required');
const policies = ['BF', 'BF_then_EoH'];
const trajectories = await Promise.all(policies.map(async policy => {
  const descriptor = sample.runs.find(run => run.policy === policy);
  assert.ok(descriptor, `${policy} must be a physical recorded run`);
  const response = await api.request.get(base + descriptor.data_url);
  const bytes = await response.body();
  assert.equal(createHash('sha256').update(bytes).digest('hex'), descriptor.sha256);
  const record = JSON.parse(bytes);
  assert.equal(record.used_bins_after.length, 5000);
  return record;
}));
report.sample = { instance_id: sample.instance_id, split: sample.split,
  runs: sample.runs.filter(run => policies.includes(run.policy)).map(({ policy, run_id, sha256, data_url }) => ({ policy, run_id, sha256, data_url })) };
await api.close();
const replayUrl = t => `${base}/#/replay/${sample.instance_id}?a=BF&b=BF_then_EoH&t=${t}&view=observed`;
const configurations = [
  { name: '360x800-touch', width: 360, height: 800, mobile: true },
  { name: '390x844-touch', width: 390, height: 844, mobile: true },
  { name: '430x932-touch', width: 430, height: 932, mobile: true },
  { name: '844x390-landscape-touch', width: 844, height: 390, mobile: true },
  { name: '900x1366-portrait-touch', width: 900, height: 1366, mobile: false },
  { name: '390x844-reduced-motion', width: 390, height: 844, mobile: true, reduced: true },
].filter(configuration => filter === 'phone' ? configuration.width <= 430 && !configuration.reduced
  : !filter || configuration.name.includes(filter));

async function snapshot(page, name) {
  const filename = name + '.png';
  await page.screenshot({ path: path.join(output, filename) });
  report.screenshots.push(filename);
}

async function check(page, configuration, name, action) {
  if (!includesCheck(name)) return;
  try {
    const evidence = await action();
    report.checks.push({ viewport: configuration.name, name, status: 'PASS', evidence });
    console.log('PASS', configuration.name, name);
  } catch (error) {
    report.checks.push({ viewport: configuration.name, name, status: 'FAIL', error: String(error.message),
      url: page.url(), geometry: await geometry(page).catch(() => null), mainText: (await page.locator('main').innerText().catch(() => '')).slice(-4500) });
    await snapshot(page, `${configuration.name}-${name}-failure`);
    console.log('FAIL', configuration.name, name, error.message);
  }
}

async function ready(page, t = 500) {
  await page.goto(replayUrl(t), { waitUntil: 'networkidle' });
  await page.getByRole('slider', { name: '回放进度（已处理项数）' }).waitFor();
  await page.waitForFunction(expected => document.querySelector('[role="slider"]')?.getAttribute('aria-valuenow') === String(expected), t);
}

async function readCounts(page, processed) {
  await page.waitForFunction(expected => document.querySelector('[role="slider"]')?.getAttribute('aria-valuenow') === String(expected), processed);
  const labels = await page.locator('canvas[role="img"]').evaluateAll(elements => elements.map(element => element.getAttribute('aria-label')));
  assert.equal(labels.length, 2, 'Two real branch canvases must share one input position');
  const expectedBins = trajectories.map(run => processed ? run.used_bins_after[processed - 1] : 0);
  const actual = labels.map(label => {
    const match = label.match(/已处理 ([\d,]+) 项，(?:已用 ([\d,]+) 箱|已开 ([\d,]+) 个箱)/);
    assert.ok(match, `Missing readable replay facts: ${label}`);
    return { processed: Number(match[1].replaceAll(',', '')), usedBins: Number((match[2] ?? match[3]).replaceAll(',', '')), label };
  });
  for (let index = 0; index < actual.length; index++) {
    assert.equal(actual[index].processed, processed, `${policies[index]} must be synchronized`);
    assert.equal(actual[index].usedBins, expectedBins[index], `${policies[index]} readable count must match real used_bins_after at t=${processed}`);
  }
  return { processed, expectedBins, actual };
}

async function geometry(page) {
  return page.evaluate(() => {
    const rect = element => {
      const r = element.getBoundingClientRect();
      return { left: r.left, top: r.top, right: r.right, bottom: r.bottom, width: r.width, height: r.height };
    };
    const navs = [...document.querySelectorAll('nav[aria-label="主要视图"]')].filter(element => element.getBoundingClientRect().height > 0);
    const nav = navs.find(element => element.getBoundingClientRect().top > innerHeight / 2);
    const controls = [...document.querySelectorAll('main button, main [role="slider"], main input')].map(element => {
      const r = rect(element);
      const x = r.left + r.width / 2;
      const y = r.top + r.height / 2;
      const visible = x >= 0 && x < innerWidth && y >= 0 && y < innerHeight;
      const hit = visible ? document.elementFromPoint(x, y) : null;
      return { name: element.getAttribute('aria-label') || element.textContent.trim() || element.type,
        rect: r, inViewport: visible, centerReceivesPointer: !!hit && (hit === element || element.contains(hit)),
        coveredBy: visible && hit && !element.contains(hit) && hit !== element ? hit.outerHTML.slice(0, 160) : null,
        bottomNavOverlap: !!nav && r.bottom > nav.getBoundingClientRect().top && r.top < nav.getBoundingClientRect().bottom };
    });
    return { width: innerWidth, clientWidth: document.documentElement.clientWidth, scrollWidth: document.documentElement.scrollWidth,
      visualViewport: { width: visualViewport.width, height: visualViewport.height, scale: visualViewport.scale },
      scrollY, height: innerHeight, touchPoints: navigator.maxTouchPoints, coarsePointer: matchMedia('(pointer: coarse)').matches,
      reducedMotion: matchMedia('(prefers-reduced-motion: reduce)').matches,
      bottomNav: nav ? rect(nav) : null, controls,
      overflowingElements: [...document.querySelectorAll('main *')].map(element => ({ tag: element.tagName,
        class: element.getAttribute('class'), ...rect(element) })).filter(r => r.right > innerWidth + 1 && r.width > 0).slice(0, 15) };
  });
}

for (const configuration of configurations) {
  const context = await browser.newContext({ viewport: { width: configuration.width, height: configuration.height },
    hasTouch: true, isMobile: configuration.mobile, deviceScaleFactor: 2,
    reducedMotion: configuration.reduced ? 'reduce' : 'no-preference' });
  const page = await context.newPage();
  page.setDefaultTimeout(4500);
  const pageErrors = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  try {
    await ready(page);
    await snapshot(page, configuration.name + '-initial');

    await check(page, configuration, 'layout-and-navigation-occlusion', async () => {
      const positions = [];
      for (const scroll of [0, 0.5, 1]) {
        await page.evaluate(ratio => scrollTo(0, (document.documentElement.scrollHeight - innerHeight) * ratio), scroll);
        await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
        positions.push(await geometry(page));
      }
      await snapshot(page, configuration.name + '-controls-bottom');
      const overflows = positions.filter(position => position.scrollWidth > position.clientWidth + 1);
      const occluded = positions.flatMap(position => position.controls.filter(control => control.inViewport && control.bottomNavOverlap && !control.centerReceivesPointer));
      const partiallyCovered = positions.flatMap(position => position.controls.filter(control =>
        control.inViewport && position.bottomNav && control.bottomNavOverlap &&
        Math.min(control.rect.bottom, position.bottomNav.bottom) - Math.max(control.rect.top, position.bottomNav.top) > 1
      ).map(control => ({ name: control.name, coveredCssPixels: Math.min(control.rect.bottom, position.bottomNav.bottom) - Math.max(control.rect.top, position.bottomNav.top) })));
      // Store full diagnostics even when an assertion reports the concise finding.
      await writeFile(path.join(output, configuration.name + '-layout.json'), JSON.stringify(positions, null, 2));
      assert.equal(overflows.length, 0, `Document overflow: ${positions.map(position => `${position.clientWidth}/${position.scrollWidth}`).join(',')}`);
      assert.equal(occluded.length, 0, `Bottom navigation covers controls: ${occluded.map(control => control.name).join(', ')}`);
      assert.equal(partiallyCovered.length, 0, `Bottom navigation clips button edges: ${partiallyCovered.map(control => `${control.name} (${control.coveredCssPixels}px)`).join(', ')}`);
      return { positions, bottomNavControlsOccluded: occluded.length, partiallyCovered };
    });

    await check(page, configuration, 'touch-endpoints-real-branch-counts', async () => {
      const evidence = [];
      for (const t of [0, 499, 500, 501, 5000]) {
        const name = t === 5000 ? '5,000' : String(t);
        await page.getByRole('button', { name, exact: true }).tap();
        evidence.push(await readCounts(page, t));
      }
      return evidence;
    });

    // Separate CDP input client/page from Playwright's own touchscreen client.
    // Mixing them can suppress subsequent synthesized clicks despite pointerup.
    const dragPage = await context.newPage();
    if (includesCheck('touch-slider-drag')) await ready(dragPage, 5000);
    await check(dragPage, configuration, 'touch-slider-drag', async () => {
      const page = dragPage;
      const slider = page.getByRole('slider', { name: '回放进度（已处理项数）' });
      await slider.scrollIntoViewIfNeeded();
      const box = await slider.boundingBox();
      assert.ok(box);
      const session = await context.newCDPSession(page);
      const y = box.y + box.height / 2;
      const startX = box.x + box.width * 0.25;
      const endX = box.x + box.width * 0.67;
      const touch = x => [{ x, y, id: 1, radiusX: 3, radiusY: 3, force: 1 }];
      const scrollBefore = await page.evaluate(() => scrollY);
      await session.send('Input.dispatchTouchEvent', { type: 'touchStart', touchPoints: touch(startX) });
      for (let move = 1; move <= 6; move++) {
        await session.send('Input.dispatchTouchEvent', { type: 'touchMove', touchPoints: touch(startX + (endX - startX) * move / 6) });
      }
      await session.send('Input.dispatchTouchEvent', { type: 'touchEnd', touchPoints: [] });
      await page.evaluate(() => new Promise(resolve => requestAnimationFrame(resolve)));
      const processed = Number(await slider.getAttribute('aria-valuenow'));
      assert.ok(Math.abs(processed - 3350) <= 2, `Real touch drag expected t≈3350, received ${processed}; slider bounds ${JSON.stringify(box)}`);
      assert.equal(await page.evaluate(() => scrollY), scrollBefore, 'Slider gesture must seek instead of scroll page');
      return { bounds: box, pointerType: 'CDP touch input', ...await readCounts(page, processed) };
    });
    await dragPage.close();
    await page.bringToFront();

    await check(page, configuration, 'touch-play-pause', async () => {
      const slider = page.getByRole('slider', { name: '回放进度（已处理项数）' });
      const before = Number(await slider.getAttribute('aria-valuenow'));
      if (before >= 4990) await page.getByRole('button', { name: '501', exact: true }).tap();
      const start = Number(await slider.getAttribute('aria-valuenow'));
      await page.getByRole('button', { name: '播放', exact: true }).tap();
      await page.waitForFunction(t => Number(document.querySelector('[role="slider"]').getAttribute('aria-valuenow')) > t, start);
      await page.getByRole('button', { name: '暂停', exact: true }).tap();
      const paused = Number(await slider.getAttribute('aria-valuenow'));
      await page.waitForTimeout(250);
      assert.equal(Number(await slider.getAttribute('aria-valuenow')), paused, 'Pause must remain stable after touch');
      return { start, paused, ...await readCounts(page, paused) };
    });

    await check(page, configuration, 'touch-main-navigation-return', async () => {
      const slider = page.getByRole('slider', { name: '回放进度（已处理项数）' });
      const before = Number(await slider.getAttribute('aria-valuenow'));
      const navigation = page.locator('nav[aria-label="主要视图"]:visible').first();
      await navigation.getByRole('link', { name: '结果', exact: true }).tap();
      await page.waitForURL(url => url.hash === '#/');
      await page.locator('main[aria-label="结果总览"]').waitFor();
      await page.waitForLoadState('networkidle');
      await page.locator('nav[aria-label="主要视图"]:visible').first().getByRole('link', { name: '回放', exact: true }).tap();
      await page.getByRole('slider').waitFor();
      assert.ok(page.url().includes(sample.instance_id), 'Return must retain the real sample');
      const params = new URLSearchParams(new URL(page.url()).hash.split('?')[1]);
      assert.equal(params.get('a'), 'BF');
      assert.equal(params.get('b'), 'BF_then_EoH');
      await page.waitForFunction(t => Number(document.querySelector('[role="slider"]').getAttribute('aria-valuenow')) === t, before);
      return { sampleRestored: true, processed: before, bothBranchesRetained: true };
    });

    await check(page, configuration, 'same-stream-hash-position', async () => {
      const evidence = [];
      // A pasted link can change only t while preserving the mounted stream
      // and policy pair. The displayed state must follow that requested t.
      for (const t of [14, 500]) {
        await page.evaluate(hash => { location.hash = hash; }, new URL(replayUrl(t)).hash);
        evidence.push(await readCounts(page, t));
        const params = new URLSearchParams(new URL(page.url()).hash.split('?')[1]);
        assert.equal(params.get('t'), String(t));
      }
      return evidence;
    });

    if (configuration.reduced) await check(page, configuration, 'reduced-motion-paused-on-load', async () => {
      // Test a fresh document load, not a t-only hash navigation on the replay
      // left running/paused by the preceding interaction checks.
      await page.goto('about:blank');
      await ready(page, 500);
      const state = await geometry(page);
      assert.equal(state.reducedMotion, true);
      assert.equal(await page.getByRole('button', { name: '播放', exact: true }).count(), 1);
      await page.waitForTimeout(250);
      assert.equal(await page.getByRole('slider').getAttribute('aria-valuenow'), '500');
      const animations = await page.evaluate(() => document.getAnimations().map(animation => ({ playState: animation.playState, timing: animation.effect?.getComputedTiming().duration })));
      await snapshot(page, configuration.name + '-paused');
      return { reducedMotion: true, automaticallyPlaying: false, animations };
    });
    report.checks.push({ viewport: configuration.name, name: 'uncaught-page-errors', status: pageErrors.length ? 'FAIL' : 'PASS', errors: pageErrors });
  } catch (error) {
    report.checks.push({ viewport: configuration.name, name: 'load-real-replay', status: 'FAIL', error: String(error.stack || error) });
    await snapshot(page, configuration.name + '-load-failure');
  } finally { await context.close(); }
}
await browser.close();
report.status = report.checks.length && report.checks.every(check => check.status === 'PASS') ? 'PASS' : 'FAIL';
report.finishedAt = new Date().toISOString();
const reportFilter = [filter, checkFilter].filter(Boolean).join('-');
const filename = reportFilter ? `mobile-report-${reportFilter.replace(/[^a-z0-9-]/gi, '_')}.json` : 'mobile-report.json';
await writeFile(path.join(output, filename), JSON.stringify(report, null, 2));
console.log(JSON.stringify({ status: report.status, checks: report.checks.length,
  failures: report.checks.filter(check => check.status === 'FAIL').map(({ viewport, name, error }) => ({ viewport, name, error })) }, null, 2));
process.exitCode = report.status === 'PASS' ? 0 : 1;
