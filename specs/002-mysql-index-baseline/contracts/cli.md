# CLI contract
`python -m concurrency_lab.experiments.index_baseline --database NAME init|seed|measure|optimize`
Global config EXP_MYSQL_HOST (127.0.0.1), EXP_MYSQL_PORT (13306), EXP_MYSQL_USER (lab_exp), EXP_MYSQL_PASSWORD (fallback MYSQL_PASSWORD in .env). Database required allowlist; never inherits MYSQL_DATABASE.
- init: only empty DB may migrate to0002; owned baseline DB may be inspected, wrong/nonempty unowned refused.
- seed --orders {10000,100000,1000000} --seed 20261023 --batch-size 1000: empty tables only. test DB permits small count in test API, public CLI only three scales.
- measure --phase baseline|optimized --repeats 7 --output-dir docs/experiments/002-mysql-index-baseline/runs: validates revision/ownership/ready/count and phase; exclusive JSON result creation, no overwrite.
- optimize --output-dir ...: requires matching baseline JSON and revision0002; migration0003.
Outputs exclude credentials/DSN; operational errors printed sanitized, nonzero exit. init/seed/measure/optimize never clear tables or drop databases. Acceptance script runs these steps only on fresh experiment DBs, rejects existing results.
JSON schema version1: dataset identity, phase/revision, environment, generator metadata, tables/indexes estimates, query parameters/sql/actual tree/parsed iterators/timings percentiles/serial throughput/error rate, cursor acquisition cost, comparison page IDs. Resource telemetry uncollected null plus explanation.
