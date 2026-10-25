# 008 实际功能验收

记录：runs/worker-20261025T093041-533b5339/result.json，complete=true。2026-10-25T09:30:41 UTC开始，32.664秒，23次实际HTTP调用，5个本脚本拥有的worker子进程；没有并行测试/构建或其他压测。MySQL8.4.13、Redis7.4.11、本地Windows/Python3.12.14，具体服务/数据/连接池版本见原始monitor_before/after。源检查点13ed68b013f8f6c487f0cf1b08bbf92ac72b7950，工作源码干净且前后SHA一致eb5ac22f51664aedb2cc3c2bdd8b5e8e31147cba0febcd8280c9bb7cfb361208。验收脚本SHA单列。HTTP进程版本没有独立远端证明，不伪称有。

|实际场景|结果|真实观测|
|---|---|---|
|受控前1次失败|max3，第2次succeeded|attempt1 failed 0.0226ms；attempt2 succeeded 15.7992ms；唯一回执4|
|受控delay400ms，预算200ms|max2，failed保留|两次timeout，handler210.3200/206.0450ms；无回执|
|失败任务关联后继，关闭故障|新任务succeeded，原任务仍failed|原两次timeout历史逐字段未变；新任务handler14.8258ms，回执5|
|真实子进程提交claim后退出|exit70；GET观测running|attempt1 finished_at、handler_ms均null|
|相同scope重启|attempt1 abandoned，第2次succeeded|abandoned_at是恢复观察；旧耗时仍null；新handler14.0622ms，回执6|

队列实测：重试场景MySQL succeeded=1；XLEN=2（两次消息保留），XPENDING=0，group lag=0；PTTL86399577ms，采集25.635ms。不是把XLEN当积压，也不根据租约声称worker在线。

耗时均为实际功能观察：handler_ms排除claim/finalization/ACK，HTTP client_rtt另列，process_wall包含启动、空闲轮询与有界循环，不是处理吞吐。受控参数不是自然故障分布；小样本不用于生产RPS/P95/P99/CPU容量结论。monitor是整实例观测，不归因于这几个任务。无清表、重置库存、全库删Redis键或改写002历史证据。

本地验证：76unit；mypy69source files；Ruff/format；37集成通过、4旧索引opt-in跳过，随后对最终原子TTL适配器重新执行9任务集成均通过；35Vue单元测试；11完整Edge E2E通过，最终样式/适配器再验1任务E2E通过；前端types/lint/format/build通过；002三规模历史证据校验通过。现有Starlette测试弃用警告和Vite大chunk警告保留，不降低检查规则。远端PR/CI单独见specs/008.../validation.md，未执行前不声称通过。

Converge补验：最终11项任务集成全部通过（含领取后实际协程取消和Task/Outbox插入后整事务回滚），25.20秒；生产源码未在实际验收后改动。
