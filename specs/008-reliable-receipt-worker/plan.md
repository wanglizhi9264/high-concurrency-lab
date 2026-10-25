# Implementation Plan: Reliable Receipt Worker
**Branch**: feature/008-reliable-receipt-worker | **Date**:2026-10-25 | **Spec**:[spec.md](spec.md)

## Summary
Implement one paid-order receipt handler with MySQL Task/Outbox/Attempt/Event/Receipt records and Redis7 Streams transport. Independent CLI workers are scoped to one owned database and inventory scenario. Database lease fencing, atomic result commits and durable republishing make duplicate/lost transport recoverable. ADR0006 is accepted before source implementation.

## Technical Context
Python3.12, FastAPI/Pydantic2, SQLAlchemy2/asyncmy/MySQL8.4/Alembic, redis-py7.4.1/Redis7, Vue3/TS/VTU/Playwright. No new framework or dependency. Task attempts1..5; handler timeout default1s (0.1..10); lease default5s (1..60, >handler timeout+0.5); Redis command deadline250ms, BLOCK100ms, dispatcher batch<=5/cooldown5s. Fixed handler, no arbitrary scripts, external email or production payment. Existing write opt-in and owned database guards apply.

## Constitution Check
All11 principles pass before/after design. I/II: HTTP service, SQL repository, queue adapter and independent worker have actual separate responsibilities; shared owned-session lifecycle extracted only because API/worker now reuse it. III/IV: explicit0005, no startupDDL, atomic task/outbox/result and fenced state transitions. V: Redis is non-authoritative scoped transport, bounded commands/retention. VI: measured attempts/events/queue snapshots and unknown crash timings, no invented workflow. VII/VIII: ADR/ER/runbooks and unchangedlock. IX: actual broker/DB/process tests plus Vue/E2E. X: named database/scenario, fixed handler/keys, no exposed lease token/credentials. XI: independent SDD/PR after main c9be2f4; nohooks; Constitution2.0.0 unchanged.

## Storage and state
models/tasks.py and Alembic0005 add:
- OrderReceipt: BIGINTPK, UNIQUE order_id FKpurchase_order, exact total DECIMAL14,2, immutable JSON snapshot, created_at UTC DATETIME(6).
- DurableTask: UUIDhexPK, scenario/order FKs, fixedkind, payload fingerprint, immutable fault configuration JSON, max_attempts, attempts, queued/running/retry_wait/succeeded/failed, available_at, private lease_token, lease_until, safe last_error, result_receipt_id FK, retry_of selfFK, created/updated/finished UTC. CHECK attempts/max/state/lease coherence; scope/state/due indexes.
- TaskOutbox: task_id PK/FK, next_publish_at index, publish_count, last_message_id/last_published_at. Repeated publishing is expected; absent confirmation is not proof of no XADD.
- TaskAttempt: PK, taskFK, UNIQUE(task,number), worker_id, running/succeeded/failed/timeout/abandoned, started/finished UTC, separate abandoned_at, nullable handler_ms, safe error, actual timeout/lease budgets. Crash finish/handler_ms remain null.
- TaskEvent: PK, taskFK, UTC, fixedtype/source, bounded safe JSON details. API returns latest100, older records retained.

Task creation UUID fingerprints order/max_attempts/fault plan/retry_of. Same intent replays via complete rollback/fresh transaction on1062. Only paid orders accepted; scenario derives from the order, not client broker keys. Failed is terminal; explicit retry creates a new idempotent successor linked to original, optionally clears controlled faults. No reset of old attempts.

Preserve0001–0004. business_schema keeps default0004 for007 and gains explicit --revision0005; already-newer schema is retained rather than downgraded. Existing base init remains0003. CLI guards actual database/purpose/ready before upgrade. No002schema changes.

## Transaction and resource boundaries
Add open_business_resources and owned_session to db/business.py for lifespan-owned engine/sessionmaker and guarded explicit transactions. InventoryService delegates its existing RR transaction body without changing its error/replay semantics. New task writes use explicit READ COMMITTED plus current Task locks; readonly detail uses REPEATABLE READ so its task, attempts, events and receipt share one snapshot. Move reused driver code extraction to db/errors.py, keep inventory import compatibility. No pool per request/message.

Task API commits Task+Outbox+created event together, no Redis prerequisite. Dispatcher first selects bounded candidate IDs without locks, then locks Task→Outbox and rechecks due/current state. One bounded XADD occurs while those rows are held; publication mark/event commit afterward. Error rolls back publication confirmation and leaves durable intent; duplicate transport is correct. Database nonterminal due scans heal transport loss/trim with cooldown; active leases are excluded.

Worker claim locks Task within explicit scope, reads database UTC, and only actual ownership increments attempt. Active lease returns busy without ACK; future retry is safely deferred using durable outbox; terminal duplicates may ACK. Expired ownership marks old attempt abandoned (abandoned_at, no fake finish/duration), then reclaims if attempts remain or terminal-fails at the limit. Claim commits and releases Session before handler execution.

Handler optionally executes clearly labelled real delay/fail-first probes, reads paid-order snapshot from MySQL and prepares receipt data under its own deadline. handler_ms is monotonic after claim through handler completion/failure, excluding claim/finalization/ACK. Finalization locks Task, verifies token/state/DB expiry; explicit receipt no-op upsert + current read and conditional fenced Task update commit atomically. If final rowcount is not1, rollback effect. Failure/retry transitions use the same fence; next_due/outbox/attempt/event are atomic before ACK. ACK failure never undoes succeeded; record observed ACK result separately when possible.

## Redis transport and CLI
cache/task_stream.py owns fixed stream keys: hcl:tasks:v1:{database:scenariohex}:stream, group receipt-v1. Only task_id transported. XGROUP id0-0/mkstream, ignore only BUSYGROUP; XAUTOCLAIM Redis7 three-item parsing/cursor; XREADGROUP count1/BLOCK100/noackfalse; XACK after durable safe disposition. Approximate maxlen1000 and24h idleTTL bound transport retention, database repairs missing nonterminal work. No KEYS/FLUSH or arbitrary command API.

workers/dispatcher.py performs outbox/reconciliation, workers/runtime.py coordinates claim/handler/finalization/ACK, workers/receipts.py CLI owns resources/loop/signals. Required --database and --scenario; --role both|dispatcher|consumer, --once or bounded --max-cycles, timeout/lease validated, --crash-after-claim is explicit experiment-only actual subprocess exit after commit. Normal stop finishes bounded in-flight work when possible; forced death recovers via lease. No HTTP process-start endpoint.

## API and Vue
TaskResponse uses narrow observed envelope, separate from old payload unions. POST /business/tasks creates intent, GET /tasks/{uuid} gives bounded detail, GET /tasks?scenario_id=... lists<=20, POST /tasks/{uuid}/retry creates linked successor; queue GET /task-queues/{scenario} independently samples DB counts then Redis XLEN/XPENDING/group lag/PTTL. Commands generated from confirmed database/scenario contain fixed safe CLI arguments only. Existing write gate and safe errors apply.

TaskLabView saves original UUID/payload, submits/replays, selects/refreshes DB detail, inspects attempts/events/receipt/outbox and queue separately, shows actual scoped worker command and source links. No fake countdown or animation; next_due is earliest eligibility, lease does not prove a live process. XLEN is retained entries, pending is delivered-unacked, lag may be null, database state counts separate. HTTP Trace uses BusinessTracePanel; async history uses distinct attempt/event models. Fault configuration has explicit controlled_fault_configuration label, measured outcomes distinct. Failed successor UUID saved across HTTP retry; original failed history preserved. Inventory paid-order view links to tasks with order query parameter.

## Source touch points
- domain/tasks.py, models/tasks.py, schemas/tasks.py and shared UTC database timestamp type.
- repositories/task_repository.py fixed SQL for lifecycle/outbox/receipt/event; services/tasks.py public workflow; services/task_execution.py lease/finalization protocol.
- cache/task_stream.py, workers/dispatcher.py/runtime.py/receipts.py; db/business.py/errors.py lifecycle reuse, main resource integration, business_schema0005, core config/errors.
- api/routes/tasks.py, frontend/types/tasks.ts/api/tasks.ts/composables/useTaskLab.ts/views/TaskLabView.vue, navigation/paid-order link.
- unit/integration task tests, frontend/tests/taskLab.test.ts/e2e/taskLab.spec.ts, scripts/verify_worker_lab.py, CI, ADR0006/ER/runbook/actualresults/README/AGENTS.

## Validation
Tests precede implementation. Real owned-test scenarios isolate stream/process scopes. Test atomic creation with broker down; post-XADD/pre-mark duplicate; post-DB/pre-ACK failure; same-order concurrent tasks; actual controlled failures/deadline/exhaustion/linked successor; real child process crash after committed claim/restart; stale success/failure tokens; exact-scope stream loss/rebuild; wrong-scope/malformed delivery; max-attempt crash termination. Never reset databases or broad-delete keys. Test child processes are owned and cleaned in finally. UI mocks prove display only; Playwright launches explicit scenario CLI worker and validates real durable receipt/retry history. Acceptance CLI retains actual parameters/source/window/observations and labelled probe configuration. Heavy performance is not normal CI. Review/Converge and protected PR merge precede009.

Retention detail: Redis MULTI/EXEC groups XADD with PEXPIRE, and XGROUP initialization with PEXPIRE. Only BUSYGROUP is ignored; EXEC still applies expiry for an existing group. A transport timeout is unconfirmed, never proof of absent publication. Idle TTL is refreshed on publication or group access, not a task deadline.
