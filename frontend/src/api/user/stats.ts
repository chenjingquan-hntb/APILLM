import apiClient from '@/api/client'
import type { UserStats } from '@/types'

export async function getStats(): Promise<UserStats> {
  const { data } = await apiClient.get('/api/user/stats')
  return data
}
