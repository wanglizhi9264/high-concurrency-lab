import { ref, shallowRef, watch } from 'vue'
import * as api from '../api/scaleExperiments'
import type {
  PhaseName,
  QueryName,
  ScaleRun,
  ScaleSummary,
  TableName,
} from '../types/scaleExperiments'
export function useScaleLab() {
  const catalogue = shallowRef<ScaleSummary[]>([]),
    record = shallowRef<ScaleRun | null>(null)
  const selectedId = ref(''),
    phase = ref<PhaseName>('baseline'),
    table = ref<TableName>('scale_order'),
    query = ref<QueryName>('user_projection')
  const catalogueLoading = ref(false),
    loading = ref(false),
    catalogueError = ref(''),
    error = ref('')
  let sequence = 0,
    catalogueSequence = 0
  async function reloadRecord() {
    const current = ++sequence,
      id = selectedId.value
    record.value = null
    error.value = ''
    if (!id) {
      loading.value = false
      return
    }
    loading.value = true
    try {
      const value = await api.getScaleExperiment(id)
      if (current === sequence) record.value = value
    } catch (failure) {
      if (current === sequence)
        error.value = failure instanceof Error ? failure.message : '读取009失败'
    } finally {
      if (current === sequence) loading.value = false
    }
  }
  watch(
    selectedId,
    () => {
      phase.value = 'baseline'
      table.value = 'scale_order'
      query.value = 'user_projection'
      void reloadRecord()
    },
    { flush: 'sync' },
  )
  async function reloadCatalogue() {
    const current = ++catalogueSequence
    catalogueLoading.value = true
    catalogueError.value = ''
    try {
      const value = await api.listScaleExperiments()
      if (current !== catalogueSequence) return
      catalogue.value = value
      if (!value.some((item) => item.manifest.id === selectedId.value))
        selectedId.value = value[0]?.manifest.id ?? ''
    } catch (failure) {
      if (current === catalogueSequence) {
        catalogue.value = []
        selectedId.value = ''
        catalogueError.value = failure instanceof Error ? failure.message : '目录读取失败'
      }
    } finally {
      if (current === catalogueSequence) catalogueLoading.value = false
    }
  }
  return {
    catalogue,
    record,
    selectedId,
    phase,
    table,
    query,
    catalogueLoading,
    loading,
    catalogueError,
    error,
    reloadCatalogue,
    reloadRecord,
  }
}
