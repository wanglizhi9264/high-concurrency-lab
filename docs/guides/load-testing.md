# 真实并发压测操作指南

前提：Docker MySQL/Redis 健康，已按 [业务实验指南](business-lab.md) 初始化 `concurrency_lab_business` 的 10000 条订单。所有请求先验证数据库归属；不清空数据库，不接触002实验实例。

```powershell
uv sync --frozen
uv run python scripts/run_load_test.py --users 10 --seconds 15 --pool-size 5 --task-rate 1 --port 18110
uv run python scripts/run_load_test.py --users 50 --seconds 15 --pool-size 5 --task-rate 1 --port 18150
uv run python scripts/run_load_test.py --users 100 --seconds 15 --pool-size 5 --task-rate 1 --port 18100
uv run python scripts/run_load_test.py --users 500 --seconds 15 --pool-size 5 --task-rate 1 --port 18500
uv run python scripts/run_load_test.py --users 100 --seconds 15 --pool-size 1 --task-rate 1 --port 18101
uv run python scripts/run_load_test.py --users 100 --seconds 15 --pool-size 5 --task-rate 2 --port 18102
```

依次执行，停止其他压测和数据库测试。端口必须空闲，不能使用预览端口18002/5173。脚本只终止自己创建的进程。users只允许10/50/100/500，seconds为5..300，pool为1..50，task-rate为0.2..5。可通过 `--scenario hot|normal|deep|mixed` 固定请求类型，默认 mixed：50%商品1、30%随机商品、10%用户订单、10%全局深分页。

实际请求：`GET /api/v1/business/products/1`、`products/{1..100}`、`users/{1..1000}/orders?limit=20`、`orders?limit=20&offset=8000`。深分页按 `created_at DESC,id DESC` 稳定排序，查询真实 `lab_order`；商品查 `lab_product`。服务拥有一个 Session/读事务，Repository 发出固定绑定 SQL。每次归属检查也产生一条 SQL，计入收到的 SQL span。

打开前端 `/load-tests`，选择 A/B。先比较100用户、池5/池1，再比较100用户、池5、节奏1/2。界面列出参数差异、成功/失败、实际窗口、原始延迟和 SQL 观测覆盖率。下拉查看完成/成功/客户端调用率、池占用、连接数和进程/容器 CPU、内存；缺失值留空。Trace开销始终存在。

每个唯一运行目录包含 `starts.csv`（客户端调用起点）、`requests.csv`（完成回调）、原始 `locust_*.csv`、`window.json`、`resources.jsonl`、`result.json`。失败运行保留 `incomplete.json`，不会列为完整记录。日志被git忽略且不通过API暴露。`GET /api/v1/benchmarks` 列表，`/{id}` 读取单次完整记录，`GET /api/v1/observability/business-metrics` 是当前快照。

关键口径：users是模拟用户数，spawn-rate是用户启动速度，task-rate是闭环每用户节奏；请求慢时实际调用率会降低。完成RPS包含失败，成功RPS需扣除失败。错误率的分母是完成请求，未完成调用单列。P50/P95/P99使用原始完成响应毫秒值，不平均各秒分位数。SQL尝试率只覆盖收到的Trace，MySQL Questions增量包含整个实例活动，两者不能互换。

短实验含爬升与收尾，无法证明生产容量。CPU范围可能超过100%；API进程与Docker容器的CPU口径不同。RSS可能重复统计共享页，Docker内存为CLI舍入估算。采样、健康检查、完整Trace会改变被测系统。需要稳定尾延迟结论时另做更长、多次、隔离负载实验。

GitHub Actions 的 Manual performance experiment 仅手动触发，参数有界，使用一次性数据库，输出下载制品，不自动修改版本库或用性能阈值阻断普通CI。
