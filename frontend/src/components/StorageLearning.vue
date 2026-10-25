<script setup lang="ts">
import { computed, ref } from 'vue'

type Step = { target: 'app' | 'mysql' | 'redis' | 'both'; command: string; detail: string }
const scenarios = [
  {
    name: '当前项目：健康检查',
    actual: true,
    summary: '只确认两个服务能响应；不会读取商品，也不会填充业务缓存。',
    steps: [
      {
        target: 'app',
        command: 'GET /health/ready',
        detail: '请求进入健康服务。下面两个探针并发执行，互不等待。',
      },
      {
        target: 'both',
        command: 'MySQL: SELECT 1  ∥  Redis: PING',
        detail: 'MySQL 返回 1；Redis 返回 PONG。这只能验证可用性，不能证明缓存命中或订单查询性能。',
      },
      {
        target: 'app',
        command: '汇总检查结果 → HTTP 200 / 503',
        detail: '两个探针都成功才返回就绪。这里是代码路径说明，点击下方真实采集查看本机结果。',
      },
    ] satisfies Step[],
  },
  {
    name: '① 首次读取 · 缓存未命中',
    actual: false,
    summary: '以商品 42 为例：Redis 没有副本时，应用去 MySQL 读取，再填入缓存。',
    steps: [
      {
        target: 'redis',
        command: 'GET product:42 → nil',
        detail: '先查 Redis：键不存在，叫作缓存未命中（MISS）。',
      },
      {
        target: 'mysql',
        command: 'SELECT id, name, price FROM product WHERE id = 42',
        detail: '应用查询 MySQL，得到商品 42「机械键盘」及价格 299。MySQL 保存权威记录。',
      },
      {
        target: 'redis',
        command: 'SET product:42 \'{"name":"机械键盘","price":299}\' EX 60',
        detail: '应用把查询结果的副本放入 Redis，并设置 60 秒有效期。MySQL 不会自动同步到 Redis。',
      },
      {
        target: 'app',
        command: '返回商品 → 浏览器',
        detail: '本次仍然访问了 MySQL，还增加了缓存读写，不能声称每次加 Redis 都更快。',
      },
    ] satisfies Step[],
  },
  {
    name: '② 再次读取 · 缓存命中',
    actual: false,
    summary: '独立场景：假设上次已填充缓存，且副本尚未过期。',
    steps: [
      {
        target: 'redis',
        command: 'GET product:42 → {"name":"机械键盘","price":299}',
        detail: 'Redis 已有副本，叫作缓存命中（HIT）。',
      },
      {
        target: 'app',
        command: '直接返回缓存内容 → 浏览器',
        detail: '此次不查询 MySQL，减少了一次数据库访问。是否更快、快多少，要靠后续真实实验测量。',
      },
    ] satisfies Step[],
  },
  {
    name: '③ 缓存过期 · 回源',
    actual: false,
    summary: '独立场景：假设 60 秒有效期已到；这是手动教学步骤，无真实倒计时。',
    steps: [
      {
        target: 'redis',
        command: 'GET product:42 → nil（已过期）',
        detail: '临时副本过期后无法命中。Redis 缓存消失不等于 MySQL 商品被删除。',
      },
      {
        target: 'mysql',
        command: 'SELECT id, name, price FROM product WHERE id = 42',
        detail: '重新从 MySQL 读取当前记录。这一步叫回源。',
      },
      {
        target: 'redis',
        command: 'SET product:42 … EX 60',
        detail:
          '重新填入副本并返回商品。写入后的缓存失效与并发一致性需要独立设计，TTL 不保证强一致性。',
      },
    ] satisfies Step[],
  },
]
const scenarioIndex = ref(0)
const stepIndex = ref(0)
const scenario = computed(() => scenarios[scenarioIndex.value]!)
const step = computed(() => scenario.value.steps[stepIndex.value]!)
const cacheFilled = computed(
  () =>
    !scenario.value.actual &&
    (scenarioIndex.value === 2 ||
      (scenarioIndex.value === 1 && stepIndex.value >= 2) ||
      (scenarioIndex.value === 3 && stepIndex.value >= 2)),
)
function choose(index: number) {
  scenarioIndex.value = index
  stepIndex.value = 0
}
</script>

<template>
  <section class="panel storage-learning" aria-label="MySQL 与 Redis 交互教学">
    <div class="panel-heading">
      <div>
        <p class="eyebrow">先分清职责，再看请求</p>
        <h2>同一份商品，为什么会出现在两个地方？</h2>
      </div>
      <span class="badge" :class="scenario.actual ? 'measured' : 'simulation'">
        {{ scenario.actual ? '实际代码路径 · 非实时采集' : 'Simulation · 不操作真实缓存' }}
      </span>
    </div>
    <div class="storage-tabs" aria-label="选择请求场景">
      <button
        v-for="(item, index) in scenarios"
        :key="item.name"
        :aria-pressed="index === scenarioIndex"
        @click="choose(index)"
      >
        {{ item.name }}
      </button>
    </div>
    <p class="storage-summary">{{ scenario.summary }}</p>
    <div class="storage-pair">
      <article
        class="storage-card mysql-card"
        :class="{ active: step.target === 'mysql' || step.target === 'both' }"
      >
        <div class="storage-title"><strong>MySQL</strong><span>权威数据 · 关系表</span></div>
        <p>保存用户、商品、订单及关联关系；用 SQL、索引和事务管理数据。</p>
        <template v-if="scenario.actual"
          ><code>SELECT 1 → 1</code>
          <p class="muted">当前探针不读业务表；002 的商品/订单数据在独立实验库。</p></template
        >
        <template v-else
          ><table>
            <caption>
              示意 product 表 · 非实际库数据
            </caption>
            <thead>
              <tr>
                <th>id</th>
                <th>name</th>
                <th>price</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>42</td>
                <td>机械键盘</td>
                <td>299</td>
              </tr>
            </tbody>
          </table>
          <p class="muted">缓存未命中或过期时，仍可从这里读取记录。</p></template
        >
      </article>
      <article
        class="storage-card redis-card"
        :class="{ active: step.target === 'redis' || step.target === 'both' }"
      >
        <div class="storage-title">
          <strong>Redis</strong
          ><span>{{ scenario.actual ? '当前：仅健康依赖' : '示例用途：临时缓存副本' }}</span>
        </div>
        <p>
          此处按键访问是教学示意，不操作真实缓存。真实商品缓存见
          <router-link to="/cache-lab">Redis 缓存实验</router-link>；不能从 PING 推断命中效果。
        </p>
        <template v-if="scenario.actual"
          ><code>PING → PONG</code>
          <p class="muted">当前不会执行商品 GET / SET，也没有业务命中率。</p></template
        >
        <template v-else
          ><code>key: product:42</code>
          <pre data-testid="cache-value">{{
            cacheFilled
              ? 'value: {"name":"机械键盘","price":299}\n有效期设置：60 秒'
              : 'value: ∅\n不存在或已过期（MISS）'
          }}</pre>
        </template>
      </article>
    </div>
    <div class="storage-step" aria-live="polite">
      <span class="badge"
        >步骤 {{ stepIndex + 1 }} / {{ scenario.steps.length }} ·
        {{
          step.target === 'both'
            ? 'MySQL ∥ Redis 并发'
            : step.target === 'app'
              ? '应用 / 浏览器'
              : step.target === 'mysql'
                ? '访问 MySQL'
                : '访问 Redis'
        }}</span
      >
      <code>{{ step.command }}</code>
      <p>{{ step.detail }}</p>
    </div>
    <div class="storage-actions">
      <el-button :disabled="stepIndex === 0" @click="stepIndex--">上一步</el-button>
      <el-button
        type="primary"
        :disabled="stepIndex === scenario.steps.length - 1"
        @click="stepIndex++"
        >下一步</el-button
      >
      <el-button @click="stepIndex = 0">重新演示</el-button>
      <router-link :to="scenario.actual ? '/trace' : '/database'">{{
        scenario.actual ? '采集一次真实健康请求 →' : '查看 MySQL 真实索引实验 →'
      }}</router-link>
    </div>
    <p class="muted storage-boundary">
      教学场景只改变本页展示，不连接数据库、不写缓存，也不展示模拟耗时。缓存模式参考
      <a
        href="https://redis.io/docs/latest/develop/use-cases/cache-aside/"
        target="_blank"
        rel="noreferrer"
        >Redis 官方 Cache-Aside 指南 ↗</a
      >。
    </p>
  </section>
</template>
