<script setup lang="ts">
import { useAuthStore } from '@/stores/auth'
import { UserFilled, User } from '@element-plus/icons-vue'
import type { AdminUser } from '@/types'

const props = defineProps<{
  users: AdminUser[]
  loading: boolean
}>()

const emit = defineEmits<{
  edit: [id: number]
  delete: [id: number]
}>()

const auth = useAuthStore()

function onEdit(row: AdminUser) {
  emit('edit', row.id)
}

function onDelete(row: AdminUser) {
  emit('delete', row.id)
}

function isSelf(row: AdminUser) {
  return auth.user?.id === row.id
}
</script>

<template>
  <el-table :data="users" v-loading="loading" style="width: 100%">
    <el-table-column prop="id" label="ID" width="70" />
    <el-table-column prop="username" label="用户名" min-width="120" />
    <el-table-column label="角色" width="100">
      <template #default="{ row }">
        <el-tag size="small" :type="row.role === 'admin' ? 'warning' : 'info'">
          <template v-if="row.role === 'admin'">
            <el-icon class="role-icon"><UserFilled /></el-icon> 管理员
          </template>
          <template v-else>
            <el-icon class="role-icon"><User /></el-icon> 用户
          </template>
        </el-tag>
      </template>
    </el-table-column>
    <el-table-column prop="balance" label="余额" width="100">
      <template #default="{ row }">
        ¥{{ row.balance.toFixed(2) }}
      </template>
    </el-table-column>
    <el-table-column label="状态" width="100">
      <template #default="{ row }">
        <span class="status-cell">
          <span class="dot" :class="row.is_active ? 'ok' : 'error'"></span>
          {{ row.is_active ? '激活' : '禁用' }}
        </span>
      </template>
    </el-table-column>
    <el-table-column label="操作" width="130" fixed="right">
      <template #default="{ row }">
        <el-button link type="primary" size="small" @click="onEdit(row)">编辑</el-button>
        <el-button v-if="!isSelf(row)" link type="danger" size="small" @click="onDelete(row)">删除</el-button>
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

.role-icon {
  margin-right: 0.25rem;
  font-size: 0.75rem;
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
