import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as keysApi from '@/api/user/keys'
import type { ApiKeyCreateResponse, ApiKeyResponse } from '@/types'

export const useUserKeysStore = defineStore('userKeys', () => {
  const items = ref<ApiKeyResponse[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchAll() {
    loading.value = true
    error.value = null
    try {
      items.value = await keysApi.listKeys()
    } catch (e) {
      error.value = e instanceof Error ? e.message : '加载失败'
    } finally {
      loading.value = false
    }
  }

  async function create(label: string): Promise<ApiKeyCreateResponse> {
    const result = await keysApi.createKey(label)
    await fetchAll()
    return result
  }

  async function remove(id: number) {
    const result = await keysApi.deleteKey(id)
    await fetchAll()
    return result
  }

  return {
    items,
    loading,
    error,
    fetchAll,
    create,
    remove,
  }
})
