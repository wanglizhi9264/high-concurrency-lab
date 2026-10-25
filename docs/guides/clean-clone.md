# 干净克隆端到端验收

前置：Git、uv/Python3.12、Node/npm、Docker可用；Windows使用已安装Edge，Linux脚本安装Playwright Chromium。源码先提交。此流程不复制工作区、.env、.venv或node_modules；用`git clone --no-local`获取同一冻结提交，验证新工作区HEAD和初始git status。它验证干净安装/运行，不测GitHub下载速度。

历史原始证据归档含较深目录，脚本为**新克隆自身**设置`core.longpaths=true`，避免Windows Git的260字符限制；不修改用户全局Git配置。Windows手动克隆也可用`git clone -c core.longpaths=true <仓库URL>`。逐步脱敏`.log`只保留本地且被忽略，版本库保存步骤argv/exit code/耗时JSON及实际实验JSON/CSV/PNG，不提交运行日志或凭据。

```powershell
uv sync --frozen
uv run python scripts/verify_end_to_end.py
```

默认克隆位于仓库上级`.hcl-acceptance/e2e-<UTC>-<UUID>`；项目名固定为新生成的`hcl-e2e-009-<UUID>`。端口：MySQL15006、Redis15379、实验MySQL15306、API18004、短Locust18005、浏览器前端5175。全部必须空闲、互不相同且不占用开发默认端口；有冲突会拒绝，绝不停止占用者。可通过同名`--mysql-port`、`--redis-port`、`--experiment-port`、`--api-port`、`--load-port`、`--frontend-port`改为其他空闲端口。

每次新生成4个本地秘密写ignored.env，日志脱敏，不复制开发凭据。COMPOSE_PROJECT_NAME、连接端口、CONCURRENCY_LAB_ROOT与浏览器代理统一指向新克隆。provision_index_lab显式传新project，避免它的默认-p覆盖环境；业务provision/Locust继承相同作用域。脚本核对容器ID、卷和旧项目不重合；不调用旧acceptance_local.py，不使用down-v。

实际步骤包括：安装frozen依赖/npm ci；新项目依赖和显式迁移；business/business_test各10000订单并升0005；002新目录smoke与原记录verify-only；009新实例10000smoke；自有API监听归属+readiness；真实业务/Trace；10用户5秒Locust；cache/inventory/worker故障验收；同一商品缓存→新库存场景→paid订单→队列任务→独立worker→回执→库存审计；全质量/集成/前端/build；最后Playwright在独立端口启动自己的API和前端，禁止复用开发预览。

输出在`docs/experiments/009-scale-comprehensive-lab/end-to-end/e2e-.../`：逐步骤argv（秘密/本地路径脱敏）、UTC、真实耗时、exit code、日志、实际journey和原始JSON/CSV/截图归档。失败保留complete=false及现场；不将未执行步骤写成通过。旧002实例存在时前后核对精确数量/数据摘要/表CHECKSUM，旧项目容器/卷身份也核对。

结束仅停止本次拥有的API/worker/新Compose项目，保留容器、卷和新克隆以便审阅。旧预览与旧数据不停止、不重置。需要释放这些保留资源时由用户明确选择具体项目处理。新克隆内原有JSON/CSV若被改写会使验收失败；E2E生成的截图另归档，不覆盖原仓库历史截图。

千万级不在此流程运行；查看已保存百万记录与新10000smoke即可完成普通开发学习。最终实际运行编号、每步结果与已知限制在009综合报告中填写，未执行前不声称通过。
