"""One request per closed-loop task. Run only in an independent Locust process."""

import argparse
import json
import random
import time
from pathlib import Path
from typing import Any

from locust import HttpUser, constant_throughput, events, task
from locust.env import Environment

from concurrency_lab.experiments.load_recording import RequestCsvRecorder


@events.init_command_line_parser.add_listener
def add_lab_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--lab-output", required=True)
    parser.add_argument("--lab-task-rate", type=float, default=1)
    parser.add_argument(
        "--lab-scenario", choices=("mixed", "hot", "normal", "deep"), default="mixed"
    )


@events.init.add_listener
def initialize_recording(environment: Environment, **kwargs: Any) -> None:
    directory = Path(environment.parsed_options.lab_output)
    recorder = RequestCsvRecorder(directory / "requests.csv")
    environment.lab_recorder = recorder

    def on_start(environment: Environment, **kwargs: Any) -> None:
        recorder.start()

    def on_request(
        request_type: str,
        name: str,
        response_time: float,
        response: Any = None,
        exception: Any = None,
        **kwargs: Any,
    ) -> None:
        status = response.status_code if response is not None else 0
        sql_attempts: int | str = ""
        request_id = error_code = ""
        if response is not None:
            try:
                payload = response.json()
                trace = payload.get("trace", {})
                if isinstance(trace.get("spans"), list):
                    sql_attempts = sum(
                        span.get("kind") == "sql_execute_fetch" for span in trace["spans"]
                    )
                    request_id = trace.get("request_id", "")
                error_code = (payload.get("error") or {}).get("code", "")
            except (ValueError, AttributeError, TypeError):
                pass  # Missing structured response means unknown SQL count, never a synthetic zero.
        recorder.record(
            {
                "completed_epoch": time.time(),
                "response_ms": response_time,
                "status": status,
                "failed": int(exception is not None),
                "sql_attempts": sql_attempts,
                "error_code": error_code,
                "error_type": type(exception).__name__ if exception else "",
                "request_id": request_id,
                "name": name,
                "started_epoch": kwargs.get("start_time", ""),
            },
            environment.runner.user_count if environment.runner else 0,
        )

    def on_stop(environment: Environment, **kwargs: Any) -> None:
        recorder.finish()

    def on_quitting(environment: Environment, **kwargs: Any) -> None:
        recorder.finish()
        recorder.close()
        with (directory / "window.json").open("x", encoding="utf-8") as output:
            json.dump(
                {
                    "start_epoch": recorder.start_epoch,
                    "end_epoch": recorder.end_epoch,
                    "duration_s": recorder.end_monotonic - recorder.start_monotonic,
                    "peak_users": recorder.peak_users,
                },
                output,
            )
        if environment.runner and environment.runner.exceptions:
            environment.process_exit_code = 2

    environment.events.test_start.add_listener(on_start)
    environment.events.request.add_listener(on_request)
    environment.events.test_stop.add_listener(on_stop)
    environment.events.quitting.add_listener(on_quitting)


class BusinessLoadUser(HttpUser):
    def on_start(self) -> None:
        self.rng = random.Random(20261025 + self.environment.lab_recorder.next_user())
        self.pacer = constant_throughput(self.environment.parsed_options.lab_task_rate)

    def wait_time(self) -> float:
        return float(self.pacer(self))

    @task
    def read_business_data(self) -> None:
        scenario = self.environment.parsed_options.lab_scenario
        choice = self.rng.randrange(10) if scenario == "mixed" else None
        if scenario == "hot" or (choice is not None and choice < 5):
            path, name = "/products/1", "hot_product"
        elif scenario == "deep" or choice == 9:
            path, name = "/orders?limit=20&offset=8000", "deep_offset"
        elif choice == 8:
            path, name = f"/users/{self.rng.randint(1, 1000)}/orders?limit=20", "user_orders"
        else:
            path, name = f"/products/{self.rng.randint(1, 100)}", "normal_product"
        self.client.get("/api/v1/business" + path, name=name, timeout=(2, 7))
