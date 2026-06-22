import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as upstreamsApi from '@/api/admin/upstreams'
import type { Upstream, UpstreamCreate, UpstreamUpdate } from '@/types'

export const useAdminUpstreamsStore = defineStore('adminUpstreams', () => {
  const items = ref<Upstream[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchAll() {
    loading.value = true
    error.value = null
    try {
      items.value = await upstreamsApi.listUpstreams()
    } catch (e) {
      error.value = e instanceof Error ? e.message : '加载失败'
    } finally {
      loading.value = false
    }
  }

  async function create(body: UpstreamCreate) {
    const result = await upstreamsApi.createUpstream(body)
    await fetchAll()
    return result
  }

  async function update(id: number, body: UpstreamUpdate) {
    const result = await upstreamsApi.updateUpstream(id, body)
    await fetchAll()
    return result
  }

  async function remove(id: number) {
    const result = await upstreamsApi.deleteUpstream(id)
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
