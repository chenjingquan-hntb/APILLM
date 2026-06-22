<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

function navigateTo(view: string) {
  router.push(`/${view}`)
}

async function handleLogout() {
  await auth.logout()
  router.push('/home')
}
</script>

<template>
  <header class="app-bar">
    <div class="container header-inner">
      <span class="logo" @click="navigateTo('home')">APILLM</span>
      <nav class="app-nav">
        <a class="nav-link" :class="{ active: route.path === '/home' }" @click="navigateTo('home')">首页</a>
        <a v-if="auth.isAuthenticated" class="nav-link" :class="{ active: route.path === '/user' }" @click="navigateTo('user')">用户后台</a>
        <a v-if="auth.isAdmin" class="nav-link" :class="{ active: route.path === '/admin' }" @click="navigateTo('admin')">管理后台</a>
      </nav>
      <div class="user-area">
        <button v-if="!auth.isAuthenticated" class="btn-text" @click="navigateTo('login')">登录</button>
        <template v-else>
          <span class="user-name">{{ auth.username }}</span>
          <button class="btn-text" @click="handleLogout">退出</button>
        </template>
      </div>
    </div>
  </header>
</template>

<style scoped>
.app-bar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 48px;
  background: rgba(8, 8, 8, 0.85);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--border);
  z-index: 100;
}

.header-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 100%;
}

.logo {
  font-family: 'Outfit', sans-serif;
  font-weight: 700;
  font-size: 1.25rem;
  color: var(--text-primary);
  cursor: pointer;
  user-select: none;
}

.app-nav {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex: 1;
  margin-left: 2rem;
}

.nav-link {
  padding: 0.5rem 0.875rem;
  border-radius: var(--radius-sm);
  color: var(--text-secondary);
  font-size: 0.875rem;
  font-weight: 500;
  cursor: pointer;
  transition: color 0.2s, background-color 0.2s;
  user-select: none;
}

.nav-link:hover {
  color: var(--text-primary);
  background-color: var(--bg-hover);
}

.nav-link.active {
  color: var(--text-primary);
  background-color: var(--bg-card-hover);
}

.user-area {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.user-name {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.btn-text {
  padding: 0.375rem 0.75rem;
  border: none;
  background: transparent;
  color: var(--text-secondary);
  font-size: 0.875rem;
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: color 0.2s, background-color 0.2s;
}

.btn-text:hover {
  color: var(--text-primary);
  background-color: var(--bg-hover);
}

@media (max-width: 768px) {
  .app-nav {
    margin-left: 1rem;
    gap: 0.25rem;
  }

  .nav-link {
    padding: 0.5rem 0.625rem;
    font-size: 0.8125rem;
  }
}
</style>
