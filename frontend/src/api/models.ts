import apiClient from '@/api/client'
import type { ModelList } from '@/types'

export async function listModels(): Promise<ModelList> {
  const { data } = await apiClient.get('/v1/models')
  return data
}
