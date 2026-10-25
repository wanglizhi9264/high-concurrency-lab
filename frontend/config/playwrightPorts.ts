export function playwrightPorts(env: Record<string, string | undefined>) {
  function port(value: string | undefined, fallback: number) {
    if (value === undefined) return fallback
    if (!/^\d+$/.test(value) || Number(value) < 1024 || Number(value) > 65535)
      throw new Error('Playwright ports must be numeric1024..65535')
    return Number(value)
  }
  const api = port(env.PLAYWRIGHT_API_PORT, 18002),
    frontend = port(env.PLAYWRIGHT_FRONTEND_PORT, 5174)
  if (api === frontend) throw new Error('API/frontend ports must differ')
  if (
    env.PLAYWRIGHT_REUSE_SERVER !== undefined &&
    !['true', 'false'].includes(env.PLAYWRIGHT_REUSE_SERVER)
  )
    throw new Error('Explicit reuse flag must be true/false')
  const reuse =
    env.PLAYWRIGHT_REUSE_SERVER === undefined ? !env.CI : env.PLAYWRIGHT_REUSE_SERVER === 'true'
  return { api, frontend, reuse }
}
