# Tasks: Real Load Testing
User explicitly requires tests and real evidence; spec/plan/research/contracts are prerequisites.
## Phase1 Setup
- [X] T001 Declare psutil dev usage, document isolated generator/metric scopes in docs/architecture/decisions/0003-load-evidence.md and benchmarks/README.md (FR-002/003).
## Phase2 Foundation
- [X] T002 Write safety/CSV/percentile/missing/time-order/result-guard tests in tests/unit/test_load_testing.py before implementation (FR-002/003/004).
- [X] T003 Add schemas/benchmarks.py and experiments/load_recording.py with typed finite/time-ordered evidence and pure exact aggregation (FR-002/003).
## Phase3 US1 Actual workloads
- [X] T004 [US1] Add fixed global order paging and actual shared business monitor via repository/service/API; test integration ownership/bounds/metadata in tests/integration/test_business.py (FR-001/003).
- [X] T005 [US1] Implement benchmarks/locust/locustfile.py and scripts/run_load_test.py with users10/50/100/500, seconds5..300, task-rate0.2..5, bounded spawn/pool, owned-child cleanup and exclusive outputs (FR-001/002).
- [X] T006 [US1] Run actual matrix plus controlled pool/pacing pairs, save CSV/resources/manifest/result under docs/experiments/005-real-load-testing/runs and analyze without capacity promises (FR-005; SC001/002).
## Phase4 US2 Inspect records
- [X] T007 [US2] Add bounded ID/containment/size/schema reader and readonly list/detail in services/benchmarks.py and api/routes/benchmarks.py; no run endpoint (FR-004).
- [X] T008 [US2] Test and implement types/benchmarks.ts, api/benchmarks.ts, LoadTestView.vue, LineChart/aria support and two-run safe comparison with null gaps (FR-004; SC003).
## Phase5 US3 Reproduce and maintain
- [X] T009 [US3] Add manual performance workflow, ordinary parser/API/frontend/real-record E2E regression; runbook/docs/limits, preserve existing CI (FR-006).
## Phase6 Validation
- [X] T010 Run related gates, record actual tests/review/metric definitions/results, fix findings, Converge against allFR/SC/tasks and publish separate PR; merge only after required CI, update main before006 (FR-006; SC004).
## Dependencies and strategy
T001→T002→T003→T004→T005→T006→T007→T008→T009→T010. US1 CLI works withoutUI; US2 inspects real data independently; US3 gates follow both. Pure tests can be authored independently, but benchmark runs never parallelize to avoid interference. Official research ran in parallel read-only; implementation sequential. No stage stops at documentation.
