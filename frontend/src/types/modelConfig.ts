export interface ModelConfig {
  id: number
  model_id: string
  display_name: string | null
  group_name: string | null
  description: string | null
  icon: string | null
  manual_prompt_price: number | null
  manual_completion_price: number | null
  is_enabled: boolean
  sort_order: number
  created_at: string | null
}

export interface ModelConfigCreate {
  model_id: string
  display_name?: string
  group_name?: string
  description?: string
  icon?: string
  manual_prompt_price?: number | null
  manual_completion_price?: number | null
  is_enabled?: boolean
  sort_order?: number
}

export type ModelConfigUpdate = Partial<ModelConfigCreate>
