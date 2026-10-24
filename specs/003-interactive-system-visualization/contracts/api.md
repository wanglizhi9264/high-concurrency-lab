# API contract
GET /api/v1/architecture -> Architecture DTO，含nodes/edges/startup events（实测lazy创建）/limitations。
GET /api/v1/experiments -> ExperimentSummary[]；固定002。
GET /api/v1/experiments/002-mysql-index-baseline -> ExperimentDetail（学习闭环、源链接、局限）。
GET .../results?scale=10000|100000|1000000 -> baseline+optimized validated002 DTO，404未知id/422非法scale/503可信数据缺失损坏。
GET .../query-plans?scale=...&phase=baseline|optimized&query=primary_key|by_user|user_time|offset|keyset|email -> sql/parameters/raw_tree/tree/source。
GET /api/v1/observability/health-trace -> LiveTrace DTO，实际ready200或503；固定探针SELECT1/PING，无用户SQL。
GET /api/v1/observability/pool -> measured瞬时gauges；未采集等待为null。
旧/health/live与/health/ready不改变。只提供固定GitHub源码/结果链接，不支持服务器文件路径或SQL输入。Trace不包含配置、主机地址、密码或异常消息。
