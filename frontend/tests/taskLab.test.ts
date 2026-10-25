import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import * as api from '../src/api/tasks'
import { useTaskLab } from '../src/composables/useTaskLab'
import TaskLabView from '../src/views/TaskLabView.vue'
import type { TaskRequestResult, TaskResponse } from '../src/types/tasks'

const response = (data: unknown): TaskRequestResult => ({
  status: 200,
  path: '/fixture',
  browserMs: 1,
  preparationMs: null,
  requestId: 'fixture',
  body: {
    data: data as TaskResponse['data'],
    error: null,
    trace: {
      request_id: 'fixture',
      spans: [],
      evidence: 'measured',
      unit: 'ms',
      database: 'fixture',
      observed_at: 'fixture',
      definitions: {},
      pool_before: {},
      pool_after: {},
      environment: {},
      service_elapsed_ms: 1,
      pool_before_offset_ms: null,
      pool_after_offset_ms: null,
    },
  },
})

afterEach(() => vi.restoreAllMocks())
describe('task lifecycle presentation contracts', () => {
  it('retains original UUID and fault configuration on an unknown POST outcome', async () => {
    vi.spyOn(api, 'createTask').mockRejectedValue(new Error('connection lost'))
    const lab = useTaskLab()
    lab.orderId.value = 42
    lab.failFirst.value = 1
    lab.prepare()
    const saved = structuredClone(lab.intent.value!)
    lab.failFirst.value = 2
    await lab.submit()
    await lab.retryRequest()
    expect(api.createTask).toHaveBeenNthCalledWith(1, saved)
    expect(api.createTask).toHaveBeenNthCalledWith(2, saved)
    expect(lab.error.value).toContain('结果待确认')
  })
  it('clears task and queue evidence when changing selected context', () => {
    const lab = useTaskLab()
    lab.taskId.value = crypto.randomUUID()
    lab.detail.value = {} as never
    lab.queue.value = {} as never
    lab.taskId.value = crypto.randomUUID()
    expect(lab.detail.value).toBeNull()
    expect(lab.queue.value).toBeNull()
    lab.prepare()
    lab.orderId.value = 99
    expect(lab.intent.value).toBeNull()
  })
  it('does not call an unavailable queue zero backlog or invent a live worker', () => {
    const view = mount(TaskLabView, {
      props: { initialOrderId: '' },
      global: { stubs: { BusinessTracePanel: true } },
    })
    expect(view.text()).toContain('XLEN')
    expect(view.text()).toContain('不证明进程存活')
    expect(view.text()).toContain('尚未采集')
    expect(view.text()).toContain('受控故障配置')
    expect(view.text()).not.toContain('worker 在线')
  })
  it('keeps the linked successor intent on a failed POST, without resetting the parent', async () => {
    vi.spyOn(api, 'retryTask').mockRejectedValue(new Error('ACK unknown'))
    const lab = useTaskLab()
    const parent = crypto.randomUUID()
    lab.detail.value = { task: { id: parent, state: 'failed' } } as never
    await lab.retryFailed()
    const saved = structuredClone(lab.successor.value!)
    await lab.retryRequest()
    expect(saved.parent).toBe(parent)
    expect(saved.payload.task_id).not.toBe(parent)
    expect(api.retryTask).toHaveBeenNthCalledWith(1, parent, saved.payload)
    expect(api.retryTask).toHaveBeenNthCalledWith(2, parent, saved.payload)
  })
  it('ignores a delayed response belonging to a previously selected task', async () => {
    let finish!: (value: TaskRequestResult) => void
    vi.spyOn(api, 'getTask').mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve
        }),
    )
    const lab = useTaskLab()
    lab.taskId.value = crypto.randomUUID()
    const operation = lab.refresh()
    lab.taskId.value = crypto.randomUUID()
    finish(response({ task: { id: 'old' }, replayed: false }))
    await operation
    expect(lab.accepted.value).toBeNull()
    expect(lab.result.value).toBeNull()
    expect(lab.loading.value).toBe(false)
  })
})
