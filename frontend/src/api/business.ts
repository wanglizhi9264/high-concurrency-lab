import type {
  BusinessCursor,
  BusinessQuery,
  BusinessRequestResult,
  BusinessResponse,
} from '../types/business'
import { executeObservedRequest } from './observed'

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
  return executeObservedRequest<T>(path, { method })
}
