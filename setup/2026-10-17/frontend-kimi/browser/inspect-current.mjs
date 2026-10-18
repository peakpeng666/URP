import { launchChrome, writeJson } from './cdp.mjs';

const root = new URL('.', import.meta.url).pathname;
const browser = await launchChrome({
  profileDir: `${root}inspect-profile-${Date.now()}`,
  downloadDir: `${root}downloads`,
  width: 1440,
  height: 900,
});
const { page } = browser;
try {
  await page.navigate('http://127.0.0.1:4100/#/plan/task-sampling-20261016-152557-420');
  await page.waitFor("document.body.innerText.includes('推荐与求解')", { timeoutMs: 30000 });
  await new Promise((resolve) => setTimeout(resolve, 2500));
  const data = await page.evaluate(`(() => {
    const visible = (el) => {
      const r = el.getBoundingClientRect();
      const s = getComputedStyle(el);
      return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && s.display !== 'none';
    };
    const rect = (el) => {
      const r = el.getBoundingClientRect();
      return { x: r.x, y: r.y, width: r.width, height: r.height };
    };
    return {
      url: location.href,
      title: document.title,
      text: document.body.innerText.slice(0, 16000),
      buttons: [...document.querySelectorAll('button')].filter(visible).map((el) => ({
        text: el.innerText, title: el.title, aria: el.getAttribute('aria-label'), disabled: el.disabled,
        className: el.className, ...rect(el),
      })),
      inputs: [...document.querySelectorAll('input,select,textarea')].filter(visible).map((el) => ({
        tag: el.tagName, type: el.type, name: el.name, value: el.value, min: el.min, max: el.max,
        step: el.step, disabled: el.disabled, aria: el.getAttribute('aria-label'), title: el.title,
        className: el.className, ...rect(el),
      })),
      tabs: [...document.querySelectorAll('[role=tab]')].filter(visible).map((el) => ({ text: el.innerText, className: el.className, ...rect(el) })),
      svg: [...document.querySelectorAll('svg')].filter(visible).map((el) => ({
        className: el.getAttribute('class'), viewBox: el.getAttribute('viewBox'), ...rect(el),
        children: [...el.children].slice(0, 30).map((child) => ({ tag: child.tagName, className: child.getAttribute('class'), data: {...child.dataset} })),
      })),
    };
  })()`);
  writeJson(`${root}inspect-current.json`, { ...data, exceptions: page.exceptions, console: page.console, httpErrors: page.httpErrors });
  await page.screenshot(`${root}inspect-current.png`);
  console.log(JSON.stringify({ buttons: data.buttons.map((x) => x.text), inputs: data.inputs, tabs: data.tabs, svg: data.svg }, null, 2));
} finally {
  await browser.close();
}
