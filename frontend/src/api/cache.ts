import { executeBusinessRequest } from './business'
import type { CacheAction, CacheRequestResult, CacheResponse } from '../types/cache'

export function cacheRequestPath(
  action: CacheAction,
  id: number,
  mode: 'cache' | 'bypass',
  ttl: number,
) {
  if (
    !Number.isSafeInteger(id) ||
    id < 1 ||
    id > 1000 ||
    !Number.isSafeInteger(ttl) ||
    ttl < 1 ||
    ttl > 60
  )
    throw new Error('商品 ID 需为 1..1000，TTL 需为 1..60 秒整数')
  const base = `/api/v1/business/cache/products/${id}`
  return action === 'inspect'
    ? `${base}/state`
    : action === 'invalidate'
      ? base
      : `${base}?mode=${mode}&ttl_seconds=${ttl}`
}
export async function executeCacheRequest(
  action: CacheAction,
  id: number,
  mode: 'cache' | 'bypass',
  ttl: number,
): Promise<CacheRequestResult> {
  const result = await executeBusinessRequest<CacheResponse>(
    cacheRequestPath(action, id, mode, ttl),
    action === 'invalidate' ? 'DELETE' : 'GET',
  )
  if (!result.body?.error && !result.body?.cache) throw new Error('缓存观测响应缺失')
  return { ...result, action }
}
