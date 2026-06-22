import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as logsApi from '@/api/user/logs'
import type { UsageLog } from '@/types'

export const useUserLogsStore = defineStore('userLogs', () => {
  const items = ref<UsageLog[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)
  const page = ref(1)
  const size = ref(20)
  const total = ref(0)

  async function fetchLogs() {
    loading.value = true
    error.value = null
    try {
      const data = await logsApi.listLogs(page.value, size.value)
      items.value = data
      total.value = data.length
    } catch (e) {
      error.value = e instanceof Error ? e.message : '加载失败'
    } finally {
      loading.value = false
    }
  }

  function setPage(p: number) {
    page.value = p
    fetchLogs()
  }

  return {
    items,
    loading,
    error,
    page,
    size,
    total,
    fetchLogs,
    setPage,
  }
})
