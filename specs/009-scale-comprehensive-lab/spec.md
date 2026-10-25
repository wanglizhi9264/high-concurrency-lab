# Feature Specification: Scale and Comprehensive Experiments
**Branch**:feature/009-scale-comprehensive-lab
**Created**:2026-10-25
**Status**:Ready
**Input**:Feature009 large-data/index/covering/deep-page/bulk-write/statistics/partition/sharding evaluation, final end-to-end and clean-clone acceptance; preserve001–008 and all historical evidence.

## User Scenarios & Testing
### US1 — Reproduce bounded larger datasets (Priority:P1)
A learner explicitly provisions an owned experiment database and streams reproducible data without exhausting application memory or modifying prior experiments. Ordinary startup requires no million-row load; ten-million is explicit opt-in.
**Independent test**: isolated small real dataset has exact count/digest independent of batch size; nonempty/foreign targets are refused and partial failures retained.
**Acceptance**: fixed-seed generation supports10000/100000/1000000 and explicit10000000 extension; inserts use bounded batch transactions, record generation/write times and configuration; no reset, broad delete, hidden startupDDL or arbitrary target.

### US2 — Measure index/partition tradeoffs (Priority:P1)
A learner compares a real baseline, composite and covering index, stable deep OFFSET/keyset, bulk-write cost, large-table statistics, and partition pruning versus unpartitioned storage. They see actual query plans/rows and space/write costs rather than assuming more indexes or partitioning is faster.
**Independent test**: real equal-data layouts/phases produce equivalent query results, retained baseline-first evidence, EXPLAIN ANALYZE and actual partition selection; conditional claims follow the measured results.
**Acceptance**:
1. Primary-key/control, user/time/projection, deep-page and time-range cases have fixed SQL/parameters, warmup/repetition counts and stable ordering, real plans and raw client timings. Known cursor page matches OFFSET; locating a random cursor is separately measured.
2. Compare appropriate composite versus covering indexes with plans proving the selected access path, not a label inferred from an index name. Record per-table/index statistics, approximate allocation semantics and measured bulk-write differences; retain unfavorable samples and errors.
3. Partition comparison records actual selected partitions for both pruning-compatible and incompatible predicates, equal logical data/result checks and schema limitations. Do not claim partitioning speeds all queries or introduce sharding on row-count alone.
4. Execute a small smoke and million-order formal experiment; ten-million supported but optional. Capture real environment/version/source/window/RPS-or-serial-query-rate/P50/P95/P99/error/CPU/memory/connections with explicit units/scopes/unknowns and no concurrent unrelated measured workloads.

### US3 — Inspect recorded comparisons (Priority:P2)
Vue presents trusted immutable009results beside earlier experiments, source SQL/parameters/plans, data identity, sampling boundaries, write/space/partition tradeoffs and unknown/error states. No API executes user SQL or launches heavy work.
**Independent test**: API/UI agree with recorded JSON, reject unsafe paths/invalid evidence, and distinguish measured results from simulation; changing selection cannot show stale evidence.
**Acceptance**: bounded read-only catalogue/details, actual comparison page with source links, raw observations and clear limits; preserve all existing visual/business/cache/inventory/worker pages and normal CI.

### US4 — Reproduce the full system from clean clone (Priority:P1)
A learner follows exact commands from a clean clone to install/start isolated dependencies, initialize safe data, run real APIs/Trace, index experiment, Locust, pool metrics, cache, inventory and worker, then read a comprehensive report and run all checks.
**Independent test**: actually execute the documented clean-clone path in separately owned resources, record each step's command/outcome/source, leave existing developer databases/volumes untouched.
**Acceptance**: final architecture/call-chain/ER/directory tree and module/source reading order, stage results and limits; reviewed independently branched009PR with actual protectedCI before merge. Final end-to-end shows a real paid order→durable receipt and serial experiments/acceptance, never a synthetic success report.

## Requirements
- **FR-001** MUST implement deterministic bounded streaming generation and explicitly guarded isolated targets; support four scales, ten-million opt-in, no destructive reset or previous-data mutation.
- **FR-002** MUST compare real baseline-first single/composite/covering index access, stable OFFSET/keyset and time-range queries with equivalent data/results, exact SQL/parameters, real EXPLAIN ANALYZE and separately recorded cursor-location cost.
- **FR-003** MUST measure bulk-write maintenance and table/index allocation/statistics for comparable layouts, documenting ordering/cache/PK/schema confounders and retaining actual raw samples.
- **FR-004** MUST implement an actual partition experiment with matching unpartitioned data/layout, real partition selection/pruning/non-pruning plans and explicit MySQL constraint/operational limits; evaluate sharding complexity from evidence without adding unnecessary sharding infrastructure.
- **FR-005** MUST preserve raw immutable results, actual environment/source/timing/resource/connection observations and honest scopes/null values; execute smoke and million scale, leave ten-million optional and heavy work outside normalCI.
- **FR-006** MUST add bounded safe read-only result APIs/Vue inspection with genuine SQL/plan/source/units, loading/empty/error/context-change handling and prior page compatibility.
- **FR-007** MUST provide unit/real DB/integration/frontend/E2E/evidence acceptance and retain existing requiredCI; no weakened assertions or fake results.
- **FR-008** MUST actually validate clean-clone installation/start/data/realAPI/Trace/index/Locust/pool/cache/inventory/worker in isolated resources, preserve command outcomes and produce final end-to-end report.
- **FR-009** MUST maintain SpecKit/ADR/schema/architecture/ER/guides/README/AGENTS/review/Converge, independent protectedPR/CI/merge and final source-reading/directory/stage-result handoff.

## Success Criteria
SC001: Exact dataset identities and comparable query results verified in smoke and million-run, old002 data/evidence unchanged.
SC002: Actual plans/partition selection/raw timing/write/resource/space observations support explicit conclusions and limitations, including cases with no benefit.
SC003: Read-only API and UI faithfully explain real records and reject unsafe or invalid evidence.
SC004: Clean-clone end-to-end and related quality/real-integration/browser gates actually execute, with command outcomes and preserved evidence; no unexecuted pass claims.
SC005: Final documentation and protected009merge complete all004–009 scope with no unresolved buildable gaps.

## Edge Cases and Assumptions
Partial generation/DDL/failure retains state; nonempty rerun refuses overwrite; source changes invalidate a measurement; malformed evidence/path traversal/symlinks rejected; resource failure means unknown not zero; approximate index statistics are not file bytes; small repeated warm samples are not production tail latency. Partition constraints may require an analytical copy without business FKs, which must be explicitly documented and compared fairly. Existing002 dataset/JSON and004–008recorded measurements are immutable. No production data, microservices, Kubernetes or automatic shard router. No ordinary startup generation. Current Constitution2.0.0 already authorizes009; no amendment needed.
