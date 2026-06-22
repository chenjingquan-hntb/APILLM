import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import * as authApi from '@/api/auth'
import type { LoginRequest, UserInfo } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const user = ref<UserInfo | null>(null)
  const accessToken = ref<string | null>(localStorage.getItem('apillm_token'))
  const refreshToken = ref<string | null>(localStorage.getItem('apillm_refresh'))

  const isAuthenticated = computed(() => !!accessToken.value)
  const isAdmin = computed(() => user.value?.role === 'admin')
  const username = computed(() => user.value?.username || '')

  function setTokens(access: string, refresh: string) {
    accessToken.value = access
    refreshToken.value = refresh
    localStorage.setItem('apillm_token', access)
    localStorage.setItem('apillm_refresh', refresh)
  }

  function setUser(info: UserInfo) {
    user.value = info
    localStorage.setItem('apillm_user', JSON.stringify(info))
  }

  function clearAuth() {
    user.value = null
    accessToken.value = null
    refreshToken.value = null
    localStorage.removeItem('apillm_token')
    localStorage.removeItem('apillm_refresh')
    localStorage.removeItem('apillm_user')
  }

  async function initFromStorage() {
    const storedUser = localStorage.getItem('apillm_user')
    if (storedUser) {
      try {
        user.value = JSON.parse(storedUser)
      } catch {
        user.value = null
      }
    }
  }

  async function login(body: LoginRequest) {
    const tokens = await authApi.login(body)
    setTokens(tokens.access_token, tokens.refresh_token)
    const me = await authApi.fetchMe()
    setUser(me)
  }

  async function tryRefresh() {
    const token = refreshToken.value || localStorage.getItem('apillm_refresh')
    if (!token) throw new Error('No refresh token')
    const tokens = await authApi.refresh({ refresh_token: token })
    setTokens(tokens.access_token, tokens.refresh_token)
    const me = await authApi.fetchMe()
    setUser(me)
  }

  async function logout() {
    const token = refreshToken.value
    if (token) {
      try {
        await authApi.logout({ refresh_token: token })
      } catch {
        // ignore
      }
    }
    clearAuth()
  }

  return {
    user,
    accessToken,
    refreshToken,
    isAuthenticated,
    isAdmin,
    username,
    setTokens,
    setUser,
    clearAuth,
    initFromStorage,
    login,
    tryRefresh,
    logout,
  }
})
