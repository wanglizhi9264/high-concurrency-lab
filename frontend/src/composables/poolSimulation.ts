export interface PoolParameters {
  requests: number
  size: number
  overflow: number
  timeout: number
  duration: number
}
export interface PoolFrame {
  at: number
  action: string
  request: number | null
  slots: (number | null)[]
  waiting: number[]
  completed: number[]
  timedOut: number[]
}
export function simulatePool(p: PoolParameters): PoolFrame[] {
  if (
    !Number.isInteger(p.requests) ||
    p.requests < 1 ||
    p.requests > 50 ||
    !Number.isInteger(p.size) ||
    p.size < 1 ||
    p.size > 10 ||
    !Number.isInteger(p.overflow) ||
    p.overflow < 0 ||
    p.overflow > 10 ||
    !Number.isFinite(p.timeout) ||
    p.timeout < 100 ||
    p.timeout > 10000 ||
    !Number.isFinite(p.duration) ||
    p.duration < 100 ||
    p.duration > 10000
  )
    throw new Error('模拟参数超出教学范围')
  const slots: (number | null)[] = Array.from({ length: p.size + p.overflow }, () => null)
  const waiting = Array.from({ length: p.requests }, (_, i) => i + 1),
    completed: number[] = [],
    timedOut: number[] = [],
    running = new Map<number, { end: number; slot: number }>(),
    frames: PoolFrame[] = []
  const emit = (at: number, action: string, request: number | null) =>
    frames.push({
      at,
      action,
      request,
      slots: [...slots],
      waiting: [...waiting],
      completed: [...completed],
      timedOut: [...timedOut],
    })
  function assign(at: number) {
    for (let slot = 0; slot < slots.length && waiting.length; slot++) {
      if (slots[slot] !== null) continue
      const request = waiting.shift()!
      slots[slot] = request
      running.set(request, { end: at + p.duration, slot })
      emit(at, '借出连接', request)
    }
  }
  emit(0, '所有请求到达，进入FIFO队列', null)
  assign(0)
  while (running.size || waiting.length) {
    const completion = running.size
      ? Math.min(...[...running.values()].map((v) => v.end))
      : Infinity
    const deadline = waiting.length ? p.timeout : Infinity
    const at = Math.min(completion, deadline)
    for (const [request, active] of [...running])
      if (active.end === at) {
        running.delete(request)
        slots[active.slot] = null
        completed.push(request)
        emit(at, '归还连接', request)
      }
    if (at <= p.timeout) assign(at)
    if (waiting.length && at >= p.timeout) {
      while (waiting.length) timedOut.push(waiting.shift()!)
      emit(at, '队列等待超时', null)
    }
  }
  return frames
}
