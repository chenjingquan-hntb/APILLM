export interface UpstreamSummary {
  total: number
  healthy: number
  degraded: number
  unhealthy: number
}

export interface HealthResponse {
  status: 'ok' | 'degraded'
  redis: 'ok' | 'disconnected'
  db: 'ok' | 'disconnected'
  upstreams: UpstreamSummary
}
