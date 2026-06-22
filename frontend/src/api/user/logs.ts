import apiClient from '@/api/client'
import type { UsageLog } from '@/types'

export async function listLogs(page = 1, size = 20): Promise<UsageLog[]> {
  const { data } = await apiClient.get('/api/user/logs', { params: { page, size } })
  return data
}
