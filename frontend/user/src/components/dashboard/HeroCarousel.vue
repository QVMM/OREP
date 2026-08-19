<template>
  <section class="hero-carousel" aria-label="首页轮播">
    <div class="carousel-track">
      <div
        v-for="(slide, index) in slides"
        :key="index"
        class="carousel-slide"
        :class="{ 'carousel-slide--active': index === activeIndex }"
        :style="slide.gradient ? { background: slide.gradient } : {}"
      >
        <div class="carousel-content">
          <span v-if="slide.eyebrow" class="carousel-eyebrow">{{ slide.eyebrow }}</span>
          <h1 class="carousel-title">{{ slide.title }}</h1>
          <p class="carousel-subtitle">{{ slide.subtitle }}</p>
          <div class="carousel-actions">
            <BaseButton
              v-if="slide.ctaText"
              type="primary"
              size="large"
              @click="$emit('navigate', slide.ctaPath)"
            >
              {{ slide.ctaText }}
            </BaseButton>
            <BaseButton
              v-if="slide.secondaryText"
              type="secondary"
              size="large"
              @click="$emit('navigate', slide.secondaryPath)"
            >
              {{ slide.secondaryText }}
            </BaseButton>
          </div>
        </div>
        <div v-if="slide.illustration" class="carousel-illustration" aria-hidden="true">
          <img :src="slide.illustration" alt="" />
        </div>
      </div>
    </div>

    <button
      v-if="slides.length > 1"
      class="carousel-arrow carousel-arrow--left"
      aria-label="上一张"
      @click="prev"
    >
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <path d="M12.5 15L7.5 10L12.5 5" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </button>

    <button
      v-if="slides.length > 1"
      class="carousel-arrow carousel-arrow--right"
      aria-label="下一张"
      @click="next"
    >
      <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
        <path d="M7.5 5L12.5 10L7.5 15" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
      </svg>
    </button>

    <div v-if="slides.length > 1" class="carousel-dots" aria-label="轮播页码">
      <button
        v-for="(_, index) in slides"
        :key="index"
        class="carousel-dot"
        :class="{ 'carousel-dot--active': index === activeIndex }"
        :aria-label="`切换到第 ${index + 1} 张`"
        @click="goTo(index)"
      ></button>
    </div>
  </section>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { BaseButton } from '../base'

const props = defineProps({
  slides: {
    type: Array,
    default: () => []
  },
  autoplay: {
    type: Boolean,
    default: true
  },
  interval: {
    type: Number,
    default: 5000
  }
})

defineEmits(['navigate'])

const activeIndex = ref(0)
let timer = null

function next() {
  if (!props.slides.length) return
  activeIndex.value = (activeIndex.value + 1) % props.slides.length
}

function prev() {
  if (!props.slides.length) return
  activeIndex.value = (activeIndex.value - 1 + props.slides.length) % props.slides.length
}

function goTo(index) {
  activeIndex.value = index
}

function startAutoplay() {
  stopAutoplay()
  if (props.autoplay && props.slides.length > 1) {
    timer = setInterval(next, props.interval)
  }
}

function stopAutoplay() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

watch(() => props.slides, startAutoplay, { immediate: true })
onMounted(startAutoplay)
onUnmounted(stopAutoplay)
</script>

<style scoped>
.hero-carousel {
  position: relative;
  border-radius: var(--radius-lg);
  overflow: hidden;
}

.carousel-track {
  position: relative;
  min-height: 320px;
}

.carousel-slide {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  padding: clamp(36px, 5vw, 64px);
  opacity: 0;
  transform: translateX(40px);
  transition: opacity 0.5s ease, transform 0.5s ease;
  pointer-events: none;
  background: linear-gradient(135deg, #007AFF 0%, #5856D6 100%);
  border-radius: var(--radius-lg);
}

.carousel-slide--active {
  position: relative;
  opacity: 1;
  transform: translateX(0);
  pointer-events: auto;
}

.carousel-content {
  position: relative;
  z-index: 2;
  width: min(640px, 60%);
}

.carousel-eyebrow {
  display: inline-block;
  padding: 6px 14px;
  margin-bottom: 16px;
  border-radius: var(--radius-sm);
  background: rgba(255, 255, 255, 0.18);
  color: rgba(255, 255, 255, 0.95);
  font-family: var(--font-sans);
  font-size: var(--font-size-xs);
  font-weight: var(--font-weight-semibold);
  letter-spacing: 1px;
  backdrop-filter: blur(4px);
}

.carousel-title {
  margin: 0 0 12px;
  color: var(--text-inverse);
  font-family: var(--font-sans);
  font-size: clamp(32px, 4vw, 48px);
  font-weight: var(--font-weight-bold);
  line-height: var(--line-height-tight);
  letter-spacing: -0.5px;
}

.carousel-subtitle {
  margin: 0 0 28px;
  color: rgba(255, 255, 255, 0.82);
  font-size: var(--font-size-base);
  line-height: var(--line-height-relaxed);
  max-width: 520px;
}

.carousel-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.carousel-actions :deep(.base-button--primary) {
  background-color: rgba(255, 255, 255, 0.95);
  color: #007AFF;
}

.carousel-actions :deep(.base-button--primary:hover) {
  background-color: #fff;
}

.carousel-actions :deep(.base-button--secondary) {
  background-color: rgba(255, 255, 255, 0.15);
  color: var(--text-inverse);
  border-color: rgba(255, 255, 255, 0.35);
  backdrop-filter: blur(4px);
}

.carousel-actions :deep(.base-button--secondary:hover) {
  background-color: rgba(255, 255, 255, 0.25);
  border-color: rgba(255, 255, 255, 0.5);
}

.carousel-illustration {
  position: absolute;
  right: 0;
  top: 0;
  bottom: 0;
  width: 40%;
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
}

.carousel-illustration img {
  max-width: 100%;
  max-height: 80%;
  object-fit: contain;
  opacity: 0.9;
}

.carousel-arrow {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  z-index: 3;
  width: 44px;
  height: 44px;
  display: grid;
  place-items: center;
  border: none;
  border-radius: var(--radius-full);
  background: rgba(255, 255, 255, 0.18);
  color: var(--text-inverse);
  cursor: pointer;
  transition: all var(--transition-fast);
  backdrop-filter: blur(4px);
}

.carousel-arrow:hover {
  background: rgba(255, 255, 255, 0.32);
  transform: translateY(-50%) scale(1.08);
}

.carousel-arrow--left {
  left: 16px;
}

.carousel-arrow--right {
  right: 16px;
}

.carousel-dots {
  position: absolute;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 3;
  display: flex;
  align-items: center;
  gap: 10px;
}

.carousel-dot {
  width: 10px;
  height: 10px;
  padding: 0;
  border: none;
  border-radius: var(--radius-full);
  background: rgba(255, 255, 255, 0.4);
  cursor: pointer;
  transition: all var(--transition-normal);
}

.carousel-dot--active {
  width: 28px;
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.95);
}

.carousel-dot:hover:not(.carousel-dot--active) {
  background: rgba(255, 255, 255, 0.65);
}

@media (max-width: 767px) {
  .carousel-track {
    min-height: 280px;
  }

  .carousel-slide {
    padding: 28px 20px;
  }

  .carousel-content {
    width: 100%;
  }

  .carousel-illustration {
    display: none;
  }

  .carousel-title {
    font-size: 28px;
  }

  .carousel-subtitle {
    font-size: var(--font-size-sm);
  }

  .carousel-arrow {
    width: 36px;
    height: 36px;
  }

  .carousel-arrow--left {
    left: 8px;
  }

  .carousel-arrow--right {
    right: 8px;
  }
}
</style>
