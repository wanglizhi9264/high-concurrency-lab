# 07 性能与排障：先证据，后调参数

## 问题与解释

发起100个请求，每个很快503，完成RPS可以很好看，但用户没有完成业务。至少区分开始速率、包含失败的完成吞吐、成功吞吐、错误率，以及P50/P95/P99。P95表示给定样本中约95%的耗时不超过该值，不能解释成“95%用户永远这样快”。七次查询样本的P99尤其不稳定。

闭环压测用户执行完一次才继续，请求慢了会降低开始速率；它和固定到达率不是一回事。并发、吞吐和平均在系统停留时间，在稳定且口径一致时可以用 Little's Law 关联，但不能拿瞬时并发除以P99算承诺容量。

连接获取 span 包含池排队、建连、pre_ping 等；execute/fetch 包含驱动、网络、取数；浏览器RTT还包含传输与客户端因素。嵌套跨度不能直接相加。容器CPU可能多核超过100%，runner CPU和数据库容器CPU也不能相加为某条SQL成本。

## 源码入口

[真实压测工作负载](../../benchmarks/locust/locustfile.py)、[原始采样](../../src/concurrency_lab/experiments/resource_sampling.py)、[Trace记录](../../src/concurrency_lab/observability/recording.py)、[005报告](../experiments/005-real-load-testing/README.md)、[009报告](../experiments/009-scale-comprehensive-lab/report.md)。

## 动手操作

先只读两个报告，对比“完成吞吐”和“成功吞吐”，不重新跑重型性能实验。单元回归：`uv run pytest tests/unit/test_load_testing.py -q`。

服务故障时，在 PowerShell 用真实端口逐层查：

```powershell
Get-NetTCPConnection -LocalPort 5173,18002 -State Listen -ErrorAction SilentlyContinue
curl.exe -i --max-time 5 http://127.0.0.1:18002/health/live
curl.exe -i --max-time 5 http://127.0.0.1:18002/health/ready
docker compose ps
```

Linux 对应先用 `ss -lntp` 看监听，`ps -ef` 看进程，`top`/`free -h`/`df -h` 看资源，`curl` 看实际HTTP；使用部署环境的日志入口。不要为排查先重启、清库或把密码贴出来。

## 预期现象

连接拒绝：该地址/端口没有可接收连接的服务，先查进程和监听。live200而ready503：API活着，依赖检查失败；ready只验证它实际执行的探针，不保证每个业务表ready。API直连成功而页面failed to fetch：再查浏览器Network的实际URL、前端代理目标、协议与跨域配置，不能直接归因MySQL。

MySQL1045是身份/密码/host匹配等认证问题；先核对实例端口、用户与客户端实际来源。修改.env不会自动修改已有MySQL卷里创建过的账号。不能用删除卷解决认证失败。参阅[连接指南](../guides/scale-lab.md)。

## 反例

“延迟高就增大池”可能增加数据库争用；“Redis故障就全部回源”可能把MySQL拖垮。过载保护要有界并发、等待上限、有限重试、必要的快速拒绝；当前没有完整入口限流器，不应宣称已治理过载。

## 自测与答案

问：500用户短测完成137.585 RPS、成功13.986 RPS，哪个能当成功容量？答：都不能直接当生产容量；后者只说明该次短测成功速率，前者还含大量失败。

问：排查记录至少写什么？答：时间、请求ID/URL、实际错误、相关日志/指标、假设、验证操作、结果；改动前留基线，避免同时改三个参数。

## 精选参考

[Google SRE Monitoring](https://sre.google/sre-book/monitoring-distributed-systems/) 只先读延迟、流量、错误、饱和度四个信号；不需要复刻Google监控栈。
