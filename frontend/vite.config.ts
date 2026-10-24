import { defineConfig } from 'vitest/config'
import vue from '@vitejs/plugin-vue'
export default defineConfig({
  plugins: [vue()],
  server: {
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': process.env.API_PROXY_TARGET || 'http://127.0.0.1:18002',
      '/health': process.env.API_PROXY_TARGET || 'http://127.0.0.1:18002',
    },
  },
  test: { environment: 'jsdom', setupFiles: ['./tests/setup.ts'], include: ['tests/**/*.test.ts'] },
})
