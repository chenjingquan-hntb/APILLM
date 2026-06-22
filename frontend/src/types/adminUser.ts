export interface AdminUser {
  id: number
  username: string
  role: 'admin' | 'user'
  balance: number
  is_active: boolean
  has_password: boolean
  created_at: string | null
}

export interface UserCreate {
  username: string
  password: string
  role?: string
}

export type UserUpdate = Partial<UserCreate> & { is_active?: boolean; balance?: number }
