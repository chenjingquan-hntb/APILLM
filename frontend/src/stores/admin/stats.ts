import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as statsApi from '@/api/admin/stats'
import type { AdminStatsOverview, StatsByModel, StatsByUpstream } from '@/types'

export const useAdminStatsStore = defineStore('adminStats', () => {
  const overview = ref<AdminStatsOverview | null>(null)
  const byModel = ref<StatsByModel[]>([])
  const byUpstream = ref<StatsByUpstream[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchOverview() {
    try {
      overview.value = await statsApi.getOverview()
    } catch (e) {
      error.value = e instanceof Error ? e.message : '加载失败'
    }
  }

  async function fetchByModel() {
    try {
      byModel.value = await statsApi.getByModel()
    } catch (e) {
      error.value = e instanceof Error ? e.message : '加载失败'
    }
  }

  async function fetchByUpstream() {
    try {
      byUpstream.value = await statsApi.getByUpstream()
    } catch (e) {
      error.value = e instanceof Error ? e.message : '加载失败'
    }
  }

  async function fetchAll() {
    loading.value = true
    error.value = null
    await Promise.all([fetchOverview(), fetchByModel(), fetchByUpstream()])
    loading.value = false
  }

  return {
    overview,
    byModel,
    byUpstream,
    loading,
    error,
    fetchOverview,
    fetchByModel,
    fetchByUpstream,
    fetchAll,
  }
})
