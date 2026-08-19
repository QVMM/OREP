<template>
  <header class="orep-top-nav">
    <div class="orep-top-nav__inner">
      <button class="orep-top-nav__brand" type="button" @click="router.push('/')">
        <img
          class="orep-top-nav__mark"
          src="/brand/competition-brain-mark.svg?v=20260723"
          alt=""
          aria-hidden="true"
        />
        <span class="orep-top-nav__brand-text">
          <strong>竞赛大脑</strong>
          <small>AI 路演训练与成长平台</small>
        </span>
      </button>

      <nav class="orep-top-nav__links" aria-label="主导航">
        <router-link
          v-for="item in OREP_NAV_ITEMS"
          :key="item.path"
          :to="item.path"
          class="orep-top-nav__link"
          :class="{ 'is-active': isOrepRouteActive(route.path, item.path) }"
        >
          <span>{{ item.label }}</span>
        </router-link>
      </nav>

      <div class="orep-top-nav__right">
        <button class="orep-top-nav__project" type="button" @click="router.push('/script-editor')">
          <span class="orep-top-nav__project-dot"></span>
          <span>智慧农业温室项目</span>
        </button>

        <el-dropdown @command="handleCommand" trigger="click">
          <button class="orep-top-nav__user" type="button">
            <span class="orep-top-nav__avatar">{{ userInitial }}</span>
            <span class="orep-top-nav__username">{{ username }}</span>
            <el-icon><ArrowDown /></el-icon>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="profile">
                <el-icon><User /></el-icon>
                个人中心
              </el-dropdown-item>
              <el-dropdown-item command="ppt-editor">
                <el-icon><MagicStick /></el-icon>
                AI PPT 生成
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
import { ArrowDown, MagicStick, SwitchButton, User } from '@element-plus/icons-vue'
import { useAuthStore } from '../../stores/auth'
import { OREP_NAV_ITEMS, isOrepRouteActive } from '../../composables/apple/useOrepNavigation'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const username = computed(() => authStore.user?.username || '用户')
const userInitial = computed(() => username.value.slice(0, 1).toUpperCase())

function handleCommand(command) {
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
.orep-top-nav {
  position: fixed;
  inset: 0 0 auto;
  z-index: var(--z-fixed);
  background: var(--orep-surface-raised);
  border-bottom: 1px solid var(--orep-border-soft);
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
}

.orep-top-nav__inner {
  width: min(100%, 1500px);
  height: var(--header-height);
  margin: 0 auto;
  padding: 0 28px;
  display: flex;
  align-items: center;
  gap: 28px;
}

.orep-top-nav__brand,
.orep-top-nav__project,
.orep-top-nav__user {
  border: 0;
  background: none;
  font: inherit;
}

.orep-top-nav__brand {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  flex: 0 0 auto;
  min-width: 270px;
  color: var(--orep-text-strong);
  cursor: pointer;
}

.orep-top-nav__mark {
  width: 40px;
  height: 40px;
  display: block;
  object-fit: contain;
}

.orep-top-nav__brand-text {
  display: grid;
  gap: 2px;
  text-align: left;
}

.orep-top-nav__brand-text strong {
  font-size: 18px;
  line-height: 1.1;
}

.orep-top-nav__brand-text small {
  color: var(--orep-muted);
  font-size: 11px;
  line-height: 1.2;
}

.orep-top-nav__links {
  display: flex;
  justify-content: center;
  gap: 34px;
  flex: 1 1 auto;
  min-width: 0;
}

.orep-top-nav__link {
  min-height: var(--header-height);
  padding: 0;
  border-radius: 0;
  display: inline-flex;
  align-items: center;
  color: var(--orep-muted);
  font-size: 15px;
  font-weight: 760;
  position: relative;
  white-space: nowrap;
  transition: color var(--transition-fast), background var(--transition-fast);
  outline: none;
}

.orep-top-nav__link:hover {
  color: var(--orep-text-strong);
  background: transparent;
}

.orep-top-nav__link.is-active {
  color: var(--orep-text-strong);
  background: transparent;
}

.orep-top-nav__link.is-active::after {
  content: "";
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 3px;
  border-radius: 3px 3px 0 0;
  background: var(--orep-text-strong);
}

.orep-top-nav__link:focus-visible {
  color: var(--orep-text-strong);
}

.orep-top-nav__right {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  flex: 0 0 auto;
}

.orep-top-nav__project,
.orep-top-nav__user {
  min-height: 40px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 999px;
  background: oklch(1 0.003 255 / 0.72);
  color: var(--orep-text);
  display: inline-flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  transition: border-color var(--transition-fast), background var(--transition-fast), transform var(--transition-fast);
}

.orep-top-nav__project {
  padding: 0 14px;
  font-size: 13px;
  font-weight: 700;
}

.orep-top-nav__project:hover,
.orep-top-nav__user:hover {
  border-color: var(--orep-border);
  background: var(--orep-surface-raised);
  transform: translateY(-1px);
}

.orep-top-nav__project-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
  background: var(--orep-green);
  box-shadow: 0 0 0 4px var(--orep-green-soft);
}

.orep-top-nav__user {
  padding: 3px 10px 3px 3px;
}

.orep-top-nav__avatar {
  width: 32px;
  height: 32px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  background: var(--orep-text-strong);
  color: oklch(0.99 0.004 255);
  font-size: 13px;
  font-weight: 800;
}

.orep-top-nav__username {
  font-size: 13px;
  font-weight: 700;
}

@media (max-width: 1120px) {
  .orep-top-nav__project {
    display: none;
  }
}

@media (max-width: 880px) {
  .orep-top-nav__links {
    display: none;
  }

  .orep-top-nav__inner {
    padding: 0 18px;
  }

  .orep-top-nav__brand {
    min-width: 0;
    flex: 1 1 auto;
  }

  .orep-top-nav__username {
    display: none;
  }
}
</style>
