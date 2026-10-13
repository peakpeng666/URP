// Browser-level page zoom, deliberately distinguished from CSS, DPR and pinch zoom.
// Only an isolated temporary Chromium profile/extension is used; no user profile changes.
// Sources: https://playwright.dev/docs/chrome-extensions
// https://developer.chrome.com/docs/extensions/reference/api/tabs#method-setZoom
import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import { mkdir, mkdtemp, writeFile, rm } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';

const base = process.argv[2] || 'http://127.0.0.1:4174';
const output = path.resolve(process.argv[3] || 'artifacts/codex-browser/browser-zoom');
const target = new URL(base);
assert.ok(['127.0.0.1', 'localhost', '[::1]'].includes(target.hostname), 'Only a local verification page is allowed');
await mkdir(output, { recursive: true });
const scratch = await mkdtemp(path.join(os.tmpdir(), 'bpp-browser-zoom-'));
const extension = path.join(scratch, 'extension');
await mkdir(extension);
await writeFile(path.join(extension, 'manifest.json'), JSON.stringify({
  manifest_version: 3, name: 'BPP isolated browser zoom verifier', version: '1.0.0',
  permissions: ['tabs'], background: { service_worker: 'background.js' },
}));
await writeFile(path.join(extension, 'background.js'), 'chrome.runtime.onInstalled.addListener(() => {});\n');

const report = {
  status: 'RUNNING', startedAt: new Date().toISOString(), base,
  scope: 'Actual Chromium page zoom via chrome.tabs API, with CSS/DPR/pinch controls; not manual toolbar clicking',
  environment: 'Headless bundled Chromium in an isolated temporary persistent profile',
  methodologySources: ['https://playwright.dev/docs/chrome-extensions', 'https://developer.chrome.com/docs/extensions/reference/api/tabs#method-setZoom'],
  states: {}, screenshots: [], consoleErrors: [], externalRequests: [],
  limitations: ['Browser API sets the actual tab zoom; toolbar menu was not physically clicked', 'Not a physical phone or native Ubuntu test'],
};
let context;

async function layout(page) {
  await page.evaluate(() => document.fonts.ready);
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  return page.evaluate(() => ({
    innerWidth, innerHeight, outerWidth, outerHeight, devicePixelRatio,
    visualViewport: { width: visualViewport.width, height: visualViewport.height, scale: visualViewport.scale },
    documentClientWidth: document.documentElement.clientWidth,
    documentScrollWidth: document.documentElement.scrollWidth,
    cssZoom: getComputedStyle(document.documentElement).zoom,
    atMost720CssPixels: matchMedia('(max-width: 720px)').matches,
    title: document.title, bodyTextLength: document.body.innerText.length,
  }));
}

async function capture(page, name, extra = {}) {
  const state = { ...await layout(page), ...extra };
  report.states[name] = state;
  return state;
}

try {
  context = await chromium.launchPersistentContext(path.join(scratch, 'profile'), {
    channel: 'chromium', headless: true, viewport: null,
    args: ['--window-size=1366,900', `--disable-extensions-except=${extension}`, `--load-extension=${extension}`],
  });
  report.browserVersion = context.browser().version();
  const worker = context.serviceWorkers()[0] || await context.waitForEvent('serviceworker', { timeout: 15000 });
  const page = await context.newPage();
  page.on('pageerror', error => report.consoleErrors.push(String(error)));
  page.on('request', request => {
    if (/^https?:/.test(request.url()) && new URL(request.url()).origin !== target.origin) report.externalRequests.push(request.url());
  });
  await page.goto(base, { waitUntil: 'networkidle' });
  if (target.hash.startsWith('#/replay/')) await page.getByRole('slider').waitFor({ timeout: 15000 });
  const currentUrl = page.url();
  const setZoom = zoom => worker.evaluate(async ({ currentUrl, zoom }) => {
    const tab = (await chrome.tabs.query({})).find(tab => tab.url === currentUrl);
    if (!tab) throw new Error(`No tab found for ${currentUrl}`);
    await chrome.tabs.setZoomSettings(tab.id, { mode: 'automatic', scope: 'per-tab' });
    await chrome.tabs.setZoom(tab.id, zoom);
    return { tabId: tab.id, tabZoom: await chrome.tabs.getZoom(tab.id), zoomSettings: await chrome.tabs.getZoomSettings(tab.id) };
  }, { currentUrl, zoom });
  const getZoom = () => worker.evaluate(async currentUrl => {
    const tab = (await chrome.tabs.query({})).find(tab => tab.url === currentUrl);
    return chrome.tabs.getZoom(tab.id);
  }, currentUrl);
  const original = await capture(page, 'browser100', await setZoom(1));
  assert.equal(original.tabZoom, 1);

  const cdp = await context.newCDPSession(page);
  // Verify native page zoom first, before comparison controls can affect app layout.
  const zoomed = await capture(page, 'browser200', await setZoom(2));
  assert.equal(zoomed.tabZoom, 2);
  assert.equal(zoomed.cssZoom, '1');
  assert.ok(Math.abs(zoomed.devicePixelRatio / original.devicePixelRatio - 2) < 0.01, 'Browser zoom must double DPR');
  assert.ok(Math.abs(zoomed.innerWidth * 2 - original.innerWidth) <= 2, 'Browser zoom must halve layout viewport');
  assert.equal(zoomed.visualViewport.scale, 1, 'Browser page zoom must be distinct from pinch zoom');
  // Playwright fullPage temporarily emulates metrics and can crop native page zoom.
  // A raw viewport capture keeps the browser's actual zoom/viewport untouched.
  const nativeScreenshot = await cdp.send('Page.captureScreenshot', { format: 'png', fromSurface: true, captureBeyondViewport: false });
  const screenshotBytes = Buffer.from(nativeScreenshot.data, 'base64');
  await writeFile(path.join(output, 'browser-zoom-200.png'), screenshotBytes);
  report.screenshots.push('browser-zoom-200.png');
  report.nativeScreenshot = { method: 'CDP Page.captureScreenshot, no clipping or emulated metrics',
    width: screenshotBytes.readUInt32BE(16), height: screenshotBytes.readUInt32BE(20) };
  report.browser200Layout = {
    noHorizontalOverflow: zoomed.documentScrollWidth <= zoomed.innerWidth + 1,
    overflowingElements: await page.evaluate(() => [...document.querySelectorAll('body *')].map(element => {
      const rectangle = element.getBoundingClientRect();
      return { tag: element.tagName, class: element.getAttribute('class'), right: rectangle.right,
        width: rectangle.width, text: element.textContent?.trim().slice(0, 80) };
    }).filter(element => element.right > innerWidth + 1 && element.width > 0).slice(0, 25)),
  };

  if (target.hash.startsWith('#/replay/')) {
    const slider = page.getByRole('slider');
    await slider.scrollIntoViewIfNeeded();
    await slider.focus();
    const start = Number(await slider.getAttribute('aria-valuenow'));
    await page.keyboard.press('ArrowRight');
    await page.waitForFunction(t => Number(document.querySelector('[role="slider"]').getAttribute('aria-valuenow')) === t, start + 1);
    await page.keyboard.press('ArrowLeft');
    await page.waitForFunction(t => Number(document.querySelector('[role="slider"]').getAttribute('aria-valuenow')) === t, start);
    const after = await layout(page);
    assert.ok(after.documentScrollWidth <= after.innerWidth + 1, 'Controls must remain usable without horizontal overflow at 200%');
    report.browser200Interaction = { status: 'PASS', startingPosition: start, steps: [start + 1, start], actualTabZoom: await getZoom() };
  }

  await setZoom(1);
  const restored = await capture(page, 'restored100', { tabZoom: await getZoom() });
  assert.equal(restored.innerWidth, original.innerWidth);
  assert.equal(restored.devicePixelRatio, original.devicePixelRatio);

  // Keyboard events dispatched into headless content may not trigger browser chrome.
  await page.keyboard.press('Control+0');
  for (let index = 0; index < 5; index++) await page.keyboard.press('Control+Equal');
  await capture(page, 'keyboardCtrlPlusFiveTimes', { tabZoom: await getZoom() });
  await setZoom(1);
  await page.evaluate(() => { document.documentElement.style.zoom = '2'; });
  await capture(page, 'cssZoom200', { tabZoom: await getZoom() });
  await page.evaluate(() => { document.documentElement.style.removeProperty('zoom'); });
  await cdp.send('Emulation.setPageScaleFactor', { pageScaleFactor: 2 });
  await capture(page, 'cdpPinch200', { tabZoom: await getZoom() });
  await cdp.send('Emulation.setPageScaleFactor', { pageScaleFactor: 1 });

  // Explicit deviceScaleFactor comparison runs in a separate ordinary context.
  const dprBrowser = await chromium.launch({ headless: true });
  try {
    const dprPage = await dprBrowser.newPage({ viewport: { width: original.innerWidth, height: original.innerHeight }, deviceScaleFactor: 2 });
    await dprPage.goto(base, { waitUntil: 'networkidle' });
    await capture(dprPage, 'deviceScaleFactor2', { tabZoom: 'not changed by this control' });
  } finally { await dprBrowser.close(); }
  report.methodStatus = 'PASS';
  report.layoutStatus = report.browser200Layout.noHorizontalOverflow ? 'PASS' : 'FINDING';
  report.status = report.browser200Layout.noHorizontalOverflow ? 'PASS' : 'LAYOUT_FINDING';
} catch (error) {
  report.status = 'FAIL';
  report.error = String(error.stack || error);
} finally {
  if (context) await context.close();
  // This generated path is verified before recursive removal; no user profile is used.
  const safeParent = path.resolve(os.tmpdir());
  assert.equal(path.dirname(path.resolve(scratch)), safeParent);
  assert.ok(path.basename(scratch).startsWith('bpp-browser-zoom-'));
  await rm(scratch, { recursive: true, force: true });
  report.finishedAt = new Date().toISOString();
  await writeFile(path.join(output, 'browser-zoom.json'), JSON.stringify(report, null, 2));
}
console.log(JSON.stringify(report, null, 2));
if (report.status !== 'PASS') process.exitCode = 1;
