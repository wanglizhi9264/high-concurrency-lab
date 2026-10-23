# Quickstart
1. uv sync --frozen; docker compose -f compose.yaml -f compose.experiments.yaml --profile experiments up -d --wait mysql-experiment
2. uv run python scripts/provision_index_lab.py
3. uv run python -m concurrency_lab.experiments.index_baseline --database concurrency_lab_exp_002_10000 init
4. Same prefix seed --orders 10000; measure --phase baseline; optimize; measure --phase optimized
5. uv run python scripts/verify_index_lab.py --orders 100000 1000000 (remaining fresh scales).
6. uv run python scripts/verify.py; uv run pytest tests/integration; EXPERIMENT_INTEGRATION=1 uv run pytest tests/integration/test_index_baseline.py (PowerShell use $env:EXPERIMENT_INTEGRATION='1').
7. Inspect JSON and report plus dbeaver.md. No reset flags: existing DB data/results cause refusal. To repeat choose an entirely new Docker project/volume intentionally and preserve old results externally; never delete a shared DB.
