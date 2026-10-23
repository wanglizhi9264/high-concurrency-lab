# Quickstart validation
1. Copy .env.example to .env，填写三个本地密码。
2. uv sync --frozen；docker compose up -d --wait。
3. uv run alembic upgrade head；uv run alembic downgrade base；uv run alembic upgrade head。
4. uv run uvicorn concurrency_lab.main:app --host 127.0.0.1。
5. GET /health/live、/health/ready，按 contracts/health.md 校验。
6. uv run pytest tests/unit；uv run pytest tests/integration；uv run ruff check .；uv run mypy src。
7. 单独 stop redis/mysql，ready 应为 503，live 200；start 并等待健康后 ready 恢复。
8. docker compose down 后 up -d --wait，迁移版本应保持 head。不要使用 down -v，除非明确要删除实验数据。
