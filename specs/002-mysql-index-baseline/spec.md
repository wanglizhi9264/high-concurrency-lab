# Feature Specification: MySQL Index Baseline
**Feature Branch**: `feature/002-mysql-index-baseline`
**Created**: 2026-10-23
**Status**: Ready for planning
**Input**: 用户要求真实 MySQL 表结构、分批造数、索引与分页实验，独立分支经 PR 合并。

## User Scenarios & Testing *(mandatory)*
### User Story 1 - Safe reproducible data (Priority: P1)
学习者在隔离的实验数据库建立用户、商品、订单、明细，并可按固定种子生成不同规模数据。
**Why this priority**: 安全和可复现是所有性能比较的前提。
**Independent Test**: 迁移升级/回滚、约束测试、两次相同种子批次摘要相同；非空数据库拒绝生成。
**Acceptance Scenarios**:
1. **Given** 专用空实验库，**When** 生成 10000/100000/1000000 订单，**Then** 数量精确、外键有效、批次有界，保存元数据。
2. **Given** 非实验库或已有数据，**When** 调用脚本，**Then** 拒绝写入，不清空任何表；中断后保留已提交批次并明确报告不可自动续跑。
### User Story 2 - Baseline then optimization (Priority: P1)
学习者先保存缺少查询专用索引的真实基线，再添加索引，对同数据和请求重测。
**Why this priority**: 没有基线无法解释优化收益和代价。
**Independent Test**: 执行验收脚本，核验 baseline/optimized 的数据身份、执行计划、时间、行数和大小。
**Acceptance Scenarios**:
1. **Given** 基线迁移，**When** 执行主键、用户过滤、用户时间排序、深分页和非索引邮箱查询，**Then** 保存完整实际计划、扫描相关行数、重复测量和统计口径。
2. **Given** 已保存基线，**When** 索引升级后重测，**Then** 同数据摘要、查询参数和样本数可比，不预设一定更快。
3. **Given** 时间重复的订单，**When** OFFSET/游标读取同一深页，**Then** 按时间与主键的稳定顺序返回相同 ID，无重复遗漏；游标定位成本单独披露。
### User Story 3 - Learn and maintain (Priority: P2)
学习者使用 DBeaver 查看关系、索引、计划，后续 Agent 能复现实验并维持质量门禁。
**Why this priority**: 原始结果需要解释和可独立验证的操作教程。
**Independent Test**: 单元/真实库测试、验收脚本、现有和新增 CI 步骤通过；教程与命令一致。
**Acceptance Scenarios**:
1. **Given** 实验结果，**When** 阅读报告，**Then** 可区分 estimated/actual rows、表/索引估算大小、冷/热缓存与测量局限。
2. **Given** 完成分支，**When** 创建 PR，**Then** 检查通过并经 PR 合并，不直接向 main 提交。
### Edge Cases
- MySQL 外键必需的索引保留，主键查询是对照；不宣称基线完全没有索引。
- 固定时间有重复，必须 (created_at,id) 双列排序和严格比较。
- 不提供清空/重置/删库选项，不覆盖已有结果文件。
- 无实验安全标识、连接库不匹配、错误迁移版本、基线丢失、种子不匹配均拒绝实验。
- 小规模结果可能受缓存与噪声影响，不将单次更快解释为普遍规律。

## Requirements *(mandatory)*
### Functional Requirements
- **FR-001**: MUST 定义四类关系实体及明确的键、类型、约束和索引；使用可逆迁移，不自动建表。
- **FR-002**: MUST 生成 1万、10万、100万订单，固定种子、分批提交，单批最多配置批量，不加载全量。
- **FR-003**: MUST 默认连接隔离实验库，验证库名和所有权标识；已有数据拒绝生成，不执行清空表/删库。
- **FR-004**: MUST 先记录基线再添加专用索引；保留 FK/PK 说明，禁止绕过基线顺序。
- **FR-005**: MUST 至少四类 SQL 的真实 EXPLAIN ANALYZE 与计时、计划实际行/循环数、表及索引大小；另加邮箱全表扫描对照。
- **FR-006**: MUST OFFSET/keyset 双列稳定排序、同页相等验证，记录游标获取开销，不将定位开销隐去。
- **FR-007**: MUST 结果和元数据存于 docs/experiments/002-mysql-index-baseline/，包含环境、参数、数据身份、原始计划、重复测量、P50/P95/P99、串行吞吐、错误率；未采集资源项显式 null。
- **FR-008**: MUST ER 图、DBeaver 指南、命令、结论局限与人工学习概念清楚。
- **FR-009**: MUST unit/real MySQL integration/acceptance 测试，保留基础 CI，独立分支 PR 合并，无 Redis/库存/队列/订单 API。
### Key Entities
用户、商品、订单、订单明细；实验所有权标识和生成元数据仅为防护与追溯，不是业务 API。

## Success Criteria *(mandatory)*
### Measurable Outcomes
- **SC-001**: 三个规模均实际完成生成、基线与优化采样，并验证订单/明细精确计数。
- **SC-002**: 每个规模至少 5 类查询原始执行计划和重复耗时可读，基线先于优化且数据一致。
- **SC-003**: OFFSET/keyset 返回同页，重复时间值下的分页测试无遗漏/重复。
- **SC-004**: 错误数据库、非空数据及结果覆盖保护测试通过，迁移与所有质量测试通过。
- **SC-005**: 文档可追溯，PR 的 quality/integration 通过，Converge 无未解决缺口。

## Assumptions
- 这是只读查询和批量写入教学实验，四类表不代表订单业务实现，不修改宪章。
- 使用独立 Compose 实验 MySQL 实例及 volume，默认端口 13306；现有 app 数据库保持独立。
- 数据每个规模独立数据库；每订单两条明细，1000 用户、100 商品；不实现非确定随机分布扩展或断点续传。
- 固定种子默认 20261023。单客户端顺序测量，暖缓存，非并发 API 压测；无性能提升硬阈值。
- 不存在需用户选择的重大歧义，Clarify 不触发。
