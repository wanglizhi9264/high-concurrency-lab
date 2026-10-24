import { describe, it, expect, vi, afterEach } from 'vitest'
import { request, api } from '../src/api'
afterEach(() => vi.unstubAllGlobals())
describe('read only API client', () => {
  it('shows failed requests as actionable errors', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: false, status: 503 })),
    )
    await expect(request('/experiments')).rejects.toThrow('503')
  })
  it('retains structured failed live traces', async () => {
    const data = { mode: 'live', http_status: 503, events: [] }
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: false, status: 503, json: async () => data })),
    )
    expect(await api.trace()).toEqual(data)
  })
  it('rejects incomplete recorded data', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => ({ ok: true, json: async () => ({ baseline: {} }) })),
    )
    await expect(api.results(1000000)).rejects.toThrow('结构不完整')
  })
})
