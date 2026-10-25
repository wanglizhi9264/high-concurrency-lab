import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import * as api from '../src/api/scaleExperiments'
import { useScaleLab } from '../src/composables/useScaleLab'
import { buildScalePlan } from '../src/lib/scalePlan'
import ScaleLabView from '../src/views/ScaleLabView.vue'
import type { ScaleRun } from '../src/types/scaleExperiments'

afterEach(() => vi.restoreAllMocks())
describe('009 recorded comparison controls', () => {
  it('clears stale record immediately and ignores late previous selection', async () => {
    let finish!: (value: ScaleRun) => void
    vi.spyOn(api, 'getScaleExperiment')
      .mockImplementationOnce(
        () =>
          new Promise((resolve) => {
            finish = resolve
          }),
      )
      .mockResolvedValue({ manifest: { id: 'new' } } as ScaleRun)
    const lab = useScaleLab()
    lab.selectedId.value = 'old'
    lab.record.value = { manifest: { id: 'old' } } as ScaleRun
    lab.selectedId.value = 'new'
    expect(lab.record.value).toBeNull()
    await flushPromises()
    finish({ manifest: { id: 'old' } } as ScaleRun)
    await flushPromises()
    expect(lab.record.value?.manifest.id).toBe('new')
  })
  it('retains unknown/unavailable semantics and does not offer heavy HTTP execution', async () => {
    vi.spyOn(api, 'listScaleExperiments').mockResolvedValue([])
    const view = mount(ScaleLabView, { global: { stubs: { ChartPanel: true, PlanTree: true } } })
    await flushPromises()
    expect(view.text()).toContain('千万级')
    expect(view.text()).toContain('普通启动')
    expect(view.text()).toContain('暂无')
    expect(view.findAll('button').some((button) => button.text().includes('开始百万'))).toBe(false)
  })
  it('builds plan hierarchy from raw indentation and preserves unknown metrics', () => {
    const plan = buildScalePlan(
      {
        tree: '-> Limit\n    -> Scan (actual time=1..2 rows=20 loops=1)',
        iterators: [
          {
            operator: 'Scan',
            first_row_ms: 1,
            iterator_ms_per_loop: 2,
            actual_rows_per_loop: 20,
            loops: 1,
            access_rows: 20,
          },
        ],
        sql: 'SELECT fixture',
        parameters: {},
      } as never,
      'a'.repeat(40),
    )
    expect(plan.tree[0]?.metrics).toBeNull()
    expect(plan.tree[0]?.children[0]?.metrics?.actual_rows_per_loop).toBe(20)
    expect(plan.raw_tree).toContain('actual time=1..2')
  })
})
