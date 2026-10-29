# Implementation Plan: 010 学习工程精修

**Branch**: feature/010-learning-craft | **Date**: 2026-10-29 | **Spec**: [spec.md](spec.md)

## Summary
将已有任务失败决策和缓存 TTL 规则提为纯函数/不可变值；服务继续拥有 I/O、事务及原子 fence。以源码为轴编写八章中文手册及精选经典参考，保留全部外部契约与测量记录。

## Technical Context
Python >=3.11 / FastAPI / SQLAlchemy2 / MySQL8.4 / Redis7，沿用 uv.lock，零新依赖。pytest 单元和现有真实集成；Windows 本机、Linux CI。此为可读性重构与学习文档，不设性能提升指标。只改两条策略调用路径，不改前端、Schema、HTTP DTO、Lua、ACK 顺序及实验源码/记录。

## Constitution Check
| 原则 | 设计前/后检查 |
|---|---|
| I 架构 | 纯决策放 domain；不添加策略工厂或通用 UoW |
| II Python | typed public functions、不可变结果、Ruff/mypy |
| III 数据库 | 无迁移、无 create_all |
| IV 一致性 | 原事务边界、唯一效果、fence 不变 |
| V Redis | Lua/lease/generation 不变；TTL 分布不变 |
| VI 证据 | 不编辑历史记录，不宣称性能改善 |
| VII 文档 | README 和源码指南可到手册；章节链接可查 |
| VIII 依赖 | frozen install，零依赖变更 |
| IX 测试 | 策略边界及真实缓存/任务回归；不可运行则保留待办 |
| X 安全 | 不读出凭据、不拓展监听；学习练习明确安全范围 |
| XI SDD | Specify→Plan→Tasks→Analyze→Implement→验证→Converge→PR |

## Project Structure
- src/concurrency_lab/domain/cache.py：命名 TTL 规则，随机性由调用方传入。
- src/concurrency_lab/domain/tasks.py：失败决策（终态、下一次等待）。
- src/concurrency_lab/services/product_cache.py、task_execution.py：调用规则。
- tests/unit/test_learning_policies.py：边界、原语义及无 I/O 决策。
- docs/learning/README.md、01..08 章节、references.md、maintaining.md。
- scripts/verify_learning_docs.py：离线检查必需章节、结构和相对文件链接。
- specs/010-learning-craft/：规格、研究、契约、任务、分析和实际验收。

## Decisions
失败决策固定现有 0.2/0.4/0.8/1.6/2 秒上限；invalid_paid_order 直接终止。终态仍保留原 available_at 写法以兼容既有记录。TTL 为原秒值加 0..10% 毫秒偏移。无可热更新配置。纯函数拒绝内部非法输入；HTTP 非法 TTL 仍保持现有 BusinessFailure。

## Phases
先规则与契约回归；再八章、经典资料及维护指南；最后离线链接验证、质量/真实服务检查、只读收敛及 PR。历史实验数据不产生新性能对比。

## Complexity Tracking
无宪法例外。鉴权、部署、备份提供清楚的缺口与学习路径，不作为本轮已实现功能。
