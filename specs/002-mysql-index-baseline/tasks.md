# Tasks: 002 MySQL Index Baseline
Input: spec.md,plan.md,research.md,data-model.md,contracts/cli.md. Tests explicitly required.
## Phase 1: Setup
- [X] T001 创建 compose.experiments.yaml、scripts/provision_index_lab.py；依赖 Analyze；标准：隔离实例/固定库，无删库；验证 compose config/启动。(FR-003)
## Phase 2: Foundational
- [X] T002 编写 tests/unit/test_index_baseline.py：allowlist/种子/batch/分页/TREE解析的失败测试；依赖 T001；标准：缺失模块预期失败；验证 pytest。(FR-002/003/005/006)
- [X] T003 实现 models/commerce.py、迁移0002/0003并更新 migrations/env.py；依赖 T002；标准：四实体/约束/两阶段迁移；验证升级/回滚/check。(FR-001/004)
## Phase 3: US1 Safe data (P1)
- [X] T004 [US1] 实现 experiments/safety.py、dataset.py、index_baseline.py init/seed；依赖 T003；标准：ownership/空表保护、bounded batch、摘要；验证 unit与真实数量。(FR-002/003)
- [X] T005 [US1] 编写 tests/integration/test_index_baseline.py 的保护与约束测试；依赖 T004；标准：重复生成拒绝、FK/金额约束、rollback；验证专用测试库。(FR-001/003/009)
## Phase 4: US2 Baseline and optimization (P1)
- [X] T006 [US2] 实现 experiments/queries.py、runner.py及 measure/optimize CLI；依赖 T005；标准：查询/分页/原始计划/空间/统计/顺序/不覆盖；验证 unit+真实小样本。(FR-004/005/006/007)
- [X] T007 [US2] 实现 scripts/verify_index_lab.py；依赖 T006；标准：三规模真实基线->优化、同页/身份验收；验证命令和 JSON。(FR-002/004/007)
- [X] T008 [US2] 实际执行10k/100k/1m，保存 docs/experiments/002-mysql-index-baseline/runs/ 与 report.md；依赖 T007；标准：全部真实、无凭据/全量数据；验证计数/摘要/计划。(SC-001/002/003)
## Phase 5: US3 Learn and maintain (P2)
- [X] T009 [US3] 更新 CI（保留原 jobs，新增实验隔离步骤）和 AGENTS.md、README、docs/database/design.md、架构文档；依赖 T008；标准：当前 schema一致；验证 quality/integration。(FR-008/009)
- [X] T010 [US3] 编写 docs/experiments/002-mysql-index-baseline/{README,dbeaver}.md，含 ER/教程/核心概念；依赖 T009；标准：命令一致且原始计划/估算说明准确；验证逐项复核。(FR-008)
## Phase 6: Validation and Convergence
- [X] T011 全量质量/集成/迁移验证，写 specs/002-mysql-index-baseline/validation.md；依赖 T010；标准：实际结果完整；验证所有 SC。
- [X] T012 执行 Converge、提交 feature 分支、创建 PR，等待 CI并经 PR 合并；依赖 T011；标准：无未解决缺口、main只经 PR修改；验证远端与干净工作区。(FR-009/SC-005)
## Dependencies & Execution Order
顺序 T001->T012，US1->US2->US3。测试先于对应实现，阶段检查后继续。
## Parallel Opportunities
独立文档可并行；MySQL官方研究由 Plan 子任务处理。实现顺序执行，数据库实验不可并行以免污染计时。
## Implementation Strategy
先安全迁移+小数据验证，再真实三规模基线/优化，最后文档/CI/PR。任何安全或统计错误先修复再接受证据。
