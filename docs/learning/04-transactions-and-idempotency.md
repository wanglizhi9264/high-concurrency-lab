# 04 事务与幂等：把“不应该发生”写成约束

## 问题与解释

库存5，两个人同时看见5，分别扣4；如果先读再无条件写，很可能产生错误。需要把“还有足够库存”与扣减放到数据库保护的操作中。本项目通过固定锁顺序、条件更新、约束和事务保护，不依赖某个 API 进程里的 Python 锁。

业务不变量是任何成功提交后都要成立的事实：available、reserved、sold 非负；三者之和等于 initial；reserved 与未结算订单匹配。创建订单和预留库存必须一起提交，任何一步失败都回滚。金额使用 DECIMAL，避免浮点近似误差。

幂等是同一个意图多次发送，只产生一次业务效果。UUID key 标识意图，payload 指纹检查内容是否相同；同 key 改数量不是重试，应冲突。唯一约束处理多个进程竞争；不能仅凭“先 SELECT 没有”就断定可以插入。

RR 普通快照读可能继续看到旧视图；`FOR UPDATE` 的锁定读取关注当前可锁定状态。发生1062后，本实现让整个事务退出，再开新事务看赢家，不复用失败 Session 或旧快照。RC 与 RR 各有一致性/竞争取舍，不是版本高低。

MVCC 用版本信息支持一致性读；undo 支持旧版本/回滚，redo 用于崩溃恢复，binlog 记录服务层变更供复制和恢复等用途。三者不是三份等价备份。间隙/next-key 锁需要结合隔离级别、索引和查询范围理解，不可只背“行锁只锁一行”。本阶段先解释现有实际冲突。

## 源码入口

[不变量与状态机](../../src/concurrency_lab/domain/inventory.py) → [事务服务](../../src/concurrency_lab/services/inventory_service.py) → [仓储条件更新与锁](../../src/concurrency_lab/repositories/inventory_repository.py) → [真实并发测试](../../tests/integration/test_inventory.py)。

## 动手操作

先运行 `uv run pytest tests/unit/test_inventory.py -q`。按[库存指南](../guides/inventory-lab.md)配置隔离测试库0004或已升级0005，PowerShell设置 `$env:INVENTORY_INTEGRATION='1'`，运行：

```text
uv run pytest tests/integration/test_inventory.py -k "distinct_concurrent or same_key or deadlock" -v
```

使用新的场景 UUID，不重置已有库存。

## 预期现象

不同意图竞争不能超卖；同意图重放只返回已有结果；死锁实际出现后，受害事务被回滚，同意图可以重试。测试执行具体失败码与审计，不是用 mock 假装数据库有锁。

取消订单是 available 增加、reserved 减少；历史 cancelled 订单仍存在，但不占库存。paid 在本项目只是状态，不代表真实支付收款。

## 反例

所有异常都自动重试，会重复放大缺货或非法状态请求。死锁1213与锁超时1205要回滚整个应用事务；提交 ACK 超时则可能是“提交了但回复丢失”，不能向用户保证未下单，更不能换一个 key 再下单。

## 自测与答案

问：幂等只需要 Redis SET NX 吗？答：不够；业务效果在 MySQL，需与持久约束/事务协调，Redis失效不应导致重复订单。

问：为什么所有事务先锁 Scenario 再锁 Order？答：统一资源获取顺序能减少相互等待形成环；仍需处理数据库检测到的死锁。

## 精选参考

[MySQL MVCC](https://dev.mysql.com/doc/refman/8.4/en/innodb-multi-versioning.html)；[Cosmic Python UoW](https://www.cosmicpython.com/book/chapter_06_uow)，只学原子工作单元思想，当前 owned_session 已承担该职责。
