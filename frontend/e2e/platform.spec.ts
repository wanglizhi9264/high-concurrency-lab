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

test('storage learning distinguishes actual probes from cache-aside scenarios', async ({
  page,
}) => {
  await page.goto('/')
  const lesson = page.getByRole('region', { name: 'MySQL 与 Redis 交互教学' })
  await expect(lesson).toContainText('实际代码路径 · 非实时采集')
  await lesson.getByRole('button', { name: '下一步', exact: true }).click()
  await expect(lesson.locator('.storage-card.active')).toHaveCount(2)
  await expect(lesson.locator('.storage-step')).toContainText('并发')
  await lesson.getByRole('button', { name: '① 首次读取 · 缓存未命中' }).click()
  await expect(lesson).toContainText('Simulation · 不操作真实缓存')
  await expect(lesson.getByTestId('cache-value')).toContainText('MISS')
  await lesson.getByRole('button', { name: '下一步', exact: true }).click()
  await expect(lesson.locator('.mysql-card')).toHaveClass(/active/)
  await lesson.getByRole('button', { name: '下一步', exact: true }).click()
  await expect(lesson.getByTestId('cache-value')).toContainText('299')
  await lesson.getByRole('button', { name: '② 再次读取 · 缓存命中' }).click()
  await expect(lesson.locator('.storage-step')).toContainText('步骤 1 / 2')
  await lesson.getByRole('button', { name: '下一步', exact: true }).click()
  await expect(lesson.locator('.storage-step')).toContainText('此次不查询 MySQL')
  await expect(lesson.getByRole('button', { name: '下一步', exact: true })).toBeDisabled()
  await lesson.screenshot({
    path: '../docs/experiments/003-interactive-system-visualization/storage-learning.png',
  })
  await page.getByRole('button', { name: '切换深色模式' }).click()
  await expect(lesson).toBeVisible()
  await expect(page.locator('html')).toHaveClass(/dark/)
  await lesson.getByRole('button', { name: '③ 缓存过期 · 回源' }).click()
  await expect(lesson.getByTestId('cache-value')).toContainText('MISS')
  await lesson.getByRole('button', { name: '下一步', exact: true }).click()
  await expect(lesson.locator('.storage-step')).toContainText('回源')
  await lesson.getByRole('button', { name: '重新演示' }).click()
  await expect(lesson.locator('.storage-step')).toContainText('步骤 1 / 3')
})

test('detailed probe guide, independent outcomes, and simulation reset', async ({ page }) => {
  await page.goto('/trace')
  await expect(page.getByTestId('probe-database')).not.toBeEmpty()
  const guide = page.locator('.probe-guide')
  await expect(guide).toContainText('Redis 逻辑库 0')
  await expect(guide).toContainText('GET /api/v1/observability/health-trace')
  await expect(guide).toContainText('不查询任何业务表')
  await guide.screenshot({
    path: '../docs/experiments/003-interactive-system-visualization/probe-guide.png',
  })
  await guide.locator(':scope > summary').click()
  await page.locator('.el-radio-button').filter({ hasText: '教学模拟' }).click()
  const scenario = page.getByLabel('选择探针结果场景')
  await scenario.selectOption('mysql-failure')
  await expect(page.getByTestId('http-status')).toHaveText('503')
  await expect(page.getByTestId('check-mysql')).toHaveText('unavailable')
  await expect(page.getByTestId('check-redis')).toHaveText('ok')
  await page.locator('.event-row').filter({ hasText: 'MySQL 检查失败' }).click()
  await expect(page.locator('.inspector')).toContainText('认证异常')
  await scenario.selectOption('redis-failure')
  await expect(page.getByTestId('check-mysql')).toHaveText('ok')
  await expect(page.getByTestId('check-redis')).toHaveText('unavailable')
  await expect(page.locator('.event-row.active')).toContainText('浏览器发送 GET')
  await scenario.selectOption('mysql-timeout')
  await page.locator('.event-row').filter({ hasText: 'MySQL 超过检查预算' }).click()
  await expect(page.locator('.inspector')).toContainText('asyncio.timeout')
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({
    path: '../docs/experiments/003-interactive-system-visualization/probe-timeout.png',
    fullPage: true,
  })
  await scenario.selectOption('success')
  await expect(page.getByTestId('http-status')).toHaveText('200')
  await expect(page.getByTestId('check-mysql')).toHaveText('ok')
  await expect(page.getByTestId('check-redis')).toHaveText('ok')
})

test('structured HTTP 503 and failed fetch are different states', async ({ page }) => {
  await page.route('**/api/v1/observability/health-trace', (route) =>
    route.fulfill({
      status: 503,
      contentType: 'application/json',
      body: JSON.stringify({
        mode: 'live',
        http_status: 503,
        checks: { mysql: 'unavailable', redis: 'ok' },
        server_elapsed_ms: 1,
        events: [],
        limitations: ['Browser fixture, not real outage evidence'],
      }),
    }),
  )
  await page.goto('/trace')
  await page.getByRole('button', { name: '采集真实健康请求' }).click()
  await expect(page.getByTestId('http-status')).toHaveText('503')
  await expect(page.getByTestId('check-mysql')).toHaveText('unavailable')
  await expect(page.getByTestId('check-redis')).toHaveText('ok')
  await expect(page.getByRole('alert')).toHaveCount(0)
  await page.unroute('**/api/v1/observability/health-trace')
  await page.route('**/api/v1/observability/health-trace', (route) => route.abort('failed'))
  await page.getByRole('button', { name: '采集真实健康请求' }).click()
  await expect(page.getByRole('alert')).toContainText('网络失败不等于')
  await expect(page.getByRole('region', { name: '本次探针结果' })).toHaveCount(0)
})
