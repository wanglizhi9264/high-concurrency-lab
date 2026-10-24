# Implementation Plan: Interactive System Visualization
**Branch**: feature/003-interactive-system-visualization | **Date**:2026-10-24 | **Spec**:[spec.md](spec.md)
## Summary
Vue SPA和现有FastAPI模块化单体。五类页面；002保留不可变，后端allowlist校验后只读投影；health最小侵入埋点；池模拟纯前端确定性离散事件。
## Technical Context
Python3.12/现有依赖；Node24（CI22）+npm锁；Vue3/TypeScript strict/Vite/VueRouter/VueFlow/ECharts/ElementPlus。无Pinia：状态目前页面内/播放composable即可。测试Vitest+VTU、Playwright E2E、pytest/Ruff/mypy。端口backend18002、frontend5173；E2E frontend5174。无Schema迁移或依赖数据重生成。
## Constitution Check
前后设计检查11原则通过：单体+前端独立；Python类型化；无DDL/create_all；只读查询；Redis仅探针；真实指标/未测null；文档同步；npm锁/uv锁；全栈与真实E2E测试；trusted allowlist/固定SQL/无敏感Trace；严格SDD/PR。001 foundation范围视为历史范围，无新增商务逻辑。
## Project Structure
- src/concurrency_lab/schemas/visualization.py：API与原始002schema模型
- services/visualization.py：固定架构/实验目录、可信读取/计划树
- services/tracing.py：单请求perf_counter事件；services/health.py可选事件回调
- api/routes/visualization.py：只读DTO与健康trace/pool快照
- frontend/src/{api,types,components,composables,router,views}，App.vue/main.ts/style.css
- frontend/tests：Vitest组件/模型测试；frontend/e2e：Playwright真实页面+API
- docs/guides/visualization-platform.md，specs/003.../*；CI新增frontend job/E2E，Dockerfile包含可信实验JSON。
## Phase0 Research
见research.md；VueFlow node-click参数为{node,event}；图表mount/resize/dispose；Vite不替代vue-tsc；FastAPI只计handler/service/probe区间，不伪造router匹配/网络/纯排队时间。
## Phase1 Design
API /api/v1/architecture、/experiments、/experiments/{id}、/experiments/{id}/results?scale=...、/query-plans?scale=...&phase=...&query=...、/observability/health-trace、/observability/pool。仅固定002id、三个scale/两个phase/六查询；文件名代码生成并resolve containment，拒绝symlink逃逸；Pydantic校验schema_version/repeats/query keys/规模/phase/revision，错误503不返回内部路径。仓库相对路径链接，不返回任意服务器文件。读文件错误处理在Service，API无SQL。测试结果故障/未知ID/路径逃逸。
Live Trace事件从handler进入、service开始、两探针开始/完成、service完成、response准备（尚未发送），每事件offset_ms为同一个服务端时钟相对handler开始；探针span含连接获取+preping+SQL/PING+关闭，不细分。前端fetch前后记录browser round-trip，时钟不混合。旧health endpoint响应不变；trace失败响应503但保留可显示的Trace DTO。启动过程记录创建资源实际事件并说明lazy；真实pool快照QueuePool gauges仅瞬时值，等待长度/纯等待时间为null。
首页VueFlow固定布局真实health分支与虚线教学Session/缓存节点，选中右侧详情；后端提供启动过程。Trace页共享playback支持Live/Simulation，播放间隔是展示速度不是实际耗时。数据库页六查询/三规模对照ECharts，metric exact源自API，计划树按indent建立父子，ElTree选中展示raw actual nodes；文件引用指向GitHub不可变002源。
池模拟规则：所有请求t0到达，容量pool_size+overflow，FIFO、不抢占、固定SQL时长；事件驱动，完成与deadline同刻先归还/分配再判超时；参数有界≤50请求/≤20容量/≤10秒。展示的是容量槽位，不暗示预建真实连接。每帧保存slot/queue/completed/timeout，回放纯前端。真实模式仅轮询手动刷新池快照；不修改生产池配置。
界面：深色侧栏、浅色实验画布、紫/绿信号色，中文解释+英文组件名，明确DATA来源badge；支持dark和常见桌面。错误组件统一重试，不堆静态装饰指标。
## Complexity Tracking
无Pinia/分布式追踪/业务API。未来Locust导入与Prometheus snapshot走独立观测adapter/DTO，不把模拟数据接入真实查询。

## Learning clarity correction
在ArchitectureView顶部嵌入StorageLearning.vue。独立局部状态承载四个场景与逐步推进，蓝色MySQL/红色Redis卡片、当前步骤高亮、表格与键值内容、明确的实际健康路径并发说明；链接真实Trace与现有索引页。无后端/API/Schema变更。先更新Spec/Plan/Tasks/Analyze再实现，使用现有E2E验证场景切换和状态。

## Probe detail plan
新增只读ProbeGuide DTO和GET /api/v1/observability/probe-guide，读取当前Settings中数据库名及预算/池超时；不执行探针，不返回地址/用户/密码。ProbeWalkthrough组件用于Trace顶部详细说明和首页折叠说明：HTTP接口对照、完整路径、目标库/命令/结果和成功失败规则、可展开具体代码、源码与排障。Trace使用独立probeSimulation.ts生成无虚构耗时的分步预设，真实结果始终展示两个checks及原始响应；网络错误与HTTP503分开解释。所有故障教学纯前端，不停止容器。测试后端投影/秘密/两种单失败/真实预算超时、前端分支及真实浏览器成功和结构化503。
