// Happy editor (merged a1d07b16).
import { test, expect, shot, openAgriCatalog, firstRunnablePattern } from './helpers';
test('I 地图编辑器：框选+批量平移、米制数值输入、几何校验定位', async ({ page }, info) => {
  await openAgriCatalog(page);
  const { card } = await firstRunnablePattern(page);
  await card.getByRole('button', { name: '校验并导入任务规划' }).click();
  await expect(page).toHaveURL(/#\/plan\/.+/, { timeout: 60_000 });
  const map = page.locator('svg[aria-label="任务地图编辑器"]');
  await expect(map).toBeVisible({ timeout: 30_000 });
  const sel = page.getByLabel('选择与精确输入'); // SelectionPanel.tsx:56
  const tasks = map.locator('g[data-hit="task"]');
  await test.step('Alt+拖动框选多个任务', async () => {
    const b = (await map.boundingBox())!;
    await page.keyboard.down('Alt');
    await page.mouse.move(b.x + b.width * 0.2, b.y + b.height * 0.15);
    await page.mouse.down();
    await page.mouse.move(b.x + b.width * 0.8, b.y + b.height * 0.85, { steps: 15 });
    await page.mouse.up();
    await page.keyboard.up('Alt');
    await expect(sel.locator('summary')).toContainText(/已选 ([2-9]|\d{2,})/); // SelectionPanel.tsx:57
    await shot(page, info, 'marquee');
  });
  await test.step('批量平移 ΔX=1 ΔY=-1', async () => {
    const first = await tasks.first().getAttribute('transform');
    await sel.getByLabel('批量平移 X（米）').fill('1');
    await sel.getByLabel('批量平移 Y（米）').fill('-1');
    await sel.getByRole('button', { name: '平移' }).click();
    await expect.poll(() => tasks.first().getAttribute('transform')).not.toBe(first);
    await shot(page, info, 'batch-moved');
  });
  await test.step('单选任务并米制输入 X', async () => {
    await sel.getByRole('button', { name: '清除' }).click();
    const t = (await tasks.first().boundingBox())!;
    await page.mouse.click(t.x + t.width / 2, t.y + t.height / 2);
    const x = sel.getByLabel('X（米）');
    await x.fill('abc'); await x.press('Enter');
    await expect(x).not.toHaveValue('abc'); // invalid reverts
    await x.fill('12.5'); await x.press('Enter');
    await expect(x).toHaveValue('12.5');
    await shot(page, info, 'metric-input');
  });
  await test.step('点击几何校验问题定位对象', async () => {
    const issues = page.getByLabel('几何校验').locator('button:not([disabled])'); // IssuesPanel.tsx:16
    test.skip(!(await issues.count()), 'no locatable geometry issue in this pattern');
    await issues.first().click();
    await expect(issues.first()).toHaveAttribute('aria-current', 'true');
    await expect(sel.locator('summary')).toContainText('已选 1');
    await shot(page, info, 'issue-located');
  });
});
