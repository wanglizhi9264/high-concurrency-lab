# Agent maintenance guide
Read .specify/memory/constitution.md, then the active feature under specs/ (including 001-project-foundation and 002-mysql-index-baseline).
Use installed official .agents/skills/speckit-* for new features. Update spec/plan before scope changes.
Run uv sync --frozen and uv run python scripts/verify.py. Integration requires Compose and Alembic head; run uv run pytest tests/integration explicitly.
No create_all, no per-request pools, no shared sessions across tasks, no committed .env. Current schema includes lab_marker and experimental commerce tables; no business order API exists.
Do not claim remote CI passed unless executed on GitHub. Keep actual validation evidence and open tasks honest.

## Git workflow
The stable default branch is main. Start each new feature or fix from updated main on a new
feature/<short-name> or fix/<short-name> branch. Do not implement future features directly on main.
Push the working branch and open a pull request targeting main, with linked SDD artifacts and
actual test results. Merge only after quality and integration checks pass and review is complete.
Never commit local credentials, .env, generated data, caches, virtual environments or logs.

## Index experiments
Read specs/002-mysql-index-baseline/ and docs/experiments/002-mysql-index-baseline/.
Use only the dedicated mysql-experiment instance and allowlisted database names. Never clear or drop a database to rerun experiments. The CLI enforces baseline revision0002 then saved evidence before index revision0003. Preserve existing runs.
Run uv run python scripts/verify_index_lab.py --verify-only for committed evidence. Opt-in database tests need EXPERIMENT_INTEGRATION=1 and the isolated instance; the first run executes the full smoke pipeline, subsequent runs retain data and skip that already-completed pipeline.

## 003 Visualization
Read specs/003-interactive-system-visualization/ and docs/guides/visualization-platform.md.
Frontend lives only in frontend/: npm ci, npm run check, npm run test, npm run build. E2E npm run test:e2e uses actual backend/readiness and requires healthy foundation dependencies; use PLAYWRIGHT_CHANNEL=msedge on Windows when needed.
Preserve immutable 002 JSON. Public APIs only read allowlisted evidence, return validated DTOs, and never execute user SQL or expose absolute server paths. Treat Live Trace, recorded measurements and Simulation as separate evidence types. Current health probes bypass ORM Session. Never invent pool-wait/router/network timings.
Backend resources remain lifespan-owned; instrumentation records only observed event intervals. No database migrations in003. Frontend build/test output and node_modules must remain ignored.
