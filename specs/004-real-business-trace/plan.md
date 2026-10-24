# Implementation Plan: Real Business Request Trace
**Branch**: feature/004-real-business-trace | **Date**:2026-10-25 | **Spec**:[spec.md](spec.md)
## Summary
Opt-in business reads in two isolated owned databases. Preserve001-003; reuse commerce models/Alembic0001-0003. No004Schema/dependency changes.
## Technical Context
Existing Python3.12/FastAPI/Pydantic2/SQLAlchemy2 asyncmy/MySQL8.4/Vue3/TS/Vite/Vitest/Playwright. Windows/LinuxCI. Default10000orders,1000users,100products,2items/order, bounded batches. No throughput promises. BUSINESS_ENABLED defaultfalse; BUSINESS_DATABASE fixed development/test allowlist.
## Constitution Check
Version2.0.0 replaces foundation-only scope per user task. All11principles pass before/after design: explicit layers/types/lifecycle, Alembic only, per-request transactions, no businessRedis004, measured intervals, consistent docs/locks/tests, isolated owned DBs, redaction andSDD/PR. No exceptions or unresolved clarifications.
## Phase0 Research
Read-only backend/frontend research subtasks audited existing specs, code and tests. research.md records decisions and official references.
## Phase1 Design
### Project Structure
core/config.py business opt-in/DB/budget; core/exceptions.py typed failures without HTTP.
db/business.py allowlist, ownership, ObservedDatabase execute/fetch helper.
main.py optional lifespan BusinessResources Engine/session factory; no startupDDL/seed.
observability/recording.py per-request spans; observability/http.py UUID/header/preparation time/safe structured logs.
schemas/business.py product/order/item/page/cursor/trace/response DTOs, Decimal strings.
repositories/product_repository.py and order_repository.py fixed bound SELECT/JOIN, noHTTP.
services/business_service.py per-request Session/explicit read transaction, acquire/ownership/workflow/budget and classified failures.
api/routes/business.py validated HTTP inputs, DI service/context, response/error mapping, noSQL.
experiments/business_dataset.py and scripts/provision_business_lab.py explicit migration/seed; extract pure reference_rows from002dataset with regressiontests, no002safety changes.
frontend/src/api/business.ts, types/business.ts, composables/useBusinessQuery.ts, components/BusinessTracePanel.vue, views/BusinessQueryView.vue; /business route/nav.
tests/unit/test_business.py, integration/test_business.py, frontend/tests/business.test.ts, e2e/business.spec.ts; CI explicit isolated provision/seed/BUSINESS_INTEGRATION.
### Interfaces and metric boundaries
Four GETs under /api/v1/business: products/{id}; users/{id}/orders idASC; users/{id}/order-page timeDESC/idDESC; orders/{id} withitemsJOIN. limit1..100,offset0..100000; paired cursor exclusive withoffset. Typed data/error/trace;404missing,422invalid,503disabled/ownership/db/pool,504budget.
Middleware generates X-Request-ID/X-Process-Time-Ms through response-start preparation (excludes network/body). JSON service_elapsed_ms ends before HTTP serialization; browserRTT separate. Spans carry observedUTCtime, ms unit, measuredsource/environment/definition; acquire includes queue/connect/preping; SQL includes driver/server/fetch. Nested spans not summed.
Every call owns one Session and sequential explicit read transaction. GuardSQL checks currentDB and business-purpose. Product/list/page one businessSQL; detail header+JOIN fixedtwo; ownershipSQL included in SQLcount/QPS. UTCnaiveDATETIME6, Decimal string. Pool gauges before/after are instant snapshots, no waitingestimate.
### Initialization safety
Only concurrency_lab_business/concurrency_lab_business_test. Provision fixed DBs/grants via Compose credentials internally. Init only empty target then Alembic0003. Seed validates emptycommerce/dataset then claims business-lab-v1, records loading, streams batches, marksready. Existingownedready verified/retained; nonowned/nonempty/loading refused. No reset/delete; reject002names beforeconnect. Preserve originalJSON and migrationhistory.
## Complexity Tracking
No newframework/abstractinterface. Separate pool protects health regression and enables later tuning. Shared observation/helper avoids timerduplication. HTTP status mapping remains inRouter.
