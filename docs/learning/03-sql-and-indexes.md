# 03 索引：少找数据，也要付维护成本

## 问题与解释

给订单建 `(user_id, created_at, id)`，类似先按人分组，再按时间与编号排目录。查询 user_id 后按时间取20条，可以沿相邻目录读取。只按 created_at 查全库，不能保证这个索引仍是最好的路；优化器也可能选择全表扫描或其他路径，必须看实际计划。

InnoDB 主键索引叶子存行；普通二级索引通常含主键用于定位行。查询字段不全在二级索引里，就可能再访问主键索引，这叫回表。覆盖索引把需要的投影放在索引中，可能减少回表，但体积变大，插入/更新要维护更多内容。`Using index condition` 表示索引条件下推，不等于覆盖。

`ORDER BY created_at DESC` 在时间相同的行之间没有稳定次序，加 id 作为平局规则。下一页游标带上 `(created_at,id)`，沿同一排序继续；OFFSET 则仍需处理并跳过前面的记录。游标适合继续翻页，不保证跳到任意页便宜；先找到第80万条作为游标也有成本。并发更新排序字段还会影响翻页，本实验查询数据固定，不能自动推导为快照分页。

## 源码入口

[商品/订单模型](../../src/concurrency_lab/models/commerce.py)、[分页查询](../../src/concurrency_lab/repositories/order_repository.py)、[009查询定义](../../src/concurrency_lab/experiments/scale/queries.py)、[009原始报告](../experiments/009-scale-comprehensive-lab/report.md)。先读 SQL 的 WHERE/ORDER/SELECT，再看索引，不从索引名字猜性能。

## 动手操作

运行只读证据检查，不重新造百万行：

```text
uv run python scripts/verify_index_lab.py --verify-only
uv run python scripts/verify_scale_lab.py
```

在 `/scale-lab` 选择同一百万数据记录，依次比较 user_projection、OFFSET、游标的基线/联合/覆盖阶段；确认 SQL、参数、排序和行数，再看 P50。Navicat/DBeaver 的连接与计划操作见[数据规模指南](../guides/scale-lab.md)，不要在历史表上手动加删索引。

## 预期现象

历史009记录中，覆盖阶段普通表深页 P50 为138.449ms，已知游标4.694ms；这是指定环境/样本的事实，不能承诺你机器同值。两者输出页有校验，游标定位另计。分区裁剪了 p3，也不保证比分区前快：该范围查询覆盖阶段普通表30.552ms、分区表42.982ms。

计划中的 estimated rows 是估算；actual rows/loops 是执行器报告，不是磁盘物理读次数。某些 skip scan 的汇总字段未知时，要看原始 TREE，不能把 null 填0。

## 反例

“索引越多越快”忽略写入和空间成本；“百万行必须分库分表”忽略行宽、索引、工作集、负载与硬件。Buffer Pool 缓存数据页，同样 SQL 冷热不同，单次测量不足以归因。

## 自测与答案

问：分页为什么额外带 id？答：时间可能重复，必须形成稳定全序。

问：查询只返回20条是否代表只读20行？答：不代表，过滤、排序、OFFSET 都可能处理更多；看计划和原始访问数据。

## 精选参考

[MySQL8.4 优化索引](https://dev.mysql.com/doc/refman/8.4/en/optimization-indexes.html)，按自己 SQL 查对应小节，不先读整本内核手册。
