# Feature Specification: Reliable Receipt Tasks and Worker
**Feature Branch**:feature/008-reliable-receipt-worker
**Created**:2026-10-25
**Status**:Ready
**Input**: Complete engineering Feature008: durable task creation/queue/worker/state/retry/timeout/idempotency/failed-task disposition and controlled stop/recovery, ADR before queue selection, real visualization/tests.

## User Scenarios & Testing *(mandatory)*
### User Story 1 - Persist a task before transporting it (Priority: P1)
A learner creates an asynchronous task for an actual paid purchase order. The fixed task generates a durable order receipt, without sending email or invoking arbitrary code. The learner can distinguish durable acceptance from actual queue publication.
**Why this priority**: A successful request must not lose the work between database commit and message publication.
**Independent Test**: With the broker unavailable, task+publication intent commit together; a later dispatcher publishes the retained work and the receipt eventually appears.
**Acceptance Scenarios**:
1. Given a paid order, task creation atomically persists task state and a pending publication record. Same UUID and matching intent replay; different intent conflicts.
2. A task is not labelled transported until actual publication is observed. Invalid/unpaid orders do not create partial tasks.
3. Publication failure or process loss retains durable work and allows safe repeated publication, without resetting the database.

### User Story 2 - Process, retry and recover safely (Priority: P1)
An independent worker consumes actual messages, records attempts and materializes one receipt per order. Duplicate delivery, worker death and dependency failures cannot create duplicate effects.
**Why this priority**: In-process background callbacks do not satisfy durable queue semantics.
**Independent Test**: Real broker/database tests cover duplicate deliveries, retries, execution timeout and an actual worker subprocess crash/restart.
**Acceptance Scenarios**:
1. Duplicate messages or multiple tasks for the same order produce at most one durable receipt; acknowledged terminal state is persisted before broker acknowledgement.
2. Retryable failure/timeout is recorded and rescheduled within a bounded attempt policy; exhausted work remains queryable as failed rather than disappearing.
3. A dead worker's ownership expires; another worker recovers it. An old worker cannot finalize with a stale lease/token. Missing timing after a crash stays unknown.
4. Failed work can be retried through an explicit linked successor task, preserving the original failed history. Stopping and restarting workers is controlled and documented.
5. Loss/recreation of transient broker transport can be healed from nonterminal durable database state; no claim of exactly-once message delivery.

### User Story 3 - Explain the real lifecycle (Priority: P2)
The Vue task lab shows actual durable state, publication, queue snapshots, attempts, failure/retry events and receipt outcome, with the exact worker command scoped to the inventory scenario.
**Independent Test**: UI values agree with actual APIs; no animation invents task transitions. Controlled fault/delay inputs are clearly separate from measured attempt outcomes.
**Acceptance Scenarios**:
1. The learner sees created/pending publication, transported/waiting, running, retry wait, succeeded or failed with real collection time/source/units.
2. Fault probes can exercise real failure and deadline paths, explicitly labelled controlled injection; they are not production performance evidence or simulated metrics.
3. Loading/empty/error/retry states preserve task UUID intent across retries; changing the selected task cannot reuse old queue/attempt data as new results.

### Edge Cases
Commit ACK unknown; duplicate/out-of-order publication; broker unavailable/restarted; pending messages claimed by another consumer; lease expiry at finalization; max attempts reached after a crash; process cancellation; malformed message; deleted transport; outcome observation unavailable. Normal/failed task records are retained. Workers operate only on a named owned business database and one explicit inventory scenario, preserving other experiments.

## Requirements *(mandatory)*
### Functional Requirements
- **FR-001** MUST offer a fixed paid-order receipt task with durable task+publication intent creation, UUID/payload idempotency and explicit state transitions; MySQL is authoritative.
- **FR-002** MUST select a lightweight transport after an ADR, publish through a durable outbox strategy, support repeated publication and broker-loss reconciliation, and distinguish acceptance/publication/acknowledgement.
- **FR-003** MUST run an independent worker with consumer ownership, bounded lease/timeout/attempts, idempotent durable effects and stale-owner fencing. No process-local background task substitutes for the queue.
- **FR-004** MUST persist attempts/failure/timeout/retry history, recover crashed workers, retain exhausted tasks and allow an explicit linked-successor retry without erasing original failure history.
- **FR-005** MUST expose actual task/attempt/event/queue/receipt observations and a Vue lifecycle page with real operations/source links, explicit fault-injection configuration, honest unknown metrics and safe error/retry states.
- **FR-006** MUST confine writes/keys/process controls to explicit owned database/scenario scope, bounded fixed commands, lifespan resources, explicit migrations and opt-in writes; preserve previous features/evidence.
- **FR-007** MUST implement real unit/integration/concurrency/subprocess/frontend/E2E tests for durable creation, duplicate effects, broker failure/recovery, retries, timeouts, failed-task retry and actual crash/stale ownership; preserve normal CI.
- **FR-008** MUST execute recorded acceptance, document architecture/ADR/ER/commands/failure recovery/limits, review/Converge and merge an independent protected PR before009.
### Key Entities
DurableTask, PublicationOutbox, TaskAttempt, TaskEvent, OrderReceipt, QueueSnapshot, ControlledFaultPlan, WorkerOwnership. Scope is derived from the paid order's inventory scenario, not an arbitrary raw broker key.

## Success Criteria *(mandatory)*
- **SC-001** Broker-down creation retains complete durable work; later processing succeeds with no missing task between commit and publication.
- **SC-002** Duplicate task/message execution produces one receipt per order; terminal state and receipt remain consistent across crashes, timeout and stale-owner attempts.
- **SC-003** Actual failure/retry/exhaustion and worker crash/restart are demonstrated with bounded completion or a truthful retained failed state, without erasing history.
- **SC-004** The learner can trace each observed lifecycle stage, distinguish controlled inputs from measured outcomes and reproduce scoped worker commands and recovery.
- **SC-005** Related local/protected CI gates pass, earlier data remains intact and actual acceptance evidence is retained.

## Assumptions
Only one fixed receipt handler, no arbitrary scripts, external email, scheduling platform or distributed framework. Receipts are learning records, not real payment processing. Existing paid single-product orders from007 are input. Workers require explicit scenario scope and a separately named business database; tests use fresh scenarios and exact keys. Controlled failure/delay probes are optional configuration and labelled as such; outcomes/timings still come from real worker execution. Exhausted tasks remain terminal; manual retry creates an idempotent successor linked to the failed original. Broker transport may be transient because durable recovery state is in MySQL. This is at-least-once delivery with idempotent effects, not an exactly-once queue claim.
