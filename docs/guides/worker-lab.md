# 可靠异步回执任务实验

先完成007创建场景→下单→标记paid。任务只生成本地实验回执，不发送邮件，也不处理真实支付。

## 显式准备与运行

项目根目录执行，已有.env只在本地维护。BUSINESS_ENABLED=true、BUSINESS_WRITES_ENABLED=true；BUSINESS_DATABASE只能是concurrency_lab_business或concurrency_lab_business_test。不要把凭据放入命令历史或Git。

```powershell
uv sync --frozen
uv run python -m concurrency_lab.experiments.business_schema --database concurrency_lab_business --revision 0005
uv run uvicorn concurrency_lab.main:app --host 127.0.0.1 --port 18002
cd frontend
npm ci
npm run dev -- --host 127.0.0.1 --port 5173
```

打开/tasks；从/inventory-lab已paid订单的链接进入可自动带入订单ID。保存任务UUID与原参数→提交→读取详情。201表示MySQL事务接受，200表示匹配意图重放；409需核对状态/参数；网络超时是结果待确认，保留UUID再次提交或GET，不能自行认定没入库。

在项目根目录另开终端，**复制任务页实际显示的命令**。示例中的UUID必须替换为该订单所属场景：

```powershell
uv run python -m concurrency_lab.workers.receipts --database concurrency_lab_business --scenario <SCENARIO_UUID>
```

--role dispatcher只发消息，--role consumer只消费，默认both。--once执行一轮，--max-cycles 15执行最多15轮。Ctrl+C请求正常停止，当前有界工作完成后退出；强制终止则等待MySQL租约到期后恢复。不要停止其他进程或删除其他场景的键。

## 每一步实际做什么

1. POST /api/v1/business/tasks：读取paid采购订单，事务内INSERT durable_task、task_outbox、task_event。没有请求Redis。UUID与完整效果参数指纹用于重放。
2. dispatcher：SELECT本场景到期任务，依次锁Task→Outbox，重新校验due；XADD只发task_id，记录真实message ID后提交发布确认。发布与确认间故障会重复发送。
3. consumer：XGROUP CREATE id0-0（仅首次），XAUTOCLAIM恢复pending，XREADGROUP领取新消息。Redis交付不代表取得业务执行权。
4. claim事务：锁Task，用MySQL UTC时钟判断due/lease，写随机私有token、attempt、claimed事件，提交并释放连接。
5. handler：实际读取paid订单并准备回执快照；受控delay/fail配置会真的执行，默认不启用。该阶段有独立deadline，不长期持有数据库Session。
6. finalize事务：锁Task验证token/租约，按UNIQUE(order_id)幂等写order_receipt；条件UPDATE再次检查DB时钟下租约仍有效。回执、成功状态、尝试完成与事件一起提交。失去执行权则回滚效果。
7. 最后XACK。ACK超时不改变已提交的success；重复消息核对终态后再ACK。ACK观测可能缺失，不代表ACK绝对没发生。

SQL详情在本次HTTP Trace中；异步worker的历史在Attempt/Event中，不把之后的工作塞进先前HTTP耗时。详情使用同一个RR快照；写事务使用RC与当前锁读。

## 看懂成功、失败与恢复

queued是持久接受；running是数据库执行权已领取，不能证明进程存活；retry_wait是最早到期时间之后才可再次尝试；succeeded关联已提交回执；failed保留耗尽/不可重试的历史。failed重试创建关联后继任务，原任务不复位。

故障配置独立标记controlled_fault_configuration。前1次失败可观察failed→retry_wait→成功；delay400ms配合CLI --timeout-seconds .2 --lease-seconds 1可观察真正超时。handler_ms只测处理阶段，不含claim/finalize/ACK，不用于生产容量推断。

实际崩溃探针只退出本次CLI子进程：

```powershell
uv run python -m concurrency_lab.workers.receipts --database concurrency_lab_business --scenario <SCENARIO_UUID> --crash-after-claim --max-cycles 10
```

观察退出码70和已提交running/attempt；同scope正常重启，过期lease会产生abandoned。崩溃尝试finished_at、handler_ms保持null；abandoned_at是恢复者的观察时刻。若最后一次尝试崩溃，恢复为failed，不能无限重试。

Redis不可用：创建仍可成功，dispatcher保留意图并报告依赖不可用，恢复后重启相同scope即可。Redis数据被trim/过期/重启丢失：数据库到期扫描可在cooldown后重发；无需清表。发布确认或DB提交ACK未知时，保留场景与UUID，不编造失败或success。旧worker不能凭过期token提交成功或失败。

## 队列与时钟

XLEN是保留条数，包含已ACK和重复历史；XPENDING是已投递未ACK；group lag可能未知；MySQL各状态计数另列。队列页采集是跨系统独立读，不是原子快照，Redis不可用显示null。PTTL为实测快照，不做客户端倒计时。每个scene固定stream键，约1000条传输保留和24h访问/发布后空闲TTL；MySQL任务/回执/历史不自动删除。

## Navicat / DBeaver核对

使用本地.env对应的business数据库连接，不在截图/文档写口令。刷新表，查看durable_task、task_outbox、task_attempt、task_event、order_receipt；按页面UUID去掉短横线过滤id/task_id。查看order_receipt唯一索引uq_receipt_order；同一order_id只一行。按task_attempt.number及task_event.id排序，核对UTC时间、状态与失败原因。不要手动改lease/token/state或清表。

## 验证

```powershell
uv run python scripts/verify.py
$env:TASK_INTEGRATION='1'
uv run pytest tests/integration/test_tasks.py
uv run python scripts/verify_worker_lab.py --base-url http://127.0.0.1:18002
```

脚本新建场景，真实启动/结束自己拥有的worker子进程，记录实际重试、deadline耗尽、关联后继、真实exit70及恢复；不会清除旧数据。结果独占保存docs/experiments/008-reliable-receipt-worker/runs/，失败也保留部分证据。这里只是功能验收，CPU/RPS/尾延迟容量实验属于005/009。CI保留既有三个required jobs并增加真实任务协议测试。

Retention detail: Redis MULTI/EXEC groups XADD with PEXPIRE, and XGROUP initialization with PEXPIRE. Only BUSYGROUP is ignored; EXEC still applies expiry for an existing group. A transport timeout is unconfirmed, never proof of absent publication. Idle TTL is refreshed on publication or group access, not a task deadline.
