# Contracts
GET /api/v1/benchmarks lists validated summaries. Empty list normal.
GET /api/v1/benchmarks/{id} returns RecordedLoadRun; safe published ID only,404unknown,503trusted-data invalid. No arbitrary filesystem/SQL/shell arguments.
GET /api/v1/observability/business-metrics returns business pool/settings, owned dataset identity, MySQL version/global status and safe unavailable state. Shared engine, bounded read only.
GET /api/v1/business/orders?limit=20&offset=8000 returns existing BusinessResponse with global timeDESC/idDESC page; same pairedcursor/bounds/headers/errors.
CLI run_load_test.py validates users/duration/spawn/rate/pool/port, unique output directory, loopback child only. Interrupted raw files retained; no overwrite/database mutation.
