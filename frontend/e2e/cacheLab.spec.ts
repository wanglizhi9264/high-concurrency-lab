import { test, expect } from '@playwright/test'

test('real product cache miss, hit, expiry, invalidation and Redis command source', async ({
  page,
  request,
}) => {
  const path = '/api/v1/business/cache/products/1'
  const enabled = await request.get('/api/v1/business/products/1')
  test.skip(
    enabled.status() === 503 && (await enabled.json()).error?.code === 'business_disabled',
    'Explicit business dataset required',
  )
  await page.goto('/cache-lab')
  await page.getByLabel('缓存 TTL', { exact: true }).fill('3')
  await page.getByRole('button', { name: '主动失效', exact: true }).click()
  await expect(page.getByTestId('cache-result')).toContainText('invalidated')
  await page.getByTestId('cache-read').click()
  await expect(page.getByTestId('cache-result')).toContainText('miss')
  await expect(page.getByTestId('cache-result')).toContainText('1.17')
  await page.getByTestId('cache-read').click()
  await expect(page.getByTestId('cache-result')).toContainText('hit')
  await expect(page.getByTestId('cache-result')).toContainText('redis')
  await expect(page.getByText('MySQL 商品 SQL 尝试 0', { exact: false })).toBeVisible()
  await page.locator('.event-row').filter({ hasText: 'Redis 命令往返' }).first().click()
  await expect(page.getByTestId('business-command')).toContainText(':product:1:value')
  await expect(page.locator('.inspector .source-link')).toHaveAttribute(
    'href',
    /cache\/products.py/,
  )
  const state = await request.get(path + '/state')
  const ttl = (await state.json()).cache.ttl_ms
  expect(ttl).toBeGreaterThan(0)
  expect(ttl).toBeLessThanOrEqual(3300)
  await expect
    .poll(async () => (await (await request.get(path + '/state')).json()).cache.ttl_ms, {
      timeout: 5000,
    })
    .toBe(-2)
  await page.getByTestId('cache-read').click()
  await expect(page.getByTestId('cache-result')).toContainText('miss')
  await page.getByRole('button', { name: '检查选定键', exact: true }).click()
  await expect(page.getByText(/MEMORY USAGE：.*bytes/)).toBeVisible()
  await page.screenshot({
    path: '../docs/experiments/006-redis-cache-aside/cache-lab.png',
    fullPage: true,
  })
})
