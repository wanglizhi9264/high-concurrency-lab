# Tasks: Real Business Request Trace
Input spec/plan/research/data-model/contracts; user requires tests and real acceptance.
## Phase1 Setup
- [X] T001 Record constitution amendment/audit and safe business boundaries in docs/architecture/decisions/0002-business-lab.md (FR-002/007).
## Phase2 Foundational
- [X] T002 Write allowlist/config/span/paging/error tests in tests/unit/test_business.py, confirm initial failure (FR-002/003/004).
- [X] T003 Add opt-in typed config and resource lifecycle in core/config.py, db/business.py, main.py; literal two DB names, budget>0 (FR-002/003).
- [X] T004 Implement schemas/business.py, observability/recording.py and http.py with real metric definitions/correlation/logging and explicit safe error taxonomy in core/exceptions.py (FR-004).
- [X] T005 Extract pure reference_rows in experiments/dataset.py with deterministic regression; add non-destructive business init/seed/provision in experiments/business_dataset.py and scripts/provision_business_lab.py (FR-002).
## Phase3 US1 Real reads
- [X] T006 [US1] Add exact-record/Decimal/stable-pagination/fixed-query-count cases in tests/integration/test_business.py before APIs (FR-001/006).
- [X] T007 [US1] Implement fixed parameterized ProductRepository and OrderRepository in repositories/product_repository.py and order_repository.py; detailJOIN, noN+1 (FR-001/003).
- [X] T008 [US1] Implement own Session/transaction/ownership workflow in services/business_service.py and DI/routing/error mapping in api/routes/business.py; limit1..100/offset0..100000/pairedcursor/positiveBIGINT (FR-001/003).
## Phase4 US2 Actual observation and failure
- [X] T009 [US2] Add real pool-capacity/timeout/concurrent-session/recovery tests in tests/integration/test_business.py and unit redaction/exception tests in tests/unit/test_business.py (FR-004/006).
- [X] T010 [US2] Complete measured SQL/acquire/service spans, before/after gauges, source/definition/UTC/evidence in db/business.py and services/business_service.py (FR-004).
## Phase5 US3 Reproduce and inspect
- [X] T011 [US3] Write frontend/tests/business.test.ts and e2e/business.spec.ts for real queries, errors, exact paths, selection and stable pages (FR-005/006).
- [X] T012 [US3] Add api/business.ts, types/business.ts, useBusinessQuery.ts, BusinessTracePanel.vue, BusinessQueryView.vue and App/router entry with load/empty/error/retry handling (FR-005).
- [X] T013 [US3] Add isolated-business integration and browser stages to .github/workflows/ci.yml; preserve existing gates and add runbook in docs/guides/business-lab.md (FR-006/007).
## Phase6 Validation and polish
- [X] T014 Run full related local gates and independent DB/browser acceptance, record real evidence/screenshots in docs/experiments/004-real-business-trace/ and specs/004-real-business-trace/validation.md (FR-006/007; SC001-004).
- [X] T015 Review layer boundaries/concurrency/errors/safety, fix findings with regression tests, Converge against all FR/SC/tasks; update README/AGENTS/architecture/database docs (FR-007).
- [ ] T016 Publish separate PR, verify required CI/review and merge; update local main before005 (FR-007).
## Dependencies and execution
T001→T002→T003/T004→T005→T006→T007→T008→T009→T010→T011→T012→T013→T014→T015→T016. US1 testable by HTTP real DB withoutUI; US2 independent failure/resource tests; US3 real-browser scenario afterUS1. Tests precede code. Research was parallel read-only; implementation remains sequential. Different test files could be prepared in parallel, but no delegated implementation needed. MVP is real read+safe trace, not a stopping point for requested scope.

## Phase7: Convergence
- [X] T017 Correct business422 to the specified safe data/error/trace envelope with validation event in api/routes/business.py and main.py; preserve other routes'422 contract; add unit/integration/browser error regressions per FR-004/005 (contradicts). HIGH F1. DependsT015; verify noSQL on invalidparameters and requestID consistency.
