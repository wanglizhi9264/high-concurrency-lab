# ADR 0004：商品 Cache-Aside 与可撤销回填

状态：接受，2026-10-25，Feature006。

商品查询复用004的独立业务库、Service读事务和Repository绑定SQL。Redis客户端由lifespan持有；缓存仅保存实际访问且存在的商品，不预热全集，不改变MySQL。默认查询路径004仍绕过缓存，006提供独立入口。缓存失败不能制造商品或把故障当作404。

固定键空间：`hcl:cache:v1:{业务库名}:product:{1..1000}:value|generation|lease`。库名只允许business/business_test，generation不设置TTL以避免版本归零的ABA问题，最多2000个generation键；value为1..60秒加0..10%正抖动，lease为1000ms。没有KEYS/SCAN/FLUSH和任意命令入口。

首次MGET同时读取generation/value，校验版本、源库、商品ID和DTO。MISS后用随机token通过短Lua原子取得lease及generation，再复查缓存。MySQL回源结束后，发布Lua必须同时匹配generation与lease token，才写入带TTL的副本。主动失效Lua先INCR generation，再删除value与lease，撤销在途回填。安全释放仅删除仍匹配自己的token。只比较generation无法阻止旧lease过期后覆盖新loader，因此两个条件都不可省。

等待者仅异步轮询最多250ms，deadline包含Redis命令时间；超时允许重复读MySQL，但不进行无lease回填。单Redis协调只减少重复工作，不承诺恰好一次回源，更不提供库存一致性。取消继续传播；finally短预算释放失败时由lease TTL兜底。每条Redis命令预算250ms，整个读取仍受业务请求预算约束。缓存写失败时直接返回已经取得的MySQL商品，不重复SQL。

替代方案：单进程锁不能协调多个worker；GET比较后独立SET存在失效竞态；无限等待使Redis成为可用性依赖；Redis全局keyspace命中率混入lease/generation/检查，不代表商品查询。采用真实初次lookup样本的hit/(hit+miss)，等待后复用单列最终来源，未知、绕过、检查、失效不参与分母。

一致性边界：当前没有商品修改API。未来商品更新必须先提交MySQL，再设计失效失败恢复；跨MySQL/Redis没有强一致事务，Redis恢复旧快照或故障切换也可能恢复陈旧副本。失效超时可能已经生效，返回degraded表示未确认，不能显示成功。TTL是副本保鲜策略，不是业务正确性锁。

穿透：不存在商品不做负缓存，重复缺失请求继续查MySQL，明确展示这一代价。击穿：短lease与有界等待合并部分回源，超时/故障/客户端池耗尽仍可重复回源。雪崩：TTL抖动降低同步到期概率，不能消除Redis整体故障导致的回源压力；需后续容量与限流设计，当前不声称已保护生产系统。

可观测性：Redis命令是客户端网络/驱动往返区间；协调等待包含轮询，非纯排队。商品SQL与所有权SQL分别计数，真实命中不创建业务Session。PTTL为采样时刻毫秒（-2不存在，-1无过期，null未知），MEMORY USAGE为选定value键字节估算，非全实例内存。nil仅表示MISS；等待实际TTL后再看到缺失，是实验序列证据，不冒充keyspace过期事件。

参考：[Redis Cache-Aside](https://redis.io/docs/latest/develop/use-cases/cache-aside/)、[SET](https://redis.io/docs/latest/commands/set/)、[安全释放token](https://redis.io/docs/latest/develop/clients/patterns/distributed-locks/)、[EVAL](https://redis.io/docs/latest/commands/eval/)、[PTTL](https://redis.io/docs/latest/commands/pttl/)、[MEMORY USAGE](https://redis.io/docs/latest/commands/memory-usage/)。实现使用Redis7兼容命令，不依赖Redis8.4新增条件命令。
