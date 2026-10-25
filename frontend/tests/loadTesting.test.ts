import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import { loadSeries } from '../src/lib/loadSeries'
import type { RecordedLoadRun } from '../src/types/benchmarks'
import LoadTestView from '../src/views/LoadTestView.vue'
import { listBenchmarks, getBenchmark } from '../src/api/benchmarks'

function fixture(id: string, pool: number): RecordedLoadRun {
  return {
    schema_version: 1,
    evidence: 'recorded',
    complete: true,
    manifest: {
      id,
      start_epoch: 100,
      end_epoch: 102,
      duration_s: 2,
      peak_users: 100,
      parameters: {
        users: 100,
        seconds: 5,
        task_rate: 1,
        spawn_rate: 500,
        pool_size: pool,
        scenario: 'mixed',
      },
      dataset: { order_count: 10000, digest: 'fixture' },
      environment: { scope: 'unit fixture' },
      raw_files: [],
    },
    summary: {
      requests: 10,
      failures: 2,
      completed_rps: 5,
      error_rate: 0.2,
      p50_ms: 10,
      p95_ms: 20,
      p99_ms: 30,
      observed_sql_attempts_per_s: null,
      unknown_sql_responses: 2,
      sql_response_coverage: 0.8,
      http_504: 0,
      pool_timeouts: 2,
      transport_timeouts: 0,
    },
    history: [
      {
        elapsed_s: 0,
        interval_s: 2,
        completed: 10,
        failures: 2,
        completed_rps: 5,
        observed_sql_attempts_per_s: null,
      },
    ],
    resources: [],
    locust_statistics: [],
    semantics: { source: 'test fixture, not real performance evidence' },
    limitations: ['unit fixture'],
  }
}
const first = fixture('load-20261025T000000-aaaaaaaa', 5)
const second = fixture('load-20261025T000001-bbbbbbbb', 1)
vi.mock('../src/api/benchmarks', () => ({
  listBenchmarks: vi.fn(async () => [first, second]),
  getBenchmark: vi.fn(async (id: string) => (id === first.manifest.id ? first : second)),
}))

describe('recorded load data and comparison', () => {
  it('separates successful completions from all completions and leaves unknown SQL blank', () => {
    expect(loadSeries(first, 'completed_rps')).toEqual([[0, 5]])
    expect(loadSeries(first, 'success_rps')).toEqual([[0, 4]])
    expect(loadSeries(first, 'sql_rate')).toEqual([[0, null]])
  })
  it('detects MySQL restart/counter resets rather than showing negative QPS', () => {
    const run = structuredClone(first)
    run.resources = [
      [0, 100, 100],
      [2, 120, 102],
      [4, 5, 1],
      [6, 10, 3],
    ].map(([seconds, questions, uptime]) => ({
      observed_at: new Date(seconds! * 1000).toISOString(),
      elapsed_s: seconds!,
      scope: 'business_pool_mysql_instance',
      source: 'unit fixture',
      cpu_percent: null,
      memory_bytes: null,
      memory_limit_bytes: null,
      error_code: null,
      business: {
        observed_at: new Date(seconds! * 1000).toISOString(),
        status: 'ok',
        pool: {},
        mysql_status: { Questions: questions!, Uptime: uptime! },
      },
    }))
    expect(loadSeries(run, 'mysql_statement_rate')).toEqual([
      [0, null],
      [2, 10],
      [4, null],
      [6, 2.5],
    ])
  })
  it('shows exact summaries, parameter differences and no stale chart after failure', async () => {
    const wrapper = mount(LoadTestView, {
      global: { plugins: [ElementPlus], stubs: { ChartPanel: true } },
    })
    await flushPromises()
    expect(wrapper.findAll('[data-testid="load-rps"]').map((node) => node.text())).toEqual([
      '5.00',
      '5.00',
    ])
    expect(wrapper.text()).toContain('pool_size')
    expect(wrapper.text()).toContain('未采集')
    vi.mocked(getBenchmark).mockRejectedValueOnce(new Error('fixture unavailable'))
    await wrapper.get('[aria-label="实验 A"]').setValue(second.manifest.id)
    await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('fixture unavailable')
    expect(wrapper.find('.load-comparison').exists()).toBe(false)
    await wrapper.get('[role="alert"] button').trigger('click')
    await flushPromises()
    expect(wrapper.find('.load-comparison').exists()).toBe(true)
  })
  it('supports a single recorded run without generating a second series', async () => {
    vi.mocked(listBenchmarks).mockResolvedValueOnce([first])
    const wrapper = mount(LoadTestView, {
      global: { plugins: [ElementPlus], stubs: { ChartPanel: true } },
    })
    await flushPromises()
    expect(wrapper.findAll('.load-comparison > section')).toHaveLength(1)
    expect(wrapper.text()).toContain('当前只有单次实验')
  })
})
