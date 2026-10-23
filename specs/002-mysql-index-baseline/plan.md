# Implementation Plan: MySQL Index Baseline
**Branch**: feature/002-mysql-index-baseline | **Date**: 2026-10-23 | **Spec**: [spec.md](spec.md)
## Summary
在专用 Compose MySQL 实例和严格 allowlist 实验库执行真实、顺序的基线/优化实验。生产应用无新路由。
## Technical Context
Python 3.12（声明 >=3.11）、现有 SQLAlchemy asyncio/asyncmy、Alembic、pytest，不增加运行时依赖。MySQL 8.4。CLI 入口 `uv run python -m concurrency_lab.experiments.index_baseline`。Windows/Linux，CI Ubuntu。
单客户端暖缓存只读查询，每 query 预热一次、默认重复 7 次；记录 wall ms 与服务器 actual iterator time。规模 10k/100k/1m，每订单两明细；每批 1000 订单，内存 O(batch+1000users+100products)。主键显式固定，自定义 Random(seed)，UTC naive DATETIME(6)，时间桶重复，金额 DECIMAL(12,2)。
## Constitution Check
设计前/后通过全部 11 原则：模块化 monolith，无 API；公共函数类型化；DDL 仅 Alembic；每批显式事务；不扩展 Redis；实测证据及未测资源 null；文档同步；不改依赖；unit/integration/CI；隔离实例+库名+所有权+不清空；按 SDD。宪章 foundation scope 是 001 范围描述，本 feature 的模型是实验结构，不是 commerce business logic，无需修改宪章。
## Project Structure
- src/concurrency_lab/models/commerce.py：四关系模型+实验元数据；复用 marker.Base。
- migrations/versions/0002_index_baseline.py：基线 schema 与 ownership；0003_query_indexes.py：实际索引新增，downgrade 先保证 FK 单列索引。
- src/concurrency_lab/experiments/{safety.py,dataset.py,queries.py,runner.py,index_baseline.py}：各有实际职责。
- compose.experiments.yaml：profile experiments，独立 MySQL、端口13306、volume。
- scripts/provision_index_lab.py：仅固定数据库 CREATE IF NOT EXISTS / GRANT，不 DROP。
- scripts/verify_index_lab.py：三个规模顺序 init/seed/baseline/optimize/compare 的验收；不会清空已存在库。
- tests/unit/test_index_baseline.py，tests/integration/test_index_baseline.py；CI 保留原 jobs，新增独立实验步骤。
- docs/experiments/002-mysql-index-baseline/{README.md,dbeaver.md,report.md,runs/}。
## Phase 0 Research
见 research.md。外键索引不能移除；非索引 email query 演示真实 scan，主键为稳定对照；用户查询基线已有 FK 索引。不使用 invisible index 冒充物理无索引空间/写入成本。
## Phase 1 Design
实验库仅允许 concurrency_lab_exp_002_10000/100000/1000000/test。命令首次 baseline 迁移只允许空库，后续要求 ownership purpose 精确匹配。绝不 DROP DATABASE/TRUNCATE/DELETE；seed 要求四表空和无 dataset row，首批写入 dataset status=loading，完成置 ready。失败保留 loading，不自动续传。配置使用独立 EXP_MYSQL_*，密码回退 MYSQL_PASSWORD 环境值，不在结果写 DSN/密码。
数据摘要 incremental SHA256，对 deterministic order/item payload 生成，与批次大小无关；每规模独立数据库，seed manifest 记录精确数量/时长/吞吐/连接数。固定1000用户100商品，两条明细，价格和 total 一致；无 ORM N+1。
基线 revision0002，优化 revision0003，CLI optimize 必须匹配既有 baseline JSON 的数据库、seed、digest、规模。runner 只接受固定查询 allowlist，无用户 SQL。基线与优化数据计数、摘要、参数相同；每次使用排他新建文件，禁止覆盖。文件命名 <database>-<phase>.json。
查询：PK id；orders user_id 过滤；user_id+created_at DESC,id DESC；全局深 OFFSET 与同页 keyset；users.email 过滤。页大小20，深度取80%订单量。keyset 通过单独一次 offset boundary 定位，成本独立记录；非真实随机跳页加速承诺。
EXPLAIN ANALYZE TREE 保存原文，解析每个 iterator actual rows/loops/time；扫描相关行数仅汇总明确 scan/lookup/range leaf 的 rows*loops，不能用 LIMIT根行数替代。全量查询结果只取 bounded LIMIT，避免加载所有数据。
大小来自 information_schema.TABLES 分配估算，补充 mysql.innodb_index_stats 的单索引页数若权限可得，否则标注不可用。ANALYZE TABLE 后采集 SHOW INDEX 元数据。CPU/内存未采集值 null，串行 wall throughput 不是并发 RPS。
## Complexity Tracking
新增实验 ownership/dataset 表是安全与追溯所需，不引入业务仓储、支付/库存或队列。
