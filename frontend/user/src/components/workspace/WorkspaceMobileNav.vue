<template>
  <nav class="workspace-mobile-nav" aria-label="移动端主导航">
    <template v-for="item in mobileEntries" :key="item.key || item.path">
      <CollaborationEntryButton
        v-if="item.kind === 'collaboration'"
        variant="mobile"
        :label="item.label"
        :count="collaboration.actionCount"
        :pressed="collaboration.isOpen"
        @click="openCollaboration"
      />
      <router-link
        v-else
        :to="item.path"
        class="workspace-mobile-nav__item"
        :class="{ 'is-active': isOrepRouteActive(route, item.path) }"
        :aria-label="item.label"
        :aria-current="isOrepRouteActive(route, item.path) ? 'page' : undefined"
      >
        <span><WorkspaceModuleIcon :name="item.group" variant="filled" /></span>
        <small>{{ item.shortLabel || item.label }}</small>
      </router-link>
    </template>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { OREP_NAV_ITEMS, isOrepRouteActive } from '../../composables/apple/useOrepNavigation'
import { useCollaborationStore } from '../../stores/collaboration'
import CollaborationEntryButton from '../collaboration/CollaborationEntryButton.vue'
import WorkspaceModuleIcon from './WorkspaceModuleIcon.vue'

const route = useRoute()
const router = useRouter()
const collaboration = useCollaborationStore()
const mobileGroups = ['home', 'training', 'roadshow', 'resources', 'profile']
const shortLabels = {
  home: '首页',
  training: '训练',
  roadshow: '讲解',
  resources: '资源',
  profile: '我的',
}

const mobileItems = computed(() => OREP_NAV_ITEMS
  .filter((item) => mobileGroups.includes(item.group))
  .map((item) => ({ ...item, shortLabel: shortLabels[item.group] })))

const mobileEntries = computed(() => {
  const entries = mobileItems.value.map((item) => ({ ...item, kind: 'route' }))
  const roadshowIndex = entries.findIndex((item) => item.group === 'roadshow')
  entries.splice(roadshowIndex + 1, 0, {
    kind: 'collaboration',
    key: 'collaboration',
    label: '待办',
  })
  return entries
})

function openCollaboration() {
  if (collaboration.isFeatureEnabled) {
    collaboration.toggle()
    return
  }
  router.push('/project-team')
}
</script>

<style scoped>
.workspace-mobile-nav {
  position: fixed;
  z-index: var(--z-fixed, 100);
  left: max(10px, env(safe-area-inset-left, 0px));
  right: max(10px, env(safe-area-inset-right, 0px));
  bottom: max(10px, env(safe-area-inset-bottom, 0px));
  min-height: 64px;
  padding: 7px;
  border: 1px solid rgba(255, 255, 255, 0.74);
  border-radius: 24px;
  display: none;
  grid-template-columns: repeat(6, minmax(0, 1fr));
  gap: 4px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 12px 40px rgba(15, 23, 42, 0.12);
  backdrop-filter: blur(22px) saturate(160%);
  -webkit-backdrop-filter: blur(22px) saturate(160%);
}

.workspace-mobile-nav__item {
  min-width: 0;
  border-radius: 18px;
  display: grid;
  place-items: center;
  gap: 3px;
  color: var(--workspace-ink-500);
  font-size: 11px;
  font-weight: 800;
}

.workspace-mobile-nav__item span {
  width: 20px;
  height: 20px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  background: rgba(255, 247, 243, 0.78);
}

.workspace-mobile-nav__item svg {
  width: 15px;
  height: 15px;
}

.workspace-mobile-nav__item small {
  font-size: 10px;
  line-height: 1;
}

.workspace-mobile-nav__item.is-active {
  color: var(--workspace-orange-600);
  background: var(--workspace-orange-50);
}

@media (max-width: 1023px) {
  .workspace-mobile-nav {
    display: grid;
  }
}
</style>
