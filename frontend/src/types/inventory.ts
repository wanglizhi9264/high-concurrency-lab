import type { ObservedResponse, ObservedRequestResult } from './observed'

export interface InventoryScenario {
  id: string
  product_id: number
  initial: number
  available: number
  reserved: number
  sold: number
  created_at: string
}
export interface PurchaseOrder {
  id: number
  scenario_id: string
  user_id: number
  idempotency_key: string
  quantity: number
  unit_price: string
  total: string
  status: 'reserved' | 'paid' | 'cancelled'
  created_at: string
  updated_at: string
}
export interface ScenarioResult {
  scenario: InventoryScenario
  replayed: boolean
}
export interface OrderResult {
  order: PurchaseOrder
  replayed: boolean
  applied: boolean
}
export interface InventoryAudit {
  scenario: InventoryScenario
  observed_at: string
  order_units: Record<string, number>
  order_counts: Record<string, number>
  checks: Record<string, boolean>
  all_pass: boolean
}
export interface InventoryResponse extends ObservedResponse {
  data: ScenarioResult | OrderResult | InventoryAudit | null
}
export type InventoryRequestResult = ObservedRequestResult<InventoryResponse>
export interface OrderPayload {
  scenario_id: string
  user_id: number
  quantity: number
}
export interface SavedOrderIntent {
  key: string
  payload: OrderPayload
}
export interface ScenarioIntent {
  scenario_id: string
  product_id: number
  initial: number
}
export interface ContestSample {
  intent: SavedOrderIntent
  result: InventoryRequestResult | null
  error: string | null
}
