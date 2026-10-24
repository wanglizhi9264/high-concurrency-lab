"""Read-only HTTP acceptance with immutable, actual request observations."""

import argparse
import json
import platform
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx

from concurrency_lab.schemas.business import BusinessResponse


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:18002")
    parser.add_argument(
        "--output-dir", type=Path, default=Path("docs/experiments/004-real-business-trace/runs")
    )
    arguments = parser.parse_args()
    paths = [
        "products/1",
        "users/500/orders?limit=3&offset=0",
        "users/500/order-page?limit=3&offset=0",
        "orders/1",
    ]
    records = []
    with httpx.Client(base_url=arguments.base_url, trust_env=False, timeout=10) as client:
        for path in paths:
            start = time.perf_counter()
            response = client.get("/api/v1/business/" + path)
            response.raise_for_status()
            body = BusinessResponse.model_validate(response.json())
            elapsed = (time.perf_counter() - start) * 1000
            if body.error or body.data is None:
                raise ValueError("Business read did not return data")
            if response.headers["x-request-id"] != body.trace.request_id:
                raise ValueError("Request identity mismatch")
            records.append(
                {
                    "path": path,
                    "http_status": response.status_code,
                    "client_http_json_ms": elapsed,
                    "response_preparation_ms": float(response.headers["x-process-time-ms"]),
                    "body": body.model_dump(mode="json"),
                }
            )
    arguments.output_dir.mkdir(parents=True, exist_ok=True)
    name = (
        "requests-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex[:8] + ".json"
    )
    with (arguments.output_dir / name).open("x", encoding="utf-8") as output:
        json.dump(
            {
                "schema_version": 1,
                "evidence": "measured",
                "observed_at": datetime.now(UTC).isoformat(),
                "environment": platform.platform(),
                "concurrency": 1,
                "unit": "ms",
                "load_rps": None,
                "limitations": [
                    "Single actual request per operation; not a load/percentile experiment.",
                    "HTTP client JSON interval is not browser or server-only SQL timing.",
                ],
                "requests": records,
            },
            output,
            ensure_ascii=False,
            indent=2,
        )
    print(f"Four actual business reads accepted; immutable evidence: {name}")


if __name__ == "__main__":
    main()
