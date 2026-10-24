<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import BusinessTracePanel from '../components/BusinessTracePanel.vue'
import { businessQueryPath } from '../api/business'
import { useBusinessQuery } from '../composables/useBusinessQuery'
import type { BusinessCursor, BusinessQuery } from '../types/business'
const query = ref<BusinessQuery>('product')
const entityId = ref(1),
  limit = ref(20),
  offset = ref(0)
const cursor = ref<BusinessCursor | null>(null)
const { result, loading, error, execute } = useBusinessQuery()
const validationError = ref('')
const path = computed(() =>
  businessQueryPath(query.value, entityId.value, limit.value, offset.value, cursor.value),
)
const nextCursor = computed(() => {
  const data = result.value?.body?.data
  return data && 'next_cursor' in data ? data.next_cursor : null
})
const isEmpty = computed(() => {
  const data = result.value?.body?.data
  return data && 'items' in data && data.items.length === 0
})
watch([query, entityId, limit, offset], () => {
  cursor.value = null
})
async function send() {
  validationError.value = ''
  if (
    !Number.isSafeInteger(entityId.value) ||
    entityId.value < 1 ||
    !Number.isInteger(limit.value) ||
    limit.value < 1 ||
    limit.value > 100 ||
    !Number.isInteger(offset.value) ||
    offset.value < 0 ||
    offset.value > 100000
  ) {
    validationError.value =
      '请输入正整数 ID、1–100 页大小及 0–100000 OFFSET；页面 ID 不超过 JS 安全整数。'
    return
  }
  await execute(path.value)
}
async function nextPage() {
  if (!nextCursor.value) return
  cursor.value = nextCursor.value
  await send()
}
</script>
<template>
  <header class="page-heading">
    <div>
      <p class="eyebrow">04 / REAL BUSINESS QUERIES</p>
      <h1>查一条真实数据，沿 SQL 看到数据库。</h1>
      <p>独立业务实验库 · 固定参数化查询 · 每次请求独立 Session 和事务</p>
    </div>
    <span class="badge measured">Live measured · 真实业务读取</span>
  </header>
  <section class="panel">
    <fieldset :disabled="loading" class="business-form">
      <label
        >查询类型<select v-model="query" aria-label="查询类型">
          <option value="product">按主键查商品</option>
          <option value="user_orders">用户订单 · ID 顺序</option>
          <option value="order_page">用户订单 · 时间 / ID 分页</option>
          <option value="order_detail">订单明细 · 固定 JOIN</option>
        </select></label
      >
      <label
        >实体 ID<input
          v-model.number="entityId"
          aria-label="实体 ID"
          type="number"
          min="1"
          :max="Number.MAX_SAFE_INTEGER"
      /></label>
      <template v-if="query === 'user_orders' || query === 'order_page'"
        ><label
          >页大小<input
            v-model.number="limit"
            aria-label="页大小"
            type="number"
            min="1"
            max="100" /></label
        ><label
          >OFFSET<input
            v-model.number="offset"
            aria-label="OFFSET"
            type="number"
            min="0"
            max="100000" /></label
      ></template>
      <el-button type="primary" :loading="loading" data-testid="execute-business" @click="send"
        >发送真实请求</el-button
      >
    </fieldset>
    <pre>
GET {{ path }}
请求体：无。浏览器通过 HTTP 访问 FastAPI；不直接连接 MySQL。</pre>
    <p class="muted">
      ID 分别表示商品、用户或订单。分页顺序固定 created_at DESC, id
      DESC，游标两字段一起发送。没有缓存；所有成功查询均经过真实 MySQL。
    </p>
  </section>
  <div v-if="loading" role="status" class="state">正在执行真实查询…</div>
  <div v-if="error || validationError" role="alert" class="state error">
    {{ validationError || error }} <el-button :disabled="loading" @click="send">重试</el-button>
  </div>
  <div v-if="!result && !loading && !error && !validationError" class="state">
    尚未执行请求。先查商品 1，再查订单 1 或用户 500 的分页。
  </div>
  <template v-if="result?.body">
    <section class="panel section-space business-request-result">
      <div class="panel-heading">
        <h2>本次实际响应 · HTTP {{ result.status }}</h2>
        <span class="badge measured">{{ result.body.trace.database }}</span>
      </div>
      <code>GET {{ result.path }}</code>
      <p class="muted">Request ID {{ result.requestId ?? result.body.trace.request_id }}</p>
      <div class="business-times">
        <span>浏览器 fetch + JSON：{{ result.browserMs.toFixed(3) }} ms</span
        ><span>服务端至响应头准备：{{ result.preparationMs ?? '未取得' }} ms</span
        ><span>JSON 记录截止：{{ result.body.trace.service_elapsed_ms?.toFixed(3) }} ms</span>
      </div>
      <p v-if="isEmpty">该用户没有符合条件的订单；空列表是正常查询结果。</p>
      <pre v-if="result.body.data" data-testid="business-result">{{
        JSON.stringify(result.body.data, null, 2)
      }}</pre>
      <el-button v-if="query === 'order_page'" :disabled="!nextCursor || loading" @click="nextPage"
        >下一页（游标）</el-button
      >
      <p class="muted">
        SQL 获取 / 取数区间包含客户端开销，不能称为 MySQL 纯执行时间。订单明细最多两条业务
        SQL，所有请求另有一条所有权检查 SQL。
      </p>
    </section>
    <BusinessTracePanel :trace="result.body.trace" />
    <details class="panel section-space">
      <summary>完整响应 JSON</summary>
      <pre>{{ JSON.stringify(result.body, null, 2) }}</pre>
    </details>
  </template>
</template>
<style scoped>
.business-form {
  border: 0;
  padding: 0;
  display: flex;
  align-items: end;
  flex-wrap: wrap;
  gap: 16px;
}
.business-form label {
  display: grid;
  gap: 8px;
  font-size: 12px;
}
.business-form select,
.business-form input {
  color: var(--text);
  background: var(--bg);
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 9px;
  font: inherit;
}
.business-form input {
  width: 135px;
}
.business-times {
  display: flex;
  gap: 18px;
  flex-wrap: wrap;
  margin: 20px 0;
  font-size: 12px;
}
.business-request-result > pre {
  max-height: 320px;
  overflow: auto;
  background: var(--bg);
  padding: 14px;
  border-radius: 8px;
}
</style>
