# Tasks: Interactive System Visualization
Input spec/plan/research/data-model/contracts。测试用户明确要求。
## Phase1 Setup
- [X] T001 frontend/package.json/package-lock.json/tsconfig/vite与质量配置；依赖Analyze；标准锁定Vue生态与测试；验证npm ci。(FR-001/009)
## Phase2 Foundation
- [X] T002 tests/unit/test_visualization.py先编写读取/模型/安全/真实trace测试并确认失败；依赖T001；验证pytest。(FR-008/009)
- [X] T003 schemas/visualization.py、services/visualization.py、api/routes/visualization.py及main.py注册；依赖T002；标准可信读取/Pydantic/只读API；验证API测试。(FR-004/005/008)
## Phase3 US1 System and trace
- [X] T004 [US1] services/tracing.py、health.py最小埋点及startup/pool快照；依赖T003；标准真实事件无精确虚构，无旧API回归；验证timeout/failure和lifecycle测试。(FR-002/003)
- [X] T005 [US1] frontend/App.vue/router/api/types、ArchitectureView/TraceView及播放composable；依赖T004；标准图选择/源码/实际与模拟回放；验证VTU/浏览器。(FR-002/003/007)
## Phase4 US2 Data and plans
- [X] T006 [US2] DatabaseView、ChartPanel与PlanTree；依赖T005；标准三规模/六SQL/真实ECharts/ElTree/rawSQL参数；验证原JSON精确值和树节点。(FR-004/005)
## Phase5 US3 Pool and learning
- [X] T007 [US3] poolSimulation.ts、PoolView、ExperimentsView/Detail；依赖T006；标准FIFO/超时/借还/真实未采集/学习闭环；验证Vitest边界。(FR-006/007)
## Phase6 Validation
- [X] T008 frontend组件/API错误与数据测试、Playwright E2E、CI前端job/集成E2E；依赖T007；标准既有测试不变且真实端到端；验证全套检查。(FR-009)
- [X] T009 README/AGENTS/架构/观测指南与截图；依赖T008；标准启动/API/真实边界/未来扩展一致；验证本地实际页面。(FR-010)
- [X] T010 执行Converge，更新specs/003.../validation.md和任务、提交PR等待CI后经PR合并；依赖T009；标准所有SC有真实证据。(SC-001..005)
## Dependencies and strategy
顺序T001->T010；先可信API再交互，先单元/组件后真实浏览器。研究按官方Plan技能委派；实现顺序进行，浏览器QA与截图依赖真实服务。
## Parallel opportunities
API schema与前端类型可在合同稳定后并行编辑；本轮不委派实现。保留原quality/integration门禁，新增frontend检查；不修改002原始JSON。
