import type { LoadMetric, RecordedLoadRun } from '../types/benchmarks'

export const loadMetrics: Record<LoadMetric, { label: string; unit: string }> = {
  client_start_rps: { label: '客户端调用起点率（非服务器到达）', unit: 'client calls/s' },
  completed_rps: { label: '完成 RPS（含失败）', unit: 'requests/s' },
  success_rps: { label: '成功 RPS', unit: 'successful requests/s' },
  sql_rate: { label: '收到响应中的 SQL 尝试率', unit: 'observed spans/s' },
  pool_checked_out: { label: '业务池借出连接快照', unit: 'connections' },
  mysql_connections: { label: 'MySQL 实例全部连接', unit: 'connections' },
  mysql_statement_rate: { label: 'MySQL 实例 Questions 增量率', unit: 'statements/s' },
  api_cpu: { label: 'API 进程树 CPU', unit: '%' },
  mysql_cpu: { label: 'MySQL 容器 CPU', unit: '%' },
  api_memory: { label: 'API 进程树 RSS 合计', unit: 'MiB' },
  mysql_memory: { label: 'MySQL 容器内存（CLI 估算）', unit: 'MiB' },
}
export function loadSeries(run: RecordedLoadRun, metric: LoadMetric): [number, number | null][] {
  if (metric === 'client_start_rps')
    return run.history.map((point) => [point.elapsed_s, point.client_start_rps ?? null])
  if (metric === 'completed_rps' || metric === 'success_rps' || metric === 'sql_rate') {
    return run.history.map((point) => [
      point.elapsed_s,
      metric === 'completed_rps'
        ? point.completed_rps
        : metric === 'success_rps'
          ? (point.completed - point.failures) / point.interval_s
          : point.observed_sql_attempts_per_s,
    ])
  }
  if (metric === 'mysql_statement_rate') {
    let previous: { epoch: number; questions: number; uptime: number } | null = null
    return run.resources
      .filter((sample) => sample.scope === 'business_pool_mysql_instance')
      .map((sample) => {
        const values = sample.business?.mysql_status
        const epoch = sample.business ? Date.parse(sample.business.observed_at) / 1000 : NaN
        if (!values || !Number.isFinite(epoch)) {
          previous = null
          return [sample.elapsed_s, null]
        }
        const current = { epoch, questions: values.Questions!, uptime: values.Uptime! }
        const valid =
          previous &&
          Number.isFinite(current.questions) &&
          Number.isFinite(current.uptime) &&
          current.epoch > previous.epoch &&
          current.questions >= previous.questions &&
          current.uptime >= previous.uptime
        const value =
          valid && previous
            ? (current.questions - previous.questions) / (current.epoch - previous.epoch)
            : null
        previous = current
        return [sample.elapsed_s, value]
      })
  }
  const resources = run.resources.filter((sample) =>
    metric.startsWith('mysql_') && (metric === 'mysql_cpu' || metric === 'mysql_memory')
      ? /-mysql-\d+$/.test(sample.scope)
      : metric.startsWith('api_')
        ? sample.scope === 'api_process_tree'
        : sample.scope === 'business_pool_mysql_instance',
  )
  return resources.map((sample) => [
    sample.elapsed_s,
    metric === 'pool_checked_out'
      ? (sample.business?.pool.checked_out ?? null)
      : metric === 'mysql_connections'
        ? (sample.business?.mysql_status?.Threads_connected ?? null)
        : metric.endsWith('_cpu')
          ? sample.cpu_percent
          : sample.memory_bytes === null
            ? null
            : sample.memory_bytes / 1048576,
  ])
}
