// DRAFT for Happy b7264ddd (not run on 03a4a998). Selectors to be confirmed against happy-editor source after merge.
import { test, expect, shot, openAgriCatalog, firstRunnablePattern } from '../tests/helpers';
async function openMap(page: any) {
  await openAgriCatalog(page);
  const { card } = await firstRunnablePattern(page);
  await card.getByRole('button', { name: '校验并导入任务规划' }).click();
  await expect(page).toHaveURL(/#\/plan\/.+/, { timeout: 60_000 });
  const map = page.locator('svg[aria-label="任务地图编辑器"]');
  await expect(map).toBeVisible({ timeout: 30_000 });
  return map;
}
async function dragBox(page: any, map: any) {
  const b = (await map.boundingBox())!;
  await page.mouse.move(b.x + b.width * 0.2, b.y + b.height * 0.15); await page.mouse.down();
  await page.mouse.move(b.x + b.width * 0.8, b.y + b.height * 0.85, { steps: 15 }); await page.mouse.up();
}
const multi = (page: any) => page.getByLabel('选择与精确输入').getByText(/已选 ([2-9]|\d{2,}) 项/);
test('J1 框选：工具栏按钮', async ({ page }, info) => {
  const map = await openMap(page);
  await page.getByRole('button', { name: /框选/ }).click();
  await dragBox(page, map); await expect(multi(page)).toBeVisible(); await shot(page, info, 'box-toolbar');
});
test('J2 框选：快捷键 B', async ({ page }, info) => {
  const map = await openMap(page);
  await map.click({ position: { x: 5, y: 5 } }); await page.keyboard.press('b');
  await dragBox(page, map); await expect(multi(page)).toBeVisible(); await shot(page, info, 'box-key-b');
});
test('J3 车辆参数问题跳转车队表单', async ({ page }, info) => {
  await openMap(page);
  const issue = page.getByLabel('几何校验').locator('button:not([disabled])').filter({ hasText: /车|容量|幅宽|车型/ });
  test.skip(!(await issue.count()), 'no vehicle-parameter issue in this pattern');
  await issue.first().click();
  await expect(page.getByRole('radio', { name: '车队' }).or(page.getByRole('button', { name: '车队', pressed: true }))).toBeVisible();
  await expect(page.locator(':focus')).toBeVisible(); await shot(page, info, 'fleet-form');
});
test('J4 窄视口侧栏布局 900px', async ({ page }, info) => {
  await page.setViewportSize({ width: 900, height: 900 });
  await openMap(page);
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
  expect(overflow, 'no horizontal overflow').toBeLessThanOrEqual(0);
  await expect(page.locator('svg[aria-label="任务地图编辑器"]')).toBeInViewport(); await shot(page, info, 'narrow');
});
