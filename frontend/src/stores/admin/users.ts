import { defineStore } from 'pinia'
import { ref } from 'vue'
import * as usersApi from '@/api/admin/users'
import type { AdminUser, UserCreate, UserUpdate } from '@/types'

export const useAdminUsersStore = defineStore('adminUsers', () => {
  const items = ref<AdminUser[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function fetchAll() {
    loading.value = true
    error.value = null
    try {
      items.value = await usersApi.listUsers()
    } catch (e) {
      error.value = e instanceof Error ? e.message : '加载失败'
    } finally {
      loading.value = false
    }
  }

  async function create(body: UserCreate) {
    const result = await usersApi.createUser(body)
    await fetchAll()
    return result
  }

  async function update(id: number, body: UserUpdate) {
    const result = await usersApi.updateUser(id, body)
    await fetchAll()
    return result
  }

  async function remove(id: number) {
    const result = await usersApi.deleteUser(id)
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
