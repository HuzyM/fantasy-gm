import { browserOrigin, browserPort } from './scripts/browser-server.mjs';
import { defineConfig } from 'playwright/test';
export default defineConfig({
  testDir: './browser-tests',
  workers: 1,
  forbidOnly: Boolean(process.env.CI),
  updateSnapshots: process.env.CI ? 'none' : undefined,
  reporter: [['list'], ['json', { outputFile: 'output/browser-results.json' }]],
  timeout: 60000,
  outputDir: 'output/screens',
  snapshotPathTemplate: '../docs/frontend/{platform}/{arg}{ext}',
  use: {
    baseURL: browserOrigin,
    headless: true,
    channel: process.env.PLAYWRIGHT_CHANNEL || 'chrome',
  },
  webServer: {
    command:
      process.env.LOCAL_API === '1'
        ? `npm run build && "${process.env.PYTHON_EXECUTABLE || (process.platform === 'win32' ? '../.venv/Scripts/python.exe' : '../.venv/bin/python')}" -B -m fantasy_gm.web --port ${browserPort}`
        : `npm run build && npm run preview -- --port ${browserPort} --strictPort`,
    url: browserOrigin,
    reuseExistingServer: false,
  },
});
