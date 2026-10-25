# 库存事务与幂等实验

先按[业务指南](business-lab.md)创建、初始化、分批写入独立业务库。基础初始化仍停在0003；库存结构必须显式升级，不在启动时建表。

```powershell
uv sync --frozen
docker compose up -d --wait
uv run python -m concurrency_lab.experiments.business_schema --database concurrency_lab_business
# 本地独立测试库已经按业务指南seed后
uv run python -m concurrency_lab.experiments.business_schema --database concurrency_lab_business_test
$env:BUSINESS_ENABLED='true'
$env:BUSINESS_WRITES_ENABLED='true'
$env:BUSINESS_DATABASE='concurrency_lab_business'
$env:BUSINESS_LOCK_WAIT_TIMEOUT='1'
uv run uvicorn concurrency_lab.main:app --host 127.0.0.1 --port 18002
# 另一个终端进入frontend
npm ci
npm run dev -- --host 127.0.0.1 --port 5173
```

迁移命令只允许两个business库并验证DATABASE、business-lab-v1、ready和revision。不会重置库存，不向002实验库执行head升级。MySQL DDL隐式提交；失败保留现场，不自动清表重建。对有数据的业务库不要运行downgrade base。

打开 `/inventory-lab`，按四步操作：

1. 创建新库存场景，商品1、初始5。每个场景是独立库存批次，旧场景保留，不是给同一仓库无限补货的生产接口。
2. 设置用户1、数量1，保存订单意图，检查UUID键和POST JSON，再提交。重复“提交/重放原意图”返回同一订单，库存不再预留。编辑数量后“原键+当前参数”用于观察409冲突；只有明确保存新意图才换键。
3. reserved订单可以标paid，或取消归还库存；同终态再次执行不重复记账。paid后取消会被拒绝，此处没有真实支付或退款。
4. 运行2..20个客户端争抢，查看每条真实响应；批量结束会实际GET审计。也可以单独GET审计。按订单ID去重计数，不能把多个重放200算成多笔下单。

审计核对：所有数量非负、available+reserved+sold=initial、reserved订单量=预留、paid订单量=已售。cancelled只是历史量；取消再下单后，历史订单总数量可以合法超过初始库存。

每次结果都有Request ID、浏览器往返、服务端区间及SQL。点击事务和SQL查看固定绑定参数与源码。写SQL显示实际影响行数；事务区间包含退出/提交成本。连接获取含连接配置与pre-ping，SQL执行含可能的锁等待，均不能称纯排队或纯锁等待。

请求与表的对应：
- `POST /api/v1/business/inventory/scenarios`：插入inventory_scenario，携带客户端scenario_id UUID，匹配重放不再创建。
- `POST /api/v1/business/purchases/orders`：Idempotency-Key UUID + scenario_id/user_id/quantity，原子插入purchase_order并预留库存。201新建，200重放，409分类冲突。
- `GET /api/v1/business/purchases/orders/by-key/{uuid}`：确认同一意图的持久化结果。
- `GET /api/v1/business/purchases/orders/{id}`：读取新订单。
- `POST /api/v1/business/purchases/orders/{id}/state`：paid/cancelled终态操作。
- `GET /api/v1/business/inventory/scenarios/{uuid}/audit`：同一RR快照核对库存与订单聚合。

原004 `/business/orders`、用户订单和明细API继续查询生成的lab_order/lab_order_item，新增订单不写进这些基线表。007新订单只在purchases路由和库存页查询。Redis商品缓存不提供库存数据或正确性锁，订单单价从MySQL读取。

故障处理：1205锁等待/1213死锁返回transaction_conflict和Retry-After，应用退出整笔事务。恢复后沿用原意图重试，不自动换键。COMMIT确认阶段超时或网络失败可能已提交：页面提示待确认，按原键查询或原样重放；不能断言“没有订单”。状态变更重试相同目标是幂等操作，跨终态冲突不要盲重试。

```powershell
# API运行、写开关明确开启后，创建全新实验场景，不重置旧场景
uv run python scripts/verify_inventory_lab.py --base-url http://127.0.0.1:18002
$env:INVENTORY_INTEGRATION='1'
$env:CACHE_INTEGRATION='1'
$env:BUSINESS_INTEGRATION='1'
uv run pytest tests/integration
uv run python scripts/verify.py
# frontend
npm run check
npm run test
npm run build
$env:PLAYWRIGHT_CHANNEL='msedge' # Windows可选，CI用Chromium
npm run test:e2e
```

脚本只接受loopback端口，保存唯一目录中的真实响应、事务/SQL、环境、意图和审计。不同键20请求争抢5库存，同键10请求只创建1订单；故障重试有界且保持键。结果见[007实验](../experiments/007-inventory-idempotency/README.md)。这是功能并发验收，不是生产容量测试。

建议源码顺序：Router → InventoryService → InventoryRepository → ObservedDatabase → domain/inventory.py → Alembic0004。重点学习事务整体回滚、统一锁顺序、RR旧快照与current read、唯一约束与幂等、条件更新、提交结果不确定、按状态审计。设计取舍见[ADR0005](../architecture/decisions/0005-inventory.md)。
