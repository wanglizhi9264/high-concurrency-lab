import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import ElementPlus from 'element-plus'
import BusinessQueryView from '../src/views/BusinessQueryView.vue'
import { businessQueryPath, executeBusinessRequest } from '../src/api/business'

afterEach(() => vi.unstubAllGlobals())
describe('actual business request UI', () => {
  it('builds fixed paths and mutually exclusive cursor parameters', () => {
    expect(businessQueryPath('product', 1, 20, 0)).toBe('/api/v1/business/products/1')
    const path = businessQueryPath('order_page', 500, 3, 20, {
      before_time: '2025-01-01T00:00:00',
      before_id: 9,
    })
    expect(path).toContain('before_id=9')
    expect(path).not.toContain('offset=')
  })
  it('retains safe structured failures for inspection', async () => {
    const body = {
      data: null,
      error: { code: 'not_found', message: 'Not found' },
      trace: { request_id: 'abc', spans: [] },
    }
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        status: 404,
        json: async () => body,
        headers: new Headers({ 'x-request-id': 'abc' }),
      })),
    )
    const response = await executeBusinessRequest('/api/v1/business/products/999')
    expect(response.body?.error?.code).toBe('not_found')
    expect(response.requestId).toBe('abc')
  })
  it('shows request, exact decimal data and error recovery', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({
        status: 200,
        headers: new Headers(),
        json: async () => ({
          data: { id: 1, name: 'Product 1', sku: 'SKU0001', price: '1.17' },
          error: null,
          trace: {
            request_id: 'request1',
            spans: [],
            definitions: {},
            database: 'business_test',
            pool_before: {},
            pool_after: {},
          },
        }),
      })),
    )
    const wrapper = mount(BusinessQueryView, {
      global: { plugins: [ElementPlus], stubs: { RouterLink: true } },
    })
    await wrapper.get('[data-testid="execute-business"]').trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('1.17')
    expect(wrapper.text()).toContain('GET /api/v1/business/products/1')
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new Error('Network failure')
      }),
    )
    await wrapper.get('[data-testid="execute-business"]').trigger('click')
    await flushPromises()
    expect(wrapper.get('[role="alert"]').text()).toContain('Network failure')
    expect(wrapper.find('[data-testid="business-result"]').exists()).toBe(false)
  })
})
