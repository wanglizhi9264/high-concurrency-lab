"""Validated public DTOs and trusted 002 evidence schema."""

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, JsonValue, model_validator


class DTO(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class SourceRef(DTO):
    path: str
    label: str
    url: str


class TraceEvent(DTO):
    id: str
    name: str
    component: str
    state: Literal["running", "waiting", "success", "failure"]
    offset_ms: float = Field(ge=0)
    source: str
    evidence: Literal["measured", "simulation"] = "measured"
    detail: str


class TraceResponse(DTO):
    mode: Literal["live"] = "live"
    http_status: Literal[200, 503]
    checks: dict[str, str]
    server_elapsed_ms: float = Field(ge=0)
    events: list[TraceEvent]
    limitations: list[str]


class ProbeGuide(DTO):
    mysql_database: str
    redis_database: Literal[0] = 0
    readiness_timeout_seconds: float = Field(gt=0)
    io_timeout_seconds: float = Field(gt=0)
    pool_timeout_seconds: float = Field(gt=0)


class ArchitectureNode(DTO):
    id: str
    label: str
    kind: str
    status: Literal["connected", "teaching", "not_implemented"]
    responsibility: str
    input: str
    output: str
    bottleneck: str
    validation: str
    source: SourceRef
    x: int
    y: int


class ArchitectureEdge(DTO):
    id: str
    source: str
    target: str
    teaching: bool = False
    label: str = ""


class Architecture(DTO):
    nodes: list[ArchitectureNode]
    edges: list[ArchitectureEdge]
    startup: list[TraceEvent]
    limitations: list[str]


class ExperimentSummary(DTO):
    id: str
    title: str
    status: str
    scales: list[int]
    source: SourceRef


class ExperimentDetail(ExperimentSummary):
    objective: str
    question: str
    hypothesis: str
    parameters: list[str]
    observations: list[str]
    explanation: list[str]
    limitations: list[str]
    sources: list[SourceRef]


class IteratorMetric(DTO):
    operator: str
    first_row_ms: float = Field(ge=0)
    iterator_ms_per_loop: float = Field(ge=0)
    actual_rows_per_loop: float = Field(ge=0)
    loops: float = Field(ge=0)
    access_rows: float | None


class QueryMetric(DTO):
    sql: str
    parameters: dict[str, JsonValue]
    result_count: int = Field(ge=0)
    wall_ms_samples: list[float] = Field(min_length=3, max_length=1000)
    p50_ms: float = Field(ge=0)
    p95_ms: float = Field(ge=0)
    p99_ms: float = Field(ge=0)
    serial_queries_per_second: float = Field(ge=0)
    error_rate: float = Field(ge=0, le=1)
    explain_analyze_tree: str
    iterators: list[IteratorMetric]
    access_operator_rows: float | None


class DatasetIdentity(DTO):
    table_checksums: dict[str, int]
    seed: int
    order_count: int
    digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    generator_version: int
    counts: dict[str, int]


class TableSize(DTO):
    table_name: str
    estimated_rows: int | None
    clustered_bytes_estimate: int = Field(ge=0)
    secondary_bytes_estimate: int = Field(ge=0)


class IndexColumn(DTO):
    table_name: str
    index_name: str
    position: int = Field(ge=1)
    column_name: str
    non_unique: Literal[0, 1]


class IndexStorage(DTO):
    table: str
    index: str
    pages: int = Field(ge=0)
    bytes_estimate: int = Field(ge=0)


class StorageSnapshot(DTO):
    tables: list[TableSize]
    indexes: list[IndexColumn]
    individual_indexes: list[IndexStorage] | None
    semantics: str


class RecordedResult(DTO):
    schema_version: Literal[1]
    recorded_at_utc: str
    database: str
    phase: Literal["baseline", "optimized"]
    revision: Literal["0002", "0003"]
    dataset: DatasetIdentity
    seed_generation: dict[str, JsonValue] | None
    repeats: int = Field(ge=3, le=1000)
    environment: dict[str, JsonValue]
    sizes: StorageSnapshot
    cursor_lookup_ms: float = Field(ge=0)
    cursor: dict[str, JsonValue]
    offset: int = Field(ge=0)
    page_ids: dict[str, list[int]]
    queries: dict[str, QueryMetric]
    scan_metric_note: str

    @model_validator(mode="after")
    def consistent(self) -> Self:
        names = {"primary_key", "by_user", "user_time", "offset", "keyset", "email"}
        if set(self.queries) != names or any(
            len(q.wall_ms_samples) != self.repeats for q in self.queries.values()
        ):
            raise ValueError("Invalid query set or sample count")
        if self.revision != ("0002" if self.phase == "baseline" else "0003"):
            raise ValueError("Phase/revision mismatch")
        if any(v < 0 for q in self.queries.values() for v in q.wall_ms_samples):
            raise ValueError("Negative measurement")
        return self


class ResultPair(DTO):
    baseline: RecordedResult
    optimized: RecordedResult
    sources: list[SourceRef]
    limitations: list[str]


class PlanNode(DTO):
    id: str
    label: str
    metrics: IteratorMetric | None
    children: list["PlanNode"] = Field(default_factory=list)


class QueryPlan(DTO):
    sql: str
    parameters: dict[str, JsonValue]
    raw_tree: str
    tree: list[PlanNode]
    source: SourceRef
    note: str


class PoolSnapshot(DTO):
    mode: Literal["live"] = "live"
    configured_size: int
    max_overflow: int
    checked_out: int
    overflow: int
    waiting: None = None
    pure_wait_ms: None = None
    observed_at: str
    note: str
