import { ref, shallowRef, watch } from 'vue'
import * as api from '../api/tasks'
import type { QueueSnapshot, Task, TaskDetail, TaskInput, TaskRequestResult } from '../types/tasks'

export function useTaskLab() {
  const orderId = ref(1),
    taskId = ref(''),
    maxAttempts = ref(3),
    failFirst = ref(0),
    delayMs = ref(0)
  const loading = ref(false),
    error = ref('')
  const intent = shallowRef<TaskInput | null>(null)
  const successor = shallowRef<{
    parent: string
    payload: { task_id: string; disable_faults: boolean }
  } | null>(null)
  const detail = shallowRef<TaskDetail | null>(null),
    queue = shallowRef<QueueSnapshot | null>(null)
  const accepted = shallowRef<Task | null>(null),
    result = shallowRef<TaskRequestResult | null>(null)
  let revision = 0,
    previous: (() => Promise<TaskRequestResult>) | null = null
  function clear() {
    revision++
    detail.value = null
    queue.value = null
    accepted.value = null
    result.value = null
    error.value = ''
    previous = null
  }
  watch(taskId, clear, { flush: 'sync' })
  watch(
    orderId,
    () => {
      clear()
      intent.value = null
      successor.value = null
      taskId.value = ''
    },
    { flush: 'sync' },
  )
  async function send(operation: () => Promise<TaskRequestResult>) {
    if (loading.value) return
    const current = revision
    loading.value = true
    error.value = ''
    result.value = null
    previous = operation
    try {
      const response = await operation()
      if (current !== revision) return
      result.value = response
      if (response.body?.error) {
        error.value = `${response.body.error.code}: ${response.body.error.message}`
        return
      }
      const data = response.body?.data
      if (data && 'outbox' in data) {
        detail.value = data
        accepted.value = data.task
      } else if (data && 'task' in data) accepted.value = data.task
      else if (data && 'database_counts' in data) queue.value = data
    } catch (failure) {
      if (current === revision)
        error.value = `${failure instanceof Error ? failure.message : '请求失败'}；结果待确认，请保留原 UUID 重试。`
    } finally {
      loading.value = false
    }
  }
  function prepare() {
    error.value = ''
    if (
      !Number.isSafeInteger(orderId.value) ||
      orderId.value < 1 ||
      !Number.isInteger(maxAttempts.value) ||
      maxAttempts.value < 1 ||
      maxAttempts.value > 5 ||
      !Number.isInteger(failFirst.value) ||
      failFirst.value < 0 ||
      failFirst.value > 5 ||
      !Number.isInteger(delayMs.value) ||
      delayMs.value < 0 ||
      delayMs.value > 5000
    ) {
      error.value = '检查订单正整数、尝试1..5、失败0..5、延迟0..5000ms'
      return
    }
    intent.value = {
      task_id: crypto.randomUUID(),
      order_id: orderId.value,
      max_attempts: maxAttempts.value,
      fault_plan:
        failFirst.value || delayMs.value
          ? {
              evidence_type: 'controlled_fault_configuration',
              fail_first_attempts: failFirst.value,
              delay_ms: delayMs.value,
            }
          : null,
    }
  }
  async function submit() {
    const saved = intent.value
    if (!saved) {
      error.value = '先保存任务意图'
      return
    }
    taskId.value = saved.task_id
    await send(() => api.createTask(saved))
  }
  async function refresh() {
    const id = taskId.value
    detail.value = null
    queue.value = null
    accepted.value = null
    await send(() => api.getTask(id))
  }
  async function refreshQueue() {
    const scope = detail.value?.task.scenario_id ?? accepted.value?.scenario_id
    queue.value = null
    if (!scope) {
      error.value = '先读取任务，确认其场景'
      return
    }
    await send(() => api.getQueue(scope))
  }
  async function retryFailed() {
    const parent = detail.value?.task
    if (!parent || parent.state !== 'failed') {
      error.value = '先读取一个已失败的原任务'
      return
    }
    const saved = {
      parent: parent.id,
      payload: { task_id: crypto.randomUUID(), disable_faults: true },
    }
    successor.value = saved
    taskId.value = saved.payload.task_id
    await send(() => api.retryTask(saved.parent, saved.payload))
  }
  async function retryRequest() {
    if (previous) await send(previous)
  }
  return {
    orderId,
    taskId,
    maxAttempts,
    failFirst,
    delayMs,
    loading,
    error,
    intent,
    successor,
    detail,
    queue,
    accepted,
    result,
    prepare,
    submit,
    refresh,
    refreshQueue,
    retryFailed,
    retryRequest,
  }
}
