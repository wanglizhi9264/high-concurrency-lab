<script setup lang="ts">
import { computed, watch } from 'vue'
import BusinessTracePanel from '../components/BusinessTracePanel.vue'
import { useTaskLab } from '../composables/useTaskLab'
const props = defineProps<{ initialOrderId?: string }>()
const lab = useTaskLab()
const {
  orderId,
  taskId,
  maxAttempts,
  failFirst,
  delayMs,
  loading,
  error,
  intent,
  successor,
  detail,
  queue,
  accepted,
  result,
} = lab
watch(
  () => props.initialOrderId,
  (value) => {
    if (value && /^\d+$/.test(value)) orderId.value = Number(value)
  },
  { immediate: true },
)
const task = computed(() => detail.value?.task ?? accepted.value)
const stateNames: Record<string, string> = {
  queued: '已入库，等待执行',
  running: '执行权已领取',
  retry_wait: '等待下一次尝试',
  succeeded: '回执已持久化',
  failed: '尝试已终止，保留失败记录',
}
const metric = (value: number | null | undefined) =>
  value == null ? '未知 / 尚未采集' : String(value)
</script>
<template>
  <header class="page-heading">
    <div>
      <p class="eyebrow">08 / DURABLE TASKS & WORKER</p>
      <h1>请求已接受，任务何时真正完成？</h1>
      <p>
        固定处理已付款订单，生成 MySQL 回执。Redis Streams 传递任务 ID；独立 worker
        执行，数据库保存恢复依据。
      </p>
    </div>
    <span class="badge measured">Live · 真实异步任务</span>
  </header>
  <section class="panel section-space">
    <h2>1. 保存意图，再提交 MySQL</h2>
    <p>
      POST /api/v1/business/tasks → 一个事务写 durable_task、task_outbox、task_event。Redis
      不可用也可接受；HTTP 201 不等于已经执行。
    </p>
    <div class="toolbar">
      <label
        >已 paid 的采购订单 ID<input
          v-model.number="orderId"
          aria-label="任务订单 ID"
          type="number"
          min="1"
          :disabled="loading"
      /></label>
      <label
        >最多尝试<input
          v-model.number="maxAttempts"
          aria-label="任务最多尝试"
          type="number"
          min="1"
          max="5"
          :disabled="loading"
      /></label>
    </div>
    <details>
      <summary>受控故障配置（实际执行，不是性能结论）</summary>
      <p>
        worker 会真的延迟 / 抛出指定异常。默认 handler 预算 1 秒，租约 5
        秒。每次尝试的结果与耗时来自实际执行。
      </p>
      <div class="toolbar">
        <label
          >前几次失败<input
            v-model.number="failFirst"
            aria-label="任务失败次数"
            type="number"
            min="0"
            max="5"
            :disabled="loading" /></label
        ><label
          >每次延迟 ms<input
            v-model.number="delayMs"
            aria-label="任务延迟 ms"
            type="number"
            min="0"
            max="5000"
            :disabled="loading"
        /></label>
      </div>
    </details>
    <div class="toolbar">
      <button data-testid="task-prepare" :disabled="loading" @click="lab.prepare">
        保存新的任务 UUID 和参数</button
      ><button
        class="primary"
        data-testid="task-submit"
        :disabled="loading || !intent"
        @click="lab.submit"
      >
        提交 / 重放已保存意图
      </button>
    </div>
    <pre v-if="intent" data-testid="task-intent">{{ JSON.stringify(intent, null, 2) }}</pre>
    <p class="muted">
      重放始终使用保存的 UUID 和原参数；修改表单后请显式保存新意图。回执按 order_id
      唯一，多个任务不会生成多份回执。
    </p>
  </section>
  <section class="panel section-space">
    <h2>2. 读取持久化状态</h2>
    <p class="muted">租约仅表示数据库执行权期限，不证明进程存活；请刷新查看真实变化。</p>
    <div class="toolbar">
      <label class="wide-label"
        >任务 UUID<input v-model="taskId" aria-label="任务 UUID" :disabled="loading" /></label
      ><button data-testid="task-refresh" :disabled="loading || !taskId" @click="lab.refresh">
        读取任务 / 尝试 / 事件</button
      ><button :disabled="loading || !task" @click="lab.refreshQueue">采集队列快照</button>
    </div>
    <div v-if="task" data-testid="task-state">
      <h3>{{ stateNames[task.state] }} · {{ task.state }}</h3>
      <p>
        订单 {{ task.order_id }} · 尝试 {{ task.attempts }} / {{ task.max_attempts }} ·
        数据库更新时间 {{ task.updated_at }}
      </p>
      <p>
        下一次最早可领取：{{ task.available_at }}；租约截止：{{
          task.lease_until ?? '无'
        }}（不证明进程存活）。
      </p>
      <p v-if="task.last_error" role="status">实际失败：{{ task.last_error }}</p>
      <p v-if="task.retry_of">关联原失败任务：{{ task.retry_of }}</p>
    </div>
    <div v-else class="state">尚未读取；不会根据客户端时间推测状态。</div>
    <template v-if="detail">
      <p data-testid="task-outbox">
        确认发布 {{ detail.outbox.publish_count }} 次 · 最后消息 ID
        {{ detail.outbox.last_message_id ?? '未确认发布' }} ·
        {{ detail.outbox.last_published_at ?? '无确认时间' }}
      </p>
      <h3>3. 在项目终端启动本场景独立 worker</h3>
      <pre data-testid="task-command">{{ detail.worker_command }}</pre>
      <p>
        dispatcher 扫描本场景到期 outbox → XADD；consumer 用 XREADGROUP / XAUTOCLAIM 领取 → MySQL
        提交尝试 → 执行回执 → 提交结果 → XACK。HTTP 服务不启动 worker。正常 Ctrl+C
        请求停止；意外退出后租约到期可恢复。
      </p>
      <h3>实际尝试（MySQL task_attempt）</h3>
      <div class="table-scroll">
        <table>
          <thead>
            <tr>
              <th>次序 / worker</th>
              <th>结果</th>
              <th>开始 UTC</th>
              <th>完成 / 被发现遗弃</th>
              <th>handler ms</th>
              <th>错误 / 预算</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="attempt in detail.attempts" :key="attempt.number">
              <td>
                {{ attempt.number }}<small>{{ attempt.worker_id }}</small>
              </td>
              <td>{{ attempt.status }}</td>
              <td>{{ attempt.started_at }}</td>
              <td>
                {{ attempt.finished_at ?? '完成时间未知' }}<br />{{
                  attempt.abandoned_at ? `恢复发现：${attempt.abandoned_at}` : ''
                }}
              </td>
              <td>{{ attempt.handler_ms == null ? '未知' : attempt.handler_ms.toFixed(3) }}</td>
              <td>
                {{ attempt.error ?? '无' }}<br />超时 {{ attempt.timeout_seconds }}s / 租约
                {{ attempt.lease_seconds }}s
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-if="!detail.attempts.length" class="state">
        尚无领取记录。请确认独立 worker 已按上面命令运行。
      </p>
      <p class="muted">
        handler ms 只含处理阶段，不含领取、最终提交和 ACK。进程崩溃没有完成观测，耗时保留未知。
      </p>
      <h3>真实事件顺序（MySQL task_event）</h3>
      <ol class="task-events">
        <li v-for="event in detail.events" :key="event.id">
          <strong>{{ event.kind }}</strong> · {{ event.source }} · {{ event.occurred_at
          }}<code>{{ JSON.stringify(event.details) }}</code>
        </li>
      </ol>
      <p v-if="detail.events_truncated">仅展示最新 100 条；更早记录保留在数据库。</p>
      <p class="muted">
        ACK 是单独观测：acknowledged / not_pending / unconfirmed。没有 ACK 事件不能证明消息没被
        ACK。
      </p>
      <div v-if="detail.receipt" class="state" data-testid="task-receipt">
        <h3>结果已提交：回执 #{{ detail.receipt.id }}</h3>
        <p>
          订单 {{ detail.receipt.order_id }} · 金额 {{ detail.receipt.total }} · UTC
          {{ detail.receipt.created_at }}
        </p>
        <pre>{{ JSON.stringify(detail.receipt.snapshot, null, 2) }}</pre>
      </div>
      <button
        v-if="detail.task.state === 'failed'"
        data-testid="task-retry-failed"
        :disabled="loading"
        @click="lab.retryFailed"
      >
        创建关联后继任务（关闭故障，保留原失败）
      </button>
      <p v-if="successor">
        后继 UUID {{ successor.payload.task_id }}；原任务 {{ successor.parent }}
      </p>
    </template>
  </section>
  <section class="panel section-space">
    <h2>队列观测：三个数字不是同一个“积压”</h2>
    <p>
      MySQL 状态计数、Redis XLEN 已保留消息（包含 ACK 历史）、XPENDING 已投递未 ACK、group lag
      尚未投递估计，分别采集；跨系统不是原子快照。
    </p>
    <div v-if="queue" data-testid="task-queue">
      <p>
        采集 {{ queue.observed_at }} · 耗时 {{ queue.collection_ms.toFixed(3) }} ms · Redis
        {{ queue.redis_available ? '可访问' : '不可用，值保留未知' }}
      </p>
      <p>
        XLEN {{ metric(queue.retained_entries) }} / pending {{ metric(queue.pending) }} / lag
        {{ metric(queue.group_lag) }} / PTTL {{ metric(queue.pttl_ms) }} ms
      </p>
      <pre>{{ JSON.stringify(queue.database_counts, null, 2) }}</pre>
      <p class="muted">{{ queue.source }}</p>
    </div>
    <p v-else class="state">尚未采集队列快照。</p>
  </section>
  <section v-if="error" class="state error" role="alert">
    {{ error
    }}<button :disabled="loading" @click="lab.retryRequest">重试上次请求（原 UUID）</button>
  </section>
  <p v-if="loading" role="status">正在请求实际服务…</p>
  <section v-if="result" class="panel section-space">
    <h2>本次 HTTP 请求，与异步执行分开</h2>
    <p>
      {{ result.path }} · HTTP {{ result.status }} · 浏览器往返 {{ result.browserMs.toFixed(3) }} ms
    </p>
    <BusinessTracePanel v-if="result.body" :trace="result.body.trace" />
    <details>
      <summary>原始响应</summary>
      <pre data-testid="task-result">{{ JSON.stringify(result.body, null, 2) }}</pre>
    </details>
  </section>
  <section class="panel section-space">
    <h2>阅读入口</h2>
    <p>
      <a
        href="https://github.com/wanglizhi9264/high-concurrency-lab/blob/main/docs/guides/worker-lab.md"
        target="_blank"
        rel="noreferrer"
        >启动、停止、故障恢复指南</a
      >
      ·
      <a
        href="https://github.com/wanglizhi9264/high-concurrency-lab/blob/main/src/concurrency_lab/services/task_execution.py"
        target="_blank"
        rel="noreferrer"
        >领取与结果事务源码</a
      >
      ·
      <a
        href="https://github.com/wanglizhi9264/high-concurrency-lab/blob/main/docs/architecture/decisions/0006-reliable-worker.md"
        target="_blank"
        rel="noreferrer"
        >队列 ADR</a
      >
    </p>
  </section>
</template>
<style scoped>
button {
  padding: 9px 14px;
  border: 1px solid var(--border);
  border-radius: 7px;
  color: var(--text);
  background: var(--panel);
  font: inherit;
}
button:hover:not(:disabled) {
  background: var(--soft);
  border-color: var(--purple);
}
button:disabled {
  opacity: 0.6;
  cursor: wait;
}
button.primary {
  color: white;
  background: var(--purple);
}
input {
  padding: 9px;
  border: 1px solid var(--border);
  border-radius: 6px;
  background: var(--bg);
  color: var(--text);
  font: inherit;
  width: 160px;
}

input {
  min-width: 110px;
}
.wide-label {
  flex: 1;
}
.wide-label input {
  width: 100%;
  min-width: 0;
}
pre {
  overflow: auto;
  max-height: 360px;
  padding: 14px;
  background: var(--bg);
  font-size: 12px;
}
table {
  width: 100%;
  text-align: left;
  font-size: 12px;
  border-collapse: collapse;
}
th,
td {
  padding: 10px;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
}
td small {
  display: block;
  max-width: 170px;
  overflow-wrap: anywhere;
}
.table-scroll {
  overflow-x: auto;
}
.task-events li {
  padding: 8px;
  font-size: 12px;
}
.task-events code {
  display: block;
  overflow-wrap: anywhere;
}
details {
  margin: 14px 0;
}
h3 {
  margin-top: 20px;
}
</style>
