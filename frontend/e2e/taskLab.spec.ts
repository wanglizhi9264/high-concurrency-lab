import { test, expect } from '@playwright/test'
import { spawn } from 'node:child_process'
import { resolve } from 'node:path'

test('real queued task, scoped worker retry, persisted receipt and separate queue snapshot', async ({
  page,
}) => {
  const scope = crypto.randomUUID()
  const base = '/api/v1/business'
  const stock = await page.request.post(`${base}/inventory/scenarios`, {
    data: { scenario_id: scope, product_id: 1, initial: 1 },
  })
  expect(stock.status()).toBe(201)
  const order = await page.request.post(`${base}/purchases/orders`, {
    data: { scenario_id: scope, user_id: 1, quantity: 1 },
    headers: { 'Idempotency-Key': crypto.randomUUID() },
  })
  expect(order.status()).toBe(201)
  const id = (await order.json()).data.order.id
  expect(
    (
      await page.request.post(`${base}/purchases/orders/${id}/state`, { data: { target: 'paid' } })
    ).status(),
  ).toBe(200)
  await page.goto(`/tasks?order_id=${id}`)
  await expect(page.getByLabel('任务订单 ID')).toHaveValue(String(id))
  await page.getByText('受控故障配置（实际执行，不是性能结论）', { exact: true }).click()
  await page.getByLabel('任务失败次数').fill('1')
  await page.getByTestId('task-prepare').click()
  await page.getByTestId('task-submit').click()
  await expect(page.getByTestId('task-state')).toContainText('queued')
  await page.getByTestId('task-refresh').click()
  await expect(page.getByTestId('task-outbox')).toContainText('确认发布 0 次')
  const taskId = await page.getByLabel('任务 UUID').inputValue()
  const response = await page.request.get(`${base}/tasks/${taskId}`)
  const database = (await response.json()).trace.database as string
  expect(['concurrency_lab_business', 'concurrency_lab_business_test']).toContain(database)
  await expect(page.getByTestId('task-command')).toContainText(`--scenario ${scope}`)
  const root = resolve('..')
  const python = resolve(
    root,
    '.venv',
    process.platform === 'win32' ? 'Scripts/python.exe' : 'bin/python',
  )
  const child = spawn(
    python,
    [
      '-m',
      'concurrency_lab.workers.receipts',
      '--database',
      database,
      '--scenario',
      scope,
      '--max-cycles',
      '15',
    ],
    {
      cwd: root,
      env: { ...process.env, BUSINESS_WRITES_ENABLED: 'true', PYTHONUTF8: '1' },
      windowsHide: true,
    },
  )
  let diagnostic = ''
  child.stderr.on('data', (chunk) => {
    diagnostic = (diagnostic + chunk.toString()).slice(-3000)
  })
  const stopped = new Promise<number | null>((resolveExit, reject) => {
    child.on('exit', resolveExit)
    child.on('error', reject)
  })
  try {
    await expect
      .poll(
        async () => {
          await page.getByTestId('task-refresh').click()
          await expect(page.getByTestId('task-state')).toBeVisible()
          return page.getByTestId('task-state').textContent()
        },
        { timeout: 15000 },
      )
      .toContain('succeeded')
    await expect(page.getByTestId('task-receipt')).toContainText('1.17')
    await expect(page.locator('tbody')).toContainText('failed')
    await expect(page.locator('tbody')).toContainText('succeeded')
    await page.getByRole('button', { name: '采集队列快照', exact: true }).click()
    await expect(page.getByTestId('task-queue')).toContainText('XLEN')
    await expect(page.getByTestId('task-queue')).toContainText('pending 0')
    expect(await stopped, diagnostic).toBe(0)
    await page.screenshot({
      path: '../docs/experiments/008-reliable-receipt-worker/task-lab.png',
      fullPage: true,
    })
  } finally {
    if (child.exitCode === null && !child.killed) child.kill()
  }
})
