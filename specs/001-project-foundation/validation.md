# Validation and delivery evidence
Date: 2026-10-23 (Asia/Shanghai). Local Windows, managed Python 3.12.14.

## SDD execution
Official specify-cli 1.2.3 from PyPI, matched GitHub stable release. `specify version`, `specify check` passed; Codex available. `specify init high-concurrency-lab --integration codex --script ps --non-interactive` installed official .specify templates/scripts/workflow and .agents skills. Constitution 1.0.0; spec/plan/research/data-model/contracts/quickstart/tasks completed before application code. Clarify skipped: no material ambiguity. Template resolver and setup-plan/setup-tasks used. Analyze recorded in analysis.md before implementation. Prerequisite check passes. No extension hooks configured. Feature branch 001-project-foundation.

## Actual commands and results
| Command / action | Result |
|---|---|
| uv python install 3.12 | managed 3.12 already installed |
| uv sync; uv sync --frozen | successful; uv.lock generated and frozen install checked |
| config tests before implementation | expected collection failure (missing module); after implementation passed |
| health tests before implementation | expected collection failure (missing main); after implementation passed |
| docker compose config --quiet | passed |
| docker compose up -d --wait | MySQL/Redis healthy after Redis host port adjustment |
| uv run alembic upgrade head; downgrade base; upgrade head | all exit 0; marker created/dropped/recreated |
| uv run alembic check | No new upgrade operations detected |
| uv run pytest tests/unit -q | 11 passed |
| uv run pytest tests/integration -q | 3 passed: MySQL Session roundtrip, independent Redis PING, real readiness |
| uv run ruff check . | passed |
| uv run ruff format --check . | passed |
| uv run mypy src | passed, 15 source files |
| uv run python scripts/verify.py | quality gates passed (final run below follows final test edits) |
| uv run uvicorn concurrency_lab.main:app --host 127.0.0.1 --port 18000 | startup completed; actual network HTTP live/ready 200 |
| uv run python scripts/acceptance_local.py | Redis down -> ready 503/live 200; restore -> 200; MySQL down -> ready 503/live 200; restore -> 200 |
| docker compose down; up -d --wait; alembic current | healthy, 0001 head retained; readiness 200 |
| docker build -t high-concurrency-lab:local . | first attempt Docker Hub auth endpoint timeout; python base pull retry then build succeeded |
| docker run non-root image with Compose network, env hosts/ports overridden | actual HTTP readiness 200; temporary container removed |
| git check-ignore .env | ignored |
| local credential value scan against all deliverable files | passed, no generated password values in deliverables |

Initial failures fixed: empty-package editable wheel rebuilt after src creation; test incorrectly patching read-only Engine instance method removed (dedicated factory-based cleanup test retained); Redis 6379 occupied -> ignored local .env uses 16379; mypy Pydantic plugin and Redis await typing added. Existing proxy intercepted local httpx requests; acceptance HTTP client now uses trust_env=False.

## Requirement acceptance
FR-001..FR-009 and SC-001..SC-005 accepted locally based on the commands above. Tests cover failed/timeout probes, lifecycle cleanup including partial initialization, and Session DI closing. No RPS/latency performance experiment was executed.
Remote GitHub Actions has been authored but not triggered: repository has not been published and no remote run is claimed. Linux CI commands/container runtime are configured; full host Linux developer walkthrough not separately executed. Python 3.11 minimum compatibility not separately executed (local/CI baseline is 3.12).
Test suite emits one upstream Starlette deprecation warning for httpx TestClient; functionality passes; keep httpx as requested and consider future transport migration in a separate dependency update.

## Image identities used
- MySQL: mysql@sha256:76f0358884cb92d9a086d24e5671c38048d3fef40f2588703d73eb55392d6b69
- Redis: redis@sha256:44960b3100c48159a66d28c18b0588c193492e25f7551d60e51dd464fc3eca5b
- Python base: python@sha256:a0f57064cbdcd6285fa45f51237ab0b35ea8ebaed06a1f5973e89e19dfb86704
Dockerfile pins uv 0.12.5; Python/MySQL/Redis version tags may receive patches, so use these digests if exact historical reproduction is required.

## Current local state
Compose dependencies remain healthy at 127.0.0.1:3306 and 127.0.0.1:16379. Uvicorn verification process remains at http://127.0.0.1:18000. .env has generated local-only passwords and is ignored. No remote repository, push or Git commit was requested/performed. MySQL volume retained. Docker build/pull logs are ignored local files.

## Next feature
002-mysql-index-baseline: specify deterministic data generator, primary/unique/composite index experiments, EXPLAIN ANALYZE and evidence collection. Keep all business/stock/cache/worker scope for separate features.
