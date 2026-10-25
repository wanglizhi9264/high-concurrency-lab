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
export interface BusinessOrder {
  id: number
  user_id: number
  created_at: string
  total: string
  status: string
}
export interface BusinessCursor {
  before_time: string
  before_id: number
}
export type BusinessData =
  | { id: number; sku: string; name: string; price: string }
  | { items: BusinessOrder[]; next_cursor: BusinessCursor | null }
  | (BusinessOrder & {
      items: {
        id: number
        product_id: number
        product_name: string
        quantity: number
        unit_price: string
      }[]
    })
export interface BusinessResponse {
  data: BusinessData | null
  error: { code: string; message: string } | null
  trace: BusinessTrace
}
export interface BusinessRequestResult<T extends BusinessResponse = BusinessResponse> {
  body: T | null
  status: number
  path: string
  browserMs: number
  preparationMs: string | null
  requestId: string | null
}
export type BusinessQuery = 'product' | 'user_orders' | 'order_page' | 'order_detail'
