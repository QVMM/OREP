<template>
  <!-- 小启：与学生端同款品牌标 -->
  <XiaoQiMark
    v-if="name === 'assistant' || name === 'xiaoqi'"
    class="teacher-module-icon is-xiaoqi"
    :size="26"
    :hoverable="hoverable"
    :active="normalizedVariant === 'filled'"
    aria-label="小启AI"
  />
  <svg
    v-else
    class="teacher-module-icon"
    :class="`is-${normalizedVariant}`"
    viewBox="0 0 24 24"
    aria-hidden="true"
    focusable="false"
  >
    <template v-if="normalizedVariant === 'filled'">
      <path v-for="(path, index) in filledIcon" :key="`f-${index}`" :d="path" />
    </template>
    <template v-else>
      <path v-for="(path, index) in outlineIcon" :key="`o-${index}`" :d="path" />
    </template>
  </svg>
</template>

<script setup>
/**
 * 教师端导航图标 —— 与用户端 WorkspaceModuleIcon 同源 path，保证视觉一致。
 * 映射：
 *   workbench → home
 *   projects  → collaboration（团队）
 *   training  → training
 *   roadshow  → roadshow
 *   ai        → aiApps
 *   resources → resources
 *   analytics → analytics（教师侧专用，风格与 review 线框一致）
 */
import { computed } from 'vue'
import XiaoQiMark from './brand/XiaoQiMark.vue'

const props = defineProps({
  name: { type: String, default: 'workbench' },
  variant: { type: String, default: 'outline' },
  hoverable: { type: Boolean, default: true },
})

const normalizedVariant = computed(() => (props.variant === 'filled' ? 'filled' : 'outline'))

/** 用户端同源 path（24 viewBox） */
const SHARED = {
  home: {
    filled: ['M12 2.8 3.5 10v10.2c0 .55.45 1 1 1h5.3v-6.4h4.4v6.4h5.3c.55 0 1-.45 1-1V10L12 2.8Z'],
    outline: [
      'M4.5 10.5 12 4l7.5 6.5v8.2a1.3 1.3 0 0 1-1.3 1.3H15v-6H9v6H5.8a1.3 1.3 0 0 1-1.3-1.3v-8.2Z',
    ],
  },
  collaboration: {
    filled: [
      'M8.2 11.2a3.5 3.5 0 1 0 0-7 3.5 3.5 0 0 0 0 7Zm8.1-.8a2.9 2.9 0 1 0 0-5.8 2.9 2.9 0 0 0 0 5.8ZM2.6 20.8a5.6 5.6 0 0 1 11.2 0v.7H2.6v-.7Zm11.4.7v-.7a7 7 0 0 0-1.1-3.8 5 5 0 0 1 8.5 3.6v.9H14Z',
    ],
    outline: [
      'M8.2 11.2a3.4 3.4 0 1 0 0-6.8 3.4 3.4 0 0 0 0 6.8Z',
      'M3 20a5.2 5.2 0 0 1 10.4 0',
      'M16.7 10.2a2.8 2.8 0 1 0 0-5.6',
      'M14.4 15.3A4.8 4.8 0 0 1 21 19.8',
    ],
  },
  training: {
    filled: [
      'M12 2 2.5 6.7 12 11.4l7-3.47V15h2V6.7L12 2Zm-6.4 9.3V16c0 2.5 2.87 4.5 6.4 4.5s6.4-2 6.4-4.5v-4.7L12 14.5l-6.4-3.2Z',
    ],
    outline: [
      'M3.5 7 12 3l8.5 4-8.5 4-8.5-4Z',
      'M6 10v5.6c0 2.4 2.7 4.4 6 4.4s6-2 6-4.4V10',
    ],
  },
  roadshow: {
    filled: [
      'M5 4.5h12a2 2 0 0 1 2 2v2.1l3-1.8v10.4l-3-1.8v2.1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-11a2 2 0 0 1 2-2Z',
    ],
    outline: [
      'M5.5 6h10A2.5 2.5 0 0 1 18 8.5v7a2.5 2.5 0 0 1-2.5 2.5h-10A2.5 2.5 0 0 1 3 15.5v-7A2.5 2.5 0 0 1 5.5 6Z',
      'm18 10 3-2v8l-3-2',
    ],
  },
  aiApps: {
    filled: [
      'M4.5 3h4A1.5 1.5 0 0 1 10 4.5v4A1.5 1.5 0 0 1 8.5 10h-4A1.5 1.5 0 0 1 3 8.5v-4A1.5 1.5 0 0 1 4.5 3Zm0 11h4a1.5 1.5 0 0 1 1.5 1.5v4A1.5 1.5 0 0 1 8.5 21h-4A1.5 1.5 0 0 1 3 19.5v-4A1.5 1.5 0 0 1 4.5 14Zm11-2h4a1.5 1.5 0 0 1 1.5 1.5v6a1.5 1.5 0 0 1-1.5 1.5h-4a1.5 1.5 0 0 1-1.5-1.5v-6a1.5 1.5 0 0 1 1.5-1.5Z',
      'm16.2 2 .62 1.88L18.7 4.5l-1.88.62L16.2 7l-.62-1.88-1.88-.62 1.88-.62L16.2 2Zm4.1 4.8.4 1.2 1.2.4-1.2.4-.4 1.2-.4-1.2-1.2-.4 1.2-.4.4-1.2Z',
    ],
    outline: [
      'M5.5 3.5h3A1.5 1.5 0 0 1 10 5v3a1.5 1.5 0 0 1-1.5 1.5h-3A1.5 1.5 0 0 1 4 8V5a1.5 1.5 0 0 1 1.5-1.5Z',
      'M5.5 14.5h3A1.5 1.5 0 0 1 10 16v3a1.5 1.5 0 0 1-1.5 1.5h-3A1.5 1.5 0 0 1 4 19v-3a1.5 1.5 0 0 1 1.5-1.5Z',
      'M16 13.5h3a1.5 1.5 0 0 1 1.5 1.5v4a1.5 1.5 0 0 1-1.5 1.5h-3a1.5 1.5 0 0 1-1.5-1.5v-4a1.5 1.5 0 0 1 1.5-1.5Z',
      'm16.8 2 .6 1.8 1.8.6-1.8.6-.6 1.8-.6-1.8-1.8-.6 1.8-.6.6-1.8Z',
    ],
  },
  resources: {
    filled: [
      'M3 6.2A2.2 2.2 0 0 1 5.2 4h5l2 2H19a2 2 0 0 1 2 2v10.2a2.8 2.8 0 0 1-2.8 2.8H5.8A2.8 2.8 0 0 1 3 18.2v-12Z',
    ],
    outline: [
      'M3.5 7V5.8A1.8 1.8 0 0 1 5.3 4h4.6l2 2h6.8a1.8 1.8 0 0 1 1.8 1.8V9',
      'M4.5 8.5h15.8a1.2 1.2 0 0 1 1.15 1.55l-2.6 8.6A1.9 1.9 0 0 1 17 20H5.9a1.9 1.9 0 0 1-1.88-1.65L2.8 10.5a1.75 1.75 0 0 1 1.7-2Z',
    ],
  },
  /** 学情分析：趋势柱图，风格与用户端 review 线框一致 */
  analytics: {
    filled: [
      'M4 20.5h16v1.5H4v-1.5Zm1.5-8h3.2v6H5.5v-6Zm5-6h3.2v12h-3.2v-12Zm5 3h3.2v9h-3.2v-9Z',
    ],
    outline: [
      'M4 20h16',
      'M6.5 15v2',
      'M11 11v6',
      'M15.5 13v4',
      'm5 11 4-4 3 2.5L19 4',
    ],
  },
}

/** 教师 nav key → 共享图标 key */
const ALIAS = {
  workbench: 'home',
  projects: 'collaboration',
  training: 'training',
  roadshow: 'roadshow',
  ai: 'aiApps',
  resources: 'resources',
  analytics: 'analytics',
  home: 'home',
  collaboration: 'collaboration',
  aiApps: 'aiApps',
}

const resolvedName = computed(() => ALIAS[props.name] || 'home')

const filledIcon = computed(() => SHARED[resolvedName.value]?.filled || SHARED.home.filled)
const outlineIcon = computed(() => SHARED[resolvedName.value]?.outline || SHARED.home.outline)
</script>

<style scoped>
.teacher-module-icon {
  width: 1em;
  height: 1em;
  display: block;
}

.teacher-module-icon.is-xiaoqi {
  width: 26px;
  height: 26px;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

.teacher-module-icon.is-filled {
  fill: currentColor;
}

.teacher-module-icon.is-outline {
  fill: none;
  stroke: currentColor;
  stroke-width: 1.9;
  stroke-linecap: round;
  stroke-linejoin: round;
}
</style>
