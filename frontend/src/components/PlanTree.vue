<script setup lang="ts">
import { ref, watch } from 'vue'
import type { QueryPlan, PlanNode } from '../types'
const props = defineProps<{ plan: QueryPlan }>()
const selected = ref<PlanNode | null>(null)
watch(
  () => props.plan,
  () => (selected.value = null),
)
</script>
<template>
  <div class="plan-layout">
    <div>
      <p class="eyebrow">EXECUTION PLAN · ACTUAL</p>
      <el-tree
        :data="plan.tree"
        node-key="id"
        default-expand-all
        highlight-current
        :expand-on-click-node="false"
        @node-click="(node: PlanNode) => (selected = node)"
      >
        <template #default="{ data }">
          <span class="tree-label" :title="data.label">{{ data.label }}</span>
        </template>
      </el-tree>
    </div>
    <div class="inspector">
      <template v-if="selected">
        <h3>算子详情</h3>
        <p>{{ selected.label }}</p>
        <dl v-if="selected.metrics">
          <dt>实际输出行数 / 每循环</dt>
          <dd>{{ selected.metrics.actual_rows_per_loop.toLocaleString() }}</dd>
          <dt>loops</dt>
          <dd>{{ selected.metrics.loops }}</dd>
          <dt>首行 / 整体迭代 ms</dt>
          <dd>{{ selected.metrics.first_row_ms }} / {{ selected.metrics.iterator_ms_per_loop }}</dd>
          <dt>访问节点行数</dt>
          <dd>{{ selected.metrics.access_rows ?? '非访问算子 / 未采集' }}</dd>
        </dl>
        <p v-else>此节点没有实际测量信息，可能未执行。</p> </template
      ><template v-else>
        <h3>选择一个执行节点</h3>
        <p>从 Limit 向下追到 Sort、Table scan 或 Index range scan，理解20行结果背后的工作量。</p>
      </template>
    </div>
  </div>
  <details>
    <summary>原始 EXPLAIN ANALYZE TREE</summary>
    <pre>{{ plan.raw_tree }}</pre>
  </details>
  <p class="muted">{{ plan.note }}</p>
</template>
