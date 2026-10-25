"""Record actual bounded product-cache operations through a loopback API. No DB reset."""

import argparse
import asyncio
import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

import httpx

from concurrency_lab.experiments.load_recording import source_identity
from concurrency_lab.experiments.queries import percentile
from concurrency_lab.schemas.business import BusinessResponse
from concurrency_lab.schemas.cache import CacheResponse

ROOT = Path(__file__).resolve().parents[1]
PRODUCT_PATH = "/api/v1/business/cache/products/1"


async def record_experiment(base_url: str, output_root: Path, concurrency: int) -> Path:
    target = urlsplit(base_url)
    if (
        target.scheme != "http"
        or target.hostname != "127.0.0.1"
        or target.username
        or target.password
        or target.path not in ("", "/")
        or target.query
        or target.fragment
        or not target.port
        or not 1024 <= target.port <= 65535
        or not 1 <= concurrency <= 20
    ):
        raise ValueError("Use an explicit loopback http://127.0.0.1:port and concurrency1..20")
    run_id = "cache-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex[:8]
    directory = output_root / run_id
    directory.mkdir(parents=True, exist_ok=False)
    observations: list[dict[str, Any]] = []
    started = datetime.now(UTC).isoformat()
    monotonic_start = time.perf_counter()
    identity = source_identity(ROOT)
    complete = False
    before = after = None
    async with httpx.AsyncClient(base_url=base_url, trust_env=False, timeout=10) as client:

        async def call(label: str, method: str = "GET", suffix: str = "") -> dict[str, Any]:
            beginning = time.perf_counter()
            row: dict[str, Any] = {
                "label": label,
                "method": method,
                "path": PRODUCT_PATH + suffix,
                "observed_at": datetime.now(UTC).isoformat(),
            }
            try:
                response = await client.request(method, PRODUCT_PATH + suffix)
                body = response.json()
                if response.status_code == 200:
                    CacheResponse.model_validate(body)
                else:
                    BusinessResponse.model_validate(body)
                row.update(
                    status=response.status_code,
                    body=body,
                    process_preparation_ms=response.headers.get("x-process-time-ms"),
                )
            except (httpx.HTTPError, ValueError) as failure:
                row.update(status=0, body=None, error_type=type(failure).__name__)
            row["client_rtt_ms"] = (time.perf_counter() - beginning) * 1000
            observations.append(row)
            return row

        try:
            before = (await client.get("/api/v1/observability/business-metrics")).json()
            for _ in range(5):
                await call("bypass", suffix="?mode=bypass")
            await call("invalidate_before_cold", "DELETE")
            await call("cold", suffix="?ttl_seconds=1")
            for _ in range(5):
                await call("hot")
            state = await call("inspection_before_wait", suffix="/state")
            ttl = (state.get("body") or {}).get("cache", {}).get("ttl_ms")
            if not isinstance(ttl, int) or not 0 < ttl <= 1100:
                raise ValueError("Expected actual short-lived key before expiry experiment")
            await asyncio.sleep(ttl / 1000 + 0.1)
            expired_state = await call("inspection_after_wait", suffix="/state")
            if (expired_state.get("body") or {}).get("cache", {}).get("ttl_ms") != -2:
                raise ValueError("Expected an observed absent key after the actual TTL wait")
            await call("read_after_ttl_wait")
            await call("active_invalidation", "DELETE")
            await call("read_after_invalidation")
            await call("invalidate_before_concurrency", "DELETE")
            await asyncio.gather(*(call("concurrent_cold") for _ in range(concurrency)))
            after = (await client.get("/api/v1/observability/business-metrics")).json()
            if any(row["status"] != 200 for row in observations):
                raise ValueError("An acceptance operation did not complete successfully")
            reads = [row for row in observations if row["body"]["data"] is not None]
            if any(row["body"]["data"] != reads[0]["body"]["data"] for row in reads):
                raise ValueError("Product copies differ")
            expected = {
                "cold": "miss",
                "hot": "hit",
                "read_after_ttl_wait": "miss",
                "read_after_invalidation": "miss",
            }
            if any(
                row["body"]["cache"]["initial_lookup"] != expected[row["label"]]
                for row in observations
                if row["label"] in expected
            ):
                raise ValueError("Expected cache sequence was not observed")
            if source_identity(ROOT)["workload_sha256"] != identity["workload_sha256"]:
                raise ValueError("Workload source changed; retain partial evidence")
            complete = True
        finally:
            groups = {}
            for label in sorted({row["label"] for row in observations}):
                rows = [row for row in observations if row["label"] == label]
                latencies = [row["client_rtt_ms"] for row in rows]
                spans = [
                    span
                    for row in rows
                    for span in (row.get("body") or {}).get("trace", {}).get("spans", [])
                    if span["kind"] == "sql_execute_fetch"
                ]
                hits = sum(
                    (row.get("body") or {}).get("cache", {}).get("initial_lookup") == "hit"
                    for row in rows
                )
                misses = sum(
                    (row.get("body") or {}).get("cache", {}).get("initial_lookup") == "miss"
                    for row in rows
                )
                groups[label] = {
                    "responses": len(rows),
                    "initial_hits": hits,
                    "initial_misses": misses,
                    "hit_rate": hits / (hits + misses) if hits + misses else None,
                    "sql_attempts": len(spans),
                    "product_sql_attempts": sum(
                        "lab_product" in (span["sql"] or "") for span in spans
                    ),
                    "p50_client_ms": percentile(latencies, 0.5),
                    "p95_client_ms": percentile(latencies, 0.95),
                    "p99_client_ms": percentile(latencies, 0.99),
                }
            evidence = {
                "schema_version": 1,
                "evidence": "recorded",
                "complete": complete,
                "id": run_id,
                "started_at": started,
                "ended_at": datetime.now(UTC).isoformat(),
                "duration_s": time.perf_counter() - monotonic_start,
                "concurrency": concurrency,
                "local_sources": identity,
                "observations": observations,
                "groups": groups,
                "monitor_before": before,
                "monitor_after": after,
                "definitions": {
                    "latency": "httpx client round trip ms, not browser or server-only time",
                    "hit_rate": (
                        "initial hits/(initial hits+misses); exclude bypass, inspection, "
                        "invalidation and unknown"
                    ),
                    "sql": "returned actual attempts incl ownership; product count separately",
                    "ttl": "sampled PTTL ms; -2 absent, -1 unbounded, null unavailable",
                    "memory": "selected Redis value key MEMORY USAGE estimate bytes",
                    "sources": "local launch sources; server revision not independently attested",
                },
                "limitations": [
                    "Short functional sample, not capacity or reliable tail latency evidence",
                    "Full traces/inspection add overhead; monitor counters include other activity",
                    "Absent key after waiting is an observation, not a keyspace expiry event",
                    "Only received traces counted; unavailable responses have unknown SQL",
                ],
            }
            with (directory / "result.json").open("x", encoding="utf-8") as output:
                json.dump(evidence, output, indent=2)
    return directory


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:18002")
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "docs/experiments/006-redis-cache-aside/runs"
    )
    parser.add_argument("--concurrency", type=int, default=6)
    arguments = parser.parse_args()
    print(
        asyncio.run(
            record_experiment(arguments.base_url, arguments.output_dir, arguments.concurrency)
        )
    )


if __name__ == "__main__":
    main()
