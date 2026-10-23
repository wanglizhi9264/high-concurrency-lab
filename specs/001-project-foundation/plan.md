# Implementation Plan: Project Foundation
**Branch**: `001-project-foundation` | **Date**: 2026-10-23 | **Spec**: [spec.md](spec.md)

## Summary
建立可复现的异步 FastAPI 模块化单体。先完成本目录规格和分析，再实施基础设施；不实现实验业务。

## Technical Context
**Language/Version**: Python >=3.11；本地/CI 3.12。
**Primary Dependencies**: FastAPI、Pydantic v2/settings、SQLAlchemy 2、asyncmy、Alembic、redis asyncio、uvicorn。
**Storage**: MySQL 8.4、Redis 7；lab_marker 最小迁移。
**Testing**: pytest/httpx、pytest-asyncio、Ruff、mypy、Locust 仅安装，暂不压测。
**Target Platform**: Windows/Linux 开发；Linux Docker/CI。
**Project Type**: src-layout web service。
**Performance Goals**: 无吞吐承诺；readiness 并发检查，每项默认总预算 2 秒。
**Constraints**: 不自动建表，不每请求建池，不泄漏配置和异常，所有实验结果保留实际证据。
**Scale/Scope**: 单进程基础工程，两条 health API、一张表、无业务接口。

## Constitution Check
设计前/后均通过：I 模块化单体；II 类型/静态检查；III Alembic；IV Session 独立事务；V lifespan Redis；VI 未测指标留空；VII 文档映射；VIII uv.lock；IX unit/integration/CI；X 环境变量和 loopback；XI 按 SDD 顺序。

## Project Structure
```text
specs/001-project-foundation/{spec,plan,tasks,research,data-model,quickstart,analysis,validation}.md
specs/001-project-foundation/contracts/health.md
src/concurrency_lab/{main.py,api/routes/health.py,core/config.py,db/session.py,models/marker.py,cache/client.py,services/health.py}
migrations/{env.py,versions/0001_lab_marker.py}
tests/{unit,integration}/
docs/{architecture/decisions,database,experiments,guides}/
.github/workflows/ci.yml
scripts/verify.py
```
**Structure Decision**: repositories、schemas 等无当前职责的目录暂缓；健康结果是稳定的小字典，无提前抽象。benchmarks 通过说明文档声明未来入口，不创建虚假压测。

## Design
Settings 强类型并隐藏 validation 输入；SQLAlchemy URL.create 编码密码；Redis 使用独立 host/password 字段。lifespan 用 AsyncExitStack 关闭部分初始化资源。Engine 与 redis 客户端保存在 app.state Resources；Session DI 用 async generator、上下文关闭，写操作显式 begin。
探针服务通过 asyncio.timeout 包住连接获取及命令，gather 并发；API 只映射 200/503，错误细节不输出。关闭时 Redis aclose、engine dispose。
Alembic async run_sync + NullPool；BigInteger 主键 marker 表，utf8mb4/InnoDB。

## Complexity Tracking
无宪章例外。asyncmy 的取消和池回收需要真实故障测试；不使用线程池包装同步驱动。
