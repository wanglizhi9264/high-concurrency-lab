# Architecture Overview
## 004 business extension
Original diagrams below describe foundation health. The opt-in business path is separate:
```mermaid
flowchart LR
  Vue[BusinessQueryView] -->|fixed HTTP GET| Router[Business Router + DI]
  Router --> Service[BusinessService / request Session transaction]
  Service --> Repository[Product/Order Repository]
  Repository --> Observation[ObservedDatabase / execute-fetch spans]
  Observation --> Session[SQLAlchemy Session + lifespan business pool]
  Session --> MySQL[(Owned business database)]
  Middleware[Request ID / preparation headers / safe logs] -.observes.-> Router
```
Responsibilities, exact observation boundaries and safety decisions: [ADR0002](decisions/0002-business-lab.md), [runbook](../guides/business-lab.md).001/003health traces remain separate;002reads immutable JSON. No businessRedis/queue yet.
```mermaid
flowchart LR
  HTTP --> API[health routes]
  API --> Probe[bounded async probes]
  Probe --> Engine[SQLAlchemy async pool]
  Probe --> Redis[Redis async client]
  Engine --> MySQL[(MySQL 8.4)]
  Redis --> Cache[(Redis 7)]
  Lifespan --> Engine
  Lifespan --> Redis
  Alembic --> MySQL
```
main.py lifespan 创建 Resources（配置、Engine、Redis、sessionmaker），退出关闭。api/routes/health.py 只负责 HTTP；services/health.py 调用 SELECT 1/PING，asyncio.timeout 包含池等待和命令时间，两项 gather 并发。默认每项 2 秒，非硬实时保证。失败仅返回 unavailable。
core/config.py 读取环境变量/.env，密码为 SecretStr，validation 不显示输入。db/session.py 提供每请求独立 AsyncSession DI；写操作必须显式 session.begin()，异常回滚，关闭 session。SQLAlchemy URL.create 安全编码特殊字符密码。
基础健康路径中 Redis 只有连通性验证，无缓存/锁/队列。MySQL 已作为004业务查询事实源。一进程基础池上限为 pool_size + max_overflow=10，多 worker 时乘 worker 数；Redis 每进程默认最多 10 个连接。pool_recycle=1800 应小于服务器 wait_timeout。
models/marker.py 仅迁移验证；没有运行时 create_all。迁移独立于应用启动，使用 NullPool。
业务 services/repositories/schemas 按004起的独立职责引入。性能改造必须对照环境、基线和尾延迟，不能将异步视作必然更快。

## 002 实验模块
experiments/ 下 safety.py 是库名/所有权保护，dataset.py 负责有界批量事务，queries.py 定义固定查询与计划解析，runner.py 保存真实测量，index_baseline.py 为 CLI。使用独立 mysql-experiment 实例与 volume，默认13306；不借用应用池，不新增 HTTP 路由。
commerce.py 中四个关系模型只服务数据/索引实验。Alembic0002提供基线结构，0003新增查询索引；ORM metadata 表示 head。迁移配置支持程序传入 database_url，仍由 Alembic管理全部DDL。安全元数据表仅保存实验身份与 loading/ready状态。

## 003 可视化入口
Vue3 SPA位于frontend/，以只读DTO API访问架构、经过Pydantic校验的002证据和健康观测。services/visualization.py仅读取固定目录及固定文件名；schemas/visualization.py定义完整证据/响应边界。services/tracing.py为单请求monotonic事件记录器，原health Service只增加可选回调，旧API响应不变。
真实健康路径直接Engine.connect，不经过Session；启动记录是lazy对象创建；frontend的浏览器往返与服务端时钟分开。池模拟完全在客户端，真实pool快照只读现有gauges。无SQL写入API、无新Schema/缓存/队列。详见 docs/guides/visualization-platform.md。

## 004 业务读取与005负载观测
Business mode显式开启后，lifespan额外拥有一个只连接固定业务库的共享池。Router映射HTTP，BusinessService拥有单请求Session和显式读事务，Repository发出绑定SQL。ObservedDatabase统一记录取数span，RequestObservation记录monotonic区间与安全的请求ID；所有权检查在同一事务中执行。详见[业务指南](../guides/business-lab.md)。

005为独立Locust子进程，不将gevent引入API。启动器只管理自己的临时单worker API/Locust进程，采集原始调用起点、完成响应、SQL观测覆盖率、进程和容器资源。业务监控读取共享池及MySQL实例状态，监测本身会竞争资源。RecordedLoadRun通过固定目录、ID、大小和schema校验后供Vue对比；HTTP不能启动压测。详见[压测指南](../guides/load-testing.md)和[ADR0003](decisions/0003-load-evidence.md)。

## 006 商品缓存
独立缓存路由 → ProductCacheService → ProductCache（固定Redis脚本）或原004 BusinessService（显式Session读事务）。命中不进入MySQL，miss/降级才执行所有权检查和商品SQL。Redis客户端继续由lifespan持有；schema/observations.py共享实际时间戳类型，缓存DTO不依赖负载实验DTO。

固定generation与随机lease token共同约束回填发布；失效会撤销在途回填，有界等待后允许无缓存重复读。缓存不是库存正确性工具。浏览器页面逐次展示实际HTTP、Redis命令、SQL、来源和选定key快照；003缓存教学仍是Simulation，健康PING仍不经过业务缓存。详见[ADR0004](decisions/0004-product-cache.md)和[操作指南](../guides/cache-lab.md)。
