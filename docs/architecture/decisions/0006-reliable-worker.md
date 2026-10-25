# ADR 0006：MySQL任务权威状态、Outbox与Redis Streams传输

状态：接受，2026-10-25，Feature008。本文在Worker实现前完成选型。

固定业务任务是为007已paid订单生成一张持久化凭证，不发送邮件、不运行任意脚本。MySQL保存Task、Outbox、Attempt、Event和Receipt；Redis只保存任务UUID及消费组传输信息。Redis丢失可重建传输，不改变任务权威状态。

选择Redis7 Streams：已存在Redis依赖，消费组/PEL/reclaim可直接验证重复交付和崩溃恢复；不增加Celery/RQ等框架。纯数据库轮询能保证任务状态，但不能满足本阶段学习真实队列传输的目标。FastAPI BackgroundTasks或进程内队列无法提供持久恢复，因此不采用。语义为at-least-once传输 + 幂等数据库效果，不称exactly-once消息。

创建事务原子写Task、Outbox和created event，任务UUID与payload fingerprint控制重放。只接受paid订单，scope由订单所属库存场景派生。API不要求Redis在线，受理不等于已发布。Outbox无发布确认也不证明Redis绝无消息：XADD可能成功而确认落库前进程失败。

Dispatcher先普通选有界候选，再依Task→Outbox顺序加锁重新检查due状态，执行一条有250ms预算的XADD，收到message ID才记录发布确认。网络调用持锁是简化方案，仅单条短预算，不无限重试。发送后DB提交失败会产生重复消息，属于预期协议。非终态任务按due/cooldown和batch上限定期重发；running且租约有效不重发。这样修复broker重启、trim或丢失pending payload；不自动清表/删全库。

Worker为独立CLI进程，显式指定owned business数据库和库存scenario，避免处理其他实验。XGROUP CREATE使用id=0-0,mkstream=True，仅忽略BUSYGROUP；XREADGROUP BLOCK100ms，禁止noack；XAUTOCLAIM按Redis7三项返回解析并继续游标。PEL consumer/idle只用于交付恢复，不是执行权。

实际执行权来自MySQL Task行租约：Task锁内检查due/state/数据库UTC时钟，增加attempt并提交随机token与lease期限，随后释放Session执行固定handler。最终事务再次锁Task，凭证唯一upsert与success原子提交，最后条件UPDATE检查token、running和DB时钟下lease仍有效；不通过则回滚效果。失败/超时也受同样fence约束。旧worker不能结束新owner的任务。

Receipt对order_id唯一，多个Task/重复消息只保留一张原凭证。使用明确ON DUPLICATE KEY UPDATE id=id，再current read，不用INSERT IGNORE掩盖FK/CHECK，也不在已失败Session内继续。paid在007为不可逆终态，创建Task不长期锁订单，避免Order→Task/Task→Order反序。

自动失败按有界attempt和backoff记录retry_wait、next_due、Attempt/Event与持久发布意图，然后才ACK旧消息。耗尽/最后一次崩溃保留failed。MySQL failed记录承担失败队列处置，不再建第二个Redis死信流；手动重试创建linked新Task，原failed/attempt历史不重置。正常成功先提交Receipt/Task，再XACK；ACK失败不把success改回failed，重复读取只确认终态后ACK。

Streams每个scenario独立键，最多约1000条保留消息、24h空闲TTL，数据库due扫描恢复可能被trim/过期的未完成工作。XLEN含已ACK和重复传输，不是积压；XPENDING是交付未ACK，group lag可能未知；数据库非终态计数单列。发布/ACK超时都可能已生效，确认未知不等于没发生。

可选故障配置独立标记controlled_fault_configuration，前N次注入失败或实际异步delay，让真实Worker执行失败/截止路径；不伪造耗时，不用于容量结论。handler_ms从claim提交后到handler返回/失败，排除claim/finalization/ACK；崩溃未记录完成时刻与耗时保持null，abandoned_at只表示恢复者观察时刻。HTTP GET Trace与异步Attempt/Event不同模型。

CLI支持有界单轮/循环、停止和恢复；crash-after-claim仅用于明确故障实验，在claim提交后真实子进程退出。作用域为显式测试/实验scenario，恢复依DB租约和outbox，不靠内存状态。凭据、lease token不输出API或日志。MySQL0005显式迁移，不在启动自动DDL；007的0004命令与002固定迁移保留。

参考：[XGROUP CREATE](https://redis.io/docs/latest/commands/xgroup-create/)、[XREADGROUP](https://redis.io/docs/latest/commands/xreadgroup/)、[XAUTOCLAIM](https://redis.io/docs/latest/commands/xautoclaim/)、[XACK](https://redis.io/docs/latest/commands/xack/)、[XINFO GROUPS](https://redis.io/docs/latest/commands/xinfo-groups/)、[MySQL错误处理](https://dev.mysql.com/doc/refman/8.4/en/innodb-error-handling.html)。本地核对redis-py7.4.1，服务Redis7；不用Redis8新增的CLAIM/XACKDEL等选项。

Retention detail: Redis MULTI/EXEC groups XADD with PEXPIRE, and XGROUP initialization with PEXPIRE. Only BUSYGROUP is ignored; EXEC still applies expiry for an existing group. A transport timeout is unconfirmed, never proof of absent publication. Idle TTL is refreshed on publication or group access, not a task deadline.
