# 004：真实业务查询与 Trace
业务库与002测量库分开，MySQL使用基础实例3306；前端仍通过HTTP，不连接数据库。默认不开启业务池，原健康检查不变。

## 初始化
在根目录执行，保留原.env密码：
```powershell
uv sync --frozen
docker compose up -d --wait
uv run python scripts/provision_business_lab.py
uv run python -m concurrency_lab.experiments.business_dataset --database concurrency_lab_business init
uv run python -m concurrency_lab.experiments.business_dataset --database concurrency_lab_business seed --orders 10000
$env:BUSINESS_ENABLED='true'
$env:BUSINESS_DATABASE='concurrency_lab_business'
uv run uvicorn concurrency_lab.main:app --host 127.0.0.1 --port 18002
```
另一个终端进入frontend，npm ci，然后npm run dev -- --host 127.0.0.1 --port 5173。打开/business。Linux把PowerShell环境设置改为export BUSINESS_ENABLED=true和export BUSINESS_DATABASE=concurrency_lab_business。也可在被忽略的.env内配置。
初始化只允许两个固定业务库。现成ready数据保留；不同规模拒绝覆盖；loading中断数据保留、不自动续跑；没有清空选项。10000订单、20000明细、1000用户、100商品，固定种子20261023。002库和JSON不变。所有DDL通过显式Alembic0003，应用启动不建表。

## 实际调用
```text
GET /api/v1/business/products/1
GET /api/v1/business/users/500/orders?limit=20&offset=0
GET /api/v1/business/users/500/order-page?limit=3&offset=0
GET /api/v1/business/orders/1
```
时间分页下一页使用响应next_cursor的before_time和before_id，不能同时给非零offset。按created_at DESC,id DESC稳定排序；底层ix_order_user_time(user_id,created_at,id)。商品主键索引；明细用order_id/product_id唯一索引前缀和商品PK的JOIN。主键/用户参数不拼进SQL。
Router（HTTP映射）→BusinessService（流程/Session/显式事务）→Repository（固定查询）→ObservedDatabase（计时）→SQLAlchemy→独立MySQL。每请求一个Session，同Session中不并发运行SQL。商品/列表每次一条业务查询；明细固定两条，另有一条实际库名/所有权/ready校验SQL。金额为Decimal字符串。未知用户为空；实体不存在404；无效参数422；未开启/连接失败/池耗尽503；请求预算504。

## 观测口径
响应X-Request-ID由服务生成，关联JSON trace和结构化请求日志。X-Process-Time-Ms测量至HTTP响应头准备，不含正文发送/网络；JSON service_elapsed_ms在序列化前结束，浏览器fetch+JSON往返另计。每span有同一服务端单调时钟起点、ms耗时、UTC观测时间、证据类型和固定源码路径。
acquire包括池等待/建连/pre_ping，不能称纯排队；sql_execute_fetch包括驱动/往返/数据库/取数，不能称MySQL服务器独立执行时间。父span含子span，不能相加。池before/after只是一进程瞬时gauges，不是等待队列。SQL结果数量含分页lookahead一行，页面仅展示limit条；计数时勿当成全表扫描行数。没有缓存，也没有真实故障动画。

## 测试
按同样步骤初始化concurrency_lab_business_test（固定测试库，不清理开发库），然后：
```powershell
$env:BUSINESS_INTEGRATION='1'
uv run pytest tests/integration/test_business.py
uv run python scripts/verify.py
uv run python scripts/verify_index_lab.py --verify-only
cd frontend
npm run check
npm run test
npm run build
$env:PLAYWRIGHT_CHANNEL='msedge'
npm run test:e2e
```
测试验证真实连接池耗尽、归还/并发独立Session、游标完整遍历和固定SQL数量。请求预算测试在隔离测试库执行受控SELECT SLEEP(1)，验证实际SQL取消、连接释放与后续查询恢复；该故障只在测试代码注入，HTTP没有SQL输入。另有真实连接失败测试。测试不会停止开发数据库或清空表。CI初始化独立业务测试库并执行关键真实浏览器测试。
