export interface LoginRequest {
  username: string
  password: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface RefreshRequest {
  refresh_token: string
}

export interface UserInfo {
  id: number
  username: string
  role: 'admin' | 'user'
  balance: number
  is_active: boolean
}
