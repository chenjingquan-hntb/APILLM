<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { useHealthStore } from '@/stores/health'
import { useModelCardsStore } from '@/stores/modelCards'
import HealthBar from '@/components/common/HealthBar.vue'
import ModelCardGrid from '@/components/model/ModelCardGrid.vue'

const healthStore = useHealthStore()
const modelStore = useModelCardsStore()

onMounted(() => {
  healthStore.startPolling()
  modelStore.fetchModels()
})

onUnmounted(() => {
  healthStore.stopPolling()
})

function reloadModels() {
  modelStore.fetchModels()
}
</script>

<template>
  <div class="container home-view">
    <HealthBar />

    <div class="section-header">
      <h2 class="section-title">模型列表</h2>
      <el-button :icon="Refresh" :loading="modelStore.loading" @click="reloadModels">刷新模型列表</el-button>
    </div>

    <ModelCardGrid :models="modelStore.items" :loading="modelStore.loading" :error="modelStore.error" @refresh="reloadModels" />
  </div>
</template>

<style scoped>
.home-view {
  padding-top: 1.5rem;
  padding-bottom: 3rem;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 2rem 0 1rem;
}

.section-title {
  font-size: 1.25rem;
  font-weight: 600;
}
</style>
