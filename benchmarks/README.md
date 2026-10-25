# Benchmarks
Feature005 uses a separate Locust process against an owned, temporary API process and the owned business MySQL database. See [runbook](../docs/guides/load-testing.md). Never import Locust/gevent into FastAPI. Normal CI checks parsers, API and UI; long load is manual only.

Raw client calls and completions, Locust CSV, resource observations and validated result.json are preserved in unique directories. SQL attempt rate is based on returned traces, with unknown coverage disclosed. It is not server QPS. Health probe latency and test execution speed are not throughput evidence.
