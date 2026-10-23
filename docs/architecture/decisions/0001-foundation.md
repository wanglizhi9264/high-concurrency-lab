# ADR-0001: Foundation architecture
Date: 2026-10-23 | Status: Accepted

| Decision | Why | Alternatives / future validation |
|---|---|---|
| Modular monolith | 单进程易调试、事务边界清楚 | 微服务增加部署复杂度，当前无证据需要 |
| FastAPI | 类型验证、ASGI、async lifespan | Flask/Django 可行；未来实验测请求路径开销 |
| SQLAlchemy 2 | 显式 SQL/事务、连接池、类型化 ORM | 直接驱动难以统一 Session；不隐藏 SQL |
| Async + asyncmy | MySQL/Redis I/O 不阻塞 event loop | 同步+线程池后续独立比较吞吐/尾延迟/连接数 |
| Docker Compose | 本地与 CI 复用真实 MySQL/Redis | 宿主安装难复现，K8s 超出范围 |
| Alembic | Schema 版本可追溯、可回滚 | create_all 不记录演进，不可替代迁移 |
| uv frozen lock | 固定依赖图，开发与 CI 一致 | 手写 requirements 范围不足以固定传递依赖 |

后果：必须测试连接取消、池耗尽、进程退出；每请求独立 Session，禁止多任务共享。基础健康检查无吞吐目标。镜像采用版本标签而非 latest，验收记录保存本次 digest；将来严格镜像复现可锁 digest 并制定升级流程。
