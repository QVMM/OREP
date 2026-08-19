<template>
  <div
    class="agent-visualizer"
    :class="[`variant-${variant}`, `state-${state}`, { compact }]"
    :style="visualStyle"
    aria-hidden="true"
  >
    <template v-if="variant === 'aura'">
      <div class="aura-dots"></div>
      <div class="aura-core">
        <span v-for="i in 5" :key="i" class="aura-ring" :style="{ '--i': i }"></span>
      </div>
    </template>

    <template v-else-if="variant === 'wave'">
      <svg class="wave-field" viewBox="0 0 240 96" preserveAspectRatio="none">
        <path class="wave-line wave-line-a" d="M0 48 C 24 18, 48 78, 72 48 S 120 18, 144 48 S 192 78, 216 48 S 252 18, 276 48" />
        <path class="wave-line wave-line-b" d="M0 50 C 30 78, 50 20, 78 50 S 126 82, 154 50 S 202 20, 230 50 S 270 82, 298 50" />
      </svg>
    </template>

    <template v-else-if="variant === 'grid'">
      <span v-for="i in 64" :key="i" class="grid-dot" :style="{ '--i': i }"></span>
    </template>

    <template v-else>
      <span v-for="i in 18" :key="i" class="bar-line" :style="{ '--i': i }"></span>
    </template>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  variant: { type: String, default: 'aura' },
  state: { type: String, default: 'listening' },
  color: { type: String, default: '#1FD5F9' },
  compact: { type: Boolean, default: false }
})

const visualStyle = computed(() => ({
  '--agent-color': props.color
}))
</script>

<style scoped>
.agent-visualizer {
  position: relative;
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 0;
  color: var(--agent-color);
  overflow: hidden;
}

.variant-aura {
  display: grid;
  place-items: center;
}

.aura-dots {
  position: absolute;
  inset: 0;
  opacity: .42;
  background-image: radial-gradient(circle, color-mix(in srgb, var(--agent-color) 42%, transparent) 1px, transparent 1px);
  background-size: 7px 7px;
  mask-image: radial-gradient(circle, rgba(0,0,0,.8), transparent 66%);
  animation: visual-drift 12s linear infinite;
}

.aura-core {
  position: relative;
  width: min(58%, 260px);
  aspect-ratio: 1;
  filter: drop-shadow(0 0 18px color-mix(in srgb, var(--agent-color) 38%, transparent));
}

.compact .aura-core {
  width: 72%;
}

.aura-ring {
  position: absolute;
  inset: 10%;
  border: 2px solid color-mix(in srgb, var(--agent-color) 74%, transparent);
  border-radius: 45% 55% 50% 50%;
  opacity: .74;
  transform: rotate(calc(var(--i) * 19deg)) scale(calc(.82 + var(--i) * .035));
  animation: aura-pulse calc(3.4s + var(--i) * .28s) cubic-bezier(.19, 1, .22, 1) infinite;
}

.aura-ring:nth-child(2n) {
  border-radius: 54% 46% 43% 57%;
  border-color: color-mix(in srgb, var(--agent-color) 48%, #f4f7ff);
  animation-direction: reverse;
}

.state-speaking .aura-ring,
.state-recording .aura-ring {
  animation-duration: calc(2s + var(--i) * .18s);
}

.state-thinking .aura-ring,
.state-processing .aura-ring {
  animation-duration: calc(4.2s + var(--i) * .22s);
  opacity: .5;
}

.variant-wave {
  display: grid;
  place-items: center;
}

.wave-field {
  width: 100%;
  height: 100%;
  overflow: visible;
}

.wave-line {
  fill: none;
  stroke: var(--agent-color);
  stroke-width: 3;
  stroke-linecap: round;
  opacity: .78;
  filter: drop-shadow(0 0 10px color-mix(in srgb, var(--agent-color) 50%, transparent));
  stroke-dasharray: 18 15;
  animation: wave-run 2.6s linear infinite;
}

.wave-line-b {
  opacity: .32;
  stroke-width: 2;
  animation-duration: 3.5s;
  animation-direction: reverse;
}

.variant-grid {
  display: grid;
  grid-template-columns: repeat(8, 1fr);
  grid-template-rows: repeat(8, 1fr);
  gap: 7%;
  padding: 12%;
}

.grid-dot {
  border-radius: 50%;
  background: currentColor;
  opacity: calc(.12 + (var(--i) % 5) * .045);
  transform: scale(.62);
  box-shadow: 0 0 12px color-mix(in srgb, var(--agent-color) 38%, transparent);
  animation: grid-breathe 2.6s cubic-bezier(.19, 1, .22, 1) infinite;
  animation-delay: calc((var(--i) % 13) * -120ms);
}

.state-connecting .grid-dot {
  animation-duration: 1.7s;
}

.variant-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4%;
  padding: 0 12%;
}

.bar-line {
  width: 3px;
  height: 28%;
  border-radius: 999px;
  background: currentColor;
  opacity: .72;
  box-shadow: 0 0 12px color-mix(in srgb, var(--agent-color) 44%, transparent);
  animation: bar-listen 1.2s cubic-bezier(.19, 1, .22, 1) infinite;
  animation-delay: calc((var(--i) % 9) * -80ms);
}

.state-idle .bar-line,
.state-muted .bar-line {
  animation-duration: 2.8s;
  opacity: .28;
}

@keyframes aura-pulse {
  0%, 100% {
    transform: rotate(calc(var(--i) * 19deg)) scale(calc(.82 + var(--i) * .035));
    filter: blur(.2px);
  }
  50% {
    transform: rotate(calc(var(--i) * 19deg + 26deg)) scale(calc(.92 + var(--i) * .045));
    filter: blur(1.4px);
  }
}

@keyframes visual-drift {
  from { transform: translate3d(0, 0, 0); }
  to { transform: translate3d(14px, 14px, 0); }
}

@keyframes wave-run {
  from { stroke-dashoffset: 0; transform: translateX(-8%); }
  to { stroke-dashoffset: -132; transform: translateX(0); }
}

@keyframes grid-breathe {
  0%, 100% { transform: scale(.45); opacity: .18; }
  45% { transform: scale(1); opacity: .82; }
}

@keyframes bar-listen {
  0%, 100% { transform: scaleY(.42); opacity: .36; }
  50% { transform: scaleY(1.52); opacity: .95; }
}

@media (prefers-reduced-motion: reduce) {
  .aura-dots,
  .aura-ring,
  .wave-line,
  .grid-dot,
  .bar-line {
    animation: none !important;
  }
}
</style>
