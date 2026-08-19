<template>
  <!-- 小启 AI：专用品牌标 + 悬停轻动 -->
  <XiaoQiMark
    v-if="name === 'assistant'"
    class="workspace-module-icon is-xiaoqi"
    :size="32"
    :hoverable="true"
    :active="normalizedVariant === 'filled'"
    aria-label="小启AI"
  />
  <!-- 待办/协作：彩色专用图标 -->
  <svg
    v-else-if="name === 'collaboration'"
    class="workspace-module-icon is-collaboration"
    :class="{ 'is-active': normalizedVariant === 'filled' }"
    viewBox="0 0 1024 1024"
    aria-hidden="true"
    focusable="false"
  >
    <defs>
      <linearGradient
        :id="peopleGradId"
        x1="120"
        y1="80"
        x2="900"
        y2="900"
        gradientUnits="userSpaceOnUse"
      >
        <stop offset="0" stop-color="#2d6cdf" />
        <stop offset="0.42" stop-color="#4f8ef7" />
        <stop offset="0.78" stop-color="#7b5ce0" />
        <stop offset="1" stop-color="#e5481d" />
      </linearGradient>
      <linearGradient
        :id="checkGradId"
        x1="560"
        y1="620"
        x2="920"
        y2="980"
        gradientUnits="userSpaceOnUse"
      >
        <stop offset="0" stop-color="#ff8a4c" />
        <stop offset="1" stop-color="#e5481d" />
      </linearGradient>
    </defs>
    <path
      class="workspace-module-icon__people"
      :fill="`url(#${peopleGradId})`"
      d="M337.5 423.4c63.5 0 119.6-31.1 154.3-78.8 5.6-7.7 10.7-15.9 15.1-24.5 13.7-26.2 21.5-56 21.5-87.6 0-22.2-3.9-43.4-10.9-63.2-6.2-17.6-14.9-34-25.7-48.9-34.7-47.6-90.8-78.8-154.3-78.8-105.4 0-190.9 85.5-190.9 190.9 0.1 105.4 85.5 190.9 190.9 190.9zM696.4 413.4c56.3 0 106.1-27.6 136.9-69.9 20.3-27.9 32.5-62.2 32.5-99.4s-12.1-71.5-32.5-99.4c-30.8-42.3-80.6-69.9-136.9-69.9-62.2 0-116.4 33.6-145.9 83.6 7 19.8 10.9 41 10.9 63.2 0 31.6-7.8 61.4-21.5 87.6 25.6 61.1 86 104.2 156.5 104.2zM503.8 780l176.9-88.5C649.2 613.9 591 550 517.3 511.4c-48.8-25.4-104.3-40-163.2-40-194.8 0-352.7 157.9-352.7 352.7h462.7l-29.8-9.3 69.5-34.8zM711.1 456.1c-58.8 0-113.7 16.2-160.7 44.4 72.2 37.8 129.6 100 161.5 175.5l188.7-94.3L853.4 769H1024c0-172.8-140.1-312.9-312.9-312.9zM640.6 982.5l48.4-68.3-48.4-14.4z"
    />
    <path
      class="workspace-module-icon__check"
      :fill="`url(#${checkGradId})`"
      d="M710.9 698.4l-26.6 13.3-151.1 75.6-59.3 29.6 25.4 8 112 35 39.9-35 43-37.6 8.7-7.7 26-22.8 51.6-45.3-49.2 60-25.7 31.4-18.1 22-38.1 46.5 147 46.8 35.3-140.4L872 617.9z"
    />
  </svg>
  <svg
    v-else
    class="workspace-module-icon"
    :class="`is-${normalizedVariant}`"
    viewBox="0 0 24 24"
    aria-hidden="true"
    focusable="false"
  >
    <template v-if="normalizedVariant === 'filled'">
      <path v-for="(path, index) in filledIcon" :key="index" :d="path" />
    </template>
    <template v-else>
      <path v-for="(path, index) in outlineIcon" :key="index" :d="path" />
    </template>
  </svg>
</template>

<script setup>
import { computed, useId } from 'vue'
import XiaoQiMark from '../brand/XiaoQiMark.vue'

const props = defineProps({
  name: { type: String, default: 'home' },
  variant: { type: String, default: 'outline' },
})

const normalizedVariant = computed(() => props.variant === 'filled' ? 'filled' : 'outline')
const uid = useId().replace(/[^a-zA-Z0-9_-]/g, '')
const peopleGradId = `collab-people-${uid}`
const checkGradId = `collab-check-${uid}`

const filledIcons = {
  home: ['M12 2.8 3.5 10v10.2c0 .55.45 1 1 1h5.3v-6.4h4.4v6.4h5.3c.55 0 1-.45 1-1V10L12 2.8Z'],
  training: ['M12 2 2.5 6.7 12 11.4l7-3.47V15h2V6.7L12 2Zm-6.4 9.3V16c0 2.5 2.87 4.5 6.4 4.5s6.4-2 6.4-4.5v-4.7L12 14.5l-6.4-3.2Z'],
  roadshow: ['M5 4.5h12a2 2 0 0 1 2 2v2.1l3-1.8v10.4l-3-1.8v2.1a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-11a2 2 0 0 1 2-2Z'],
  review: ['M4 20.5h16v1.5H4v-1.5Zm1.5-8h3.2v6H5.5v-6Zm5-6h3.2v12h-3.2v-12Zm5 3h3.2v9h-3.2v-9Z'],
  resources: ['M3 6.2A2.2 2.2 0 0 1 5.2 4h5l2 2H19a2 2 0 0 1 2 2v10.2a2.8 2.8 0 0 1-2.8 2.8H5.8A2.8 2.8 0 0 1 3 18.2v-12Z'],
  aiApps: [
    'M4.5 3h4A1.5 1.5 0 0 1 10 4.5v4A1.5 1.5 0 0 1 8.5 10h-4A1.5 1.5 0 0 1 3 8.5v-4A1.5 1.5 0 0 1 4.5 3Zm0 11h4a1.5 1.5 0 0 1 1.5 1.5v4A1.5 1.5 0 0 1 8.5 21h-4A1.5 1.5 0 0 1 3 19.5v-4A1.5 1.5 0 0 1 4.5 14Zm11-2h4a1.5 1.5 0 0 1 1.5 1.5v6a1.5 1.5 0 0 1-1.5 1.5h-4a1.5 1.5 0 0 1-1.5-1.5v-6a1.5 1.5 0 0 1 1.5-1.5Z',
    'm16.2 2 .62 1.88L18.7 4.5l-1.88.62L16.2 7l-.62-1.88-1.88-.62 1.88-.62L16.2 2Zm4.1 4.8.4 1.2 1.2.4-1.2.4-.4 1.2-.4-1.2-1.2-.4 1.2-.4.4-1.2Z',
  ],
  profile: ['M12 12.1a4.5 4.5 0 1 0 0-9 4.5 4.5 0 0 0 0 9Zm-7.7 9.3a7.7 7.7 0 0 1 15.4 0H4.3Z'],
}

const outlineIcons = {
  home: [
    'M4.5 10.5 12 4l7.5 6.5v8.2a1.3 1.3 0 0 1-1.3 1.3H15v-6H9v6H5.8a1.3 1.3 0 0 1-1.3-1.3v-8.2Z',
  ],
  progress: ['M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z', 'M12 7v5l3.2 2'],
  learning: ['M4 5.5A2.5 2.5 0 0 1 6.5 3H11v16H6.5A2.5 2.5 0 0 0 4 21V5.5Z', 'M20 5.5A2.5 2.5 0 0 0 17.5 3H13v16h4.5A2.5 2.5 0 0 1 20 21V5.5Z'],
  training: [
    'M3.5 7 12 3l8.5 4-8.5 4-8.5-4Z',
    'M6 10v5.6c0 2.4 2.7 4.4 6 4.4s6-2 6-4.4V10',
  ],
  roadshow: [
    'M5.5 6h10A2.5 2.5 0 0 1 18 8.5v7a2.5 2.5 0 0 1-2.5 2.5h-10A2.5 2.5 0 0 1 3 15.5v-7A2.5 2.5 0 0 1 5.5 6Z',
    'm18 10 3-2v8l-3-2',
  ],
  review: [
    'M4 20h16',
    'M6.5 15v2',
    'M11 11v6',
    'M15.5 13v4',
    'm5 11 4-4 3 2.5L19 4',
  ],
  resources: [
    'M3.5 7V5.8A1.8 1.8 0 0 1 5.3 4h4.6l2 2h6.8a1.8 1.8 0 0 1 1.8 1.8V9',
    'M4.5 8.5h15.8a1.2 1.2 0 0 1 1.15 1.55l-2.6 8.6A1.9 1.9 0 0 1 17 20H5.9a1.9 1.9 0 0 1-1.88-1.65L2.8 10.5a1.75 1.75 0 0 1 1.7-2Z',
  ],
  rhythm: ['M5 4h14a2 2 0 0 1 2 2v14H3V6a2 2 0 0 1 2-2Z', 'M8 2v4', 'M16 2v4', 'M3 9h18', 'M7 13h3', 'M14 13h3', 'M7 17h3'],
  actions: ['M10 6h10', 'M10 12h10', 'M10 18h10', 'm4 6 1.4 1.4L8 4.8', 'm4 12 1.4 1.4L8 10.8', 'm4 18 1.4 1.4L8 16.8'],
  aiApps: [
    'M5.5 3.5h3A1.5 1.5 0 0 1 10 5v3a1.5 1.5 0 0 1-1.5 1.5h-3A1.5 1.5 0 0 1 4 8V5a1.5 1.5 0 0 1 1.5-1.5Z',
    'M5.5 14.5h3A1.5 1.5 0 0 1 10 16v3a1.5 1.5 0 0 1-1.5 1.5h-3A1.5 1.5 0 0 1 4 19v-3a1.5 1.5 0 0 1 1.5-1.5Z',
    'M16 13.5h3a1.5 1.5 0 0 1 1.5 1.5v4a1.5 1.5 0 0 1-1.5 1.5h-3a1.5 1.5 0 0 1-1.5-1.5v-4a1.5 1.5 0 0 1 1.5-1.5Z',
    'm16.8 2 .6 1.8 1.8.6-1.8.6-.6 1.8-.6-1.8-1.8-.6 1.8-.6.6-1.8Z',
  ],
  profile: [
    'M12 11.8a4.2 4.2 0 1 0 0-8.4 4.2 4.2 0 0 0 0 8.4Z',
    'M5 20.5a7 7 0 0 1 14 0',
  ],
}

const filledIcon = computed(() => filledIcons[props.name] || filledIcons.home)
const outlineIcon = computed(() => outlineIcons[props.name] || outlineIcons.home)
</script>

<style scoped>
.workspace-module-icon {
  width: 1em;
  height: 1em;
  display: block;
}

/* 略大于线框图标（28→32），裁切后填满、光学居中 */
.workspace-module-icon.is-xiaoqi {
  width: 32px;
  height: 32px;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}

/* 待办彩色图标：略放大以匹配线框视觉重量 */
.workspace-module-icon.is-collaboration {
  width: 22px;
  height: 22px;
  overflow: visible;
  filter: drop-shadow(0 1px 1.5px rgba(45, 108, 223, 0.18));
}

.workspace-module-icon.is-collaboration.is-active {
  filter: drop-shadow(0 1px 2px rgba(229, 72, 29, 0.22));
}

.workspace-module-icon.is-filled {
  fill: currentColor;
}

.workspace-module-icon.is-outline {
  fill: none;
  stroke: currentColor;
  stroke-width: 1.9;
  stroke-linecap: round;
  stroke-linejoin: round;
}
</style>
