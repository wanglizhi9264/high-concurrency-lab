# Feature Specification: Interactive System Visualization
**Feature Branch**: feature/003-interactive-system-visualization
**Created**: 2026-10-24
**Status**: Ready for planning
**Input**: 用户提供交互式系统可视化实验平台任务；复用001/002，五个页面，明确真实与模拟。

## User Scenarios & Testing *(mandatory)*
### User Story 1 - Understand the actual system (Priority: P1)
学习者在全景图选择组件，理解职责、实际调用路径、启动资源与源码，并采集一次真实健康请求再逐步回放。
**Why this priority**: 可验证的真实路径是教学基础。
**Independent Test**: 架构节点选择同步详情；真实健康追踪记录实际事件/状态，成功与失败均可回放。
**Acceptance Scenarios**:
1. **Given** 首页，**When** 点击MySQL/Redis等节点，**Then** 展示职责、输入输出、瓶颈、验证方式和仓库源码链接。
2. **Given** 真实追踪，**When** 触发请求，**Then** MySQL/Redis实际检查，显示HTTP状态、可信来源与观测区间；不可拆造未知的Router/网络/pool-wait耗时。
3. **Given** 有事件，**When** 单步/播放/暂停/重置，**Then** 状态与选中步骤同步，回放速度与原始耗时明确区分。
### User Story 2 - Explain indexing results (Priority: P1)
学习者选择三个数据规模和查询，比较002实测的基线/优化及其计划、空间、SQL/参数/原始文件。
**Why this priority**: 通过真实数据解释因果，不能用演示数值代替。
**Independent Test**: API数值与原始JSON一致，页面呈现百万数据和可展开计划树。
**Acceptance Scenarios**:
1. **Given** 百万订单/深OFFSET，**When** 比较，**Then** P50/P95/P99与002一致，计划可展开且节点可选，展示actual rows/loops/访问方式。
2. **Given** 数据损坏或未知ID/查询，**When** 请求，**Then** 返回有界错误，不读任意文件、不执行SQL、不泄漏路径/凭据。
### User Story 3 - Explore and learn (Priority: P2)
学习者调节连接池参数并回放排队/借还/超时；查看实验详情，形成观察-问题-假设-验证闭环。
**Why this priority**: 给后续并发实验提供可理解入口。
**Independent Test**: 确定性FIFO模拟测试、边界超时测试；页面始终标Simulation，真实池仅显示已采集快照。
**Acceptance Scenarios**:
1. **Given** 小池/多请求，**When** 运行模拟，**Then** 排队/释放/超时和参数变化一致；不会触发真实SQL或改池配置。
2. **Given** 实验列表，**When** 打开002详情，**Then** 展示目标、问题、假设、参数、现象、原始数据、解释与局限。
3. **Given** 任一页面，**When** API失败、加载或空数据，**Then** 可理解的状态和重试入口；浅色/深色与桌面布局可用。
### Edge Cases
- readiness当前使用engine.connect而非ORM Session：图中的Session明确标为已定义但本探针不经过，不伪造链路。
- engine/redis client创建是lazy，启动记录不等于远端连接建立。
- MySQL与Redis检查并发，span重叠不可求和；HTTP响应构造不等于已发送，浏览器收到响应单独用浏览器时钟记录。
- 002只有7次暖缓存单客户端样本，CPU/内存未采集；图表不得暗示并发性能。
- 组件切换/卸载释放图表/定时器；重复点击采集时防止请求竞态。
- SQL TREE存在科学计数与无actual节点，保留原文并正确表示未采集/未执行。

## Requirements *(mandatory)*
### Functional Requirements
- **FR-001**: MUST 使用Vue3/TS/Vite/Router/VueFlow/ECharts/ElementPlus，frontend独立目录；共享状态无实际需求不引入Pinia。
- **FR-002**: MUST 全景图缩放/拖动/选中，职责/输入输出/源码/瓶颈验证，区分Redis健康与未实现缓存及真实Session路径。
- **FR-003**: MUST Live Trace和Simulation明确区分；可采集真实健康事件并单步/播放/暂停/重置，无虚构分段计时。
- **FR-004**: MUST 读取验证过的002原始结果，三规模/六查询/两阶段P50/P95/P99/访问行数/大小/游标成本可比，原始SQL参数/计划文件可定位。
- **FR-005**: MUST TREE解析为可展开树并显示节点actual rows/loops/访问类型，保留原文与统计局限。
- **FR-006**: MUST 确定性FIFO池模拟（参数有界），借还/等待/超时/逐步回放；真实模式只展示实际快照，未采集项标未接入。
- **FR-007**: MUST 实验列表/详情与学习闭环；五类页面、侧栏、深浅色、loading/empty/error/retry状态。
- **FR-008**: MUST 新API使用Pydantic响应模型、只读allowlist文件/固定探针、schema验证、安全错误；不允许任意SQL/路径/数据库写入；原API不变。
- **FR-009**: MUST TS严格/ESLint/Prettier/Vitest/VTU与后端检查/集成测试，CI保留现有门禁并新增前端和E2E；真实浏览器读取002数据并触发一次成功真实健康请求后验收。
- **FR-010**: MUST 文档与真实截图/可验证页面、启动命令/API/观测可信边界/局限/未来Locust和Prometheus接入方案一致；独立分支PR合并。
### Key Entities
ArchitectureNode、SourceRef、ExperimentResult、PlanNode、TraceEvent（来源/时钟/置信类型）、PoolSnapshot、SimulationFrame。

## Success Criteria *(mandatory)*
### Measurable Outcomes
- **SC-001**: 五类页面及实验详情可访问，节点选择/主题/回放交互通过组件及浏览器验收。
- **SC-002**: 三规模×两阶段×六SQL正确读取，百万offset P50值与原JSON精确相同；计划树节点保留actual信息。
- **SC-003**: 真实健康采集成功200，失败503也有可信事件；任何未测区间无捏造精确值。
- **SC-004**: 模拟排队/超时确定性、无真实DB变更；所有安全/质量/回归/CI检查通过。
- **SC-005**: Spec/Plan/Tasks/Analyze/Converge可追溯，最终E2E和PR状态有实际证据。

## Assumptions
仅本地教学开发，不生产部署。Vite代理同源/API；无需CORS通配或登录。API源码引用只提供固定仓库相对路径和https链接，无磁盘绝对路径。无需重大架构澄清，Clarify跳过。新增实时快照仅池size/checkedout/overflow，等待队列/纯pool_wait未接入。
