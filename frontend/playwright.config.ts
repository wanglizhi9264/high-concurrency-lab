import { defineConfig } from '@playwright/test'
export default defineConfig({
  testDir: './e2e',
  timeout: 30000,
  use: {
    baseURL: 'http://127.0.0.1:5174',
    channel: process.env.PLAYWRIGHT_CHANNEL || undefined,
    viewport: { width: 1440, height: 1000 },
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      command: 'uv run uvicorn concurrency_lab.main:app --host 127.0.0.1 --port 18002',
      cwd: '..',
      url: 'http://127.0.0.1:18002/health/live',
      reuseExistingServer: !process.env.CI,
    },
    {
      command: 'npm run dev -- --host 127.0.0.1 --port 5174',
      url: 'http://127.0.0.1:5174',
      reuseExistingServer: !process.env.CI,
    },
  ],
})
