import apiClient from '@/api/client'
import type { ApiKeyCreateResponse, ApiKeyResponse } from '@/types'

export async function listKeys(): Promise<ApiKeyResponse[]> {
  const { data } = await apiClient.get('/api/user/keys')
  return data
}

export async function createKey(label: string): Promise<ApiKeyCreateResponse> {
  const { data } = await apiClient.post('/api/user/keys', { label })
  return data
}

export async function deleteKey(id: number): Promise<{ status: string }> {
  const { data } = await apiClient.delete(`/api/user/keys/${id}`)
  return data
}
