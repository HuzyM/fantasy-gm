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
    command: 'npm run build && npm run preview -- --port 4173 --strictPort',
    url: 'http://127.0.0.1:4173',
    reuseExistingServer: false,
  },
});
