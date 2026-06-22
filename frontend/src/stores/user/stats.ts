import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as statsApi from '@/api/user/stats'
import type { UserStats } from '@/types'

export const useUserStatsStore = defineStore('userStats', () => {
  const stats = ref<UserStats | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchStats() {
    loading.value = true
    error.value = null
    try {
      stats.value = await statsApi.getStats()
    } catch (e) {
      error.value = e instanceof Error ? e.message : '加载失败'
    } finally {
      loading.value = false
    }
  }

  return {
    stats,
    loading,
    error,
    fetchStats,
  }
})
