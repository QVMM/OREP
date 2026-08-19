<template>
  <div class="voice-avatar" :class="{ speaking, muted }" role="img" :aria-label="normalizedInitials">
    <span class="avatar-aura" aria-hidden="true"></span>
    <span class="avatar-halo halo-outer" aria-hidden="true"></span>
    <span class="avatar-halo halo-mid" aria-hidden="true"></span>

    <svg class="voice-wave" viewBox="0 0 280 128" aria-hidden="true" focusable="false">
      <defs>
        <filter :id="filterId" x="-20%" y="-100%" width="140%" height="300%">
          <feGaussianBlur stdDeviation="1.4" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <path class="wave-glow wave-left" :style="{ filter: `url(#${filterId})` }" d="M20 64 C34 64 38 64 48 64 C58 64 62 64 72 64 C82 64 86 64 100 64" />
      <path class="wave-glow wave-right" :style="{ filter: `url(#${filterId})` }" d="M180 64 C194 64 198 64 208 64 C218 64 222 64 232 64 C242 64 246 64 260 64" />
      <path class="wave-main wave-left" d="M20 64 C34 64 38 64 48 64 C58 64 62 64 72 64 C82 64 86 64 100 64" />
      <path class="wave-main wave-right" d="M180 64 C194 64 198 64 208 64 C218 64 222 64 232 64 C242 64 246 64 260 64" />
      <path class="wave-thin wave-left" d="M20 64 C34 64 38 64 48 64 C58 64 62 64 72 64 C82 64 86 64 100 64" />
      <path class="wave-thin wave-right" d="M180 64 C194 64 198 64 208 64 C218 64 222 64 232 64 C242 64 246 64 260 64" />
    </svg>

    <span class="avatar-core" aria-hidden="true">
      <span class="avatar-sheen"></span>
      <span class="avatar-ring"></span>
      <span class="avatar-initials">{{ normalizedInitials }}</span>
    </span>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  initials: { type: String, default: '?' },
  speaking: { type: Boolean, default: false },
  muted: { type: Boolean, default: false }
})

const normalizedInitials = computed(() => props.initials || '?')
// Unique filter id so multiple avatars on a page don't clash
const filterId = `wave-glow-${Math.random().toString(36).slice(2, 9)}`
</script>

<style scoped>
.voice-avatar {
  --voice-color: #5b8def;
  --orb-from: #9bb8f5;
  --orb-mid: #6b93e8;
  --orb-to: #4a78d4;
  --orb-shadow: 90, 130, 210;
  position: relative;
  width: clamp(200px, 22vw, 320px);
  height: clamp(200px, 22vw, 320px);
  display: grid;
  place-items: center;
  isolation: isolate;
}

.avatar-aura {
  position: absolute;
  width: 72%;
  height: 72%;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(var(--orb-shadow), 0.14) 0%, rgba(var(--orb-shadow), 0.05) 42%, transparent 70%);
  z-index: 0;
  pointer-events: none;
}

.avatar-halo {
  position: absolute;
  border-radius: 50%;
  border: 1px solid rgba(var(--orb-shadow), 0.14);
  z-index: 0;
  pointer-events: none;
}

.halo-outer {
  width: 78%;
  height: 78%;
  border-color: rgba(var(--orb-shadow), 0.1);
  box-shadow: 0 0 0 10px rgba(var(--orb-shadow), 0.035);
}

.halo-mid {
  width: 62%;
  height: 62%;
  border-color: rgba(var(--orb-shadow), 0.16);
}

.voice-wave {
  position: absolute;
  inset: 18% 4%;
  width: auto;
  height: auto;
  overflow: visible;
  z-index: 1;
  opacity: 0.2;
  transition: opacity 0.22s ease, filter 0.22s ease;
}

.wave-main,
.wave-thin,
.wave-glow {
  fill: none;
  stroke: var(--voice-color);
  stroke-linecap: round;
  vector-effect: non-scaling-stroke;
}

.wave-glow {
  stroke-width: 8;
  opacity: 0.1;
}

.wave-main {
  stroke-width: 2.2;
  opacity: 0.7;
}

.wave-thin {
  stroke-width: 1.1;
  opacity: 0.28;
}

.avatar-core {
  position: relative;
  z-index: 2;
  width: clamp(88px, 9vw, 128px);
  height: clamp(88px, 9vw, 128px);
  display: grid;
  place-items: center;
  border-radius: 50%;
  background:
    radial-gradient(circle at 34% 28%, rgba(255, 255, 255, 0.78) 0%, transparent 34%),
    radial-gradient(circle at 70% 78%, rgba(40, 70, 140, 0.2) 0%, transparent 42%),
    linear-gradient(145deg, var(--orb-from) 0%, var(--orb-mid) 48%, var(--orb-to) 100%);
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.6),
    inset 0 -18px 28px rgba(40, 70, 140, 0.16),
    0 0 0 1px rgba(var(--orb-shadow), 0.1),
    0 18px 40px rgba(var(--orb-shadow), 0.22),
    0 6px 14px rgba(15, 23, 42, 0.07);
  transition: transform 0.22s ease, box-shadow 0.22s ease, border-color 0.22s ease;
}

.avatar-sheen {
  position: absolute;
  inset: 10% 14% auto;
  height: 34%;
  border-radius: 50%;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.55), transparent);
  pointer-events: none;
}

.avatar-ring {
  position: absolute;
  inset: 8%;
  border-radius: inherit;
  border: 1px solid rgba(255, 255, 255, 0.28);
  background: radial-gradient(circle at 40% 30%, rgba(255, 255, 255, 0.16), transparent 46%);
  pointer-events: none;
}

.avatar-initials {
  position: relative;
  z-index: 1;
  color: #ffffff;
  font-size: clamp(28px, 2.6vw, 42px);
  font-weight: 820;
  line-height: 1;
  letter-spacing: -0.02em;
  text-shadow: 0 1px 2px rgba(30, 50, 100, 0.28);
  user-select: none;
  text-transform: lowercase;
}

.speaking {
  --voice-color: #5b8def;
}

.speaking .voice-wave {
  opacity: 0.85;
}

.speaking .avatar-aura {
  animation: aura-breathe 1.6s ease-in-out infinite;
}

.speaking .halo-outer {
  animation: halo-pulse 1.8s ease-out infinite;
}

.speaking .halo-mid {
  animation: halo-pulse 1.8s ease-out infinite 0.25s;
}

.speaking .wave-left.wave-main {
  animation: wave-left-main 880ms cubic-bezier(0.19, 1, 0.22, 1) infinite;
}

.speaking .wave-right.wave-main {
  animation: wave-right-main 880ms cubic-bezier(0.19, 1, 0.22, 1) infinite;
  animation-delay: -120ms;
}

.speaking .wave-left.wave-thin,
.speaking .wave-left.wave-glow {
  animation: wave-left-alt 1.16s cubic-bezier(0.19, 1, 0.22, 1) infinite;
}

.speaking .wave-right.wave-thin,
.speaking .wave-right.wave-glow {
  animation: wave-right-alt 1.16s cubic-bezier(0.19, 1, 0.22, 1) infinite;
  animation-delay: -150ms;
}

.speaking .avatar-core {
  border-color: rgba(255, 255, 255, 0.58);
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.65),
    inset 0 -18px 28px rgba(40, 70, 140, 0.14),
    0 0 0 1px rgba(var(--orb-shadow), 0.14),
    0 0 0 12px rgba(var(--orb-shadow), 0.08),
    0 20px 48px rgba(var(--orb-shadow), 0.26),
    0 8px 18px rgba(15, 23, 42, 0.08);
  animation: core-speaking 880ms cubic-bezier(0.19, 1, 0.22, 1) infinite;
}

.muted {
  --voice-color: #94a3b8;
  --orb-from: #e2e8f0;
  --orb-mid: #cbd5e1;
  --orb-to: #94a3b8;
}

.muted .voice-wave {
  opacity: 0.12;
}

.muted .avatar-aura,
.muted .avatar-halo {
  opacity: 0.45;
}

.muted .avatar-initials {
  text-shadow: 0 1px 1px rgba(15, 23, 42, 0.18);
}

@keyframes wave-left-main {
  0%, 100% { d: path("M20 64 C34 64 38 64 48 64 C58 64 62 64 72 64 C82 64 86 64 100 64"); }
  50% { d: path("M20 64 C32 64 37 55 46 64 C55 78 60 34 70 64 C80 94 86 50 100 64"); }
}

@keyframes wave-right-main {
  0%, 100% { d: path("M180 64 C194 64 198 64 208 64 C218 64 222 64 232 64 C242 64 246 64 260 64"); }
  50% { d: path("M180 64 C194 50 199 94 208 64 C218 34 223 78 234 64 C244 55 249 64 260 64"); }
}

@keyframes wave-left-alt {
  0%, 100% { d: path("M20 64 C34 64 38 64 48 64 C58 64 62 64 72 64 C82 64 86 64 100 64"); }
  50% { d: path("M20 64 C32 64 38 72 48 64 C58 48 64 88 74 64 C84 40 88 68 100 64"); }
}

@keyframes wave-right-alt {
  0%, 100% { d: path("M180 64 C194 64 198 64 208 64 C218 64 222 64 232 64 C242 64 246 64 260 64"); }
  50% { d: path("M180 64 C192 68 198 40 208 64 C218 88 224 48 234 64 C244 72 250 64 260 64"); }
}

@keyframes core-speaking {
  0%, 100% { transform: scale(1); }
  45% { transform: scale(1.035); }
}

@keyframes aura-breathe {
  0%, 100% { transform: scale(1); opacity: 0.9; }
  50% { transform: scale(1.08); opacity: 1; }
}

@keyframes halo-pulse {
  0% { transform: scale(0.92); opacity: 0.55; }
  70% { transform: scale(1.06); opacity: 0; }
  100% { transform: scale(1.08); opacity: 0; }
}

@media (prefers-reduced-motion: reduce) {
  .speaking .wave-main,
  .speaking .wave-thin,
  .speaking .wave-glow,
  .speaking .avatar-core,
  .speaking .avatar-aura,
  .speaking .avatar-halo {
    animation: none !important;
  }
}
</style>
