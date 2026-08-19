<template>
  <div class="app-container" :class="{ 'is-meeting-route': isImmersiveRoute, 'is-public-shell': isAuthPage }">
    <template v-if="!isAuthPage">
      <WorkspaceShell v-if="!isImmersiveRoute" />
      <router-view v-else />
    </template>
    <router-view v-else v-slot="{ Component, route: publicRoute }">
      <Transition name="public-route" mode="out-in">
        <component :is="Component" :key="publicRoute.path" />
      </Transition>
    </router-view>
  </div>
</template>

<script setup>
import { computed, watchEffect } from 'vue'
import { useRoute } from 'vue-router'
import WorkspaceShell from './components/workspace/WorkspaceShell.vue'
import { shouldUseImmersiveShell } from './composables/apple/useOrepNavigation'

const route = useRoute()

const isAuthPage = computed(() => {
  return Boolean(route.meta.publicShell) || route.path === '/login'
})

const isImmersiveRoute = computed(() => {
  return Boolean(route.meta.immersive) || shouldUseImmersiveShell(route.path)
})

watchEffect((onCleanup) => {
  if (!isAuthPage.value) return
  document.documentElement.classList.add('is-public-shell')
  document.body.classList.add('is-public-shell')
  onCleanup(() => {
    document.documentElement.classList.remove('is-public-shell')
    document.body.classList.remove('is-public-shell')
  })
})
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: var(--orep-font-sans);
  background-color: var(--ds-canvas, #f7f7f8);
  background-image: none;
  color: var(--orep-text);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  font-synthesis: none;
  text-rendering: optimizeLegibility;
}

html.is-public-shell,
body.is-public-shell,
body.is-public-shell #app {
  height: 100%;
  min-height: 100%;
  min-height: 100dvh;
  overflow: hidden;
  overscroll-behavior-y: none;
  background: #f7f7f8;
}

.app-container {
  width: 100%;
  height: 100vh;
  height: 100dvh;
  min-height: 100vh;
  min-height: 100dvh;
  overflow: hidden;
  background-color: var(--ds-canvas, #f7f7f8);
  background-image: none;
}

.app-container.is-public-shell {
  height: 100%;
  min-height: 100%;
  min-height: 100dvh;
  overflow: hidden;
  /* 与产品台 / 登录页同一 canvas */
  background: #f7f7f8;
}

.public-route-enter-active,
.public-route-leave-active {
  transition: opacity 0.28s cubic-bezier(0.22, 1, 0.36, 1), transform 0.28s cubic-bezier(0.22, 1, 0.36, 1);
}

.public-route-enter-from {
  opacity: 0;
  transform: translateY(14px) scale(0.992);
}

.public-route-leave-to {
  opacity: 0;
  transform: translateY(-10px) scale(1.006);
}

/* Element Plus Dropdown Enhancement */
.el-dropdown-menu {
  min-width: 176px !important;
  border-radius: var(--radius-sm) !important;
  padding: var(--spacing-sm) !important;
  box-shadow: var(--shadow-lg) !important;
  border: 1px solid var(--border-light) !important;
}

.el-dropdown-menu__item {
  min-height: 40px !important;
  border-radius: 6px !important;
  padding: 0 12px !important;
  gap: 10px;
  font-size: var(--font-size-xs) !important;
  font-weight: var(--font-weight-medium) !important;
  letter-spacing: 0 !important;
  transition: background var(--transition-fast), color var(--transition-fast) !important;
}

.el-dropdown-menu__item:hover,
.el-dropdown-menu__item:focus,
.el-dropdown-menu__item:not(.is-disabled):focus {
  background: var(--bg-tertiary) !important;
  outline: none !important;
}

.el-dropdown-menu__item--divided {
  margin-top: 6px !important;
  border-top: 1px solid var(--border-light) !important;
}

.el-dropdown-menu__item--divided::before {
  display: none !important;
}
</style>
