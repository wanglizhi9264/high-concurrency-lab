<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import type { EChartsOption } from 'echarts'
import AsyncState from '../components/AsyncState.vue'
import ChartPanel from '../components/ChartPanel.vue'
import PlanTree from '../components/PlanTree.vue'
import { useScaleLab } from '../composables/useScaleLab'
import { buildScalePlan } from '../lib/scalePlan'
import type { PhaseName, QueryName, TableName } from '../types/scaleExperiments'

const lab = useScaleLab()
const {
  catalogue,
  record,
  selectedId,
  phase,
  table,
  query,
  catalogueLoading,
  loading,
  catalogueError,
  error,
} = lab
onMounted(() => void lab.reloadCatalogue())
const phases: { value: PhaseName; label: string }[] = [
  { value: 'baseline', label: '单列索引基线' },
  { value: 'composite', label: '联合索引' },
  { value: 'covering', label: '覆盖候选索引' },
]
const tables: { value: TableName; label: string }[] = [
  { value: 'scale_order', label: '普通表 · 同复合主键' },
  { value: 'scale_order_partitioned', label: '季度分区表 · 同复合主键' },
]
const cases: { value: QueryName; label: string }[] = [
  { value: 'primary_key', label: '主键 + 日期控制' },
  { value: 'by_user', label: '单用户，按 ID' },
  { value: 'user_projection', label: '用户时间排序，投影金额/状态' },
  { value: 'offset', label: '深分页 OFFSET' },
  { value: 'keyset', label: '同页 Keyset 游标' },
  { value: 'time_range', label: '时间范围聚合（裁剪候选）' },
  { value: 'id_without_time', label: '仅 ID（不含分区时间）' },
]
const activePhase = computed(() => record.value?.phases.find((item) => item.phase === phase.value))
const activeTable = computed(() => activePhase.value?.tables[table.value])
const activeQuery = computed(() => activeTable.value?.queries[query.value])
const plan = computed(() =>
  activeQuery.value && record.value
    ? buildScalePlan(activeQuery.value, record.value.manifest.source.revision)
    : null,
)
const metric = ref<'p50_ms' | 'p95_ms' | 'p99_ms' | 'access_operator_rows'>('p50_ms')
const unit = computed(() =>
  metric.value === 'access_operator_rows' ? '访问算子输出行 × loops' : 'ms',
)
const comparison = computed(
  () =>
    record.value?.phases.flatMap((stage) =>
      tables.map((layout) => ({
        stage: stage.phase,
        label: layout.label,
        observation: stage.tables[layout.value].queries[query.value],
      })),
    ) ?? [],
)
const chart = computed<EChartsOption>(() => ({
  animation: false,
  color: ['#7964d9', '#379c9a'],
  legend: {},
  grid: { left: 90, right: 25, top: 45, bottom: 45 },
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'category', data: phases.map((p) => p.label) },
  yAxis: { type: 'value', name: unit.value, min: 0 },
  series: tables.map((layout) => ({
    name: layout.label,
    type: 'bar',
    data:
      record.value?.phases.map(
        (stage) => stage.tables[layout.value].queries[query.value][metric.value],
      ) ?? [],
  })),
}))
const scopes = computed(() => [
  ...new Set(record.value?.resources.map((point) => point.scope) ?? []),
])
const resourceScope = ref(''),
  resourceMetric = ref<'cpu_percent' | 'memory_bytes'>('cpu_percent')
watch(scopes, (value) => {
  resourceScope.value = value[0] ?? ''
})
const resources = computed(
  () => record.value?.resources.filter((point) => point.scope === resourceScope.value) ?? [],
)
const resourceChart = computed<EChartsOption>(() => ({
  animation: false,
  grid: { left: 80, right: 30, top: 40, bottom: 45 },
  tooltip: { trigger: 'axis' },
  xAxis: { type: 'value', name: '实际实验起点后 / s' },
  yAxis: {
    type: 'value',
    name: resourceMetric.value === 'cpu_percent' ? '%（该作用域）' : 'MiB（该作用域）',
    min: 0,
  },
  series: [
    {
      type: 'line',
      smooth: false,
      connectNulls: false,
      showSymbol: true,
      data: resources.value.map((point) => [
        point.elapsed_s,
        point[resourceMetric.value] == null
          ? null
          : resourceMetric.value === 'memory_bytes'
            ? point.memory_bytes! / 1048576
            : point.cpu_percent,
      ]),
    },
  ],
}))
const number = (value: number | null | undefined) =>
  value == null ? '未知 / 未采集' : value.toLocaleString(undefined, { maximumFractionDigits: 4 })
const source = (path: string) =>
  `https://github.com/wanglizhi9264/high-concurrency-lab/blob/main/${path}`
</script>
<template>
  <header class="page-heading">
    <div>
      <p class="eyebrow">09 / SCALE, INDEX & PARTITION</p>
      <h1>索引减少了什么，又付出了什么？</h1>
      <p>
        真实数据、三阶段索引、同主键分区对照。原始
        SQL、执行计划、批次提交和空间观测保留在同一条证据链。
      </p>
    </div>
    <span class="badge measured">Recorded · 历史真实实验</span>
  </header>
  <section class="panel section-space">
    <h2>选择已完成记录</h2>
    <p>
      这里只读结果，不从 HTTP
      启动生成、改索引或压测。普通启动不依赖百万行；千万级是显式扩展，不是前置条件。
    </p>
    <AsyncState
      :loading="catalogueLoading"
      :error="catalogueError"
      :empty="catalogue.length === 0"
      @retry="lab.reloadCatalogue"
      ><div class="toolbar">
        <label
          >实验运行<select v-model="selectedId" aria-label="009 实验运行">
            <option v-for="run in catalogue" :key="run.manifest.id" :value="run.manifest.id">
              {{ run.manifest.order_count.toLocaleString() }} 行 / {{ run.manifest.id }}
            </option>
          </select></label
        ><button @click="lab.reloadCatalogue">刷新目录</button>
      </div></AsyncState
    >
  </section>
  <AsyncState :loading="loading" :error="error" :empty="!record" @retry="lab.reloadRecord">
    <template v-if="record">
      <section class="panel section-space" data-testid="scale-identity">
        <h2>数据与边界</h2>
        <p>
          {{ record.manifest.database }} · 每张查询表
          {{ record.manifest.order_count.toLocaleString() }} 行 · seed {{ record.manifest.seed }} ·
          batch {{ record.manifest.batch_size }} · 并发 1
        </p>
        <p>
          {{ record.manifest.started_at }} → {{ record.manifest.finished_at }} · 全流程
          {{ number(record.manifest.duration_seconds) }} s
        </p>
        <p>
          两张表均为 <code>PRIMARY KEY(id,created_at)</code> 的分析副本，无业务外键；单列 ID
          唯一由生成与流式读库校验，不是数据库独立 UNIQUE(id)。查询数据全程不改。
        </p>
        <p class="muted">
          已校验数据 SHA {{ record.phases[0]?.dataset.digest }}<br />源码
          {{ record.manifest.source.revision }} / SHA {{ record.manifest.source.sha256 }} ·
          {{
            record.manifest.source.sources_dirty ? '源码有未提交变更，请核对限制' : '源码检查点干净'
          }}
        </p>
      </section>
      <section class="panel section-space">
        <h2>1. 用同一个查询比较索引与分区</h2>
        <div class="toolbar">
          <label
            >SQL 案例<select v-model="query" aria-label="009 SQL 案例">
              <option v-for="item in cases" :key="item.value" :value="item.value">
                {{ item.label }}
              </option>
            </select></label
          ><label
            >图表指标<select v-model="metric" aria-label="009 对比指标">
              <option value="p50_ms">客户端 P50 ms</option>
              <option value="p95_ms">客户端 P95 ms</option>
              <option value="p99_ms">客户端 P99 ms</option>
              <option value="access_operator_rows">访问算子输出行 × loops</option>
            </select></label
          >
        </div>
        <ChartPanel :option="chart" aria-label="009 三阶段普通表与分区表实际对比" />
        <div class="table-scroll">
          <table data-testid="scale-comparison">
            <thead>
              <tr>
                <th>阶段 / 表</th>
                <th>P50 / P95 / P99 ms</th>
                <th>访问输出行 × loops</th>
                <th>实际覆盖</th>
                <th>优化器选中分区</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in comparison" :key="row.stage + row.label">
                <td>{{ row.stage }}<br />{{ row.label }}</td>
                <td>
                  {{ number(row.observation.p50_ms) }} / {{ number(row.observation.p95_ms) }} /
                  {{ number(row.observation.p99_ms) }}
                </td>
                <td>{{ number(row.observation.access_operator_rows) }}</td>
                <td>
                  {{ row.observation.covering_observed ? 'using_index=true' : '未观察到覆盖' }}
                </td>
                <td>
                  {{ row.observation.selected_partitions?.join(', ') ?? '未分区 / JSON 未报告' }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <p class="muted">
          客户端执行/取数含网络；暖缓存，预热 1 次，重复 {{ record.manifest.repeats }} 次。小样本
          P95/P99 不代表生产尾延迟。访问算子输出行不是物理
          I/O。表名或“覆盖候选”标签不证明优化器实际采用。
        </p>
      </section>
      <section v-if="activeQuery && activeTable && activePhase" class="panel section-space">
        <h2>2. 追到原始 SQL 和计划</h2>
        <div class="toolbar">
          <label
            >索引阶段<select v-model="phase" aria-label="009 索引阶段">
              <option v-for="item in phases" :key="item.value" :value="item.value">
                {{ item.label }}
              </option>
            </select></label
          ><label
            >布局<select v-model="table" aria-label="009 表布局">
              <option v-for="item in tables" :key="item.value" :value="item.value">
                {{ item.label }}
              </option>
            </select></label
          >
        </div>
        <pre data-testid="scale-sql">{{ activeQuery.sql }}</pre>
        <pre data-testid="scale-parameters">{{
          JSON.stringify(activeQuery.parameters, null, 2)
        }}</pre>
        <p data-testid="scale-partitions">
          选中分区：{{
            activeQuery.selected_partitions?.join(', ') ??
            (table === 'scale_order' ? '普通表未分区' : '未知 / JSON 未报告')
          }}；实际覆盖：{{ activeQuery.covering_observed ? 'using_index=true' : '未观察到' }}。Using
          index condition 是 ICP，不是覆盖证明。
        </p>
        <PlanTree v-if="plan" :plan="plan" />
        <details>
          <summary>原始 TREE / JSON 计划</summary>
          <pre data-testid="scale-tree">{{ activeQuery.tree }}</pre>
          <pre>{{ JSON.stringify(activeQuery.json_plan, null, 2) }}</pre>
        </details>
        <details>
          <summary>原始客户端样本与结果摘要</summary>
          <p>
            串行 SELECT / s {{ number(activeQuery.serial_selects_per_second) }}，不是并发 HTTP
            RPS。完成样本失败 {{ activeQuery.failures }} /
            {{ activeQuery.attempts }}，不包含未完成运行。
          </p>
          <pre data-testid="scale-samples">{{ JSON.stringify(activeQuery.client_ms_samples) }}</pre>
          <p>结果 SHA {{ activeQuery.result_sha256 }} · {{ activeQuery.result_count }} 行</p>
          <pre>{{ JSON.stringify(activeQuery.result_rows, null, 2) }}</pre>
        </details>
        <p>
          深页 OFFSET {{ activeTable.offset }}；本阶段随机定位游标另花
          {{ number(activeTable.cursor_lookup_ms) }} ms。OFFSET 与已知边界 keyset
          同页已校验，游标不是免费随机跳页。
        </p>
        <details>
          <summary>游标与同页 ID</summary>
          <pre>{{
            JSON.stringify({ cursor: activeTable.cursor, page_ids: activeTable.page_ids }, null, 2)
          }}</pre>
        </details>
      </section>
      <section v-if="activePhase" class="panel section-space">
        <h2>3. 看实际结构与空间代价</h2>
        <p>
          本阶段 {{ activePhase.revision }} · 统计采集
          {{ activePhase.statistics.observed_at ?? '未知' }}。COUNT/SHA
          是精确读库校验；TABLE_ROWS、cardinality、DATA_LENGTH、INDEX_LENGTH
          和页数是统计/分配估算，不是文件字节。
        </p>
        <div class="table-scroll">
          <table>
            <thead>
              <tr>
                <th>表</th>
                <th>估计行</th>
                <th>聚簇分配估算 bytes</th>
                <th>二级分配估算 bytes</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in activePhase.statistics.tables" :key="row.table_name">
                <td>{{ row.table_name }}</td>
                <td>{{ number(row.estimated_rows) }}</td>
                <td>{{ number(row.clustered_bytes_estimate) }}</td>
                <td>{{ number(row.secondary_bytes_estimate) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <details>
          <summary>所选表 SHOW CREATE / SHOW INDEX</summary>
          <pre>{{ activePhase.statistics.show_create?.[table] }}</pre>
          <pre>{{ JSON.stringify(activePhase.statistics.indexes?.[table], null, 2) }}</pre>
        </details>
        <details>
          <summary>分区和逐索引页统计</summary>
          <pre>{{ JSON.stringify(activePhase.statistics.partitions, null, 2) }}</pre>
          <pre>{{ JSON.stringify(activePhase.statistics.index_pages, null, 2) }}</pre>
          <p v-if="activePhase.statistics.index_pages_error">
            {{ activePhase.statistics.index_pages_error }}，未知值不填 0。
          </p>
        </details>
        <details>
          <summary>DDL 实际时间与实例环境</summary>
          <p>索引构建/迁移与查询和增量写入分开记录，包含客户端往返与隐式 DDL 提交。</p>
          <pre>{{ JSON.stringify(record.migrations, null, 2) }}</pre>
          <pre>{{
            JSON.stringify(
              {
                environment: activePhase.environment,
                before: activePhase.mysql_before,
                after: activePhase.mysql_after,
              },
              null,
              2,
            )
          }}</pre>
        </details>
      </section>
      <section class="panel section-space">
        <h2>4. 索引维护的写入成本</h2>
        <p>
          三张预建索引、起始为空的探针表，各提交相同
          {{ record.writes.rows_per_probe.toLocaleString() }}
          行，按批轮换表顺序；查询表不追加。这里只说明空表起始增量写入，不推断百万存量写放大。
        </p>
        <div class="table-scroll">
          <table data-testid="scale-writes">
            <thead>
              <tr>
                <th>布局</th>
                <th>已提交行</th>
                <th>INSERT + COMMIT ms</th>
                <th>行 / SQL计时秒</th>
                <th>批次 P50 / P95 / P99 ms</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(probe, name) in record.writes.probes" :key="name">
                <td>{{ name }}</td>
                <td>{{ probe.identity.count.toLocaleString() }}</td>
                <td>{{ number(probe.total_execute_commit_ms) }}</td>
                <td>{{ number(probe.rows_per_sql_second) }}</td>
                <td>
                  {{ number(probe.p50_batch_ms) }} / {{ number(probe.p95_batch_ms) }} /
                  {{ number(probe.p99_batch_ms) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <details>
          <summary>原始批次、执行顺序、写后结构与空间</summary>
          <pre>{{ JSON.stringify(record.writes, null, 2) }}</pre>
        </details>
        <p class="muted">
          生成、散列与读回校验不在批次 INSERT+COMMIT 计时内；共享缓存、执行先后等影响仍存在。
        </p>
      </section>
      <section class="panel section-space">
        <h2>5. 资源观测不能混用作用域</h2>
        <div class="toolbar">
          <label
            >实际作用域<select v-model="resourceScope" aria-label="009 资源作用域">
              <option v-for="scope in scopes" :key="scope" :value="scope">{{ scope }}</option>
            </select></label
          ><label
            >资源<select v-model="resourceMetric">
              <option value="cpu_percent">CPU %</option>
              <option value="memory_bytes">内存 MiB</option>
            </select></label
          >
        </div>
        <ChartPanel
          v-if="resources.length"
          :option="resourceChart"
          aria-label="009 所选作用域原始资源采样，未知点留空"
        />
        <p v-else class="state">该作用域没有采样，保留未知。</p>
        <p>
          psutil 是自有 runner 进程树，CPU 首次没有区间基线；Docker 是实验 MySQL 容器/VM 口径，CPU
          可以超过 100%，内存是 Docker 输出的分配估算。采样不是每条 SQL 的资源归因。
        </p>
        <details>
          <summary>原始资源点</summary>
          <pre>{{ JSON.stringify(resources, null, 2) }}</pre>
        </details>
      </section>
      <section class="panel section-space">
        <h2>结论必须附带条件</h2>
        <ul>
          <li v-for="limit in record.limitations" :key="limit">{{ limit }}</li>
        </ul>
        <p>
          分区只对部分谓词有效，不取代合适索引。是否需要分表还涉及容量目标、路由、全局唯一、跨片事务、JOIN
          和再平衡，不能只按行数决定。
        </p>
        <p>
          <a
            :href="source('docs/experiments/009-scale-comprehensive-lab/report.md')"
            target="_blank"
            rel="noreferrer"
            >实际综合报告</a
          >
          ·
          <a
            :href="source('docs/architecture/decisions/0007-scale-partition-comparison.md')"
            target="_blank"
            rel="noreferrer"
            >分析模型与分区 ADR</a
          >
          ·
          <a :href="source('docs/guides/clean-clone.md')" target="_blank" rel="noreferrer"
            >干净克隆端到端验收</a
          >
        </p>
      </section>
    </template>
  </AsyncState>
  <section class="panel section-space">
    <h2>独立触发重型实验</h2>
    <pre>
uv run python scripts/provision_scale_lab.py --project-name high-concurrency-lab
uv run python scripts/run_scale_experiment.py --orders 10000
uv run python scripts/run_scale_experiment.py --orders 1000000</pre>
    <p>
      仅在独立 owned 009
      数据库执行，先保存基线再改索引；不清理旧数据，已完成目标拒绝覆盖。正式实验期间不同时跑测试、构建或其他负载。千万级还需
      --allow-ten-million。
    </p>
  </section>
</template>
<style scoped>
select,
button {
  padding: 9px 12px;
  border: 1px solid var(--border);
  border-radius: 7px;
  background: var(--panel);
  color: var(--text);
  font: inherit;
  max-width: 100%;
}
select {
  min-width: 170px;
}
label {
  display: grid;
  gap: 7px;
  min-width: 0;
}
.toolbar {
  align-items: end;
}
.table-scroll {
  overflow: auto;
}
table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  text-align: left;
}
th,
td {
  padding: 12px 8px;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
}
pre {
  max-height: 440px;
  overflow: auto;
  padding: 14px;
  background: var(--bg);
}
details {
  margin: 16px 0;
}
summary {
  cursor: pointer;
}
.muted {
  overflow-wrap: anywhere;
}
</style>
