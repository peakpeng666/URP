// Happy editor (942b376a): task shapes are g[data-hit="task"] (FieldEditor.tsx:512); status bar shows 选中：任务 <id>
// (Studio.tsx:435); SelectionPanel (aria-label 选择与精确输入) shows 已选 1 项 · 任务 <id> and NumField X（米） (SelectionPanel.tsx:31,66).
import { test, expect, shot, openAgriCatalog, firstRunnablePattern } from './helpers';
test('C 地图编辑器：选择对象、拖拽、撤销/重做、数值输入', async ({ page }, info) => {
  await openAgriCatalog(page);
  const { card } = await firstRunnablePattern(page);
  await card.getByRole('button', { name: '校验并导入任务规划' }).click();
  await expect(page).toHaveURL(/#\/plan\/.+/, { timeout: 60_000 });
  const map = page.locator('svg[aria-label="任务地图编辑器"]');
  await expect(map).toBeVisible({ timeout: 30_000 });
  const undo = page.getByRole('button', { name: /撤销/ });
  const redo = page.getByRole('button', { name: /重做/ });
  const sel = page.getByLabel('选择与精确输入');
  const xInput = sel.getByLabel('X（米）', { exact: true });
  const taskG = map.locator('g[data-hit="task"]').first();
  const id = await taskG.getAttribute('data-id');
  const task = taskG.locator('circle:not([r="11"])'); // the dot itself, not the g bbox (plots underneath took the click in run8 dry-run)
  await test.step('选择对象（点击任务点）', async () => {
    const sb = (await task.boundingBox())!;
    await page.mouse.click(sb.x + sb.width / 2, sb.y + sb.height / 2);
    await expect(page.getByText(`选中：任务 ${id}`)).toBeVisible();
    await expect(sel.getByText(new RegExp(`已选 1 项 · 任务点 ${id}$`)) /* ITEM_LABEL.task='任务点' selection.ts:13 */).toBeVisible();
    await expect(xInput).toBeVisible();
    await shot(page, info, 'selected');
  });
  const before = await xInput.inputValue();
  await test.step('拖拽对象', async () => {
    const b = (await task.boundingBox())!;
    await page.mouse.move(b.x + b.width / 2, b.y + b.height / 2); await page.mouse.down();
    await page.mouse.move(b.x + b.width / 2 + 60, b.y + b.height / 2 + 30, { steps: 12 }); await page.mouse.up();
    await expect(xInput).not.toHaveValue(before);
    await expect(undo).toBeEnabled();
    await shot(page, info, 'dragged');
  });
  const after = await xInput.inputValue();
  await test.step('撤销', async () => { await undo.click(); await expect(xInput).toHaveValue(before); await expect(redo).toBeEnabled(); await shot(page, info, 'undone'); });
  await test.step('重做', async () => { await redo.click(); await expect(xInput).toHaveValue(after); await shot(page, info, 'redone'); });
  await test.step('数值输入 X', async () => {
    await xInput.fill('12.5'); await xInput.press('Enter');
    await expect(xInput).toHaveValue('12.5');
    await shot(page, info, 'numeric');
  });
});
