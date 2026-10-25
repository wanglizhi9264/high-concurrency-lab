import { request } from './index'
import type { BenchmarkSummary, RecordedLoadRun } from '../types/benchmarks'

export async function listBenchmarks(): Promise<BenchmarkSummary[]> {
  const value = await request<BenchmarkSummary[]>('/benchmarks')
  if (!Array.isArray(value)) throw new Error('压测目录格式错误')
  return value
}
export async function getBenchmark(id: string): Promise<RecordedLoadRun> {
  if (!/^load-\d{8}T\d{6}-[0-9a-f]{8}$/.test(id)) throw new Error('无效压测运行 ID')
  const value = await request<RecordedLoadRun>(`/benchmarks/${encodeURIComponent(id)}`)
  if (value.evidence !== 'recorded' || !Array.isArray(value.history) || !value.complete)
    throw new Error('压测记录不完整')
  return value
}
