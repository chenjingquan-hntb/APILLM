<script setup lang="ts">
defineProps<{
  value: number | string
  label: string
  prefix?: string
  decimals?: number
}>()

function formatValue(value: number | string, prefix?: string, decimals?: number) {
  const num = typeof value === 'string' ? parseFloat(value) : value
  if (prefix === '¥') {
    return `¥${num.toFixed(decimals ?? 4)}`
  }
  return num.toLocaleString('zh-CN', {
    minimumFractionDigits: decimals ?? 0,
    maximumFractionDigits: decimals ?? 0,
  })
}
</script>

<template>
  <div class="stat-card">
    <div class="stat-value">{{ formatValue(value, prefix, decimals) }}</div>
    <div class="stat-label">{{ label }}</div>
  </div>
</template>

<style scoped>
.stat-card {
  flex: 1 1 200px;
  min-width: 160px;
  padding: 1.25rem;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  text-align: center;
  transition: border-color 0.2s;
}

.stat-card:hover {
  border-color: var(--border-visible);
}

.stat-value {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.75rem;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 0.375rem;
}

.stat-label {
  font-size: 0.8125rem;
  color: var(--text-muted);
}
</style>
