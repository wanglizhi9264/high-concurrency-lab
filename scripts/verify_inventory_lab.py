"""Record fresh inventory contests/replays/audits via loopback HTTP; never reset stock."""

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
from concurrency_lab.schemas.benchmarks import BusinessMetrics
from concurrency_lab.schemas.business import BusinessResponse
from concurrency_lab.schemas.inventory import InventoryResponse

ROOT = Path(__file__).resolve().parents[1]
BASE = "/api/v1/business"


async def record_inventory(base_url: str, output_root: Path) -> Path:
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
    ):
        raise ValueError("Use an explicit http://127.0.0.1:port loopback target")
    directory = output_root / (
        "inventory-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex[:8]
    )
    directory.mkdir(parents=True, exist_ok=False)
    observations: list[dict[str, Any]] = []
    audits: dict[str, Any] = {}
    identity = source_identity(ROOT)
    started, clock = datetime.now(UTC).isoformat(), time.perf_counter()
    complete = False
    monitor_before = monitor_after = None
    async with httpx.AsyncClient(base_url=base_url, trust_env=False, timeout=15) as client:

        async def call(
            label: str, method: str, path: str, body: Any = None, key: str | None = None
        ) -> dict[str, Any]:
            before = time.perf_counter()
            row: dict[str, Any] = {
                "label": label,
                "method": method,
                "path": path,
                "intent": body,
                "idempotency_key": key,
                "observed_at": datetime.now(UTC).isoformat(),
            }
            try:
                response = await client.request(
                    method,
                    path,
                    **({"json": body} if body is not None else {}),
                    headers={"Idempotency-Key": key} if key else {},
                )
                data = response.json()
                if response.status_code in (200, 201):
                    InventoryResponse.model_validate(data)
                else:
                    BusinessResponse.model_validate(data)
                row.update(status=response.status_code, body=data)
            except (httpx.HTTPError, ValueError) as failure:
                row.update(status=0, body=None, error_type=type(failure).__name__)
            row["client_rtt_ms"] = (time.perf_counter() - before) * 1000
            observations.append(row)
            return row

        def require(row: dict[str, Any], statuses: tuple[int, ...]) -> Any:
            if row["status"] not in statuses:
                raise ValueError("Acceptance response unexpected; retain actual evidence")
            return row["body"]["data"]

        async def create(stock: int) -> str:
            identifier = str(uuid4())
            row = await call(
                "new_scenario",
                "POST",
                BASE + "/inventory/scenarios",
                {"scenario_id": identifier, "product_id": 1, "initial": stock},
            )
            require(row, (201,))
            return identifier

        async def submit(label: str, intent: dict[str, Any], key: str) -> dict[str, Any]:
            return await call(label, "POST", BASE + "/purchases/orders", intent, key)

        async def audit(identifier: str, label: str) -> Any:
            row = await call(label, "GET", f"{BASE}/inventory/scenarios/{identifier}/audit")
            data = require(row, (200,))
            if not data["all_pass"]:
                raise ValueError("Persisted inventory invariant failed")
            audits[label] = data
            return data

        try:
            monitor_before = BusinessMetrics.model_validate(
                (await client.get("/api/v1/observability/business-metrics")).json()
            ).model_dump(mode="json")
            identifier = await create(5)
            intents = [
                (str(uuid4()), {"scenario_id": identifier, "user_id": 1, "quantity": 1})
                for _ in range(20)
            ]
            responses = await asyncio.gather(
                *(submit("distinct_contest", body, key) for key, body in intents)
            )
            # Only retry bounded ambiguous/transaction/pool outcomes, preserving exact intent.
            for attempt in range(2):
                retry = [
                    (index, key, body)
                    for index, (key, body) in enumerate(intents)
                    if responses[index]["status"] in (0, 503, 504)
                    or ((responses[index].get("body") or {}).get("error") or {}).get("code")
                    == "transaction_conflict"
                ]
                if not retry:
                    break
                replayed = await asyncio.gather(
                    *(submit(f"bounded_retry_{attempt + 1}", body, key) for _, key, body in retry)
                )
                for (index, _, _), response in zip(retry, replayed, strict=True):
                    responses[index] = response
            first_audit = await audit(identifier, "after_distinct_contest")
            if (
                first_audit["scenario"]["reserved"] != 5
                or first_audit["order_counts"]["reserved"] != 5
            ):
                raise ValueError("Five committed reservations expected after bounded contest")
            winners = [row for row in responses if row["status"] in (200, 201)]
            if len({row["body"]["data"]["order"]["id"] for row in winners}) != 5:
                raise ValueError(
                    "Five unique acknowledged orders required before state experiments"
                )
            first = winners[0]["body"]["data"]["order"]
            second = winners[1]["body"]["data"]["order"]
            changed = await submit(
                "mismatched_payload",
                {"scenario_id": identifier, "user_id": 1, "quantity": 2},
                first["idempotency_key"],
            )
            require(changed, (409,))
            if changed["body"]["error"]["code"] != "idempotency_conflict":
                raise ValueError("Expected explicit payload conflict")
            for label in ("cancel", "cancel_replay"):
                require(
                    await call(
                        label,
                        "POST",
                        f"{BASE}/purchases/orders/{first['id']}/state",
                        {"target": "cancelled"},
                    ),
                    (200,),
                )
            require(
                await call(
                    "pay",
                    "POST",
                    f"{BASE}/purchases/orders/{second['id']}/state",
                    {"target": "paid"},
                ),
                (200,),
            )
            rejected = await call(
                "reject_paid_cancel",
                "POST",
                f"{BASE}/purchases/orders/{second['id']}/state",
                {"target": "cancelled"},
            )
            require(rejected, (409,))
            if rejected["body"]["error"]["code"] != "invalid_order_transition":
                raise ValueError("Expected explicit terminal-state conflict")
            require(
                await submit(
                    "reserve_returned_unit",
                    {"scenario_id": identifier, "user_id": 1, "quantity": 1},
                    str(uuid4()),
                ),
                (201,),
            )
            final_audit = await audit(identifier, "after_states")
            if final_audit["order_units"] != {"reserved": 4, "paid": 1, "cancelled": 1}:
                raise ValueError(
                    "Final state quantities differ from actual expected business sequence"
                )
            duplicate_scenario, shared_key = await create(1), str(uuid4())
            body = {"scenario_id": duplicate_scenario, "user_id": 1, "quantity": 1}
            matching = await asyncio.gather(
                *(submit("matching_key_contest", body, shared_key) for _ in range(10))
            )
            if any(row["status"] not in (200, 201) for row in matching):
                raise ValueError(
                    "Matching-key contest did not complete with confirmed order results"
                )
            if sum(row["status"] == 201 for row in matching) != 1:
                raise ValueError("Exactly one new matching-key order expected")
            if len({row["body"]["data"]["order"]["id"] for row in matching}) != 1:
                raise ValueError("Matching intent created multiple orders")
            await audit(duplicate_scenario, "after_matching_contest")
            monitor_after = BusinessMetrics.model_validate(
                (await client.get("/api/v1/observability/business-metrics")).json()
            ).model_dump(mode="json")
            if source_identity(ROOT)["workload_sha256"] != identity["workload_sha256"]:
                raise ValueError("Sources changed during experiment")
            complete = True
        finally:
            evidence = {
                "schema_version": 1,
                "evidence": "recorded",
                "complete": complete,
                "started_at": started,
                "ended_at": datetime.now(UTC).isoformat(),
                "duration_s": time.perf_counter() - clock,
                "local_sources": identity,
                "monitor_before": monitor_before,
                "monitor_after": monitor_after,
                "observations": observations,
                "audits": audits,
                "definitions": {
                    "latency": "client httpx round trip ms, not pure SQL/lock time",
                    "outcomes": "201 new;200 may replay;409 classified; commit ACK may be unknown",
                    "audit": "same-snapshot persisted counters and orders; cancelled is historical",
                    "scope": "fresh scenarios only; no old stock, baseline rows or Redis writes",
                    "sources": "local checkpoint; server revision not independently attested",
                },
                "limitations": [
                    "Small functional contest, not production capacity/tail-latency evidence",
                    "Client concurrency does not guarantee equal simultaneous server execution",
                    "Lock waits and full trace overhead are included; no pure lock-wait estimate",
                ],
            }
            with (directory / "result.json").open("x", encoding="utf-8") as output:
                json.dump(evidence, output, indent=2)
    return directory


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:18002")
    parser.add_argument(
        "--output-dir", type=Path, default=ROOT / "docs/experiments/007-inventory-idempotency/runs"
    )
    arguments = parser.parse_args()
    print(asyncio.run(record_inventory(arguments.base_url, arguments.output_dir)))


if __name__ == "__main__":
    main()
