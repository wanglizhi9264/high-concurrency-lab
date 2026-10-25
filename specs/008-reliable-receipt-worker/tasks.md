# Tasks: Reliable Receipt Worker

## Phase 1 — Setup
- [x] T001 Record accepted queue/lease/outbox decision before implementation in docs/architecture/decisions/0006-reliable-worker.md and verify existing ignores.

## Phase 2 — Foundation
- [x] T002 Write pure intent/budget/contract tests first in tests/unit/test_tasks.py; enforce attempts1..5, fail-first0..5, delay0..5000ms and lease greater than timeout+0.5s.
- [x] T003 Define Task/Outbox/Attempt/Event/Receipt with UUIDhex/task scope, UNIQUE receipt(order_id), UNIQUE attempt(task,number), coherent state/lease and attempt bounds in src/concurrency_lab/models/tasks.py; add explicit migrations/versions/0005_receipt_tasks.py and guarded business_schema --revision0005 without changing0001–0004.
- [x] T004 Extract actual shared owned-resource/explicit transaction lifecycle into src/concurrency_lab/db/business.py and driver-code helper into db/errors.py; preserve007RR semantics with regression tests.

## Phase 3 — US1 durable acceptance (P1)
Independent test: broker unavailable still commits task/outbox, later dispatcher recovers.
- [x] T005 [US1] Add creation/replay/unpaid/rollback API tests in tests/integration/test_tasks.py before implementation; implement fixed SQL repository, narrow schema and task service/routes in src/concurrency_lab/repositories/task_repository.py, schemas/tasks.py, services/tasks.py and api/routes/tasks.py.
- [x] T006 [US1] Implement bounded scoped Redis7 Streams adapter in src/concurrency_lab/cache/task_stream.py with real duplicate/malformed/unavailable tests in tests/integration/test_tasks.py.
- [x] T007 [US1] Implement Task→Outbox lock order, bounded publication and due reconciliation in src/concurrency_lab/workers/dispatcher.py; test post-XADD/pre-mark ambiguity and exact-scope stream loss.

## Phase 4 — US2 execution/recovery (P1)
Independent test: actual child exits after committed claim, lease expires, new worker produces one receipt.
- [x] T008 [US2] Write success/failure/deadline/exhaustion/stale-token/concurrent-receipt tests first in tests/integration/test_tasks.py; implement lease claim, fixed handler, fenced atomic finalization and retained linked retry in src/concurrency_lab/services/task_execution.py.
- [x] T009 [US2] Implement independent bounded CLI/runtime with explicit database/scenario, safe stop, Redis7 pending recovery and actual crash probe in src/concurrency_lab/workers/runtime.py and receipts.py.
- [x] T010 [US2] Execute actual subprocess crash/restart, last-attempt abandonment, post-commit/pre-ACK, broker repair and stale success/failure tests in tests/integration/test_tasks.py; retain unknown crash finish/duration.

## Phase 5 — US3 explain lifecycle (P2)
Independent test: actual UI task/attempt/receipt values match APIs; queue fields retain distinct source/unknown semantics.
- [x] T011 [US3] Write intent preservation/null/source/context-switch tests in frontend/tests/taskLab.test.ts before frontend implementation.
- [x] T012 [US3] Build frontend/src/types/tasks.ts, api/tasks.ts, composables/useTaskLab.ts and views/TaskLabView.vue; navigation/paid-order link, separate HTTP/async observations; run frontend/e2e/taskLab.spec.ts against actual scoped worker.

## Phase 6 — Validation and publication
- [x] T013 Implement scripts/verify_worker_lab.py, execute actual functional acceptance and preserve exclusive raw source/window/probe/result records in docs/experiments/008-reliable-receipt-worker/.
- [x] T014 Extend existing .github/workflows/ci.yml with explicit0005/task integration and actual worker E2E while retaining prior gates; no heavy performance in normal CI.
- [x] T015 Update README.md, AGENTS.md, docs/architecture/, docs/database/tasks.md ER and docs/guides/worker-lab.md with transaction/queue/ACK/failure semantics and exact commands.
- [x] T016 Run local quality/integration/frontend/E2E/prior-evidence gates, review and Converge; record real results in specs/008-reliable-receipt-worker/validation.md and converge.md.
- [ ] T017 Push independent branch, create/attach protected PR, verify remote required checks, merge and update main before009; record publication in specs/008-reliable-receipt-worker/validation.md.

## Dependencies and execution
T001→T002→T003→T004→T005→T006→T007→T008→T009→T010; US3 tests/UI follow API contracts; final gates follow all stories. Test specifications precede corresponding source. No delegated implementation. Independent read-only unit and frontend checks may run concurrently after source stabilizes; measured acceptance runs alone. MVP is US1 durable acceptance, then complete US2 and US3 before publication. FR001:T002–005; FR002:T006–007; FR003:T008–010; FR004:T005/T008–010; FR005:T005/T011–012; FR006:T001/T003–004/T006/T009; FR007:T002/T005–014; FR008:T013–017. SC001–005 covered by the story independent tests and final gates.

## Phase 7: Convergence
- [x] T018 [US2] Close lifecycle verification gap (FR003/004/007, edge cancellation; constitutionIX): add actual cancellation after committed claim and atomic creation failure-after-INSERT rollback tests in tests/integration/test_tasks.py; prove no false completion/ACK, retained recoverable lease, no partial Task/Outbox, then rerun task integration and quality gates.
