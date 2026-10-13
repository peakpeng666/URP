import { chromium } from 'playwright';
import assert from 'node:assert/strict';
import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';

const base = process.argv[2] || 'http://127.0.0.1:5173';
const directory = path.resolve('artifacts/codex-browser');
await mkdir(directory, { recursive: true });
const sourcePath = path.resolve('src/replay/CurvePanel.tsx');
const sourceHash = async () => createHash('sha256').update(await readFile(sourcePath)).digest('hex');
const report = {
  scope: 'Two targeted actual-product CurvePanel checks only; read-only to product sources',
  base, startedAt: new Date().toISOString(), sourceSha256: await sourceHash(), checks: [], screenshots: [],
};
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1366, height: 900 } });
const pageErrors = [];
page.on('pageerror', (error) => pageErrors.push(error.message));
const fetchJSON = async (url) => {
  const response = await page.request.get(`${base}${url}`);
  assert.equal(response.status(), 200);
  return response.json();
};
const catalog = await fetchJSON('/data/catalog.json');
const navigate = async (instance, a, b, t) => {
  const query = new URLSearchParams({ a, t: String(t), view: 'observed' });
  if (b) query.set('b', b);
  await page.goto(`${base}/#/replay/${encodeURIComponent(instance)}?${query}`, { waitUntil: 'networkidle' });
  const slider = page.getByRole('slider', { name: '回放进度（已处理项数）' });
  await slider.waitFor({ timeout: 15000 });
  assert.equal(await slider.getAttribute('aria-valuenow'), String(t));
};
const curveFigure = (comparing) => page.locator('figure').filter({ has: page.locator('figcaption').filter({ hasText: comparing ? '累计箱数之差' : '累计已用箱数随已处理项数变化' }) });

try {
  const instance = 'confirmation_weibull_3_45_r0__descending';
  const stream = catalog.streams.find((stream) => stream.instance_id === instance);
  const run = await fetchJSON(stream.runs.find((run) => run.policy === 'BF').data_url);
  assert.equal(run.used_bins_after[9], 10);
  assert.equal(run.used_bins_after[13], 14);
  await navigate(instance, 'BF', null, 14);
  const figure = curveFigure(false);
  const geometry = await figure.locator('svg').evaluate((svg) => {
    const curve = svg.querySelector('path');
    const endpoint = curve.getPointAtLength(curve.getTotalLength());
    const bbox = curve.getBBox();
    const screen = new DOMPoint(endpoint.x, endpoint.y).matrixTransform(curve.getScreenCTM());
    const svgBounds = svg.getBoundingClientRect();
    const viewBox = svg.viewBox.baseVal;
    const svgPoint = new DOMPoint(screen.x, screen.y).matrixTransform(svg.getScreenCTM().inverse());
    return {
      path: curve.getAttribute('d'), pathEndpointInPlot: { x: endpoint.x, y: endpoint.y },
      pathBBoxInPlot: { x: bbox.x, y: bbox.y, width: bbox.width, height: bbox.height },
      endpointInSVG: { x: svgPoint.x, y: svgPoint.y },
      endpointInViewport: { x: screen.x, y: screen.y },
      svgBounds: { x: svgBounds.x, y: svgBounds.y, width: svgBounds.width, height: svgBounds.height },
      viewBox: { x: viewBox.x, y: viewBox.y, width: viewBox.width, height: viewBox.height },
      yAxisLabels: [...svg.querySelectorAll('text[text-anchor="end"]')].map((element) => element.textContent),
      svgOverflow: getComputedStyle(svg).overflow,
    };
  });
  const filename = 'curve-audit-BF-t14.png';
  await figure.scrollIntoViewIfNeeded();
  await page.screenshot({ path: path.join(directory, filename), fullPage: true });
  report.screenshots.push(filename);
  const insidePlot = geometry.pathEndpointInPlot.y >= -0.01 && geometry.pathEndpointInPlot.y <= 162.01;
  const insideSVG = geometry.endpointInSVG.y >= geometry.viewBox.y - 0.01
    && geometry.endpointInSVG.y <= geometry.viewBox.y + geometry.viewBox.height + 0.01;
  report.checks.push({
    name: 'nonsampled current endpoint remains within curve plot/SVG bounds',
    status: insidePlot && insideSVG ? 'PASS' : 'FAIL',
    evidence: { instance, policy: 'BF', processed: 14, actualUsedBinsAt10: run.used_bins_after[9], actualUsedBinsAt14: run.used_bins_after[13], insidePlot, insideSVG, geometry },
  });
  console.log(`${insidePlot && insideSVG ? 'PASS' : 'FAIL'} BF t14 endpoint: ${JSON.stringify(geometry.pathEndpointInPlot)}`);

  const risk = catalog.streams.filter((stream) => stream.split === 'risk');
  const group = risk.filter((stream) => stream.group_id === risk[0].group_id);
  const axes = [];
  let firstPrefix = null;
  for (const stream of group) {
    const run = await fetchJSON(stream.runs.find((run) => run.policy === 'SELECTOR').data_url);
    const prefix = run.items.slice(0, 500);
    if (firstPrefix) assert.deepEqual(prefix, firstPrefix, 'The selected risk group must have the same actual prefix');
    else firstPrefix = prefix;
    await navigate(stream.instance_id, 'SELECTOR', 'BF_then_EoH', 500);
    const figure = curveFigure(true);
    axes.push({ instance: stream.instance_id, processed: 500, labels: await figure.locator('svg text[text-anchor="end"]').allTextContents(), caption: await figure.locator('figcaption').innerText() });
  }
  const sameAxes = axes.length === 3 && axes[0].labels.length > 0 && axes.every((axis) => JSON.stringify(axis.labels) === JSON.stringify(axes[0].labels));
  report.checks.push({ name: 'same observed risk prefix has identical Y-axis scale despite different futures', status: sameAxes ? 'PASS' : 'FAIL', evidence: { group: group[0].group_id, verifiedIdenticalPrefixItems: firstPrefix.length, axes } });
  console.log(`${sameAxes ? 'PASS' : 'FAIL'} same-prefix observed risk Y-axis: ${JSON.stringify(axes.map((axis) => axis.labels))}`);
} catch (error) {
  report.checks.push({ name: 'targeted curve audit execution', status: 'FAIL', error: error.stack });
  console.error(error);
} finally {
  report.pageErrors = pageErrors;
  report.sourceSha256AtFinish = await sourceHash();
  report.sourceChangedDuringRun = report.sourceSha256AtFinish !== report.sourceSha256;
  report.finishedAt = new Date().toISOString();
  report.status = report.checks.every((check) => check.status === 'PASS') && pageErrors.length === 0 ? 'PASS' : 'FAIL';
  await writeFile(path.join(directory, 'curve-audit.json'), `${JSON.stringify(report, null, 2)}\n`);
  await browser.close();
  process.exitCode = report.status === 'PASS' ? 0 : 1;
}
