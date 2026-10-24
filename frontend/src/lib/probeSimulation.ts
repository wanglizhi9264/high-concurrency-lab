import type { TraceEvent, TraceResponse } from '../types'

export type ProbeScenario = 'success' | 'mysql-failure' | 'redis-failure' | 'mysql-timeout'
export const probeScenarios: { value: ProbeScenario; label: string }[] = [
  { value: 'success', label: '两项成功 → 200' },
  { value: 'mysql-failure', label: 'MySQL 失败 → 503' },
  { value: 'redis-failure', label: 'Redis 失败 → 503' },
  { value: 'mysql-timeout', label: 'MySQL 超时 → 503' },
]
export function simulateProbe(scenario: ProbeScenario): TraceResponse {
  const mysqlOk = scenario === 'success' || scenario === 'redis-failure'
  const redisOk = scenario !== 'redis-failure'
  const events: TraceEvent[] = []
  function emit(component: string, name: string, state: TraceEvent['state'], detail: string) {
    events.push({
      id: `simulation-${events.length}`,
      component,
      name,
      state,
      detail,
      offset_ms: 0,
      source: 'teaching.preset',
      evidence: 'simulation',
    })
  }
  emit(
    'client',
    '浏览器发送 GET',
    'running',
    'GET /api/v1/observability/health-trace；无请求体。教学模式不会真的发送这个请求。',
  )
  emit('router', '路由进入 health_trace', 'running', '获取 lifespan 共享资源，创建本次请求记录器。')
  emit(
    'service',
    'readiness 并发启动',
    'running',
    'asyncio.gather 同时调度两个 observed → bounded_check；下面的列表顺序仅为教学展开，不能当成串行依赖。',
  )
  emit(
    'mysql',
    'MySQL 获取连接并执行 SELECT 1',
    'running',
    'engine.connect() 借连接；SELECT 1 不读订单表，退出作用域归还连接。',
  )
  emit('redis', 'Redis 执行 PING', 'running', 'await client.ping()，不查询任何业务缓存键。')
  // Independent parallel branches: one valid completion ordering, no artificial timing.
  emit(
    'redis',
    redisOk ? 'Redis 返回 PONG' : 'Redis 检查失败',
    redisOk ? 'success' : 'failure',
    redisOk
      ? 'redis-py 解析为 True，checks.redis = ok。MySQL 仍可继续运行。'
      : '假设 Redis 命令抛出连接异常；bounded_check 捕获后返回 False，checks.redis = unavailable。MySQL 不被跳过。',
  )
  emit(
    'mysql',
    mysqlOk
      ? 'MySQL 正常归还连接'
      : scenario === 'mysql-timeout'
        ? 'MySQL 超过检查预算'
        : 'MySQL 检查失败',
    mysqlOk ? 'success' : 'failure',
    mysqlOk
      ? 'SQL 与连接作用域正常结束，函数返回 True，checks.mysql = ok。'
      : scenario === 'mysql-timeout'
        ? '假设 MySQL 操作一直未完成：asyncio.timeout 取消该检查，bounded_check 返回 False。公开结果为 unavailable，并没有单独 timeout 字段。'
        : '假设获取 MySQL 连接时抛出认证异常；bounded_check 返回 False。这里只是假设，真实 API 不公开异常原因。',
  )
  const healthy = mysqlOk && redisOk
  emit(
    'service',
    '聚合两个检查结果',
    healthy ? 'success' : 'failure',
    healthy
      ? 'all(check == ok) 为 True → 就绪。'
      : '至少一个 unavailable，all(check == ok) 为 False → 不就绪；另一项成功也不能变成 200。',
  )
  emit(
    'router',
    `准备 HTTP ${healthy ? 200 : 503} JSON`,
    healthy ? 'success' : 'failure',
    '响应包含 mode、http_status、checks、events。事件列表和时钟是假设教学数据。',
  )
  emit(
    'client',
    '浏览器读取响应',
    healthy ? 'success' : 'failure',
    healthy
      ? '展示两个 ok。200 只证明这次探针通过，不证明订单功能或缓存命中。'
      : '收到 HTTP 503 并展示结构化结果；这与没有响应的 Failed to fetch 不同。',
  )
  return {
    mode: 'simulation',
    http_status: healthy ? 200 : 503,
    checks: { mysql: mysqlOk ? 'ok' : 'unavailable', redis: redisOk ? 'ok' : 'unavailable' },
    server_elapsed_ms: 0,
    events,
    limitations: [
      'Simulation：故障、完成顺序均为教学假设，不访问数据库，不停止服务，无模拟性能数值。',
    ],
  }
}
