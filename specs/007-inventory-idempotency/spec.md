# Feature Specification: Transactional Inventory and Idempotent Orders
**Feature Branch**: feature/007-inventory-idempotency
**Created**:2026-10-25
**Status**:Ready
**Input**: Complete engineering request Feature007: minimal real ordering, inventory reservation/deduction, states, unique idempotency, transactions/locks/conflicts/rollback, real concurrent invariants.

## User Scenarios & Testing *(mandatory)*
### User Story 1 - Order against an isolated stock experiment (Priority: P1)
A learner starts a new bounded inventory scenario for one existing product and creates a single-product order. MySQL owns stock and exact monetary values. Earlier generated orders and datasets remain unchanged.
**Why this priority**: Repeatable experiments must not reset a developer's stock or overwrite query baselines.
**Independent Test**: A new scenario starts with known stock; a successful order reserves the requested units and records the exact order atomically.
**Acceptance Scenarios**:
1. Given fresh stock, when creating a valid order, then one complete order and one reservation commit together; stock never becomes negative.
2. Given insufficient stock or an invalid user, then no partial order or reservation commits.
3. Given many distinct concurrent requests, committed quantities cannot exceed initial stock, and the audit confirms available+reserved+sold equals initial.

### User Story 2 - Retry safely and change state (Priority: P1)
A learner repeats a request with the same key, tries conflicting payloads and changes an order to paid or cancelled.
**Why this priority**: Network retries and conflicts must not double-reserve or double-release stock.
**Independent Test**: Repeated matching requests return the same committed order without additional reservation; changed payload under the same key is refused.
**Acceptance Scenarios**:
1. Given simultaneous identical idempotent requests, then exactly one order/reservation commits; all successful replays refer to that order.
2. Given an existing key with different scenario/user/quantity, then conflict is explicit and no additional write commits.
3. Reserved→paid moves reserved units to sold; reserved→cancelled returns them to available. Repeating the same final target changes nothing; switching between final states is rejected. A concurrent pay/cancel race permits only one final result.
4. Deadlock, lock wait timeout, request/pool timeout and dependency failure have safe classifications and documented retry rules. Retrying creation uses the same key; invalid transitions are not blindly retried.

### User Story 3 - Inspect transaction evidence and invariants (Priority: P2)
The Vue lab shows actual creation/state requests, SQL/transaction spans, outcomes, stock and an audit of committed quantities. An acceptance script saves genuine concurrent results.
**Independent Test**: User can run a small bounded stock contest, inspect failure/replay outcomes and verify invariants using actual persisted data, not animation or HTTP200 alone.
**Acceptance Scenarios**:
1. Each write has explicit transaction boundaries and actual SQL/lock-related statements; execution intervals do not pretend to isolate server lock wait.
2. New experiments create new scenarios; there is no reset or arbitrary SQL endpoint. Writes require explicit enablement and an owned business database.
3. UI loading/empty/error/retry states preserve idempotency keys across retries; recorded results disclose scope/time/source/limits.

### Edge Cases
Same key concurrent insert visibility, commit acknowledgement uncertainty, duplicate final transitions, cancel/pay races, missing scenario/order/user, insufficient stock, actual lock waits, deadlocks, request cancellation and rollback. Existing004read/006cache contracts and002/005/006evidence stay intact. Product cache is never an inventory authority.

## Requirements *(mandatory)*
### Functional Requirements
- **FR-001** MUST provide bounded fresh stock scenarios and minimal single-product order create/query/state operations, with exact prices read from MySQL and no reset of existing scenarios or generated baseline orders.
- **FR-002** MUST enforce nonnegative stock and available+reserved+sold=initial at the database boundary; reserve/order/state changes have explicit atomic transaction boundaries using conditional updates/row locks and constraints.
- **FR-003** MUST enforce unique request keys, payload-match replay and mismatch conflict across concurrent processes; retries cannot reserve twice. No process-local or Redis lock is the sole correctness guarantee.
- **FR-004** MUST define states, idempotent terminal transitions, rollback, deadlock/lock-timeout classification and bounded retry guidance; failed transactions leave no incomplete order.
- **FR-005** MUST expose actual request/transaction/SQL/source evidence, bounded Vue controls and a persisted-state invariant audit. Loading/error/empty/retry feedback is honest; failed HTTP is not success.
- **FR-006** MUST use explicit Alembic migration and safe owned-database initialization, real unit/integration/concurrency/frontend/E2E tests, preserve CI and immutable historical experiments.
- **FR-007** MUST execute a repeatable actual concurrent acceptance experiment, document invariants/schema/commands/results/limits, review/Converge and merge an independent protected PR before008.
### Key Entities
InventoryScenario: one product, initial/available/reserved/sold quantities and unique experiment identity. PurchaseOrder: scenario/user, exact quantity/unit price/total, unique key and payload fingerprint, reserved/paid/cancelled state. InvariantAudit: independently aggregated committed orders and stock consistency. ObservedWrite: genuine transaction and SQL intervals, result and safe conflict code.

## Success Criteria *(mandatory)*
- **SC-001** Concurrent successful reservations never exceed initial stock and all audited counters match committed orders; constraints reject negative/inconsistent quantities.
- **SC-002** Matching-key concurrency yields one order/reservation; mismatch, failed transactions, lock contention and terminal races preserve invariants with safe outcomes.
- **SC-003** The learner can create/query/retry/transition/audit through real UI/API and inspect actual SQL/transaction evidence; no stock is fabricated or reset.
- **SC-004** Related local and protected CI checks pass, a real concurrent report is retained and older datasets/records remain unchanged.

## Assumptions
A stock scenario is a new isolated learning batch, not a reset of product stock. One product per order is sufficient; no real payment gateway, refund, multi-item checkout, Redis stock, tasks or queue in007. Existing generated lab_order tables remain historical query fixtures; new purchase orders have distinct names/routes. Business writes default disabled, enabled only for explicitly owned business DBs after migration. MySQL remains authoritative even if product cache contains stale data. Cancellation restores stock only before payment; repeated final state is a no-op.
