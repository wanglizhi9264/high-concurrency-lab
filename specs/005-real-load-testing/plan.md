# Implementation Plan: Real Load Testing
**Branch**: feature/005-real-load-testing | **Date**:2026-10-25 | **Spec**:[spec.md](spec.md)
## Summary
Independent Locust child drives an owned temporary single-worker API. Preserve raw Locust/request CSV and process/container resource samples; publish a typed immutable summary and Vue comparison. No performance framework runs inside FastAPI.
## Technical Context
Existing Python3.12/Locust2.47/httpx/SQLAlchemy/Vue/ECharts. Declare existing transitive psutil as direct dev dependency for process CPU/RSS. Runtime5..300s; users10/50/100/500; separate startup users/s and per-user task pacing. Reuse004owned10000orders; no writes during load.
## Constitution Check
All11 principles pass before/after design: modularity, typed boundaries, lifespan pools, existing transactions, no Redis cache, truthful evidence, versioned docs/locks/tests, loopback/allowlist, SDD/PR. Heavy load is opt-in. Research.md resolves statistical unknowns from official source and installed2.47.
## Phase1 Structure and responsibilities
schemas/benchmarks.py defines typed manifest/summary/history/resource/recorded-run and finite/time-order validation.
experiments/load_recording.py owns raw completion CSV and pure aggregation, no Locust imports.
benchmarks/locust/locustfile.py owns HttpUser and per-environment recorder, one request/task, deterministic per-user mix, closed-loop pacing.
scripts/run_load_test.py validates bounds, creates unique output dir, owns API/Locust children and cleanup, samples psutil/Docker/business metrics, retains incomplete raw files and publishes result.json only after normal validated completion.
services/benchmarks.py and api/routes/benchmarks.py expose bounded fixed-directory ID/list/detail records; no load or shell HTTP endpoint. services/load_monitor.py and repositories/metrics_repository.py read actual business pool/dataset/version/global status through shared engine and bounded acquisition. Monitoring competes with load and is disclosed.
Extend order repository/service/router with global time-ordered GET /api/v1/business/orders for real deepOFFSET; explicit nullable user filter, no magic ID. Existing004contracts retained.
frontend types/benchmarks.ts, api/benchmarks.ts, views/LoadTestView.vue; ChartPanel adds LineChart/optional aria label without changing002bar defaults. Two run selections, request-sequence protection, parameter difference notes, unsmoothed lines/null gaps.
tests/unit/test_load_testing.py, integration monitor/globalpage cases, frontend/real-record browser tests; separate workflow_dispatch performance job, ordinaryCI no heavy matrix.
## Metrics and data
Manifest: UTC window/monotonic duration, dataset purpose/digest/count, versions/revision, users/spawn/pacing/pool/timeouts, actual peakusers, rawfiles and complete state. Request CSV: completion UTC, response ms, HTTP/error category, requestID, received SQL attempt count or unknown. Client request-start time only if provided by pinned Locust; never called server arrival.
Exact overall linear-interpolation percentiles come from raw response samples, distinct from rounded Locust histogram values. CompletionRPS=N/actual window; received-SQL-spans/window labelled observed attempts with coverage, not server totalQPS. One-second completion buckets use timestamps. Original rolling Locust history retained, no averaging percentiles.
MySQL Questions/Queries/Threads/Uptime snapshots describe entire instance including monitoring, health and transactions; detect resets before deriving rates. Pool snapshots use business pool. Resources each have UTC/elapsed/source/scope and nullable CPU/memory. psutil scopes owned API/Locust processes; firstCPU null. Docker scopes mysql/redis containers/VM; raw rows and actual intervals retained. No synthesized samples.
## Actual runs
15s ramp-inclusive matrix10/50/100/500, task-rate1,pool5. Extra100/pool1/rate1 and100/pool5/rate2 create controlled pool/pacing pairs. Errors remain measured outcomes, not hidden failures. Short smoke cannot establish capacity or reliable tail latency; longer runs optional up to300s.
## Safety and complexity
Only loopback unused owned API port; preview18002/5173 untouched. Fixed cases and ownedDB guard. Unique directories/exclusive writes; partial runs not published. IDs regex/resolve containment/symlink/size/schema validated. No raw exception-log endpoint. Independent historical adapter preserves002/003. No new runtime framework or distributed generators.
