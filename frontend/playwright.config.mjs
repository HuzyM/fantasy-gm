import { defineConfig } from 'playwright/test';
export default defineConfig({
  testDir: './browser-tests',
  workers: 1,
  timeout: 60000,
  outputDir: 'output/screens',
  snapshotPathTemplate: '../docs/frontend/{platform}/{arg}{ext}',
  use: {
    baseURL: 'http://127.0.0.1:4173',
    headless: true,
    channel: process.env.PLAYWRIGHT_CHANNEL || 'chrome',
  },
  webServer: {
    command:
      process.env.LOCAL_API === '1'
        ? `npm run build && "${process.env.PYTHON_EXECUTABLE || (process.platform === 'win32' ? '../.venv/Scripts/python.exe' : '../.venv/bin/python')}" -B -m fantasy_gm.web --port 4173`
        : 'npm run build && npm run preview -- --port 4173 --strictPort',
    url: 'http://127.0.0.1:4173',
    reuseExistingServer: false,
  },
});
