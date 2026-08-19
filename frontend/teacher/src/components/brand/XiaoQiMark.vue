<template>
  <span
    class="xiaoqi-mark"
    :class="{
      'is-hoverable': hoverable,
      'is-active': active,
    }"
    :style="wrapStyle"
    role="img"
    :aria-label="ariaLabel"
  >
    <img
      class="xiaoqi-mark__img"
      :src="src"
      alt=""
      aria-hidden="true"
      draggable="false"
    />
  </span>
</template>

<script setup>
import { computed } from 'vue'

/** 与用户端同一套新形象（ai-mascot/owlby） */
const ASSET = '/brand/xiaoqi-owlby.png?v=20260812'

const props = defineProps({
  size: { type: [Number, String], default: 22 },
  hoverable: { type: Boolean, default: true },
  active: { type: Boolean, default: false },
  ariaLabel: { type: String, default: '小启AI' },
  src: { type: String, default: ASSET },
})

const wrapStyle = computed(() => {
  const s = typeof props.size === 'number' ? `${props.size}px` : props.size
  return { width: s, height: s }
})
</script>

<style scoped>
.xiaoqi-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  line-height: 0;
  vertical-align: middle;
  transform: translateY(-1px);
}

.xiaoqi-mark__img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: contain;
  object-position: center bottom;
  pointer-events: none;
  user-select: none;
  transform-origin: 50% 70%;
  will-change: transform;
  filter: drop-shadow(0 2px 3px rgba(100, 55, 10, 0.14));
  transition: transform 0.35s cubic-bezier(0.22, 1, 0.36, 1);
}

.xiaoqi-mark.is-hoverable:hover .xiaoqi-mark__img,
.xiaoqi-mark.is-hoverable:focus-visible .xiaoqi-mark__img {
  animation: xiaoqi-alive 1.15s cubic-bezier(0.45, 0.05, 0.25, 1) infinite;
}

:global(.workspace-nav__item.is-xiaoqi-nav:hover .xiaoqi-mark.is-hoverable .xiaoqi-mark__img),
:global(.ai-app-card:hover .xiaoqi-mark.is-hoverable .xiaoqi-mark__img) {
  animation: xiaoqi-alive 1.15s cubic-bezier(0.45, 0.05, 0.25, 1) infinite;
}

.xiaoqi-mark.is-active:not(:hover) .xiaoqi-mark__img {
  animation: xiaoqi-breathe 3.2s ease-in-out infinite;
}

@keyframes xiaoqi-alive {
  0%,
  100% {
    transform: translate3d(0, 0, 0) rotate(0deg) scale(1);
  }
  18% {
    transform: translate3d(0, -1.2px, 0) rotate(-5deg) scale(1.045);
  }
  40% {
    transform: translate3d(0, -2px, 0) rotate(4deg) scale(1.06);
  }
  62% {
    transform: translate3d(0, -0.8px, 0) rotate(-2.5deg) scale(1.03);
  }
  82% {
    transform: translate3d(0, -1.4px, 0) rotate(2deg) scale(1.04);
  }
}

@keyframes xiaoqi-breathe {
  0%,
  100% {
    transform: translate3d(0, 0, 0) scale(1);
  }
  50% {
    transform: translate3d(0, -0.6px, 0) scale(1.015);
  }
}

@media (prefers-reduced-motion: reduce) {
  .xiaoqi-mark__img,
  .xiaoqi-mark.is-hoverable:hover .xiaoqi-mark__img,
  .xiaoqi-mark.is-active .xiaoqi-mark__img {
    animation: none !important;
    transition: none !important;
  }
}
</style>
