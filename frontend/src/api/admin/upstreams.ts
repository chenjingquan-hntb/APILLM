import apiClient from '@/api/client'
import type { Upstream, UpstreamCreate, UpstreamUpdate } from '@/types'

export async function listUpstreams(): Promise<Upstream[]> {
  const { data } = await apiClient.get('/api/admin/upstreams')
  return data
}

export async function createUpstream(body: UpstreamCreate): Promise<{ id: number; name: string }> {
  const { data } = await apiClient.post('/api/admin/upstreams', body)
  return data
}

export async function updateUpstream(id: number, body: UpstreamUpdate): Promise<{ status: string }> {
  const { data } = await apiClient.put(`/api/admin/upstreams/${id}`, body)
  return data
}

export async function deleteUpstream(id: number): Promise<{ status: string }> {
  const { data } = await apiClient.delete(`/api/admin/upstreams/${id}`)
  return data
}
