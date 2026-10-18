import fs from 'node:fs';
import { launchChrome, writeJson } from './cdp.mjs';

const root = new URL('.', import.meta.url).pathname;
const fixtures = JSON.parse(fs.readFileSync(`${root}acceptance-fixtures.json`, 'utf8'));
const browser = await launchChrome({ profileDir: `${root}inspector-profile-${Date.now()}`, downloadDir: `${root}downloads`, width: 1440, height: 900 });
const { page } = browser;
async function click(selector, text = null) {
  const point = await page.evaluate(`(() => {
    const needle = ${JSON.stringify(text)};
    const el = [...document.querySelectorAll(${JSON.stringify(selector)})].find((item) => !needle || item.innerText.includes(needle));
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return { x: r.x + r.width / 2, y: r.y + r.height / 2 };
  })()`);
  if (!point) throw new Error(`Missing click target: ${selector} ${text ?? ''}`);
  await page.cdp.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: point.x, y: point.y, button: 'left', clickCount: 1 });
  await page.cdp.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: point.x, y: point.y, button: 'left', clickCount: 1 });
}
try {
  await page.navigate(`http://127.0.0.1:4100/#/plan/${fixtures.fleet_scenario_id}`);
  await page.waitFor("document.body.innerText.includes('推荐与求解') && !!document.querySelector('[data-hit=task][data-id=\"1\"]')");
  await click('[data-hit=task][data-id="1"] circle');
  await click('[role=tab]', '检查器');
  await new Promise((resolve) => setTimeout(resolve, 700));
  const data = await page.evaluate(`(() => {
    const visible = (el) => { const r=el.getBoundingClientRect(); return r.width>0&&r.height>0&&getComputedStyle(el).display!=='none'; };
    return {
      text: document.body.innerText.slice(-10000),
      inputs: [...document.querySelectorAll('input,select,textarea')].filter(visible).map((el) => ({
        tag:el.tagName,type:el.type,value:el.value,min:el.min,max:el.max,step:el.step,disabled:el.disabled,
        parent:el.parentElement?.innerText,grandparent:el.parentElement?.parentElement?.innerText,
      })),
      buttons:[...document.querySelectorAll('button')].filter(visible).map((el)=>el.innerText).filter(Boolean),
    };
  })()`);
  writeJson(`${root}inspect-inspector.json`, { ...data, exceptions: page.exceptions, console: page.console, httpErrors: page.httpErrors });
  await page.screenshot(`${root}inspect-inspector.png`);
  console.log(JSON.stringify(data, null, 2));
} finally { await browser.close(); }
