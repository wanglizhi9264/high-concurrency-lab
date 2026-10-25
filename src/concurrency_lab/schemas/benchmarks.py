"""Recorded load evidence and live monitoring use distinct validated models."""

from typing import Literal, Self

from pydantic import Field, JsonValue, model_validator

from concurrency_lab.schemas.visualization import DTO


class LoadParameters(DTO):
    users: Literal[10, 50, 100, 500]
    seconds: int = Field(ge=5, le=300)
    task_rate: float = Field(ge=0.2, le=5)
    spawn_rate: float = Field(gt=0, le=1000)
    pool_size: int = Field(ge=1, le=50)
    scenario: Literal["mixed", "hot", "normal", "deep"] = "mixed"


class BusinessMetrics(DTO):
    evidence: Literal["measured"] = "measured"
    observed_at: str
    collection_ms: float = Field(ge=0)
    status: Literal["ok", "unavailable", "disabled"]
    database: str
    pool: dict[str, int]
    configuration: dict[str, JsonValue]
    dataset: dict[str, JsonValue] | None = None
    mysql_version: str | None = None
    mysql_status: dict[str, int] | None = None
    error_code: str | None = None


class LoadSummary(DTO):
    requests: int = Field(ge=0)
    failures: int = Field(ge=0)
    completed_rps: float = Field(ge=0)
    error_rate: float = Field(ge=0, le=1)
    p50_ms: float | None = Field(default=None, ge=0)
    p95_ms: float | None = Field(default=None, ge=0)
    p99_ms: float | None = Field(default=None, ge=0)
    observed_sql_attempts_per_s: float | None = Field(default=None, ge=0)
    unknown_sql_responses: int = Field(ge=0)
    sql_response_coverage: float = Field(ge=0, le=1)
    http_504: int = Field(ge=0)
    pool_timeouts: int = Field(ge=0)
    transport_timeouts: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_counts(self) -> Self:
        if self.failures > self.requests or self.unknown_sql_responses > self.requests:
            raise ValueError("Invalid request counts")
        return self


class LoadHistorySample(DTO):
    elapsed_s: float = Field(ge=0)
    interval_s: float = Field(gt=0)
    completed: int = Field(ge=0)
    completed_rps: float = Field(ge=0)
    failures: int = Field(ge=0)
    observed_sql_attempts_per_s: float | None


class ResourceSample(DTO):
    observed_at: str
    elapsed_s: float = Field(ge=0)
    scope: str
    source: str
    cpu_percent: float | None = Field(default=None, ge=0)
    memory_bytes: int | None = Field(default=None, ge=0)
    memory_limit_bytes: int | None = Field(default=None, ge=0)
    business: BusinessMetrics | None = None
    raw: dict[str, JsonValue] | None = None
    error_code: str | None = None


class LoadManifest(DTO):
    id: str = Field(pattern=r"^load-[0-9]{8}T[0-9]{6}-[0-9a-f]{8}$")
    start_epoch: float
    end_epoch: float
    duration_s: float = Field(gt=0)
    parameters: LoadParameters
    peak_users: int = Field(ge=0)
    dataset: dict[str, JsonValue]
    environment: dict[str, JsonValue]
    raw_files: list[str]

    @model_validator(mode="after")
    def validate_window(self) -> Self:
        if self.end_epoch <= self.start_epoch:
            raise ValueError("Invalid measurement window")
        return self


class RecordedLoadRun(DTO):
    schema_version: Literal[1] = 1
    evidence: Literal["recorded"] = "recorded"
    complete: Literal[True] = True
    manifest: LoadManifest
    summary: LoadSummary
    history: list[LoadHistorySample]
    resources: list[ResourceSample]
    locust_statistics: list[dict[str, str]]
    semantics: dict[str, str]
    limitations: list[str]

    @model_validator(mode="after")
    def validate_history(self) -> Self:
        offsets = [point.elapsed_s for point in self.history]
        if offsets != sorted(set(offsets)):
            raise ValueError("History must have distinct increasing offsets")
        if sum(point.completed for point in self.history) != self.summary.requests:
            raise ValueError("History count mismatch")
        return self


class BenchmarkSummary(DTO):
    manifest: LoadManifest
    summary: LoadSummary
