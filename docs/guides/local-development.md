# Local Development
Windows：安装 Docker Desktop/WSL2、Git、官方 uv；PowerShell 执行 README 命令。Windows Store python alias 不是可用解释器，使用 uv python install 3.12 和 uv run。Linux：安装 Docker Engine+Compose plugin、Git、uv；复制配置用 cp，SDD 的 PowerShell 脚本需 pwsh。
官方 uv 安装：https://docs.astral.sh/uv/getting-started/installation/ 。Spec Kit：uv tool install specify-cli==1.2.3；specify check。

## 环境与运行
.env.example 复制为 .env，设置三个随机本地密码，不提交。uv sync --frozen；docker compose up -d --wait；uv run alembic upgrade head；uv run uvicorn concurrency_lab.main:app --reload --host 127.0.0.1。
连接池参数在 .env.example 中集中展示；修改配置后重启应用。GET /health/live 不查外部依赖；/health/ready 同时检查真实数据库和 Redis。

## MySQL 调试
`docker compose exec mysql mysql -u lab -p concurrency_lab`，交互输入 MYSQL_PASSWORD。可执行 SELECT VERSION(); SHOW TABLES; EXPLAIN ANALYZE SELECT * FROM lab_marker; SHOW VARIABLES LIKE 'max_connections'; SHOW STATUS LIKE 'Threads_connected';。
不得将密码写在命令参数或提交到仓库。使用 root 仅用于数据库管理；应用用 lab 用户。

## Redis CLI
`docker compose exec redis sh` 后执行 `REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli`，然后 PING、INFO clients。配置密码来自容器环境；不在共享终端打印环境。

## 迁移与质量
README 列出 upgrade/current/downgrade/revision 命令；生成迁移后人工审核。回滚会删除 marker 数据。
`uv run python scripts/verify.py` 执行 Ruff、format、mypy、unit；`uv run pytest tests/integration` 额外验证真实依赖，需先迁移。CI integration 独立 job 使用同一 Compose。

## 常见问题
- daemon pipe 不存在：启动 Docker Desktop，等待 docker info 成功。
- 端口占用：调整 .env MYSQL_PORT/REDIS_PORT，再 docker compose up -d --wait。本机 Redis 已改为 16379。
- 修改密码后 MySQL 拒绝登录：现有 volume 保留旧账号，需用原凭据更改账户；仅可丢弃环境才删除 volume。
- ready 503：docker compose ps，分别检查服务健康和 .env；不把 health 输出改成异常堆栈。
- 池等待：检查 worker * (pool_size+max_overflow) 与 MySQL max_connections，先测量再调大。
- uv hardlink 警告：跨磁盘缓存会回退复制，可设置 UV_LINK_MODE=copy。
- 单元测试不应依赖本机 .env：显式 _env_file=None 并控制进程环境。
- Redis 当前无需持久化；MySQL volume 由 down 保留，禁止无意执行 down -v。
