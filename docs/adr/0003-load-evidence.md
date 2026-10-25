# ADR 0003: Independent Locust process and immutable measured records

Status: accepted, 2026-10-25, Feature005.

Locust/gevent runs only in a child process. The runner owns an independent single-worker API, configured business pool and cleanup. Existing preview processes are untouched. Each run uses an unused loopback port and the existing owned business dataset; ownership is verified by every business request. No data is reset.

Preserve original Locust CSV and independently record call starts and HTTP completions. Exact overall percentiles use raw response times including failures. Locust histogram percentiles and rolling history retain their original semantics. Closed-loop pacing is not an open arrival guarantee. Client invocation is not server arrival. Unfinished calls remain visible separately from completed-request error rate.

Record monotonic duration and UTC boundaries. Reject a clock discontinuity exceeding 250ms rather than silently misbin observations. Retain incomplete raw runs without publishing result.json. Hash canonical workload sources before/after; refuse publication if they change. Git revision and dirty state accompany the hash.

psutil is a direct development dependency for owned-process CPU/RSS. CPU is unknown until every observed member has a baseline. Docker CLI supplies separate Linux VM/container observations and rounded memory estimates. Live monitoring uses the existing shared business pool, competing with workload; MySQL global counters include monitoring and unrelated instance activity. No metric substitutes zero for unavailable data.

A bounded, schema-validated readonly catalogue serves recorded evidence. HTTP cannot start a benchmark or choose arbitrary paths/SQL. Normal CI does not assert machine-dependent performance thresholds. A separate workflow_dispatch job produces downloadable raw artifacts on a disposable database.
