import { test, expect, shot, openAgriCatalog } from './helpers';
// Luna 9dfd4e09: catalog precheck (no import). Click issue in ul[aria-label=预检问题] (PreviewMap.tsx:49-50) →
// target highlighted ([data-picked]) and param <label data-located> (AgriCatalog.tsx:157) input focused.
test('H 预检定位：点击预检问题高亮对象并聚焦表单字段', async ({ page }, info) => {
  const catalog = await openAgriCatalog(page);
  const card = catalog.locator('details', { has: page.locator('summary', { hasText: '行间机械除草' }) }).first();
  await card.locator('summary').click();
  await test.step('地头宽度设为小于幅宽', async () => {
    // aria-label is `${p.name} ${param.label}`; name has （固定行向覆盖近似）. 地头宽 must stay ≥ 最小转弯半径 (5 m) or the preview
    // errors out with no 预检问题 list (run8 dry-run), so widen 幅宽: 12 行 × 0.6 m = 7.2 m, 地头宽 6 m (preview.ts:82 warning).
    await card.getByLabel(/^行间机械除草.* 每趟行数$/).fill('12');
    const hw = card.getByLabel(/^行间机械除草.* 地头宽度$/);
    await hw.fill('6'); await hw.blur();
    await shot(page, info, 'headland-6m-swath-7.2m');
  });
  const issue = card.locator('ul[aria-label="预检问题"]').getByRole('button', { name: /地头宽.*小于.*幅宽/ });
  await test.step('预检问题出现', async () => { await expect(issue).toBeVisible({ timeout: 10_000 }); });
  await test.step('点击问题 → 高亮对象 + 聚焦地头宽度', async () => {
    await issue.click();
    await expect(card.locator('[data-picked]').first()).toBeAttached();
    // locateIssue focuses keys[0]=headland_width (AgriCatalog.tsx:93-98) but issueFields also marks 行距/每趟行数/机具宽度
    // (preview.ts:101), which precede 地头宽度 in DOM. Hard: focused input is 地头宽度 and is [data-located].
    const hw = card.getByLabel(/^行间机械除草.* 地头宽度$/);
    await expect(hw).toBeFocused();
    await expect(card.locator('label[data-located]', { has: page.locator('input[aria-label$=" 地头宽度"]') })).toContainText('地头宽');
    // Spec as written: the FIRST [data-located] field is focused and its label is 地头宽 — soft, so the gap is recorded.
    await expect.soft(page.locator('[data-located] input, [data-located] select').first(), 'first located field focused').toBeFocused();
    await expect.soft(page.locator('label[data-located]').first(), 'first located label is 地头宽').toContainText('地头宽');
    await shot(page, info, 'located');
  });
  await test.step('点击地图形状只高亮不定位', async () => {
    await page.locator('body').click({ position: { x: 1, y: 1 } });
    await card.locator('[data-target="boundary"]').click({ force: true });
    await expect(card.locator('[data-target="boundary"][data-picked]')).toBeAttached();
    await shot(page, info, 'shape-highlight');
  });
});
