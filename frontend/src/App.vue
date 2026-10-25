<script setup lang="ts">
import { ref, watch } from 'vue'
const theme = ref(localStorage.getItem('lab-theme') === 'dark' ? 'dark' : 'light')
watch(
  theme,
  (value) => {
    document.documentElement.classList.toggle('dark', value === 'dark')
    localStorage.setItem('lab-theme', value)
  },
  { immediate: true },
)
const links = [
  { path: '/', number: '01', name: '系统全景图', description: 'SYSTEM ATLAS' },
  { path: '/trace', number: '02', name: '请求生命周期', description: 'LIVE TRACE' },
  { path: '/database', number: '03', name: '数据与索引', description: 'MYSQL EXPLORER' },
  { path: '/pool', number: '04', name: '连接池实验室', description: 'POOL LAB' },
  { path: '/experiments', number: '05', name: '实验记录与学习', description: 'NOTEBOOK' },
  { path: '/business', number: '06', name: '真实业务查询', description: 'BUSINESS TRACE' },
  { path: '/load-tests', number: '07', name: '真实并发压测', description: 'LOCUST EVIDENCE' },
  { path: '/cache-lab', number: '08', name: 'Redis 缓存实验', description: 'REAL CACHE-ASIDE' },
  {
    path: '/inventory-lab',
    number: '09',
    name: '库存事务与幂等',
    description: 'REAL TRANSACTIONS',
  },
  { path: '/tasks', number: '10', name: '可靠异步任务', description: 'DURABLE WORKER' },
  { path: '/scale-lab', number: '11', name: '大数据综合实验', description: 'SCALE & PARTITION' },
]
</script>
<template>
  <div class="app-shell">
    <aside class="sidebar">
      <router-link to="/" class="brand">
        <span class="brand-mark">C<span>↗</span></span>
        <div>Concurrency<span>LAB / 实验台</span></div>
      </router-link>
      <div class="sidebar-caption">从请求，到原理。</div>
      <nav>
        <router-link
          v-for="link in links"
          :key="link.path"
          :to="link.path"
          :title="link.name"
          :class="{
            current: link.path === '/' ? $route.path === '/' : $route.path.startsWith(link.path),
          }"
        >
          <span class="nav-number">{{ link.number }}</span
          ><span
            >{{ link.name }}<small>{{ link.description }}</small></span
          ><span class="nav-arrow">↗</span>
        </router-link>
      </nav>
      <div class="sidebar-bottom">
        <span class="badge simulation">LEARN BY EXPERIMENT</span>
        <p>真实测量有证据，<br />教学模拟有边界。</p>
        <a
          href="https://github.com/wanglizhi9264/high-concurrency-lab"
          target="_blank"
          rel="noreferrer"
          >GitHub / 查看工程 ↗</a
        >
      </div>
    </aside>
    <div class="main-shell">
      <div class="topbar">
        <span>HIGH CONCURRENCY LAB <b>/</b> {{ $route.meta.title }}</span>
        <div>
          <span class="local-tag">LOCAL · 实验环境</span
          ><button
            class="theme-toggle"
            :aria-label="theme === 'light' ? '切换深色模式' : '切换浅色模式'"
            @click="theme = theme === 'light' ? 'dark' : 'light'"
          >
            {{ theme === 'light' ? '◑ 深色' : '◐ 浅色' }}
          </button>
        </div>
      </div>
      <main><router-view /></main>
      <footer class="app-footer">
        观察现象 · 理解原因 · 用实验验证 <span>003 / Interactive system visualization</span>
      </footer>
    </div>
  </div>
</template>
