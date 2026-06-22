<script setup lang="ts">
import type { ModelConfig } from '@/types'

defineProps<{
  models: ModelConfig[]
  loading: boolean
}>()

const emit = defineEmits<{
  edit: [id: number]
  delete: [id: number]
}>()

function onEdit(row: ModelConfig) {
  emit('edit', row.id)
}

function onDelete(row: ModelConfig) {
  emit('delete', row.id)
}

function priceStr(value: number | null) {
  if (value == null) return '自动'
  return `¥${(value * 1000).toFixed(3)}`
}
</script>

<template>
  <el-table :data="models" v-loading="loading" style="width: 100%">
    <el-table-column label="模型ID" min-width="180">
      <template #default="{ row }">
        <code>{{ row.model_id }}</code>
      </template>
    </el-table-column>
    <el-table-column prop="display_name" label="展示名" min-width="140" />
    <el-table-column label="手动价格" min-width="120">
      <template #default="{ row }">
        {{ priceStr(row.manual_prompt_price) }}
      </template>
    </el-table-column>
    <el-table-column label="状态" width="100">
      <template #default="{ row }">
        <span class="status-cell">
          <span class="dot" :class="row.is_enabled ? 'ok' : 'error'"></span>
          {{ row.is_enabled ? '启用' : '禁用' }}
        </span>
      </template>
    </el-table-column>
    <el-table-column label="操作" width="130" fixed="right">
      <template #default="{ row }">
        <el-button link type="primary" size="small" @click="onEdit(row)">编辑</el-button>
        <el-button link type="danger" size="small" @click="onDelete(row)">删除</el-button>
      </template>
    </el-table-column>
  </el-table>
</template>

<style scoped>
.status-cell {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
}

.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.dot.ok {
  background: var(--accent-green);
  box-shadow: 0 0 6px var(--accent-green-glow);
}

.dot.error {
  background: var(--accent-red);
  box-shadow: 0 0 6px var(--accent-red-glow);
}
</style>
