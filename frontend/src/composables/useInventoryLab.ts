import { ref, shallowRef, watch } from 'vue'
import * as api from '../api/inventory'
import type {
  ContestSample,
  InventoryAudit,
  InventoryRequestResult,
  InventoryScenario,
  OrderPayload,
  PurchaseOrder,
  SavedOrderIntent,
} from '../types/inventory'

export function contestSummary(samples: ContestSample[]) {
  const orders = samples.flatMap((sample) => {
    const data = sample.result?.body?.data
    return data && 'order' in data ? [data] : []
  })
  return {
    uniqueOrders: new Set(orders.map((item) => item.order.id)).size,
    created: samples.filter((sample) => sample.result?.status === 201).length,
    replays: orders.filter((item) => item.replayed).length,
    insufficient: samples.filter(
      (sample) => sample.result?.body?.error?.code === 'insufficient_stock',
    ).length,
    conflicts: samples.filter(
      (sample) => sample.result?.body?.error?.code === 'transaction_conflict',
    ).length,
    unknown: samples.filter((sample) => sample.result === null).length,
  }
}
export function useInventoryLab() {
  const productId = ref(1),
    initial = ref(5),
    scenarioId = ref(''),
    userId = ref(1),
    quantity = ref(1)
  const contestSize = ref(10),
    loading = ref(false),
    error = ref('')
  const result = shallowRef<InventoryRequestResult | null>(null)
  const scenario = shallowRef<InventoryScenario | null>(null),
    currentOrder = shallowRef<PurchaseOrder | null>(null)
  const audit = shallowRef<InventoryAudit | null>(null)
  const intent = shallowRef<SavedOrderIntent | null>(null)
  const samples = shallowRef<ContestSample[]>([])
  const history = shallowRef<InventoryRequestResult[]>([])
  let previous: (() => Promise<void>) | null = null

  watch(
    scenarioId,
    () => {
      scenario.value = null
      currentOrder.value = null
      audit.value = null
      intent.value = null
      samples.value = []
      result.value = null
      error.value = ''
    },
    { flush: 'sync' },
  )
  function accept(response: InventoryRequestResult, remember = true) {
    error.value = ''
    result.value = response
    if (remember) history.value = [...history.value, response].slice(-30)
    const body = response.body
    if (body?.error) error.value = `${body.error.code}: ${body.error.message}`
    const data = body?.data
    if (!data) return
    if ('scenario' in data) scenario.value = data.scenario
    if ('order' in data) currentOrder.value = data.order
    if ('checks' in data) audit.value = data
  }
  async function send(operation: () => Promise<InventoryRequestResult>) {
    if (loading.value) return
    loading.value = true
    error.value = ''
    result.value = null
    previous = () => send(operation)
    try {
      accept(await operation())
    } catch (failure) {
      error.value = `${failure instanceof Error ? failure.message : '未取得响应'}；结果待确认，请保留原意图查询或重放。`
    } finally {
      loading.value = false
    }
  }
  function payload(): OrderPayload {
    api.requireUuid(scenarioId.value)
    if (
      !Number.isSafeInteger(userId.value) ||
      userId.value < 1 ||
      !Number.isInteger(quantity.value) ||
      quantity.value < 1 ||
      quantity.value > 100
    )
      throw new Error('用户 ID 需为正整数，数量为 1..100 整数')
    return { scenario_id: scenarioId.value, user_id: userId.value, quantity: quantity.value }
  }
  function prepareOrder() {
    error.value = ''
    intent.value = null
    try {
      intent.value = { key: crypto.randomUUID(), payload: payload() }
    } catch (failure) {
      error.value = failure instanceof Error ? failure.message : '意图参数错误'
    }
  }
  async function createNewScenario() {
    const saved = {
      scenario_id: crypto.randomUUID(),
      product_id: productId.value,
      initial: initial.value,
    }
    scenarioId.value = saved.scenario_id
    scenario.value = null
    currentOrder.value = null
    audit.value = null
    intent.value = null
    samples.value = []
    await send(() => api.createScenario(saved))
  }
  async function submitSavedOrder() {
    const saved = intent.value
    if (!saved) {
      error.value = '请先保存新的订单意图'
      result.value = null
      return
    }
    await send(() => api.submitOrder(saved))
  }
  async function submitChangedPayload() {
    if (!intent.value) {
      error.value = '请先保存订单意图'
      return
    }
    try {
      const changed = { key: intent.value.key, payload: payload() }
      await send(() => api.submitOrder(changed))
    } catch (failure) {
      error.value = failure instanceof Error ? failure.message : '参数无效'
    }
  }
  async function confirmByKey() {
    const key = intent.value?.key
    if (!key) {
      error.value = '请先保存订单意图'
      return
    }
    await send(() => api.readOrderByKey(key))
  }
  async function inspectAudit() {
    const identifier = scenarioId.value
    await send(() => api.readScenario(identifier, true))
  }
  async function transition(target: 'paid' | 'cancelled') {
    const identifier = currentOrder.value?.id
    if (!identifier) {
      error.value = '先创建或查询一个订单'
      return
    }
    await send(() => api.transitionOrder(identifier, target))
  }
  async function runContest(saved: SavedOrderIntent[]) {
    if (loading.value) return
    loading.value = true
    error.value = ''
    result.value = null
    audit.value = null
    previous = () => runContest(saved)
    try {
      const outcomes = await Promise.allSettled(saved.map((item) => api.submitOrder(item)))
      samples.value = outcomes.map((outcome, index) => ({
        intent: saved[index]!,
        result: outcome.status === 'fulfilled' ? outcome.value : null,
        error: outcome.status === 'rejected' ? String(outcome.reason) : null,
      }))
      const response = await api.readScenario(saved[0]!.payload.scenario_id, true)
      accept(response) // An actual GET audit follows the client contest, never local guessed stock.
    } catch (failure) {
      error.value = failure instanceof Error ? failure.message : '审计未确认'
    } finally {
      loading.value = false
    }
  }
  async function startContest() {
    try {
      if (!Number.isInteger(contestSize.value) || contestSize.value < 2 || contestSize.value > 20)
        throw new Error('客户端争抢数量限制为 2..20')
      const value = payload()
      await runContest(
        Array.from({ length: contestSize.value }, () => ({
          key: crypto.randomUUID(),
          payload: { ...value },
        })),
      )
    } catch (failure) {
      error.value = failure instanceof Error ? failure.message : '参数无效'
    }
  }
  return {
    productId,
    initial,
    scenarioId,
    userId,
    quantity,
    contestSize,
    loading,
    error,
    result,
    scenario,
    currentOrder,
    audit,
    intent,
    samples,
    history,
    createNewScenario,
    prepareOrder,
    submitSavedOrder,
    submitChangedPayload,
    confirmByKey,
    inspectAudit,
    transition,
    startContest,
    retry: async () => {
      if (previous) await previous()
    },
    selectResponse: (response: InventoryRequestResult) => accept(response, false),
  }
}
