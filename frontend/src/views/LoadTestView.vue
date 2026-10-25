<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { EChartsOption } from 'echarts'
import AsyncState from '../components/AsyncState.vue'
import ChartPanel from '../components/ChartPanel.vue'
import { listBenchmarks, getBenchmark } from '../api/benchmarks'
import { useRequest } from '../composables/useRequest'
import { loadMetrics, loadSeries } from '../lib/loadSeries'
import type { LoadMetric, RecordedLoadRun } from '../types/benchmarks'

const { data: catalogue, loading, error, reload } = useRequest(listBenchmarks)
const firstId = ref(''),
  secondId = ref('')
const metric = ref<LoadMetric>('success_rps')
const first = useRequest(async () => (firstId.value ? getBenchmark(firstId.value) : null))
const second = useRequest(async () => (secondId.value ? getBenchmark(secondId.value) : null))
watch(firstId, () => void first.reload())
watch(secondId, () => void second.reload())
watch(catalogue, (records) => {
  if (!records?.length) return
  const baseline =
    records.find(
      (run) =>
        run.manifest.parameters.users === 100 &&
        run.manifest.parameters.pool_size === 5 &&
        run.manifest.parameters.task_rate === 1,
    ) ?? records[0]!
  firstId.value = baseline.manifest.id
  secondId.value =
    records.find(
      (run) =>
        run.manifest.parameters.users === baseline.manifest.parameters.users &&
        run.manifest.parameters.task_rate === baseline.manifest.parameters.task_rate &&
        run.manifest.parameters.pool_size !== baseline.manifest.parameters.pool_size,
    )?.manifest.id ??
    records.find((run) => run.manifest.id !== baseline.manifest.id)?.manifest.id ??
    ''
})
const runs = computed(() =>
  [first.data.value, second.data.value].filter((run): run is RecordedLoadRun => run !== null),
)
const parameterDifferences = computed(() => {
  if (runs.value.length !== 2) return []
  const [a, b] = runs.value as [RecordedLoadRun, RecordedLoadRun]
  const keys = ['users', 'seconds', 'pool_size', 'task_rate', 'spawn_rate', 'scenario'] as const
  const changed = keys
    .filter((key) => a.manifest.parameters[key] !== b.manifest.parameters[key])
    .map(String)
  if (a.manifest.dataset.digest !== b.manifest.dataset.digest) changed.push('dataset digest')
  return changed
})
const hasPoints = computed(() =>
  runs.value.some((run) => loadSeries(run, metric.value).some((point) => point[1] !== null)),
)
const option = computed<EChartsOption>(() => ({
  animation: false,
  color: ['#7964d9', '#379c9a'],
  legend: { textStyle: { color: '#8990a5' } },
  tooltip: {
    trigger: 'axis',
    valueFormatter: (value) =>
      value == null ? '未采集' : `${Number(value).toFixed(3)} ${loadMetrics[metric.value].unit}`,
  },
  grid: { left: 75, right: 30, bottom: 50, top: 45 },
  xAxis: { type: 'value', name: '各自实验起点后 / s', nameLocation: 'middle', nameGap: 28 },
  yAxis: { type: 'value', name: loadMetrics[metric.value].unit, min: 0 },
  series: runs.value.map((run, index) => ({
    type: 'line',
    name: `${index ? 'B' : 'A'} · ${run.manifest.id.slice(-8)}`,
    smooth: false,
    connectNulls: false,
    showSymbol: true,
    data: loadSeries(run, metric.value),
  })),
}))
function numeric(value: number | null | undefined, digits = 2) {
  return value == null ? '未采集' : value.toFixed(digits)
}
function successfulRps(run: RecordedLoadRun) {
  return (run.summary.requests - run.summary.failures) / run.manifest.duration_s
}
function utc(epoch: number) {
  return new Date(epoch * 1000).toISOString()
}
async function retryRuns() {
  await Promise.all([first.reload(), second.reload()])
}
</script>

<template>
  <header class="page-heading">
    <div>
      <p class="eyebrow">05 / REAL LOAD EXPERIMENTS</p>
      <h1>吞吐上升，成功的请求也增加了吗？</h1>
      <p>Locust 历史实测；每组使用独立单进程 API、真实 MySQL 查询和有界连接池。</p>
    </div>
    <span class="badge measured">Recorded · 历史实测</span>
  </header>
  <AsyncState :loading="loading" :error="error" :empty="!catalogue?.length" @retry="reload">
    <section class="panel toolbar">
      <label
        >实验 A<select v-model="firstId" aria-label="实验 A">
          <option v-for="run in catalogue" :key="run.manifest.id" :value="run.manifest.id">
            {{ run.manifest.parameters.users }} 用户 / 池 {{ run.manifest.parameters.pool_size }} /
            节奏 {{ run.manifest.parameters.task_rate }} · {{ run.manifest.id.slice(-8) }}
          </option>
        </select></label
      >
      <label
        >实验 B<select v-model="secondId" aria-label="实验 B">
          <option value="">仅查看 A</option>
          <option v-for="run in catalogue" :key="run.manifest.id" :value="run.manifest.id">
            {{ run.manifest.parameters.users }} 用户 / 池 {{ run.manifest.parameters.pool_size }} /
            节奏 {{ run.manifest.parameters.task_rate }} · {{ run.manifest.id.slice(-8) }}
          </option>
        </select></label
      >
    </section>
    <AsyncState
      :loading="first.loading.value || second.loading.value"
      :error="first.error.value || second.error.value"
      :empty="!runs.length"
      @retry="retryRuns"
    >
      <div class="callout">
        <p>
          参数差异：{{
            parameterDifferences.join('、') ||
            (runs.length === 2 ? '所列参数相同' : '当前只有单次实验')
          }}。多项变化时不能把差异只归因于池大小。
        </p>
        <p>
          目标用户数 ≠ 请求到达率。spawn_rate 是用户启动数/秒；task_rate
          是每用户每秒任务的闭环目标，每任务一条请求，变慢时实际吞吐会下降。
        </p>
      </div>
      <div class="load-comparison">
        <section v-for="(run, index) in runs" :key="run.manifest.id" class="panel section-space">
          <div class="panel-heading">
            <h2>
              {{ index ? 'B' : 'A' }} · {{ run.manifest.parameters.users }} 用户 / 池
              {{ run.manifest.parameters.pool_size }}
            </h2>
            <span class="badge" :class="run.summary.failures ? 'simulation' : 'measured'"
              >失败 {{ run.summary.failures }} / {{ run.summary.requests }}</span
            >
          </div>
          <p class="muted">
            {{ run.manifest.id }}<br />UTC {{ utc(run.manifest.start_epoch) }} →
            {{ utc(run.manifest.end_epoch) }}
          </p>
          <table class="data-table">
            <tbody>
              <tr>
                <td>实际窗口（含爬升 / 收尾）</td>
                <td>{{ run.manifest.duration_s.toFixed(3) }} s</td>
              </tr>
              <tr>
                <td>目标 / 观测用户峰值</td>
                <td>{{ run.manifest.parameters.users }} / {{ run.manifest.peak_users }}</td>
              </tr>
              <tr>
                <td>用户启动速率 / 闭环任务节奏</td>
                <td>
                  {{ run.manifest.parameters.spawn_rate }} users/s ·
                  {{ run.manifest.parameters.task_rate }} tasks/user/s
                </td>
              </tr>
              <tr>
                <td>完成 RPS（含失败）</td>
                <td data-testid="load-rps">{{ numeric(run.summary.completed_rps) }}</td>
              </tr>
              <tr>
                <td>客户端调用起点率 / 未完成调用</td>
                <td>
                  {{ numeric(run.summary.client_start_rps) }} calls/s /
                  {{ run.summary.uncompleted_client_calls ?? '未采集' }}
                </td>
              </tr>
              <tr>
                <td>成功 RPS</td>
                <td>{{ numeric(successfulRps(run)) }}</td>
              </tr>
              <tr>
                <td>错误率</td>
                <td class="error-text">{{ (run.summary.error_rate * 100).toFixed(2) }} %</td>
              </tr>
              <tr>
                <td>P50 / P95 / P99（所有完成请求）</td>
                <td>
                  {{ numeric(run.summary.p50_ms) }} / {{ numeric(run.summary.p95_ms) }} /
                  {{ numeric(run.summary.p99_ms) }} ms
                </td>
              </tr>
              <tr>
                <td>收到响应中的 SQL 尝试率</td>
                <td>{{ numeric(run.summary.observed_sql_attempts_per_s) }} spans/s</td>
              </tr>
              <tr>
                <td>SQL 观测覆盖率 / 未知响应数</td>
                <td>
                  {{ (run.summary.sql_response_coverage * 100).toFixed(2) }} % /
                  {{ run.summary.unknown_sql_responses }}
                </td>
              </tr>
              <tr>
                <td>HTTP 504 / 池超时 / 传输超时</td>
                <td>
                  {{ run.summary.http_504 }} / {{ run.summary.pool_timeouts }} /
                  {{ run.summary.transport_timeouts }}
                </td>
              </tr>
              <tr>
                <td>订单规模 / 数据摘要</td>
                <td>
                  {{ run.manifest.dataset.order_count }} ·
                  {{ String(run.manifest.dataset.digest).slice(0, 12) }}
                </td>
              </tr>
            </tbody>
          </table>
          <details>
            <summary>参数、环境、统计口径及原始 Locust 汇总</summary>
            <pre>{{
              JSON.stringify(
                {
                  manifest: run.manifest,
                  semantics: run.semantics,
                  locust_statistics: run.locust_statistics,
                },
                null,
                2,
              )
            }}</pre>
          </details>
          <a
            class="source-link"
            :href="`https://github.com/wanglizhi9264/high-concurrency-lab/blob/main/docs/experiments/005-real-load-testing/runs/${run.manifest.id}/result.json`"
            target="_blank"
            rel="noreferrer"
            >↗ 原始 result.json 与同目录 CSV / resources.jsonl</a
          >
        </section>
      </div>
      <section class="panel section-space">
        <div class="panel-heading">
          <h2>真实采样曲线</h2>
          <label
            >指标
            <select v-model="metric" aria-label="压测指标">
              <option v-for="(entry, key) in loadMetrics" :key="key" :value="key">
                {{ entry.label }}
              </option>
            </select></label
          >
        </div>
        <ChartPanel
          v-if="hasPoints"
          :option="option"
          :aria-label="`${loadMetrics[metric].label}，历史实测比较`"
        />
        <div v-else class="state">该指标没有可用采样，未补零或生成示意曲线。</div>
        <p class="muted">
          各次运行按自己的起点对齐。断点保留为未采集；曲线不平滑、不连接缺失值。实例 Questions
          增量包含监测 / 健康 / 事务语句，遇到计数或 Uptime 回退时留空。
        </p>
        <details>
          <summary>当前曲线原始采样点（秒、指标值）</summary>
          <pre data-testid="load-series">{{
            JSON.stringify(
              runs.map((run) => ({ id: run.manifest.id, points: loadSeries(run, metric) })),
              null,
              2,
            )
          }}</pre>
        </details>
      </section>
      <div class="callout">
        <p>
          连接池是瞬时快照，不等于纯排队长度。API / Locust 进程 CPU 与 Docker 容器 CPU
          口径不同，可超过 100%；RSS 合计可能重复计算共享页，Docker 内存由 CLI 舍入值换算。
        </p>
        <p>
          本平台为每个业务请求返回完整
          Trace，包含观测开销；短实验包含用户爬升和收尾，不能当成生产容量或可靠尾延迟结论。超时分类可能重叠，不能相加当作总失败数。
        </p>
        <p v-for="note in runs[0]?.limitations" :key="note">{{ note }}</p>
      </div>
    </AsyncState>
  </AsyncState>
</template>
<style scoped>
.load-comparison {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 20px;
}
select {
  color: var(--text);
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 8px;
  font: inherit;
  max-width: 100%;
}
pre {
  max-height: 400px;
  overflow: auto;
}
.data-table td {
  overflow-wrap: anywhere;
}
@media (max-width: 1150px) {
  .load-comparison {
    grid-template-columns: 1fr;
  }
}
</style>
