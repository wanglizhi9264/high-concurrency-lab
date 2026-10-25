/** Shared observation envelope, independent of any business payload. */
export interface BusinessSpan {
  id: string
  parent_id: string | null
  name: string
  kind: string
  source: string
  start_ms: number
  duration_ms: number
  state: 'success' | 'error' | 'timeout' | 'cancelled'
  sql: string | null
  parameters: Record<string, unknown>
  result_count: number | null
}
export interface BusinessTrace {
  request_id: string
  evidence: 'measured'
  observed_at: string
  unit: 'ms'
  environment: Record<string, string>
  service_elapsed_ms: number
  database: string
  spans: BusinessSpan[]
  pool_before: Record<string, number>
  pool_after: Record<string, number>
  pool_before_offset_ms: number | null
  pool_after_offset_ms: number | null
  definitions: Record<string, string>
}
export interface ObservedResponse {
  error: { code: string; message: string } | null
  trace: BusinessTrace
}
export interface ObservedRequestResult<T extends ObservedResponse> {
  body: T | null
  status: number
  path: string
  browserMs: number
  preparationMs: string | null
  requestId: string | null
}
