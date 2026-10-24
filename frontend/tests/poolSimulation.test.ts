import { describe, it, expect } from 'vitest'
import { simulatePool } from '../src/composables/poolSimulation'
describe('deterministic pool simulation', () => {
  it('keeps FIFO and separates deadlines from actual timings', () => {
    const frames = simulatePool({
      requests: 6,
      size: 2,
      overflow: 0,
      timeout: 1500,
      duration: 1000,
    })
    const last = frames.at(-1)!
    expect(last.completed).toEqual([1, 2, 3, 4])
    expect(last.timedOut).toEqual([5, 6])
    expect(last.slots.every((v) => v === null)).toBe(true)
    expect(frames.filter((f) => f.action === '借出连接').map((f) => f.request)).toEqual([
      1, 2, 3, 4,
    ])
  })
  it('returns and assigns before timeout at the same timestamp', () => {
    const last = simulatePool({
      requests: 2,
      size: 1,
      overflow: 0,
      timeout: 1000,
      duration: 1000,
    }).at(-1)!
    expect(last.completed).toEqual([1, 2])
    expect(last.timedOut).toEqual([])
  })
  it('bounds input and produces repeatable frames', () => {
    const p = { requests: 5, size: 1, overflow: 1, timeout: 500, duration: 1000 }
    expect(simulatePool(p)).toEqual(simulatePool(p))
    expect(() => simulatePool({ ...p, requests: 51 })).toThrow()
  })
})
