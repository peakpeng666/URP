import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

class CDP {
  constructor(url) {
    this.url = url;
    this.id = 0;
    this.pending = new Map();
    this.listeners = new Map();
  }

  async connect() {
    this.ws = new WebSocket(this.url);
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => reject(new Error(`CDP connect timeout: ${this.url}`)), 10000);
      this.ws.addEventListener('open', () => { clearTimeout(timer); resolve(); }, { once: true });
      this.ws.addEventListener('error', (event) => { clearTimeout(timer); reject(event.error ?? new Error('CDP WebSocket error')); }, { once: true });
    });
    this.ws.addEventListener('message', (event) => {
      const message = JSON.parse(String(event.data));
      if (message.id) {
        const pending = this.pending.get(message.id);
        if (!pending) return;
        this.pending.delete(message.id);
        clearTimeout(pending.timer);
        if (message.error) pending.reject(new Error(`${pending.method}: ${message.error.message}`));
        else pending.resolve(message.result);
        return;
      }
      for (const listener of this.listeners.get(message.method) ?? []) listener(message.params);
    });
    this.ws.addEventListener('close', () => {
      for (const pending of this.pending.values()) {
        clearTimeout(pending.timer);
        pending.reject(new Error(`CDP closed during ${pending.method}`));
      }
      this.pending.clear();
    });
  }

  on(method, listener) {
    const listeners = this.listeners.get(method) ?? [];
    listeners.push(listener);
    this.listeners.set(method, listeners);
  }

  send(method, params = {}, timeoutMs = 30000) {
    const id = ++this.id;
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new Error(`CDP timeout: ${method}`));
      }, timeoutMs);
      this.pending.set(id, { resolve, reject, timer, method });
      this.ws.send(JSON.stringify({ id, method, params }));
    });
  }

  close() {
    this.ws?.close();
  }
}

export class BrowserPage {
  constructor(cdp) {
    this.cdp = cdp;
    this.console = [];
    this.exceptions = [];
    this.httpErrors = [];
    cdp.on('Runtime.consoleAPICalled', (event) => {
      this.console.push({ type: event.type, text: event.args.map((arg) => arg.value ?? arg.description ?? '').join(' '), timestamp: event.timestamp });
    });
    cdp.on('Runtime.exceptionThrown', (event) => this.exceptions.push(event.exceptionDetails));
    cdp.on('Network.responseReceived', (event) => {
      if (event.response.status >= 400) this.httpErrors.push({ url: event.response.url, status: event.response.status, statusText: event.response.statusText });
    });
  }

  async evaluate(expression, timeoutMs = 30000) {
    const result = await this.cdp.send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true, userGesture: true }, timeoutMs);
    if (result.exceptionDetails) {
      const detail = result.exceptionDetails.exception?.description ?? result.exceptionDetails.text;
      throw new Error(`Browser evaluation failed: ${detail}\n${expression}`);
    }
    return result.result.value;
  }

  async waitFor(expression, { timeoutMs = 30000, intervalMs = 150, label = expression } = {}) {
    const deadline = Date.now() + timeoutMs;
    let last;
    while (Date.now() < deadline) {
      last = await this.evaluate(expression);
      if (last) return last;
      await new Promise((resolve) => setTimeout(resolve, intervalMs));
    }
    const text = await this.evaluate('document.body?.innerText?.slice(0, 5000)').catch(() => '');
    throw new Error(`Timed out waiting for ${label}; page text:\n${text}`);
  }

  async navigate(url) {
    await this.cdp.send('Page.navigate', { url });
    await this.waitFor("document.readyState === 'complete'", { label: `load ${url}` });
  }

  async setViewport(width, height) {
    await this.cdp.send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile: false });
  }

  async screenshot(file) {
    fs.mkdirSync(path.dirname(file), { recursive: true });
    const result = await this.cdp.send('Page.captureScreenshot', { format: 'png', fromSurface: true, captureBeyondViewport: false });
    fs.writeFileSync(file, Buffer.from(result.data, 'base64'));
  }
}

export async function launchChrome({ profileDir, downloadDir, width = 1440, height = 900 }) {
  fs.mkdirSync(profileDir, { recursive: true });
  fs.mkdirSync(downloadDir, { recursive: true });
  const env = { ...process.env };
  delete env.LD_LIBRARY_PATH;
  const chrome = spawn('/usr/bin/google-chrome', [
    '--headless=new', '--no-sandbox', '--disable-dev-shm-usage', '--no-first-run', '--no-default-browser-check',
    '--disable-background-networking', '--remote-debugging-address=127.0.0.1', '--remote-debugging-port=0',
    `--user-data-dir=${profileDir}`, `--window-size=${width},${height}`, 'about:blank',
  ], { env, stdio: ['ignore', 'pipe', 'pipe'] });
  let chromeLog = '';
  const browserWs = await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`Chrome startup timeout:\n${chromeLog}`)), 20000);
    const inspect = (chunk) => {
      chromeLog += chunk;
      const match = chromeLog.match(/DevTools listening on (ws:\/\/[^\s]+)/);
      if (match) { clearTimeout(timer); resolve(match[1]); }
    };
    chrome.stderr.on('data', inspect);
    chrome.stdout.on('data', inspect);
    chrome.once('exit', (code) => { clearTimeout(timer); reject(new Error(`Chrome exited ${code}:\n${chromeLog}`)); });
  });
  const port = new URL(browserWs).port;
  const browser = new CDP(browserWs);
  await browser.connect();
  await browser.send('Browser.setDownloadBehavior', { behavior: 'allow', downloadPath: downloadDir, eventsEnabled: true });
  const targets = await fetch(`http://127.0.0.1:${port}/json/list`).then((response) => response.json());
  const target = targets.find((item) => item.type === 'page');
  if (!target) throw new Error('Chrome page target not found');
  const cdp = new CDP(target.webSocketDebuggerUrl);
  await cdp.connect();
  await Promise.all([cdp.send('Page.enable'), cdp.send('Runtime.enable'), cdp.send('Network.enable'), cdp.send('Log.enable')]);
  const page = new BrowserPage(cdp);
  await page.setViewport(width, height);
  return {
    page,
    chromeLog: () => chromeLog,
    async close() {
      try { await browser.send('Browser.close', {}, 5000); } catch { /* already closed */ }
      browser.close();
      cdp.close();
      await new Promise((resolve) => {
        const timer = setTimeout(resolve, 3000);
        chrome.once('exit', () => { clearTimeout(timer); resolve(); });
      });
      if (chrome.exitCode == null) chrome.kill('SIGTERM');
    },
  };
}

export async function api(pathname, options = {}) {
  const response = await fetch(`http://127.0.0.1:4100${pathname}`, {
    ...options,
    headers: { Accept: 'application/json', ...(options.body ? { 'Content-Type': 'application/json' } : {}), ...options.headers },
  });
  const text = await response.text();
  let data;
  try { data = text ? JSON.parse(text) : null; } catch { throw new Error(`Non-JSON API ${pathname} (${response.status}): ${text.slice(0, 300)}`); }
  if (!response.ok) throw new Error(`API ${pathname} (${response.status}): ${JSON.stringify(data)}`);
  return data;
}

export function writeJson(file, value) {
  fs.mkdirSync(path.dirname(file), { recursive: true });
  fs.writeFileSync(file, `${JSON.stringify(value, null, 2)}\n`);
}
