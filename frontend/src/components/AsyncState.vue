<script setup lang="ts">
defineProps<{ loading: boolean; error: string; empty?: boolean }>()
defineEmits<{ retry: [] }>()
</script>
<template>
  <div v-if="loading" class="state" role="status">正在读取可信数据…</div>
  <div v-else-if="error" class="state error" role="alert">
    {{ error }} <el-button @click="$emit('retry')">重试</el-button>
  </div>
  <div v-else-if="empty" class="state">暂无数据，尚未接入观测。</div>
  <slot v-else />
</template>
