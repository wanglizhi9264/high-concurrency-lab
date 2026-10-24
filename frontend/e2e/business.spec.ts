import { test, expect } from '@playwright/test'

test('real business product, detail, paging and trace source', async ({ page, request }) => {
  const enabled = await request.get('/api/v1/business/products/1')
  test.skip(
    enabled.status() === 503 && (await enabled.json()).error?.code === 'business_disabled',
    'Business lab explicitly disabled; CI enables isolated dataset',
  )
  await page.goto('/business')
  await page.getByTestId('execute-business').click()
  await expect(page.getByTestId('business-result')).toContainText('1.17')
  await expect(page.locator('.business-request-result')).toContainText('concurrency_lab_business')
  await page.locator('.event-row').filter({ hasText: 'MySQL SQL + 取数' }).last().click()
  await expect(page.getByTestId('business-sql')).toContainText('lab_product')
  await expect(page.locator('.source-link').last()).toHaveAttribute('href', /product_repository.py/)
  await page.getByLabel('查询类型').selectOption('order_detail')
  await page.getByTestId('execute-business').click()
  await expect(page.getByTestId('business-result')).toContainText('unit_price')
  await page.getByLabel('查询类型').selectOption('order_page')
  await page.getByLabel('实体 ID').fill('500')
  await page.getByLabel('页大小').fill('3')
  await page.getByTestId('execute-business').click()
  await expect(page.getByRole('button', { name: '下一页（游标）' })).toBeEnabled()
  await page.getByRole('button', { name: '下一页（游标）' }).click()
  await expect(page.locator('.business-request-result')).toContainText('before_id')
  const invalid = await request.get('/api/v1/business/users/500/order-page?before_id=3')
  expect(invalid.status()).toBe(422)
  const failure = await invalid.json()
  expect(failure.error.code).toBe('invalid_input')
  expect(failure.trace.request_id).toBe(invalid.headers()['x-request-id'])
  expect(failure.trace.spans.every((span: { sql: string | null }) => span.sql === null)).toBe(true)
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({
    path: '../docs/experiments/004-real-business-trace/business-query.png',
    fullPage: true,
  })
})
