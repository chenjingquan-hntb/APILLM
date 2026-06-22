export interface UsageLog {
  id: number
  model: string
  user_id?: number
  upstream_id: number | null
  tokens_in: number
  tokens_out: number
  cost: number
  status: string
  error_message: string | null
  latency_ms: number | null
  created_at: string | null
}

export interface PaginatedLogs {
  total: number
  page: number
  size: number
  data: UsageLog[]
}
