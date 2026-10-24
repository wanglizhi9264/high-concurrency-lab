<script setup lang="ts">
import { api } from '../api'
import { useRequest } from '../composables/useRequest'
import AsyncState from './AsyncState.vue'
defineProps<{ compact?: boolean }>()
const { data, loading, error, reload } = useRequest(api.probeGuide)
const sources = [
  ['HTTP 路由', 'src/concurrency_lab/api/routes/visualization.py'],
  ['探针与聚合', 'src/concurrency_lab/services/health.py'],
  ['MySQL 池', 'src/concurrency_lab/db/session.py'],
  ['Redis 客户端', 'src/concurrency_lab/cache/client.py'],
]
</script>
<template>
  <details class="panel probe-guide" :open="!compact">
    <summary>请求到底发到哪里？展开查看 URL、数据库、命令与成功失败规则</summary>
    <p>
      探针就是一个小检查函数：尝试执行固定命令，在限定时间内得到可用结果。它不是后台不断扫描数据库的任务。
    </p>
    <AsyncState :loading="loading" :error="error" :empty="!data" @retry="reload">
      <template v-if="data">
        <div class="probe-request">
          <span class="badge measured">当前后端配置 · 非连接成功证明</span>
          <h2>点击“采集真实健康请求”时</h2>
          <code>GET /api/v1/observability/health-trace</code>
          <p>
            请求体：无。浏览器请求当前网页同源地址；本地 Vite 将 /api 请求代理到后端（开发默认
            127.0.0.1:18002，可由 API_PROXY_TARGET
            覆盖）。浏览器不直接连数据库，也不发送数据库密码。
          </p>
        </div>
        <ol class="probe-route">
          <li>
            <strong>浏览器 fetch</strong
            ><span
              >先记录浏览器开始时间，发送上面的 GET；请求读取有 12
              秒上限。这不是探针执行预算。</span
            >
          </li>
          <li>
            <strong>FastAPI health_trace(request)</strong
            ><span
              >路由已匹配后创建 TraceRecorder，从 app.state.resources 取 lifespan 创建的 Engine 和
              Redis 客户端。</span
            >
          </li>
          <li>
            <strong>readiness(...) → asyncio.gather(...)</strong
            ><span
              >同时启动 MySQL 和 Redis 检查。下面两张卡是并行分支，不是先 MySQL 再 Redis。</span
            >
          </li>
        </ol>
        <div class="storage-pair">
          <article class="storage-card mysql-card">
            <div class="storage-title">
              <strong>MySQL 探针</strong><span>mysql_ping(engine)</span>
            </div>
            <dl class="probe-fields">
              <dt>连接哪个库？</dt>
              <dd>
                <code data-testid="probe-database">{{ data.mysql_database }}</code
                >（当前应用库）
              </dd>
              <dt>查询哪张表？</dt>
              <dd>不查询任何业务表。SELECT 1 返回常量，不会扫描订单。</dd>
              <dt>具体执行</dt>
              <dd>
                engine.connect() 借用连接 → execute(text("SELECT 1")) → 退出 async with
                归还连接。池启用 pre_ping，借用时可能额外探测已有连接；当前路径不使用 ORM Session。
              </dd>
              <dt>成功的判断</dt>
              <dd>
                SQL 执行且连接作用域正常退出 → 函数返回 True → checks.mysql = "ok"。SQL 预期返回
                1；代码没有读取并比较该值。
              </dd>
              <dt>失败的判断</dt>
              <dd>连接、认证、SQL、退出连接发生异常，或超过检查预算 → False → "unavailable"。</dd>
            </dl>
            <code>SELECT 1</code>
          </article>
          <article class="storage-card redis-card">
            <div class="storage-title">
              <strong>Redis 探针</strong><span>redis_ping(client)</span>
            </div>
            <dl class="probe-fields">
              <dt>连接哪个库？</dt>
              <dd>Redis 逻辑库 {{ data.redis_database }}（客户端默认库）；PING 本身不读键。</dd>
              <dt>查询哪个键？</dt>
              <dd>没有键。不会执行 GET product:42，也不会填入缓存。</dd>
              <dt>具体执行</dt>
              <dd>
                复用 lifespan Redis 客户端及其连接池 → await client.ping() → redis-py 将正常 PONG
                转为 True。
              </dd>
              <dt>成功的判断</dt>
              <dd>bool(await client.ping()) 为 True → checks.redis = "ok"。</dd>
              <dt>失败的判断</dt>
              <dd>连接、认证、命令异常，返回 False，或超过检查预算 → "unavailable"。</dd>
            </dl>
            <code>PING → PONG → True</code>
          </article>
        </div>
        <ol class="probe-route" start="4">
          <li>
            <strong>bounded_check：每项检查各自有上限</strong
            ><span
              >当前每项总预算
              {{ data.readiness_timeout_seconds }} 秒，包住获取连接、命令与清理。MySQL 连接超时和
              Redis 连接/读写超时配置为 {{ data.io_timeout_seconds }} 秒；MySQL 池获取超时为
              {{ data.pool_timeout_seconds }}
              秒。更早触发的异常也会失败，实际时长不保证恰好等于预算。</span
            >
          </li>
          <li>
            <strong>聚合结果：all(value == "ok")</strong
            ><span
              >两个都 ok → HTTP 200；任一个 unavailable → HTTP
              503。某项先失败不会跳过另一项，要等两个有界检查完成。当前就绪策略要求 Redis
              也可用。</span
            >
          </li>
          <li>
            <strong>浏览器接收并展示 JSON</strong
            ><span
              >503 也能带回结构化 checks 和 events；fetch 本身不会因为 HTTP 503
              抛出网络错误，本页专门保留这类响应。回放控制只播放已收集记录，不控制数据库执行。</span
            >
          </li>
        </ol>
        <details>
          <summary>展开真实调用结构（与源码一致，省略埋点）</summary>
          <pre>
async def mysql_ping(engine):
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))
    return True

async def redis_ping(client):
    return bool(await client.ping())

async def bounded_check(check, budget):
    try:
        async with asyncio.timeout(budget):
            return await check()
    except Exception:
        return False

mysql, redis = await asyncio.gather(
    bounded_check(lambda: mysql_ping(engine), budget),
    bounded_check(lambda: redis_ping(client), budget),
)
healthy = mysql and redis
http_status = 200 if healthy else 503</pre>
        </details>
        <h3>这些请求分别做什么？</h3>
        <div class="probe-table-scroll">
          <table class="probe-table">
            <thead>
              <tr>
                <th>HTTP 请求（均无请求体）</th>
                <th>读哪里 / 执行什么</th>
                <th>返回什么</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>GET /health/live</td>
                <td>只运行路由，不访问 MySQL / Redis</td>
                <td>200 {"status":"alive"}；不证明数据库可用</td>
              </tr>
              <tr>
                <td>GET /health/ready</td>
                <td>并发 SELECT 1 / PING</td>
                <td>200 ready 或 503 unavailable，加 checks；没有事件列表</td>
              </tr>
              <tr>
                <td>GET /api/v1/observability/health-trace</td>
                <td>与 ready 使用同一个 readiness 服务，加实际埋点</td>
                <td>200 / 503，加 checks、events、server_elapsed_ms</td>
              </tr>
              <tr>
                <td>GET /api/v1/architecture</td>
                <td>读取代码中的架构目录及本进程初始化记录</td>
                <td>节点和连线；不会执行探针</td>
              </tr>
              <tr>
                <td>GET /api/v1/observability/probe-guide</td>
                <td>安全投影当前数据库名与超时设置</td>
                <td>本说明的数据；不会连接数据库</td>
              </tr>
              <tr>
                <td>GET /api/v1/experiments/002-mysql-index-baseline/results?scale=1000000</td>
                <td>
                  读取 docs/experiments/002-mysql-index-baseline/runs/ 的已保存 JSON；当时实验库为
                  concurrency_lab_exp_002_1000000
                </td>
                <td>基线与优化实测记录；此 HTTP 请求不重新执行 SQL</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="callout">
          <p>
            <strong>失败如何理解？</strong> unavailable
            统一表示该检查没有成功。公开接口隐藏异常原文，因此不能仅凭它断言“密码错”“端口错”或“超时”。下方教学场景会明确写出假设原因，真实记录不会猜测。
          </p>
          <p>
            <strong>Failed to fetch 与 503 不同：</strong
            >前者通常是浏览器没取得可读响应（网络、服务、代理等问题）；503
            是收到了服务器“不就绪”的响应。先检查页面服务和后端是否启动，再看 checks；Vite 502/500
            等代理错误也不等于某个数据库探针已执行。
          </p>
        </div>
        <div class="probe-sources">
          <a
            v-for="[label, path] in sources"
            :key="path"
            :href="`https://github.com/wanglizhi9264/high-concurrency-lab/blob/main/${path}`"
            target="_blank"
            rel="noreferrer"
            >{{ label }} ↗</a
          >
        </div>
        <router-link v-if="compact" to="/trace" class="primary-link"
          >去请求生命周期：采集真实结果 / 分步查看失败场景 →</router-link
        >
      </template>
    </AsyncState>
  </details>
</template>
