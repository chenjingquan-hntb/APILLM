import axios, { AxiosError, type InternalAxiosRequestConfig } from 'axios'

const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '',
  headers: { 'Content-Type': 'application/json' },
})

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem('apillm_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

let isRefreshing = false
let pendingRequests: Array<(token: string) => void> = []

apiClient.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean }
    if (error.response?.status === 401 && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve) => {
          pendingRequests.push((token: string) => {
            originalRequest.headers.Authorization = `Bearer ${token}`
            resolve(apiClient(originalRequest))
          })
        })
      }
      originalRequest._retry = true
      isRefreshing = true
      try {
        const refreshToken = localStorage.getItem('apillm_refresh')
        if (!refreshToken) throw new Error('No refresh token')
        const response = await axios.post('/api/auth/refresh', { refresh_token: refreshToken })
        const { access_token, refresh_token } = response.data as { access_token: string; refresh_token: string }
        localStorage.setItem('apillm_token', access_token)
        localStorage.setItem('apillm_refresh', refresh_token)
        apiClient.defaults.headers.common.Authorization = `Bearer ${access_token}`
        pendingRequests.forEach((cb) => cb(access_token))
        pendingRequests = []
        originalRequest.headers.Authorization = `Bearer ${access_token}`
        return apiClient(originalRequest)
      } catch (refreshError) {
        localStorage.removeItem('apillm_token')
        localStorage.removeItem('apillm_refresh')
        localStorage.removeItem('apillm_user')
        pendingRequests = []
        window.location.hash = '#/login'
        return Promise.reject(refreshError)
      } finally {
        isRefreshing = false
      }
    }
    const data = error.response?.data as { detail?: string; message?: string } | undefined
    const message = data?.detail || data?.message || error.message
    return Promise.reject(new Error(message))
  }
)

export default apiClient
