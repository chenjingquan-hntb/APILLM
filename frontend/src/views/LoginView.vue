<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  if (!username.value.trim() || !password.value) {
    error.value = '请输入用户名和密码'
    return
  }
  error.value = ''
  loading.value = true
  try {
    await auth.login({ username: username.value, password: password.value })
    const redirect = route.query.redirect as string | undefined
    router.push(redirect || '/home')
  } catch (e) {
    error.value = e instanceof Error ? e.message : '登录失败'
  } finally {
    loading.value = false
  }
}

function onKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') handleLogin()
}
</script>

<template>
  <div class="login-page">
    <div class="login-box">
      <h2 class="login-title">登录</h2>
      <el-form label-position="top" @submit.prevent>
        <el-form-item label="用户名">
          <el-input v-model="username" placeholder="请输入用户名" @keydown="onKeydown" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="password" type="password" placeholder="请输入密码" show-password @keydown="onKeydown" />
        </el-form-item>
        <div v-if="error" class="login-error">{{ error }}</div>
        <el-button type="primary" :loading="loading" class="login-btn" @click="handleLogin">
          {{ loading ? '登录中…' : '登录' }}
        </el-button>
      </el-form>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 2rem 1rem;
}

.login-box {
  width: 100%;
  max-width: 360px;
  padding: 2rem;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
}

.login-title {
  margin-bottom: 1.5rem;
  font-size: 1.5rem;
  text-align: center;
}

.login-btn {
  width: 100%;
  margin-top: 0.5rem;
}

.login-error {
  margin-bottom: 1rem;
  padding: 0.625rem 0.875rem;
  background: rgba(239, 68, 68, 0.1);
  border: 1px solid rgba(239, 68, 68, 0.2);
  border-radius: var(--radius-sm);
  color: var(--accent-red);
  font-size: 0.8125rem;
}
</style>
