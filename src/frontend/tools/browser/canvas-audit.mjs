/** Inspect actual Canvas draw bounds against a real recorded run, without editing the product. */
import { chromium } from 'playwright';
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';
const base = process.argv[2] || 'http://127.0.0.1:5173';
const out = path.resolve('artifacts/codex-browser/canvas-audit');
await mkdir(out, { recursive: true });
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });
const errors = [];
page.on('pageerror', e => errors.push(e.message));
await page.addInitScript(() => {
  const state = new WeakMap();
  const proto = CanvasRenderingContext2D.prototype;
  const originalClear = proto.clearRect;
  const originalFill = proto.fillRect;
  proto.clearRect = function (...args) { state.set(this.canvas, { bars: 0, clipped: 0, maximumBottom: 0 }); return originalClear.apply(this, args); };
  proto.fillRect = function (x, y, w, h) {
    const info = state.get(this.canvas);
    if (info) {
      const transform = this.getTransform();
      const height = this.canvas.height / transform.d;
      const width = this.canvas.width / transform.a;
      info.bars++;
      if (y < 0 || y + h > height || x < 0 || x + w > width) info.clipped++;
      info.maximumBottom = Math.max(info.maximumBottom, y + h);
    }
    return originalFill.call(this, x, y, w, h);
  };
  window.__canvasAudit = canvas => state.get(canvas);
});
const report = { scope: 'Actual product Canvas bar drawing at recorded final state', base, startedAt: new Date().toISOString(), errors, cases: [] };
try {
  const response = await page.request.get(base + '/data/catalog.json');
  const catalog = await response.json();
  const stream = catalog.streams.reduce((best, stream) => stream.results.BF > best.results.BF ? stream : best);
  const descriptor = stream.runs.find(run => run.policy === 'BF');
  const record = await (await page.request.get(base + descriptor.data_url)).json();
  await page.goto(base + `/#/replay/${stream.instance_id}?a=BF&t=5000`, { waitUntil: 'networkidle' });
  await page.getByRole('slider').waitFor({ timeout: 10000 });
  await page.evaluate(() => new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve))));
  const drawing = await page.locator('canvas').first().evaluate(canvas => ({
    ...window.__canvasAudit(canvas), ariaLabel: canvas.getAttribute('aria-label'),
    cssWidth: canvas.clientWidth, cssHeight: canvas.clientHeight,
    width: canvas.width, height: canvas.height,
  }));
  report.cases.push({ instance: stream.instance_id, policy: 'BF', processed: 5000,
    expectedUsedBins: record.used_bins, largestAssignedSlot: Math.max(...record.assignment), drawing });
  await page.screenshot({ path: path.join(out, 'largest-real-run.png'), fullPage: true });
  report.status = !errors.length && drawing.clipped === 0 && drawing.bars === record.used_bins ? 'PASS' : 'FINDING';
} catch (error) { report.status = 'ERROR'; report.error = error.message; }
report.finishedAt = new Date().toISOString();
await writeFile(path.join(out, 'canvas-audit.json'), JSON.stringify(report, null, 2));
await browser.close();
console.log(JSON.stringify(report, null, 2));
process.exitCode = report.status === 'PASS' ? 0 : 1;
