export interface AdminStatsOverview {
  total_calls_24h: number
  total_tokens_in_24h: number
  total_tokens_out_24h: number
  total_cost_24h: number
  active_users_24h: number
}

export interface StatsByModel {
  model: string
  calls: number
  tokens_in: number
  tokens_out: number
  cost: number
}

export interface StatsByUpstream {
  upstream_id: number
  calls: number
  tokens_in: number
  tokens_out: number
  cost: number
}

export interface UserStats {
  total_calls: number
  total_tokens_in: number
  total_tokens_out: number
  total_cost: number
  balance: number
}
