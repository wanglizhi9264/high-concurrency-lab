# Research and repository audit
Official Plan read-only backend/frontend research audited existing specs/source/tests; no implementation by researchers.
## Reuse
001 lifespan pools, Settings, Session factory, migrations and health.002 commerce models/indexes, pure order_batches/price/digest and immutable10k/100k/1m evidence.003 trusted evidenceAPI, measured health events, VueFlow/ECharts/AsyncState/playback. Locust installed but no load suite/businessAPI/cache/inventory/Worker.
## Cautious refactors
Extract bounded pure reference_rows from002inline catalog generation without changing values, retaining deterministic tests. Keep business trace separate from health DTO. Default-off business pool preserves old lifecycle assertions. Later005 adds LineChart/own historical-result adapter; don't rewrite002readers or globalstyles.
## Decisions
Fixed owned business DBs because future writes must never mutate002 controls. Existing002CLI/safety/seed enforce baseline revision/purpose and cannot be used for business writes. Reuse existing models/migrations instead of duplicate schema. Each request owns its Session; sequential SQL, explicit JOIN avoids lazyIO/N+1. Stable disjunctive time/id cursor; paired validation; bounded offset. Acquisition includes queue/connect/preping; SQL span includes driver/server/fetch; preparation header and browserRTT are separate. No invented purequeue/server-only timing.
Official references: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html ; https://docs.sqlalchemy.org/en/20/orm/session_basics.html ; https://dev.mysql.com/doc/refman/8.4/en/row-constructor-optimization.html . Unknowns resolved.
## Delivery order and amendment
004reads/trace →005Locust/resources →006cacheaside/expiry/invalidation/concurrency →007inventory/transactions/idempotency →008ADR/durableoutbox/StreamsWorker/recovery →009coverage/partition/writecost/optional10m/comprehensive report. Each has independent SDD/review/PR.
Constitution1.0.0→2.0.0 replaces business prohibition with staged gates per user task. Safety/evidence principles retained; original ratification2026-10-23, amendment2026-10-25.
