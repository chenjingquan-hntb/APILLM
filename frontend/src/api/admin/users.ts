import apiClient from '@/api/client'
import type { AdminUser, UserCreate, UserUpdate } from '@/types'

export async function listUsers(): Promise<AdminUser[]> {
  const { data } = await apiClient.get('/api/admin/users')
  return data
}

export async function createUser(body: UserCreate): Promise<{ id: number; username: string; role: string }> {
  const { data } = await apiClient.post('/api/admin/users', body)
  return data
}

export async function updateUser(id: number, body: UserUpdate): Promise<{ status: string }> {
  const { data } = await apiClient.put(`/api/admin/users/${id}`, body)
  return data
}

export async function deleteUser(id: number): Promise<{ status: string }> {
  const { data } = await apiClient.delete(`/api/admin/users/${id}`)
  return data
}
