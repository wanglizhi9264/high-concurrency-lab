<script setup lang="ts">
import { computed } from 'vue'
import BusinessTracePanel from '../components/BusinessTracePanel.vue'
import { cacheSampleSummary, useCacheLab } from '../composables/useCacheLab'
import { cacheRequestPath } from '../api/cache'
import type { BusinessSpan } from '../types/business'

const lab = useCacheLab()
const { productId, ttl, mode, result, inspection, history, loading, error, networkFailures } = lab
const summary = computed(() => cacheSampleSummary(history.value))
const path = computed(() => {
  try {
    return cacheRequestPath('read', productId.value, mode.value, ttl.value)
  } catch {
    return '参数无效'
  }
})
const sql = computed(
  () => result.value?.body?.trace.spans.filter((s) => s.kind === 'sql_execute_fetch') ?? [],
)
function productSql(spans: BusinessSpan[]) {
  return spans.filter((s) => s.sql?.includes('lab_product')).length
}
function ttlText(value: number | null | undefined) {
  return value == null
    ? '未采集'
    : value === -2
      ? '键不存在（-2）'
      : value === -1
        ? '未设置过期（-1，异常）'
        : `${value} ms`
}
</script>
<template>
  <header class="page-heading">
    <div>
      <p class="eyebrow">06 / REAL CACHE-ASIDE</p>
      <h1>这次请求，商品到底从哪里来？</h1>
      <p>真实 Redis 缓存副本、真实 MySQL 回源。每次操作都有 HTTP、命令与源码依据。</p>
    </div>
    <span class="badge measured">Live measured · 实际请求</span>
  </header>
  <section class="panel toolbar">
    <label
      >商品 ID<input
        v-model.number="productId"
        aria-label="缓存商品 ID"
        type="number"
        min="1"
        max="1000"
        :disabled="loading"
    /></label>
    <label
      >查询方式<select v-model="mode" aria-label="缓存查询方式" :disabled="loading">
        <option value="cache">使用缓存</option>
        <option value="bypass">绕过缓存（只查 MySQL）</option>
      </select></label
    >
    <label
      >回填 TTL / 秒<input
        v-model.number="ttl"
        aria-label="缓存 TTL"
        type="number"
        min="1"
        max="60"
        :disabled="loading"
    /></label>
    <button
      class="primary-button"
      data-testid="cache-read"
      :disabled="loading"
      @click="lab.execute('read')"
    >
      {{ loading ? '请求进行中…' : '发送商品查询' }}
    </button>
    <button :disabled="loading" @click="lab.execute('inspect')">检查选定键</button>
    <button :disabled="loading" @click="lab.execute('invalidate')">主动失效</button>
  </section>
  <div class="callout">
    <p>
      <code>GET {{ path }}</code>
    </p>
    <p>
      主动失效实际发送 DELETE /api/v1/business/cache/products/{{
        productId
      }}，只操作该商品缓存。检查键是独立 GET …/{{
        productId
      }}/state，不参与查询命中率。绕过缓存不发送任何 Redis 命令。
    </p>
  </div>
  <div v-if="error" class="state error" role="alert">
    {{ error }}
    <button data-testid="cache-retry" :disabled="loading" @click="lab.retry">重试本次操作</button>
  </div>
  <div v-else-if="loading" class="state" role="status">正在等待实际 HTTP 响应…</div>
  <div v-else-if="!result" class="state">尚无请求，先主动失效，再连续查询两次观察 MISS → HIT。</div>
  <section v-if="result?.body" class="panel section-space">
    <div class="panel-heading">
      <h2>本次实际结果</h2>
      <span class="badge">HTTP {{ result.status }} · {{ result.action }}</span>
    </div>
    <p>
      <code>{{ result.action === 'invalidate' ? 'DELETE' : 'GET' }} {{ result.path }}</code>
    </p>
    <div v-if="result.body.cache" data-testid="cache-result">
      <p>
        路径 <strong>{{ result.body.cache.outcome }}</strong> · 初次查找
        <strong>{{ result.body.cache.initial_lookup }}</strong> · 最终来源
        <strong>{{ result.body.cache.served_from ?? '无商品读取' }}</strong>
      </p>
      <p>
        回填发布：{{
          result.body.cache.fill_published === true
            ? '已发布'
            : result.body.cache.fill_published === false
              ? '被版本 / lease fencing 拒绝'
              : '未发生或未确认'
        }}
        · 原因：{{ result.body.cache.reason ?? '无' }}
      </p>
      <p v-if="result.body.cache.outcome === 'degraded'" class="error-text">
        缓存操作未确认可用。若有商品数据，由实际 MySQL 查询返回；主动失效不能视为成功，请恢复 Redis
        后重试。
      </p>
      <pre>{{ JSON.stringify(result.body.data, null, 2) }}</pre>
    </div>
    <p>
      MySQL 商品 SQL 尝试 {{ productSql(sql) }} · 所有权 / 其他 SQL 尝试
      {{ sql.length - productSql(sql) }} · 总计 {{ sql.length }}。实际 hit 不创建业务
      Session；基础健康池是另一条路径。
    </p>
    <p>
      浏览器往返 {{ result.browserMs.toFixed(3) }} ms · 服务端响应准备
      {{ result.preparationMs ?? '未采集' }} ms · Trace 截止快照
      {{ result.body.trace.service_elapsed_ms.toFixed(3) }} ms；不同边界不能相加。
    </p>
  </section>
  <section class="panel section-space">
    <h2>选定缓存键的独立快照</h2>
    <p>
      TTL：{{ ttlText(inspection?.ttl_ms) }} · MEMORY USAGE：{{
        inspection?.memory_bytes == null ? '未采集' : `${inspection.memory_bytes} bytes`
      }}
    </p>
    <p v-if="inspection">
      <code>{{ inspection.key }}</code
      ><br />采样 UTC {{ inspection.observed_at }} · generation
      {{ inspection.generation ?? '未知' }}
    </p>
    <p class="muted">
      剩余 TTL 是采样时刻的值，页面不伪造倒计时。真实等待后再读；一次 MISS
      也可能来自失效、淘汰或从未填充，不能独自证明 TTL 过期。内存仅为选定 value 键的 Redis
      估算，不是整个实例内存。
    </p>
  </section>
  <section class="panel section-space">
    <h2>本页最近 {{ history.length }} 条实际响应（最多 50）</h2>
    <p>
      初次命中率：{{
        summary.hitRate == null ? '未测量' : `${(summary.hitRate * 100).toFixed(2)}%`
      }}
      = {{ summary.hits }} hit / ({{ summary.hits }} hit +
      {{ summary.misses }} miss)。等待后复用仍是初查 miss；最终来自 Redis
      {{ summary.redisServed }} 次，降级 {{ summary.degraded }} 次。
    </p>
    <p>
      排除 {{ summary.excluded }} 条 bypass / 检查 / 失效 / 未知响应；本页累计另有
      {{ networkFailures }} 次未取得可用响应，不当作零 SQL
      或成功。统计仅覆盖本页保留响应，非全实例指标，刷新页面会清空。
    </p>
    <div v-if="!history.length" class="state">暂无已完成响应</div>
    <div v-else class="cache-history">
      <button
        v-for="(row, index) in history"
        :key="index"
        :disabled="loading"
        @click="result = row"
      >
        {{ row.body?.trace.observed_at }} · {{ row.action }} · HTTP {{ row.status }} ·
        {{ row.body?.cache?.initial_lookup ?? '未知' }} →
        {{ row.body?.cache?.served_from ?? '无商品读取' }}
      </button>
    </div>
  </section>
  <BusinessTracePanel v-if="result?.body" :trace="result.body.trace" />
  <div class="callout">
    <p>
      MySQL 是权威数据源。缓存仅保存被访问的商品，TTL 加 0..10% 抖动。失效会原子推进 generation
      并撤销旧 lease；回填须同时通过 generation 和随机 token 检查。
    </p>
    <p>
      最多等待其他回填 250 ms，随后允许重复读 MySQL，且不无锁写缓存；不承诺永远只有一次回源。Redis
      不可用时降级也会放大数据库压力。不存在商品暂不做负缓存，重复缺失请求仍会穿透；抖动也不能消除雪崩。
    </p>
    <p>
      当前阶段没有修改商品的 API，不能把缓存 lease 当作数据库事务锁或强一致保证。完整 Trace
      和检查命令有开销；真实性能以记录的实验环境为准。
    </p>
  </div>
</template>
<style scoped>
button {
  border: 1px solid var(--border);
  border-radius: 7px;
  background: var(--panel);
  color: var(--text);
  padding: 9px 14px;
  font: inherit;
}
button:hover:not(:disabled) {
  border-color: var(--purple);
  background: var(--soft);
}
button:disabled {
  cursor: wait;
  opacity: 0.6;
}
.primary-button {
  color: white;
  background: var(--purple);
  border-color: var(--purple);
}
.primary-button:hover:not(:disabled) {
  background: var(--purple);
  filter: brightness(1.08);
}
input,
select {
  color: var(--text);
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 8px;
  max-width: 240px;
}
pre,
code {
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}
.cache-history {
  display: grid;
  gap: 8px;
  max-height: 280px;
  overflow: auto;
}
.cache-history button {
  text-align: left;
  padding: 8px;
}
</style>
