# ADR 0005：库存事务、统一锁顺序与可确认的幂等请求

状态：接受，2026-10-25，Feature007。

每次实验创建新的UUID库存场景，描述某个商品的一批初始数量；没有重置已有库存的接口。既有lab_order查询样本保持不变，新增inventory_scenario/purchase_order承载可写实验。范围限单商品订单，不接真实支付或退款。

MySQL库存行约束：所有数量非负，available+reserved+sold=initial。订单约束数量1..100、total=quantity×unit_price、状态枚举、外键及唯一幂等键。价格来自MySQL并作为订单快照保存；Redis副本和进程内锁不决定库存。

正常写入统一按Scenario→Order取锁。创建先做普通幂等查询以快速重放；不存在则SELECT场景FOR UPDATE，取得MySQL价格，INSERT唯一订单，再执行available>=quantity的条件UPDATE。必须先处理唯一INSERT，再判断可用数量：等待锁期间别的请求可能已用同键提交且库存售罄。先插入带父外键订单再升级库存锁会产生共享→排他升级死锁，因此不采用该顺序。

ownership普通SELECT可能建立RR旧快照。1062唯一冲突后退出整个事务并回滚，用新Session/事务查赢家、核对规范化payload SHA256；不在SAVEPOINT回滚后的旧快照里找赢家。fingerprint仅包含场景/用户/数量，不包含实时价格。相同键与内容重放原订单，不再预留；内容不同409。场景UUID本身也提供创建幂等，匹配场景重放，改初始量或商品则冲突。

状态变更先普通读取订单定位不可变场景ID，再锁场景，最后以列映射SELECT订单FOR UPDATE取得current state，避开ORM identity map旧状态。reserved→paid转移到sold，reserved→cancelled归还available；同终态重放不记账，跨终态拒绝。库存变更检查reserved>=quantity且影响恰好一行，订单状态与库存同事务提交。

1213死锁与1205锁等待均让应用退出并回滚整个事务。1205默认仅回滚失败语句，不能继续提交先前步骤。连接池在允许写入时统一设置session innodb_lock_wait_timeout（默认1秒，范围1..10），不SET GLOBAL；设置发生于连接初始化，包含在获取连接区间，不假装是独立业务SQL观测。没有透明无限重试，冲突返回安全代码与Retry-After，创建重试必须沿用原键。

取消发生于提交前的受控测试可证明回滚；COMMIT确认或网络阶段超时则可能结果未知。不能从transaction.error/timeout推断绝无订单，应按原键查询或原样重放确认。事务span包含实际退出/提交成本，SQL区间包含可能的服务端锁等待，不能称纯锁等待。

审计在同一RR快照做普通读取与按状态聚合：核对库存余额、reserved订单量和paid订单量。cancelled数量只是历史，合法取消再预留后，历史订单总量可以超过initial。真实死锁测试仅在独立测试库引入外部反序事务，使用barrier与真实行锁，记录实际受害者；生产路径不使用反序，不假设InnoDB固定选择某一事务。

Alembic0004由独立owned-business迁移命令显式执行，基础business初始化仍冻结0003；不升级002实验库。MySQL DDL隐式提交，失败时保留现场，不自动清表重建。写入口默认关闭，需要明确迁移后启用BUSINESS_WRITES_ENABLED。

参考：[RR一致性读](https://dev.mysql.com/doc/refman/8.4/en/innodb-consistent-read.html)、[InnoDB锁](https://dev.mysql.com/doc/refman/8.4/en/innodb-locks-set.html)、[错误与回滚](https://dev.mysql.com/doc/refman/8.4/en/innodb-error-handling.html)、[死锁检测](https://dev.mysql.com/doc/refman/8.4/en/innodb-deadlock-detection.html)、[DDL隐式提交](https://dev.mysql.com/doc/refman/8.4/en/implicit-commit.html)。

库存事务获取连接时显式指定REPEATABLE READ，不依赖服务器默认隔离级别。真实隔离测试从READ COMMITTED会话开始，验证审计内实际隔离为RR；连接配置与重置包含在资源获取/退出成本中。
