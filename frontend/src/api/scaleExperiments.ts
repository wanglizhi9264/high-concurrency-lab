import { request } from './index'
import type { ScaleRun, ScaleSummary } from '../types/scaleExperiments'
export async function listScaleExperiments(): Promise<ScaleSummary[]> {
  const value = await request<ScaleSummary[]>('/scale-experiments')
  if (!Array.isArray(value)) throw new Error('009 实验目录格式错误')
  return value
}
export async function getScaleExperiment(id: string): Promise<ScaleRun> {
  if (!/^scale-\d{8}T\d{6}-[0-9a-f]{8}$/.test(id)) throw new Error('无效的 009 运行 ID')
  const value = await request<ScaleRun>(`/scale-experiments/${encodeURIComponent(id)}`)
  if (
    !value.complete ||
    value.evidence !== 'recorded' ||
    value.manifest?.id !== id ||
    value.phases?.length !== 3
  )
    throw new Error('009 实验记录不完整或身份不匹配')
  return value
}
