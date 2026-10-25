import type { IteratorMetric } from './index'
import type { ResourceSample } from './benchmarks'
export type PhaseName = 'baseline' | 'composite' | 'covering'
export type TableName = 'scale_order' | 'scale_order_partitioned'
export type QueryName =
  | 'primary_key'
  | 'by_user'
  | 'user_projection'
  | 'offset'
  | 'keyset'
  | 'time_range'
  | 'id_without_time'
export interface ScaleSource {
  revision: string
  sha256: string
  sources_dirty: boolean
  files: number
}
export interface ScaleManifest {
  id: string
  database: string
  source: ScaleSource
  started_at: string
  finished_at: string
  duration_seconds: number
  order_count: number
  seed: number
  batch_size: number
  repeats: number
  container: Record<string, unknown> | null
}
export interface ScaleSummary {
  manifest: ScaleManifest
  phases: string[]
  limitations: string[]
}
export interface QueryObservation {
  sql: string
  parameters: Record<string, unknown>
  warmups: number
  repeats: number
  client_ms_samples: number[]
  p50_ms: number
  p95_ms: number
  p99_ms: number
  serial_selects_per_second: number
  attempts: number
  failures: number
  error_rate: number
  result_count: number
  result_rows: unknown[][]
  result_sha256: string
  tree: string
  json_plan: Record<string, unknown>
  iterators: IteratorMetric[]
  access_operator_rows: number | null
  selected_partitions: string[] | null
  covering_observed: boolean
}
export interface TableObservation {
  cursor_lookup_ms: number
  cursor: Record<string, unknown>
  offset: number
  page_ids: Record<string, number[]>
  queries: Record<QueryName, QueryObservation>
}
export interface ScaleStatistics {
  observed_at?: string
  show_create?: Record<string, string>
  indexes?: Record<string, unknown[]>
  tables?: {
    table_name: string
    estimated_rows: number | null
    clustered_bytes_estimate: number | null
    secondary_bytes_estimate: number | null
  }[]
  partitions?: Record<string, unknown>[]
  index_pages?: Record<string, unknown>[] | null
  index_pages_error?: string | null
  semantics?: string
}
export interface ScalePhase {
  phase: PhaseName
  revision: string
  started_at: string
  finished_at: string
  source: ScaleSource
  dataset: { seed: number; order_count: number; digest: string; tables: Record<string, unknown> }
  repeats: number
  tables: Record<TableName, TableObservation>
  statistics: ScaleStatistics
  mysql_before: Record<string, unknown>
  mysql_after: Record<string, unknown>
  environment: Record<string, unknown>
}
export interface WriteProbe {
  table: string
  identity: { count: number; digest: string }
  batches: { rows: number; execute_commit_ms: number }[]
  total_execute_commit_ms: number
  rows_per_sql_second: number
  p50_batch_ms: number
  p95_batch_ms: number
  p99_batch_ms: number
  failures: number
}
export interface ScaleRun {
  schema_version: 1
  evidence: 'recorded'
  complete: true
  manifest: ScaleManifest
  generation: Record<string, unknown>
  migrations: Record<string, unknown>[]
  phases: ScalePhase[]
  writes: {
    started_at: string
    finished_at: string
    wall_seconds: number
    rows_per_probe: number
    batch_size: number
    layout_order_per_batch: string[][]
    probes: Record<string, WriteProbe>
    statistics: ScaleStatistics
    semantics: string
  }
  resources: ResourceSample[]
  definitions: Record<string, string>
  limitations: string[]
}
