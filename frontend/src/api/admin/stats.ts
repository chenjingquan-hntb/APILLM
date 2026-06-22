import apiClient from '@/api/client'
import type { AdminStatsOverview, StatsByModel, StatsByUpstream } from '@/types'

export async function getOverview(): Promise<AdminStatsOverview> {
  const { data } = await apiClient.get('/api/admin/stats/overview')
  return data
}

export async function getByModel(): Promise<StatsByModel[]> {
  const { data } = await apiClient.get('/api/admin/stats/by-model')
  return data
}

export async function getByUpstream(): Promise<StatsByUpstream[]> {
  const { data } = await apiClient.get('/api/admin/stats/by-upstream')
  return data
}
