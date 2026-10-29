# Tasks: 010 learning craft

## Phase 1: Setup
- [x] T001 在 specs/010-learning-craft/ 完成 Specify、Plan、研究、契约及只读 Analyze（FR-001..006）。

## Phase 2: US1 策略可读性
- [x] T002 [US1] 在 tests/unit/test_learning_policies.py 验证 TTL 边界、重试次数和终态语义（FR-002/SC-001）。
- [x] T003 [US1] 在 domain/cache.py、domain/tasks.py 实现 data-model.md 的整数范围、不可变结果与固定默认规则，并接入 services/product_cache.py、task_execution.py（FR-001/002）。

## Phase 3: US2 学习手册
- [x] T004 [US2] 编写 docs/learning/README.md 和 01..08 八章，每章源码/操作/现象/反例/自测/答案齐全（FR-003/SC-002）。
- [x] T005 [US2] 编写 docs/learning/references.md 精选原始资料及阅读边界，能力矩阵明确原理与未实现项（FR-004/005）。

## Phase 4: US3 可维护性
- [x] T006 [US3] 编写 docs/learning/maintaining.md，修正 docs/guides/source-reading.md 的失效源码入口，更新 README.md（FR-005）。
- [x] T007 [US3] 编写 scripts/verify_learning_docs.py 并执行离线验收（FR-003/SC-002）。

## Phase 5: Validation and delivery
- [x] T008 在 specs/010-learning-craft/validation.md 记录质量与真实缓存/任务回归，核对历史证据未变（FR-001/006/SC-003）。
- [x] T009 对现有实现执行只读 Converge，在 specs/010-learning-craft/converge.md 记录结果（FR-006）。
- [x] T010 通过独立 GitHub PR 交付，远端 CI 与合并状态写入实际报告（FR-006）。

依赖：T001→T002→T003；T004/T005可在规格后独立完成；T006/T007依赖手册；T008依赖实现；T009依赖验证；T010依赖前述工作及实际 CI。无自动重测百万数据。
