<template>
  <div
    class="score-medal"
    :class="[`is-${tier}`, { 'is-animate': animate }]"
    :aria-label="ariaLabel"
    role="img"
  >
    <svg class="medal-svg" viewBox="0 0 88 108" aria-hidden="true">
      <defs>
        <!-- 丝带 -->
        <linearGradient :id="uid('ribL')" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" :stop-color="palette.ribbonLight" />
          <stop offset="55%" :stop-color="palette.ribbon" />
          <stop offset="100%" :stop-color="palette.ribbonDeep" />
        </linearGradient>
        <linearGradient :id="uid('ribR')" x1="100%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" :stop-color="palette.ribbonLight" />
          <stop offset="55%" :stop-color="palette.ribbon" />
          <stop offset="100%" :stop-color="palette.ribbonDeep" />
        </linearGradient>

        <!-- 金属盘面 -->
        <radialGradient :id="uid('disc')" cx="38%" cy="32%" r="68%">
          <stop offset="0%" :stop-color="palette.metalHi" />
          <stop offset="42%" :stop-color="palette.metal" />
          <stop offset="78%" :stop-color="palette.metalMid" />
          <stop offset="100%" :stop-color="palette.metalDeep" />
        </radialGradient>
        <linearGradient :id="uid('rim')" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" :stop-color="palette.rimHi" />
          <stop offset="45%" :stop-color="palette.metal" />
          <stop offset="100%" :stop-color="palette.rimDeep" />
        </linearGradient>
        <radialGradient :id="uid('inner')" cx="42%" cy="36%" r="62%">
          <stop offset="0%" :stop-color="palette.innerHi" />
          <stop offset="100%" :stop-color="palette.innerDeep" />
        </radialGradient>

        <!-- 高光扫光 -->
        <linearGradient :id="uid('shine')" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="#fff" stop-opacity="0" />
          <stop offset="45%" stop-color="#fff" stop-opacity="0.55" />
          <stop offset="55%" stop-color="#fff" stop-opacity="0.15" />
          <stop offset="100%" stop-color="#fff" stop-opacity="0" />
        </linearGradient>

        <filter :id="uid('soft')" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="3" stdDeviation="2.2" flood-color="#5a3a18" flood-opacity="0.28" />
        </filter>
        <filter :id="uid('glow')" x="-30%" y="-30%" width="160%" height="160%">
          <feGaussianBlur stdDeviation="1.2" result="b" />
          <feMerge>
            <feMergeNode in="b" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>

        <clipPath :id="uid('discClip')">
          <circle cx="44" cy="62" r="26" />
        </clipPath>
      </defs>

      <!-- 丝带 -->
      <g class="ribbon">
        <path
          d="M33 8 L28 46 L44 36 L44 8 Z"
          :fill="`url(#${uid('ribL')})`"
        />
        <path
          d="M55 8 L60 46 L44 36 L44 8 Z"
          :fill="`url(#${uid('ribR')})`"
        />
        <path
          d="M33 8 H55 L52 18 H36 Z"
          :fill="palette.ribbonKnot"
          opacity="0.92"
        />
      </g>

      <!-- 奖牌盘 -->
      <g class="disc" :filter="`url(#${uid('soft')})`">
        <circle cx="44" cy="62" r="30" :fill="`url(#${uid('rim')})`" />
        <circle cx="44" cy="62" r="26" :fill="`url(#${uid('disc')})`" />
        <circle
          cx="44"
          cy="62"
          r="21.5"
          fill="none"
          :stroke="palette.ring"
          stroke-width="1.4"
          opacity="0.85"
        />
        <circle cx="44" cy="62" r="18" :fill="`url(#${uid('inner')})`" opacity="0.55" />

        <!-- 星形浮雕 -->
        <path
          class="star"
          d="M44 46.5l3.1 6.4 7 .9-5.1 5 1.3 7L44 62.2l-6.3 3.6 1.3-7-5.1-5 7-.9Z"
          :fill="palette.star"
          :stroke="palette.starStroke"
          stroke-width="0.7"
          stroke-linejoin="round"
          :filter="`url(#${uid('glow')})`"
        />

        <!-- 金属扫光 -->
        <g :clip-path="`url(#${uid('discClip')})`">
          <rect
            class="shine"
            x="-20"
            y="36"
            width="28"
            height="52"
            :fill="`url(#${uid('shine')})`"
            opacity="0.55"
          />
        </g>

        <!-- 顶部高光弧 -->
        <path
          d="M28 52c4-10 14-15 24-12"
          fill="none"
          stroke="#fff"
          stroke-width="2.2"
          stroke-linecap="round"
          opacity="0.35"
        />
      </g>
    </svg>
    <span v-if="showCaption" class="medal-cap">{{ caption }}</span>
  </div>
</template>

<script setup>
import { computed, useId } from 'vue'

const props = defineProps({
  /** gold | silver | bronze */
  tier: {
    type: String,
    required: true,
    validator: (v) => ['gold', 'silver', 'bronze'].includes(v)
  },
  animate: { type: Boolean, default: true },
  showCaption: { type: Boolean, default: true }
})

const idBase = useId().replace(/[^a-zA-Z0-9_-]/g, '')
function uid(part) {
  return `sm-${idBase}-${part}`
}

const CAPTION = { gold: '金牌', silver: '银牌', bronze: '铜牌' }
const caption = computed(() => CAPTION[props.tier] || '')
const ariaLabel = computed(() => `本场评级：${caption.value}`)

const PALETTES = {
  gold: {
    ribbon: '#e84a1c',
    ribbonLight: '#ff7a45',
    ribbonDeep: '#c43a12',
    ribbonKnot: '#f05a2e',
    metalHi: '#fff6d0',
    metal: '#f0c14b',
    metalMid: '#e0a020',
    metalDeep: '#b07810',
    rimHi: '#ffe9a0',
    rimDeep: '#8a5a08',
    innerHi: '#fff8de',
    innerDeep: '#d4a018',
    ring: '#fff0b8',
    star: '#fff8e8',
    starStroke: '#c49218'
  },
  silver: {
    ribbon: '#5b6b7c',
    ribbonLight: '#8a9aab',
    ribbonDeep: '#3d4a58',
    ribbonKnot: '#6d7e90',
    metalHi: '#ffffff',
    metal: '#d5dee8',
    metalMid: '#a8b4c2',
    metalDeep: '#6f7e90',
    rimHi: '#f4f7fb',
    rimDeep: '#556370',
    innerHi: '#ffffff',
    innerDeep: '#9aabbc',
    ring: '#eef3f8',
    star: '#ffffff',
    starStroke: '#7a8a9a'
  },
  bronze: {
    ribbon: '#c45a28',
    ribbonLight: '#e08a55',
    ribbonDeep: '#8f3d18',
    ribbonKnot: '#d06830',
    metalHi: '#f7d2b0',
    metal: '#d08a52',
    metalMid: '#b06835',
    metalDeep: '#7a4420',
    rimHi: '#f0c49a',
    rimDeep: '#5c3014',
    innerHi: '#f8dfc8',
    innerDeep: '#a86030',
    ring: '#efc9a4',
    star: '#fff0e4',
    starStroke: '#9a5830'
  }
}

const palette = computed(() => PALETTES[props.tier] || PALETTES.bronze)
</script>

<style scoped>
.score-medal {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  width: 72px;
  perspective: 420px;
  user-select: none;
}
.medal-svg {
  width: 64px;
  height: 78px;
  display: block;
  overflow: visible;
  transform-origin: 50% 58%;
  filter: drop-shadow(0 8px 14px rgba(90, 50, 20, 0.16));
}
.medal-cap {
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.12em;
  color: var(--orange-deep, #c43a12);
  line-height: 1;
}
.score-medal.is-silver .medal-cap {
  color: #5b6b7c;
}
.score-medal.is-bronze .medal-cap {
  color: #9a5830;
}

.score-medal.is-animate .medal-svg {
  animation: medalFloat 4.2s ease-in-out infinite;
}
.score-medal.is-animate .shine {
  animation: medalShine 3.6s ease-in-out infinite;
}
.score-medal.is-animate .star {
  animation: medalStar 4.2s ease-in-out infinite;
}

@keyframes medalFloat {
  0%, 100% {
    transform: translateY(0) rotateY(-7deg) rotateZ(-1.2deg);
  }
  50% {
    transform: translateY(-5px) rotateY(7deg) rotateZ(1.2deg);
  }
}
@keyframes medalShine {
  0% { transform: translateX(-8px) skewX(-12deg); opacity: 0; }
  18% { opacity: 0.65; }
  42% { transform: translateX(72px) skewX(-12deg); opacity: 0; }
  100% { transform: translateX(72px) skewX(-12deg); opacity: 0; }
}
@keyframes medalStar {
  0%, 100% { opacity: 0.92; transform: scale(1); transform-origin: 44px 58px; }
  50% { opacity: 1; transform: scale(1.04); transform-origin: 44px 58px; }
}

@media (prefers-reduced-motion: reduce) {
  .score-medal.is-animate .medal-svg,
  .score-medal.is-animate .shine,
  .score-medal.is-animate .star {
    animation: none !important;
  }
}
</style>
