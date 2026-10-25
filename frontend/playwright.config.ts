import { defineConfig } from '@playwright/test'
import { playwrightPorts } from './config/playwrightPorts'
const ports = playwrightPorts(process.env)
export default defineConfig({
  testDir: './e2e',
  timeout: 30000,
  use: {
    baseURL: `http://127.0.0.1:${ports.frontend}`,
    channel: process.env.PLAYWRIGHT_CHANNEL || undefined,
    viewport: { width: 1440, height: 1000 },
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  webServer: [
    {
      command: `uv run uvicorn concurrency_lab.main:app --host 127.0.0.1 --port ${ports.api}`,
      cwd: '..',
      url: `http://127.0.0.1:${ports.api}/health/live`,
      reuseExistingServer: ports.reuse,
    },
    {
      command: `npm run dev -- --host 127.0.0.1 --port ${ports.frontend} --strictPort`,
      env: { API_PROXY_TARGET: `http://127.0.0.1:${ports.api}` },
      url: `http://127.0.0.1:${ports.frontend}`,
      reuseExistingServer: ports.reuse,
    },
  ],
})
