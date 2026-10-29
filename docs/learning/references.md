# 精选参考：读对问题，不收藏整片互联网

以下链接于2026-10-29研究时核对。原始资料多数英文，先读本手册的中文解释，再按问题定位；不要求读完所有源码。这里学习的是设计理由，不复制外部项目代码，也不把其特定配置描述成本项目保证。

| 经典项目/一手资料 | 只读哪里 | 对应本项目 | 不照搬什么 |
|---|---|---|---|
| [Cosmic Python示例项目](https://github.com/cosmicpython/code)及[Repository章](https://www.cosmicpython.com/book/chapter_02_repository)、[UoW章](https://www.cosmicpython.com/book/chapter_06_uow) | 谁负责规则、存取、一次原子工作 | domain、repositories、owned_session | 不引入Message Bus/CQRS/通用UoW，不直接搬同步Session |
| [SQLAlchemy项目](https://github.com/sqlalchemy/sqlalchemy)及[Session Basics](https://docs.sqlalchemy.org/en/20/orm/session_basics.html) | Session生命周期、事务退出、并发使用 | db/business.py | 不通读ORM内核，不共享AsyncSession |
| [Celery Tasks](https://docs.celeryq.dev/en/stable/userguide/tasks.html) | 幂等、retry、超时、ACK的问题 | task_execution / worker runtime | 不新增Celery，其acks_late/进程终止规则不同 |
| [Python3.12 asyncio](https://docs.python.org/3.12/library/asyncio-dev.html) | blocking code、取消相关概念 | async Service/worker | 不认为async自动把同步操作移到线程 |
| [MySQL8.4 MVCC](https://dev.mysql.com/doc/refman/8.4/en/innodb-multi-versioning.html)、[索引](https://dev.mysql.com/doc/refman/8.4/en/optimization-indexes.html) | 版本读与实际SQL访问 | inventory / scale | 不先研究数据库内核源码 |
| [Redis SET](https://redis.io/docs/latest/commands/set/)、[EVAL](https://redis.io/docs/latest/commands/eval/) | NX/PX、Lua调用约定 | cache/products.py | 不把锁模板当任意业务正确性保证 |
| [MDN HTTP](https://developer.mozilla.org/en-US/docs/Web/HTTP/Guides/Overview) | 请求/响应、连接链路 | API与浏览器排障 | 不先补全所有HTTP扩展 |
| [Google SRE Monitoring](https://sre.google/sre-book/monitoring-distributed-systems/) | 四个监控信号 | load monitor / resources | 不搭整套生产监控平台来学一个指标 |
| [OWASP对象级授权](https://api-security.owasp.org/editions/2023/en/0xa1-broken-object-level-authorization/) | 用ID访问对象时逐次验证权限 | 未来订单授权 | 不把本机写开关当登录权限 |

学习材料选择标准：解释当前代码中的真实决定；能用小测试或时间线验证；读完能帮助修改或排错。与当前场景无关的分布式共识实现、搜索引擎、Kubernetes、全套微服务暂不列必修。
