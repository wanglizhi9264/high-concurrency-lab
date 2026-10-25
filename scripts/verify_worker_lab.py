"""Record actual scoped worker retry/deadline/crash recovery over loopback HTTP."""

import argparse
import asyncio
import hashlib
import json
import os
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from uuid import uuid4

import httpx

from concurrency_lab.experiments.load_recording import source_identity
from concurrency_lab.schemas.benchmarks import BusinessMetrics
from concurrency_lab.schemas.tasks import TaskResponse

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = Path(__file__).resolve()
BASE = "/api/v1/business"


def identity() -> dict[str, Any]:
    return {
        **source_identity(ROOT),
        "acceptance_script_sha256": hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
    }


async def record(base_url: str, output_root: Path) -> Path:
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
        "worker-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex[:8]
    )
    directory.mkdir(parents=True, exist_ok=False)
    evidence: dict[str, Any] = {
        "evidence_type": "measured_functional_acceptance",
        "not_capacity_benchmark": True,
        "limitations": [
            "Functional acceptance only; no production RPS/CPU/tail-latency conclusion",
            "Local source checkpoint captured; API process revision not independently attested",
            "HTTP RTT, process wall time and handler_ms measure different boundaries",
            "Business/MySQL monitor values are whole-instance, not task-only attribution",
        ],
        "source_before": identity(),
        "started_at": datetime.now(UTC).isoformat(),
        "worker_policy": {"timeout_seconds": 0.2, "lease_seconds": 1},
        "http": [],
        "workers": [],
        "cases": {},
        "complete": False,
    }
    clock = time.perf_counter()
    children: list[asyncio.subprocess.Process] = []
    async with httpx.AsyncClient(base_url=base_url, trust_env=False, timeout=10) as client:

        async def call(
            label: str,
            method: str,
            path: str,
            payload: Any = None,
            headers: dict[str, str] | None = None,
        ) -> Any:
            row: dict[str, Any] = {
                "label": label,
                "method": method,
                "path": path,
                "payload": payload,
                "observed_at": datetime.now(UTC).isoformat(),
            }
            started = time.perf_counter()
            evidence["http"].append(row)
            response = await client.request(
                method, path, **({"json": payload} if payload is not None else {}), headers=headers
            )
            row.update(
                status=response.status_code,
                body=response.json(),
                client_rtt_ms=(time.perf_counter() - started) * 1000,
            )
            if path.startswith(BASE + "/tasks") or path.startswith(BASE + "/task-queues"):
                TaskResponse.model_validate(row["body"])
            if response.status_code not in (200, 201):
                raise ValueError("Actual acceptance HTTP failed; preserve raw partial results")
            return row["body"]

        async def new_task(
            label: str, plan: dict[str, int] | None, maximum: int
        ) -> tuple[str, str, str]:
            scope = str(uuid4())
            await call(
                label,
                "POST",
                BASE + "/inventory/scenarios",
                {"scenario_id": scope, "product_id": 1, "initial": 1},
            )
            order = await call(
                label,
                "POST",
                BASE + "/purchases/orders",
                {"scenario_id": scope, "user_id": 1, "quantity": 1},
                {"Idempotency-Key": str(uuid4())},
            )
            order_id = order["data"]["order"]["id"]
            await call(
                label, "POST", BASE + f"/purchases/orders/{order_id}/state", {"target": "paid"}
            )
            task_id = str(uuid4())
            task = await call(
                label,
                "POST",
                BASE + "/tasks",
                {
                    "task_id": task_id,
                    "order_id": order_id,
                    "max_attempts": maximum,
                    "fault_plan": plan,
                },
            )
            database = task["trace"]["database"]
            if database not in ("concurrency_lab_business", "concurrency_lab_business_test"):
                raise ValueError("Refusing worker against unexpected database")
            return scope, task_id, database

        async def child(label: str, scope: str, database: str, crash: bool = False) -> None:
            arguments = [
                sys.executable,
                "-m",
                "concurrency_lab.workers.receipts",
                "--database",
                database,
                "--scenario",
                scope,
                "--timeout-seconds",
                ".2",
                "--lease-seconds",
                "1",
                "--max-cycles",
                "15",
            ]
            if crash:
                arguments.append("--crash-after-claim")
            started = time.perf_counter()
            process = await asyncio.create_subprocess_exec(
                *arguments,
                cwd=ROOT,
                env={**os.environ, "BUSINESS_WRITES_ENABLED": "true", "PYTHONUTF8": "1"},
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            children.append(process)
            stdout, stderr = await asyncio.wait_for(process.communicate(), 20)
            observation = {
                "label": label,
                "scope": scope,
                "database": database,
                "controlled_crash_probe": crash,
                "exit_code": process.returncode,
                "process_wall_ms": (time.perf_counter() - started) * 1000,
                "stdout": stdout.decode("utf-8"),
                "stderr_present": bool(stderr),
            }
            evidence["workers"].append(observation)
            expected = 70 if crash else 0
            if process.returncode != expected or (
                crash and "crash_after_committed_claim" not in observation["stdout"]
            ):
                raise ValueError("Owned worker process did not produce the expected actual outcome")

        try:
            evidence["monitor_before"] = BusinessMetrics.model_validate(
                await call("monitor_before", "GET", "/api/v1/observability/business-metrics")
            ).model_dump(mode="json")
            scope, task_id, database = await new_task("retry", {"fail_first_attempts": 1}, 3)
            evidence["cases"]["retry_before"] = (
                await call("queued", "GET", BASE + f"/tasks/{task_id}")
            )["data"]
            await child("fail_once_then_success", scope, database)
            data = (await call("retry_result", "GET", BASE + f"/tasks/{task_id}"))["data"]
            if data["task"]["state"] != "succeeded" or [a["status"] for a in data["attempts"]] != [
                "failed",
                "succeeded",
            ]:
                raise ValueError("Real retry acceptance failed")
            evidence["cases"]["retry"] = data
            evidence["cases"]["retry_queue"] = (
                await call("queue", "GET", BASE + f"/task-queues/{scope}")
            )["data"]
            scope, task_id, database = await new_task("timeout", {"delay_ms": 400}, 2)
            await child("deadline_exhaustion", scope, database)
            data = (await call("failed_result", "GET", BASE + f"/tasks/{task_id}"))["data"]
            if data["task"]["state"] != "failed" or [a["status"] for a in data["attempts"]] != [
                "timeout",
                "timeout",
            ]:
                raise ValueError("Real timeout acceptance failed")
            evidence["cases"]["exhausted"] = data
            successor = str(uuid4())
            await call(
                "linked_retry",
                "POST",
                BASE + f"/tasks/{task_id}/retry",
                {"task_id": successor, "disable_faults": True},
            )
            await child("linked_successor", scope, database)
            data = (await call("successor_result", "GET", BASE + f"/tasks/{successor}"))["data"]
            if data["task"]["state"] != "succeeded" or data["task"]["retry_of"] != task_id:
                raise ValueError("Linked successor acceptance failed")
            evidence["cases"]["successor"] = data
            evidence["cases"]["original_retained"] = (
                await call("original_retained", "GET", BASE + f"/tasks/{task_id}")
            )["data"]
            scope, task_id, database = await new_task("crash", None, 3)
            await child("actual_crash_after_claim", scope, database, True)
            data = (await call("crashed_state", "GET", BASE + f"/tasks/{task_id}"))["data"]
            if data["task"]["state"] != "running" or data["attempts"][0]["finished_at"] is not None:
                raise ValueError("Crash state not durably observed")
            evidence["cases"]["after_crash"] = data
            await child("restarted_worker", scope, database)
            data = (await call("crash_recovered", "GET", BASE + f"/tasks/{task_id}"))["data"]
            if (
                data["task"]["state"] != "succeeded"
                or data["attempts"][0]["status"] != "abandoned"
                or data["attempts"][0]["handler_ms"] is not None
            ):
                raise ValueError("Actual crash recovery acceptance failed")
            evidence["cases"]["recovered"] = data
            evidence["monitor_after"] = BusinessMetrics.model_validate(
                await call("monitor_after", "GET", "/api/v1/observability/business-metrics")
            ).model_dump(mode="json")
            evidence["source_after"] = identity()
            if evidence["source_before"] != evidence["source_after"]:
                raise ValueError("Source changed during acceptance; retain partial results")
            evidence["complete"] = True
        finally:
            for process in children:
                if process.returncode is None:
                    process.kill()
                    await process.wait()
            evidence["finished_at"] = datetime.now(UTC).isoformat()
            evidence["wall_seconds"] = time.perf_counter() - clock
            with (directory / "result.json").open("x", encoding="utf-8") as output:
                json.dump(evidence, output, ensure_ascii=False, indent=2)
    return directory


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:18002")
    arguments = parser.parse_args()
    result = asyncio.run(
        record(arguments.base_url, ROOT / "docs/experiments/008-reliable-receipt-worker/runs")
    )
    print(result)


if __name__ == "__main__":
    main()
