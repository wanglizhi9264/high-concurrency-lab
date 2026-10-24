import { onMounted, ref, shallowRef } from 'vue'
export function useRequest<T>(loader: () => Promise<T>) {
  const data = shallowRef<T | null>(null),
    loading = ref(false),
    error = ref('')
  let sequence = 0
  async function reload() {
    const current = ++sequence
    loading.value = true
    error.value = ''
    try {
      const value = await loader()
      if (current === sequence) data.value = value
    } catch (e) {
      if (current === sequence) error.value = e instanceof Error ? e.message : '加载失败'
    } finally {
      if (current === sequence) loading.value = false
    }
  }
  onMounted(() => void reload())
  return { data, loading, error, reload }
}
