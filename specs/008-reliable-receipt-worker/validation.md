# Worker validation

Specify/Plan/Tasks/readonlyAnalyze completed before source. Analyze:8/8FR and5/5SC mapped; no critical/high inconsistencies, no unresolved clarifications. ADR0006 predates implementation. Constitution2.0.0 unchanged, no hooks.

Implementation evidence is being completed. Local first gates:75 unit passed, mypy69source files, Ruff/format;19 real task+inventory cases passed;33 Vue unit cases and one actual Edge task E2E passed. Final regression/acceptance/remote CI remain pending; no remote pass claimed here.

## Final local validation and review

Actual acceptance: docs/experiments/008-reliable-receipt-worker/runs/worker-20261025T093041-533b5339/result.json complete=true,32.664s,23HTTP,5owned processes;source13ed68b clean and unchanged. Fail-first retry, two real deadline timeouts/retained failure, linked successor, actualexit70 and restarted lease recovery all observed. Crash finish/duration remainnull. Report preserves units/boundaries/controlled inputs and no capacity claims.

Final local gates: uv sync --frozen; Ruff/format225files; mypy69src;76unit; fullintegration37passed/4oldoptinskipped; final adapter9taskintegrationpassed; Vue35unit; frontendtype/lint/format/build;11fullEdgeE2E then1finaltaskE2E;002evidence10000/100000/1000000accepted. No historical JSON/CSV/PNG edits retained.

Code review: inspected resource disposal, inventory RR regression, RC Task→Outbox ordering, DBUTC fencing at final mutation, receipt current-read uniqueness, unknown commit/ACK handling, retry limits/last-crash exhaustion, boundRedis7 commands, exactscope/subprocess cleanup and UI intent/context/null semantics. Fixed non-atomic XADD/TTL setup using MULTI/EXEC; both group setup and publication atomically apply expiry. Fixed UI response fixture types and consistent controls; actual relevant tests rerun. No unresolved actionable correctness/security findings. No new dependency/framework, no `.env` or credentials tracked.

Protected PR and remote required checks remain open until executed. T017 is publication workflow work, not hidden implementation completion.

ConvergenceT018 completed: actual cancellation leaves pending+committed running lease without false completion, recovery abandons old attempt with unknown timing and succeeds. Actual failure afterTask+OutboxINSERT rolls back both; sameUUID can subsequently create. Final task suite11passed25.20s;no source change from measured checkpoint. Second Converge found0buildable gaps; publicationT017 remains open.
