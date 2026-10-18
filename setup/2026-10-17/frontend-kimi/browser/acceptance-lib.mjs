import fs from 'node:fs';
import { api } from './cdp.mjs';

export const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

export async function click(page, selector, text = null, nth = 0) {
  const point = await page.evaluate(`(() => {
    const needle = ${JSON.stringify(text)};
    const visible = [...document.querySelectorAll(${JSON.stringify(selector)})].filter((el) => {
      const r = el.getBoundingClientRect();
      const style = getComputedStyle(el);
      return r.width > 0 && r.height > 0 && style.display !== 'none' && style.visibility !== 'hidden';
    });
    const own = needle ? visible.filter((el) => [el.innerText, el.textContent].filter(Boolean).join(' ').includes(needle)) : visible;
    const matches = own.length || !needle ? own : visible.filter((el) => [el.parentElement?.innerText, el.parentElement?.parentElement?.innerText].filter(Boolean).join(' ').includes(needle));
    const el = matches[${nth}];
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return { x: r.x + r.width / 2, y: r.y + r.height / 2, text: el.innerText ?? el.textContent ?? '' };
  })()`);
  if (!point) throw new Error(`Missing visible click target: ${selector} ${text ?? ''} #${nth}`);
  await sleep(80);
  await page.cdp.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: point.x, y: point.y, button: 'left', clickCount: 1 });
  await page.cdp.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: point.x, y: point.y, button: 'left', clickCount: 1 });
  await sleep(120);
  return point;
}

async function inputPoint(page, mode, needle) {
  return page.evaluate(`(() => {
    const mode = ${JSON.stringify(mode)};
    const needle = ${JSON.stringify(needle)};
    const els = [...document.querySelectorAll('input,select,textarea')].filter((el) => {
      const r = el.getBoundingClientRect();
      if (r.width <= 0 || r.height <= 0 || getComputedStyle(el).display === 'none') return false;
      if (mode === 'aria') return el.getAttribute('aria-label') === needle;
      return el.parentElement?.parentElement?.innerText?.split('\\n')[0] === needle;
    });
    const el = els[0];
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return { x: r.x + r.width / 2, y: r.y + r.height / 2, tag: el.tagName, value: el.value };
  })()`);
}

export async function setInput(page, label, value, mode = 'label') {
  const point = await inputPoint(page, mode, label);
  if (!point) throw new Error(`Missing input ${mode}: ${label}`);
  if (point.tag === 'SELECT') {
    await page.evaluate(`(() => {
      const mode = ${JSON.stringify(mode)};
      const needle = ${JSON.stringify(label)};
      const value = ${JSON.stringify(String(value))};
      const el = [...document.querySelectorAll('select')].find((item) => mode === 'aria'
        ? item.getAttribute('aria-label') === needle
        : item.parentElement?.parentElement?.innerText?.split('\\n')[0] === needle);
      if (!el) return false;
      el.value = value;
      el.dispatchEvent(new Event('change', { bubbles: true }));
      return el.value === value;
    })()`);
    await sleep(120);
    return;
  }
  await page.cdp.send('Input.dispatchMouseEvent', { type: 'mousePressed', x: point.x, y: point.y, button: 'left', clickCount: 1 });
  await page.cdp.send('Input.dispatchMouseEvent', { type: 'mouseReleased', x: point.x, y: point.y, button: 'left', clickCount: 1 });
  await page.evaluate(`(() => {
    const el = document.activeElement;
    if (!el || typeof el.setSelectionRange !== 'function') return false;
    el.setSelectionRange(0, el.value.length);
    return document.activeElement === el && el.selectionStart === 0 && el.selectionEnd === el.value.length;
  })()`);
  await page.cdp.send('Input.insertText', { text: String(value) });
  await page.cdp.send('Input.dispatchKeyEvent', { type: 'keyDown', key: 'Tab', code: 'Tab' });
  await page.cdp.send('Input.dispatchKeyEvent', { type: 'keyUp', key: 'Tab', code: 'Tab' });
  await sleep(180);
}

export async function inputValue(page, label, mode = 'label') {
  return page.evaluate(`(() => {
    const mode = ${JSON.stringify(mode)};
    const needle = ${JSON.stringify(label)};
    const el = [...document.querySelectorAll('input,select,textarea')].find((item) => {
      const r = item.getBoundingClientRect();
      if (r.width <= 0 || r.height <= 0) return false;
      return mode === 'aria' ? item.getAttribute('aria-label') === needle : item.parentElement?.parentElement?.innerText?.split('\\n')[0] === needle;
    });
    return el ? el.value : null;
  })()`);
}

export async function waitForScenarioRuns(scenarioId, count, excludedJobs = new Set(), timeoutMs = 45000) {
  const deadline = Date.now() + timeoutMs;
  let latest = null;
  while (Date.now() < deadline) {
    const payload = await api(`/lab/api/runs?scenario_id=${encodeURIComponent(scenarioId)}&limit=30`);
    const jobId = payload.runs[0]?.job_id;
    if (jobId && !excludedJobs.has(jobId)) {
      const rows = payload.runs.filter((run) => run.job_id === jobId);
      latest = rows;
      if (rows.length === count && rows.every((run) => !['queued', 'running'].includes(run.state))) return rows;
    }
    await sleep(250);
  }
  throw new Error(`Timed out waiting for ${count} runs on ${scenarioId}; latest=${JSON.stringify(latest?.map((r) => ({ id: r.run_id, state: r.state, status: r.status, error: r.error })))}`);
}

export async function waitForFile(directory, predicate, timeoutMs = 15000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const found = fs.readdirSync(directory).filter((name) => !name.endsWith('.crdownload')).find(predicate);
    if (found) return `${directory}/${found}`;
    await sleep(200);
  }
  throw new Error(`Timed out waiting for download in ${directory}`);
}

export async function layoutEvidence(page) {
  return page.evaluate(`(() => {
    const visible = (el) => { const r=el.getBoundingClientRect(); return r.width>0&&r.height>0&&getComputedStyle(el).display!=='none'; };
    const buttons = [...document.querySelectorAll('button,a')].filter(visible).filter((el) => /对比|求解|导出实验记录|关闭仿真|停止|Gazebo/.test(el.innerText)).map((el) => {
      const r=el.getBoundingClientRect(); return {text:el.innerText,left:r.left,right:r.right,top:r.top,bottom:r.bottom};
    });
    const toolbar = document.querySelector('header');
    const map = document.querySelector('[aria-label="任务地图编辑器"],[aria-label="场景地图"]');
    return {
      innerWidth, innerHeight, documentWidth: document.documentElement.scrollWidth, bodyWidth: document.body.scrollWidth,
      toolbar: toolbar ? {clientWidth:toolbar.clientWidth,scrollWidth:toolbar.scrollWidth,height:toolbar.getBoundingClientRect().height} : null,
      map: map ? {width:map.getBoundingClientRect().width,height:map.getBoundingClientRect().height} : null,
      buttons,
    };
  })()`);
}
