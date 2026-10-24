# High Concurrency Lab

用于系统学习高并发、MySQL、Redis、数据库优化、异步任务和后端架构的长期实验工程。
当前已实现 `001-project-foundation` 基础环境与健康API，`002-mysql-index-baseline` 的关系模型、批量数据和索引/分页实验，以及 `003-interactive-system-visualization` 的交互式学习入口。

技术栈：Python 3.11+（开发/CI 3.12）、FastAPI、Pydantic v2、SQLAlchemy 2/asyncmy、Alembic、MySQL 8.4、Redis 7、uv、pytest/httpx、Ruff、mypy、Locust。解析版本以 uv.lock 为准。

## 快速开始

需安装 Git、uv、Docker Desktop（Windows 启用 WSL2）或 Docker Engine + Compose（Linux）。
```powershell
uv python install 3.12
Copy-Item .env.example .env
# 编辑 .env：填写 MYSQL_PASSWORD、MYSQL_ROOT_PASSWORD、REDIS_PASSWORD 三个本地随机密码
uv sync --frozen
docker compose up -d --wait
uv run alembic upgrade head
uv run uvicorn concurrency_lab.main:app --host 127.0.0.1 --port 8000
```
Linux 复制命令为 `cp .env.example .env`。访问 http://127.0.0.1:8000/health/live 和 /health/ready；预期 200。
.env 不提交。默认端口 3306/6379，仅绑定 loopback；端口占用时修改 .env 的 MYSQL_PORT/REDIS_PORT，API 同步读取。本次机器 Redis 使用 16379。

## 迁移和检查
```text
uv run alembic upgrade head
uv run alembic current
uv run alembic downgrade base
uv run alembic upgrade head
uv run alembic revision --autogenerate -m "describe schema change"
uv run pytest tests/unit
uv run pytest tests/integration
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run python scripts/verify.py
```
回滚 base 会删除 lab_marker 表及其中数据，限可丢弃实验数据使用。autogenerate 产物必须审核再升级。集成测试要求 Compose healthy 且迁移为 head，缺少服务会失败；默认 `uv run pytest` 仅运行 unit。

```text
docker compose stop
docker compose start --wait
docker compose down
docker compose up -d --wait
docker build -t high-concurrency-lab:local .
```
down 保留 MySQL volume，down -v 会删除数据。Redis 当前不承诺持久化。
镜像以非 root 用户运行；连接 Compose 时通过 --network high-concurrency-lab_default，传入 --env-file .env 并覆盖 MYSQL_HOST=mysql、REDIS_HOST=redis、MYSQL_PORT=3306、REDIS_PORT=6379。禁止把 localhost 当作其他容器地址。

## 目录
- `.specify/`、`.agents/skills/`：官方 Spec Kit 1.2.3、Codex integration；specs/ 保存当前 feature 规格、计划、任务和证据。
- `src/concurrency_lab/`：main 生命周期；api 路由；core 配置；db Session/engine；cache 客户端；services 探针；models 最小表。
- `migrations/`：Alembic；`tests/unit/`、`tests/integration/`：隔离测试和真实服务测试。
- `docs/architecture/`、`docs/database/`、`docs/experiments/`、`docs/guides/`：设计、ADR、实验模板、操作指南。
- `scripts/`：质量检查；`benchmarks/`：未来负载实验约定；`.github/workflows/`：CI。

## SDD 与后续路线
官方安装：`uv tool install specify-cli==1.2.3`；检查：`specify version`、`specify check`。
本项目通过 `specify init high-concurrency-lab --integration codex --script ps --non-interactive` 初始化。
在 Codex 用 `$speckit-constitution`、`$speckit-specify`、`$speckit-clarify`（必要时）、`$speckit-plan`、`$speckit-tasks`、`$speckit-analyze`、`$speckit-implement`、`$speckit-converge`。这些是 Agent skills，不是 CLI 子命令。Linux 可执行同样的 uv/Compose 命令；官方工作流脚本为 PowerShell，需 pwsh，或新项目初始化时选择 --script sh。

后续独立 Feature 顺序：01 MySQL 索引与 EXPLAIN ANALYZE；02 同步/异步 API 和连接池/Locust；03 Cache-Aside 与一致性；04 并发库存与幂等；05 异步队列/Streams/Worker；06 百万数据、覆盖索引、深分页、分区/分表比较。
每项先保存基线，再做优化；002 已有 SQL 性能实测结果；仍无缓存业务、订单 API、锁或 Worker。

详细设计见 [架构](docs/architecture/overview.md)、[ADR](docs/architecture/decisions/0001-foundation.md)、[数据库](docs/database/design.md)、[开发指南](docs/guides/local-development.md)。实际执行结果见 [验收记录](specs/001-project-foundation/validation.md)。

## GitHub 协作流程
稳定默认分支为 `main`。新功能和修复从最新 main 创建分支，完成后通过 Pull Request 合并；不直接在 main 开发。
```text
git switch main
git pull --ff-only
git switch -c feature/002-mysql-index-baseline
# 先更新 SDD 规格和计划，再实施与验证
git push -u origin feature/002-mysql-index-baseline
gh pr create --base main
```
PR 需附规格、变更说明和实际测试结果，quality 与 integration 通过后再合并。合并后删除已完成的功能分支。

## 002: MySQL 索引基线实验
已实现用于实验的用户、商品、订单及明细表、两阶段 Alembic迁移、确定性分批造数和 SQL计划/分页测量，无新增订单 API。
独立 MySQL 实验实例默认端口13306；详见 [实验命令与ER图](docs/experiments/002-mysql-index-baseline/README.md)、[DBeaver教程](docs/experiments/002-mysql-index-baseline/dbeaver.md)、[实测报告](docs/experiments/002-mysql-index-baseline/report.md)。
已提交结果只能读取，新实验指定新 output-dir；已有数据库不会被自动清空。执行 `uv run python scripts/verify_index_lab.py --verify-only` 校验仓库内证据。

## 003：交互式系统实验台
新增 frontend/ Vue3+TS界面：系统全景图、真实/模拟请求回放、002数据/计划对照、连接池教学模拟和实验笔记。后端只读API及最小健康埋点，无业务API或数据库Schema变化。
```powershell
# 仓库根目录，先确保本地.env有效
uv sync --frozen
docker compose up -d --wait
uv run uvicorn concurrency_lab.main:app --host 127.0.0.1 --port 18002
# 另开终端进入frontend目录
npm ci
npm run dev -- --host 127.0.0.1 --port 5173
```
打开 http://127.0.0.1:5173/ 。完整[页面/API/可信观测边界/模拟规则/测试指南](docs/guides/visualization-platform.md)。前端执行 npm run check、npm run test、npm run build；真实端到端npm run test:e2e（需浏览器和基础MySQL/Redis健康）。
仅本地开发，不进行生产部署；002展示直接读取历史JSON，不会重新生成百万数据。Live Trace只报告实测区间，Simulation不是实际MySQL性能。
