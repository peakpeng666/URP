// Luna 260abc42 (workbench 7c8a6f65): 生成来源 section (studio/agri/GeneratedFrom.tsx) inside ScenarioInfo (PlanPanels.tsx:632,654,
// shown in the 检查器 dock tab). data-generated = parametric | manual | unknown. 回到目录改参数 → #/archive, catalog card reopened
// with the scenario's params + seed (AgriCatalog.tsx:60-89).
import { test, expect, shot, openAgriCatalog, firstRunnablePattern, openInspectorTab } from './helpers';
async function readForm(card: any, name: string) {
  const out: Record<string, string> = {};
  const fields = card.locator(`fieldset [aria-label^="${name} "]`);
  for (let i = 0; i < (await fields.count()); i++) {
    const f = fields.nth(i); const k = (await f.getAttribute('aria-label'))!;
    out[k] = (await f.getAttribute('type')) === 'checkbox' ? String(await f.isChecked()) : await f.inputValue();
  }
  return out;
}
test('K 生成来源：参数化 → 手工编辑 → 回到目录改参数', async ({ page }, info) => {
  const catalog = await openAgriCatalog(page);
  // Pinned to 果园采收集运 (a57a43fb/d6aec3bf normalized diff for this pattern, seed 7).
  const card = catalog.locator('details', { has: page.locator('summary', { hasText: '果园采收集运' }) }).first();
  const firstRunnable = await firstRunnablePattern(page);
  console.log('K first runnable card:', firstRunnable.name);
  if (firstRunnable.card !== card) await firstRunnable.card.locator('summary').click(); // collapse
  if ((await card.getAttribute('open')) === null) await card.locator('summary').click();
  const name = (await card.locator('summary').innerText()).split(' · ')[0].trim();
  console.log('K selected card:', name);
  expect(name).toContain('果园采收集运');
  await card.getByLabel(`${name} 随机种子`).fill('7');
  const form = await readForm(card, name);
  expect(form[`${name} 随机种子`]).toBe('7');
  await card.getByRole('button', { name: '校验并导入任务规划' }).click();
  await expect(page).toHaveURL(/#\/plan\/.+/, { timeout: 60_000 });
  const map = page.locator('svg[aria-label="任务地图编辑器"]');
  await expect(map).toBeVisible({ timeout: 30_000 });
  await openInspectorTab(page);
  const scenarioBtn = page.getByRole('group', { name: '检查器' }).getByRole('button', { name: '场景', exact: true }); // fleet inspector: 车队/选中/场景 (PlanPanels.tsx:399)
  if (await scenarioBtn.count()) await scenarioBtn.click();
  const gen = page.getByRole('region', { name: '生成来源' }).or(page.locator('section[aria-label="生成来源"]')).first();
  await test.step('导入后：参数化生成', async () => {
    await expect(gen).toBeVisible({ timeout: 15_000 });
    await expect(gen).toHaveAttribute('data-generated', 'parametric');
    await expect(gen).toContainText('种子 7');
    await shot(page, info, 'parametric');
  });
  await test.step('拖动任务点 → 手工编辑并列出变化', async () => {
    const t = (await map.locator('g[data-hit="task"]').first().boundingBox())!;
    await page.mouse.move(t.x + t.width / 2, t.y + t.height / 2); await page.mouse.down();
    await page.mouse.move(t.x + t.width / 2 + 60, t.y + t.height / 2 + 30, { steps: 12 }); await page.mouse.up();
    await openInspectorTab(page);
    if (await scenarioBtn.count()) await scenarioBtn.click();
    await expect(gen).toHaveAttribute('data-generated', 'manual', { timeout: 10_000 });
    await expect(gen.getByRole('status')).toContainText(/手工编辑.*：.+/);
    await shot(page, info, 'manual');
  });
  await test.step('回到目录改参数 → 卡片展开，参数与种子一致', async () => {
    await gen.getByRole('button', { name: '回到目录改参数' }).click();
    // Luna fix: stays on #/plan/..., opens 场景库 (ScenarioNavigator) with agri catalog expanded + card located.
    await expect(page).toHaveURL(/#\/plan\/.+/);
    const catalog = page.getByRole('region', { name: '农业任务目录' });
    await expect(catalog).toBeVisible({ timeout: 15_000 });
    const back = catalog.locator('details', { has: page.locator('summary', { hasText: name }) }).first();
    await expect(back).toHaveAttribute('open', '');
    await expect(back.getByLabel(`${name} 随机种子`)).toHaveValue('7');
    expect(await readForm(back, name)).toEqual(form);
    await shot(page, info, 'back-to-catalog');
  });
});
