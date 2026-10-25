export interface LoadParameters {
  users: number
  seconds: number
  task_rate: number
  spawn_rate: number
  pool_size: number
  scenario: string
}
export interface LoadSummary {
  requests: number
  failures: number
  completed_rps: number
  error_rate: number
  p50_ms: number | null
  p95_ms: number | null
  p99_ms: number | null
  observed_sql_attempts_per_s: number | null
  unknown_sql_responses: number
  sql_response_coverage: number
  http_504: number
  pool_timeouts: number
  transport_timeouts: number
  client_started?: number | null
  client_start_rps?: number | null
  uncompleted_client_calls?: number | null
}
export interface LoadManifest {
  id: string
  start_epoch: number
  end_epoch: number
  duration_s: number
  parameters: LoadParameters
  peak_users: number
  dataset: Record<string, unknown>
  environment: Record<string, unknown>
  raw_files: string[]
}
export interface LoadHistorySample {
  elapsed_s: number
  interval_s: number
  completed: number
  completed_rps: number
  failures: number
  observed_sql_attempts_per_s: number | null
  client_started?: number | null
  client_start_rps?: number | null
}
export interface ResourceSample {
  observed_at: string
  elapsed_s: number
  scope: string
  source: string
  cpu_percent: number | null
  memory_bytes: number | null
  memory_limit_bytes: number | null
  error_code: string | null
  business: {
    observed_at: string
    status: string
    pool: Record<string, number>
    mysql_status: Record<string, number> | null
  } | null
}
export interface BenchmarkSummary {
  manifest: LoadManifest
  summary: LoadSummary
}
export interface RecordedLoadRun extends BenchmarkSummary {
  schema_version: 1
  evidence: 'recorded'
  complete: true
  history: LoadHistorySample[]
  resources: ResourceSample[]
  locust_statistics: Record<string, string>[]
  semantics: Record<string, string>
  limitations: string[]
}
export type LoadMetric =
  | 'client_start_rps'
  | 'completed_rps'
  | 'success_rps'
  | 'sql_rate'
  | 'pool_checked_out'
  | 'mysql_connections'
  | 'mysql_statement_rate'
  | 'api_cpu'
  | 'mysql_cpu'
  | 'api_memory'
  | 'mysql_memory'
