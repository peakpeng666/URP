import assert from 'node:assert/strict';
import fs from 'node:fs';
import { launchChrome, api, writeJson } from './cdp.mjs';
import { click, setInput, inputValue, waitForScenarioRuns, waitForFile, layoutEvidence, sleep } from './acceptance-lib.mjs';

const root = new URL('.', import.meta.url).pathname;
const fixtures = JSON.parse(fs.readFileSync(`${root}acceptance-fixtures.json`, 'utf8'));
const scenarioId = fixtures.fleet_scenario_id;
const downloadDir = `${root}downloads`;
const browser = await launchChrome({ profileDir: `${root}fleet-planning-profile-${Date.now()}`, downloadDir, width: 1440, height: 900 });
const { page } = browser;
const evidence = { scenario_id: scenarioId, steps: {}, downloads: {}, layouts: [] };
const terminal = new Set(['done', 'error', 'timeout', 'canceled']);

async function openScenario() {
  await page.navigate(`http://127.0.0.1:4100/#/plan/${encodeURIComponent(scenarioId)}`);
  await page.waitFor("document.body.innerText.includes('推荐与求解') && !!document.querySelector('[data-hit=task][data-id=\"1\"] circle')", { timeoutMs: 30000 });
  await sleep(500);
}
async function selectDepot() {
  await click(page, '[data-hit=depot][data-id="0"] rect');
  await click(page, '[role=tab]', '检查器');
  await page.waitFor("document.body.innerText.includes('车库 D1')");
}
async function selectTask() {
  await click(page, '[data-hit=task][data-id="1"] circle');
  await click(page, '[role=tab]', '检查器');
  await page.waitFor("document.body.innerText.includes('任务点 B1')");
}
async function waitScenario(predicate, timeoutMs = 15000) {
  const deadline = Date.now() + timeoutMs;
  let current;
  while (Date.now() < deadline) {
    current = await api(`/lab/api/scenarios/${encodeURIComponent(scenarioId)}`);
    if (predicate(current)) return current;
    await sleep(250);
  }
  throw new Error(`Scenario predicate timed out: ${JSON.stringify(current?.instance?.depot)}`);
}

try {
  await openScenario();
  const original = await api(`/lab/api/scenarios/${encodeURIComponent(scenarioId)}`);
  assert.deepEqual(original.instance.depot, [2.75, 2.75]);

  await selectDepot();
  await setInput(page, 'X', '3');
  const saved = await waitScenario((sc) => sc.instance.depot?.[0] === 3 && sc.instance.depots?.[0]?.[0] === 3);
  evidence.steps.save = { depot: saved.instance.depot, depots: saved.instance.depots };
  await page.cdp.send('Page.reload', { ignoreCache: true });
  await page.waitFor("document.readyState === 'complete' && document.body.innerText.includes('推荐与求解')", { timeoutMs: 30000 });
  await sleep(600);
  await selectDepot();
  evidence.steps.reload = { x_input: await inputValue(page, 'X'), api: (await api(`/lab/api/scenarios/${encodeURIComponent(scenarioId)}`)).instance.depot };
  assert.equal(Number(evidence.steps.reload.x_input), 3);
  assert.equal(evidence.steps.reload.api[0], 3);
  await page.screenshot(`${root}fleet-save-reload.png`);

  await click(page, '[role=tab]', '推荐与求解');
  await click(page, 'input[type=checkbox]', '节约算法 + 2-opt');
  await setInput(page, '时间预算', '2');
  await setInput(page, '随机种子', '42');
  await page.waitFor("document.body.innerText.includes('对比 2 个算法')");
  await click(page, 'button', '对比 2 个算法');
  const first = await waitForScenarioRuns(scenarioId, 2);
  assert(first.every((run) => run.state === 'done' && run.check?.valid));
  assert.equal(new Set(first.map((run) => run.instance_sha256)).size, 1);
  assert(first.every((run) => run.params.time_limit_s === 2 && run.params.seed === 42));
  const firstJob = first[0].job_id;
  evidence.steps.first_solve = first.map((run) => ({ run_id: run.run_id, algorithm: run.algorithm.id, state: run.state, status: run.status, objective: run.objective, check: run.check?.valid, sha: run.instance_sha256, params: run.params }));
  await click(page, '[role=tab]', '验算');
  await page.waitFor("document.body.innerText.includes('全部通过') && document.body.innerText.includes('每个任务点恰好服务一次')");
  await page.screenshot(`${root}fleet-first-check.png`);

  await selectTask();
  await setInput(page, '作业时间', '2');
  await waitScenario((sc) => sc.instance.tasks.find((task) => task.id === 1)?.service_s === 2);
  await page.waitFor("document.body.innerText.includes('当前输入已修改，历史结果需重新求解')");
  const oldRuns = await Promise.all(first.map((run) => api(`/lab/api/runs/${run.run_id}`)));
  assert(oldRuns.every((run) => run.instance.tasks.find((task) => task.id === 1)?.service_s === 0));
  evidence.steps.stale = { old_service: oldRuns.map((run) => run.instance.tasks.find((task) => task.id === 1)?.service_s), current_service: 2 };
  await click(page, '[role=tab]', '地图');
  await page.screenshot(`${root}fleet-stale.png`);
  await click(page, 'button', '查看冻结输入');
  await page.waitFor("document.body.innerText.includes('历史运行冻结输入')");
  await page.screenshot(`${root}fleet-frozen-input.png`);
  await click(page, 'button', '返回当前草稿');

  await click(page, '[role=tab]', '推荐与求解');
  await click(page, 'input[type=checkbox]', 'OR-Tools 车队调度');
  await setInput(page, '时间预算', '30');
  await page.waitFor("document.body.innerText.includes('求解') && !document.body.innerText.includes('对比 2 个算法')");
  await click(page, 'button', '求解');
  const canceled = await waitForScenarioRuns(scenarioId, 1, new Set([firstJob]), 10000).catch(async () => {
    const payload = await api(`/lab/api/runs?scenario_id=${encodeURIComponent(scenarioId)}&limit=5`);
    const run = payload.runs[0];
    if (run && !terminal.has(run.state)) return [run];
    throw new Error('No cancellable run appeared');
  });
  const cancelId = canceled[0].run_id;
  await click(page, '[role=tab]', '方案对比');
  await page.waitFor("[...document.querySelectorAll('button')].some((el) => el.innerText.includes('取消') && !el.disabled)");
  await click(page, 'button', '取消');
  const cancelDeadline = Date.now() + 15000;
  let canceledRun;
  while (Date.now() < cancelDeadline) {
    canceledRun = await api(`/lab/api/runs/${cancelId}`);
    if (canceledRun.state === 'canceled') break;
    await sleep(250);
  }
  assert.equal(canceledRun.state, 'canceled');
  evidence.steps.cancel = { run_id: cancelId, state: canceledRun.state, status: canceledRun.status, process: canceledRun.process };
  await page.screenshot(`${root}fleet-canceled.png`);

  await click(page, 'tr', 'PyVRP 固定车队');
  await click(page, '[role=tab]', '实验结果');
  await page.waitFor("document.body.innerText.includes('方案已取消') && document.body.innerText.includes('导出实验记录')");
  await click(page, 'button', '导出实验记录');
  const canceledRecord = await waitForFile(downloadDir, (name) => name.includes(cancelId) && name.endsWith('.json'));
  const canceledEnvelope = JSON.parse(fs.readFileSync(canceledRecord, 'utf8'));
  assert.equal(canceledEnvelope.record.run_id, cancelId);
  evidence.downloads.canceled = canceledRecord;
  await page.screenshot(`${root}fleet-canceled-export.png`);

  await click(page, '[role=tab]', '推荐与求解');
  await click(page, 'input[type=checkbox]', 'OR-Tools 车队调度');
  await setInput(page, '时间预算', '2');
  await page.waitFor("document.body.innerText.includes('对比 2 个算法')");
  await click(page, 'button', '对比 2 个算法');
  const finalRuns = await waitForScenarioRuns(scenarioId, 2, new Set([firstJob, canceledRun.job_id]));
  assert(finalRuns.every((run) => run.state === 'done' && run.check?.valid));
  assert(finalRuns.every((run) => run.instance.tasks.find((task) => task.id === 1)?.service_s === 2));
  assert(finalRuns.every((run) => run.params.time_limit_s === 2 && run.params.seed === 42));
  assert.notEqual(finalRuns[0].instance_sha256, first[0].instance_sha256);
  const executeRun = finalRuns.find((run) => run.algorithm.id === 'pyvrp.fleet') ?? finalRuns[0];
  evidence.steps.final_solve = finalRuns.map((run) => ({ run_id: run.run_id, job_id: run.job_id, algorithm: run.algorithm.id, state: run.state, status: run.status, objective: run.objective, check: run.check?.valid, sha: run.instance_sha256, params: run.params }));
  evidence.execute_run_id = executeRun.run_id;

  await click(page, 'tr', 'PyVRP 固定车队');
  await click(page, '[role=tab]', '验算');
  await page.waitFor("document.body.innerText.includes('全部通过')");
  await page.screenshot(`${root}fleet-final-check.png`);
  await click(page, '[role=tab]', '实验结果');
  await page.waitFor("document.body.innerText.includes('导出实验记录')");
  for (const [width, height] of [[1440, 900], [1024, 768], [620, 900]]) {
    await page.setViewport(width, height);
    await sleep(400);
    const layout = await layoutEvidence(page);
    evidence.layouts.push({ width, height, ...layout });
    assert.equal(layout.documentWidth, width);
    for (const button of layout.buttons.filter((item) => item.text.includes('导出实验记录'))) {
      assert(button.left >= 0 && button.right <= width, `Export button out of viewport at ${width}: ${JSON.stringify(button)}`);
    }
    await page.screenshot(`${root}fleet-layout-${width}.png`);
  }
  await page.setViewport(1440, 900);
  evidence.console = page.console;
  evidence.exceptions = page.exceptions;
  evidence.httpErrors = page.httpErrors;
  writeJson(`${root}fleet-planning-result.json`, evidence);
  console.log(JSON.stringify({ execute_run_id: executeRun.run_id, first: evidence.steps.first_solve, final: evidence.steps.final_solve, cancel: evidence.steps.cancel, layouts: evidence.layouts.map((x) => ({ width: x.width, documentWidth: x.documentWidth, map: x.map, buttons: x.buttons })) }, null, 2));
} catch (error) {
  evidence.error = String(error?.stack ?? error);
  evidence.console = page.console;
  evidence.exceptions = page.exceptions;
  evidence.httpErrors = page.httpErrors;
  writeJson(`${root}fleet-planning-result.json`, evidence);
  await page.screenshot(`${root}fleet-planning-error.png`).catch(() => {});
  throw error;
} finally {
  await browser.close();
}
