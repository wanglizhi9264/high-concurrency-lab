import { ref, shallowRef, watch } from 'vue'
import { executeCacheRequest } from '../api/cache'
import type { CacheAction, CacheObservation, CacheRequestResult } from '../types/cache'

export function cacheSampleSummary(rows: CacheRequestResult[]) {
  const reads = rows.filter((row) => row.action === 'read')
  const hits = reads.filter((row) => row.body?.cache?.initial_lookup === 'hit').length
  const misses = reads.filter((row) => row.body?.cache?.initial_lookup === 'miss').length
  return {
    hits,
    misses,
    hitRate: hits + misses ? hits / (hits + misses) : null,
    redisServed: reads.filter((row) => row.body?.cache?.served_from === 'redis').length,
    degraded: reads.filter((row) => row.body?.cache?.outcome === 'degraded').length,
    excluded: rows.length - hits - misses,
  }
}
export function useCacheLab() {
  const productId = ref(1),
    ttl = ref(5),
    mode = ref<'cache' | 'bypass'>('cache')
  const result = shallowRef<CacheRequestResult | null>(null)
  const inspection = shallowRef<CacheObservation | null>(null)
  const history = shallowRef<CacheRequestResult[]>([])
  const loading = ref(false),
    error = ref(''),
    networkFailures = ref(0)
  let previous: CacheAction = 'read'
  watch(productId, () => {
    result.value = null
    inspection.value = null
    error.value = ''
  })
  async function execute(action: CacheAction) {
    if (loading.value) return
    const id = productId.value
    loading.value = true
    error.value = ''
    result.value = null
    previous = action
    try {
      const response = await executeCacheRequest(action, id, mode.value, ttl.value)
      history.value = [...history.value, response].slice(-50)
      if (id !== productId.value) return
      result.value = response
      if (action === 'inspect') inspection.value = response.body?.cache ?? null
      if (action === 'invalidate') inspection.value = null
      if (response.body?.error)
        error.value = `${response.body.error.code}: ${response.body.error.message}`
    } catch (failure) {
      networkFailures.value += 1
      if (id === productId.value) {
        error.value = failure instanceof Error ? failure.message : '未取得响应'
        if (action === 'inspect') inspection.value = null
      }
    } finally {
      loading.value = false
    }
  }
  return {
    productId,
    ttl,
    mode,
    result,
    inspection,
    history,
    loading,
    error,
    networkFailures,
    execute,
    retry: () => execute(previous),
  }
}
