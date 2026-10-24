<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { simulatePool } from '../composables/poolSimulation'
import { usePlayback } from '../composables/usePlayback'
import { useRequest } from '../composables/useRequest'
import { api } from '../api'
import AsyncState from '../components/AsyncState.vue'
const mode = ref<'simulation' | 'live'>('simulation'),
  parameters = reactive({ requests: 12, size: 2, overflow: 0, timeout: 1500, duration: 1000 })
const simulationError = ref('')
const applied = ref({ ...parameters })
const frames = ref(simulatePool(parameters)),
  length = computed(() => frames.value.length)
const { index, playing, next, play, pause, reset } = usePlayback(length)
const frame = computed(() => frames.value[index.value]!)
const { data: snapshot, loading, error, reload } = useRequest(api.pool)
function chooseFrame(value: number) {
  pause()
  index.value = value
}
function run() {
  try {
    const nextFrames = simulatePool({ ...parameters })
    reset()
    applied.value = { ...parameters }
    frames.value = nextFrames
    simulationError.value = ''
  } catch (error) {
    simulationError.value = error instanceof Error ? error.message : '模拟参数无效'
  }
}
</script>
<template>
  <header class="page-heading">
    <div>
      <p class="eyebrow">04 / CONNECTION POOL LAB</p>
      <h1>连接不够时，请求去了哪里？</h1>
      <p>用离散事件理解借出、归还、排队和超时，再与真实观测边界对照。</p>
    </div>
    <span class="badge" :class="mode === 'simulation' ? 'simulation' : 'measured'">{{
      mode === 'simulation' ? 'Simulation · 非真实性能指标' : 'Live snapshot · 瞬时观测'
    }}</span>
  </header>
  <div class="toolbar">
    <el-radio-group v-model="mode">
      <el-radio-button value="simulation">教学模拟</el-radio-button
      ><el-radio-button value="live">真实池快照</el-radio-button>
    </el-radio-group>
  </div>
  <template v-if="mode === 'simulation'">
    <div v-if="simulationError" role="alert" class="state error">{{ simulationError }}</div>
    <div class="pool-layout">
      <aside class="panel controls-panel">
        <h2>改变一个条件</h2>
        <label
          >并发请求数 <strong>{{ parameters.requests }}</strong
          ><el-slider
            v-model="parameters.requests"
            :min="1"
            :max="50"
            aria-label="并发请求数" /></label
        ><label
          >pool_size <strong>{{ parameters.size }}</strong
          ><el-slider v-model="parameters.size" :min="1" :max="10" /></label
        ><label
          >max_overflow <strong>{{ parameters.overflow }}</strong
          ><el-slider v-model="parameters.overflow" :min="0" :max="10" /></label
        ><label
          >pool_timeout / ms
          <el-input-number
            v-model="parameters.timeout"
            :min="100"
            :max="10000"
            :step="100" /></label
        ><label
          >SQL占用时长 / ms
          <el-input-number
            v-model="parameters.duration"
            :min="100"
            :max="10000"
            :step="100" /></label
        ><el-button type="primary" @click="run">应用参数并重新模拟</el-button>
        <p class="muted">调整参数后重新运行。此处不会修改真实池，也不会执行SQL。</p>
      </aside>
      <section class="panel">
        <div class="panel-heading">
          <h2>容量槽位</h2>
          <span class="badge simulation">虚拟时间 {{ frame.at }} ms</span>
        </div>
        <div class="pool-slots">
          <div
            v-for="(request, i) in frame.slots"
            :key="i"
            class="pool-slot"
            :class="{ occupied: request !== null, overflow: i >= applied.size }"
          >
            <small>{{ i >= applied.size ? 'overflow' : 'pool' }} #{{ i + 1 }}</small
            ><strong>{{ request === null ? '空闲' : `R${request}` }}</strong>
          </div>
        </div>
        <div class="queue-area">
          <h3>FIFO 等待队列 · {{ frame.waiting.length }}</h3>
          <span v-for="request in frame.waiting" :key="request" class="request-chip"
            >R{{ request }}</span
          >
          <p v-if="!frame.waiting.length" class="muted">没有等待请求</p>
        </div>
        <div class="pool-outcomes">
          <span class="success-text">已归还 {{ frame.completed.length }}</span
          ><span class="error-text">已超时 {{ frame.timedOut.length }}</span
          ><span>{{ frame.action }}{{ frame.request ? ` · R${frame.request}` : '' }}</span>
        </div>
        <div class="toolbar">
          <el-button @click="next">单步</el-button
          ><el-button @click="playing ? pause() : play()">{{ playing ? '暂停' : '播放' }}</el-button
          ><el-button @click="reset">重置</el-button
          ><span class="muted">{{ index + 1 }} / {{ frames.length }}</span>
        </div>
        <el-slider v-model="index" :min="0" :max="Math.max(1, frames.length - 1)" @input="pause" />
        <div class="event-log">
          <button
            v-for="(entry, i) in frames"
            :key="i"
            :class="{ active: index === i }"
            @click="chooseFrame(i)"
          >
            <code>{{ entry.at }}ms</code> {{ entry.action }}
            {{ entry.request ? `R${entry.request}` : '' }}
          </button>
        </div>
      </section>
    </div>
    <div class="callout">
      <strong>模拟规则</strong>
      <p>
        所有请求在t=0同时到达；FIFO、固定SQL时长、不抢占，容量=pool_size+max_overflow。同一时刻先归还并分配连接，再处理仍在等待的超时请求。
      </p>
      <p>
        槽位代表容量上限，不代表真实SQLAlchemy预先创建的连接数。模拟不含网络、数据库锁和系统调度开销，不是MySQL性能测试。
      </p>
    </div> </template
  ><template v-else>
    <AsyncState :loading="loading" :error="error" :empty="!snapshot" @retry="reload">
      <section class="panel">
        <div class="panel-heading">
          <h2>SQLAlchemy Pool · 实际瞬时值</h2>
          <el-button @click="reload">刷新实际快照</el-button>
        </div>
        <dl v-if="snapshot" class="snapshot">
          <div>
            <dt>configured size</dt>
            <dd>{{ snapshot.configured_size }}</dd>
          </div>
          <div>
            <dt>checked out</dt>
            <dd>{{ snapshot.checked_out }}</dd>
          </div>
          <div>
            <dt>current overflow</dt>
            <dd>{{ snapshot.overflow }}</dd>
          </div>
          <div>
            <dt>max overflow</dt>
            <dd>{{ snapshot.max_overflow }}</dd>
          </div>
          <div>
            <dt>waiting / pure wait</dt>
            <dd>未接入</dd>
          </div>
        </dl>
        <p>{{ snapshot?.note }}</p>
        <p class="muted">{{ snapshot?.observed_at }}</p>
      </section>
    </AsyncState>
    <div class="callout">
      后续可接入Locust负载和Prometheus时间序列；当前快照不能推断吞吐或排队时间。
    </div>
  </template>
</template>
