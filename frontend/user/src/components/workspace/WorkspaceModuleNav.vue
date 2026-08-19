<template>
  <aside class="workspace-module-nav">
    <header class="workspace-module-nav__head">
      <h2>{{ moduleConfig.title }}</h2>
      <p>{{ moduleConfig.subtitle }}</p>
    </header>

    <nav class="workspace-module-nav__list" :aria-label="`${moduleConfig.title}二级导航`">
      <RouterLink
        v-for="item in moduleConfig.items"
        :key="item.key"
        :to="item.to"
        class="workspace-module-nav__item"
        :class="{ 'is-active': isActive(item) }"
      >
        <span class="workspace-module-nav__label">{{ item.label }}</span>
        <span class="workspace-module-nav__hint">{{ item.hint }}</span>
      </RouterLink>
    </nav>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'

const route = useRoute()

const MODULES = {
  roadshow: {
    title: '路演训练',
    subtitle: '练习 · 回看 · 评分',
    items: [
      { key: 'meeting', label: '路演训练', hint: '发起 · 加入 · 练习', to: '/online-meeting', match: ['/online-meeting', '/meeting/'] },
      { key: 'replay', label: '路演回放', hint: '视频回放 · 语音转录', to: '/my-recordings', match: ['/meeting-history', '/my-recordings'] },
    ],
  },
  review: {
    title: '复盘改进',
    subtitle: '看结果 · 找原因 · 去改进',
    items: [
      { key: 'reports', label: '评分报告', hint: '结果、依据与改进', to: '/statistics', match: ['/statistics', '/ai-score/report', '/ai-score/report-id', '/ai-score/', '/score-result', '/roadshow-chat'] },
      { key: 'upload', label: '上传评分', hint: '上传路演，生成评分', to: '/ai-score-upload', match: ['/ai-score-upload'] },
    ],
  },
  collaboration: {
    title: '团队协作',
    subtitle: '任务 · 文件 · 协同',
    items: [
      {
        key: 'tasks',
        label: '任务管理',
        hint: '分工 · 进度 · 提交',
        to: '/project-team',
        match: ['/project-team'],
        exclude: ['/resource-center'],
      },
      { key: 'files', label: '资源中心', hint: '材料 · 版本 · 共享', to: '/resource-center', match: ['/resource-center'] },
    ],
  },
}

const moduleConfig = computed(() => MODULES[route.meta.moduleGroup] || MODULES[inferGroup(route)])

function inferGroup(currentRoute) {
  const path = currentRoute.path
  if (path.startsWith('/training')) return 'training'
  if (
    path.startsWith('/online-meeting')
    || path.startsWith('/meeting/')
    || path.startsWith('/meeting-history')
    || path.startsWith('/my-recordings')
  ) return 'roadshow'
  if (path.startsWith('/statistics') || path.startsWith('/ai-score') || path.startsWith('/score-result') || path.startsWith('/roadshow-chat')) return 'review'
  if (path.startsWith('/project-team')) return 'collaboration'
  if (path.startsWith('/script-editor')) return currentRoute.query.tab === 'materials' ? 'collaboration' : 'aiApps'
  if (
    path.startsWith('/ai-apps')
    || path.startsWith('/ppt-')
    || path.startsWith('/resources')
    || path.startsWith('/typing-practice')
  ) return 'aiApps'
  return null
}

function isActive(item) {
  if (item.exclude?.some(prefix => route.path === prefix || route.path.startsWith(`${prefix}/`))) return false
  const pathMatches = item.match.some(prefix => route.path === prefix || route.path.startsWith(prefix))
  if (!pathMatches) return false
  if (
    item.key === 'script'
    && (route.path.startsWith('/script-editor/detail') || route.path.startsWith('/script-editor/template'))
  ) return true
  if (item.tab) return (route.query.tab || 'script') === item.tab
  return true
}
</script>

<style scoped>
.workspace-module-nav {
  grid-column: 2;
  grid-row: 1 / -1;
  z-index: 20;
  min-width: 0;
  padding: 24px 12px;
  background: var(--ds-surface-solid);
  border-right: 1px solid var(--ds-line);
}

.workspace-module-nav__head {
  min-height: 64px;
  padding: 0 14px 20px;
  border-bottom: 1px solid var(--ds-line);
}

.workspace-module-nav__head h2 {
  margin: 0;
  color: var(--ds-ink);
  font-size: 18px;
  font-weight: 700;
  letter-spacing: -0.02em;
}

.workspace-module-nav__head p {
  margin: 5px 0 0;
  color: var(--ds-muted);
  font-size: 12px;
  line-height: 1.4;
}

.workspace-module-nav__list {
  display: grid;
  gap: 6px;
  padding-top: 14px;
}

.workspace-module-nav__item {
  display: grid;
  gap: 4px;
  min-height: 64px;
  padding: 12px 14px;
  color: var(--ds-ink-2);
  text-decoration: none;
  border: 1px solid transparent;
  border-radius: var(--ds-radius-md);
  transition:
    background-color var(--ds-control-transition),
    border-color var(--ds-control-transition),
    color var(--ds-control-transition);
}

.workspace-module-nav__item:hover {
  background: var(--ds-btn-secondary-bg-hover);
  border-color: var(--ds-line-strong);
}

.workspace-module-nav__item:focus-visible {
  outline: var(--ds-focus-outline);
  outline-offset: var(--ds-focus-offset);
  box-shadow: var(--ds-btn-focus-ring);
}

.workspace-module-nav__item.is-active {
  background: var(--ds-orange-wash);
  border-color: var(--ds-btn-selected-border);
  box-shadow: none;
}

.workspace-module-nav__label {
  color: var(--ds-ink-2);
  font-size: 14px;
  font-weight: 650;
  transition:
    color var(--ds-control-transition),
    transform var(--ds-motion-duration-standard) var(--ds-motion-ease-out);
}

:global(.workspace-app.is-motion-enabled .workspace-module-nav__item:hover .workspace-module-nav__label) {
  transform: translateX(2px);
}

.workspace-module-nav__item.is-active .workspace-module-nav__label {
  color: var(--ds-orange-action);
}

.workspace-module-nav__hint {
  overflow: hidden;
  color: var(--ds-faint);
  font-size: 11px;
  line-height: 1.35;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 1180px) {
  .workspace-module-nav {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .workspace-module-nav__label {
    transition-duration: 0.01ms;
  }

  :global(.workspace-app.is-motion-enabled .workspace-module-nav__item:hover .workspace-module-nav__label) {
    transform: none;
  }
}
</style>
