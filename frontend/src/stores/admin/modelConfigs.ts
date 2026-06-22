import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as modelsApi from '@/api/admin/models'
import type { ModelConfig, ModelConfigCreate, ModelConfigUpdate } from '@/types'

export const useAdminModelConfigsStore = defineStore('adminModelConfigs', () => {
  const items = ref<ModelConfig[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchAll() {
    loading.value = true
    error.value = null
    try {
      items.value = await modelsApi.listModelConfigs()
    } catch (e) {
      error.value = e instanceof Error ? e.message : '加载失败'
    } finally {
      loading.value = false
    }
  }

  async function create(body: ModelConfigCreate) {
    const result = await modelsApi.createModelConfig(body)
    await fetchAll()
    return result
  }

  async function update(id: number, body: ModelConfigUpdate) {
    const result = await modelsApi.updateModelConfig(id, body)
    await fetchAll()
    return result
  }

  async function remove(id: number) {
    const result = await modelsApi.deleteModelConfig(id)
    await fetchAll()
    return result
  }

  return {
    items,
    loading,
    error,
    fetchAll,
    create,
    update,
    remove,
  }
})
