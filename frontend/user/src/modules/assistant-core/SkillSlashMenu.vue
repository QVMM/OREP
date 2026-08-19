<template>
  <Teleport to="body">
    <div
      v-if="open && items.length"
      ref="rootEl"
      class="skill-slash-menu skill-slash-menu--fixed"
      role="listbox"
      :aria-label="ariaLabel"
      :style="panelStyle"
      @mousedown.prevent
    >
      <div class="skill-slash-menu__head">
        <span class="skill-slash-menu__title">技能</span>
        <span class="skill-slash-menu__hint">↑↓ 选择 · Enter 填入 · Esc 关闭</span>
      </div>
      <button
        v-for="(skill, index) in items"
        :key="skill.name"
        type="button"
        role="option"
        class="skill-slash-menu__item"
        :class="{ 'is-active': index === activeIndex }"
        :aria-selected="index === activeIndex"
        @mouseenter="activeIndex = index"
        @click="emitPick(skill)"
      >
        <span class="skill-slash-menu__slash">/{{ skill.slash }}</span>
        <span class="skill-slash-menu__desc">{{ skill.description }}</span>
      </button>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'

const props = defineProps({
  open: { type: Boolean, default: false },
  items: { type: Array, default: () => [] },
  /** 对齐锚点：composer box 或 textarea */
  anchorEl: { type: Object, default: null },
  ariaLabel: { type: String, default: '技能列表' },
})

const emit = defineEmits(['pick', 'close'])

const activeIndex = ref(0)
const rootEl = ref(null)
const coords = ref({ top: 0, left: 0, width: 320, maxHeight: 280, place: 'above' })

const panelStyle = computed(() => {
  const c = coords.value
  const style = {
    left: `${c.left}px`,
    width: `${c.width}px`,
    maxHeight: `${c.maxHeight}px`,
  }
  if (c.place === 'below') {
    style.top = `${c.top}px`
    style.bottom = 'auto'
  } else {
    style.bottom = `${window.innerHeight - c.top}px`
    style.top = 'auto'
  }
  return style
})

watch(
  () => [props.open, props.items, props.anchorEl],
  async () => {
    activeIndex.value = 0
    if (props.open) {
      await nextTick()
      updatePosition()
    }
  },
  { deep: true },
)

function updatePosition() {
  const el = props.anchorEl
  if (!el || typeof el.getBoundingClientRect !== 'function') return
  const rect = el.getBoundingClientRect()
  // 锚点已不可见（半栏收起/display:none）：不要留浮层
  if (rect.width < 2 && rect.height < 2) {
    emit('close')
    return
  }
  const gap = 8
  const preferredHeight = Math.min(280, window.innerHeight * 0.42)
  const spaceAbove = rect.top - gap
  const spaceBelow = window.innerHeight - rect.bottom - gap
  const placeAbove = spaceAbove >= 160 || spaceAbove >= spaceBelow
  const maxHeight = Math.max(140, Math.min(preferredHeight, placeAbove ? spaceAbove : spaceBelow))
  const width = Math.min(Math.max(rect.width, 280), Math.min(420, window.innerWidth - 16))
  let left = rect.left
  if (left + width > window.innerWidth - 8) left = window.innerWidth - width - 8
  if (left < 8) left = 8

  if (placeAbove) {
    coords.value = {
      top: rect.top - gap,
      left,
      width,
      maxHeight,
      place: 'above',
    }
  } else {
    coords.value = {
      top: rect.bottom + gap,
      left,
      width,
      maxHeight,
      place: 'below',
    }
  }
}

function onWin() {
  if (props.open) updatePosition()
}

function onDocPointerDown(e) {
  if (!props.open) return
  const root = rootEl.value
  if (root && root.contains(e.target)) return
  // 点在输入框/工具栏 / 按钮内：不关
  const anchor = props.anchorEl
  if (anchor && typeof anchor.contains === 'function' && anchor.contains(e.target)) return
  emit('close')
}

function onDocKeydown(e) {
  if (!props.open) return
  if (e.key === 'Escape') {
    e.preventDefault()
    emit('close')
  }
}

if (typeof window !== 'undefined') {
  window.addEventListener('resize', onWin)
  window.addEventListener('scroll', onWin, true)
  document.addEventListener('pointerdown', onDocPointerDown, true)
  document.addEventListener('keydown', onDocKeydown, true)
}

onBeforeUnmount(() => {
  if (typeof window !== 'undefined') {
    window.removeEventListener('resize', onWin)
    window.removeEventListener('scroll', onWin, true)
    document.removeEventListener('pointerdown', onDocPointerDown, true)
    document.removeEventListener('keydown', onDocKeydown, true)
  }
})

function emitPick(skill) {
  emit('pick', skill)
}

function move(delta) {
  const n = props.items.length
  if (!n) return
  activeIndex.value = (activeIndex.value + delta + n) % n
}

function pickActive() {
  const skill = props.items[activeIndex.value]
  if (skill) emitPick(skill)
  return !!skill
}

defineExpose({ move, pickActive, activeIndex, updatePosition })
</script>
