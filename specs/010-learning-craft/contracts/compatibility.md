# Compatibility contract

所有 HTTP 路由、JSON/Trace 字段、错误码和默认参数保持不变。缓存 bypass 不接触 Redis；协调超时不冒充 hit；发布失败不重复 SQL；finally 释放 lease，取消继续传播。TTL 随机偏移依旧等概率整数 0..ttl_seconds*100 毫秒。

任务 invalid_paid_order 立即终止，其他原有错误达到最大次数才终止。原失败 attempt 状态（timeout/failed）、next_publish_at、available_at、事件和提交后 ACK 保持不变。规则不替代数据库 lease/token/state 校验，不把 Redis 当业务事实源。

本轮没有新 HTTP/CLI 业务契约。新增文档验收 CLI 无参数，只读本仓库 docs/learning 并校验章节与文件链接；失败返回非零，不启动服务。
