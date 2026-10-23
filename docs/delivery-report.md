# 交付报告：001-project-foundation

项目位置：D:/Digital_Life/02_Projects/03_HOU/high-concurrency-lab。
分支：001-project-foundation；已初始化本地 Git，无提交/推送。

## Spec Kit
官方 specify-cli 1.2.3，Codex integration，PowerShell 脚本，官方模板及技能保留。
Constitution 1.0.0 -> Specify -> Clarify（无重大歧义，跳过）-> Plan -> Tasks -> Analyze -> Implement -> Converge。
详见 specs/001-project-foundation/。12 项任务已完成。

## 架构及文件映射
- T001-003：pyproject.toml、uv.lock、src/concurrency_lab/{core/config.py,db/session.py,cache/client.py}：配置、异步池、Session DI。
- T004-006：compose.yaml、Dockerfile、main.py、api/routes/health.py、services/health.py：环境、lifespan、健康探针。
- T007-008：tests/integration/、migrations/、models/marker.py：真实连接、最小迁移。
- T009-010：.github/workflows/ci.yml、scripts/verify.py、README、docs/：质量门禁与文档。
- T011-012：scripts/acceptance_local.py、specs/001-project-foundation/validation.md、tasks.md：实际验收和收敛。
选择模块化单体降低部署复杂度；FastAPI 支持 ASGI/lifespan；SQLAlchemy+asyncmy 保持异步 I/O 和显式事务；Compose 统一真实依赖；Alembic 记录 Schema 演进。详细比较见 ADR-0001。

## 本地启动
当前 .env 已创建并含本地随机密码（已忽略），无需覆盖。Redis 本机端口为 16379。
```powershell
cd D:\Digital_Life\02_Projects\03_HOU\high-concurrency-lab
uv sync --frozen
docker compose up -d --wait
uv run alembic upgrade head
uv run uvicorn concurrency_lab.main:app --host 127.0.0.1 --port 8000
```
当前验收进程运行在 http://127.0.0.1:18000/health/ready；MySQL/Redis healthy。
新克隆从 .env.example 复制并填写本地密码，详见 README。

## 执行结果
- uv sync --frozen：成功。
- uv run python scripts/verify.py：Ruff、format、mypy 15 源文件、11 项单元测试通过。
- uv run pytest tests/integration -q：3 项通过。
- uv run alembic upgrade head / downgrade base / upgrade head：成功；alembic check 无差异。
- uv run python scripts/acceptance_local.py：实际 HTTP 200、Redis 故障 503、MySQL 故障 503、live 始终 200、恢复后 200；重建容器后迁移 head 保留。
- docker build -t high-concurrency-lab:local .：成功；容器实际 HTTP readiness 200。
- .env ignore 和本地密码值扫描：通过。
完整环境、镜像 digest、修复过的失败及限制见 validation.md。无性能实验或虚构指标。

## 限制与后续
远端 CI 未触发（未发布仓库），Python 3.11 与完整 Linux 宿主指南未单独执行。上游 Starlette TestClient 有一条 httpx 弃用警告，测试通过。
Converge：9 FR、5 SC、11 原则及计划/12 tasks 均复核，无可操作缺口，tasks.md 未追加空收敛阶段。
建议下一 Feature：002-mysql-index-baseline，确定性数据生成、索引对照、EXPLAIN ANALYZE 和原始结果归档。

## 最终目录树
见下方（不含 .git、.venv、缓存、忽略的本地密码/日志）。

```text
high-concurrency-lab/
├── .agents/
│   └── skills/
│       ├── speckit-analyze/
│       │   └── SKILL.md
│       ├── speckit-checklist/
│       │   └── SKILL.md
│       ├── speckit-clarify/
│       │   └── SKILL.md
│       ├── speckit-constitution/
│       │   └── SKILL.md
│       ├── speckit-converge/
│       │   └── SKILL.md
│       ├── speckit-implement/
│       │   └── SKILL.md
│       ├── speckit-plan/
│       │   └── SKILL.md
│       ├── speckit-specify/
│       │   └── SKILL.md
│       ├── speckit-tasks/
│       │   └── SKILL.md
│       └── speckit-taskstoissues/
│           └── SKILL.md
├── .dockerignore
├── .env.example
├── .github/
│   └── workflows/
│       └── ci.yml
├── .gitignore
├── .python-version
├── .specify/
│   ├── .gitignore
│   ├── init-options.json
│   ├── integration.json
│   ├── integrations/
│   │   ├── codex.manifest.json
│   │   └── speckit.manifest.json
│   ├── memory/
│   │   ├── .constitution-template.json
│   │   └── constitution.md
│   ├── scripts/
│   │   └── powershell/
│   │       ├── check-prerequisites.ps1
│   │       ├── common.ps1
│   │       ├── create-new-feature.ps1
│   │       ├── resolve-template.ps1
│   │       ├── setup-plan.ps1
│   │       └── setup-tasks.ps1
│   ├── templates/
│   │   ├── checklist-template.md
│   │   ├── constitution-template.md
│   │   ├── plan-template.md
│   │   ├── spec-template.md
│   │   └── tasks-template.md
│   └── workflows/
│       ├── speckit/
│       │   └── workflow.yml
│       └── workflow-registry.json
├── AGENTS.md
├── Dockerfile
├── README.md
├── alembic.ini
├── benchmarks/
│   └── README.md
├── compose.yaml
├── docs/
│   ├── architecture/
│   │   ├── decisions/
│   │   │   └── 0001-foundation.md
│   │   └── overview.md
│   ├── database/
│   │   └── design.md
│   ├── delivery-report.md
│   ├── experiments/
│   │   └── template.md
│   └── guides/
│       └── local-development.md
├── migrations/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0001_lab_marker.py
├── pyproject.toml
├── scripts/
│   ├── acceptance_local.py
│   └── verify.py
├── specs/
│   └── 001-project-foundation/
│       ├── analysis.md
│       ├── checklists/
│       │   └── requirements.md
│       ├── contracts/
│       │   └── health.md
│       ├── data-model.md
│       ├── plan.md
│       ├── quickstart.md
│       ├── research.md
│       ├── spec.md
│       ├── tasks.md
│       └── validation.md
├── src/
│   └── concurrency_lab/
│       ├── __init__.py
│       ├── api/
│       │   ├── __init__.py
│       │   └── routes/
│       │       ├── __init__.py
│       │       └── health.py
│       ├── cache/
│       │   ├── __init__.py
│       │   └── client.py
│       ├── core/
│       │   ├── __init__.py
│       │   └── config.py
│       ├── db/
│       │   ├── __init__.py
│       │   └── session.py
│       ├── main.py
│       ├── models/
│       │   ├── __init__.py
│       │   └── marker.py
│       └── services/
│           ├── __init__.py
│           └── health.py
├── tests/
│   ├── integration/
│   │   ├── test_api.py
│   │   ├── test_mysql.py
│   │   └── test_redis.py
│   └── unit/
│       ├── test_config.py
│       └── test_health.py
└── uv.lock
```
