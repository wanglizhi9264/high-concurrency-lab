# Quickstart
Initialize004 owned business data first. Run `uv run python scripts/run_load_test.py --users 10 --seconds 15 --pool-size 5 --task-rate 1`.
Output goes to a new ID under docs/experiments/005-real-load-testing/runs: raw CSV/resources/result.json. Repeat10/50/100/500; compare100users/pool1vs5 and pacing1vs2 atpool5. Runner owns temporary API on unused18003 and stops it; preview remains up. Open /load-tests and select two real runs.
NormalCI runs parsers/API/UI tests, not the long matrix. Dedicated workflow_dispatch performs bounded load independently. See final guide for exact commands/limitations.
