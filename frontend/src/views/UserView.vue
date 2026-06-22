<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { Plus, RefreshRight, Delete, Wallet } from '@element-plus/icons-vue'
import { useUserKeysStore } from '@/stores/user/keys'
import { useUserLogsStore } from '@/stores/user/logs'
import { useUserStatsStore } from '@/stores/user/stats'
import { useToast } from '@/composables/useToast'
import StatCard from '@/components/common/StatCard.vue'
import type { ApiKeyResponse } from '@/types'

const route = useRoute()
const { showToast } = useToast()

const activeTab = ref((route.query.tab as string) || 'keys')

const keysStore = useUserKeysStore()
const logsStore = useUserLogsStore()
const statsStore = useUserStatsStore()

onMounted(() => {
  keysStore.fetchAll()
  logsStore.fetchLogs()
  statsStore.fetchStats()
})

async function createKey() {
  try {
    const { value } = await ElMessageBox.prompt('输入 Key 标签 (可选):', '创建 API Key', {
      inputValue: 'default',
      confirmButtonText: '创建',
      cancelButtonText: '取消',
    })
    const result = await keysStore.create(value || 'default')
    await ElMessageBox.alert(
      `新 API Key:\n\n${result.key}\n\n请立即复制保存，关闭后无法再次查看。`,
      '创建成功',
      { confirmButtonText: '我已复制' }
    )
  } catch {
    // cancelled
  }
}

async function deleteKey(row: ApiKeyResponse) {
  try {
    await ElMessageBox.confirm('确定删除此 API Key？此操作不可撤销。', '确认删除', { type: 'warning' })
    await keysStore.remove(row.id)
    showToast('已删除', 'success')
  } catch {
    // cancelled
  }
}

function formatDate(value: string | null) {
  return value ? value.slice(0, 16) : '—'
}

function refreshLogs() {
  logsStore.fetchLogs()
}

function refreshStats() {
  statsStore.fetchStats()
}
</script>

<template>
  <div class="container user-view">
    <el-tabs v-model="activeTab" type="border-card" class="user-tabs">
      <!-- API Keys -->
      <el-tab-pane label="API Key" name="keys">
        <div class="toolbar">
          <el-button type="primary" :icon="Plus" @click="createKey">创建 Key</el-button>
        </div>

        <el-table :data="keysStore.items" v-loading="keysStore.loading" style="width: 100%">
          <el-table-column prop="label" label="标签" />
          <el-table-column prop="key_prefix" label="Key 预览">
            <template #default="{ row }">
              <code>{{ row.key_prefix }}</code>
            </template>
          </el-table-column>
          <el-table-column label="创建时间">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="最后使用">
            <template #default="{ row }">
              {{ formatDate(row.last_used_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="100">
            <template #default="{ row }">
              <el-button link type="danger" size="small" :icon="Delete" @click="deleteKey(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <!-- Logs -->
      <el-tab-pane label="调用日志" name="logs">
        <div class="toolbar">
          <el-button :icon="RefreshRight" @click="refreshLogs">刷新</el-button>
        </div>

        <el-table :data="logsStore.items" v-loading="logsStore.loading" style="width: 100%">
          <el-table-column label="时间">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="模型">
            <template #default="{ row }">
              <code>{{ row.model }}</code>
            </template>
          </el-table-column>
          <el-table-column prop="upstream_id" label="上游">
            <template #default="{ row }">
              {{ row.upstream_id || '—' }}
            </template>
          </el-table-column>
          <el-table-column label="Token">
            <template #default="{ row }">
              {{ row.tokens_in }}+{{ row.tokens_out }}
            </template>
          </el-table-column>
          <el-table-column label="费用">
            <template #default="{ row }">
              ¥{{ row.cost.toFixed(4) }}
            </template>
          </el-table-column>
          <el-table-column label="状态">
            <template #default="{ row }">
              <span class="status-cell">
                <span class="dot" :class="row.status === 'success' ? 'ok' : 'error'"></span>
                {{ row.status }}
              </span>
            </template>
          </el-table-column>
        </el-table>

        <el-pagination
          v-model:current-page="logsStore.page"
          v-model:page-size="logsStore.size"
          :total="logsStore.total"
          layout="prev, pager, next"
          @current-change="logsStore.setPage"
        />
      </el-tab-pane>

      <!-- Stats -->
      <el-tab-pane label="统计" name="stats">
        <div class="toolbar">
          <el-button :icon="RefreshRight" @click="refreshStats">刷新</el-button>
        </div>
        <div class="stat-grid">
          <StatCard :value="statsStore.stats?.total_calls ?? 0" label="总调用" />
          <StatCard :value="(statsStore.stats?.total_tokens_in ?? 0) + (statsStore.stats?.total_tokens_out ?? 0)" label="总Token" />
          <StatCard :value="statsStore.stats?.total_cost ?? 0" label="总费用" prefix="¥" :decimals="4" />
          <StatCard :value="statsStore.stats?.balance ?? 0" label="余额" prefix="¥" :decimals="4" />
        </div>
      </el-tab-pane>

      <!-- Recharge -->
      <el-tab-pane label="充值" name="recharge">
        <div class="placeholder">
          <el-icon size="48" class="placeholder-icon"><component :is="Wallet" /></el-icon>
          <p>充值功能即将上线</p>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<style scoped>
.user-view {
  padding-top: 1.5rem;
  padding-bottom: 3rem;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.stat-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
}

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

.placeholder {
  min-height: 240px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  color: var(--text-muted);
}

.placeholder-icon {
  color: var(--text-secondary);
}
</style>
