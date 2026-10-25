# Agent maintenance guide
Read .specify/memory/constitution.md, then the active feature under specs/ (including 001-project-foundation and 002-mysql-index-baseline).
Use installed official .agents/skills/speckit-* for new features. Update spec/plan before scope changes.
Run uv sync --frozen and uv run python scripts/verify.py. Integration requires Compose and Alembic head; run uv run pytest tests/integration explicitly.
No create_all, no per-request pools, no shared sessions across tasks, no committed .env. Commerce read APIs now use a separately owned business database;002 measured databases remain immutable.
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

## 004 Business queries
Read specs/004-real-business-trace and docs/guides/business-lab.md. Business mode defaults off; optional lifespan pool only targets concurrency_lab_business or concurrency_lab_business_test. Never use002databases. Explicit provision/init/seed only; no reset. Service owns one Session/read transaction per request, Repository fixed bound SQL/JOIN; ownership guard SQL counts in observedSQL/QPS. Acquisition includes queue/connect/preping, client execute/fetch is not server-only SQL. Header, JSON and browserRTT boundaries differ; pool sample offsets relate to trace UTC start. BUSINESS_INTEGRATION=1 enables isolated real read/pool/cancellation tests. Subsequent features require independent SDD/branch/PR and preserve004read contracts.

## 005 Load testing
Read specs/005-real-load-testing and docs/guides/load-testing.md. Locust/gevent runs only in a child process against an owned temporary API, fixed loopback target and guarded business database. Do not run database tests/builds/other benchmarks concurrently with measured runs. Preserve raw starts/completions/Locust CSV/resources and exclusive result files. Client start rate, completed RPS including failures, successful RPS and SQL attempt coverage are distinct. Resource CPU scopes differ; unknown values stay null. Normal CI validates evidence/API/UI; heavy performance work uses workflow_dispatch. Never edit workload sources mid-measurement.

## 006 Product cache
Read specs/006-redis-cache-aside, docs/guides/cache-lab.md and ADR0004. Existing Redis client is lifespan-owned. Fixed business-database/product1..1000 namespace, finite value TTL and bounded lease/command/coordination. Fill requires BOTH captured generation and lease token; invalidate atomically revokes value/lease and advances generation. Do not remove these fences or substitute process-local locks. Bypass never inspects Redis. Redis errors degrade to actual guarded MySQL reads; failed publication never repeats an already completed SQL query. No KEYS/FLUSH, no arbitrary-key API. CACHE_INTEGRATION=1 tests only precise test namespace keys, never clears developer DBs. Initial lookup hit rate differs from final Redis reuse; ownership and product SQL are separate. Missing products remain uncached. Future product writes must design commit/invalidation consistency; cached data never enforces inventory invariants.

## 007 Inventory
Read specs/007-inventory-idempotency, ADR0005 and docs/guides/inventory-lab.md. Business init stays0003; explicit owned business_schema upgrade applies0004. Never upgrade002 DBs or reset existing stock. Writes default off, require BUSINESS_WRITES_ENABLED; pool session lock timeout is configured on connect. Use fresh UUID scenarios and intent keys. Every write locks Scenario before Order. Unique INSERT precedes availability rejection,1062 unwinds the whole transaction and resolves via freshSession; never reuse an oldRR snapshot/savepoint.1205/1213 roll back application transaction and require same-intent retries. Commit ACK timeout is unknown, not proven absence. Audit reserved/paid separately; cancelled history is not occupancy. Redis does not enforce inventory. INVENTORY_INTEGRATION=1 enables actual constraints/concurrency/lock/deadlock/cancel tests on owned testDB; record actual deadlock victim. Generic frontend observedHTTP owns trace/transport only, business payload types remain separate.

## 008 Durable tasks
Read specs/008-reliable-receipt-worker, ADR0006 and docs/guides/worker-lab.md. Explicit owned business_schema --revision0005 only; default007upgrade remains0004 and retains newer revisions. Required worker database/scenario scope, fixed receipt handler/stream namespace. MySQL task/outbox/attempt/event/receipt authoritative; Redis transient at-least-once delivery. Task→Outbox lock order; claim commits before handler, final success/failure token/state/DBUTC lease fenced; receipt UNIQUE(order_id) effect and terminal state atomic beforeXACK. No handlerSession held during delay. Crash finished_at/handler_ms unknown, abandoned_at only recovery observation. Failed remains terminal, linked successor only. TASK_INTEGRATION=1 includes actual child exit70, broker loss, duplicate ACK/effect and stale-token tests; exact owned-test key cleanup only, noFLUSH/reset. No API process start or arbitrary handler/key/script. TaskDetail RR snapshot; task writesRC, inventory RR unchanged.

## 009 Scale
Read specs/009-scale-comprehensive-lab and ADR0007. Independent009DBallowlist/ScaleBase/migrations/scale; never expand002targets or edit0001–0005. Immutable twinquerydata with samePK(id,created_at), syntheticyear2025/no businessFK; streamactualDBSHA/id/monthcounts. Baselineproof beforecomposite beforecovering; actualusing_index notICP, actualselectedpartitions; queryprojectionincludesmoney/status. Three empty50kwriteprobes separate frommillionfixtures, rotatebatchorder, no million-stockwriteclaim. Source-frozen ownedchild+verifiedexperimentcontainer, separateCSV/raw/CPUscopes/unknowns; cap10000inlinebatchobservations. SCALE_INTEGRATION optin testtargets preservepartialloading/advancedstates. New cleancloneproject/ports/volumes and noenvcopy, never useoldacceptance_local.py/down-v. DefaultPlaywrightports preserved, cloneexplicitports/noReuse. Historical002–008evidence immutable.
