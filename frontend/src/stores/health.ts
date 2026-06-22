import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as healthApi from '@/api/health'
import type { HealthResponse, UpstreamSummary } from '@/types'

export const useHealthStore = defineStore('health', () => {
  const status = ref<'ok' | 'degraded' | 'error' | 'checking'>('checking')
  const upstreams = ref<UpstreamSummary>({ total: 0, healthy: 0, degraded: 0, unhealthy: 0 })
  const lastChecked = ref<string | null>(null)
  let timer: ReturnType<typeof setInterval> | null = null

  async function refresh() {
    status.value = 'checking'
    try {
      const data: HealthResponse = await healthApi.getHealth()
      status.value = data.status
      upstreams.value = data.upstreams
      lastChecked.value = new Date().toLocaleTimeString()
    } catch {
      status.value = 'error'
    }
  }

  function startPolling(intervalMs = 30000) {
    if (timer) return
    refresh()
    timer = setInterval(() => refresh(), intervalMs)
  }

  function stopPolling() {
    if (timer) {
      clearInterval(timer)
      timer = null
    }
  }

  return {
    status,
    upstreams,
    lastChecked,
    refresh,
    startPolling,
    stopPolling,
  }
})
