<script setup lang="ts">
import { computed } from 'vue'
import type { ModelCard } from '@/types'

const props = defineProps<{
  model: ModelCard
}>()

const priceStr = computed(() => {
  if (props.model.lowest_price == null) return '暂无报价'
  return `¥${(props.model.lowest_price * 1000000).toFixed(3)}/M tokens`
})

const availClass = computed(() => (props.model.available ? 'card-ok' : 'card-err'))
const availText = computed(() => (props.model.available ? '可用' : '不可用'))
</script>

<template>
  <div class="model-card" :class="availClass">
    <div class="card-head">
      <code class="model-name">{{ model.id }}</code>
      <span class="upstream-badge">{{ model.upstream_count || 1 }}源</span>
    </div>
    <div class="card-price">{{ priceStr }}</div>
    <div class="card-foot">
      <span class="availability">
        <span class="dot" :class="availClass"></span>
        {{ availText }}
      </span>
    </div>
  </div>
</template>

<style scoped>
.model-card {
  padding: 1.25rem;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-left: 3px solid var(--border);
  border-radius: var(--radius-md);
  transition: border-color 0.2s, background-color 0.2s;
}

.model-card:hover {
  background: var(--bg-card-hover);
  border-color: var(--border-visible);
}

.model-card.card-ok {
  border-left-color: var(--accent-green);
}

.model-card.card-err {
  border-left-color: var(--accent-red);
  opacity: 0.7;
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  margin-bottom: 0.75rem;
}

.model-name {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-primary);
  word-break: break-all;
}

.upstream-badge {
  flex-shrink: 0;
  padding: 0.125rem 0.5rem;
  background: var(--bg-input);
  border-radius: 999px;
  font-size: 0.75rem;
  color: var(--text-secondary);
}

.card-price {
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.125rem;
  font-weight: 600;
  color: var(--accent-green);
  margin-bottom: 1rem;
}

.card-foot {
  display: flex;
  align-items: center;
}

.availability {
  display: inline-flex;
  align-items: center;
  gap: 0.375rem;
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
}

.dot.card-ok {
  background: var(--accent-green);
  box-shadow: 0 0 6px var(--accent-green-glow);
}

.dot.card-err {
  background: var(--accent-red);
  box-shadow: 0 0 6px var(--accent-red-glow);
}
</style>
