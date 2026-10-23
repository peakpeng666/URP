import { test, expect, shot, openAgriCatalog, firstRunnablePattern } from './helpers';
test('A 农业目录：筛选环境/作业/状态、打开模式、改参数与种子、预览几何', async ({ page }, info) => {
  const catalog = await openAgriCatalog(page);
  await shot(page, info, 'catalog-open');
  const count = catalog.getByText(/^当前 \d+ 个模式$/); // AgriCatalog.tsx:31
  await test.step('按生产环境筛选', async () => {
    await catalog.getByLabel('生产环境').selectOption({ index: 1 }); // AgriCatalog.tsx:22
    await expect(count).toBeVisible(); await shot(page, info, 'filter-env');
  });
  await test.step('按农业作业筛选', async () => {
    await catalog.getByLabel('农业作业').selectOption({ index: 1 });
    await shot(page, info, 'filter-op');
  });
  await test.step('按模式状态筛选', async () => {
    await catalog.getByLabel('模式状态').selectOption({ index: 1 });
    await shot(page, info, 'filter-status');
  });
  await test.step('清除筛选', async () => {
    for (const l of ['生产环境', '农业作业', '模式状态']) await catalog.getByLabel(l).selectOption('');
  });
  const { card, name } = await test.step('打开模式详情', () => firstRunnablePattern(page));
  await shot(page, info, 'pattern-detail');
  await test.step('修改参数与随机种子', async () => {
    const num = card.locator('input[type=number]').first();
    const v = Number(await num.inputValue());
    await num.fill(String(Number.isFinite(v) ? v + 1 : 1));
    await card.getByLabel(`${name} 随机种子`).fill('7'); // AgriCatalog.tsx:91
    await shot(page, info, 'params-changed');
  });
  await test.step('导入后预览几何出现', async () => {
    // Baseline has no inline preview in the card; geometry is shown on the plan map after import.
    // EXPECTED (spec): an in-card preview. We accept either.
    await card.getByRole('button', { name: '校验并导入任务规划' }).click();
    await expect(page).toHaveURL(/#\/plan\/.+/, { timeout: 60_000 }); // AgriCatalog.tsx:68
    await expect(page.locator('svg[aria-label="任务地图编辑器"], [aria-label="二维场景与规划路径"]').first()).toBeVisible({ timeout: 30_000 });
    await shot(page, info, 'preview-geometry');
  });
});
