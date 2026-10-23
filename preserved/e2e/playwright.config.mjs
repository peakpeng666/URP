import { defineConfig } from '@playwright/test';
const out = process.env.ART || 'artifacts/run';
export default defineConfig({
  testDir: 'tests', timeout: 120000, workers: 1, outputDir: out + '/test-results',
  reporter: [['list'], ['html', { outputFolder: out + '/report', open: 'never' }], ['json', { outputFile: out + '/results.json' }]],
  use: { ...(process.env.PW_CHANNEL ? { channel: process.env.PW_CHANNEL } : {}), baseURL: process.env.BASE_URL || 'http://127.0.0.1:4100', video: 'on', trace: 'on', screenshot: 'on', viewport: { width: 1440, height: 900 } },
});
