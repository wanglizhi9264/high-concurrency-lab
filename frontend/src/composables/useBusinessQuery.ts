import { ref, shallowRef } from 'vue'
import { executeBusinessRequest } from '../api/business'
import type { BusinessRequestResult } from '../types/business'

export function useBusinessQuery() {
  const result = shallowRef<BusinessRequestResult | null>(null)
  const loading = ref(false)
  const error = ref('')
  async function execute(path: string) {
    if (loading.value) return
    loading.value = true
    error.value = ''
    result.value = null
    try {
      result.value = await executeBusinessRequest(path)
      if (result.value.body?.error)
        error.value = `${result.value.body.error.code}：${result.value.body.error.message}`
    } catch (failure) {
      error.value = failure instanceof Error ? failure.message : '未取得业务响应'
    } finally {
      loading.value = false
    }
  }
  return { result, loading, error, execute }
}
