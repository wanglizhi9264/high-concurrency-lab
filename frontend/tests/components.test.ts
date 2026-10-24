import { describe, it, expect, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { defineComponent } from 'vue'
import ElementPlus from 'element-plus'
import ArchitectureView from '../src/views/ArchitectureView.vue'
import DatabaseView from '../src/views/DatabaseView.vue'
import AsyncState from '../src/components/AsyncState.vue'
import baseline from '../../docs/experiments/002-mysql-index-baseline/runs/concurrency_lab_exp_002_1000000-baseline.json'
import optimized from '../../docs/experiments/002-mysql-index-baseline/runs/concurrency_lab_exp_002_1000000-optimized.json'
vi.mock('../src/api', () => ({
  api: {
    architecture: async () => ({
      nodes: [
        {
          id: 'mysql',
          label: 'MySQL',
          status: 'connected',
          kind: '存储',
          responsibility: '真实数据库职责',
          input: 'SQL',
          output: '结果',
          bottleneck: '扫描',
          validation: 'EXPLAIN',
          source: { path: 'models.py', url: 'https://example.invalid' },
          x: 0,
          y: 0,
        },
      ],
      edges: [],
      startup: [],
      limitations: [],
    }),
    results: async () => ({ baseline, optimized, sources: [], limitations: [] }),
    plans: async () => ({
      sql: 'SELECT',
      parameters: {},
      raw_tree: '-> scan',
      tree: [],
      source: {},
      note: 'actual',
    }),
  },
}))
const flow = defineComponent({
  props: { nodes: { type: Array, required: true } },
  emits: ['node-click'],
  template:
    '<button v-for="node in nodes" :key="node.id" @click="$emit(\'node-click\',{node})">{{node.data.label}}</button>',
})
describe('component evidence and selection', () => {
  it('syncs selected architecture node and details', async () => {
    const wrapper = mount(ArchitectureView, {
      global: {
        plugins: [ElementPlus],
        stubs: { VueFlow: flow, Background: true, Controls: true, RouterLink: true },
      },
    })
    await flushPromises()
    await wrapper.get('button').trigger('click')
    expect(wrapper.text()).toContain('真实数据库职责')
    expect(wrapper.text()).toContain('models.py')
  })
  it('uses original 002 measurements in the comparison table', async () => {
    const wrapper = mount(DatabaseView, {
      global: { plugins: [ElementPlus], stubs: { ChartPanel: true, PlanTree: true } },
    })
    await flushPromises()
    expect(wrapper.get('[data-testid="baseline-p50"]').text()).toBe(
      baseline.queries.offset.p50_ms.toFixed(3),
    )
    expect(wrapper.get('[data-testid="optimized-p50"]').text()).toBe(
      optimized.queries.offset.p50_ms.toFixed(3),
    )
  })
  it('exposes API error and retry states', async () => {
    const wrapper = mount(AsyncState, {
      props: { loading: false, error: 'API 503' },
      global: { plugins: [ElementPlus] },
    })
    expect(wrapper.get('[role="alert"]').text()).toContain('503')
    await wrapper.get('button').trigger('click')
    expect(wrapper.emitted('retry')).toHaveLength(1)
  })
})
