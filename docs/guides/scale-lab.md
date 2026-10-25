# 大数据、索引与分区实验

009使用独立分析数据库，不修改002实验库、业务订单、库存或任务。应用启动不生成数据。查询表为相同列、相同复合主键的普通表/季度分区表；依次记录单列索引、联合索引、覆盖候选索引。写入另用三张空探针表。

在仓库根目录，先配置ignored `.env`中的实验实例连接（默认127.0.0.1:13306），安装frozen依赖并启动已有实验服务：

```powershell
uv sync --frozen
docker compose -f compose.yaml -f compose.experiments.yaml --profile experiments up -d --wait mysql-experiment
uv run python scripts/provision_scale_lab.py --project-name high-concurrency-lab
uv run python scripts/run_scale_experiment.py --orders 10000 --project-name high-concurrency-lab
uv run python scripts/run_scale_experiment.py --orders 1000000 --project-name high-concurrency-lab
uv run python scripts/verify_scale_lab.py
```

正式运行要求源码已提交；实验期间不修改源码、不并行测试/构建/其他压测。固定seed20261025，batch默认1000，预热1次/测量7次。batch范围1..10000，每个数据集/探针最多保留10000批次；过小组合在建表前拒绝，不丢弃样本凑结果。十万级也支持；千万级须同时传`--orders 10000000 --allow-ten-million`，本阶段普通启动与正常CI不依赖它。

新数据库固定为`concurrency_lab_exp_009_<规模>`；测试用test/test_partial/test_gate另隔离。只允许空库显式初始化。loading/已完成库、已有证据不重置或覆盖；部分DDL/批次失败保留现场。需要重复全流程时用新的Compose项目和独立端口/卷（或运行clean-clone验收），不要清库。MySQL命名锁避免同一目标并行演进；每步还核对ownership、revision、数据及上一阶段证据。

每个run独占目录保留seed、baseline、composite、covering、writes、database-result、resources.jsonl和最终result.json。子进程数据库结果与父进程资源合并分别写文件，不覆盖原始结果。阶段成功落盘后才改索引。失败阶段保留安全错误类型、SQL/参数、已完成样本和partial证据，不把未完成运行算0错误。

打开`/scale-lab`读取结果：同一SQL跨阶段/两布局比较；再选择阶段和表，查看SQL参数、TREE、JSON选中分区与using_index。`Using index condition`是ICP，不能当覆盖。OFFSET与keyset按created_atDESC,idDESC稳定排序，已知游标同页校验；随机定位游标另计成本。

注意模型限制：分区要求所有唯一键含created_at，且分区InnoDB不能保留业务FK。因此两表都使用PK(id,created_at)，不声明数据库保证id单列唯一。生成与流式读库校验id、SHA、月份与精确数量；它们是分析副本，不是把业务表直接分区的迁移建议。

写入比较是三张起始为空的表各提交50000行，批次轮换顺序，计execute+COMMIT；生成/散列/校验在SQL计时外。索引构建DDL时间另列。不能将此结果推断为百万存量更新写放大。

客户端查询ms含执行/取数与网络；EXPLAIN ANALYZE另一次执行带仪表开销。访问行数是访问算子输出×loops汇总，不是物理I/O，不能相加嵌套算子时间。串行SELECT/s不是并发HTTP RPS。空间/逐索引页为InnoDB分配估算，TABLE_ROWS不是精确COUNT。资源采样按自有runner/实验容器分别显示，CPU首次无基线为null，失败为未知；不是每条SQL资源归因。暖缓存仅指预热，无buffer pool清空或保证全表驻留。

实际数值见[009报告](../experiments/009-scale-comprehensive-lab/report.md)；分表评估结合真实目标、访问路径、写入、空间与运维成本，不由行数直接决定。测试：`SCALE_INTEGRATION=1 uv run pytest tests/integration/test_scale.py`（PowerShell先设置`$env:SCALE_INTEGRATION='1'`）。CI仅小规模，重型实验使用手动workflow。

## Navicat / DBeaver 逐项观察

新建MySQL连接：host `127.0.0.1`、port `13306`、user `lab_exp`，密码使用本机ignored.env的`EXP_MYSQL_PASSWORD`，不要把密码贴到文档或提交。先测试连接，再选择`concurrency_lab_exp_009_1000000`；这与3306的业务库不同。1045先核对用户/密码/端口对应同一实例，不要为排错重置已有数据库。

展开表→`scale_order`→列/约束/索引，对照`scale_order_partitioned`的相同PK和列；在分区页或DDL页查看`PARTITION BY RANGE COLUMNS(created_at)`与p1..p_future。已完成库处于covering阶段，历史baseline/composite结构从运行JSON的`statistics.show_create/indexes`查看，不删索引回放历史。

从`/scale-lab`选择运行、阶段、表、SQL案例，复制**实际SQL和该次参数**到SQL编辑器；替换命名绑定参数为记录中的字面量后执行`EXPLAIN ANALYZE SELECT ...`，再执行`EXPLAIN FORMAT=JSON SELECT ...`。DBeaver可选择语句后点“解释执行计划”，Navicat点“解释”；树形/图形界面与原始TREE/JSON一起阅读。ANALYZE实际执行查询，会有资源开销，正式测量时不要同时操作。

先观察用户投影的covering lookup，再观察OFFSET与keyset访问行数；时间范围看JSON partitions是否p3，id-only看是否所有分区。`Using index condition`不是覆盖索引。当前skip-scan通用解析汇总可能为未知，此时直接看原始TREE实际行数；JSON未给using_index不等于TREE没有覆盖访问。空间与TABLE_ROWS是统计估计，精确数量/SHA以实测校验为准。
