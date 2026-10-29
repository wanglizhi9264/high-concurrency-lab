# 05 缓存：快照副本的两张通行证

## 问题与解释

MySQL 是事实，Redis 是副本。Cache-Aside 指先查缓存，没命中才查数据库，然后尝试回填。缓存不可用时可回数据库，但这不代表无限回源安全：数据库仍可能过载。库存判断因此从不依赖商品缓存。

为什么要两种标记？token 表示“这次租约是谁的”，generation 表示“这是哪一代缓存”。它们解决的不是同一个问题。

例一：A取得租约，执行很慢；租约过期后 B取得新租约并回填。A恢复时若不核对 token，就能覆盖 B 或删除 B 的租约。

例二：A读取旧商品；管理员失效缓存，generation 从3变4；A随后回填。即使 A自认为读成功，旧版本也不能复活。发布必须同时核对 token 和 generation，且检查与写入放在同一 Lua 原子操作中，不能拆成 Python 的 GET→判断→SET。

TTL 是副本自动消失的时间。`CacheTtl` 把范围写清楚：1..60秒，加0..10%的毫秒抖动。例如5秒实际为5000..5500ms，旨在分散同时过期；不能保证消除雪崩。协调等待另有250ms预算，不是把所有请求永久锁住。

## 源码入口

[纯 TTL 规则](../../src/concurrency_lab/domain/cache.py) → [读链路](../../src/concurrency_lab/services/product_cache.py) → [Redis 原子脚本](../../src/concurrency_lab/cache/products.py)。纯规则不知道 Redis，Service 选择随机数，Lua 才拥有实际发布的原子性。

## 动手操作

```text
uv run pytest tests/unit/test_learning_policies.py -k ttl -v
uv run pytest tests/unit/test_product_cache.py -k failed_publication -v
```

配置 owned test 库和 Redis 后，设置 `$env:CACHE_INTEGRATION='1'`，再运行：

```text
uv run pytest tests/integration/test_product_cache.py -k "generation or invalidation or unreachable" -v
```

也可在 `/cache-lab` 依次观察 bypass、首次读取、热读和失效，再展开 SQL/Redis 操作。不要使用 FLUSH 清空整个 Redis。

## 预期现象

bypass 不访问 Redis；热读不执行商品 SQL；拿不到租约的请求有界等待，必要时不带租约回源但不发布。已查到 MySQL 商品后若缓存发布失败，仍可返回商品，不应该重新查一遍 MySQL。finally 尝试只释放自己的租约，失败还有租约 TTL。

## 反例

“删除缓存后绝不再出现旧值”只有在防回填规则正确时才成立。当前也没有真实商品修改事务与可靠失效闭环；手动 invalidate 演示不等于解决了“数据库更新提交后 Redis 恰好故障”。后续应定义失效补偿和允许不一致窗口。

缓存穿透是大量不存在对象也回源；热点击穿是热点副本过期带来并发回源；大量key或实例同时失效可能形成雪崩。本项目实现冷读协调/抖动/降级，但缺失商品不做负缓存，不宣称三类问题全部解决。

## 自测与答案

问：只检查 generation，能防止旧租约误删新租约吗？答：不能，释放必须检查 token。

问：Redis GET 返回成功是否一定是合法商品？答：不是，还需验证 schema、库名、商品ID、generation；错误缓存不能冒充正常结果。

## 精选参考

[Redis SET](https://redis.io/docs/latest/commands/set/) 阅读 NX/PX；[Redis EVAL](https://redis.io/docs/latest/commands/eval/) 对照脚本接口；不要直接照搬“分布式锁万能模板”。
