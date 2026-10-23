import { test, expect, shot, openAgriCatalog } from './helpers';
// Luna 9dfd4e09: catalog precheck (no import). Click issue in ul[aria-label=预检问题] (PreviewMap.tsx:49-50) →
// target highlighted ([data-picked]) and param <label data-located> (AgriCatalog.tsx:157) input focused.
test('H 预检定位：点击预检问题高亮对象并聚焦表单字段', async ({ page }, info) => {
  const catalog = await openAgriCatalog(page);
  const card = catalog.locator('details', { has: page.locator('summary', { hasText: '行间机械除草' }) }).first();
  await card.locator('summary').click();
  await test.step('地头宽度设为小于幅宽', async () => {
    const hw = card.getByLabel(/行间机械除草 地头宽度/);
    await hw.fill('1'); await hw.blur();
    await shot(page, info, 'headland-1m');
  });
  const issue = card.locator('ul[aria-label="预检问题"]').getByRole('button', { name: /地头宽.*小于.*幅宽/ });
  await test.step('预检问题出现', async () => { await expect(issue).toBeVisible({ timeout: 10_000 }); });
  await test.step('点击问题 → 高亮对象 + 聚焦地头宽度', async () => {
    await issue.click();
    await expect(card.locator('[data-picked]').first()).toBeAttached();
    const field = page.locator('[data-located] input, [data-located] select').first();
    await expect(field).toBeFocused();
    await expect(page.locator('label[data-located]').first()).toContainText('地头宽');
    await shot(page, info, 'located');
  });
  await test.step('点击地图形状只高亮不定位', async () => {
    await page.locator('body').click({ position: { x: 1, y: 1 } });
    await card.locator('[data-target="boundary"]').click({ force: true });
    await expect(card.locator('[data-target="boundary"][data-picked]')).toBeAttached();
    await shot(page, info, 'shape-highlight');
  });
});
