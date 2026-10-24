<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { EChartsOption } from 'echarts'
import { api } from '../api'
import { useRequest } from '../composables/useRequest'
import AsyncState from '../components/AsyncState.vue'
import ChartPanel from '../components/ChartPanel.vue'
import PlanTree from '../components/PlanTree.vue'
const scale = ref(1000000),
  query = ref('offset'),
  phase = ref('baseline')
const names: Record<string, string> = {
  primary_key: '主键查询',
  by_user: '按用户过滤',
  user_time: '用户 + 时间排序',
  offset: '深 OFFSET 分页',
  keyset: 'Keyset 游标分页',
  email: '邮箱过滤',
}
const { data, loading, error, reload } = useRequest(() => api.results(scale.value))
const {
  data: plan,
  loading: planLoading,
  error: planError,
  reload: reloadPlan,
} = useRequest(() => api.plans(scale.value, phase.value, query.value))
watch(scale, () => void reload())
watch([scale, query, phase], () => void reloadPlan())
const baseline = computed(() => data.value?.baseline.queries[query.value]),
  optimized = computed(() => data.value?.optimized.queries[query.value])
const option = computed<EChartsOption>(() => ({
  color: ['#9b9fba', '#7864d9'],
  tooltip: { trigger: 'axis', valueFormatter: (v) => `${Number(v).toFixed(3)} ms` },
  legend: { textStyle: { color: '#8990a5' } },
  grid: { left: 58, right: 30, bottom: 35, top: 40 },
  xAxis: { type: 'category', data: ['P50', 'P95', 'P99'], axisLabel: { color: '#8990a5' } },
  yAxis: {
    type: 'value',
    name: 'wall time / ms',
    axisLabel: { color: '#8990a5' },
    splitLine: { lineStyle: { color: '#ccd0dd', type: 'dashed', opacity: 0.3 } },
  },
  series: [
    {
      name: 'Baseline',
      type: 'bar',
      barMaxWidth: 52,
      data: baseline.value
        ? [baseline.value.p50_ms, baseline.value.p95_ms, baseline.value.p99_ms]
        : [],
    },
    {
      name: 'Optimized',
      type: 'bar',
      barMaxWidth: 52,
      data: optimized.value
        ? [optimized.value.p50_ms, optimized.value.p95_ms, optimized.value.p99_ms]
        : [],
    },
  ],
}))
const sizes = computed(() => {
  if (!data.value) return []
  return ['baseline', 'optimized'].map((phase) => {
    const record = phase === 'baseline' ? data.value!.baseline : data.value!.optimized
    const table = record.sizes.tables.find((t) => t.table_name === 'lab_order')
    return {
      phase,
      clustered: table ? (Number(table.clustered_bytes_estimate) / 1048576).toFixed(2) : '未采集',
      secondary: table ? (Number(table.secondary_bytes_estimate) / 1048576).toFixed(2) : '未采集',
      cursor: record.cursor_lookup_ms.toFixed(2),
    }
  })
})
</script>
<template>
  <header class="page-heading">
    <div>
      <p class="eyebrow">03 / MYSQL INDEX EXPLORER</p>
      <h1>不只看快多少，更看为什么。</h1>
      <p>真实002实验记录 · 相同数据与SQL，比较索引前后的工作量。</p>
    </div>
    <span class="badge measured">Recorded measurement · 2026-10-23</span>
  </header>
  <div class="toolbar panel">
    <label
      >订单规模
      <el-select v-model="scale" aria-label="订单规模" style="width: 140px"
        ><el-option
          v-for="value in [10000, 100000, 1000000]"
          :key="value"
          :value="value"
          :label="value.toLocaleString()" /></el-select></label
    ><label
      >SQL场景
      <el-select v-model="query" aria-label="SQL场景" style="width: 190px"
        ><el-option
          v-for="(name, key) in names"
          :key="key"
          :value="key"
          :label="name" /></el-select></label
    ><span class="muted">7 samples · warm cache · 1 client</span>
  </div>
  <AsyncState :loading="loading" :error="error" :empty="!data" @retry="reload">
    <div class="comparison-grid">
      <section class="panel">
        <div class="panel-heading">
          <h2>{{ names[query] }} · 延迟对照</h2>
          <span class="muted">客户端 wall ms</span>
        </div>
        <ChartPanel :option="option" />
        <table class="data-table">
          <thead>
            <tr>
              <th>方案</th>
              <th>P50</th>
              <th>P95</th>
              <th>P99</th>
              <th>访问节点行数</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Baseline</td>
              <td data-testid="baseline-p50">{{ baseline?.p50_ms.toFixed(3) }}</td>
              <td>{{ baseline?.p95_ms.toFixed(3) }}</td>
              <td>{{ baseline?.p99_ms.toFixed(3) }}</td>
              <td>{{ baseline?.access_operator_rows?.toLocaleString() ?? '未采集' }}</td>
            </tr>
            <tr>
              <td>Optimized</td>
              <td data-testid="optimized-p50">{{ optimized?.p50_ms.toFixed(3) }}</td>
              <td>{{ optimized?.p95_ms.toFixed(3) }}</td>
              <td>{{ optimized?.p99_ms.toFixed(3) }}</td>
              <td>{{ optimized?.access_operator_rows?.toLocaleString() ?? '未采集' }}</td>
            </tr>
          </tbody>
        </table>
      </section>
      <aside class="panel inspector">
        <p class="eyebrow">ASK WHY</p>
        <h2>20行结果，多少行工作？</h2>
        <p>
          沿执行计划追到底层访问算子，再检查是否出现
          Sort。新增索引既可能减少扫描，也可能提供稳定排序。
        </p>
        <div class="question">OFFSET仍要跳过前面的行；Keyset从已知边界开始。</div>
        <p>本实验为了比较同一深页，额外执行了一次游标定位。它的成本单独列在下方，不能隐去。</p>
        <a
          v-for="item in data?.sources"
          :key="item.path"
          :href="item.url"
          target="_blank"
          rel="noreferrer"
          class="source-link"
          >↗ {{ item.label }}</a
        >
      </aside>
    </div>
    <section class="panel section-space">
      <div class="panel-heading">
        <h2>执行计划 · 点进每一个算子</h2>
        <el-radio-group v-model="phase">
          <el-radio-button value="baseline">Baseline</el-radio-button
          ><el-radio-button value="optimized">Optimized</el-radio-button>
        </el-radio-group>
      </div>
      <AsyncState :loading="planLoading" :error="planError" :empty="!plan" @retry="reloadPlan">
        <template v-if="plan">
          <div class="sql-block">
            <code>{{ plan.sql }}</code>
            <pre>绑定参数 {{ JSON.stringify(plan.parameters, null, 2) }}</pre>
          </div>
          <PlanTree :plan="plan" />
        </template>
      </AsyncState>
    </section>
    <section class="panel section-space">
      <h2>收益之外：索引空间与定位成本</h2>
      <table class="data-table">
        <thead>
          <tr>
            <th>方案</th>
            <th>聚簇索引分配 / MiB</th>
            <th>二级索引分配 / MiB</th>
            <th>游标定位 / ms</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in sizes" :key="row.phase">
            <td>{{ row.phase }}</td>
            <td>{{ row.clustered }}</td>
            <td>{{ row.secondary }}</td>
            <td>{{ row.cursor }}</td>
          </tr>
        </tbody>
      </table>
      <p class="muted">空间为InnoDB页分配估算，不是精确物理文件大小。当前表：lab_order。</p>
      <details>
        <summary>查看原始环境与逐索引统计</summary>
        <pre>{{
          JSON.stringify(
            {
              environment: data?.baseline.environment,
              indexes: data?.optimized.sizes.individual_indexes,
            },
            null,
            2,
          )
        }}</pre>
      </details>
    </section>
    <div class="callout">
      <p v-for="note in data?.limitations" :key="note">{{ note }}</p>
    </div>
  </AsyncState>
</template>
