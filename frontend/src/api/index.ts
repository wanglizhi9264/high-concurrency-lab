import type {
  Architecture,
  ExperimentDetail,
  ExperimentSummary,
  ResultPair,
  QueryPlan,
  TraceResponse,
  PoolSnapshot,
  ProbeGuide,
} from '../types'
const id = '002-mysql-index-baseline'
export async function request<T>(path: string, acceptUnavailable = false): Promise<T> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), 12000)
  try {
    const response = await fetch(`/api/v1${path}`, { signal: controller.signal })
    if (!response.ok && !(acceptUnavailable && response.status === 503))
      throw new Error(`API ${response.status}：数据暂不可用，请检查后端并重试。`)
    const value: unknown = await response.json()
    if (value === null || typeof value !== 'object') throw new Error('API返回格式错误')
    return value as T
  } finally {
    clearTimeout(timer)
  }
}
export const api = {
  architecture: () => request<Architecture>('/architecture'),
  experiments: () => request<ExperimentSummary[]>('/experiments'),
  experiment: () => request<ExperimentDetail>(`/experiments/${id}`),
  results: async (scale: number) => {
    const value = await request<ResultPair>(`/experiments/${id}/results?scale=${scale}`)
    if (!value.baseline?.queries?.offset || !value.optimized?.queries?.offset)
      throw new Error('实验数据结构不完整')
    return value
  },
  plans: (scale: number, phase: string, query: string) =>
    request<QueryPlan>(
      `/experiments/${id}/query-plans?scale=${scale}&phase=${phase}&query=${query}`,
    ),
  trace: () => request<TraceResponse>('/observability/health-trace', true),
  pool: () => request<PoolSnapshot>('/observability/pool'),
  probeGuide: () => request<ProbeGuide>('/observability/probe-guide'),
}
