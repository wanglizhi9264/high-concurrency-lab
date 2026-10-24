<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { BusinessTrace } from '../types/business'
const props = defineProps<{ trace: BusinessTrace }>()
const selectedId = ref('')
watch(
  () => props.trace.request_id,
  () => {
    selectedId.value = props.trace.spans[0]?.id ?? ''
  },
  { immediate: true },
)
const selected = computed(() => props.trace.spans.find((span) => span.id === selectedId.value))
const labels: Record<string, string> = {
  router: 'HTTP 路由',
  service: '业务服务',
  repository: '查询仓储',
  acquire: 'SQLAlchemy 获取连接',
  sql_execute_fetch: 'MySQL SQL + 取数',
  request_budget: '请求预算',
}
</script>
<template>
  <section class="panel section-space">
    <div class="panel-heading">
      <h2>真实调用链 · 点击区间查看 SQL 和源码</h2>
      <span class="badge measured">Live measured · ms</span>
    </div>
    <p class="muted">
      {{ trace.database }} · {{ trace.observed_at }} · Request ID {{ trace.request_id }}
    </p>
    <div class="trace-layout">
      <div>
        <button
          v-for="span in trace.spans"
          :key="span.id"
          class="event-row"
          :class="{ active: selectedId === span.id }"
          @click="selectedId = span.id"
        >
          <span
            ><strong>{{ labels[span.kind] ?? span.kind }} · {{ span.state }}</strong
            ><small>{{ span.name }}</small></span
          ><code>{{ span.duration_ms.toFixed(3) }} ms</code>
        </button>
      </div>
      <aside v-if="selected" class="panel inspector">
        <h3>{{ selected.name }}</h3>
        <p>
          从请求起点 {{ selected.start_ms.toFixed(3) }} ms 开始，区间
          {{ selected.duration_ms.toFixed(3) }} ms。父区间包含子区间，不能相加。
        </p>
        <p>{{ trace.definitions[selected.kind] ?? '该层实际调用区间，包含下层操作。' }}</p>
        <pre v-if="selected.sql" data-testid="business-sql">{{ selected.sql }}</pre>
        <pre v-if="selected.sql">
绑定参数 {{ JSON.stringify(selected.parameters, null, 2) }}
实际取得 {{ selected.result_count ?? '未完成' }} 行</pre>
        <a
          class="source-link"
          :href="`https://github.com/wanglizhi9264/high-concurrency-lab/blob/main/${selected.source}`"
          target="_blank"
          rel="noreferrer"
          >↗ {{ selected.source }}</a
        >
      </aside>
    </div>
    <details>
      <summary>池快照、指标口径与环境</summary>
      <pre>{{
        JSON.stringify(
          {
            before: trace.pool_before,
            after: trace.pool_after,
            before_offset_ms: trace.pool_before_offset_ms,
            after_offset_ms: trace.pool_after_offset_ms,
            definitions: trace.definitions,
            environment: trace.environment,
          },
          null,
          2,
        )
      }}</pre>
    </details>
  </section>
</template>
