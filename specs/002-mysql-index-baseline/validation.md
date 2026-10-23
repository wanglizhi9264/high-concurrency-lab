# 002 Validation Evidence
Date: 2026-10-23 (Asia/Shanghai). Feature branch: feature/002-mysql-index-baseline.

## SDD
Official installed Spec Kit 1.2.3 skills used: Specify -> Plan -> Tasks -> Analyze -> Implement. spec-template resolver, setup-plan/setup-tasks and check-prerequisites executed. Constitution1.0.0 unchanged; eleven principles checked before/after design. Clarify skipped (no major ambiguities). No extension hooks registered. Plan research used a read-only research subtask as required by official skill. Pre-implementation analysis covers nine FR/five SC. Converge reviews the completed implementation before publication.

## Actual local results
- `uv run pytest tests/unit/test_index_baseline.py` before implementation: expected missing module collection error.
- `docker compose -f compose.yaml -f compose.experiments.yaml --profile experiments up -d --wait mysql-experiment`: healthy, dedicated instance/volume at13306.
- `uv run python scripts/provision_index_lab.py`: fixed databases and lab_exp permissions created without deleting anything.
- `uv run python scripts/verify_index_lab.py --orders 10000`: full init/seed/baseline/optimize/optimized accepted.
- Same command `--orders 100000 1000000`: both full pipelines accepted.
- Exact data: 10000/100000/1000000 orders with20000/200000/2000000 items,1000users/100products each; checksums and generation digest match before/after index upgrade.
- `uv run python scripts/verify_index_lab.py --verify-only`: all3 scales accepted. Six SQL cases each,7 wall samples/query/phase plus real TREE plan; OFFSET and keyset same page.
- `uv run python scripts/verify.py`: Ruff/format/mypy passed; unit suite initially19 then20 after amount consistency test. Final count is confirmed by CI/check output.
- `uv run pytest tests/integration` without opt-in:3 passed,4 explicitly skipped (dedicated experimental tests).
- First opt-in experimental smoke:4 passed against real MySQL, including full two-stage pipeline; subsequent run:3 passed,1 skipped intentionally because optimized test data is retained, no reset/downgrade performed by fixture.
- Unit guards: forbidden DB names, wrong actual DB/ownership, seed/batch validity and determinism, digest invariance, baseline identity mismatch, actual plan parsing, stable paging SQL, amount/item consistency.
- Real tests: invalid FK and negative price rejected; MySQL/asyncmy maps CHECK violation to OperationalError rather than IntegrityError, so test uses DBAPIError for that case. Tied timestamp pagination test uses a rollback-only update to force duplicates, then verifies complete keyset walk without duplicates/omissions.
- Wrong-db CLI seed: exit2, refusal before connecting. Existing generation result: exit2, no overwrite. Nonempty seed test: refusal.
- `uv run alembic upgrade head; uv run alembic check` on app DB: successful, no metadata differences; existing MySQL/Redis/API tests still pass.
- Separate fresh Compose project hcl-migration-check port14306, only its empty test DB: upgrade head -> downgrade0002 -> upgrade head -> downgrade base -> upgrade head all passed, then Alembic check no differences. This explicitly targeted empty test environment, never the measured data. Instance stopped afterward; volume retained.
- Local Windows pytest temp permission problem worked around with `--basetemp .pytest_cache/...`; no application behavior changed.

## Evidence and limitations
Raw immutable JSON and report: docs/experiments/002-mysql-index-baseline/. MySQL image digest recorded in report. No full data dumps or credentials committed. CPU/memory utilization not sampled (null); Docker allocated CPU/memory and MySQL config/connection count recorded. One client, warm cache,7samples, no cold-cache or concurrent load claims. Cursor acquisition is an explicit extra OFFSET cost. Optimized writes were not benchmarked. DBeaver GUI instructions researched from official docs, not clicked/tested locally. Python3.11 not separately executed; baseline/CI Python3.12.
Existing upstream httpx TestClient deprecation warning remains; functionality passes. No dependency changes.

## Publication
This feature is delivered through a branch and PR to protected main. Remote CI outcome and merge are verified against the PR, rather than inferred from local tests. See the final delivery message / PR checks for the actual remote run and merge SHA.
