# Implementation Plan: Redis Cache-Aside Lab
**Branch**: feature/006-redis-cache-aside | **Date**:2026-10-25 | **Spec**:[spec.md](spec.md)

## Summary
Add a product-only Cache-Aside service around004 guarded reads and existing lifespan Redis client. Fixed Redis Lua scripts fence stale fills by both generation and lease token; bounded coordination degrades to MySQL. Extend actual request spans and add a Vue cache lab plus reproducible recorded experiment. Preserve004/005contracts and immutable results.

## Technical Context
Python3.12/FastAPI/Pydantic2/SQLAlchemy2, installed redis-py7.4.1 against Redis7, Vue3/strictTS/VTU/Playwright. No dependency, migration or runtime framework changes. Product IDs1..1000; TTL1..60s plus0..10%positive jitter. Existing separately owned10000-order business database, seeded products1..100; missing IDs not cached. Per Redis command budget250ms, lease1000ms, coordination wait250ms; entire cache read uses configured business budget. No performance threshold promise.

## Constitution Check
All eleven principles pass before/after design. I/II: Router maps HTTP, service owns policy, cache adapter owns fixed commands/Lua; retainSQL repository. III/IV: no DDL or MySQL writes, guarded read transaction reused; future writes need committed invalidation design. V: lifespanclient, bounded derived keys/timeouts, finiteTTL and explicitinvalidations. VI: actual monotonic command spans, UTC samples, separate RTT/SQL/guard metrics and recorded evidence. VII: guides/ADR/source references. VIII: unchangedlock. IX: real Redis/MySQL expiry/race/concurrency/failure tests plus frontend/E2E. X: fixednamespaces, allowlistedbusinessDB, positiveboundedIDs, no raw commands/credentials. XI: SDD precedes code; independentPR/main gate. Constitution2.0.0 needs no amendment; no extensions configured.

## Research and decisions
Official read-only Plan agents investigate Redis atomic scripts/leases and existing frontend reuse. Use Redis7-compatible EVAL, not Redis8-only conditional commands. Cache key prefix hcl:cache:v1:{business_database}:product:{id}, with :value/:generation/:lease. All IDs bounded to1000; generation keys persist (max2000 across two allowedDBs) to avoid ABA reset, values expire, leases expire. No scans/KEYS/FLUSH.

Lookup reads generation/value together. Validated cached entry must match generation, database and productID. Missing/corrupt value is not a product. Positive values only; absent product404 remains uncached. On miss, atomically acquire random-token lease and generation, then double-check lookup. Owner reads guarded MySQL and publishes only if currentgeneration AND lease token match, atomically; then releases lease. Invalidation atomically advancesgeneration and deletesvalue/lease. Token-checked release cannot delete another owner's lease. Lease expiry or invalidation rejects stale publishing. Waiters poll within250ms; on wait expiry readMySQL without unleasedfill. Redis failures skip subsequent cache commands and fall back. Cancelled owner releases ifpossible, otherwiseleaseTTL recovers; no in-process lock as cross-process guarantee.

TTL jitter reduces synchronizedexpiry but cannot prevent avalanche, penetration or fallback overload. Product writes outside006; cache remains eventually consistent withinTTL and explicitinvalidation semantics, not strongconsistency. Nil lookup is only observedmiss; expiry is demonstrated by waiting beyond an actualPTTL snapshot, not fabricated keyspaceevent.

## Project Structure and responsibilities
- schemas/observations.py shares timestamp validation used by benchmarks and cache; schemas/cache.py: CacheEntry, CacheObservation, CacheResponse, bounded read parameters; preserve BusinessTrace model.
- cache/products.py: fixed key construction, bounded instrumented Redis operations and atomic Lua scripts; no SQL/HTTP.
- services/product_cache.py: Cache-Aside/coordination/fallback workflow, delegates guardedSQL to BusinessService; independent request observation.
- api/routes/product_cache.py: typed read/state/invalidate endpoints under existing business middleware/error envelope.
- observability/recording.py: add definitions for Redis command and coordination/fence observations; no invented server-only timings.
- frontend types/cache.ts, api/cache.ts, composables/useCacheLab.ts, views/CacheLabView.vue; extendBusinessTracePanel labels/commandparameter inspector and navigation; revise stale global cache-unimplemented teaching labels in StorageLearning/architectureAPI and the App READ ONLY tag. Actual requests only, no animated fake cache flow. Bounded sequence history shows sampled hit-rate/coverage, guardSQL vs productSQL, RTT/header/trace boundaries and selected-keyTTL/memory.
- scripts/verify_cache_lab.py: bounded actual bypass/cold/hot/expiry/invalidate/concurrent runs, exclusive rawresponseJSON/report, source/environment/time/units/limitations; no userSQL or reset. Namespace-local invalidation is explicit experiment setup.
- tests/unit/test_product_cache.py; tests/integration/test_product_cache.py; frontend/tests/cacheLab.test.ts; frontend/e2e/cacheLab.spec.ts. CI enables cacheintegration besidebusiness tests; normal CI does not run heavy load.
- docs/architecture/decisions/0004-product-cache.md, docs/guides/cache-lab.md, docs/experiments/006-redis-cache-aside/, README/AGENTS/architecture.

## API and observability
GET /api/v1/business/cache/products/{id}?mode=cache|bypass&ttl_seconds=5 returns product/cache/trace. GET .../{id}/state samples selectedkeyTTL/memory/generation without loading data. DELETE .../{id} explicitly invalidates only that product. All IDs1..1000; invalid422, missingproduct404, disabledbusiness503 use existing safeerror trace. Redisfailure inspection returns unavailable/nulls; read falls back with reason. No arbitrarykeys/Rediscommands/endpoints to mutateMySQL.

Rediscommand spans carry fixed commandname and key-only parameters (never SQL field/valuecredentials); client execute interval includes network/driver. Cache outcomes hit/coalesced/miss/bypass/degraded, fillpublished and safe reasons, observed_at/source. Pool snapshots only if a DBread actuallyoccurs. UI sampledhitratio counts initial_lookup=hit divided by initial hit+miss; coalesced waiters keep initial_lookup=miss and served_from=redis. Report failures/unknown/degraded coverage and exclude bypass/inspection/invalidation. ProductSQL count identifies fixedlab_product statement; ownershipSQL separate; never multiplyexpectedquerycounts. MEMORYUSAGE is selectedvaluekey bytes, not entireRedisprocessmemory. TTL -2absent/-1noexpiry/nullunavailable distinct.

## Validation strategy
Tests first for keybounds/entryidentity/fallbackAPI. Real integration uses only business_test database namespace, noFLUSH or tablescleanup. Verify hitnoSQL, TTLexpires, invalidate/refill, corruptentry recovery, concurrentcoldreadsameproduct and leases released/expired, staleowner cannotpublish afterinvalidate orleaseexpired/reacquired, wrongtokenreleasepreservesnewlease, realunreachableRedisfallsback thenrecover. Use precise expected invariants, not only200. Actual CLI records before/after series andconcurrency counts; no performancefabrication. Frontend mocks proveviewrules only; realPlaywright verifiesmiss/hit/noSQL/invalidate/keyPTTL. Full relatedgates and review/Converge precede protectedPRmerge.
