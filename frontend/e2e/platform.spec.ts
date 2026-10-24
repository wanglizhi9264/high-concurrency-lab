import { test, expect } from '@playwright/test'
test('real architecture, recorded data, live health and pool simulation', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', (e) => errors.push(e.message))
  await page.goto('/')
  await expect(page.getByRole('heading', { name: '先看见系统，再深入原理。' })).toBeVisible()
  await page.locator('.vue-flow__node').filter({ hasText: 'MySQL 8.4' }).click()
  await expect(page.locator('.inspector')).toContainText('EXPLAIN ANALYZE')
  await page.getByRole('button', { name: '查看实际初始化记录' }).click()
  await expect(page.locator('.startup')).toContainText('lazy')
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({
    path: '../docs/experiments/003-interactive-system-visualization/architecture.png',
    fullPage: true,
  })
  await page.goto('/database')
  await expect(page.getByTestId('baseline-p50')).toHaveText('414.682')
  await expect(page.getByTestId('optimized-p50')).toHaveText('153.842')
  await page
    .locator('.el-tree-node__content')
    .filter({ hasText: 'Table scan on lab_order' })
    .click()
  await expect(page.locator('.plan-layout .inspector')).toContainText('1,000,000')
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({
    path: '../docs/experiments/003-interactive-system-visualization/database.png',
    fullPage: true,
  })
  await page.goto('/trace')
  await page.getByRole('button', { name: '采集真实健康请求' }).click()
  await expect(page.getByTestId('http-status')).toHaveText('200')
  await expect(page.getByTestId('parallel-probes')).toContainText('并发探针')
  await expect(page.getByTestId('parallel-probes').locator('.lane-node')).toHaveCount(2)
  await expect(page.locator('.page-heading .badge.measured')).toContainText('Live Trace')
  await page.getByRole('button', { name: '单步', exact: true }).click()
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({
    path: '../docs/experiments/003-interactive-system-visualization/live-trace.png',
    fullPage: true,
  })
  await page.goto('/pool')
  await expect(page.locator('.page-heading .badge')).toContainText('Simulation')
  await page.getByRole('button', { name: '播放', exact: true }).click()
  await page.getByRole('button', { name: '暂停', exact: true }).click()
  await page.goto('/experiments')
  await page.getByRole('link').filter({ hasText: 'MySQL 索引与分页基线' }).click()
  await expect(
    page.getByRole('heading', { name: '为什么只返回20行，底层却可能访问100万行？' }),
  ).toBeVisible()
  await page.getByRole('button', { name: '切换深色模式' }).click()
  await expect(page.locator('html')).toHaveClass(/dark/)
  expect(errors).toEqual([])
})
test('API error is visible and recoverable', async ({ page }) => {
  await page.route('**/api/v1/architecture', (route) =>
    route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: '{"detail":"unavailable"}',
    }),
  )
  await page.goto('/')
  await expect(page.getByRole('alert')).toContainText('API 503')
  await expect(page.getByRole('button', { name: '重试' })).toBeVisible()
})
