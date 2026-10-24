import { describe, it, expect } from 'vitest'
import { simulateProbe, type ProbeScenario } from '../src/lib/probeSimulation'

describe('probe outcome teaching', () => {
  it.each<[ProbeScenario, number, string, string]>([
    ['success', 200, 'ok', 'ok'],
    ['mysql-failure', 503, 'unavailable', 'ok'],
    ['redis-failure', 503, 'ok', 'unavailable'],
    ['mysql-timeout', 503, 'unavailable', 'ok'],
  ])('keeps independent branch outcomes for %s', (scenario, status, mysql, redis) => {
    const trace = simulateProbe(scenario)
    expect(trace.http_status).toBe(status)
    expect(trace.checks).toEqual({ mysql, redis })
    expect(trace.events.every((event) => event.evidence === 'simulation')).toBe(true)
    expect(
      trace.events.find((event) => event.component === 'client' && event.name === '浏览器读取响应')
        ?.state,
    ).toBe(status === 200 ? 'success' : 'failure')
    expect(
      trace.events.filter(
        (event) => ['mysql', 'redis'].includes(event.component) && event.state !== 'running',
      ),
    ).toHaveLength(2)
  })
})
