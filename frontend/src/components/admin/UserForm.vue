<script setup lang="ts">
import { reactive, watch } from 'vue'
import type { AdminUser, UserCreate, UserUpdate } from '@/types'

const props = defineProps<{
  user: AdminUser | null
}>()

const emit = defineEmits<{
  submit: [data: UserCreate | UserUpdate]
}>()

const form = reactive<UserCreate & { is_active: boolean; balance: number }>({
  username: '',
  password: '',
  role: 'user',
  is_active: true,
  balance: 0,
})

watch(
  () => props.user,
  (u) => {
    if (u) {
      form.username = u.username
      form.password = ''
      form.role = u.role
      form.is_active = u.is_active
      form.balance = u.balance
    } else {
      form.username = ''
      form.password = ''
      form.role = 'user'
      form.is_active = true
      form.balance = 0
    }
  },
  { immediate: true }
)

function onSubmit() {
  const payload: UserCreate | UserUpdate = { ...form }
  if (props.user) {
    if (!payload.password) delete payload.password
    emit('submit', payload as UserUpdate)
  } else {
    emit('submit', payload as UserCreate)
  }
}
</script>

<template>
  <el-form label-position="top">
    <el-form-item label="用户名">
      <el-input v-model="form.username" />
    </el-form-item>

    <el-form-item :label="user ? '密码（留空不修改）' : '密码'">
      <el-input v-model="form.password" type="password" />
    </el-form-item>

    <el-form-item label="角色">
      <el-select v-model="form.role" style="width: 100%">
        <el-option label="用户" value="user" />
        <el-option label="管理员" value="admin" />
      </el-select>
    </el-form-item>

    <el-form-item label="余额">
      <el-input-number v-model="form.balance" :min="0" :step="0.01" style="width: 100%" />
    </el-form-item>

    <el-form-item label="激活">
      <el-switch v-model="form.is_active" />
    </el-form-item>

    <el-button type="primary" @click="onSubmit">保存</el-button>
  </el-form>
</template>
