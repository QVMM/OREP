<template>
  <svg
    class="xq-icon"
    :class="[`is-${name}`, sizeClass]"
    viewBox="0 0 24 24"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    aria-hidden="true"
    focusable="false"
  >
    <!-- plus -->
    <template v-if="name === 'plus'">
      <path d="M12 5v14M5 12h14" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
    </template>
    <!-- search -->
    <template v-else-if="name === 'search'">
      <circle cx="11" cy="11" r="6.5" stroke="currentColor" stroke-width="1.8" />
      <path d="M16.2 16.2 20 20" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
    </template>
    <!-- panel left -->
    <template v-else-if="name === 'panel-left'">
      <rect x="3.5" y="4.5" width="17" height="15" rx="2.5" stroke="currentColor" stroke-width="1.7" />
      <path d="M9 4.5v15" stroke="currentColor" stroke-width="1.7" />
    </template>
    <!-- panel right -->
    <template v-else-if="name === 'panel-right'">
      <rect x="3.5" y="4.5" width="17" height="15" rx="2.5" stroke="currentColor" stroke-width="1.7" />
      <path d="M15 4.5v15" stroke="currentColor" stroke-width="1.7" />
    </template>
    <!-- stop -->
    <template v-else-if="name === 'stop'">
      <rect x="7" y="7" width="10" height="10" rx="2" fill="currentColor" />
    </template>
    <!-- share -->
    <template v-else-if="name === 'share'">
      <circle cx="18" cy="5.5" r="2.2" stroke="currentColor" stroke-width="1.7" />
      <circle cx="6" cy="12" r="2.2" stroke="currentColor" stroke-width="1.7" />
      <circle cx="18" cy="18.5" r="2.2" stroke="currentColor" stroke-width="1.7" />
      <path d="M8 11.2 15.8 6.8M8 12.8l7.8 4.4" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" />
    </template>
    <!-- download / export -->
    <template v-else-if="name === 'download'">
      <path d="M12 4v11M7.5 11.5 12 16l4.5-4.5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
      <path d="M5 19h14" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
    </template>
    <!-- paperclip -->
    <template v-else-if="name === 'paperclip'">
      <path
        d="M15.5 8.5 9.2 14.8a2.7 2.7 0 0 0 3.8 3.8l7-7a4.5 4.5 0 0 0-6.4-6.4l-7.5 7.5a6 6 0 0 0 8.5 8.5l5.8-5.8"
        stroke="currentColor"
        stroke-width="1.7"
        stroke-linecap="round"
        stroke-linejoin="round"
      />
    </template>
    <!-- library / folder -->
    <template v-else-if="name === 'library'">
      <path d="M4 7.2V5.8A1.8 1.8 0 0 1 5.8 4h4.2l2 2H18a2 2 0 0 1 2 2v1" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" />
      <path d="M5 9h14a1.5 1.5 0 0 1 1.45 1.9l-1.8 7A2 2 0 0 1 16.7 20H7.1a2 2 0 0 1-1.95-1.5L3.8 10.9A1.5 1.5 0 0 1 5 9Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" />
    </template>
    <!-- send -->
    <template v-else-if="name === 'send'">
      <path d="M4.5 11.2 19.2 4.5 12.5 19.2l-1.6-6.2-6.4-1.8Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" />
      <path d="m10.9 13 8.3-8.5" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" />
    </template>
    <!-- copy -->
    <template v-else-if="name === 'copy'">
      <rect x="8.5" y="8.5" width="11" height="11" rx="2" stroke="currentColor" stroke-width="1.7" />
      <path d="M15.5 8.5V6.8A1.8 1.8 0 0 0 13.7 5H6.8A1.8 1.8 0 0 0 5 6.8v6.9A1.8 1.8 0 0 0 6.8 15.5H8.5" stroke="currentColor" stroke-width="1.7" />
    </template>
    <!-- refresh -->
    <template v-else-if="name === 'refresh'">
      <path d="M19 12a7 7 0 1 1-2-4.9" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
      <path d="M19 5v5h-5" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
    </template>
    <!-- file -->
    <template v-else-if="name === 'file'">
      <path d="M7 4.5h7l4 4V19a1.5 1.5 0 0 1-1.5 1.5h-9.5A1.5 1.5 0 0 1 5.5 19V6A1.5 1.5 0 0 1 7 4.5Z" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" />
      <path d="M14 4.5V9h4.5" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" />
    </template>
    <!-- more -->
    <template v-else-if="name === 'more'">
      <circle cx="6" cy="12" r="1.4" fill="currentColor" />
      <circle cx="12" cy="12" r="1.4" fill="currentColor" />
      <circle cx="18" cy="12" r="1.4" fill="currentColor" />
    </template>
    <!-- close -->
    <template v-else-if="name === 'close'">
      <path d="m7 7 10 10M17 7 7 17" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
    </template>
    <!-- pin -->
    <template v-else-if="name === 'pin'">
      <path d="M14.5 4.5 19.5 9.5 14 12l-2 7-1.5-1.5L12 12 5.5 9.5 10.5 4.5Z" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" />
    </template>
    <!-- trash -->
    <template v-else-if="name === 'trash'">
      <path d="M5 7h14M9.5 7V5.5A1.5 1.5 0 0 1 11 4h2a1.5 1.5 0 0 1 1.5 1.5V7M8 7l.8 12h6.4L16 7" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" />
    </template>
  </svg>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  name: { type: String, required: true },
  size: { type: String, default: 'md' }, // sm | md | lg
})

const sizeClass = computed(() => `xq-icon--${props.size}`)
</script>

<style scoped>
.xq-icon {
  display: block;
  flex-shrink: 0;
}
.xq-icon--sm {
  width: 16px;
  height: 16px;
}
.xq-icon--md {
  width: 18px;
  height: 18px;
}
.xq-icon--lg {
  width: 20px;
  height: 20px;
}
</style>
