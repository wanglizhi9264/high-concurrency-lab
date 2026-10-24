# Feature Specification: Real Business Request Trace
**Feature Branch**: feature/004-real-business-trace
**Created**: 2026-10-25
**Status**: Accepted for planning
**Input**: Complete engineering task, first independent Feature004; preserve001–003.

## User Scenarios & Testing *(mandatory)*
### User Story1 - Execute real business reads (Priority: P1)
Learners query a product, a user's orders, a stable time-ordered page, and an order with its items against an isolated business dataset.
**Why this priority**: Actual business data is needed before meaningful concurrent/cache experiments.
**Independent Test**: Four read operations return exact seeded records and decimal amounts; missing entities and invalid paging are explicit errors.
**Acceptance Scenarios**:
1. Given an initialized business dataset, when each query is sent, then results correspond to that dataset and the measured002 databases remain unchanged.
2. Given tied timestamps, when walking cursor pages, then ordering is stable with no duplicate or omitted IDs in the unchanged dataset.
3. Given an order with multiple items, when fetching details, then database work is bounded by fixed query count rather than item count.
### User Story2 - Understand actual execution and failure (Priority: P1)
Learners see the request identity, exact fixed query, acquisition/execution intervals, resource snapshot and corresponding source, including unavailable/timeout outcomes.
**Why this priority**: Trustworthy observation is the basis of later comparisons.
**Independent Test**: Real success and real isolated pool exhaustion produce request IDs, bounded outcomes and released resources; public errors expose no credentials or exception text.
**Acceptance Scenarios**:
1. Given a business request, when inspecting it, then each observed interval has a unit, source, collection time, definition and evidence label.
2. Given a dependency failure or exhausted pool, when a request completes, then the error is bounded, observable, sanitized and subsequent requests can recover.
3. Given concurrent requests, when sessions are used, then each owns an independent transaction scope and all connections are returned.
### User Story3 - Reproduce and maintain (Priority: P2)
A new developer safely initializes a small independent dataset and uses the existing Vue platform to execute and inspect real queries.
**Why this priority**: Clean-clone acceptance and code clarity precede feature quantity.
**Independent Test**: Documented setup plus backend/frontend/real-browser gates pass without regenerating002 data.
**Acceptance Scenarios**:
1. Given a normal checkout, when following setup, then business reads are available after explicit migration/seed, without automatic startup DDL.
2. Given an existing/non-owned target, when running initialization, then data is retained and destructive reset is refused.

### Edge Cases
Missing product/order404; unknown user yields empty orders. Limit1..100, offset0..100000; cursor time/id must be supplied together; IDs positive signedBIGINT. UTC-naive microsecond timestamps correspond to UTC. Business mode disabled gives actionable503. No arbitrary SQL or DB target supplied through HTTP. Error/timeout/cancellation must close transactions and release connections. A response-preparation header interval and browser RTT are distinct from service trace duration; nested spans must not be summed.

## Requirements *(mandatory)*
### Functional Requirements
- **FR-001**: MUST provide four real bounded read operations with typed validation, stable ordering and exact decimal serialization; detail lookup has noN+1.
- **FR-002**: MUST preserve002 databases/JSON, use only two allowlisted independently owned business databases and explicit non-destructive initialization.
- **FR-003**: MUST separate HTTP, workflow, query, resource ownership and observation responsibilities; keep per-request Session scope and explicit transaction cleanup.
- **FR-004**: MUST correlate request ID/header, processing-to-response-preparation interval, acquisition and SQL execute/fetch intervals, safe errors/timeouts and instantaneous pool gauges; define each unit/source/time/environment/evidence.
- **FR-005**: MUST provide a real Vue query page with exact request/target/result, selectable trace/source, SQL and parameters; preserve existing003 real/historical/teaching boundaries.
- **FR-006**: MUST test actual database behavior, stable pagination, fixed SQL counts, pool exhaustion, independent concurrent sessions and recovery; keep existing unit/integration/frontend/CI gates.
- **FR-007**: MUST document audit, amendment, module boundaries, diagrams, setup, actual tests/review/limits and deliver through a separate PR after checks.
### Key Entities
Product, UserOrder, OrderItem, OrderPage, Cursor, RequestObservation, MeasuredSpan, PoolSnapshot, OwnedBusinessDataset.

## Success Criteria *(mandatory)*
### Measurable Outcomes
- **SC-001**: All four operations can be executed from the learning page against initialized records, including empty/not-found/invalid cases.
- **SC-002**: Full cursor walk returns every expected ID exactly once; detail work remains fixed for multiple items.
- **SC-003**: Success, pool exhaustion and request-budget failure are observable with distinct request identities and subsequent recovery, with no leaked active connections.
- **SC-004**: The clean-clone runbook, quality gates, existing evidence checks and real-browser acceptance pass with recorded evidence and reviewed code.

## Assumptions
Local loopback learning system, no production/authentication scope. Only Feature004 is implemented in this branch;005–009 follow their own SDD/PR stages. Default business mode off preserves001/003; explicit setup enables a separate business pool. No Redis business cache, inventory writes or worker yet. Existing002 generators are reusable as pure data generators only.
