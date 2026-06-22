import apiClient from '@/api/client'
import type { LoginRequest, TokenResponse, RefreshRequest, UserInfo } from '@/types'

export async function login(body: LoginRequest): Promise<TokenResponse> {
  const { data } = await apiClient.post('/api/auth/login', body)
  return data
}

export async function refresh(body: RefreshRequest): Promise<TokenResponse> {
  const { data } = await apiClient.post('/api/auth/refresh', body)
  return data
}

export async function logout(body: RefreshRequest): Promise<{ status: string }> {
  const { data } = await apiClient.post('/api/auth/logout', body)
  return data
}

export async function fetchMe(): Promise<UserInfo> {
  const { data } = await apiClient.get('/api/auth/me')
  return data
}
