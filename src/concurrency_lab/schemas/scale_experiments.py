"""Validated recorded009observations. No simulation or execution endpoint in this model."""

import hashlib
import json
import math
from datetime import datetime
from typing import Annotated, Literal, Self

from pydantic import Field, JsonValue, model_validator

from concurrency_lab.experiments.queries import parse_tree, percentile
from concurrency_lab.experiments.scale.queries import partition_observation
from concurrency_lab.schemas.benchmarks import ResourceSample
from concurrency_lab.schemas.observations import CollectionTimestamp
from concurrency_lab.schemas.visualization import DTO

Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
QUERIES = frozenset(
    (
        "primary_key",
        "by_user",
        "user_projection",
        "offset",
        "keyset",
        "time_range",
        "id_without_time",
    )
)
TABLES = frozenset(("scale_order", "scale_order_partitioned"))


def close(actual: float, expected: float) -> bool:
    return math.isclose(actual, expected, rel_tol=1e-9, abs_tol=1e-7)


class ScaleSource(DTO):
    revision: str = Field(pattern=r"^[0-9a-f]{40}$")
    sha256: Digest
    sources_dirty: bool
    files: int = Field(ge=1)


class TableIdentity(DTO):
    count: int = Field(ge=1, le=10000000)
    digest: Digest
    monthly_counts: dict[str, int]
    id_unique: Literal[True]

    @model_validator(mode="after")
    def valid_months(self) -> Self:
        if sum(self.monthly_counts.values()) != self.count or any(
            v < 1 for v in self.monthly_counts.values()
        ):
            raise ValueError("Monthly counts differ from exact count")
        if any(
            key not in {f"2025-{month:02d}" for month in range(1, 13)}
            for key in self.monthly_counts
        ):
            raise ValueError("Dataset outside declared2025year")
        return self


class DatasetIdentity(DTO):
    seed: int
    order_count: int = Field(ge=1, le=10000000)
    generator_version: Literal[1]
    digest: Digest
    tables: dict[str, TableIdentity]

    @model_validator(mode="after")
    def equivalent_twins(self) -> Self:
        if set(self.tables) != TABLES or any(
            v.count != self.order_count or v.digest != self.digest for v in self.tables.values()
        ):
            raise ValueError("Actual twin identity mismatch")
        if self.tables["scale_order"] != self.tables["scale_order_partitioned"]:
            raise ValueError("Twin logical datasets differ")
        return self


class QueryObservation(DTO):
    sql: str
    parameters: dict[str, JsonValue]
    warmups: Literal[1]
    repeats: int = Field(ge=3, le=30)
    client_ms_samples: list[Annotated[float, Field(gt=0)]] = Field(min_length=3, max_length=30)
    p50_ms: float = Field(gt=0)
    p95_ms: float = Field(gt=0)
    p99_ms: float = Field(gt=0)
    serial_selects_per_second: float = Field(gt=0)
    attempts: int
    failures: Literal[0]
    error_rate: float = Field(ge=0, le=0)
    result_count: int = Field(ge=0, le=20)
    result_rows: list[list[JsonValue]]
    result_sha256: Digest
    tree: str
    json_plan: dict[str, JsonValue]
    iterators: list[dict[str, JsonValue]]
    access_operator_rows: float | None = Field(default=None, ge=0)
    selected_partitions: list[str] | None
    covering_observed: bool

    @model_validator(mode="after")
    def verify_observations(self) -> Self:
        if len(self.client_ms_samples) != self.repeats or self.attempts != self.repeats:
            raise ValueError("Query sample count mismatch")
        for value, quantile in ((self.p50_ms, 0.5), (self.p95_ms, 0.95), (self.p99_ms, 0.99)):
            if not close(value, percentile(self.client_ms_samples, quantile)):
                raise ValueError("Query percentile differs from raw samples")
        if not close(
            self.serial_selects_per_second, self.repeats * 1000 / sum(self.client_ms_samples)
        ):
            raise ValueError("Serial rate differs from sample sum")
        digest = hashlib.sha256(
            json.dumps(self.result_rows, separators=(",", ":")).encode()
        ).hexdigest()
        if self.result_count != len(self.result_rows) or self.result_sha256 != digest:
            raise ValueError("Query result digest/count mismatch")
        if self.iterators != parse_tree(self.tree):
            raise ValueError("Iterator observations differ from actual TREE")
        accesses = [
            float(node["access_rows"])
            for node in parse_tree(self.tree)
            if node["access_rows"] is not None
        ]
        expected_rows = sum(accesses) if accesses else None
        if (expected_rows is None) != (self.access_operator_rows is None) or (
            expected_rows is not None
            and self.access_operator_rows is not None
            and not close(self.access_operator_rows, expected_rows)
        ):
            raise ValueError("Access row summary differs from actual iterators")
        observed = partition_observation(self.json_plan)
        if (
            self.covering_observed != observed["covering_observed"]
            or self.selected_partitions != observed["selected_partitions"]
        ):
            raise ValueError("Coverage/partitions differ from optimizer JSON")
        return self


class TableObservation(DTO):
    cursor_lookup_ms: float = Field(ge=0)
    cursor: dict[str, JsonValue]
    offset: int = Field(ge=0)
    page_ids: dict[str, list[int]]
    queries: dict[str, QueryObservation]

    @model_validator(mode="after")
    def same_page(self) -> Self:
        if set(self.queries) != QUERIES or set(self.page_ids) != {"offset", "keyset"}:
            raise ValueError("Required query/page cases missing")
        if self.page_ids["offset"] != self.page_ids["keyset"]:
            raise ValueError("OFFSET/keyset page mismatch")
        for name in ("offset", "keyset"):
            if self.page_ids[name] != [row[0] for row in self.queries[name].result_rows]:
                raise ValueError("Page identities differ from actual rows")
        return self


class ScalePhase(DTO):
    phase: Literal["baseline", "composite", "covering"]
    revision: Literal["scale001", "scale002", "scale003"]
    started_at: CollectionTimestamp
    finished_at: CollectionTimestamp
    source: ScaleSource
    dataset: DatasetIdentity
    repeats: int = Field(ge=3, le=30)
    tables: dict[str, TableObservation]
    statistics: dict[str, JsonValue]
    mysql_before: dict[str, JsonValue]
    mysql_after: dict[str, JsonValue]
    environment: dict[str, JsonValue]

    @model_validator(mode="after")
    def compare_queries(self) -> Self:
        if set(self.tables) != TABLES:
            raise ValueError("Required twin observations missing")
        if {"baseline": "scale001", "composite": "scale002", "covering": "scale003"}[
            self.phase
        ] != self.revision:
            raise ValueError("Phase revision mismatch")
        for name in QUERIES:
            a, b = (
                self.tables[table].queries[name]
                for table in ("scale_order", "scale_order_partitioned")
            )
            if (
                a.result_sha256 != b.result_sha256
                or a.repeats != self.repeats
                or b.repeats != self.repeats
            ):
                raise ValueError("Twin results or repeat count differ")
        if datetime.fromisoformat(self.finished_at) < datetime.fromisoformat(self.started_at):
            raise ValueError("Phase window is reversed")
        return self


class WriteBatch(DTO):
    rows: int = Field(ge=1, le=10000)
    execute_commit_ms: float = Field(gt=0)


class WriteProbe(DTO):
    table: str
    identity: TableIdentity
    batches: list[WriteBatch] = Field(min_length=1, max_length=10000)
    total_execute_commit_ms: float = Field(gt=0)
    rows_per_sql_second: float = Field(gt=0)
    p50_batch_ms: float = Field(gt=0)
    p95_batch_ms: float = Field(gt=0)
    p99_batch_ms: float = Field(gt=0)
    failures: Literal[0]

    @model_validator(mode="after")
    def verify_batches(self) -> Self:
        samples = [b.execute_commit_ms for b in self.batches]
        if not samples or sum(b.rows for b in self.batches) != self.identity.count:
            raise ValueError("Committed batch rows mismatch")
        if not close(sum(samples), self.total_execute_commit_ms) or not close(
            self.identity.count * 1000 / sum(samples), self.rows_per_sql_second
        ):
            raise ValueError("Write rate differs from raw batches")
        for value, quantile in (
            (self.p50_batch_ms, 0.5),
            (self.p95_batch_ms, 0.95),
            (self.p99_batch_ms, 0.99),
        ):
            if not close(value, percentile(samples, quantile)):
                raise ValueError("Write percentile differs from raw batches")
        return self


class WriteComparison(DTO):
    started_at: CollectionTimestamp
    finished_at: CollectionTimestamp
    wall_seconds: float = Field(gt=0)
    rows_per_probe: int = Field(ge=1, le=50000)
    batch_size: int = Field(ge=1, le=10000)
    layout_order_per_batch: list[list[str]]
    probes: dict[str, WriteProbe]
    statistics: dict[str, JsonValue]
    semantics: str

    @model_validator(mode="after")
    def equivalent_probes(self) -> Self:
        if (
            set(self.probes) != {"single", "composite", "covering"}
            or len({probe.identity.digest for probe in self.probes.values()}) != 1
        ):
            raise ValueError("Write layouts/data differ")
        if any(p.identity.count != self.rows_per_probe for p in self.probes.values()):
            raise ValueError("Probe count differs from requested count")
        if any(set(order) != set(self.probes) for order in self.layout_order_per_batch):
            raise ValueError("Probe execution order missing layout")
        if any(
            len(probe.batches) != len(self.layout_order_per_batch) for probe in self.probes.values()
        ):
            raise ValueError("Probe order count differs from actual batches")
        return self


class ScaleManifest(DTO):
    id: str = Field(pattern=r"^scale-[0-9]{8}T[0-9]{6}-[0-9a-f]{8}$")
    database: str = Field(pattern=r"^concurrency_lab_exp_009_(test|10000|100000|1000000|10000000)$")
    source: ScaleSource
    started_at: CollectionTimestamp
    finished_at: CollectionTimestamp
    duration_seconds: float = Field(gt=0)
    order_count: int = Field(ge=1, le=10000000)
    seed: int
    batch_size: int = Field(ge=1, le=10000)
    repeats: int = Field(ge=3, le=30)
    container: dict[str, JsonValue] | None = None


class ScaleRun(DTO):
    schema_version: Literal[1]
    evidence: Literal["recorded"]
    complete: Literal[True]
    manifest: ScaleManifest
    generation: dict[str, JsonValue]
    migrations: list[dict[str, JsonValue]]
    phases: list[ScalePhase]
    writes: WriteComparison
    resources: list[ResourceSample]
    definitions: dict[str, str]
    limitations: list[str]

    @model_validator(mode="after")
    def validate_comparison(self) -> Self:
        if [phase.phase for phase in self.phases] != ["baseline", "composite", "covering"]:
            raise ValueError("Required baseline-first phase order missing")
        first = self.phases[0]
        if (
            first.dataset.order_count != self.manifest.order_count
            or first.dataset.seed != self.manifest.seed
        ):
            raise ValueError("Manifest dataset mismatch")
        for phase in self.phases:
            if (
                phase.dataset != first.dataset
                or phase.source != self.manifest.source
                or phase.repeats != self.manifest.repeats
            ):
                raise ValueError("Phase source/dataset/repeats changed")
            for table in TABLES:
                for query in QUERIES:
                    if (
                        phase.tables[table].queries[query].result_sha256
                        != first.tables[table].queries[query].result_sha256
                    ):
                        raise ValueError("Result identity changed across phases")
                    if (
                        phase.tables[table].queries[query].sql
                        != first.tables[table].queries[query].sql
                        or phase.tables[table].queries[query].parameters
                        != first.tables[table].queries[query].parameters
                    ):
                        raise ValueError("SQL/parameters changed across phases")
        start, end = (
            datetime.fromisoformat(value).timestamp()
            for value in (self.manifest.started_at, self.manifest.finished_at)
        )
        if end <= start or abs((end - start) - self.manifest.duration_seconds) > 0.5:
            raise ValueError("UTC/monotonic run window mismatch")
        previous = start
        for phase in self.phases:
            phase_start, phase_end = (
                datetime.fromisoformat(value).timestamp()
                for value in (phase.started_at, phase.finished_at)
            )
            if not previous <= phase_start <= phase_end <= end:
                raise ValueError("Phase windows overlap or escape actual run")
            previous = phase_end
        if (
            not previous
            <= datetime.fromisoformat(self.writes.started_at).timestamp()
            <= datetime.fromisoformat(self.writes.finished_at).timestamp()
            <= end
        ):
            raise ValueError("Write probe window overlaps immutable query phases")
        if any(
            not start <= datetime.fromisoformat(point.observed_at).timestamp() <= end
            or point.elapsed_s > self.manifest.duration_seconds + 0.5
            for point in self.resources
        ):
            raise ValueError("Resource outside actual run window")
        return self


class ScaleSummary(DTO):
    manifest: ScaleManifest
    phases: list[str]
    limitations: list[str]
