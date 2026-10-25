import type {
  BusinessCursor,
  BusinessQuery,
  BusinessRequestResult,
  BusinessResponse,
} from '../types/business'

export function businessQueryPath(
  query: BusinessQuery,
  id: number,
  limit: number,
  offset: number,
  cursor: BusinessCursor | null = null,
): string {
  const base = '/api/v1/business'
  if (query === 'product') return `${base}/products/${id}`
  if (query === 'order_detail') return `${base}/orders/${id}`
  const parameters = new URLSearchParams({ limit: String(limit) })
  if (cursor && query === 'order_page') {
    parameters.set('before_time', cursor.before_time)
    parameters.set('before_id', String(cursor.before_id))
  } else parameters.set('offset', String(offset))
  return `${base}/users/${id}/${query === 'order_page' ? 'order-page' : 'orders'}?${parameters}`
}
export async function executeBusinessRequest<T extends BusinessResponse = BusinessResponse>(
  path: string,
  method: 'GET' | 'DELETE' = 'GET',
): Promise<BusinessRequestResult<T>> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 65000)
  const started = performance.now()
  try {
    const response = await fetch(path, { method, signal: controller.signal })
    const body = await response.json()
    if (!body.trace?.request_id || !Array.isArray(body.trace.spans)) {
      throw new Error(`HTTP ${response.status}：请求未进入业务执行；请检查参数、代理和后端。`)
    }
    return {
      body,
      status: response.status,
      path,
      browserMs: performance.now() - started,
      preparationMs: response.headers.get('x-process-time-ms'),
      requestId: response.headers.get('x-request-id'),
    }
  } finally {
    clearTimeout(timeout)
  }
}
