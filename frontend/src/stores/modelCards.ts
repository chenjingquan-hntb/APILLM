import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as modelsApi from '@/api/models'
import type { ModelCard } from '@/types'

export const useModelCardsStore = defineStore('modelCards', () => {
  const items = ref<ModelCard[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchModels() {
    loading.value = true
    error.value = null
    try {
      const data = await modelsApi.listModels()
      items.value = data.data
    } catch (e) {
      error.value = e instanceof Error ? e.message : '加载失败'
    } finally {
      loading.value = false
    }
  }

  return {
    items,
    loading,
    error,
    fetchModels,
  }
})
