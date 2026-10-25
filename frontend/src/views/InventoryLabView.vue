<script setup lang="ts">
import { computed } from 'vue'
import BusinessTracePanel from '../components/BusinessTracePanel.vue'
import { contestSummary, useInventoryLab } from '../composables/useInventoryLab'

const lab = useInventoryLab()
const {
  productId,
  initial,
  scenarioId,
  userId,
  quantity,
  contestSize,
  loading,
  error,
  result,
  scenario,
  currentOrder,
  audit,
  intent,
  samples,
  history,
} = lab
const contest = computed(() => contestSummary(samples.value))
const sqlCount = computed(
  () =>
    result.value?.body?.trace.spans.filter((span) => span.kind.startsWith('sql_execute_')).length ??
    0,
)
</script>
<template>
  <header class="page-heading">
    <div>
      <p class="eyebrow">07 / TRANSACTIONS & IDEMPOTENCY</p>
      <h1>请求可以重试，库存不能重复扣。</h1>
      <p>真实 MySQL 事务、条件更新、行锁与唯一约束。新场景保留旧数据，不重置库存。</p>
    </div>
    <span class="badge measured">Live measured · 真实写入</span>
  </header>
  <section class="panel section-space">
    <h2>1. 创建新的库存实验</h2>
    <div class="toolbar">
      <label
        >商品 ID<input
          v-model.number="productId"
          aria-label="库存商品 ID"
          type="number"
          min="1"
          max="1000"
          :disabled="loading"
      /></label>
      <label
        >初始数量<input
          v-model.number="initial"
          aria-label="初始库存"
          type="number"
          min="0"
          max="10000"
          :disabled="loading"
      /></label>
      <button
        class="primary"
        data-testid="inventory-new-scenario"
        :disabled="loading"
        @click="lab.createNewScenario"
      >
        创建新场景（保留旧场景）
      </button>
    </div>
    <label class="wide-label"
      >场景 ID<input
        v-model="scenarioId"
        aria-label="库存场景 ID"
        :disabled="loading"
        placeholder="新场景 UUID，或粘贴已有场景"
    /></label>
    <p class="muted">
      POST /api/v1/business/inventory/scenarios，携带唯一
      scenario_id。网络失败后“重试上次操作”保留原场景 UUID，匹配重放不会再建一批库存。
    </p>
    <div v-if="scenario" class="stock-grid" data-testid="inventory-stock">
      <span
        >初始 <strong>{{ scenario.initial }}</strong></span
      ><span
        >可用 <strong>{{ scenario.available }}</strong></span
      >
      <span
        >预留 <strong>{{ scenario.reserved }}</strong></span
      ><span
        >已售 <strong>{{ scenario.sold }}</strong></span
      >
    </div>
    <p v-if="scenario" class="muted">
      最近确认的库存快照 · {{ scenario.id }}；不是客户端实时推测值。
    </p>
    <div v-else class="state">尚无库存实验的已确认快照。</div>
  </section>
  <section class="panel section-space">
    <h2>2. 保存订单意图，再提交或重放</h2>
    <div class="toolbar">
      <label
        >用户 ID<input
          v-model.number="userId"
          aria-label="下单用户 ID"
          type="number"
          min="1"
          :disabled="loading"
      /></label>
      <label
        >数量<input
          v-model.number="quantity"
          aria-label="下单数量"
          type="number"
          min="1"
          max="100"
          :disabled="loading"
      /></label>
      <button data-testid="inventory-prepare" :disabled="loading" @click="lab.prepareOrder">
        保存新意图（新 UUID）
      </button>
      <button
        class="primary"
        data-testid="inventory-submit"
        :disabled="loading || !intent"
        @click="lab.submitSavedOrder"
      >
        提交 / 重放原意图
      </button>
      <button :disabled="loading || !intent" @click="lab.confirmByKey">按原键确认订单</button>
      <button :disabled="loading || !intent" @click="lab.submitChangedPayload">
        冲突实验：原键 + 当前参数
      </button>
    </div>
    <div v-if="intent" class="callout">
      <p>
        Idempotency-Key（同一业务意图保持不变）<code data-testid="inventory-intent-key">{{
          intent.key
        }}</code>
      </p>
      <p><code>POST /api/v1/business/purchases/orders</code></p>
      <pre>{{ JSON.stringify(intent.payload, null, 2) }}</pre>
      <p>
        编辑上方数量不会偷偷改变这个快照。只有“保存新意图”生成新键；冲突实验明确用原键发送当前参数。
      </p>
    </div>
    <p v-else class="muted">
      没有已保存的订单意图。商品价格来自 MySQL，前端不提交价格，也不从 Redis 决定库存。
    </p>
  </section>
  <section class="panel section-space">
    <h2>3. 最近确认订单的状态</h2>
    <div v-if="currentOrder">
      <p>
        订单 ID {{ currentOrder.id }} · 状态
        <strong data-testid="inventory-order-state">{{ currentOrder.status }}</strong> · 数量
        {{ currentOrder.quantity }} · 单价 {{ currentOrder.unit_price }} · 总额
        {{ currentOrder.total }}
      </p>
      <p class="muted">
        持久化订单 ID 不同于每次 HTTP 的 Request ID，也不同于稳定幂等键
        {{ currentOrder.idempotency_key }}。
      </p>
      <div class="toolbar">
        <button :disabled="loading" @click="lab.transition('paid')">标记 paid（实验）</button
        ><button :disabled="loading" @click="lab.transition('cancelled')">取消并归还预留</button>
      </div>
    </div>
    <div v-else class="state">先创建订单，或按原键查询确认。</div>
    <p class="muted">
      reserved→paid：预留转已售；reserved→cancelled：预留回到可用。同一终态重放不重复记账，paid与cancelled不能互转。这里没有真实支付请求。
    </p>
  </section>
  <section class="panel section-space">
    <h2>4. 客户端有界争抢与独立审计</h2>
    <div class="toolbar">
      <label
        >请求数量<input
          v-model.number="contestSize"
          aria-label="争抢请求数量"
          type="number"
          min="2"
          max="20"
          :disabled="loading"
      /></label>
      <button
        :disabled="loading || !scenarioId"
        data-testid="inventory-contest"
        @click="lab.startContest"
      >
        并发发起独立意图
      </button>
      <button
        :disabled="loading || !scenarioId"
        data-testid="inventory-audit"
        @click="lab.inspectAudit"
      >
        GET 实际库存审计
      </button>
    </div>
    <p class="muted">
      2..20个客户端调用不等于相同数量的服务端同时执行。每个争抢意图独立UUID；批量结束后实际GET审计，不在前端猜测扣减结果。
    </p>
    <div v-if="samples.length">
      <p>
        确认唯一订单 {{ contest.uniqueOrders }} · 本次新建响应 {{ contest.created }} · 重放
        {{ contest.replays }} · 库存不足 {{ contest.insufficient }} · 事务冲突
        {{ contest.conflicts }} · 网络未知 {{ contest.unknown }}
      </p>
      <div class="request-list">
        <button
          v-for="sample in samples"
          :key="sample.intent.key"
          :disabled="loading || !sample.result"
          @click="sample.result && lab.selectResponse(sample.result)"
        >
          {{ sample.intent.key }} ·
          {{ sample.result ? `HTTP ${sample.result.status}` : '结果未知' }} ·
          {{ sample.result?.body?.error?.code ?? sample.error ?? '点击检查实际响应' }}
        </button>
      </div>
    </div>
    <div v-if="audit" data-testid="inventory-audit-result">
      <h3>{{ audit.all_pass ? '所有审计项通过' : '审计发现不一致' }}</h3>
      <p>采样 {{ audit.observed_at }} · 场景 {{ audit.scenario.id }}</p>
      <table class="data-table">
        <tbody>
          <tr v-for="(passed, name) in audit.checks" :key="name">
            <td>{{ name }}</td>
            <td :class="passed ? '' : 'error-text'">{{ passed ? '通过' : '失败' }}</td>
          </tr>
        </tbody>
      </table>
      <pre>{{
        JSON.stringify(
          {
            stock: audit.scenario,
            order_units: audit.order_units,
            order_counts: audit.order_counts,
          },
          null,
          2,
        )
      }}</pre>
      <p class="muted">
        核对可用+预留+已售=初始、reserved订单量=预留、paid订单量=已售。cancelled只是历史量；取消后再下单合法，全部历史订单数量可以超过初始库存。
      </p>
    </div>
    <div v-else class="state">尚无当前场景的实际审计；不能用 HTTP 200 代替库存正确性。</div>
  </section>
  <div v-if="error" class="state error" role="alert">
    {{ error }}
    <button data-testid="inventory-retry" :disabled="loading" @click="lab.retry">
      重试上次操作（原键 / 原内容）
    </button>
  </div>
  <div v-if="loading" class="state" role="status">等待实际数据库事务和 HTTP 响应…</div>
  <section v-if="result" class="panel section-space">
    <h2>本次真实 HTTP 响应</h2>
    <p>
      HTTP {{ result.status }} · <code>{{ result.path }}</code>
    </p>
    <p>
      Request ID {{ result.requestId ?? result.body?.trace.request_id }} · 浏览器往返
      {{ result.browserMs.toFixed(3) }} ms · 服务端准备 {{ result.preparationMs ?? '未知' }} ms ·
      实际返回的 SQL 尝试 {{ sqlCount }}
    </p>
    <pre v-if="result.body?.data" data-testid="inventory-result">{{
      JSON.stringify(result.body.data, null, 2)
    }}</pre>
    <p v-if="result.body?.data && 'order' in result.body.data">
      applied={{ result.body.data.applied }} · replayed={{
        result.body.data.replayed
      }}。多个重放响应可以指向同一订单，不能当作多次扣减。
    </p>
  </section>
  <BusinessTracePanel v-if="result?.body" :trace="result.body.trace" />
  <details v-if="history.length" class="panel section-space">
    <summary>最近 {{ history.length }} 条实际响应（最多30条）</summary>
    <div class="request-list">
      <button
        v-for="(row, index) in history"
        :key="index"
        :disabled="loading"
        @click="lab.selectResponse(row)"
      >
        HTTP {{ row.status }} · {{ row.path }} · {{ row.body?.trace.observed_at }}
      </button>
    </div>
  </details>
  <div class="callout">
    <p>
      MySQL约束与事务保证库存不变量，Redis缓存和Python进程内锁不参与库存正确性。正常写入始终按“场景→订单”顺序取锁；条件UPDATE仍检查影响行数，失败整笔事务退出。
    </p>
    <p>
      1213死锁与1205锁等待返回安全冲突，恢复后按原意图重试。事务区间包含实际提交或回滚退出成本，SQL区间包含网络和可能的锁等待，不能叫纯锁等待。
    </p>
    <p>
      提交确认阶段超时或断网时，结果可能未知；不要直接宣布“没有订单”。保留原幂等键，按键查询或原样重放确认。业务写入默认关闭，需明确迁移独立业务库并开启
      BUSINESS_WRITES_ENABLED。
    </p>
  </div>
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
  cursor: wait;
  opacity: 0.6;
}
button.primary {
  color: white;
  background: var(--purple);
}
input {
  padding: 9px;
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text);
  background: var(--bg);
  width: 130px;
  font: inherit;
}
.wide-label {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 14px;
}
.wide-label input {
  flex: 1;
  min-width: 0;
  max-width: 580px;
}
.stock-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 28px;
  margin: 20px 0;
}
.stock-grid strong {
  font-size: 24px;
  margin-left: 8px;
}
.request-list {
  display: grid;
  gap: 8px;
  max-height: 260px;
  overflow: auto;
  margin: 12px 0;
}
.request-list button {
  text-align: left;
  overflow-wrap: anywhere;
}
code,
pre {
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}
</style>
