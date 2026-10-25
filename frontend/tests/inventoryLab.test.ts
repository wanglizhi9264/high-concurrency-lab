import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { executeObservedRequest } from '../src/api/observed'
import * as api from '../src/api/inventory'
import { contestSummary, useInventoryLab } from '../src/composables/useInventoryLab'
import InventoryLabView from '../src/views/InventoryLabView.vue'
import type { InventoryRequestResult, InventoryResponse } from '../src/types/inventory'

const uuid = '11111111-1111-4111-8111-111111111111'
function response(data: unknown = null): InventoryRequestResult {
  return {
    status: 200,
    path: '/fixture',
    browserMs: 1,
    preparationMs: '0.5',
    requestId: 'r',
    body: {
      data: data as InventoryResponse['data'],
      error: null,
      trace: {
        request_id: 'r',
        evidence: 'measured',
        unit: 'ms',
        spans: [],
        database: 'fixture',
        observed_at: 'fixture',
        definitions: {},
        pool_before: {},
        pool_after: {},
        environment: {},
        service_elapsed_ms: 0.4,
        pool_before_offset_ms: null,
        pool_after_offset_ms: null,
      },
    },
  }
}
afterEach(() => {
  vi.restoreAllMocks()
  vi.unstubAllGlobals()
})
describe('transactional inventory UI contracts', () => {
  it('inspects a historical response without changing active stock or recording another request', () => {
    const lab = useInventoryLab()
    lab.scenario.value = {
      id: uuid,
      product_id: 1,
      initial: 5,
      available: 5,
      reserved: 0,
      sold: 0,
      created_at: 'fixture',
    }
    lab.selectResponse(response({ scenario: { id: '22222222-2222-4222-8222-222222222222' } }))
    expect(lab.scenario.value.id).toBe(uuid)
    expect(lab.history.value).toHaveLength(0)
    expect(lab.result.value?.path).toBe('/fixture')
  })
  it('sends exact POST JSON and intent header while retaining structured conflict', async () => {
    const fetch = vi.fn<typeof globalThis.fetch>().mockResolvedValue(
      new Response(
        JSON.stringify({
          data: null,
          error: { code: 'idempotency_conflict', message: 'Conflict' },
          trace: { request_id: 'r', spans: [] },
        }),
        { status: 409, headers: { 'x-request-id': 'r' } },
      ),
    )
    vi.stubGlobal('fetch', fetch)
    const result = await executeObservedRequest<InventoryResponse>(
      '/api/v1/business/purchases/orders',
      {
        method: 'POST',
        body: { quantity: 1 },
        headers: { 'Idempotency-Key': uuid },
      },
    )
    expect(fetch.mock.calls[0]?.[1]).toMatchObject({
      method: 'POST',
      body: '{"quantity":1}',
      headers: { 'Content-Type': 'application/json', 'Idempotency-Key': uuid },
    })
    expect(result.status).toBe(409)
    expect(result.body?.error?.code).toBe('idempotency_conflict')
  })
  it('retries the saved key and original payload despite form edits', async () => {
    vi.spyOn(api, 'submitOrder')
      .mockRejectedValueOnce(new Error('ack unknown'))
      .mockResolvedValue(response())
    const lab = useInventoryLab()
    lab.scenarioId.value = uuid
    lab.prepareOrder()
    const original = structuredClone(lab.intent.value!)
    lab.quantity.value = 2
    await lab.submitSavedOrder()
    expect(lab.error.value).toContain('ack unknown')
    await lab.retry()
    expect(api.submitOrder).toHaveBeenNthCalledWith(1, original)
    expect(api.submitOrder).toHaveBeenNthCalledWith(2, original)
    lab.prepareOrder()
    expect(lab.intent.value!.key).not.toBe(original.key)
    expect(lab.intent.value!.payload.quantity).toBe(2)
  })
  it('counts unique committed order identities rather than replay responses', () => {
    const result = response({ order: { id: 9 }, replayed: false, applied: true })
    const replay = response({ order: { id: 9 }, replayed: true, applied: false })
    const summary = contestSummary([
      { intent: {} as never, result, error: null },
      { intent: {} as never, result: replay, error: null },
      { intent: {} as never, result: null, error: 'unknown' },
    ])
    expect(summary.uniqueOrders).toBe(1)
    expect(summary.replays).toBe(1)
    expect(summary.unknown).toBe(1)
  })
  it('clears stale success on a network failure and offers an explicit retry', async () => {
    vi.spyOn(api, 'createScenario')
      .mockResolvedValueOnce(
        response({
          scenario: {
            id: uuid,
            product_id: 1,
            initial: 5,
            available: 5,
            reserved: 0,
            sold: 0,
          },
          replayed: false,
        }),
      )
      .mockRejectedValueOnce(new Error('network unknown'))
    const wrapper = mount(InventoryLabView, { global: { stubs: { BusinessTracePanel: true } } })
    expect(wrapper.text()).toContain('尚无库存实验')
    await wrapper.get('[data-testid="inventory-new-scenario"]').trigger('click')
    await flushPromises()
    expect(wrapper.get('[data-testid="inventory-result"]').text()).toContain(uuid)
    await wrapper.get('[data-testid="inventory-new-scenario"]').trigger('click')
    await flushPromises()
    expect(wrapper.find('[data-testid="inventory-result"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('network unknown')
    expect(wrapper.find('[data-testid="inventory-retry"]').exists()).toBe(true)
    wrapper.unmount()
  })
})
