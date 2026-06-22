import apiClient from '@/api/client'
import type { ModelConfig, ModelConfigCreate, ModelConfigUpdate } from '@/types'

export async function listModelConfigs(): Promise<ModelConfig[]> {
  const { data } = await apiClient.get('/api/admin/models')
  return data
}

export async function createModelConfig(body: ModelConfigCreate): Promise<{ id: number; model_id: string }> {
  const { data } = await apiClient.post('/api/admin/models', body)
  return data
}

export async function updateModelConfig(id: number, body: ModelConfigUpdate): Promise<{ status: string }> {
  const { data } = await apiClient.put(`/api/admin/models/${id}`, body)
  return data
}

export async function deleteModelConfig(id: number): Promise<{ status: string }> {
  const { data } = await apiClient.delete(`/api/admin/models/${id}`)
  return data
}
