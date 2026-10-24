<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { api } from '../api'
import type { TraceResponse, TraceEvent } from '../types'
import { usePlayback } from '../composables/usePlayback'
import ProbeWalkthrough from '../components/ProbeWalkthrough.vue'
import { probeScenarios, simulateProbe, type ProbeScenario } from '../lib/probeSimulation'
const mode = ref<'live' | 'simulation'>('live'),
  trace = ref<TraceResponse | null>(null),
  loading = ref(false),
  error = ref(''),
  browserMs = ref<number | null>(null)
const scenario = ref<ProbeScenario>('success')
const simulation = computed(() => simulateProbe(scenario.value))
const currentTrace = computed(() => (mode.value === 'simulation' ? simulation.value : trace.value))
const events = computed<TraceEvent[]>(() => {
    if (mode.value === 'simulation') return simulation.value.events
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
        detail:
          '发送 GET /api/v1/observability/health-trace，无请求体；经同源开发代理访问FastAPI。这里只是调用fetch的时间点，不代表字节离开网卡。',
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
const components = ['client', 'router', 'service']
const componentNames: Record<string, string> = {
  client: '浏览器',
  router: 'FastAPI 路由',
  service: '健康服务',
  mysql: 'MySQL',
  redis: 'Redis',
}
function stateLabel(value: string) {
  return (
    (
      {
        idle: '待回放',
        running: '执行中',
        success: '成功',
        failure: '失败',
        waiting: '等待',
      } as Record<string, string>
    )[value] ?? value
  )
}
const dependencies = ['mysql', 'redis']
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
watch([mode, scenario], reset)
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
    <el-radio-group v-model="mode" :disabled="loading">
      <el-radio-button value="live">真实追踪</el-radio-button
      ><el-radio-button value="simulation">教学模拟</el-radio-button> </el-radio-group
    ><el-button v-if="mode === 'live'" type="primary" :loading="loading" @click="collect">
      采集真实健康请求 </el-button
    ><span v-if="currentTrace"
      >HTTP <strong data-testid="http-status">{{ currentTrace.http_status }}</strong></span
    ><span v-if="mode === 'live' && browserMs !== null"
      >浏览器往返 {{ browserMs.toFixed(2) }} ms</span
    >
    <label v-if="mode === 'simulation'"
      >假设结果
      <select v-model="scenario" aria-label="选择探针结果场景">
        <option v-for="item in probeScenarios" :key="item.value" :value="item.value">
          {{ item.label }}
        </option>
      </select>
    </label>
  </div>
  <ProbeWalkthrough />
  <div v-if="error" role="alert" class="state error">
    {{ error }}
    <p>
      未取得可显示的探针记录：先检查前端、后端和代理是否运行。网络失败不等于 MySQL 或 Redis
      已被检查并失败；HTTP 503 的探针响应会在下方保留。
    </p>
    <el-button @click="collect">重试</el-button>
  </div>
  <div v-if="!currentTrace && !error" class="empty-hero">
    <span>↗</span>
    <h2>尚未采集真实请求</h2>
    <p>点击采集后，服务端将真实执行 SELECT 1 和 Redis PING。没有记录的区间不会凭空出现。</p>
  </div>
  <template v-if="currentTrace">
    <section class="panel probe-results" aria-label="本次探针结果">
      <div class="panel-heading">
        <h2>{{ mode === 'live' ? '这次请求的实际结果' : '假设场景的结果 · 非实测' }}</h2>
        <span class="badge" :class="currentTrace.http_status === 200 ? 'measured' : 'simulation'"
          >HTTP {{ currentTrace.http_status }}</span
        >
      </div>
      <div class="storage-pair">
        <article
          v-for="dependency in dependencies"
          :key="dependency"
          class="probe-result"
          :class="currentTrace.checks[dependency] === 'ok' ? 'success' : 'failure'"
        >
          <strong>{{ dependency === 'mysql' ? 'MySQL · SELECT 1' : 'Redis · PING' }}</strong
          ><span :data-testid="`check-${dependency}`">{{ currentTrace.checks[dependency] }}</span>
          <p>
            {{
              currentTrace.checks[dependency] === 'ok'
                ? '本次检查通过。'
                : '本次检查未通过；真实响应不公开异常原因。'
            }}
          </p>
        </article>
      </div>
      <p>
        {{
          currentTrace.http_status === 200
            ? '两个都 ok，因此返回 200。探针没有查询商品、用户或订单表。'
            : '至少一项 unavailable，因此返回 503。后端已响应，但依赖没有全部就绪。'
        }}
      </p>
      <p class="muted">这是本次完成结果；下面的节点颜色表示回放到哪一步，两者含义不同。</p>
      <details>
        <summary>
          查看本次完整响应 JSON（{{ mode === 'live' ? '实际服务端返回' : '教学预设' }}）
        </summary>
        <pre data-testid="trace-json">{{ JSON.stringify(currentTrace, null, 2) }}</pre>
      </details>
    </section>
    <div class="request-lane">
      <div
        v-for="component in components"
        :key="component"
        class="lane-node"
        :class="state(component)"
      >
        <span class="dot" :class="state(component)"></span>{{ componentNames[component]
        }}<small>{{ stateLabel(state(component)) }}</small>
      </div>
      <div class="dependency-branch" data-testid="parallel-probes">
        <span class="branch-caption">MySQL ∥ Redis · 并发探针</span>
        <div
          v-for="component in dependencies"
          :key="component"
          class="lane-node"
          :class="state(component)"
        >
          <span class="dot" :class="state(component)"></span>{{ componentNames[component] }}
          <small>{{ stateLabel(state(component)) }}</small>
        </div>
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
            ><small
              >{{ componentNames[event.component] ?? event.component }} ·
              {{ stateLabel(event.state) }}</small
            ></span
          ><code
            >{{
              mode === 'simulation'
                ? '教学步骤'
                : event.source.startsWith('browser')
                  ? 'browser'
                  : 'server'
            }}
            {{ mode === 'simulation' ? i + 1 : event.offset_ms.toFixed(2) + ' ms' }}</code
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
                : '只有步骤顺序，无性能计时'
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
