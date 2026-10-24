# Research
官方资料checked2026-10-24（Plan只读研究子任务）。
- VueTS https://vuejs.org/guide/typescript/overview.html ：vue-tsc独立检查；Vite https://vite.dev/guide/ ，锁定npm依赖。
- VueFlow https://vueflow.dev/guide/vue-flow/events.html ：node-click单对象{node,event}；https://vueflow.dev/guide/node.html 。
- ECharts https://apache.github.io/echarts-handbook/en/concepts/chart-size/ ：明确容器高度、ResizeObserver和dispose。
- ElementPlus https://element-plus.org/en-US/component/tree.html ：node-key/highlight-current/node-click。
- FastAPI https://fastapi.tiangolo.com/tutorial/middleware/ ：call_next区间不可拆造router/network精确值。
- SQLAlchemy https://docs.sqlalchemy.org/en/20/core/events.html#sqlalchemy.events.PoolEvents.checkout ：checkout不是纯排队起点。
决策：直接记录handler/service和实际probe调用事件；startup lazy资源不冒充远端连接。健康实际用Engine不是Session，图中区分。Vue页面内状态+共享播放composable足够，不引入Pinia。前端同源Vite proxy避免通配CORS。Sites采用local-only既有仓库路径，无注册/部署。
