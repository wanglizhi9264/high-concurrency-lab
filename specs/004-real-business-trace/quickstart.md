# Quickstart validation
uv sync --frozen; docker compose up -d --wait; uv run python scripts/provision_business_lab.py
uv run python -m concurrency_lab.experiments.business_dataset --database concurrency_lab_business init
uv run python -m concurrency_lab.experiments.business_dataset --database concurrency_lab_business seed --orders 10000
Enable BUSINESS_ENABLED=true and BUSINESS_DATABASE=concurrency_lab_business locally; start uvicorn18002/Vite5173; open /business. Query product1/user500/order1; inspect exact SQL/trace/header/decimal. Try missingentity andinvalidcursor.
CI uses concurrency_lab_business_test and BUSINESS_INTEGRATION=1. Run scripts/verify.py, tests/integration and frontend check/test/build/test:e2e. No reset; readyseed retained, loading refused.
