# DBeaver 可视化操作教程

本教程是操作说明，未在本机安装/点击 DBeaver 验证。界面名称与图形计划能力可能随版本/edition变化。

## 1. 连接隔离实验 MySQL
Database → New Database Connection → MySQL；Host=127.0.0.1，Port=13306（重复环境使用对应端口）；Database=concurrency_lab_exp_002_10000（或100000/1000000），Username=lab_exp，Password 输入本地 .env 中 MYSQL_PASSWORD 或单独 EXP_MYSQL_PASSWORD。
首次连接按提示下载官方 MySQL JDBC 驱动，Test Connection 后 Finish。只在受控本地环境使用，凭据不要放入截图或提交仓库。若 JDBC 提示公钥认证，核对 MySQL驱动/TLS配置，按官方驱动要求为本地环境配置认证，不要修改生产连接设置来套用实验配置。
不要连接应用 concurrency_lab 数据库执行实验。SQL 编辑器先执行：
```sql
SELECT DATABASE(), VERSION();
SELECT * FROM experiment_ownership;
SELECT * FROM experiment_dataset;
SELECT * FROM alembic_version;
```
数据库必须为所选 allowlist 名称，ownership purpose 为 index-baseline-v1，status=ready。

## 2. 查看表结构、关联和约束
Database Navigator 展开连接 → Databases/schema → Tables；双击 lab_order，Properties 内查看 Columns、Foreign Keys、Constraints、Indexes 与 DDL。lab_order.user_id 引用 lab_user.id；lab_order_item 的 order_id/product_id 分别引用订单/商品。
选择关联表并打开 ER Diagram（版本不同可在表/Schema上下文菜单中选择 View Diagram），与 README ER 图核对。金额 DECIMAL(12,2)、时间 DATETIME(6)、quantity>0、price>=0 等 CHECK 也可以用 SHOW CREATE TABLE 核对。

## 3. 查看索引
```sql
SHOW CREATE TABLE lab_order;
SHOW INDEX FROM lab_order;
SHOW INDEX FROM lab_user;
```
基线0002有 ix_order_user，尚无 ix_order_user_time/ix_order_time/ix_user_email；优化0003新增这三项。
在 Properties → Indexes 中观察复合索引的列顺序和唯一性。执行迁移后刷新 Navigator（通常F5）再查看。不要用 DBeaver 编辑器直接创建/删除索引；DDL仍由 Alembic 执行和追踪。

## 4. 估计计划与实际计划分别查看
在 SQL Editor 选择查询，使用 Explain Execution Plan（常见快捷键 Ctrl+Shift+E）查看估计计划。检查 access type、key、estimated rows、filesort；按钮的普通 EXPLAIN不等于实际测量。
实际执行指标用 SQL Editor 执行下面的 EXPLAIN ANALYZE，注意它会真的跑查询：
```sql
EXPLAIN ANALYZE FORMAT=TREE
SELECT id, total FROM lab_order WHERE id=5000;

EXPLAIN ANALYZE FORMAT=TREE
SELECT id FROM lab_order WHERE user_id=500 ORDER BY id LIMIT 20;

EXPLAIN ANALYZE FORMAT=TREE
SELECT id,created_at FROM lab_order WHERE user_id=500
ORDER BY created_at DESC,id DESC LIMIT 20;

EXPLAIN ANALYZE FORMAT=TREE
SELECT id,created_at FROM lab_order
ORDER BY created_at DESC,id DESC LIMIT 20 OFFSET 8000;

EXPLAIN ANALYZE FORMAT=TREE
SELECT id FROM lab_user WHERE email='user0500@example.invalid';
```
10万/100万库把主键示例改为50000/500000，offset改为80000/800000，与原始JSON参数一致。
当前库已经优化；历史基线请阅读 runs/*-baseline.json，或在新隔离环境按 README完整执行。不要为“看基线”在当前库手工删索引。
复制 TREE 文本观察：Table scan、Index lookup、Covering index range scan、Sort 和 Limit/Offset。根节点rows=20不能解释为只扫描20行。时间包含子节点且多循环时为平均，不能累加。

## 5. 手工比较 OFFSET / 游标
先取得前一行边界（10k库）：
```sql
SELECT created_at,id FROM lab_order
ORDER BY created_at DESC,id DESC LIMIT 1 OFFSET 7999;
```
复制返回的时间和id，替换下面示例变量；变量必须来自该库，不可直接使用其他规模的游标：
```sql
SET @cursor_time = '2025-01-01 00:00:00'; -- 替换为实际返回值
SET @cursor_id = 1; -- 替换为实际返回值
EXPLAIN ANALYZE FORMAT=TREE
SELECT id,created_at FROM lab_order
WHERE created_at < @cursor_time
   OR (created_at=@cursor_time AND id<@cursor_id)
ORDER BY created_at DESC,id DESC LIMIT 20;
```
比较同页全部ID、扫描相关叶节点行数与时间。先定位游标也有成本，正式报告已独立记录。

## 6. 查看估算空间
```sql
ANALYZE TABLE lab_user,lab_product,lab_order,lab_order_item;
SELECT table_name,table_rows,data_length,index_length
FROM information_schema.tables WHERE table_schema=DATABASE();
SELECT table_name,index_name,stat_value AS pages
FROM mysql.innodb_index_stats
WHERE database_name=DATABASE() AND stat_name='size';
SELECT @@innodb_page_size;
```
页数乘页大小是近似分配空间；TABLE_ROWS是估计，验收数量请用 COUNT(*)。新索引增大空间，即使查询变快也有存储和写入维护成本。

官方参考：[Properties Editor](https://dbeaver.com/docs/dbeaver/Properties-Editor/)、[Indexes](https://dbeaver.com/docs/dbeaver/Creating-Indexes/)、[Query Execution Plan](https://dbeaver.com/docs/dbeaver/Query-Execution-Plan/)、[MySQL EXPLAIN](https://dev.mysql.com/doc/refman/8.4/en/explain.html)。
