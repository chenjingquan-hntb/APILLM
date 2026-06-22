<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { Plus, Refresh, FirstAidKit, Download } from '@element-plus/icons-vue'
import { useAdminUpstreamsStore } from '@/stores/admin/upstreams'
import { useAdminModelConfigsStore } from '@/stores/admin/modelConfigs'
import { useAdminUsersStore } from '@/stores/admin/users'
import { useAdminStatsStore } from '@/stores/admin/stats'
import { useHealthStore } from '@/stores/health'
import { useToast } from '@/composables/useToast'
import { triggerHealthCheck, triggerPriceFetch, triggerPricingSync } from '@/api/admin/actions'
import UpstreamTable from '@/components/admin/UpstreamTable.vue'
import UpstreamForm from '@/components/admin/UpstreamForm.vue'
import ModelConfigTable from '@/components/admin/ModelConfigTable.vue'
import ModelConfigForm from '@/components/admin/ModelConfigForm.vue'
import AdminUserTable from '@/components/admin/AdminUserTable.vue'
import UserForm from '@/components/admin/UserForm.vue'
import StatCard from '@/components/common/StatCard.vue'
import type { ModelConfigCreate, ModelConfigUpdate, UpstreamCreate, UpstreamUpdate, UserCreate, UserUpdate } from '@/types'

const route = useRoute()
const router = useRouter()
const { showToast } = useToast()

const activeTab = ref((route.query.tab as string) || 'upstreams')

watch(activeTab, (tab) => {
  router.replace({ path: '/admin', query: { tab } })
})

watch(() => route.query.tab, (tab) => {
  if (tab && typeof tab === 'string') {
    activeTab.value = tab
  }
})

const upstreamsStore = useAdminUpstreamsStore()
const modelConfigsStore = useAdminModelConfigsStore()
const usersStore = useAdminUsersStore()
const statsStore = useAdminStatsStore()
const healthStore = useHealthStore()

onMounted(() => {
  upstreamsStore.fetchAll()
  modelConfigsStore.fetchAll()
  usersStore.fetchAll()
  statsStore.fetchAll()
})

// Upstream modal
const upstreamModalVisible = ref(false)
const editingUpstreamId = ref<number | null>(null)
const editingUpstream = computed(() => {
  if (!editingUpstreamId.value) return null
  return upstreamsStore.items.find((u) => u.id === editingUpstreamId.value) || null
})

function openUpstreamModal(id?: number) {
  editingUpstreamId.value = id ?? null
  upstreamModalVisible.value = true
}

async function saveUpstream(data: UpstreamCreate | UpstreamUpdate) {
  try {
    if (editingUpstreamId.value) {
      await upstreamsStore.update(editingUpstreamId.value, data as UpstreamUpdate)
    } else {
      await upstreamsStore.create(data as UpstreamCreate)
    }
    upstreamModalVisible.value = false
    showToast('上游已保存', 'success')
    await triggerHealthCheck()
    await triggerPriceFetch()
    await new Promise((r) => setTimeout(r, 2000))
    await healthStore.refresh()
    showToast('健康检查和价格抓取完成', 'success')
  } catch (e) {
    showToast(e instanceof Error ? e.message : '保存失败', 'error')
  }
}

async function deleteUpstream(id: number) {
  try {
    await ElMessageBox.confirm('确定删除此上游？', '确认删除', { type: 'warning' })
    await upstreamsStore.remove(id)
    showToast('已删除', 'success')
  } catch {
    // cancelled
  }
}

async function fetchPrices() {
  try {
    const res = await triggerPriceFetch()
    showToast(`价格抓取完成，已抓取 ${res.upstreams_fetched} 个上游`, 'success')
  } catch (e) {
    showToast(e instanceof Error ? e.message : '抓取失败', 'error')
  }
}

async function checkHealth() {
  try {
    await triggerHealthCheck()
    await new Promise((r) => setTimeout(r, 2000))
    await healthStore.refresh()
    showToast('健康检查完成', 'success')
  } catch (e) {
    showToast(e instanceof Error ? e.message : '检查失败', 'error')
  }
}

async function syncPricing() {
  try {
    const res = await triggerPricingSync()
    showToast(`定价同步完成：新建 ${res.created}，更新 ${res.updated}`, 'success')
  } catch (e) {
    showToast(e instanceof Error ? e.message : '同步失败', 'error')
  }
}

// Model modal
const modelModalVisible = ref(false)
const editingModelId = ref<number | null>(null)
const editingModel = computed(() => {
  if (!editingModelId.value) return null
  return modelConfigsStore.items.find((m) => m.id === editingModelId.value) || null
})

function openModelModal(id?: number) {
  editingModelId.value = id ?? null
  modelModalVisible.value = true
}

async function saveModel(data: ModelConfigCreate | ModelConfigUpdate) {
  try {
    if (editingModelId.value) {
      await modelConfigsStore.update(editingModelId.value, data as ModelConfigUpdate)
    } else {
      await modelConfigsStore.create(data as ModelConfigCreate)
    }
    modelModalVisible.value = false
    showToast('模型配置已保存', 'success')
  } catch (e) {
    showToast(e instanceof Error ? e.message : '保存失败', 'error')
  }
}

async function deleteModel(id: number) {
  try {
    await ElMessageBox.confirm('确定删除此模型配置？', '确认删除', { type: 'warning' })
    await modelConfigsStore.remove(id)
    showToast('已删除', 'success')
  } catch {
    // cancelled
  }
}

// User modal
const userModalVisible = ref(false)
const editingUserId = ref<number | null>(null)
const editingUser = computed(() => {
  if (!editingUserId.value) return null
  return usersStore.items.find((u) => u.id === editingUserId.value) || null
})

function openUserModal(id?: number) {
  editingUserId.value = id ?? null
  userModalVisible.value = true
}

async function saveUser(data: UserCreate | UserUpdate) {
  try {
    if (editingUserId.value) {
      await usersStore.update(editingUserId.value, data as UserUpdate)
    } else {
      await usersStore.create(data as UserCreate)
    }
    userModalVisible.value = false
    showToast('用户已保存', 'success')
  } catch (e) {
    showToast(e instanceof Error ? e.message : '保存失败', 'error')
  }
}

async function deleteUser(id: number) {
  try {
    await ElMessageBox.confirm('确定删除此用户？', '确认删除', { type: 'warning' })
    await usersStore.remove(id)
    showToast('已删除', 'success')
  } catch {
    // cancelled
  }
}

// Stats
const statsMode = ref<'models' | 'upstreams'>('models')

const statsTableData = computed(() => {
  return statsMode.value === 'models'
    ? statsStore.byModel.map((item) => ({ ...item, dimension: item.model }))
    : statsStore.byUpstream.map((item) => ({ ...item, dimension: `#${item.upstream_id}` }))
})

function refreshStats() {
  statsStore.fetchAll()
}
</script>

<template>
  <div class="container admin-view">
    <el-tabs v-model="activeTab" type="border-card" class="admin-tabs">
      <!-- Upstreams -->
      <el-tab-pane label="上游管理" name="upstreams">
        <div class="toolbar">
          <el-button type="primary" :icon="Plus" @click="openUpstreamModal()">新增上游</el-button>
          <el-button :icon="Refresh" @click="fetchPrices">抓取价格</el-button>
          <el-button :icon="FirstAidKit" @click="checkHealth">健康检查</el-button>
          <el-button :icon="Download" @click="syncPricing">同步定价</el-button>
        </div>
        <UpstreamTable :upstreams="upstreamsStore.items" :loading="upstreamsStore.loading" @edit="openUpstreamModal" @delete="deleteUpstream" />
      </el-tab-pane>

      <!-- Models -->
      <el-tab-pane label="模型配置" name="models">
        <div class="toolbar">
          <el-button type="primary" :icon="Plus" @click="openModelModal()">新增模型</el-button>
        </div>
        <ModelConfigTable :models="modelConfigsStore.items" :loading="modelConfigsStore.loading" @edit="openModelModal" @delete="deleteModel" />
      </el-tab-pane>

      <!-- Users -->
      <el-tab-pane label="用户管理" name="users">
        <div class="toolbar">
          <el-button type="primary" :icon="Plus" @click="openUserModal()">新建用户</el-button>
        </div>
        <AdminUserTable :users="usersStore.items" :loading="usersStore.loading" @edit="openUserModal" @delete="deleteUser" />
      </el-tab-pane>

      <!-- Stats -->
      <el-tab-pane label="数据看板" name="stats">
        <div class="stat-grid">
          <StatCard :value="statsStore.overview?.total_calls_24h ?? 0" label="24h调用" />
          <StatCard :value="(statsStore.overview?.total_tokens_in_24h ?? 0) + (statsStore.overview?.total_tokens_out_24h ?? 0)" label="24h Token" />
          <StatCard :value="statsStore.overview?.total_cost_24h ?? 0" label="24h费用" prefix="¥" :decimals="4" />
          <StatCard :value="statsStore.overview?.active_users_24h ?? 0" label="活跃用户" />
        </div>

        <div class="toolbar">
          <el-radio-group v-model="statsMode">
            <el-radio-button label="models">按模型统计</el-radio-button>
            <el-radio-button label="upstreams">按上游统计</el-radio-button>
          </el-radio-group>
          <el-button :icon="Refresh" @click="refreshStats">刷新</el-button>
        </div>

        <el-table :data="statsTableData" v-loading="statsStore.loading" style="width: 100%">
          <el-table-column prop="dimension" :label="statsMode === 'models' ? '模型' : '上游'" min-width="160">
            <template #default="{ row }">
              <code v-if="statsMode === 'models'">{{ row.dimension }}</code>
              <span v-else>{{ row.dimension }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="calls" label="调用次数" />
          <el-table-column prop="tokens_in" label="Token输入" />
          <el-table-column prop="tokens_out" label="Token输出" />
          <el-table-column label="费用">
            <template #default="{ row }">
              ¥{{ row.cost.toFixed(4) }}
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- Upstream Modal -->
    <el-dialog v-model="upstreamModalVisible" :title="editingUpstreamId ? '编辑上游' : '新增上游'" width="560px">
      <UpstreamForm :upstream="editingUpstream" @submit="saveUpstream" />
    </el-dialog>

    <!-- Model Modal -->
    <el-dialog v-model="modelModalVisible" :title="editingModelId ? '编辑模型配置' : '新增模型配置'" width="480px">
      <ModelConfigForm :model-config="editingModel" @submit="saveModel" />
    </el-dialog>

    <!-- User Modal -->
    <el-dialog v-model="userModalVisible" :title="editingUserId ? '编辑用户' : '新建用户'" width="480px">
      <UserForm :user="editingUser" @submit="saveUser" />
    </el-dialog>
  </div>
</template>

<style scoped>
.admin-view {
  padding-top: 1.5rem;
  padding-bottom: 3rem;
}

.admin-tabs {
  --el-tabs-header-bg-color: var(--bg-card);
  --el-tabs-content-bg-color: var(--bg-card);
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
  flex-wrap: wrap;
}

.stat-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  margin-bottom: 1.5rem;
}
</style>
