<script setup lang="ts">
import { computed, ref } from 'vue'
import { VueFlow } from '@vue-flow/core'
import { Background } from '@vue-flow/background'
import { Controls } from '@vue-flow/controls'
import { api } from '../api'
import { useRequest } from '../composables/useRequest'
import AsyncState from '../components/AsyncState.vue'
import StorageLearning from '../components/StorageLearning.vue'
import ProbeWalkthrough from '../components/ProbeWalkthrough.vue'
const { data, loading, error, reload } = useRequest(api.architecture)
const selectedId = ref('service'),
  showStartup = ref(false)
const selected = computed(() => data.value?.nodes.find((n) => n.id === selectedId.value))
const nodes = computed(
  () =>
    data.value?.nodes.map((n) => ({
      id: n.id,
      position: { x: n.x, y: n.y },
      data: { label: n.label },
      class: `architecture-node ${n.status} ${n.id === selectedId.value ? 'selected' : ''}`,
    })) ?? [],
)
const edges = computed(
  () =>
    data.value?.edges.map((e) => ({
      ...e,
      animated: false,
      style: {
        stroke: e.teaching ? '#9296a7' : '#8d79e8',
        strokeDasharray: e.teaching ? '6 6' : undefined,
      },
    })) ?? [],
)
function select({ node }: { node: { id: string } }) {
  selectedId.value = node.id
}
</script>
<template>
  <header class="page-heading">
    <div>
      <p class="eyebrow">01 / SYSTEM ATLAS</p>
      <h1>先看见系统，再深入原理。</h1>
      <p>点击一个组件，沿真实健康请求理解它的职责与边界。</p>
    </div>
    <span class="badge measured">实际代码拓扑</span>
  </header>
  <StorageLearning />
  <ProbeWalkthrough compact />
  <AsyncState :loading="loading" :error="error" :empty="!data" @retry="reload">
    <div class="architecture-layout">
      <section class="panel flow-panel">
        <div class="panel-heading">
          <h2>请求流向</h2>
          <div class="legend">实线 · 已接入 <span>虚线 · 教学 / 未实现</span></div>
        </div>
        <VueFlow
          :nodes="nodes"
          :edges="edges"
          fit-view-on-init
          :min-zoom="0.3"
          @node-click="select"
        >
          <Background pattern-color="#c8cbd3" :gap="22" /><Controls />
        </VueFlow>
        <div class="flow-footer">滚轮缩放 · 拖动画布 · 拖动节点 · 点击查看源码</div>
      </section>
      <aside v-if="selected" class="panel inspector">
        <span class="badge" :class="selected.status === 'connected' ? 'measured' : 'simulation'"
          >{{ selected.kind }} ·
          {{
            selected.status === 'connected'
              ? '已接入'
              : selected.status === 'teaching'
                ? '教学旁路'
                : '尚未实现'
          }}</span
        >
        <h2>{{ selected.label }}</h2>
        <p>{{ selected.responsibility }}</p>
        <dl>
          <dt>输入 → 输出</dt>
          <dd>{{ selected.input }} → {{ selected.output }}</dd>
          <dt>什么时候成为瓶颈？</dt>
          <dd>{{ selected.bottleneck }}</dd>
          <dt>如何验证？</dt>
          <dd>{{ selected.validation }}</dd>
        </dl>
        <a :href="selected.source.url" target="_blank" rel="noreferrer" class="source-link"
          >↗ {{ selected.source.path }}</a
        >
      </aside>
    </div>
    <div class="section-bar">
      <h2>启动与资源生命周期</h2>
      <el-button @click="showStartup = !showStartup">
        {{ showStartup ? '收起初始化过程' : '查看实际初始化记录' }}
      </el-button>
    </div>
    <div v-if="showStartup" class="panel startup">
      <div v-for="event in data?.startup" :key="event.id">
        <span class="dot success"></span><strong>{{ event.name }}</strong
        ><span>{{ event.offset_ms.toFixed(2) }} ms · {{ event.detail }}</span>
      </div>
    </div>
    <div class="callout">
      <p v-for="note in data?.limitations" :key="note">{{ note }}</p>
      <router-link to="/trace">执行一次真实健康请求 →</router-link>
    </div>
  </AsyncState>
</template>
