"""Actual clean Git clone + separate Compose project acceptance; never reset developer data."""

import argparse
import asyncio
import hashlib
import json
import os
import re
import secrets as secret_generator
import shutil
import socket
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx
import psutil
from sqlalchemy.exc import SQLAlchemyError

from concurrency_lab.experiments.resource_sampling import stop_owned_process
from concurrency_lab.experiments.runner import dataset_identity as old_dataset_identity
from concurrency_lab.experiments.runner import save_result
from concurrency_lab.experiments.safety import assert_owned as assert_old_owned
from concurrency_lab.experiments.safety import engine_for as old_engine_for
from concurrency_lab.experiments.scale.identity import ROOT, source_identity

DEFAULT_PORTS = {
    "mysql": 15006,
    "redis": 15379,
    "experiment": 15306,
    "api": 18004,
    "load": 18005,
    "frontend": 5175,
}
SECRET_NAMES = ("MYSQL_PASSWORD", "MYSQL_ROOT_PASSWORD", "REDIS_PASSWORD", "EXP_MYSQL_PASSWORD")
RESERVED_PORTS = frozenset((3306, 6379, 13306, 16379, 18000, 18002, 18003, 5173, 5174))


def clone_target(base: Path, run_id: str) -> Path:
    if not re.fullmatch(r"e2e-[0-9]{8}T[0-9]{6}-[0-9a-f]{8}", run_id):
        raise ValueError("Invalid clean-clone ID")
    target = base.resolve() / run_id
    if target.resolve().parent != base.resolve():
        raise ValueError("Clone target escapes its explicit workspace")
    if target.exists() or target.is_symlink():
        raise FileExistsError("Clone target already exists; never reset or overwrite")
    return target


def validate_ports(ports: dict[str, int]) -> None:
    if set(ports) != set(DEFAULT_PORTS) or len(set(ports.values())) != len(ports):
        raise ValueError("All six distinct acceptance ports required")
    for port in ports.values():
        if not 1024 <= port <= 65535 or port in RESERVED_PORTS:
            raise ValueError("Acceptance ports must avoid developer defaults")
        try:
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", port))
        except OSError as failure:
            raise ValueError(
                f"Acceptance port {port} unavailable; no existing process stopped"
            ) from failure


def isolated_environment(
    clone: Path, project: str, ports: dict[str, int], credentials: dict[str, str]
) -> dict[str, str]:
    if not re.fullmatch(r"hcl-e2e-009-[0-9a-f]{8}", project):
        raise ValueError("Only a newly generated009acceptance project is permitted")
    if set(credentials) != set(SECRET_NAMES):
        raise ValueError("Four new local secrets required")
    environment = dict(os.environ)
    for key in (
        "PYTHONPATH",
        "PYTHONHOME",
        "VIRTUAL_ENV",
        "UV_PROJECT_ENVIRONMENT",
        "UV_PROJECT",
        "COMPOSE_FILE",
        "COMPOSE_PATH_SEPARATOR",
        "COMPOSE_PROFILES",
        "NODE_PATH",
    ):
        environment.pop(key, None)
    environment.update(credentials)
    environment.update(
        COMPOSE_PROJECT_NAME=project,
        CONCURRENCY_LAB_ROOT=str(clone),
        PYTHONUTF8="1",
        UV_LINK_MODE="copy",
        MYSQL_HOST="127.0.0.1",
        MYSQL_PORT=str(ports["mysql"]),
        MYSQL_DATABASE="concurrency_lab",
        MYSQL_USER="lab",
        REDIS_HOST="127.0.0.1",
        REDIS_PORT=str(ports["redis"]),
        EXP_MYSQL_HOST="127.0.0.1",
        EXP_MYSQL_PORT=str(ports["experiment"]),
        EXP_MYSQL_USER="lab_exp",
        BUSINESS_ENABLED="true",
        BUSINESS_WRITES_ENABLED="true",
        BUSINESS_DATABASE="concurrency_lab_business",
        PLAYWRIGHT_API_PORT=str(ports["api"]),
        PLAYWRIGHT_FRONTEND_PORT=str(ports["frontend"]),
        PLAYWRIGHT_REUSE_SERVER="false",
        API_PROXY_TARGET=f"http://127.0.0.1:{ports['api']}",
        BUSINESS_INTEGRATION="1",
        CACHE_INTEGRATION="1",
        INVENTORY_INTEGRATION="1",
        TASK_INTEGRATION="1",
        SCALE_INTEGRATION="1",
        EXPERIMENT_INTEGRATION="1",
        PYTEST_ADDOPTS="--basetemp=.pytest_cache/clean-clone-tests",
    )
    if sys.platform == "win32" and not environment.get("PLAYWRIGHT_CHANNEL"):
        environment["PLAYWRIGHT_CHANNEL"] = "msedge"
    return environment


def redact(text: str, credentials: dict[str, str], clone: Path) -> str:
    for value in credentials.values():
        text = text.replace(value, "<redacted>")
    return text.replace(str(clone), "<clean-clone>").replace(str(ROOT), "<source-repository>")


def npm_argv(*arguments: str) -> list[str]:
    node, npm = shutil.which("node"), shutil.which("npm")
    if not node or not npm:
        raise ValueError("Node/npm required")
    script = Path(npm).parent / "node_modules/npm/bin/npm-cli.js"
    if script.is_file():
        return [node, str(script), *arguments]
    if sys.platform != "win32":
        return [npm, *arguments]
    raise ValueError("Cannot locate npm-cli.js for hidden direct Node invocation")


def project_identity(project: str) -> dict[str, Any]:
    identifiers = subprocess.check_output(
        ["docker", "ps", "-aq", "--filter", f"label=com.docker.compose.project={project}"],
        text=True,
    ).split()
    containers = []
    for identifier in identifiers:
        data = json.loads(subprocess.check_output(["docker", "inspect", identifier], text=True))[0]
        labels = data["Config"]["Labels"]
        if labels.get("com.docker.compose.project") != project:
            raise ValueError("Container project identity mismatch")
        containers.append(
            {
                "id": data["Id"],
                "service": labels.get("com.docker.compose.service"),
                "image": data["Image"],
                "running": data["State"]["Running"],
                "volumes": sorted(m["Name"] for m in data["Mounts"] if m.get("Name")),
                "ports": data["NetworkSettings"]["Ports"],
            }
        )
    return {"project": project, "containers": sorted(containers, key=lambda c: c["id"])}


async def old_database_snapshot(prior: dict[str, Any]) -> dict[str, Any]:
    if not any(c["service"] == "mysql-experiment" and c["running"] for c in prior["containers"]):
        return {"status": "not_running", "databases": {}}
    result = {}
    for count in (10000, 100000, 1000000):
        database = f"concurrency_lab_exp_002_{count}"
        engine = old_engine_for(database)
        try:
            async with engine.connect() as connection:
                await assert_old_owned(connection, database)
                result[database] = await old_dataset_identity(connection)
        finally:
            await engine.dispose()
    return {"status": "verified", "databases": result}


def file_snapshot(clone: Path) -> dict[str, str]:
    return {
        path.relative_to(clone).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (clone / "docs/experiments").rglob("*")
        if path.is_file() and path.suffix in (".json", ".jsonl", ".csv", ".png")
    }


def export_new_evidence(clone: Path, destination: Path, before: dict[str, str]) -> list[str]:
    exported = []
    for relative, digest in file_snapshot(clone).items():
        if before.get(relative) == digest:
            continue
        if relative in before and not relative.endswith(".png"):
            raise ValueError("Existing recorded measurement changed during clean-clone acceptance")
        path = destination / "artifacts" / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            raise FileExistsError("Export never overwrites evidence")
        shutil.copy2(clone / relative, path)
        exported.append(path.relative_to(destination).as_posix())
    return sorted(exported)


class Acceptance:
    def __init__(
        self, clone: Path, directory: Path, environment: dict[str, str], credentials: dict[str, str]
    ) -> None:
        self.clone, self.directory, self.environment, self.credentials = (
            clone,
            directory,
            environment,
            credentials,
        )
        self.steps: list[dict[str, Any]] = []

    def step(
        self, label: str, arguments: list[str], cwd: Path | None = None, timeout: int = 900
    ) -> str:
        item: dict[str, Any] = {
            "label": label,
            "argv": [redact(arg, self.credentials, self.clone) for arg in arguments],
            "cwd": "frontend" if cwd == self.clone / "frontend" else "<clean-clone>",
            "started_at": datetime.now(UTC).isoformat(),
            "passed": False,
        }
        self.steps.append(item)
        started, process = time.perf_counter(), None
        try:
            process = subprocess.Popen(
                arguments,
                cwd=cwd or self.clone,
                env=self.environment,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
            output, _ = process.communicate(timeout=timeout)
            item["exit_code"] = process.returncode
            log = f"{len(self.steps):02d}-{label}.log"
            (self.directory / log).write_text(
                redact(output, self.credentials, self.clone), encoding="utf-8"
            )
            item["log"] = log
            if process.returncode != 0:
                raise ValueError(f"Acceptance step failed: {label}; see retained redacted log")
            item["passed"] = True
            return output
        except subprocess.TimeoutExpired:
            item["error_type"] = "owned_step_timeout"
            raise
        finally:
            stop_owned_process(process)
            item["finished_at"] = datetime.now(UTC).isoformat()
            item["duration_seconds"] = time.perf_counter() - started


def owned_listener(process: subprocess.Popen[Any], port: int) -> bool:
    if process.poll() is not None:
        return False
    try:
        root = psutil.Process(process.pid)
        return any(
            connection.status == psutil.CONN_LISTEN
            and connection.laddr
            and connection.laddr[1] == port
            for member in (root, *root.children(recursive=True))
            for connection in member.net_connections(kind="tcp")
        )
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def start_api(acceptance: Acceptance, python: str, port: int) -> subprocess.Popen[Any]:
    cache = acceptance.clone / ".pytest_cache"
    cache.mkdir(parents=True, exist_ok=True)
    log = (cache / "owned-acceptance-api.log").open("x", encoding="utf-8")
    process = subprocess.Popen(
        [
            python,
            "-m",
            "uvicorn",
            "concurrency_lab.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=acceptance.clone,
        env=acceptance.environment,
        stdout=log,
        stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    log.close()
    try:
        with httpx.Client(trust_env=False, timeout=3) as client:
            deadline = time.monotonic() + 30
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    raise ValueError("Owned API stopped before readiness")
                if owned_listener(process, port):
                    response = client.get(f"http://127.0.0.1:{port}/health/ready")
                    if response.status_code == 200:
                        return process
                time.sleep(0.2)
        raise ValueError("Owned API readiness/port ownership not confirmed")
    except (ValueError, httpx.HTTPError):
        stop_owned_process(process)
        raise


def record_journey(acceptance: Acceptance, python: str, port: int) -> dict[str, Any]:
    observations = []
    with httpx.Client(base_url=f"http://127.0.0.1:{port}", trust_env=False, timeout=10) as client:

        def call(
            method: str, path: str, body: Any = None, headers: dict[str, str] | None = None
        ) -> Any:
            started = time.perf_counter()
            response = client.request(
                method, path, **({"json": body} if body is not None else {}), headers=headers
            )
            row = {
                "method": method,
                "path": path,
                "intent": body,
                "status": response.status_code,
                "observed_at": datetime.now(UTC).isoformat(),
                "client_rtt_ms": (time.perf_counter() - started) * 1000,
                "body": response.json(),
            }
            observations.append(row)
            response.raise_for_status()
            return row["body"]

        base = "/api/v1/business"
        call("GET", "/health/ready")
        call("GET", "/api/v1/observability/business-metrics")
        call("GET", base + "/cache/products/1?mode=cache&ttl_seconds=5")
        scenario, task_id, key = str(uuid4()), str(uuid4()), str(uuid4())
        call(
            "POST",
            base + "/inventory/scenarios",
            {"scenario_id": scenario, "product_id": 1, "initial": 2},
        )
        order = call(
            "POST",
            base + "/purchases/orders",
            {"scenario_id": scenario, "user_id": 1, "quantity": 1},
            {"Idempotency-Key": key},
        )["data"]["order"]
        call("POST", base + f"/purchases/orders/{order['id']}/state", {"target": "paid"})
        task = call("POST", base + "/tasks", {"task_id": task_id, "order_id": order["id"]})
        if task["data"]["task"]["state"] != "queued":
            raise ValueError("Journey acceptance did not observe durable queued state")
        acceptance.step(
            "journey-worker",
            [
                python,
                "-m",
                "concurrency_lab.workers.receipts",
                "--database",
                "concurrency_lab_business",
                "--scenario",
                scenario,
                "--max-cycles",
                "5",
            ],
            timeout=30,
        )
        detail = call("GET", base + f"/tasks/{task_id}")["data"]
        audit = call("GET", base + f"/inventory/scenarios/{scenario}/audit")["data"]
        call("GET", base + f"/task-queues/{scenario}")
        if (
            detail["task"]["state"] != "succeeded"
            or detail["receipt"]["order_id"] != order["id"]
            or not audit["all_pass"]
            or audit["scenario"]["sold"] != 1
            or audit["scenario"]["reserved"] != 0
        ):
            raise ValueError("Real paid-order→receipt→inventory journey failed")
        result = {
            "complete": True,
            "evidence": "measured_functional_journey",
            "scenario_id": scenario,
            "order_id": order["id"],
            "task_id": task_id,
            "receipt_id": detail["receipt"]["id"],
            "observations": observations,
        }
        save_result(acceptance.directory / "journey.json", result)
        return {
            "order_id": order["id"],
            "task_id": task_id,
            "receipt_id": detail["receipt"]["id"],
            "inventory_audit_pass": True,
        }


def verify(workspace: Path, ports: dict[str, int]) -> Path:
    validate_ports(ports)
    original_source = source_identity()
    if original_source["sources_dirty"]:
        raise ValueError("Freeze/commit source before clean-clone acceptance")
    identifier = "e2e-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S") + "-" + uuid4().hex[:8]
    clone = clone_target(workspace, identifier)
    project = "hcl-e2e-009-" + identifier[-8:]
    credentials = {name: secret_generator.token_hex(24) for name in SECRET_NAMES}
    environment = isolated_environment(clone, project, ports, credentials)
    directory = ROOT / "docs/experiments/009-scale-comprehensive-lab/end-to-end" / identifier
    directory.mkdir(parents=True, exist_ok=False)
    legacy_project = os.getenv("COMPOSE_PROJECT_NAME", "high-concurrency-lab")
    prior = project_identity(legacy_project)
    old_before = asyncio.run(old_database_snapshot(prior))
    if project_identity(project)["containers"]:
        raise ValueError("New acceptance project unexpectedly exists; no takeover")
    acceptance = Acceptance(clone, directory, environment, credentials)
    manifest: dict[str, Any] = {
        "id": identifier,
        "complete": False,
        "evidence": "actual_clean_clone_acceptance",
        "source": original_source,
        "project": project,
        "ports": ports,
        "credentials_generated": True,
        "prior_project": prior,
        "old002_before": old_before,
        "started_at": datetime.now(UTC).isoformat(),
        "steps": acceptance.steps,
        "limitations": [
            "Local Git clone --no-local of exact frozen commit; "
            "no workspace/env/venv/node_modules copied; not a network-download benchmark",
            "Functional feature acceptance and short Locust, not production capacity",
            "Logs redact generated secrets/local paths; "
            "exported measurement artifacts retain original bytes",
        ],
    }
    api_process, before_files, project_started = None, {}, False
    try:
        clone.parent.mkdir(parents=True, exist_ok=True)
        acceptance.step(
            "clean-git-clone",
            ["git", "clone", "-c", "core.longpaths=true", "--no-local", str(ROOT), str(clone)],
            cwd=ROOT,
            timeout=120,
        )
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=clone, text=True).strip()
        status = subprocess.check_output(
            ["git", "status", "--porcelain", "--untracked-files=all"], cwd=clone, text=True
        ).strip()
        if head != original_source["revision"] or status:
            raise ValueError("Clean clone does not match frozen source")
        manifest["clone_proof"] = {
            "head": head,
            "initial_git_status": status,
            "copied_local_environment": False,
        }
        before_files = file_snapshot(clone)
        config = {
            key: value
            for key, value in environment.items()
            if key in SECRET_NAMES
            or key.startswith(("MYSQL_", "REDIS_", "EXP_MYSQL_", "BUSINESS_"))
            or key == "COMPOSE_PROJECT_NAME"
        }
        with (clone / ".env").open("x", encoding="utf-8") as output:
            output.write(
                "\n".join(f"{key}={value}" for key, value in sorted(config.items())) + "\n"
            )
        (clone / ".env").chmod(0o600)
        acceptance.step("ignored-env", ["git", "check-ignore", ".env"])
        acceptance.step("frozen-python-install", ["uv", "sync", "--frozen"])
        python = str(
            clone / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
        )
        acceptance.step("npm-ci", npm_argv("ci"), cwd=clone / "frontend")
        compose = [
            "docker",
            "compose",
            "-p",
            project,
            "-f",
            "compose.yaml",
            "-f",
            "compose.experiments.yaml",
            "--profile",
            "experiments",
        ]
        project_started = True
        acceptance.step("owned-dependencies", [*compose, "up", "-d", "--wait"], timeout=240)
        owned = project_identity(project)
        if {c["service"] for c in owned["containers"]} != {"mysql", "redis", "mysql-experiment"}:
            raise ValueError("Owned dependency project incomplete")
        old_volumes = {v for c in prior["containers"] for v in c["volumes"]}
        if old_volumes.intersection(v for c in owned["containers"] for v in c["volumes"]):
            raise ValueError("Acceptance dependencies share developer volumes")
        manifest["owned_dependencies"] = owned
        acceptance.step("foundation-migration", [python, "-m", "alembic", "upgrade", "head"])
        acceptance.step("business-provision", [python, "scripts/provision_business_lab.py"])
        for database in ("concurrency_lab_business", "concurrency_lab_business_test"):
            for action in (["init"], ["seed", "--orders", "10000"]):
                acceptance.step(
                    f"business-{database}-{action[0]}",
                    [
                        python,
                        "-m",
                        "concurrency_lab.experiments.business_dataset",
                        "--database",
                        database,
                        *action,
                    ],
                )
            acceptance.step(
                f"upgrade-{database}",
                [
                    python,
                    "-m",
                    "concurrency_lab.experiments.business_schema",
                    "--database",
                    database,
                    "--revision",
                    "0005",
                ],
            )
        acceptance.step(
            "index-provision", [python, "scripts/provision_index_lab.py", "--project-name", project]
        )
        acceptance.step(
            "scale-provision", [python, "scripts/provision_scale_lab.py", "--project-name", project]
        )
        acceptance.step(
            "prior-index-evidence", [python, "scripts/verify_index_lab.py", "--verify-only"]
        )
        acceptance.step(
            "new-index-smoke",
            [
                python,
                "scripts/verify_index_lab.py",
                "--orders",
                "10000",
                "--output-dir",
                "docs/experiments/009-scale-comprehensive-lab/clone-index-smoke",
            ],
        )
        acceptance.step(
            "new009smoke",
            [
                python,
                "scripts/run_scale_experiment.py",
                "--orders",
                "10000",
                "--project-name",
                project,
            ],
            timeout=600,
        )
        api_process = start_api(acceptance, python, ports["api"])
        base_url = f"http://127.0.0.1:{ports['api']}"
        acceptance.step(
            "real-business-trace",
            [python, "scripts/verify_business_lab.py", "--base-url", base_url],
        )
        acceptance.step(
            "short-real-locust",
            [
                python,
                "scripts/run_load_test.py",
                "--users",
                "10",
                "--seconds",
                "5",
                "--spawn-rate",
                "10",
                "--port",
                str(ports["load"]),
            ],
            timeout=120,
        )
        acceptance.step(
            "real-cache", [python, "scripts/verify_cache_lab.py", "--base-url", base_url]
        )
        acceptance.step(
            "real-inventory", [python, "scripts/verify_inventory_lab.py", "--base-url", base_url]
        )
        acceptance.step(
            "real-worker-recovery",
            [python, "scripts/verify_worker_lab.py", "--base-url", base_url],
            timeout=120,
        )
        manifest["journey"] = record_journey(acceptance, python, ports["api"])
        acceptance.step("python-quality", [python, "scripts/verify.py"])
        acceptance.step(
            "all-real-integration", [python, "-m", "pytest", "tests/integration"], timeout=240
        )
        acceptance.step("frontend-check", npm_argv("run", "check"), cwd=clone / "frontend")
        acceptance.step("frontend-unit", npm_argv("run", "test"), cwd=clone / "frontend")
        acceptance.step("frontend-build", npm_argv("run", "build"), cwd=clone / "frontend")
        stop_owned_process(api_process)
        api_process = None  # Playwright must start its own isolated servers, no reuse.
        if sys.platform != "win32":
            acceptance.step(
                "browser-install",
                npm_argv("exec", "--", "playwright", "install", "--with-deps", "chromium"),
                cwd=clone / "frontend",
            )
        acceptance.step(
            "real-browser-e2e", npm_argv("run", "test:e2e"), cwd=clone / "frontend", timeout=180
        )
        manifest["complete"] = True
    finally:
        stop_owned_process(api_process)
        if clone.exists() and before_files:
            try:
                manifest["exported_artifacts"] = export_new_evidence(clone, directory, before_files)
            except (ValueError, OSError) as failure:
                manifest["complete"] = False
                manifest["evidence_export_error"] = type(failure).__name__
            api_log = clone / ".pytest_cache/owned-acceptance-api.log"
            if api_log.is_file():
                (directory / "owned-api.log").write_text(
                    redact(
                        api_log.read_text(encoding="utf-8", errors="replace"), credentials, clone
                    ),
                    encoding="utf-8",
                )
        if project_started:
            try:
                acceptance.step(
                    "stop-owned-project",
                    [
                        "docker",
                        "compose",
                        "-p",
                        project,
                        "-f",
                        "compose.yaml",
                        "-f",
                        "compose.experiments.yaml",
                        "--profile",
                        "experiments",
                        "stop",
                    ],
                    timeout=120,
                )
                manifest["owned_dependencies_after_stop"] = project_identity(project)
            except (ValueError, subprocess.SubprocessError):
                manifest["complete"] = False
                manifest["cleanup_error"] = "owned_project_stop_unconfirmed"
        try:
            manifest["prior_project_after"] = project_identity(legacy_project)
            manifest["old002_after"] = asyncio.run(old_database_snapshot(prior))
        except (ValueError, SQLAlchemyError, subprocess.SubprocessError):
            manifest["complete"] = False
            manifest["preservation_error"] = "prior_identity_collection_unavailable"
        else:
            if manifest["prior_project_after"] != prior or manifest["old002_after"] != old_before:
                manifest["complete"] = False
                manifest["preservation_error"] = "prior_resource_or_data_identity_changed"
        try:
            validate_ports(ports)
        except ValueError:
            manifest["complete"] = False
            manifest["cleanup_error"] = "owned_acceptance_port_still_in_use"
        manifest["finished_at"] = datetime.now(UTC).isoformat()
        manifest["steps"] = acceptance.steps
        save_result(directory / "result.json", manifest)
    if not manifest["complete"]:
        raise ValueError("Clean-clone acceptance incomplete; preserve evidence and resources")
    return directory


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, default=ROOT.parent / ".hcl-acceptance")
    for name, port in DEFAULT_PORTS.items():
        parser.add_argument(f"--{name}-port", type=int, default=port)
    arguments = parser.parse_args()
    print(
        verify(
            arguments.workspace,
            {name: getattr(arguments, f"{name}_port") for name in DEFAULT_PORTS},
        )
    )


if __name__ == "__main__":
    main()
