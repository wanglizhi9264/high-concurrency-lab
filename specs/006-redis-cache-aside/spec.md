# Feature Specification: Redis Cache-Aside Learning Lab

**Feature Branch**: `feature/006-redis-cache-aside`
**Created**: 2026-10-25
**Status**: Ready
**Input**: Feature006 in the complete engineering request: real product Cache-Aside, bypass/miss/hit/expiry/invalidation/refill/hotspots, truthful metrics, concurrency and Redis failure recovery.

## User Scenarios & Testing *(mandatory)*
### User Story 1 - Follow a real cache lookup (Priority: P1)
A learner compares the same product with cache bypass, an empty cache, a hit, expiry and active invalidation. Each response explains where the value came from and which actual operations ran.
**Why this priority**: Redis health PING does not teach how caching affects real MySQL work.
**Independent Test**: An isolated real environment returns identical product data; a hit performs no business SQL while bypass/miss does. Expiry and invalidation cause another guarded read.
**Acceptance Scenarios**:
1. Given an initialized owned business dataset and empty product cache, when looking up twice, then the first query returns from MySQL and the second from Redis, with different actual traces.
2. Given a cached product, when its TTL expires or the learner invalidates it, then the next lookup refills from MySQL. Invalidation racing with an earlier fill cannot publish that earlier generation afterward.
3. Given bypass mode, when reading, then Redis is not involved and existing business data/contracts remain intact.

### User Story 2 - Understand cache failure and competition (Priority: P1)
A learner sees concurrent cold requests, coordination waiting and fallback, rather than assuming every miss means one database query.
**Why this priority**: MySQL remains authoritative; a cache optimization cannot make unavailable Redis a correctness dependency.
**Independent Test**: Concurrent real cold reads return consistent products, bounded coordination terminates, and unreachable Redis falls back to real MySQL. No process-local lock is the sole coordination mechanism.
**Acceptance Scenarios**:
1. Given simultaneous cold reads, when a fill completes within the coordination lease, then waiting readers may reuse it; timeout/lease expiry permits explicitly recorded duplicate refills rather than unbounded waiting.
2. Given Redis unavailable or corrupt cached content, when reading, then valid MySQL data is returned with degraded/cache-invalid evidence; raw infrastructure errors and credentials are not exposed.
3. Given a missing product, then no invented product is returned; penetration risks and the selected missing-value policy are documented and tested.

### User Story 3 - Inspect actual experiment evidence (Priority: P2)
The Vue lab lets learners execute real lookups/invalidation and inspect Redis key purpose, remaining TTL, memory, hit outcome, SQL count and latency. A bounded repeatable experiment saves actual results.
**Independent Test**: UI values and plotted/request evidence agree with actual API responses; recorded evidence has explicit source/time/unit/environment and no synthetic measurements.
**Acceptance Scenarios**:
1. Given a sequence of real requests, then observed hit rate uses a disclosed denominator, MySQL SQL count comes from actual returned spans, and Redis command timing is distinguished from network RTT.
2. Loading, empty, error and retry states are visible; cache key names are scoped to the owned business database; no arbitrary Redis commands or key patterns are accepted.

### Edge Cases
Redis unavailable before/after read; lease expiry or cancelled fill; simultaneous invalidation; invalid/malformed cached value; absent product; TTL boundary; failed inspection command leaves memory/TTL unknown. Multiple refills are safe reads, not a distributed exactly-once claim. No cache writes alter authoritative MySQL data. Pre-existing002/005records remain immutable.

## Requirements *(mandatory)*
### Functional Requirements
- **FR-001** MUST implement real product Cache-Aside with bypass, miss, hit, TTL expiry, explicit invalidation and refill; keep MySQL authoritative and avoid caching the whole dataset.
- **FR-002** MUST use bounded namespaced keys/commands/timeouts, bounded best-effort cold-fill coordination and generation fencing against invalidation races; Redis failure degrades to guarded MySQL reads.
- **FR-003** MUST expose actual request outcomes, Redis command spans, SQL attempts, latency, selected-key TTL/memory and invalidation events; sampled hit-rate scope and unavailable values are explicit.
- **FR-004** MUST add an interactive Vue cache lab with real operations, source links, safe error/retry/loading/empty states and preserve earlier pages/contracts.
- **FR-005** MUST validate real expiry, invalidation, concurrent refill, stale-fill rejection and Redis failure/recovery using isolated owned test data/keys; retain unit, integration, concurrency and frontend/E2E gates.
- **FR-006** MUST save repeatable actual bypass/cold/hot/expiry/invalidation/concurrency evidence, analyze consistency/penetration/stampede/avalanche/duplicate refill/degradation and known limits, review/Converge and merge an independent PR.
### Key Entities
ProductCacheEntry: product copy, generation and source database; CacheOutcome: hit/miss/bypass/degraded plus actually observed operations; CacheInspection: selected key, TTL/memory sample with time and source; CacheExperiment: requests, scoped hit rate and raw evidence.

## Success Criteria *(mandatory)*
- **SC-001** Real sequences demonstrate all six states with unchanged product data and zero business SQL spans on a true hit.
- **SC-002** Concurrent and failure tests establish returned-data correctness, bounded completion and stale-generation rejection; limitations do not assert guaranteed single refill.
- **SC-003** The learner can reproduce and inspect every operation, distinguish measured from recorded evidence and verify metrics against saved raw responses.
- **SC-004** All relevant local and protected-PR checks pass, earlier immutable evidence is preserved and operating instructions match code.

## Assumptions
Local learning system, existing owned10000-order business dataset and Redis lifespan client. Product mutations remain outside006; future write features must define invalidation after committed changes. Cache staleness is bounded by selected TTL, not a strong-consistency promise. Product experiment identifiers are bounded1..1000 (seeded1..100, missing IDs remain testable). Missing products are not cached initially; penetration is demonstrated/documented instead of claiming a protection not built. No new runtime framework, schema change, inventory or worker feature.
