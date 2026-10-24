# 003 End-to-end acceptance
2026-10-24；真实本地浏览器截图（Edge / 1440×1000，全页截图），由 frontend/e2e/platform.spec.ts 在实际 FastAPI/MySQL/Redis 环境生成。

- architecture.png：选中MySQL后职责/源码详情同步，展示真实lazy资源创建记录；虚线Session与缓存不是实际健康路径。
- database.png：百万订单OFFSET数据来自002，Baseline P50=414.6824999770615ms；Optimized P50对应原JSON；选中Table scan显示actual rows=1000000。
- live-trace.png：实际健康HTTP200后单步回放，服务端事件与浏览器时钟独立，非模拟请求。

同一E2E流程还验证Pool Simulation、播放/暂停、实验列表/详情、深色模式和无页面异常；独立503测试注入API错误验证重试界面。结果以 specs/003-interactive-system-visualization/validation.md 和PR CI为准。

这些截图是具体时刻的观察，时间不是性能基准。002原始JSON保持不变；003没有重跑造数或写入业务表。
