<script setup>
import { computed, ref } from 'vue'

defineOptions({ name: 'AnimatedTeamTooltip' })

const props = defineProps({
  items: {
    type: Array,
    default: () => []
  },
  totalCount: {
    type: Number,
    default: 0
  },
  maxVisible: {
    type: Number,
    default: 5
  }
})

const hoveredId = ref(null)
const pointerX = ref(0)

const visibleItems = computed(() => props.items.slice(0, Math.max(1, props.maxVisible)))
const resolvedTotal = computed(() => Math.max(Number(props.totalCount || 0), props.items.length))
const hiddenCount = computed(() => Math.max(0, resolvedTotal.value - visibleItems.value.length))
const tooltipTranslate = computed(() => `${pointerX.value * 9}px`)
const tooltipRotation = computed(() => `${pointerX.value * 5}deg`)

function updatePointer(event, id) {
  hoveredId.value = id
  const rect = event.currentTarget?.getBoundingClientRect()
  if (!rect?.width) {
    pointerX.value = 0
    return
  }
  const relativeX = (event.clientX - rect.left - rect.width / 2) / (rect.width / 2)
  pointerX.value = Math.max(-1, Math.min(1, relativeX))
}

function showFromKeyboard(id) {
  hoveredId.value = id
  pointerX.value = 0
}

function hideTooltip() {
  hoveredId.value = null
  pointerX.value = 0
}
</script>

<template>
  <div
    class="animated-team-tooltip"
    :aria-label="`小队成员，共 ${resolvedTotal} 人`"
    data-testid="team-animated-tooltip"
  >
    <div
      v-for="(item, index) in visibleItems"
      :key="item.id"
      class="animated-team-tooltip__item"
      :style="{ '--member-index': index, '--member-color': item.color }"
      @mouseenter="updatePointer($event, item.id)"
      @mousemove="updatePointer($event, item.id)"
      @mouseleave="hideTooltip"
      @focusin="showFromKeyboard(item.id)"
      @focusout="hideTooltip"
    >
      <Transition name="member-tooltip">
        <div
          v-if="hoveredId === item.id"
          :id="`team-member-tooltip-${item.id}`"
          class="animated-team-tooltip__popup"
          :style="{
            '--tooltip-translate': tooltipTranslate,
            '--tooltip-rotation': tooltipRotation
          }"
          role="tooltip"
          data-testid="team-member-tooltip"
        >
          <strong>{{ item.name }}</strong>
          <span>{{ item.designation }}</span>
        </div>
      </Transition>

      <span
        class="animated-team-tooltip__avatar"
        tabindex="0"
        :aria-describedby="hoveredId === item.id ? `team-member-tooltip-${item.id}` : undefined"
        :aria-label="`${item.name}，${item.designation}`"
        data-testid="team-member-avatar"
      >
        {{ item.initial }}
      </span>
    </div>

    <div
      v-if="hiddenCount"
      class="animated-team-tooltip__item animated-team-tooltip__item--more"
      :style="{ '--member-index': visibleItems.length }"
      @mouseenter="updatePointer($event, 'more')"
      @mousemove="updatePointer($event, 'more')"
      @mouseleave="hideTooltip"
      @focusin="showFromKeyboard('more')"
      @focusout="hideTooltip"
    >
      <Transition name="member-tooltip">
        <div
          v-if="hoveredId === 'more'"
          id="team-member-tooltip-more"
          class="animated-team-tooltip__popup"
          :style="{
            '--tooltip-translate': tooltipTranslate,
            '--tooltip-rotation': tooltipRotation
          }"
          role="tooltip"
          data-testid="team-member-tooltip"
        >
          <strong>共 {{ resolvedTotal }} 人</strong>
          <span>还有 {{ hiddenCount }} 位成员</span>
        </div>
      </Transition>

      <span
        class="animated-team-tooltip__avatar animated-team-tooltip__avatar--more"
        tabindex="0"
        :aria-describedby="hoveredId === 'more' ? 'team-member-tooltip-more' : undefined"
        :aria-label="`还有 ${hiddenCount} 位成员，共 ${resolvedTotal} 人`"
        data-testid="team-member-avatar-more"
      >
        +{{ hiddenCount }}
      </span>
    </div>

    <span class="animated-team-tooltip__count">{{ resolvedTotal }}人</span>
  </div>
</template>

<style scoped>
.animated-team-tooltip {
  min-width: 0;
  display: flex;
  align-items: center;
  padding: 5px 0 3px;
}

.animated-team-tooltip__item {
  position: relative;
  z-index: calc(10 - var(--member-index));
  flex: 0 0 auto;
  margin-left: -8px;
}

.animated-team-tooltip__item:first-child {
  margin-left: 0;
}

.animated-team-tooltip__item:hover,
.animated-team-tooltip__item:focus-within {
  z-index: 30;
}

.animated-team-tooltip__avatar {
  position: relative;
  width: 30px;
  height: 30px;
  border: 2px solid #fff;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: #fff;
  background: var(--member-color, #293043);
  box-shadow:
    0 2px 8px rgba(18, 20, 26, 0.12),
    0 0 0 1px rgba(18, 20, 26, 0.04);
  cursor: default;
  font-size: 11px;
  font-weight: 800;
  line-height: 1;
  transition:
    transform 320ms cubic-bezier(0.22, 1, 0.36, 1),
    box-shadow 320ms ease;
}

.animated-team-tooltip__item:hover .animated-team-tooltip__avatar,
.animated-team-tooltip__item:focus-within .animated-team-tooltip__avatar {
  transform: translateY(-3px) scale(1.08);
  box-shadow:
    0 8px 18px rgba(18, 20, 26, 0.18),
    0 0 0 1px rgba(18, 20, 26, 0.05);
  outline: none;
}

.animated-team-tooltip__avatar:focus-visible {
  outline: 2px solid var(--ds-orange-action, #d93914);
  outline-offset: 3px;
}

.animated-team-tooltip__avatar--more {
  color: var(--ds-ink-soft, #535a68);
  background: #eef0f4;
  font-size: 10px;
}

.animated-team-tooltip__popup {
  position: absolute;
  left: 50%;
  bottom: calc(100% + 12px);
  z-index: 50;
  min-width: 112px;
  padding: 8px 11px 9px;
  border-radius: 9px;
  display: grid;
  gap: 2px;
  color: #fff;
  background: #17191f;
  box-shadow: 0 12px 28px rgba(18, 20, 26, 0.24);
  text-align: center;
  white-space: nowrap;
  transform:
    translateX(calc(-50% + var(--tooltip-translate, 0px)))
    rotate(var(--tooltip-rotation, 0deg));
  transform-origin: 50% 100%;
}

.animated-team-tooltip__popup::before,
.animated-team-tooltip__popup::after {
  content: '';
  position: absolute;
  bottom: -1px;
  width: 42%;
  height: 1px;
}

.animated-team-tooltip__popup::before {
  right: 50%;
  background: linear-gradient(90deg, transparent, #19a974);
}

.animated-team-tooltip__popup::after {
  left: 50%;
  background: linear-gradient(90deg, #3b82f6, transparent);
}

.animated-team-tooltip__popup strong {
  overflow: visible;
  color: #fff;
  font-size: 12px;
  font-weight: 800;
  line-height: 1.3;
}

.animated-team-tooltip__popup span {
  color: rgba(255, 255, 255, 0.72);
  font-size: 10px;
  font-weight: 600;
  line-height: 1.3;
}

.animated-team-tooltip__count {
  margin-left: 9px;
  color: var(--ds-muted, #737987);
  font-size: 11px;
  font-weight: 700;
  white-space: nowrap;
}

.member-tooltip-enter-active {
  animation: member-tooltip-in 380ms cubic-bezier(0.22, 1.25, 0.36, 1);
}

.member-tooltip-leave-active {
  transition:
    opacity 130ms ease,
    transform 130ms ease;
}

.member-tooltip-leave-to {
  opacity: 0;
  transform:
    translateX(calc(-50% + var(--tooltip-translate, 0px)))
    translateY(8px)
    rotate(var(--tooltip-rotation, 0deg))
    scale(0.82);
}

@keyframes member-tooltip-in {
  0% {
    opacity: 0;
    transform:
      translateX(calc(-50% + var(--tooltip-translate, 0px)))
      translateY(10px)
      rotate(var(--tooltip-rotation, 0deg))
      scale(0.72);
  }
  72% {
    opacity: 1;
    transform:
      translateX(calc(-50% + var(--tooltip-translate, 0px)))
      translateY(-2px)
      rotate(var(--tooltip-rotation, 0deg))
      scale(1.03);
  }
  100% {
    opacity: 1;
    transform:
      translateX(calc(-50% + var(--tooltip-translate, 0px)))
      rotate(var(--tooltip-rotation, 0deg))
      scale(1);
  }
}

@media (prefers-reduced-motion: reduce) {
  .animated-team-tooltip__avatar,
  .member-tooltip-enter-active,
  .member-tooltip-leave-active {
    animation: none;
    transition: none;
  }
}
</style>
