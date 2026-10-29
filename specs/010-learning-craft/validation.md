# Actual validation — 2026-10-29

环境：Windows / Python3.12.14 / frozen uv.lock；Docker Desktop 当时未运行，启动后只启动已有 high-concurrency-lab 的三个容器，保留现有卷/库，无 reset、迁移或重造数据。

| Command | Actual result |
|---|---|
| uv sync --frozen | Checked 69 packages，锁文件未改 |
| uv run python scripts/verify.py | Ruff通过；format通过；mypy84源码通过；110单元通过，5.83s |
| 新规则测试子集 | 23通过，TTL整数边界/不可变/抖动上下界/重试和终态 |
| CACHE_INTEGRATION=1 TASK_INTEGRATION=1 INVENTORY_INTEGRATION=1 BUSINESS_INTEGRATION=1 uv run pytest tests/integration/test_product_cache.py tests/integration/test_tasks.py tests/integration/test_inventory.py tests/integration/test_business.py -q | **36 passed in 40.15s**，真实MySQL/Redis、子进程崩溃恢复、死锁/取消、缓存fence及查询回归，无skip |
| uv run python scripts/verify_learning_docs.py | 八章、必需小节、本地文件链接全部通过 |
| uv run python scripts/verify_index_lab.py --verify-only | 002的1万/10万/100万历史证据全部accepted |
| uv run python scripts/verify_scale_lab.py | 009的1万/100万原始记录accepted |
| git diff --check | 通过；docs/experiments、migrations无变更 |

单元运行时保留已有 Starlette TestClient deprecation warning；未因此修改无关依赖。首次format检查发现教程Python代码块空行需格式化，格式化后全293文件检查通过。

无新性能测量，不宣称提升吞吐。前端无代码变更，本地未重复浏览器/前端全套，远端CI仍保留原quality/integration/frontend三个job。生产认证/发布/备份尚未实现，手册明确标识。

代码审查：两处规则提取保留原TTL随机范围和退避，所有事务/SQL/Lua/最终fence/ACK边界不变；任务新输入边界与现有ck_task_attempts一致。资料为独立中文解释，附原始链接，没有复制外部实现。GitHub实际结果见PR，不以本地结果代替。
