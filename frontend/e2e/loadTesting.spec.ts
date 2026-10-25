import { test, expect } from '@playwright/test'

test('actual recorded load comparison agrees with the API', async ({ page, request }) => {
  const response = await request.get('/api/v1/benchmarks')
  expect(response.ok()).toBe(true)
  const records = await response.json()
  expect(records.length).toBeGreaterThanOrEqual(6)
  await page.goto('/load-tests')
  await expect(page.getByTestId('load-rps')).toHaveCount(2)
  const selected = await page.getByLabel('实验 A', { exact: true }).inputValue()
  const raw = await request.get(`/api/v1/benchmarks/${selected}`)
  const record = await raw.json()
  await expect(page.getByTestId('load-rps').first()).toHaveText(
    record.summary.completed_rps.toFixed(2),
  )
  await expect(page.locator('.callout').first()).toContainText('pool_size')
  await page.getByLabel('压测指标').selectOption('api_cpu')
  await expect(page.getByRole('img', { name: /CPU.*历史实测比较/ })).toBeVisible()
  const expectedPoints = record.resources
    .filter((sample: { scope: string }) => sample.scope === 'api_process_tree')
    .map((sample: { elapsed_s: number; cpu_percent: number | null }) => [
      sample.elapsed_s,
      sample.cpu_percent,
    ])
  await expect
    .poll(async () => JSON.parse((await page.getByTestId('load-series').textContent())!)[0].points)
    .toEqual(expectedPoints)
  await page.screenshot({
    path: '../docs/experiments/005-real-load-testing/load-comparison.png',
    fullPage: true,
  })
})
