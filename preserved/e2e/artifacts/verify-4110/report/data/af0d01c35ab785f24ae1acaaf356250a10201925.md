# Instructions

- Following Playwright test failed.
- Explain why, be concise, respect Playwright best practices.
- Provide a snippet of code with the fix, if possible.

# Test info

- Name: smoke.spec.mjs >> agri catalog + flow
- Location: tests/smoke.spec.mjs:29:1

# Error details

```
Test timeout of 240000ms exceeded.
```

```
Error: locator.fill: Test timeout of 240000ms exceeded.
Call log:
  - waiting for locator('details').filter({ has: locator('input[aria-label$=" 障碍半径"]') }).first().locator('input[aria-label$=" 障碍半径"]')
    - locator resolved to <input min="0" max="40" step="any" value="12" type="number" aria-label="果园采收集运 障碍半径" class="_input_a5ga1_358"/>
    - fill("40")
  - attempting fill action
    2 × waiting for element to be visible, enabled and editable
      - element is not visible
    - retrying fill action
    - waiting 20ms
    2 × waiting for element to be visible, enabled and editable
      - element is not visible
    - retrying fill action
      - waiting 100ms
    433 × waiting for element to be visible, enabled and editable
        - element is not visible
      - retrying fill action
        - waiting 500ms

```

# Test source

```ts
  3   | const ART = process.env.ART || 'artifacts/run';
  4   | const shots = ART + '/shots'; fs.mkdirSync(shots, { recursive: true });
  5   | const log = {};
  6   | function watch(page, key) {
  7   |   const r = log[key] = { console: [], failed: [], http: [] };
  8   |   page.on('console', (m) => { if (m.type() === 'error') r.console.push(m.text().slice(0, 300)); });
  9   |   page.on('pageerror', (e) => r.console.push('pageerror: ' + e.message.slice(0, 300)));
  10  |   page.on('requestfailed', (q) => r.failed.push(q.method() + ' ' + q.url() + ' ' + q.failure()?.errorText));
  11  |   page.on('response', (s) => { if (s.status() >= 400) r.http.push(s.status() + ' ' + s.request().method() + ' ' + s.url()); });
  12  |   return r;
  13  | }
  14  | test.afterAll(() => fs.writeFileSync(ART + '/errors.json', JSON.stringify(log, null, 2)));
  15  | for (const [name, hash] of [['home', '#/'], ['plan', '#/plan'], ['assets', '#/assets'], ['sim', '#/sim'], ['jobs', '#/jobs'], ['bpp', '#/bpp']]) {
  16  |   test('route ' + name, async ({ page }) => {
  17  |     const r = watch(page, name);
  18  |     await page.goto('/' + hash); await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
  19  |     await page.waitForTimeout(1500);
  20  |     await page.screenshot({ path: `${shots}/${name}.png`, fullPage: true });
  21  |     expect(r.console.filter((t) => t.startsWith('pageerror')), 'uncaught page errors').toEqual([]);
  22  |   });
  23  | }
  24  | async function openCatalog(page) {
  25  |   await page.goto('/#/'); await page.reload(); await page.getByRole('button', { name: '打开农业任务目录' }).click();
  26  |   await page.locator('details').first().waitFor();
  27  | }
  28  | const cardWith = (page, suffix) => page.locator('details').filter({ has: page.locator(`input[aria-label$=" ${suffix}"]`) }).first();
  29  | test('agri catalog + flow', async ({ page }) => { test.setTimeout(240000);
  30  |   const r = watch(page, 'agri');
  31  |   await openCatalog(page); await page.screenshot({ path: `${shots}/agri-catalog.png`, fullPage: true });
  32  |   const card = cardWith(page, '任务点数'); await card.locator('summary').click();
  33  |   await card.screenshot({ path: `${shots}/agri-card-open.png` });
  34  |   const preview = card.getByRole('img', { name: /几何预览/ });
  35  |   const hasPreview = await preview.count();
  36  |   test.info().annotations.push({ type: 'preview', description: String(hasPreview) });
  37  |   if (hasPreview) {
  38  |     await expect(preview).toContainText('原点 (0,0)'); await expect(preview).toContainText(/\d+ m/);
  39  |     await expect(card.getByRole('group', { name: '图层' }).locator('input[type=checkbox]')).toHaveCount(5);
  40  |     await expect(card.locator('figcaption')).toContainText('图例');
  41  |     await card.getByRole('group', { name: '图层' }).getByLabel('服务对象').uncheck();
  42  |     await card.screenshot({ path: `${shots}/agri-preview-layer-off.png` });
  43  |     await card.getByRole('group', { name: '图层' }).getByLabel('服务对象').check();
  44  |   }
  45  |   // draft
  46  |   const nm = (await card.locator('input[aria-label$=" 任务点数"]').getAttribute('aria-label')).replace(/ 任务点数$/, '');
  47  |   await card.locator('input[aria-label$=" 任务点数"]').fill('7');
  48  |   await card.locator('input[aria-label$=" 随机种子"]').fill('123');
  49  |   await page.waitForTimeout(800);
  50  |   await page.reload(); await page.goto('/#/plan'); await page.waitForTimeout(500);
  51  |   await openCatalog(page);
  52  |   const c2 = page.locator('details').filter({ has: page.locator(`input[aria-label="${nm} 任务点数"]`) }).first();
  53  |   await c2.locator('summary').click();
  54  |   const restoredN = await c2.locator(`input[aria-label="${nm} 任务点数"]`).inputValue();
  55  |   const restoredSeed = await c2.locator(`input[aria-label="${nm} 随机种子"]`).inputValue();
  56  |   test.info().annotations.push({ type: 'draft-restored', description: `${restoredN}/${restoredSeed}` });
  57  |   await c2.screenshot({ path: `${shots}/agri-draft-restored.png` });
  58  |   const reset = c2.getByRole('button', { name: '清除草稿并恢复默认' });
  59  |   if (await reset.count()) {
  60  |     await reset.click();
  61  |     test.info().annotations.push({ type: 'after-reset', description: `${await c2.locator(`input[aria-label="${nm} 任务点数"]`).inputValue()}/${await c2.locator(`input[aria-label="${nm} 随机种子"]`).inputValue()}` });
  62  |     await c2.screenshot({ path: `${shots}/agri-draft-reset.png` });
  63  |   }
  64  |   // import + solve
  65  |   await c2.getByRole('button', { name: '校验并导入任务规划', exact: true }).click();
  66  |   await page.waitForURL((u) => u.hash.startsWith('#/plan/agri-'), { timeout: 20000 });
  67  |   const id = decodeURIComponent(new URL(page.url()).hash.slice('#/plan/'.length));
  68  |   await page.waitForTimeout(2000); await page.screenshot({ path: `${shots}/agri-imported-plan.png`, fullPage: true });
  69  |   const solve = page.getByRole('button', { name: /求解|运行/ }).first();
  70  |   test.info().annotations.push({ type: 'scenario', description: id });
  71  |   if (await solve.count()) {
  72  |     await solve.click(); await page.waitForTimeout(15000);
  73  |     await page.screenshot({ path: `${shots}/agri-after-solve.png`, fullPage: true });
  74  |   } else test.info().annotations.push({ type: 'solve', description: 'no solve button found' });
  75  |   // last-import link
  76  |   await openCatalog(page);
  77  |   const c3 = page.locator('details').filter({ has: page.locator(`input[aria-label="${nm} 任务点数"]`) }).first();
  78  |   await c3.locator('summary').click();
  79  |   const notice = c3.getByText(/上次导入为/);
  80  |   test.info().annotations.push({ type: 'last-import-notice', description: String(await notice.count()) });
  81  |   if (await notice.count()) {
  82  |     await expect(c3.getByText(/再次导入会新建一个场景/)).toBeVisible();
  83  |     const href = await c3.locator(`a[href="#/plan/${encodeURIComponent(id)}"]`).count();
  84  |     test.info().annotations.push({ type: 'last-import-link-matches', description: String(href) });
  85  |   }
  86  |   await page.waitForTimeout(1500);
  87  |   test.info().annotations.push({ type: 'manual-edit-diff', description: (await c3.getByText(/手工编辑/).allInnerTexts()).join(' | ').slice(0, 400) });
  88  |   const refill = c3.getByRole('button', { name: '用该场景的参数和种子填回表单' });
  89  |   test.info().annotations.push({ type: 'refill-button', description: String(await refill.count()) });
  90  |   if (await refill.count()) { await refill.click(); await page.waitForTimeout(300);
  91  |     test.info().annotations.push({ type: 'after-refill', description: `${await c3.locator(`input[aria-label="${nm} 任务点数"]`).inputValue()}/${await c3.locator(`input[aria-label="${nm} 随机种子"]`).inputValue()}` }); }
  92  |   await c3.screenshot({ path: `${shots}/agri-last-import.png` });
  93  |   // preflight: coverage headland < swath
  94  |   const cov = cardWith(page, '地头宽度'); await cov.locator('summary').click();
  95  |   await cov.locator('input[aria-label$=" 地头宽度"]').fill('1');
  96  |   await page.waitForTimeout(500);
  97  |   const issues = cov.getByRole('list', { name: '预检问题' }).getByRole('button');
  98  |   test.info().annotations.push({ type: 'coverage-issues', description: (await issues.allInnerTexts()).join(' | ') });
  99  |   if (await issues.count()) await issues.first().click();
  100 |   await cov.screenshot({ path: `${shots}/agri-preflight-headland.png` });
  101 |   // preflight: obstacle radius huge in a fleet card
  102 |   const ob = cardWith(page, '障碍半径'); await ob.locator('summary').click();
> 103 |   await ob.locator('input[aria-label$=" 障碍半径"]').fill('40'); await page.waitForTimeout(500);
      |                                                  ^ Error: locator.fill: Test timeout of 240000ms exceeded.
  104 |   const iss2 = ob.getByRole('list', { name: '预检问题' }).getByRole('button');
  105 |   test.info().annotations.push({ type: 'obstacle-issues', description: (await iss2.allInnerTexts()).join(' | ').slice(0, 400) });
  106 |   if (await iss2.count()) { await iss2.first().click(); await page.waitForTimeout(300);
  107 |     test.info().annotations.push({ type: 'issue-click-status', description: (await ob.getByRole('status').allInnerTexts()).join(' | ') }); }
  108 |   await ob.screenshot({ path: `${shots}/agri-preflight-obstacle.png` });
  109 |   const built = await ob.getByText(/当前参数无法生成预览/).allInnerTexts();
  110 |   if (built.length) test.info().annotations.push({ type: 'obstacle-build-error', description: built.join(' ') });
  111 | });
  112 | 
```