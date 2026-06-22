<script setup lang="ts">
import type { Upstream } from '@/types'

defineProps<{
  upstreams: Upstream[]
  loading: boolean
}>()

const emit = defineEmits<{
  edit: [id: number]
  delete: [id: number]
}>()

function onEdit(row: Upstream) {
  emit('edit', row.id)
}

function onDelete(row: Upstream) {
  emit('delete', row.id)
}

function truncateUrl(url: string) {
  return url.length > 40 ? url.slice(0, 40) + '…' : url
}
</script>

<template>
  <el-table :data="upstreams" v-loading="loading" style="width: 100%">
    <el-table-column prop="name" label="名称" min-width="140" />
    <el-table-column prop="protocol" label="协议" width="100">
      <template #default="{ row }">
        <el-tag size="small">{{ row.protocol }}</el-tag>
      </template>
    </el-table-column>
    <el-table-column label="地址" min-width="200">
      <template #default="{ row }">
        <code>{{ truncateUrl(row.base_url) }}</code>
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
