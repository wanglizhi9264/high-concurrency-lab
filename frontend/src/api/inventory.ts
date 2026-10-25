import { executeObservedRequest } from './observed'
import type { InventoryResponse, SavedOrderIntent, ScenarioIntent } from '../types/inventory'

const base = '/api/v1/business'
const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
export function requireUuid(value: string) {
  if (!uuidPattern.test(value)) throw new Error('需要完整 UUID；先创建库存场景或保存订单意图')
  return value
}
export function createScenario(intent: ScenarioIntent) {
  requireUuid(intent.scenario_id)
  return executeObservedRequest<InventoryResponse>(`${base}/inventory/scenarios`, {
    method: 'POST',
    body: intent,
  })
}
export function submitOrder(intent: SavedOrderIntent) {
  requireUuid(intent.key)
  requireUuid(intent.payload.scenario_id)
  return executeObservedRequest<InventoryResponse>(`${base}/purchases/orders`, {
    method: 'POST',
    body: intent.payload,
    headers: { 'Idempotency-Key': intent.key },
  })
}
export function readScenario(id: string, audit = false) {
  return executeObservedRequest<InventoryResponse>(
    `${base}/inventory/scenarios/${requireUuid(id)}${audit ? '/audit' : ''}`,
  )
}
export function readOrderByKey(key: string) {
  return executeObservedRequest<InventoryResponse>(
    `${base}/purchases/orders/by-key/${requireUuid(key)}`,
  )
}
export function transitionOrder(id: number, target: 'paid' | 'cancelled') {
  if (!Number.isSafeInteger(id) || id < 1) throw new Error('需要有效订单 ID')
  return executeObservedRequest<InventoryResponse>(`${base}/purchases/orders/${id}/state`, {
    method: 'POST',
    body: { target },
  })
}
