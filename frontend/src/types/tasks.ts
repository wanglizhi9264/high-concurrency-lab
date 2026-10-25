import type { ObservedRequestResult, ObservedResponse } from './observed'
export interface FaultPlan {
  evidence_type: 'controlled_fault_configuration'
  fail_first_attempts: number
  delay_ms: number
}
export interface TaskInput {
  task_id: string
  order_id: number
  max_attempts: number
  fault_plan: FaultPlan | null
}
export interface Task {
  id: string
  scenario_id: string
  order_id: number
  kind: 'order_receipt'
  fault_plan: FaultPlan | null
  max_attempts: number
  attempts: number
  state: 'queued' | 'running' | 'retry_wait' | 'succeeded' | 'failed'
  available_at: string
  lease_until: string | null
  last_error: string | null
  result_receipt_id: number | null
  retry_of: string | null
  created_at: string
  updated_at: string
  finished_at: string | null
}
export interface TaskResult {
  task: Task
  replayed: boolean
}
export interface Attempt {
  number: number
  worker_id: string
  status: string
  started_at: string
  finished_at: string | null
  abandoned_at: string | null
  handler_ms: number | null
  error: string | null
  timeout_seconds: number
  lease_seconds: number
}
export interface TaskEvent {
  id: number
  occurred_at: string
  kind: string
  source: string
  details: Record<string, unknown>
}
export interface TaskDetail {
  task: Task
  outbox: {
    task_id: string
    next_publish_at: string
    publish_count: number
    last_message_id: string | null
    last_published_at: string | null
  }
  attempts: Attempt[]
  events: TaskEvent[]
  events_truncated: boolean
  receipt: {
    id: number
    order_id: number
    total: string
    snapshot: Record<string, unknown>
    created_at: string
  } | null
  worker_command: string
  source: string
  definitions: string[]
}
export interface QueueSnapshot {
  scenario_id: string
  observed_at: string
  collection_ms: number
  database_counts: Record<string, number>
  redis_available: boolean
  group_ready: boolean | null
  retained_entries: number | null
  pending: number | null
  group_lag: number | null
  pttl_ms: number | null
  source: string
  definitions: string[]
}
export interface TaskResponse extends ObservedResponse {
  data: TaskResult | TaskDetail | { tasks: Task[] } | QueueSnapshot | null
}
export type TaskRequestResult = ObservedRequestResult<TaskResponse>
