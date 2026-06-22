export interface Upstream {
  id: number
  name: string
  base_url: string
  api_key: string
  protocol: 'openai' | 'anthropic'
  priority: number
  markup_rate: number
  is_enabled: boolean
  pricing_config: Record<string, unknown> | null
  created_at: string | null
}

export interface UpstreamCreate {
  name: string
  base_url: string
  api_key: string
  protocol: string
  priority?: number
  markup_rate?: number
  is_enabled?: boolean
  pricing_config?: Record<string, unknown> | null
}

export type UpstreamUpdate = Partial<UpstreamCreate>
