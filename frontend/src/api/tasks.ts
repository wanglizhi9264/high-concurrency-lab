import { executeObservedRequest } from './observed'
import { requireUuid } from './inventory'
import type { TaskInput, TaskResponse } from '../types/tasks'
const root = '/api/v1/business/tasks'
export const createTask = (intent: TaskInput) =>
  executeObservedRequest<TaskResponse>(root, { method: 'POST', body: intent })
export function getTask(id: string) {
  requireUuid(id)
  return executeObservedRequest<TaskResponse>(`${root}/${id}`)
}
export function getQueue(scope: string) {
  requireUuid(scope)
  return executeObservedRequest<TaskResponse>(`/api/v1/business/task-queues/${scope}`)
}
export function retryTask(id: string, intent: { task_id: string; disable_faults: boolean }) {
  requireUuid(id)
  return executeObservedRequest<TaskResponse>(`${root}/${id}/retry`, {
    method: 'POST',
    body: intent,
  })
}
