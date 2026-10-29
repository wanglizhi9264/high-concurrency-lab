# Quickstart

仓库根目录：`uv sync --frozen`，`uv run pytest tests/unit/test_learning_policies.py`，`uv run python scripts/verify_learning_docs.py`，`uv run python scripts/verify.py`。

真实服务先依照现有业务/库存/worker 指南检查 owned business_test 已 ready 且迁移0005，不清库。PowerShell 设置 `$env:CACHE_INTEGRATION='1'; $env:TASK_INTEGRATION='1'`，执行 `uv run pytest tests/integration/test_product_cache.py tests/integration/test_tasks.py`。预期零失败；没有服务不是通过，应保留待验收。

阅读从 [学习入口](../../docs/learning/README.md) 开始；小实验优先单个现有测试，不运行重型性能任务。原始002–009记录只读。
