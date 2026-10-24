# High Concurrency Lab Constitution

## Core Principles

### I. Architecture and modularity
MUST use a src-layout modular monolith. API delegates infrastructure work; introduce layers only for actual responsibilities. Routers own HTTP mapping, Services own workflows, Repositories own persistence, and observability owns instrumentation. Introduce Domain rules only when actual independent invariants exist. No speculative abstractions, circular dependencies or duplicated workflows.
### II. Python standards
MUST use Python 3.11+, typed public functions, Ruff and mypy. Resource ownership must be explicit. Names MUST describe behavior; functions MUST have one primary responsibility and explicit inputs/outputs. Vue components use PascalCase, views end in View.vue, composables use useXxx.ts; TypeScript identifiers use camelCase. Refactors MUST preserve behavior with regression tests.
### III. Database design
MUST use SQLAlchemy 2 and Alembic migrations, explicit primary keys, justified indexes and field types. MUST NOT create tables at application startup.
### IV. Data consistency
MySQL is authoritative. MUST define transaction boundaries; sessions are request scoped and rolled back/closed on failure. Write transactions MUST preserve business invariants with database constraints/conditional updates or row locks; process-local locks MUST NOT be the sole correctness mechanism. Retries MUST classify conflicts and preserve idempotency. Reliable tasks MUST persist state and coordinate transaction/message delivery via a documented durable strategy.
### V. Redis
MUST manage clients in lifespan, bound connection/command timeouts, and treat Redis as non-authoritative unless a later spec explicitly decides otherwise. Foundation remains health-only. Cache, locks and queues require their own approved feature design, bounded namespaced keys and real failure/concurrency tests. Cache is a derivative copy; TTL and invalidation semantics MUST be explicit. Durable task state remains in MySQL; Redis Streams can transport retryable, duplicate deliveries after an ADR.
### VI. Performance evidence
MUST preserve baseline, environment, data size, load, RPS, P50/P95/P99, error rate, CPU, memory and connection counts. Each metric MUST state unit, collection time/window, source, environment, computation and evidence type. Concurrency, arrival rate, throughput, acquisition interval and pure queueing MUST NOT be conflated. Unmeasured values remain unmeasured; historical measurements and teaching simulations MUST have separate models and labels.
### VII. Documentation
MUST keep README, architecture, database, guides and feature artifacts consistent with code. Separate planned schemas from migrated schemas.
### VIII. Dependencies
MUST use uv.lock, frozen installs and stable supported dependencies. Dependency changes require lockfile updates; containers use explicit version tags.
### IX. Tests
MUST test API success, failure, timeout and lifecycle; independently test real MySQL and Redis. CI must run lint, types and unit tests; integration is explicit. Business correctness requires real MySQL transactions/constraints, Redis expiry/invalidation and concurrent inventory/idempotency/recovery tests. Long performance/data-scale suites MUST be opt-in, separate from normal CI. Tests MUST use isolated owned databases and MUST NOT clear developer data. Never claim an unexecuted test passed.
### X. Security and configuration
MUST use environment configuration, ignored local secrets, redacted errors and loopback service ports. MUST NOT commit credentials. Example files contain placeholders only.
### XI. SDD changes
MUST specify and plan before implementation, trace tasks to requirements, analyze consistency before coding, and converge after implementation. Scope changes require spec/plan/task updates.

## Scope and Constraints
Features001–003 remain preserved foundation, immutable index experiments and visualization. Independently specified Features004–009 may add real business reads, Locust workloads, cache-aside, transactional inventory/idempotency, durable workers and large-data experiments in that order. Each stage MUST remain runnable and pass its review and quality gates before the next merges. Business/worker writes MUST be confined to separately allowlisted owned databases; 002 measured databases and JSON MUST remain unchanged. No microservices, Kubernetes or unnecessary frameworks. Ten-million-row data is opt-in, never a startup prerequisite. No unsupported performance claims.

## Delivery Workflow
Run Constitution -> Specify -> Clarify when materially ambiguous -> Plan -> Tasks -> Analyze -> Implement -> Validation -> Code Review -> Converge -> protected-branch PR merge. Continue the next feature from updated main. All local checks and integration acceptance evidence must be recorded; environmental blockers keep acceptance open.

## Governance
This constitution governs reviews. Amendments require rationale, affected artifacts and semantic versioning: breaking principles major, additions minor, clarification patch. Every feature plan checks all eleven principles before and after design.

**Version**: 2.0.0 | **Ratified**: 2026-10-23 | **Last Amended**: 2026-10-25
