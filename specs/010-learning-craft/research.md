# Research — 2026-10-29

只读研究已完成：仓库内核对两条实际链路，speckit-plan 研究代理核对参考适用范围。

| Decision | Rationale | Alternative |
|---|---|---|
| 参考 [Cosmic Python](https://github.com/cosmicpython/code) 的 Repository 与 UoW 职责 | 与当前订单/库存业务直接对应；事务入口已有 owned_session | 不照搬 Message Bus/CQRS，也不增加通用 UoW 包装 |
| 参考 [SQLAlchemy Session](https://docs.sqlalchemy.org/en/20/orm/session_basics.html) | 对照现有异步事务所有权 | 不把书中的同步 Session 例子搬成共享 AsyncSession |
| 参考 [Celery Tasks](https://docs.celeryq.dev/en/stable/userguide/tasks.html) 的重试/幂等/ACK 问题 | 帮助解释已有 Outbox/Stream/receipt | 不引入 Celery，不把其特定 ACK 行为描述为本项目保证 |
| 提取实际决策，不建立策略框架 | 两个真实规则有独立边界；纯测试能检查语义 | 策略注册器、继承树和插件配置没有当前需求 |

未决问题：无。外部资料作为解释来源，代码独立编写；不复制书籍或框架源码。
