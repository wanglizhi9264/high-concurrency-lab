# Tasks: Project Foundation
**Input**: spec.md、plan.md、research.md、data-model.md、contracts/health.md。
**Tests**: 用户明确要求 unit/integration/CI。

## Phase 1: Setup
- [X] T001 创建 pyproject.toml、.python-version、uv.lock、.gitignore；依赖：分析通过；完成：frozen sync；验证：uv sync --frozen。(FR-002)
## Phase 2: Foundational
- [X] T002 编写 tests/unit/test_config.py 配置边界测试并确认初始失败；依赖 T001；完成：缺失/无效配置覆盖；验证 pytest。(FR-002/009)
- [X] T003 实现 src/concurrency_lab/core/config.py、db/session.py、cache/client.py；依赖 T002；完成：强类型配置与共享池/Session DI；验证配置测试/mypy。(FR-005)
## Phase 3: US1 Environment (P1)
- [X] T004 [US1] 编写 compose.yaml、Dockerfile、.env.example、.dockerignore；依赖 T003；完成：loopback/healthcheck/volume；验证 compose config/up --wait 和镜像 build。(FR-003)
- [X] T005 [US1] 编写 tests/unit/test_health.py，先验证失败；依赖 T003；完成：live/ready/失败/超时/关闭场景；验证 pytest。(FR-004/005)
- [X] T006 [US1] 实现 src/concurrency_lab/main.py、services/health.py、api/routes/health.py；依赖 T005；完成：两探针和 lifespan 清理；验证 health tests。(FR-004/005)
## Phase 4: US2 Readiness and migration (P1)
- [X] T007 [US2] 编写 tests/integration/test_mysql.py、test_redis.py、test_api.py；依赖 T006；完成：真实连接、Session、API；验证独立集成测试。(FR-006/007)
- [X] T008 [US2] 实现 alembic.ini、migrations/env.py、migrations/versions/0001_lab_marker.py、src/concurrency_lab/models/marker.py；依赖 T007；完成：upgrade/downgrade；验证真实 MySQL 迁移链路。(FR-006)
## Phase 5: US3 Maintainability (P2)
- [X] T009 [US3] 配置 .github/workflows/ci.yml、scripts/verify.py；依赖 T008；完成：frozen/lint/types/unit/integration；验证本地相同命令，远端 CI 单独标明未运行。(FR-007)
- [X] T010 [US3] 完成 README.md、docs/architecture/overview.md、docs/architecture/decisions/0001-foundation.md、docs/database/design.md、docs/experiments/template.md、docs/guides/local-development.md、benchmarks/README.md、AGENTS.md；依赖 T009；完成：与代码一致；验证按指南复核。(FR-008)
## Phase 6: Verification and polish
- [X] T011 实际运行 quickstart 和故障/恢复、持久化、Docker build 检查，记录 specs/001-project-foundation/validation.md；依赖 T010；完成：证据完整；验证所有 SC。(FR-009)
- [X] T012 更新 specs/001-project-foundation/tasks.md 并执行 converge 复核；依赖 T011；完成：无遗漏或追加明确任务；验证 prerequisites 和逐项验收。(FR-001/009)

## Dependencies & Execution Order
T001 -> T002 -> T003 -> T004 -> T005 -> T006 -> T007 -> T008 -> T009 -> T010 -> T011 -> T012。
## Parallel opportunities
US1 Dockerfile/Compose 可与独立测试文件编辑并行；US2 MySQL/Redis 测试独立；US3 各文档可并行。本轮顺序实施，不要求多 Agent 实施。
## Implementation Strategy
先交付 US1 可运行环境作为 MVP，再 US2 迁移和真实依赖验证，再 US3 文档质量门禁。每个阶段复核后再继续。

