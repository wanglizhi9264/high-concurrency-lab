import { describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { cacheRequestPath, executeCacheRequest } from '../src/api/cache'
import { cacheSampleSummary } from '../src/composables/useCacheLab'
import CacheLabView from '../src/views/CacheLabView.vue'
import type { CacheRequestResult } from '../src/types/cache'

vi.mock('../src/api/cache', async (original) => ({
  ...(await original<object>()),
  executeCacheRequest: vi.fn(),
}))
function result(
  initial: 'hit' | 'miss' | 'skipped' | 'unknown',
  source: 'redis' | 'mysql',
  outcome = 'miss',
) {
  return {
    action: 'read',
    body: {
      data: { id: 1, price: '1.17' },
      error: null,
      cache: {
        outcome,
        initial_lookup: initial,
        served_from: source,
        key: 'fixture:key',
        ttl_ms: null,
        memory_bytes: null,
        fill_published: null,
        observed_at: 'fixture',
      },
      trace: {
        request_id: 'fixture',
        database: 'fixture',
        spans: [],
        pool_before: {},
        pool_after: {},
        definitions: {},
        environment: {},
        observed_at: 'fixture',
        service_elapsed_ms: 1,
      },
    },
    status: 200,
    path: '/fixture',
    browserMs: 2,
  } as unknown as CacheRequestResult
}
describe('real cache lab boundaries', () => {
  it('clears the selected key snapshot when product changes', async () => {
    const inspected = result('skipped', 'mysql', 'inspected')
    inspected.action = 'inspect'
    inspected.body!.cache!.ttl_ms = 500
    vi.mocked(executeCacheRequest).mockResolvedValueOnce(inspected)
    const wrapper = mount(CacheLabView, { global: { stubs: { BusinessTracePanel: true } } })
    await wrapper.get('button:nth-of-type(2)').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('fixture:key')
    await wrapper.get('[aria-label="缓存商品 ID"]').setValue(2)
    expect(wrapper.text()).not.toContain('fixture:key')
    expect(wrapper.text()).toContain('未采集')
    wrapper.unmount()
  })
  it('builds bounded fixed operations, not user Redis commands', () => {
    expect(cacheRequestPath('read', 1, 'cache', 5)).toContain('ttl_seconds=5')
    expect(cacheRequestPath('inspect', 1, 'cache', 5)).toBe(
      '/api/v1/business/cache/products/1/state',
    )
    expect(() => cacheRequestPath('read', 1001, 'cache', 5)).toThrow()
  })
  it('counts initial hit ratio separately from final Redis reuse and exclusions', () => {
    const rows = [
      result('hit', 'redis', 'hit'),
      result('miss', 'redis', 'coalesced'),
      result('skipped', 'mysql', 'bypass'),
      result('unknown', 'mysql', 'degraded'),
    ]
    const summary = cacheSampleSummary(rows)
    expect(summary.hits).toBe(1)
    expect(summary.misses).toBe(1)
    expect(summary.hitRate).toBe(0.5)
    expect(summary.redisServed).toBe(2)
    expect(summary.excluded).toBe(2)
    expect(cacheSampleSummary([]).hitRate).toBeNull()
  })
  it('shows real outcomes, unknown inspection and clears success on failure with retry', async () => {
    vi.mocked(executeCacheRequest)
      .mockResolvedValueOnce(result('miss', 'mysql'))
      .mockRejectedValueOnce(new Error('fetch unavailable'))
      .mockResolvedValueOnce(result('hit', 'redis', 'hit'))
    const wrapper = mount(CacheLabView, { global: { stubs: { BusinessTracePanel: true } } })
    expect(wrapper.text()).toContain('尚无请求')
    await wrapper.get('[data-testid="cache-read"]').trigger('click')
    await flushPromises()
    expect(wrapper.get('[data-testid="cache-result"]').text()).toContain('1.17')
    expect(wrapper.text()).toContain('未采集')
    await wrapper.get('[data-testid="cache-read"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-testid="cache-result"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('fetch unavailable')
    await wrapper.get('[data-testid="cache-retry"]').trigger('click')
    await flushPromises()
    expect(wrapper.get('[data-testid="cache-result"]').text()).toContain('redis')
    wrapper.unmount()
  })
})
