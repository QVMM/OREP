<template>
  <nav class="orep-mobile-nav" aria-label="移动端主导航">
    <router-link
      v-for="item in mobileItems"
      :key="item.path"
      :to="item.path"
      class="orep-mobile-nav__item"
      :class="{ 'is-active': isOrepRouteActive(route.path, item.path) }"
    >
      <component :is="item.icon" />
      <span>{{ item.label }}</span>
    </router-link>
  </nav>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import {
  DataAnalysis,
  EditPen,
  HomeFilled,
  Reading,
  VideoCamera,
} from '@element-plus/icons-vue'
import { OREP_NAV_ITEMS, isOrepRouteActive } from '../../composables/apple/useOrepNavigation'

const route = useRoute()

const iconMap = {
  home: HomeFilled,
  learn: Reading,
  practice: EditPen,
  prepare: DataAnalysis,
  roadshow: VideoCamera,
}

const mobileItems = computed(() => OREP_NAV_ITEMS
  .filter((item) => ['home', 'learn', 'practice', 'prepare', 'roadshow'].includes(item.group))
  .map((item) => ({ ...item, icon: iconMap[item.group] })))
</script>

<style scoped>
.orep-mobile-nav {
  position: fixed;
  z-index: var(--z-fixed);
  left: 12px;
  right: 12px;
  bottom: 12px;
  min-height: 64px;
  padding: 7px;
  border: 1px solid var(--orep-border-soft);
  border-radius: 24px;
  background: oklch(1 0.003 255 / 0.86);
  box-shadow: 0 20px 54px oklch(0.42 0.05 255 / 0.18);
  backdrop-filter: blur(22px) saturate(160%);
  -webkit-backdrop-filter: blur(22px) saturate(160%);
  display: none;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 4px;
}

.orep-mobile-nav__item {
  min-width: 0;
  border-radius: 18px;
  color: var(--orep-muted);
  display: grid;
  place-items: center;
  gap: 3px;
  font-size: 11px;
  font-weight: 800;
  line-height: 1;
}

.orep-mobile-nav__item :deep(svg) {
  width: 18px;
  height: 18px;
}

.orep-mobile-nav__item.is-active {
  color: var(--orep-blue);
  background: var(--orep-blue-soft);
}

@media (max-width: 880px) {
  .orep-mobile-nav {
    display: grid;
  }
}
</style>
