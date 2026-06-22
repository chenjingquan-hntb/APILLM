import apiClient from '@/api/client'
import type { PaginatedLogs, UsageLog } from '@/types'

export async function listLogs(params: { page?: number; size?: number; model?: string; status?: string; user_id?: number }): Promise<PaginatedLogs> {
  const { data } = await apiClient.get('/api/admin/logs', { params })
  return data
}

export async function triggerPriceFetch(): Promise<{ status: string; upstreams_fetched: number }> {
  const { data } = await apiClient.post('/api/admin/prices/fetch')
  return data
}

export async function triggerHealthCheck(): Promise<{ status: string }> {
  const { data } = await apiClient.post('/api/admin/health/check')
  return data
}

export async function triggerPricingSync(): Promise<{ status: string; created: number; updated: number; total: number }> {
  const { data } = await apiClient.post('/api/admin/prices/sync')
  return data
}

export async function listPrices(params?: { model?: string }): Promise<{ prices: UsageLog[] }> {
  const { data } = await apiClient.get('/api/admin/prices', { params })
  return data
}
