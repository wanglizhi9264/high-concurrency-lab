<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { api } from '../api'
import type { TraceResponse, TraceEvent } from '../types'
import { usePlayback } from '../composables/usePlayback'
const mode = ref<'live' | 'simulation'>('live'),
  trace = ref<TraceResponse | null>(null),
  loading = ref(false),
  error = ref(''),
  browserMs = ref<number | null>(null)
const simulation: TraceResponse = {
  mode: 'simulation',
  http_status: 200,
  checks: { mysql: 'simulated', redis: 'simulated' },
  server_elapsed_ms: 0,
  limitations: ['Simulation预设事件，不访问数据库；示意时间不是实测性能。'],
  events: [
    '浏览器发送请求',
    'Router匹配（概念）',
    'Service调用（概念）',
    'MySQL与Redis检查（概念）',
    '响应返回（概念）',
  ].map((name, i) => ({
    id: `simulation-${i}`,
    name,
    component: ['client', 'router', 'service', 'mysql', 'router'][i]!,
    state: i === 4 ? 'success' : 'running',
    offset_ms: i * 100,
    source: 'teaching.preset',
    evidence: 'simulation',
    detail: '预设教学事件，无真实耗时或依赖结果。',
  })),
}
const currentTrace = computed(() => (mode.value === 'simulation' ? simulation : trace.value))
const events = computed<TraceEvent[]>(() => {
    if (mode.value === 'simulation') return simulation.events
    if (!trace.value) return []
    return [
      {
        id: 'browser-start',
        name: '浏览器发起fetch',
        component: 'client',
        state: 'running',
        offset_ms: 0,
        source: 'browser.performance.now',
        evidence: 'measured',
        detail: '浏览器调用fetch的时间点；不代表字节实际离开网卡的时间。',
      },
      ...trace.value.events,
      {
        id: 'browser-end',
        name: '浏览器读取响应完成',
        component: 'client',
        state: trace.value.http_status === 200 ? 'success' : 'failure',
        offset_ms: browserMs.value ?? 0,
        source: 'browser.performance.now',
        evidence: 'measured',
        detail: 'fetch与JSON读取完成的浏览器往返区间；不与服务端相对时钟拼接求差。',
      },
    ]
  }),
  length = computed(() => events.value.length)
const { index, playing, next, play, pause, reset } = usePlayback(length)
const selected = computed(() => events.value[index.value])
const components = ['client', 'router', 'service', 'mysql', 'redis']
const sourcePath = computed(() => {
  const name = selected.value?.component
  return name === 'client'
    ? 'frontend/src/views/TraceView.vue'
    : name === 'router'
      ? 'src/concurrency_lab/api/routes/visualization.py'
      : 'src/concurrency_lab/services/health.py'
})
function state(component: string) {
  let result = 'idle'
  for (const event of events.value.slice(0, index.value + 1))
    if (event.component === component) result = event.state
  return result
}
async function collect() {
  if (loading.value) return
  loading.value = true
  error.value = ''
  trace.value = null
  browserMs.value = null
  reset()
  const start = performance.now()
  try {
    trace.value = await api.trace()
    browserMs.value = performance.now() - start
  } catch (e) {
    error.value = e instanceof Error ? e.message : '请求失败'
  } finally {
    loading.value = false
  }
}
watch(mode, reset)
function choose(event: TraceEvent) {
  pause()
  index.value = events.value.findIndex((e) => e.id === event.id)
}
</script>
<template>
  <header class="page-heading">
    <div>
      <p class="eyebrow">02 / REQUEST LIFECYCLE</p>
      <h1>一条请求，哪些过程真的被看见？</h1>
      <p>先采集，再回放。动画速度不是请求的真实执行速度。</p>
    </div>
    <span class="badge" :class="mode === 'live' ? 'measured' : 'simulation'">{{
      mode === 'live' ? 'Live Trace · 实际埋点' : 'Simulation · 教学预设'
    }}</span>
  </header>
  <div class="toolbar panel">
    <el-radio-group v-model="mode">
      <el-radio-button value="live">真实追踪</el-radio-button
      ><el-radio-button value="simulation">教学模拟</el-radio-button> </el-radio-group
    ><el-button v-if="mode === 'live'" type="primary" :loading="loading" @click="collect">
      采集真实健康请求 </el-button
    ><span v-if="currentTrace"
      >HTTP <strong data-testid="http-status">{{ currentTrace.http_status }}</strong></span
    ><span v-if="mode === 'live' && browserMs !== null"
      >浏览器往返 {{ browserMs.toFixed(2) }} ms</span
    >
  </div>
  <div v-if="error" role="alert" class="state error">
    {{ error }}<el-button @click="collect">重试</el-button>
  </div>
  <div v-if="!currentTrace && !error" class="empty-hero">
    <span>↗</span>
    <h2>尚未采集真实请求</h2>
    <p>点击采集后，服务端将真实执行 SELECT 1 和 Redis PING。没有记录的区间不会凭空出现。</p>
  </div>
  <template v-if="currentTrace">
    <div class="request-lane">
      <div
        v-for="component in components"
        :key="component"
        class="lane-node"
        :class="state(component)"
      >
        <span class="dot" :class="state(component)"></span>{{ component
        }}<small>{{ state(component) === 'idle' ? '待回放' : state(component) }}</small>
      </div>
    </div>
    <div class="toolbar">
      <el-button :disabled="!events.length" @click="next">单步</el-button
      ><el-button @click="playing ? pause() : play()">{{ playing ? '暂停' : '播放' }}</el-button
      ><el-button @click="reset">重置回放</el-button
      ><span class="muted">{{ index + 1 }} / {{ events.length }} · 回放间隔650ms，仅用于教学</span>
    </div>
    <div class="trace-layout">
      <section class="panel">
        <button
          v-for="(event, i) in events"
          :key="event.id"
          class="event-row"
          :class="{ active: i === index, future: i > index }"
          @click="choose(event)"
        >
          <span class="step-index">{{ String(i + 1).padStart(2, '0') }}</span
          ><span
            ><strong>{{ event.name }}</strong
            ><small>{{ event.component }} · {{ event.state }}</small></span
          ><code
            >{{ event.source.startsWith('browser') ? 'browser' : 'server' }}
            {{ event.offset_ms.toFixed(2) }} ms</code
          >
        </button>
        <div v-if="mode === 'live'" class="flow-footer">
          浏览器已收到此响应；浏览器往返与服务端相对时钟分开显示。
        </div>
      </section>
      <aside v-if="selected" class="panel inspector">
        <span class="badge" :class="mode === 'live' ? 'measured' : 'simulation'">{{
          selected.evidence
        }}</span>
        <h2>{{ selected.name }}</h2>
        <p>{{ selected.detail }}</p>
        <dl>
          <dt>数据来源</dt>
          <dd>{{ selected.source }}</dd>
          <dt>时间基准</dt>
          <dd>
            {{
              mode === 'live'
                ? selected.source.startsWith('browser')
                  ? '浏览器fetch前后的相对ms'
                  : '服务端handler开始后的相对ms'
                : 'Simulation虚拟示意时间'
            }}
          </dd>
          <dt>不可推断的内容</dt>
          <dd>不能把这个区间当成纯网络、纯排队或独立SQL执行耗时。</dd>
        </dl>
        <a
          class="source-link"
          :href="`https://github.com/wanglizhi9264/high-concurrency-lab/blob/main/${sourcePath}`"
          target="_blank"
          rel="noreferrer"
          >↗ {{ sourcePath }}</a
        >
      </aside>
    </div>
    <div class="callout">
      <p v-for="note in currentTrace.limitations" :key="note">{{ note }}</p>
      <p v-if="mode === 'live'">
        服务端handler观测总区间 {{ currentTrace.server_elapsed_ms.toFixed(2) }} ms。Response
        prepared不是字节传输完成事件。
      </p>
    </div>
  </template>
</template>
