# Research
## Decisions
- Decision: async SQLAlchemy + asyncmy。Rationale: 避免 I/O 阻塞事件循环；Alternatives: 同步驱动需线程池，未来实验单独比较。
- Decision: lifespan owns engine/redis。Rationale: 一次创建、明确释放；Alternatives: per-request pools 浪费连接。
- Decision: Alembic async run_sync + NullPool。Rationale: 迁移独立运行；Alternatives: create_all 无迁移历史。
- Decision: 模块化单体、FastAPI、SQLAlchemy、Compose。Rationale: 类型清晰、SQL 可控、依赖易复现；Alternatives: 微服务/K8s 超出教学基础范围。
- Decision: uv 锁定稳定主版本；镜像 MySQL 8.4/Redis 7 标签支持安全更新，精确镜像 digest 在验证记录保存。
## Official sources (checked 2026-10-23)
- https://github.com/github/spec-kit : CLI 1.2.3, Codex skills integration, converge supported。
- https://fastapi.tiangolo.com/advanced/events/ : lifespan。
- https://docs.sqlalchemy.org/en/20/dialects/mysql.html#asyncmy : asyncmy。
- https://docs.sqlalchemy.org/en/20/core/pooling.html : AsyncAdaptedQueuePool。
- https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html : Session per task。
- https://alembic.sqlalchemy.org/en/latest/cookbook.html#using-asyncio-with-alembic
- https://redis.readthedocs.io/en/stable/examples/asyncio_examples.html
## Environment
空工作目录；uv 0.12.5，Git 2.55.0，Docker 29.8.1/Compose 5.5.1。python 命令是 Windows Store alias；uv python install 3.12 确认已有 managed 3.12.14。uv tool install specify-cli 安装 1.2.3，与 GitHub latest stable 相同；复现用 uv tool install specify-cli==1.2.3。Docker daemon 初始未启动，已启动 Docker Desktop，docker info 返回 29.8.1。
无重大需求歧义，Clarify 跳过。Spec Kit 为 Agent 技能，不是伪造可执行的 specify plan/analyze CLI；按官方技能读模板并产出文件。未配置 extensions hooks。
