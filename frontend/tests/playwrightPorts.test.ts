import { describe, expect, it } from 'vitest'
import { playwrightPorts } from '../config/playwrightPorts'
describe('isolated browser acceptance ports', () => {
  it('preserves defaults and accepts distinct explicit loopback ports', () => {
    expect(playwrightPorts({})).toEqual({ api: 18002, frontend: 5174, reuse: true })
    expect(
      playwrightPorts({
        PLAYWRIGHT_API_PORT: '18004',
        PLAYWRIGHT_FRONTEND_PORT: '5175',
        PLAYWRIGHT_REUSE_SERVER: 'false',
      }),
    ).toEqual({ api: 18004, frontend: 5175, reuse: false })
  })
  it('rejects shell text, invalid ranges, duplicate ports and invalid reuse flags', () => {
    for (const env of [
      { PLAYWRIGHT_API_PORT: '18004;anything' },
      { PLAYWRIGHT_API_PORT: '80' },
      { PLAYWRIGHT_API_PORT: '5174' },
      { PLAYWRIGHT_REUSE_SERVER: 'perhaps' },
    ])
      expect(() => playwrightPorts(env)).toThrow()
    expect(playwrightPorts({ CI: 'true' }).reuse).toBe(false)
  })
})
