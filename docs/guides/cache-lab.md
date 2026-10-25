# Redis 商品缓存实验

先按[业务指南](business-lab.md)初始化独立 `concurrency_lab_business`（本地）和 `concurrency_lab_business_test`（测试）。保留002实验数据。Redis沿用 `.env` 配置和lifespan客户端，密码不写入代码。

```powershell
uv sync --frozen
docker compose up -d --wait
$env:BUSINESS_ENABLED='true'
$env:BUSINESS_DATABASE='concurrency_lab_business'
uv run uvicorn concurrency_lab.main:app --host 127.0.0.1 --port 18002
# 另一个终端，frontend目录
npm ci
npm run dev -- --host 127.0.0.1 --port 5173
```

打开 `/cache-lab`。商品1的精确金额为字符串 `1.17`。选择“绕过缓存”发送真实GET，只查MySQL；选择“使用缓存”，先点“主动失效”，再连续查询两次。首次MISS会执行所有权检查和商品SQL，回填成功后再次查询为HIT，SQL为0。每次结果都展示实际URL、来源、请求ID、浏览器往返、服务端区间、Redis命令和SQL源码。

“检查选定键”是独立请求，显示key、采样时刻、PTTL和MEMORY USAGE。TTL是快照，不是假倒计时。设置短TTL后真实等待，再检查键不存在并查询回源。MISS也可能来自淘汰、失效或从未缓存，不能直接当作Redis过期事件。

“主动失效”实际发送DELETE，只处理该商品value/lease并更新generation，不删除MySQL商品。degraded表示操作未确认，不能当作失效成功；恢复Redis后再试。回填显示被fencing拒绝时，商品仍是当次真实MySQL结果，只是旧加载者无权再发布缓存。

固定接口：
- `GET /api/v1/business/cache/products/1?mode=cache&ttl_seconds=5`
- `GET /api/v1/business/cache/products/1?mode=bypass`
- `GET /api/v1/business/cache/products/1/state`
- `DELETE /api/v1/business/cache/products/1`

商品实验ID限1..1000，TTL限1..60秒，实际value过期增加0..10%抖动。原004商品读取入口继续无缓存。接口不接受Redis key、命令、Lua或SQL。所有命令使用固定命名空间，禁止FLUSH或清空开发数据库。

本页初次命中率为已收到响应中 `initial hit/(hit+miss)`；等待后复用是初查MISS、最终来自Redis，两者单列。绕过、检查、失效、未知不进分母。每页保留最近50条响应，可以点击历史请求检查Trace；网络失败单列，不补成0 SQL。Redis往返时间包含网络，协调等待包含轮询，不是纯排队。MySQL商品SQL和所有权SQL分开统计。

```powershell
# 仓库根目录，API运行后；只对商品1执行明确的缓存失效，不改MySQL
uv run python scripts/verify_cache_lab.py --base-url http://127.0.0.1:18002 --concurrency 6
# 使用已初始化的独立测试库与真实Redis
$env:CACHE_INTEGRATION='1'
$env:BUSINESS_INTEGRATION='1'
uv run pytest tests/integration
uv run python scripts/verify.py
# frontend目录
npm run check
npm run test
npm run build
$env:PLAYWRIGHT_CHANNEL='msedge' # Windows可选，CI使用Chromium
npm run test:e2e
```

记录脚本只接受显式loopback端口，并发1..20，创建唯一目录；保存每次真实响应、客户端HTTP毫秒、SQL尝试、初次命中与MySQL实例监测。完整结果在 `docs/experiments/006-redis-cache-aside/runs/`，失败记录标complete=false。不能把5条请求的P95当作可靠尾延迟或容量结论。

源码阅读顺序：`api/routes/product_cache.py` → `services/product_cache.py` → `cache/products.py` → 原004 `BusinessService`/Repository。原子脚本和一致性取舍见[ADR0004](../architecture/decisions/0004-product-cache.md)。Redis不可用会放大MySQL负载；lease不保证恰好一次回源，TTL抖动不保证没有雪崩，不存在商品目前仍会穿透。后续商品写入必须设计提交后失效及失败恢复。
