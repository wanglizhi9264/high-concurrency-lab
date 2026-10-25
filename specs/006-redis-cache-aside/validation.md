# Validation and review — 006

2026-10-25，base main df3c590（005 PR7已合并），分支feature/006-redis-cache-aside。Constitution2.0.0复核无需修订；Specify→Plan（官方只读研究代理）→Tasks→Analyze→Implement顺序执行。16条requirements-quality checklist全部通过；Analyze只读核对6FR/4SC/12任务覆盖，无阻塞项；无extensions hooks。

实际本地验证：
- Ruff lint/format、mypy48sourcefiles通过；完整Python单元56项通过，补充4项CLI目标保护后缓存单元11项通过；最终完整单元套件结果将在下方补记。
- `CACHE_INTEGRATION=1 BUSINESS_INTEGRATION=1 uv run pytest tests/integration`：18passed，4项旧002opt-in测试跳过。8项缓存测试使用真实Redis与独立business_test库；仅清理明确测试商品的精确Redis键，不重置数据库。原004和foundation测试保留。
- 实测包含bypass/miss/hit、PTTL真实过期、MEMORY USAGE、主动失效、无效副本与generation、缺失商品不造数据、12冷请求协调、6慢请求有界重复回源、旧lease不能覆盖或释放新owner、旧generation不能发布、取消恢复、真实不可达Redis和真实客户端池耗尽降级及恢复。
- 前端TypeScript/ESLint/Prettier通过，25Vitest/VTU通过，build通过。真实Edge全8项E2E通过；最后按钮样式调整后缓存E2E单独重跑通过，包含MISS→HIT、零商品SQL、Redis命令源码、实际TTL等待与检查。
- `verify_index_lab.py --verify-only`三种规模通过；002JSON/数据库、005原始runs未修改。
- 两次实际缓存CLI实验完整保存；最终记录来源clean checkpoint01efe1a，实际数值见docs/experiments/006-redis-cache-aside/README.md。不把单元Mock、受控并发暂停或小样本P95当作性能结论。

代码审查与修正：
1. Redis共用sync/async EVAL stubs：只在asyncio.Redis适配器边界cast Awaitable，业务层不泄漏客户端类型差异。
2. generation-only fencing不足：固定Lua同时比较generation与随机lease token；失效原子撤销lease；真实lease过期/旧owner测试验证。
3. 轮询deadline若只在循环入口判断，最后一条Redis命令可能越界：改为整段asyncio.timeout，span标记timeout，无lease降级不填缓存。
4. 默认Redis池10连接使12个同时请求部分降级：协调测试配置足够连接以隔离机制，另补真实max1耗尽/释放/恢复测试，未削弱单次回源断言。
5. 缓存写失败不能重复MySQL查询：独立单元回归验证只读一次；已取到的商品直接返回。
6. 初次查找与最终来源分开，合并回源不伪装初查命中；generation损坏与Redis连接不可达区分，检查失败保持null。
7. 共享UTC时间戳校验抽到schemas/observations.py，使cache DTO不依赖负载实验DTO；旧benchmarks契约回归通过。
8. 旧003“缓存尚未实现”和全局READ ONLY断言已同步，教学模型继续标Simulation，PING继续不经过商品缓存。

模块职责清晰：Router仅映射HTTP；Service协调读/降级；Redis适配器仅固定安全命令；MySQL读事务继续由004Service拥有；trace计时集中在RequestObservation。无新DDL、无create_all、无进程内锁冒充跨进程保护、无任意Redis命令或未授权MySQL写入。lease token不输出给客户端，错误不暴露凭据、连接地址或原始异常。

已知现有提示：Starlette TestClient弃用提示、Vite大chunk建议仍存在，未降低检查规则。远程CI/PR尚待执行，发布任务T012保持开放。

## Final local gate and Converge
Full verify.py after final test additions: Ruff/format/mypy48files passed,60unit passed. Converge readonly assessment covered6FR/4SC/3storyacceptancegroups/12tasks, plan module/safety/metric decisions and11constitutionprinciples. No remaining implementation findings of missing/partial/contradicts/unrequested type, all severities0. Implementation converged; external publication/check/merge gate T012 remains pending. No empty convergence task section or extension hooks.
