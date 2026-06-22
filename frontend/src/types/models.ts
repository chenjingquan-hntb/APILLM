export interface ModelCard {
  id: string
  object: string
  created: number
  owned_by: string
  upstream_count: number
  lowest_price: number | null
  available: boolean
}

export interface ModelList {
  object: string
  data: ModelCard[]
}
