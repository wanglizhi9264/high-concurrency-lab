# Health contract
GET /health/live -> 200 {"status":"alive"}，不查询依赖。
GET /health/ready -> 200 {"status":"ready","checks":{"mysql":"ok","redis":"ok"}}。
任一不可用 -> 503 {"status":"unavailable","checks":{"mysql":"ok|unavailable","redis":"ok|unavailable"}}（每个值是枚举，不是字面含竖线的字符串）。
默认两项检查并发，每个完整检查 2 秒预算，包括获取连接；无异常文本、凭据或主机详情。启动无需依赖在线。
