import { expect, type Page, type TestInfo, test } from '@playwright/test';
export const API = '/lab/api'; // src/lab/api.ts:28, src/studio/api.ts:22
export async function shot(page: Page, info: TestInfo, name: string) {
  const path = info.outputPath(`${String(info.attachments.length).padStart(2, '0')}-${name}.png`);
  await page.screenshot({ path, fullPage: false });
  await info.attach(name, { path, contentType: 'image/png' });
}
/** Open the scenario library's agri catalog (src/studio/panels/LibraryPanels.tsx:51). */
export async function openAgriCatalog(page: Page) {
  await page.goto('/#/plan');
  const toggle = page.getByRole('button', { name: '打开农业任务目录' });
  await expect(toggle).toBeVisible({ timeout: 30_000 });
  await toggle.click();
  const catalog = page.getByRole('region', { name: '农业任务目录' }); // AgriCatalog.tsx:20
  await expect(catalog).toBeVisible();
  return catalog;
}
/** First runnable (non-proposal) pattern card: has a 校验并导入任务规划 button (AgriCatalog.tsx:99). */
export async function firstRunnablePattern(page: Page) {
  const catalog = page.getByRole('region', { name: '农业任务目录' });
  const cards = catalog.locator('details');
  const n = await cards.count();
  for (let i = 0; i < n; i++) {
    const c = cards.nth(i);
    if (!(await c.isVisible())) continue;
    await c.locator('summary').click();
    if (await c.getByRole('button', { name: '校验并导入任务规划' }).count()) {
      const name = (await c.locator('summary').innerText()).split(' · ')[0].trim();
      return { card: c, name };
    }
    await c.locator('summary').click();
  }
  throw new Error('no runnable agri pattern found');
}
export async function listScenarios(page: Page): Promise<Array<{ id: string; title: string; origin?: string }>> {
  const r = await page.request.get(`${API}/scenarios`); // src/lab/api.ts:81
  expect(r.ok()).toBeTruthy();
  return (await r.json()).scenarios;
}
/** Bring the Studio dock tab “检查器” (InspectorPanel, PlanPanels.tsx:369) to front; it is inactive by default. */
export async function openInspectorTab(page: Page) {
  await page.getByText('检查器', { exact: true }).first().click();
}
export { test, expect };
