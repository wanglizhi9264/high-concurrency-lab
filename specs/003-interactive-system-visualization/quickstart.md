# Quickstart acceptance
1. uv sync --frozen；docker compose up -d --wait；uv run uvicorn concurrency_lab.main:app --host 127.0.0.1 --port 18002。
2. cd frontend；npm ci；npm run dev -- --host 127.0.0.1；打开打印URL。
3. 首页选择MySQL/Redis节点与源码；生命周期页采集真实请求，检查LiveTrace/200与浏览器roundtrip、回放操作。
4. 数据页百万OFFSET，P50必须等于002源数据414.6824999770615和153.842...；展开树选中TableScan，展示1e6actual rows。
5. 池模拟并发12/容量2/SQL1000ms/timeout1500ms：观察FIFO和超时；真实模式等待指标为未接入。
6. npm run check；npm run test；npm run build；npm run test:e2e（实际真实backend/代理，无mock）；uv run python scripts/verify.py；uv run pytest tests/integration。
7. PR CI通过后合并；截图/具体浏览器验收保存到docs/experiments/003-interactive-system-visualization/。
