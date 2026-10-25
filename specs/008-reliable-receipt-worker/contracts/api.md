# Contracts
POST /api/v1/business/tasks {task_id:UUID,order_id:positive,max_attempts:1..5,fault_plan:null|controlledconfig};201new/200matchingreplay/409mismatch or notpaid. Task+Outbox commit even when Redis down.
GET /api/v1/business/tasks?scenario_id=UUID&limit=1..20; bounded persisted task summaries.
GET /api/v1/business/tasks/{uuid}; task/outbox/attempts/events/receipt and safe CLI command.
POST /api/v1/business/tasks/{uuid}/retry {task_id:newUUID,disable_faults:true}; original must be failed, creates linked successor idempotently and retains original.
GET /api/v1/business/task-queues/{scenario}; validates owned scope, independent DB counts/Redis snapshot; unavailable Redis remains null, not zero.
Writes require existing opt-in; inputs422, absent404, mismatch/state409, pool503, requestbudget504 with outcome-unknown guidance. No arbitrary handler/key/script/host or process-start HTTP.
CLI: uv run python -m concurrency_lab.workers.receipts --database <fixedbusinessDB> --scenario <confirmedUUID> [--role both|dispatcher|consumer] [--once|--max-cyclesN] [bounded timeout/lease] [explicit --crash-after-claim probe]. Handler effect is durable DB receipt only.
Frontend /tasks preserves saved task/successor intent and exact payload; manual GET refreshes actual state, queue snapshot separate; no client timer changes server state. Task event/attempt models are not HTTP trace. Fault input label distinct from measured outcomes.
