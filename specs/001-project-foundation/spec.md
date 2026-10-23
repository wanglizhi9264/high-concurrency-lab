# Feature Specification: Project Foundation

**Feature Branch**: `001-project-foundation`
**Created**: 2026-10-23
**Status**: Accepted for implementation
**Input**: 用户提供的 High Concurrency Lab 工程初始化与 SDD 开发任务。

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reproducible development environment (Priority: P1)
开发者从干净克隆启动依赖服务，并使用锁定依赖运行应用。
**Why this priority**: 所有后续实验依赖可复现环境。
**Independent Test**: frozen sync、Compose healthy、停止后再次启动保留数据。
**Acceptance Scenarios**:
1. **Given** Docker 和 uv 可用，**When** 按 README 启动，**Then** MySQL、Redis healthy。
2. **Given** 本地配置，**When** 启动应用，**Then** live 返回 200。

### User Story 2 - Dependency readiness and migration (Priority: P1)
开发者区分应用存活和依赖就绪，并可升级及回滚最小 Schema。
**Why this priority**: 防止将进程存活误判为服务可用。
**Independent Test**: real integration tests plus dependency failure unit tests。
**Acceptance Scenarios**:
1. **Given** 依赖健康，**When** ready，**Then** 200 且两个依赖为 ok。
2. **Given** 任一依赖失败或超时，**When** ready，**Then** 503，live 仍为 200，响应无异常详情。
3. **Given** 空数据库，**When** upgrade / downgrade / upgrade，**Then** marker 表创建、删除、重建。

### User Story 3 - Maintainable SDD and quality gates (Priority: P2)
后续 Agent 能追溯规格、架构和实验规范，并运行一致的检查。
**Why this priority**: 保障长期实验可维护。
**Independent Test**: Spec Kit prerequisites、静态检查、pytest、文档命令复核。
**Acceptance Scenarios**:
1. **Given** 锁定依赖，**When** 执行质量命令，**Then** Ruff、mypy、unit tests 全部通过。
2. **Given** 后续实验需求，**When** 阅读文档，**Then** 当前 Schema 和未来规划明确区分。

### Edge Cases
- 缺少密码配置时应用启动明确失败；密码不可出现在 validation 错误。
- 连接池耗尽、连接失败及命令挂起由 readiness 每个依赖的总超时限制。
- 启动不连接依赖也不建表；依赖离线仍可检查 live。
- 关闭应用时连接池均释放；初始化部分失败也释放已创建资源。
- 集成测试仅显式运行，不能将缺少服务解释为通过。

## Requirements *(mandatory)*
### Functional Requirements
- **FR-001**: MUST 初始化官方 Spec Kit、Constitution、feature artifacts，并保留版本及流程记录。
- **FR-002**: MUST 使用 src 包、uv.lock、Python 3.11+ 和明确配置验证。
- **FR-003**: MUST 提供 MySQL 8.4、Redis 7 Compose、healthcheck、持久化卷、环境密码和 loopback 端口，以及 Dockerfile。
- **FR-004**: MUST 提供 GET /health/live 200 和 GET /health/ready 200/503，返回稳定 JSON；依赖检查并发，每个默认 2 秒总超时，不泄漏异常。
- **FR-005**: MUST lifespan 复用并关闭 Engine/Redis pools，集中配置池参数，提供 Session DI。
- **FR-006**: MUST Alembic 管理一张最小 lab_marker 表，支持 upgrade/downgrade，无 create_all。
- **FR-007**: MUST 单元测试、独立 MySQL/Redis 集成测试和 CI lint/types/unit/integration gates。
- **FR-008**: MUST README、架构图、ADR、数据库设计、实验模板、开发指南及六阶段路线与代码一致。
- **FR-009**: MUST 记录实际验证、失败及未验证项；不得虚构性能指标或提交真实凭据。

### Key Entities
- LabMarker: 仅验证迁移链路，整数主键 id；无业务接口或预置数据。
- HealthResponse: status 与可选 checks；checks 键为 mysql、redis，值为 ok 或 unavailable。

## Success Criteria *(mandatory)*
### Measurable Outcomes
- **SC-001**: 干净安装与依赖启动按 README 可复现，服务可重复停止/启动。
- **SC-002**: live 200；ready 健康 200，MySQL/Redis 单独离线均 503；挂起检查在总预算内退出。
- **SC-003**: 迁移升级、回滚、再升级成功，数据可经 Session 读写。
- **SC-004**: 所有质量检查和真实集成测试通过，并逐项记录证据。
- **SC-005**: 九项 FR 均有任务和验证映射，无未解释规格占位符。

## Assumptions
- 本机开发单实例，无认证业务；health 输出不包含敏感诊断。
- Python 3.12 作为本地及 CI 基线，最低声明 3.11。
- 默认本地端口 3306/6379，可由环境修改。
- 没有影响范围的重大歧义，Clarify 无需提问；具体选型在 Plan/ADR 说明。
