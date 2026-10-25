import { createRouter, createWebHistory } from 'vue-router'
const ArchitectureView = () => import('../views/ArchitectureView.vue')
const TraceView = () => import('../views/TraceView.vue')
const DatabaseView = () => import('../views/DatabaseView.vue')
const PoolView = () => import('../views/PoolView.vue')
const ExperimentsView = () => import('../views/ExperimentsView.vue')
export const router = createRouter({
  history: createWebHistory(),
  routes: [
    {
      path: '/inventory-lab',
      component: () => import('../views/InventoryLabView.vue'),
      meta: { title: '库存事务与幂等' },
    },
    {
      path: '/cache-lab',
      component: () => import('../views/CacheLabView.vue'),
      meta: { title: 'Redis 缓存实验' },
    },
    {
      path: '/load-tests',
      component: () => import('../views/LoadTestView.vue'),
      meta: { title: '真实并发压测' },
    },
    {
      path: '/business',
      component: () => import('../views/BusinessQueryView.vue'),
      meta: { title: '真实业务查询' },
    },
    { path: '/', component: ArchitectureView, meta: { title: '系统全景图' } },
    { path: '/trace', component: TraceView, meta: { title: '请求生命周期' } },
    { path: '/database', component: DatabaseView, meta: { title: 'MySQL数据与索引' } },
    { path: '/pool', component: PoolView, meta: { title: '连接池实验室' } },
    { path: '/experiments', component: ExperimentsView, meta: { title: '实验记录与学习' } },
    {
      path: '/experiments/002-mysql-index-baseline',
      component: ExperimentsView,
      meta: { title: '002实验详情' },
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})
