<script setup lang="ts">
import { RefreshRight, Warning } from '@element-plus/icons-vue'
import type { ModelCard } from '@/types'
import ModelCardItem from './ModelCardItem.vue'

defineProps<{
  models: ModelCard[]
  loading: boolean
  error: string | null
}>()

const emit = defineEmits<{
  refresh: []
}>()
</script>

<template>
  <div v-if="loading" v-loading="loading" class="loading-state">
    <span class="text-muted">加载中…</span>
  </div>
  <div v-else-if="error" class="error-state">
    <el-icon class="icon"><Warning /></el-icon>
    <span>加载失败: {{ error }}</span>
    <el-button :icon="RefreshRight" size="small" @click="emit('refresh')">重试</el-button>
  </div>
  <div v-else-if="models.length === 0" class="empty-state">
    <span class="text-muted">暂无模型</span>
  </div>
  <div v-else class="card-grid">
    <ModelCardItem v-for="model in models" :key="model.id" :model="model" />
  </div>
</template>

<style scoped>
.card-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}

.loading-state,
.error-state,
.empty-state {
  min-height: 160px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  color: var(--text-secondary);
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
}

.error-state .icon {
  font-size: 1.5rem;
  color: var(--accent-red);
}

@media (max-width: 1024px) {
  .card-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 640px) {
  .card-grid {
    grid-template-columns: 1fr;
  }
}
</style>
