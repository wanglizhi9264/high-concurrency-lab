# Data model

没有数据库变更。

- CacheTtl：ttl_seconds 为整数 1..60；jitter_limit_ms=ttl_seconds*100；expiration_ms 输入 jitter_ms 为整数 0..jitter_limit_ms，返回 ttl_seconds*1000+jitter_ms。不可变，不访问随机源或 Redis。
- FailureDecision：terminal bool，delay_seconds float；由 failure_decision(attempt, max_attempts, error) 返回；1<=attempt<=max_attempts<=5。非法值拒绝；invalid_paid_order 或最后一次 terminal=True；其他可重试。等待固定 0.2*2^(attempt-1)，最多2秒。
- 规则输出不直接改变状态；Service 用数据库 UTC 计算 due，在原事务内写 task/outbox/attempt/event，原最终 fence 仍生效。
