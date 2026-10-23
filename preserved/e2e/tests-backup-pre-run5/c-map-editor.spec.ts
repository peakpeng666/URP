import { test, expect, shot, openAgriCatalog, firstRunnablePattern } from './helpers';
test('C 地图编辑器：选择对象、拖拽、撤销/重做、数值输入', async ({ page }, info) => {
  await openAgriCatalog(page);
  const { card } = await firstRunnablePattern(page);
  await card.getByRole('button', { name: '校验并导入任务规划' }).click();
  await expect(page).toHaveURL(/#\/plan\/.+/, { timeout: 60_000 });
  const map = page.locator('svg[aria-label="任务地图编辑器"]'); // FieldEditor.tsx:320-321
  await expect(map).toBeVisible({ timeout: 30_000 });
  const undo = page.getByRole('button', { name: /撤销/ }); // PlanPanels.tsx:141 (title="撤销 (⌘Z)")
  const redo = page.getByRole('button', { name: /重做/ }); // PlanPanels.tsx:142
  const box = (await map.boundingBox())!;
  const xInput = page.locator('label', { has: page.locator('span', { hasText: /^X$/ }) }).locator('input[type=number]').first(); // PlanPanels.tsx:392-397
  await test.step('选择对象（点击地图中心附近的对象）', async () => {
    // Uncertain: no data-testid on SVG shapes; click the first task/obstacle shape in the SVG.
    const shape = map.locator('circle[class*="task"]:not([class*="Halo"])').first(); // FieldEditor.tsx:396
    const sb = (await shape.boundingBox())!;
    await page.mouse.click(sb.x + sb.width / 2, sb.y + sb.height / 2);
    await expect(xInput).toBeVisible({ timeout: 10_000 });
    await shot(page, info, 'selected');
  });
  const before = (await xInput.count()) ? await xInput.inputValue() : null;
  await test.step('拖拽对象', async () => {
    const sel = map.locator('circle[class*="task"]:not([class*="Halo"])').first();
    const b = await sel.boundingBox();
    if (b) { await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2); await page.mouse.down(); await page.mouse.move(b.x + b.width / 2 + 60, b.y + b.height / 2 + 30, { steps: 12 }); await page.mouse.up(); }
    await shot(page, info, 'dragged');
    await expect(undo).toBeEnabled();
  });
  await test.step('撤销', async () => { await undo.click(); await shot(page, info, 'undone'); if (before !== null) await expect(xInput).toHaveValue(before); await expect(redo).toBeEnabled(); });
  await test.step('重做', async () => { await redo.click(); await shot(page, info, 'redone'); });
  await test.step('数值输入 X', async () => {
    await expect(xInput).toBeVisible();
    await xInput.fill('12.5'); await xInput.blur();
    await expect(xInput).toHaveValue('12.5');
    await shot(page, info, 'numeric');
  });
});
