<template>
  <header class="app-header">
    <div class="header-inner">
      <div class="header-left">
        <div class="logo" @click="router.push('/')">
          <img
            class="logo-mark"
            src="/brand/competition-brain-logo.svg?v=20260723"
            alt="竞赛大脑"
          />
        </div>
      </div>

      <nav class="header-nav">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-item"
          :class="{ active: isActive(item.path) }"
        >
          <span class="nav-code">{{ item.code }}</span>
          <span class="nav-label">{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="header-right">
        <el-dropdown @command="handleCommand" trigger="click">
          <div class="user-trigger">
            <div class="user-avatar">
              {{ username.charAt(0).toUpperCase() }}
            </div>
            <span class="user-name">{{ username }}</span>
            <el-icon class="user-arrow"><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">
                <el-icon><User /></el-icon>
                个人中心
              </el-dropdown-item>
              <el-dropdown-item command="ppt-editor">
                <el-icon><MagicStick /></el-icon>
                AI PPT生成
              </el-dropdown-item>
              <el-dropdown-item divided command="logout">
                <el-icon><SwitchButton /></el-icon>
                退出登录
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../../stores/auth'
import {
  User, ArrowDown, SwitchButton, MagicStick
} from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const username = computed(() => authStore.user?.username || '用户')

const navItems = [
  { path: '/', label: '首页', code: 'HOME' },
  { path: '/training/today', label: '训练任务', code: 'TRAIN' },
  { path: '/online-meeting', label: '路演训练', code: 'SHOW' },
  { path: '/ppt-editor', label: 'PPT生成', code: 'PPT' }
]

function isActive(path) {
  if (path === '/') return route.path === '/'
  return route.path.startsWith(path)
}

const handleCommand = (command) => {
  if (command === 'profile') {
    router.push('/profile')
  } else if (command === 'ppt-editor') {
    router.push('/ppt-editor')
  } else if (command === 'logout') {
    authStore.logout()
    router.push('/login')
  }
}
</script>

<style scoped>
.app-header {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: var(--z-fixed);
  background: rgba(255, 255, 255, 0.72);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border-bottom: 1px solid var(--border-light);
}

.header-inner {
  max-width: var(--content-max-width);
  margin: 0 auto;
  padding: 0 var(--spacing-xl);
  height: var(--header-height);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-xl);
}

.header-left {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.logo {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  cursor: pointer;
  user-select: none;
}

.logo-mark {
  width: 148px;
  height: 38px;
  display: block;
  object-fit: contain;
  object-position: left center;
}

.header-nav {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  gap: var(--spacing-xs);
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 6px;
  height: 36px;
  padding: 0 14px;
  position: relative;
  color: var(--text-secondary);
  text-decoration: none;
  border-radius: var(--radius-sm);
  transition: color var(--transition-fast), background var(--transition-fast);
}

.nav-item:hover {
  color: var(--text-primary);
  background: var(--bg-tertiary);
}

.nav-item.active {
  color: var(--text-primary);
  background: var(--bg-tertiary);
  font-weight: var(--font-weight-semibold);
}

.nav-item.active::after {
  content: "";
  position: absolute;
  left: 50%;
  bottom: -1px;
  transform: translateX(-50%);
  width: 20px;
  height: 2px;
  background: var(--color-primary);
  border-radius: 1px;
}

.nav-code {
  color: var(--text-tertiary);
  font-family: var(--font-mono);
  font-size: 10px;
  font-weight: var(--font-weight-bold);
  letter-spacing: 0.1em;
}

.nav-label {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-medium);
}

.header-right {
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.user-trigger {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  height: 40px;
  padding: 3px 10px 3px 3px;
  border: 1px solid var(--border-light);
  border-radius: 999px;
  cursor: pointer;
  transition: background var(--transition-fast), border-color var(--transition-fast);
}

.user-trigger:hover {
  background: var(--bg-tertiary);
  border-color: var(--border-default);
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-full);
  background: var(--color-primary);
  color: var(--text-inverse);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-bold);
  display: flex;
  align-items: center;
  justify-content: center;
}

.user-name {
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  color: var(--text-primary);
}

.user-arrow {
  font-size: 12px;
  color: var(--text-tertiary);
}

@media (max-width: 768px) {
  .header-nav {
    display: none;
  }

  .user-name {
    display: none;
  }

  .header-inner {
    height: 56px;
    padding: 0 var(--spacing-md);
  }

  .logo-mark {
    width: 132px;
  }
}
</style>
