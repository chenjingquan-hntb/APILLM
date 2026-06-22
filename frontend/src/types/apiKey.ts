export interface ApiKeyResponse {
  id: number
  key_prefix: string
  label: string
  created_at: string | null
  last_used_at: string | null
}

export interface ApiKeyCreateResponse {
  id: number
  key: string
  label: string
  created_at: string | null
}
