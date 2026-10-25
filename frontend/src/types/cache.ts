import type { BusinessRequestResult, BusinessResponse } from './business'

export type CacheAction = 'read' | 'inspect' | 'invalidate'
export interface CacheObservation {
  evidence: 'measured'
  outcome: string
  initial_lookup: 'hit' | 'miss' | 'unknown' | 'skipped'
  served_from: 'mysql' | 'redis' | null
  key: string
  generation: number | null
  redis_available: boolean | null
  ttl_ms: number | null
  memory_bytes: number | null
  fill_published: boolean | null
  reason: string | null
  observed_at: string
}
export interface CacheResponse extends BusinessResponse {
  cache?: CacheObservation
}
export interface CacheRequestResult extends BusinessRequestResult<CacheResponse> {
  action: CacheAction
}
