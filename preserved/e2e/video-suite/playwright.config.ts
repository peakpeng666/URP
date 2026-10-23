import { defineConfig } from '@playwright/test';
const evidence = process.env.URP_EVIDENCE_DIR ?? './evidence';
export default defineConfig({
  testDir: './tests',
  outputDir: `${evidence}/artifacts`,
  workers: 1, fullyParallel: false, retries: 0, timeout: 180_000,
  reporter: [['list'], ['json', { outputFile: `${evidence}/results.json` }], ['html', { outputFolder: `${evidence}/html`, open: 'never' }]],
  use: {
    baseURL: process.env.URP_BASE_URL ?? 'http://127.0.0.1:4100',
    video: 'on', trace: 'on', screenshot: 'on',
    viewport: { width: 1440, height: 900 }, locale: 'zh-CN', timezoneId: 'Asia/Tokyo',
  },
});
