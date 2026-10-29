# 源码阅读顺序

初次学习先读[中文八章手册](../learning/README.md)，它按问题解释源码，并附小实验与答案。以下清单用于回到具体实现。

1. `.specify/memory/constitution.md`与`specs/004...009`：先看每阶段目标、约束、实际验证，分清计划和已测证据。
2. `core/config.py`、`db/session.py`、`main.py`、`db/business.py`：配置、lifespan资源、一请求/一事务Session、pool和owned库。健康探针直接连接，不经过业务Session。
3. `models/commerce.py`和迁移0001–0003、`experiments/safety.py/dataset.py/index_baseline.py`：为什么002独立库、基线先保存、分批与稳定游标。
4. `api/routes/business.py`→`services/business_service.py`→`repositories/product_repository.py`/`order_repository.py`、`observability/recording.py`：一次真实请求实际执行什么SQL，acquire/execute/response/browser各测到哪里。
5. `scripts/run_load_test.py`、`benchmarks/locust/locustfile.py`、`experiments/load_recording.py/resource_sampling.py`：开始/完成/成功RPS、原始CSV、百分位、未知CPU和作用域。
6. `cache/products.py`与`services/product_cache.py`：Cache-Aside回填为什么要generation与lease双fence；命中、合并等待、降级、失效不是同一件事。
7. `domain/inventory.py`→`services/inventory_service.py`→`repositories/inventory_repository.py`：Scenario→Order锁序、条件库存更新、唯一键/指纹、1062后新事务、RR审计、1205/1213重试。
8. `services/tasks.py`→`workers/dispatcher.py/runtime.py`→`services/task_execution.py`→`cache/task_stream.py`：MySQL受理/outbox、Redis运输、领取lease、结果fence、最后ACK；为何崩溃耗时未知、failed保留并关联后继。
9. `experiments/scale/`、独立`migrations/scale/`、`scripts/run_scale_experiment.py`：不可变双表、三阶段索引、覆盖/分区真实计划、独立写探针、资源与源码检查点。
10. `schemas/scale_experiments.py`→`services/scale_results.py`与Vue`ScaleLabView.vue`：如何验证和展示已保存记录，而不在HTTP执行实验。最后读`verify_end_to_end.py`的隔离和逐步验收。

每一步配合相应`docs/guides/`跑小规模真实操作，再读SQL/Trace/原始结果。重点自己掌握：事务/隔离/唯一约束/幂等，索引前缀与覆盖、稳定排序/游标，缓存副本与权威数据，at-least-once和幂等效果，资源作用域、统计样本与因果限制。先理解已有边界，再扩展新Feature。
