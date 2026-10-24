<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { api } from '../api'
import { useRequest } from '../composables/useRequest'
import AsyncState from '../components/AsyncState.vue'
const route = useRoute(),
  detail = computed(() => route.path.includes('002-mysql'))
const { data, loading, error, reload } = useRequest(api.experiment)
</script>
<template>
  <header class="page-heading">
    <div>
      <p class="eyebrow">05 / EXPERIMENT NOTEBOOK</p>
      <h1>{{ detail ? '从现象走到可验证的解释。' : '每个结论，都有一条证据链。' }}</h1>
      <p>观察 → 提问 → 假设 → 改变参数 → 比较 → 解释局限</p>
    </div>
    <span class="badge measured">Recorded experiment</span>
  </header>
  <AsyncState :loading="loading" :error="error" :empty="!data" @retry="reload">
    <template v-if="data">
      <router-link v-if="!detail" :to="`/experiments/${data.id}`" class="experiment-card panel">
        <span class="experiment-number">002</span>
        <div>
          <span class="eyebrow">MYSQL / INDEX / PAGINATION</span>
          <h2>{{ data.title }}</h2>
          <p>{{ data.question }}</p>
          <div class="tags">
            <span v-for="scale in data.scales" :key="scale"
              >{{ scale.toLocaleString() }} orders</span
            ><span>6 SQL cases</span>
          </div>
        </div>
        <span class="arrow">↗</span>
      </router-link>
      <div v-else class="notebook">
        <section class="panel">
          <p class="eyebrow">01 · 观察与问题</p>
          <h2>{{ data.question }}</h2>
          <p>{{ data.objective }}</p>
          <ul>
            <li v-for="item in data.observations" :key="item">{{ item }}</li>
          </ul>
        </section>
        <section class="panel">
          <p class="eyebrow">02 · 假设与条件</p>
          <h2>{{ data.hypothesis }}</h2>
          <ul>
            <li v-for="item in data.parameters" :key="item">{{ item }}</li>
          </ul>
        </section>
        <section class="panel">
          <p class="eyebrow">03 · 用证据验证</p>
          <h2>改变访问路径，而非只看秒表。</h2>
          <ul>
            <li v-for="item in data.explanation" :key="item">{{ item }}</li>
          </ul>
          <router-link to="/database" class="primary-link">打开数据与执行计划对照 →</router-link>
        </section>
        <section class="panel">
          <p class="eyebrow">04 · 原始数据与源码</p>
          <a :href="data.source.url" target="_blank" rel="noreferrer" class="source-link"
            >↗ {{ data.source.label }}</a
          ><a
            v-for="item in data.sources"
            :key="item.path"
            :href="item.url"
            target="_blank"
            rel="noreferrer"
            class="source-link"
            >↗ {{ item.label }} · {{ item.path }}</a
          >
        </section>
        <div class="callout">
          <p v-for="note in data.limitations" :key="note">{{ note }}</p>
        </div>
      </div>
    </template>
  </AsyncState>
</template>
