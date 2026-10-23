<!-- Sync impact: template -> 1.0.0; added eleven principles and delivery gates; no deferred values. -->
# High Concurrency Lab Constitution

## Core Principles

### I. Architecture and modularity
MUST use a src-layout modular monolith. API delegates infrastructure work; introduce layers only for actual responsibilities. No speculative business modules.
### II. Python standards
MUST use Python 3.11+, typed public functions, Ruff and mypy. Resource ownership must be explicit.
### III. Database design
MUST use SQLAlchemy 2 and Alembic migrations, explicit primary keys, justified indexes and field types. MUST NOT create tables at application startup.
### IV. Data consistency
MySQL is authoritative. MUST define transaction boundaries; sessions are request scoped and rolled back/closed on failure. Future retries require idempotency analysis.
### V. Redis
MUST manage clients in lifespan, bound connection/command timeouts, and treat Redis as non-authoritative unless a later spec explicitly decides otherwise. No locks or queues in foundation.
### VI. Performance evidence
MUST preserve baseline, environment, data size, load, RPS, P50/P95/P99, error rate, CPU, memory and connection counts. Unmeasured values remain unmeasured.
### VII. Documentation
MUST keep README, architecture, database, guides and feature artifacts consistent with code. Separate planned schemas from migrated schemas.
### VIII. Dependencies
MUST use uv.lock, frozen installs and stable supported dependencies. Dependency changes require lockfile updates; containers use explicit version tags.
### IX. Tests
MUST test API success, failure, timeout and lifecycle; independently test real MySQL and Redis. CI must run lint, types and unit tests; integration is explicit. Never claim an unexecuted test passed.
### X. Security and configuration
MUST use environment configuration, ignored local secrets, redacted errors and loopback service ports. MUST NOT commit credentials. Example files contain placeholders only.
### XI. SDD changes
MUST specify and plan before implementation, trace tasks to requirements, analyze consistency before coding, and converge after implementation. Scope changes require spec/plan/task updates.

## Scope and Constraints
Foundation contains health endpoints, shared pools, one migration marker and development tooling. Six future experiments require separate features. No microservices, Kubernetes, commerce business logic or performance claims.

## Delivery Workflow
Run Constitution -> Specify -> Clarify when materially ambiguous -> Plan -> Tasks -> Analyze -> Implement -> Converge. All local checks and integration acceptance evidence must be recorded; environmental blockers keep acceptance open.

## Governance
This constitution governs reviews. Amendments require rationale, affected artifacts and semantic versioning: breaking principles major, additions minor, clarification patch. Every feature plan checks all eleven principles before and after design.

**Version**: 1.0.0 | **Ratified**: 2026-10-23 | **Last Amended**: 2026-10-23
