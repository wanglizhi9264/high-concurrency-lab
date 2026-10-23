# Pre-implementation Analyze
2026-10-23；在任何应用代码修改前执行。未配置 extension hooks。
| Requirement | Tasks | Acceptance |
|---|---|---|
| FR-001 | T003,T005 | migrations/constraints/ER |
| FR-002 | T002,T004,T007,T008 | deterministic bounded batches at3 scales |
| FR-003 | T001,T002,T004,T005 | allowlist/ownership/empty protection |
| FR-004 | T003,T006,T007 | revision and saved-baseline gate |
| FR-005 | T002,T006,T008 | raw TREE/per iterator/size |
| FR-006 | T002,T006,T008 | stable equal page/cursor cost |
| FR-007 | T006,T008 | real JSON/percentiles/unmeasured null |
| FR-008 | T009,T010 | documentation/tutorial |
| FR-009 | T005,T009,T011,T012 | tests/CI/PR |
SC-001/002/003 -> T008；SC-004 -> T011；SC-005 -> T012。
Nine FR covered, five SC mapped, zero orphan tasks, zero unresolved ambiguities. Eleven constitution principles checked before/after design. No critical/high findings. Explicitly retain FK index and distinguish baseline without suitable sorting/email index; PK is control. No destructive reset. Proceed to Implement.
