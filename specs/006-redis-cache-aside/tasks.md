# Tasks: Redis Cache-Aside Lab
**Input**: spec/plan/research/data-model/contracts/quickstart. Tests explicitly required by user.
## Phase 1: Setup
- [X] T001 Record existing Constitution2.0.0 compatibility and accepted cache policy/limits in docs/architecture/decisions/0004-product-cache.md; no dependency or migration changes (FR-001/002).
## Phase 2: Foundation
- [X] T002 Author unit contracts/keybounds/entryidentity/fallback/error tests in tests/unit/test_product_cache.py before implementation (FR-001/002/005).
- [X] T003 Add schemas/cache.py, cache/products.py fixednamespaces/boundedcommands/atomicgeneration+token scripts; noSQL/HTTP or arbitrarycommands (FR-001/002/003).
## Phase 3: US1 Real cache sequence
- [X] T004 [US1] Add services/product_cache.py around guardedBusinessService, api/routes/product_cache.py and mainrouter, Redis/coordination definitions in observability/recording.py (FR-001/002/003).
- [X] T005 [US1] Implement real isolatedintegration bypass/miss/hit/noSQL, inspectionTTL/memory, actualexpiry, invalidate/refill and missing/corruptentry cases in tests/integration/test_product_cache.py (FR-001/003/005; SC001).
## Phase 4: US2 Competition and failures
- [X] T006 [US2] Verify actual coldreadconcurrency, boundedwait/unleasedfallback, generation+lease fence rejection, tokenrelease safety, cancelledowner recovery, realunreachableRedis fallback and subsequent recovery in tests/integration/test_product_cache.py (FR-002/005; SC002).
## Phase 5: US3 Learning interface and evidence
- [X] T007 [US3] Author frontend/tests/cacheLab.test.ts for samplehitdenominator, source/SQL separation, safeerrors/retry/staleinspection and commandspans; implement types/cache.ts, api/cache.ts, composables/useCacheLab.ts and CacheLabView.vue/navigation (FR-003/004/005; SC003).
- [X] T008 [US3] Extend BusinessTracePanel Rediscommandparameter/source view; update StorageLearning/architectureAPI teachinglabels and App local-mode tag withoutremoving003teaching or004bypass behavior; update relevantregressions and real frontend/e2e/cacheLab.spec.ts (FR-003/004/005).
- [X] T009 [US3] Add scripts/verify_cache_lab.py with bounded realseries/concurrency, uniqueoutput and noreset; executeactual experiment into docs/experiments/006-redis-cache-aside/, record safe rawresponses/source/time/environment/units and comparisons (FR-003/006; SC003).
## Phase 6: Validation and publication
- [X] T010 Extend existingCI isolatedcacheintegration withoutheavyload; update README/AGENTS/architecture/guides/cache-lab.md and actualreport, document consistency/penetration/stampede/avalanche/duplicatefill/degradation limits (FR-005/006).
- [X] T011 Run related Ruff/format/mypy/unit/realintegration/frontend/build/E2E gates, code review and fix findings; record evidence in specs/006-redis-cache-aside/validation.md; Converge allFR/SC/plan/tasks/constitution (FR-005/006; SC001-004).
- [ ] T012 Publish independentPR, verifyprotectedCI thenmerge; update latestmain before007 (FR-006; SC004).
## Dependencies and execution
T001→T002→T003→T004→T005→T006→T007→T008→T009→T010→T011→T012. US1 works byrealAPI withoutUI; US2 verifieshardcases separately; US3 explains provenbehavior. Readonlyresearch mayrunparallel perPlan skill; implementationsequential. No heavybenchmark run alongsideDBtests/builds. Completion ofonejourney isnot a stoppingpoint forauthorized006–009scope.
