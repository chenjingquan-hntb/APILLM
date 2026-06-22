<script setup lang="ts">
import { computed } from 'vue'
import { useHealthStore } from '@/stores/health'
import { Refresh } from '@element-plus/icons-vue'

const healthStore = useHealthStore()

const statusClass = computed(() => {
  switch (healthStore.status) {
    case 'ok':
      return 'ok'
    case 'degraded':
      return 'warn'
    default:
      return 'error'
  }
})

const statusText = computed(() => {
  switch (healthStore.status) {
    case 'ok':
      return '正常'
    case 'degraded':
      return '降级'
    case 'checking':
      return '检查中'
    default:
      return '异常'
  }
})

async function refresh() {
  await healthStore.refresh()
}
</script>

<template>
  <div class="health-bar">
    <div class="health-status">
      <span class="dot" :class="statusClass"></span>
      <span class="status-text">{{ statusText }}</span>
    </div>
    <div class="health-upstreams">
      <span>上游: {{ healthStore.upstreams.total }}</span>
      <span v-if="healthStore.upstreams.healthy > 0" class="count ok">{{ healthStore.upstreams.healthy }}<span class="dot ok"></span></span>
      <span v-if="healthStore.upstreams.degraded > 0" class="count warn">{{ healthStore.upstreams.degraded }}<span class="dot warn"></span></span>
      <span v-if="healthStore.upstreams.unhealthy > 0" class="count error">{{ healthStore.upstreams.unhealthy }}<span class="dot error"></span></span>
    </div>
    <div class="health-time">{{ healthStore.lastChecked || '--:--:--' }}</div>
    <el-button :icon="Refresh" circle size="small" :loading="healthStore.status === 'checking'" @click="refresh" />
  </div>
</template>

<style scoped>
.health-bar {
  display: flex;
  align-items: center;
  gap: 1.25rem;
  padding: 0.875rem 1.25rem;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  flex-wrap: wrap;
}

.health-status {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.status-text {
  font-weight: 500;
  font-size: 0.9375rem;
}

.health-upstreams {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  color: var(--text-secondary);
  font-size: 0.875rem;
}

.health-upstreams .count {
  display: inline-flex;
  align-items: center;
  gap: 0.25rem;
}

.health-time {
  margin-left: auto;
  color: var(--text-muted);
  font-size: 0.8125rem;
  font-family: 'JetBrains Mono', monospace;
}

.dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.dot.ok {
  background: var(--accent-green);
  box-shadow: 0 0 8px var(--accent-green-glow);
}

.dot.warn {
  background: var(--accent-yellow);
  box-shadow: 0 0 8px var(--accent-yellow-glow);
}

.dot.error {
  background: var(--accent-red);
  box-shadow: 0 0 8px var(--accent-red-glow);
}

@media (max-width: 768px) {
  .health-bar {
    gap: 0.75rem;
  }

  .health-time {
    margin-left: 0;
  }
}
</style>
