import type { ObservedRequestResult, ObservedResponse } from '../types/observed'

export interface ObservedRequestOptions {
  method?: 'GET' | 'POST' | 'DELETE'
  body?: unknown
  headers?: Record<string, string>
}
export async function executeObservedRequest<T extends ObservedResponse>(
  path: string,
  options: ObservedRequestOptions = {},
): Promise<ObservedRequestResult<T>> {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), 65000)
  const started = performance.now()
  try {
    const response = await fetch(path, {
      method: options.method ?? 'GET',
      signal: controller.signal,
      headers: {
        ...(options.body === undefined ? {} : { 'Content-Type': 'application/json' }),
        ...options.headers,
      },
      ...(options.body === undefined ? {} : { body: JSON.stringify(options.body) }),
    })
    const body = await response.json()
    if (!body.trace?.request_id || !Array.isArray(body.trace.spans))
      throw new Error(`HTTP ${response.status}：请求未进入业务执行；请检查参数、代理和后端。`)
    return {
      body,
      status: response.status,
      path,
      browserMs: performance.now() - started,
      preparationMs: response.headers.get('x-process-time-ms'),
      requestId: response.headers.get('x-request-id'),
    }
  } finally {
    clearTimeout(timeout)
  }
}
