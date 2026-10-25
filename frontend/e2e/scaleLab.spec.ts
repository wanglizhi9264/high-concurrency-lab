import { test, expect } from '@playwright/test'
import type { ScaleRun, ScaleSummary } from '../src/types/scaleExperiments'

test('actual009 evidence agrees with selected SQL, plan, partitions and writes', async ({
  page,
}) => {
  const list = await page.request.get('/api/v1/scale-experiments')
  expect(list.status()).toBe(200)
  const runs = (await list.json()) as ScaleSummary[]
  expect(runs.length).toBeGreaterThan(0)
  const selected = runs.find((run) => run.manifest.order_count === 1000000) ?? runs[0]!
  const response = await page.request.get(`/api/v1/scale-experiments/${selected.manifest.id}`)
  expect(response.status()).toBe(200)
  const record = (await response.json()) as ScaleRun
  await page.goto('/scale-lab')
  await page.getByLabel('009 实验运行').selectOption(selected.manifest.id)
  await expect(page.getByTestId('scale-identity')).toContainText(selected.manifest.source.revision)
  await page.getByLabel('009 SQL 案例').selectOption('time_range')
  await page.getByLabel('009 索引阶段').selectOption('covering')
  await page.getByLabel('009 表布局').selectOption('scale_order_partitioned')
  const observation = record.phases.find((phase) => phase.phase === 'covering')!.tables
    .scale_order_partitioned.queries.time_range
  await expect(page.getByTestId('scale-sql')).toHaveText(observation.sql)
  await expect(page.getByTestId('scale-partitions')).toContainText(
    observation.selected_partitions!.join(', '),
  )
  await expect(page.getByTestId('scale-partitions')).toContainText(
    observation.covering_observed
      ? 'JSON 覆盖标志：using_index=true'
      : '未报告 using_index=true（另看 TREE）',
  )
  await page.getByText('原始 TREE / JSON 计划', { exact: true }).click()
  await expect(page.getByTestId('scale-tree')).toHaveText(observation.tree)
  await expect(page.getByTestId('scale-writes')).toContainText(
    record.writes.rows_per_probe.toLocaleString(),
  )
  await page.getByTestId('scale-sql').scrollIntoViewIfNeeded()
  await page.screenshot({ path: '../docs/experiments/009-scale-comprehensive-lab/scale-plan.png' })
  await page.evaluate(() => window.scrollTo(0, 0))
  await page.screenshot({
    path: '../docs/experiments/009-scale-comprehensive-lab/scale-overview.png',
  })
})
