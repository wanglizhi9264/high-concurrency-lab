<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import * as echarts from 'echarts/core'
import type { EChartsOption } from 'echarts'
import { BarChart, LineChart } from 'echarts/charts'
import { GridComponent, LegendComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
echarts.use([BarChart, LineChart, GridComponent, LegendComponent, TooltipComponent, CanvasRenderer])
const props = defineProps<{ option: EChartsOption; ariaLabel?: string }>()
const element = ref<HTMLElement>()
let chart: ReturnType<typeof echarts.init> | undefined, observer: ResizeObserver | undefined
onMounted(() => {
  if (!element.value) return
  chart = echarts.init(element.value)
  chart.setOption(props.option)
  observer = new ResizeObserver(() => chart?.resize())
  observer.observe(element.value)
})
watch(
  () => props.option,
  (option) => chart?.setOption(option, true),
  { deep: true },
)
onUnmounted(() => {
  observer?.disconnect()
  chart?.dispose()
})
</script>
<template>
  <div
    ref="element"
    class="chart"
    role="img"
    :aria-label="props.ariaLabel ?? 'Baseline 与 Optimized 的真实指标对照图'"
  ></div>
</template>
