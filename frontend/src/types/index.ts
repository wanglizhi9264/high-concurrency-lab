export interface SourceRef {
  path: string
  label: string
  url: string
}
export type EventState = 'running' | 'waiting' | 'success' | 'failure'
export interface TraceEvent {
  id: string
  name: string
  component: string
  state: EventState
  offset_ms: number
  source: string
  evidence: 'measured' | 'simulation'
  detail: string
}
export interface TraceResponse {
  mode: 'live' | 'simulation'
  http_status: number
  checks: Record<string, string>
  server_elapsed_ms: number
  events: TraceEvent[]
  limitations: string[]
}
export interface ArchitectureNode {
  id: string
  label: string
  kind: string
  status: 'connected' | 'teaching' | 'not_implemented'
  responsibility: string
  input: string
  output: string
  bottleneck: string
  validation: string
  source: SourceRef
  x: number
  y: number
}
export interface Architecture {
  nodes: ArchitectureNode[]
  edges: { id: string; source: string; target: string; teaching: boolean; label: string }[]
  startup: TraceEvent[]
  limitations: string[]
}
export interface ExperimentSummary {
  id: string
  title: string
  status: string
  scales: number[]
  source: SourceRef
}
export interface ExperimentDetail extends ExperimentSummary {
  objective: string
  question: string
  hypothesis: string
  parameters: string[]
  observations: string[]
  explanation: string[]
  limitations: string[]
  sources: SourceRef[]
}
export interface IteratorMetric {
  operator: string
  first_row_ms: number
  iterator_ms_per_loop: number
  actual_rows_per_loop: number
  loops: number
  access_rows: number | null
}
export interface QueryMetric {
  sql: string
  parameters: Record<string, unknown>
  result_count: number
  wall_ms_samples: number[]
  p50_ms: number
  p95_ms: number
  p99_ms: number
  serial_queries_per_second: number
  error_rate: number
  explain_analyze_tree: string
  iterators: IteratorMetric[]
  access_operator_rows: number | null
}
export interface TableSize {
  table_name: string
  clustered_bytes_estimate: number
  secondary_bytes_estimate: number
  estimated_rows: number
}
export interface RecordedResult {
  phase: 'baseline' | 'optimized'
  recorded_at_utc: string
  dataset: { order_count: number; counts: Record<string, number>; seed: number; digest: string }
  repeats: number
  environment: Record<string, unknown>
  sizes: { tables: TableSize[]; individual_indexes: unknown[] | null }
  cursor_lookup_ms: number
  queries: Record<string, QueryMetric>
  scan_metric_note: string
}
export interface ResultPair {
  baseline: RecordedResult
  optimized: RecordedResult
  sources: SourceRef[]
  limitations: string[]
}
export interface PlanNode {
  id: string
  label: string
  metrics: IteratorMetric | null
  children: PlanNode[]
}
export interface QueryPlan {
  sql: string
  parameters: Record<string, unknown>
  raw_tree: string
  tree: PlanNode[]
  source: SourceRef
  note: string
}
export interface PoolSnapshot {
  mode: 'live'
  configured_size: number
  max_overflow: number
  checked_out: number
  overflow: number
  waiting: null
  pure_wait_ms: null
  observed_at: string
  note: string
}
