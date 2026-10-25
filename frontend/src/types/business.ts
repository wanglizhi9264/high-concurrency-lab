import type { ObservedResponse, ObservedRequestResult } from './observed'
export type { BusinessSpan, BusinessTrace } from './observed'
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
export interface BusinessResponse extends ObservedResponse {
  data: BusinessData | null
}
export type BusinessRequestResult<T extends BusinessResponse = BusinessResponse> =
  ObservedRequestResult<T>
export type BusinessQuery = 'product' | 'user_orders' | 'order_page' | 'order_detail'
