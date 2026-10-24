FROM ghcr.io/astral-sh/uv:0.12.5 AS uv
FROM python:3.12-slim
COPY --from=uv /uv /uvx /bin/
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy CONCURRENCY_LAB_ROOT=/app
COPY pyproject.toml uv.lock ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable
COPY alembic.ini ./
COPY migrations ./migrations
COPY docs/experiments/002-mysql-index-baseline/runs ./docs/experiments/002-mysql-index-baseline/runs
RUN useradd --create-home app
USER app
EXPOSE 8000
CMD ["/app/.venv/bin/uvicorn", "concurrency_lab.main:app", "--host", "0.0.0.0", "--port", "8000"]
