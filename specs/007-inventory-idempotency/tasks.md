# Tasks: Transactional Inventory and Idempotency
**Input**: spec/plan/research/data-model/contracts/quickstart. Testsrequiredbyuser.
## Phase 1: Setup
- [X] T001 Record accepted transaction/lock/idempotency/unknowncommit decisions in docs/architecture/decisions/0005-inventory.md; add defaultoffwriteconfig/exampleflag (FR-001/004/006).
## Phase 2: Foundation
- [X] T002 Write tests/unit/test_inventory.py forcanonicalfingerprint/state/audit/bounds/drivercodes/writegate beforeimplementation (FR-002/003/004/006).
- [X] T003 Add domain/inventory.py, models/inventory.py, schemas/inventory.py and migrations/versions/0004_inventory_orders.py withFK/CHECK/unique/exactmoney; registermetadata (FR-001/002/003/006).
- [X] T004 Add safe experiments/business_schema.py explicitownedDBupgrade0004; preservebusiness_dataset0003and002runners; central db/business.py observedDMLaffectedrows/insertID (FR-002/005/006).
## Phase 3: US1 Atomic stock and orders
- [X] T005 [US1] Implement repositories/inventory_repository.py fixedSQL/conditionalupdate/currentrowlocks and services/inventory_service.py explicitfreshSessiontransactions/budgets/uniformScenario→Order order; api/routes/inventory.py CRUD/query/audit/writegate andsafeHTTPmapping (FR-001/002/004/005).
- [X] T006 [US1] Create real tests/integration/test_inventory.py foractualmigrations/constraints/FKs/price/commit/insufficientstockrollback/freshscenarios/distinctkeyconcurrency/audit (FR-001/002/006; SC001).
## Phase 4: US2 Idempotency and state conflicts
- [X] T007 [US2] Implement uniquekey/fingerprintreplaywith1062rollbackfreshtransaction, idempotentscenariocreate, reserved→paid/cancelled/no-op andinvalidcrossfinaltransition; noavailabilitycheckbeforeduplicateINSERT (FR-003/004).
- [X] T008 [US2] Verify real matching/mismatchedkeyconcurrency, soldoutreplay, pay/cancelrace, actual1205/1213rollback/recovery andcancelledtransaction in tests/integration/test_inventory.py; neverdependonvictimchoiceorHTTP200alone (FR-002/003/004/006; SC002).
## Phase 5: US3 Actual learning and evidence
- [X] T009 [US3] Write frontend/tests/inventoryLab.test.ts forsharedobservedPOSTJSON/oldGETDELETEcompatibility, stableintent/keyretry, explicitnewkey, no stale success, audit/transitionfeedback; implement types/observed.ts andapi/observed.ts withbackwardsbusinessAPIcompatibility (FR-003/005/006).
- [X] T010 [US3] Add types/inventory.ts/api/inventory.ts/composables/useInventoryLab.ts/views/InventoryLabView.vue/nav/router and BusinessTracePanel transaction/DMLaffectedrowlabels; bounded saved-intent client contest with unique-order counts and real frontend/e2e/inventoryLab.spec.ts create/replay/conflict/cancel/no-op/paidreject/audit (FR-005/006; SC003).
- [X] T011 [US3] Add scripts/verify_inventory_lab.py boundedactualfreshscenario/contest/replay/state/audit withuniqueoutputs andnoreset; executeandsave docs/experiments/007-inventory-idempotency/actualrawresults/report (FR-007; SC001-003).
## Phase 6: Validation and publication
- [X] T012 Add explicitmigration/inventoryintegration/writeenabledE2EtoexistingCI; update README/AGENTS/architecture/databaseER/guides/inventory-lab.md, commands/results/limits (FR-006/007).
- [X] T013 Run allrelatedRuff/format/mypy/unit/realintegration/concurrency/frontend/build/E2Egates,reviewandfixfindings,record specs/007-inventory-idempotency/validation.md; ConvergeallFR/SC/tasks/plan/constitution (FR-006/007; SC004).
- [X] T014 PublishindependentPR,verifyrequiredCIthenmergeandupdatemainbefore008 (FR-007; SC004).
## Dependencies and execution
T001→T002→T003→T004→T005→T006→T007→T008→T009→T010→T011→T012→T013→T014. CoreAPI/auditworkswithoutUI; idempotency/lockingtestsindependentfrombrowser; frontendonlyexplainsprovenpersistedbehavior. OfficialPlanresearchparallelreadonly; implementationsequential. ActualexperimentsneverparallelDBtests/builds. Singlejourneycompletionisnotendofauthorizedscope.
