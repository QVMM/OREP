<template>
  <article
    class="resource-folder"
    :class="[
      `is-${folder.tone || 'custom'}`,
      {
        'is-drop-target': dropActive,
        'is-readonly': readonly,
        'is-public': folder.key === 'public'
      }
    ]"
    :aria-label="`${folder.label}，${folder.count || 0} 份资料${readonly ? '，只读' : ''}`"
    tabindex="0"
    @click="$emit('open', folder)"
    @keydown.enter.prevent="$emit('open', folder)"
    @keydown.space.prevent="$emit('open', folder)"
    @dragenter.prevent="onDragEnter"
    @dragover.prevent="onDragOver"
    @dragleave="onDragLeave"
    @drop.prevent="onDrop"
  >
    <div
      class="resource-folder__stage"
      :class="`has-${displayCovers.length}-covers`"
      aria-hidden="true"
    >
      <span class="resource-folder__back">
        <svg viewBox="0 0 96 72" role="presentation">
          <path d="M7 18.5c0-4.7 3.8-8.5 8.5-8.5h22.7l8 8H80.5c4.7 0 8.5 3.8 8.5 8.5v31C89 62.2 85.2 66 80.5 66h-65C10.8 66 7 62.2 7 57.5v-39Z" />
        </svg>
      </span>
      <span
        v-for="(cover, index) in displayCovers"
        :key="cover.id || `${folder.key}-${index}`"
        class="resource-folder__cover"
        :class="`is-layer-${index + 1}`"
      >
        <ResourceFileThumbnail :file="cover" />
      </span>
      <span class="resource-folder__front">
        <svg viewBox="0 0 96 72" role="presentation">
          <path d="M7 29h82v28.5c0 4.7-3.8 8.5-8.5 8.5h-65C10.8 66 7 62.2 7 57.5V29Z" />
        </svg>
      </span>
      <span v-if="dropActive" class="resource-folder__drop-copy">移动到这里</span>
    </div>

    <div class="resource-folder__copy">
      <span>
        <strong>{{ folder.label }}</strong>
        <small>{{ folder.count || 0 }} 份资料 · {{ readonly ? '公共只读' : '团队文件夹' }}</small>
      </span>
      <button
        v-if="folder.id && !readonly"
        type="button"
        aria-label="文件夹操作"
        title="文件夹操作"
        @click.stop="$emit('manage', folder)"
      >
        ···
      </button>
      <i v-else aria-hidden="true">›</i>
    </div>
  </article>
</template>

<script setup>
import { computed, ref } from 'vue'
import ResourceFileThumbnail from './ResourceFileThumbnail.vue'

const props = defineProps({
  folder: { type: Object, required: true },
  readonly: { type: Boolean, default: false },
  canDrop: { type: Boolean, default: false }
})

const emit = defineEmits(['open', 'drop-file', 'manage'])
const dragDepth = ref(0)
const dropActive = ref(false)

const displayCovers = computed(() => {
  return Array.isArray(props.folder?.covers) ? props.folder.covers.slice(0, 3) : []
})

function onDragEnter(event) {
  if (!props.canDrop || props.readonly) return
  dragDepth.value += 1
  dropActive.value = true
  event.dataTransfer.dropEffect = 'move'
}

function onDragOver(event) {
  if (!props.canDrop || props.readonly) return
  dropActive.value = true
  event.dataTransfer.dropEffect = 'move'
}

function onDragLeave() {
  if (!props.canDrop || props.readonly) return
  dragDepth.value = Math.max(0, dragDepth.value - 1)
  if (!dragDepth.value) dropActive.value = false
}

function onDrop() {
  if (!props.canDrop || props.readonly) return
  dragDepth.value = 0
  dropActive.value = false
  emit('drop-file', props.folder)
}
</script>

<style scoped>
.resource-folder {
  min-width: 0;
  display: grid;
  gap: 10px;
  padding: 14px 16px 15px;
  border: 1px solid var(--rc-border, #e7e9ee);
  border-radius: 18px;
  background: linear-gradient(145deg, #fff, #fbfbfc);
  box-shadow: 0 8px 24px rgba(28, 35, 48, 0.05);
  cursor: pointer;
  outline: none;
  transition:
    transform 180ms cubic-bezier(.2,.8,.2,1),
    border-color 180ms ease,
    box-shadow 180ms ease,
    background 180ms ease;
}

.resource-folder:hover,
.resource-folder:focus-visible {
  transform: translateY(-2px);
  border-color: rgba(240, 75, 35, 0.28);
  background: linear-gradient(145deg, #fff, #fff8f4);
  box-shadow: 0 14px 32px rgba(53, 35, 25, 0.09);
}

.resource-folder:focus-visible {
  box-shadow: 0 0 0 3px rgba(240, 75, 35, 0.14), 0 14px 32px rgba(53, 35, 25, 0.09);
}

.resource-folder.is-drop-target {
  transform: translateY(-3px) scale(1.012);
  border-color: var(--rc-accent, #ef4c23);
  background: #fff4ed;
  box-shadow: 0 16px 36px rgba(240, 75, 35, 0.16);
}

.resource-folder.is-readonly {
  background: linear-gradient(145deg, #fff, #f7f8fb);
}

.resource-folder__stage {
  --teaser-width: 60px;
  --teaser-height: 42px;
  --preview-width: 112px;
  --preview-height: 74px;
  position: relative;
  height: 124px;
  display: grid;
  place-items: end center;
  perspective: 760px;
}

.resource-folder__cover {
  position: absolute;
  left: 50%;
  bottom: 37px;
  width: var(--teaser-width);
  height: var(--teaser-height);
  overflow: hidden;
  border: 2px solid rgba(255,255,255,.96);
  border-radius: 9px;
  background: #fff;
  box-shadow:
    0 10px 24px rgba(34, 43, 57, .14),
    0 2px 6px rgba(34, 43, 57, .08);
  transform-origin: 50% 100%;
  transition:
    width 420ms cubic-bezier(.22,1,.36,1),
    height 420ms cubic-bezier(.22,1,.36,1),
    bottom 420ms cubic-bezier(.22,1,.36,1),
    transform 420ms cubic-bezier(.22,1,.36,1),
    box-shadow 260ms ease;
  will-change: width, height, transform;
}

.resource-folder__cover.is-layer-1 {
  z-index: 4;
  transform: translateX(-50%) translateY(-1px) rotate(-1deg);
}

.resource-folder__cover.is-layer-2 {
  z-index: 3;
  transform: translateX(-54%) translateY(1px) rotate(-3deg);
}

.resource-folder__cover.is-layer-3 {
  z-index: 2;
  transform: translateX(-46%) translateY(2px) rotate(3deg);
}

.resource-folder:hover .resource-folder__cover,
.resource-folder:focus-visible .resource-folder__cover {
  bottom: 35px;
  width: var(--preview-width);
  height: var(--preview-height);
  box-shadow:
    0 14px 30px rgba(34, 43, 57, .16),
    0 3px 8px rgba(34, 43, 57, .09);
}

.resource-folder:hover .resource-folder__cover.is-layer-1,
.resource-folder:focus-visible .resource-folder__cover.is-layer-1 {
  transform: translateX(-50%) translateY(-20px) rotate(-1deg);
}

.resource-folder:hover .resource-folder__cover.is-layer-2,
.resource-folder:focus-visible .resource-folder__cover.is-layer-2 {
  transform: translateX(-86%) translateY(-11px) rotate(-11deg);
}

.resource-folder:hover .resource-folder__cover.is-layer-3,
.resource-folder:focus-visible .resource-folder__cover.is-layer-3 {
  transform: translateX(-14%) translateY(-10px) rotate(11deg);
}

.resource-folder__stage.has-1-covers .resource-folder__cover.is-layer-1 {
  transform: translateX(-50%) translateY(-1px) rotate(-2deg);
}

.resource-folder:hover .resource-folder__stage.has-1-covers .resource-folder__cover.is-layer-1,
.resource-folder:focus-visible .resource-folder__stage.has-1-covers .resource-folder__cover.is-layer-1 {
  transform: translateX(-50%) translateY(-18px) rotate(-2deg);
}

.resource-folder__stage.has-2-covers .resource-folder__cover.is-layer-1 {
  transform: translateX(-47%) translateY(-1px) rotate(2deg);
}

.resource-folder__stage.has-2-covers .resource-folder__cover.is-layer-2 {
  transform: translateX(-53%) translateY(1px) rotate(-3deg);
}

.resource-folder:hover .resource-folder__stage.has-2-covers .resource-folder__cover.is-layer-1,
.resource-folder:focus-visible .resource-folder__stage.has-2-covers .resource-folder__cover.is-layer-1 {
  transform: translateX(-31%) translateY(-17px) rotate(8deg);
}

.resource-folder:hover .resource-folder__stage.has-2-covers .resource-folder__cover.is-layer-2,
.resource-folder:focus-visible .resource-folder__stage.has-2-covers .resource-folder__cover.is-layer-2 {
  transform: translateX(-69%) translateY(-12px) rotate(-9deg);
}

.resource-folder__back,
.resource-folder__front {
  position: absolute;
  left: 50%;
  bottom: 4px;
  width: 84px;
  height: 63px;
  transform: translateX(-50%);
}

.resource-folder__back {
  z-index: 1;
  filter: drop-shadow(0 8px 9px rgba(118, 73, 46, .1));
}

.resource-folder__front {
  z-index: 5;
  filter: drop-shadow(0 9px 10px rgba(118, 73, 46, .14));
  transform-origin: 50% 100%;
  transition:
    transform 460ms cubic-bezier(.22,1,.36,1),
    filter 340ms ease;
  will-change: transform;
}

.resource-folder__front::after {
  content: "";
  position: absolute;
  z-index: 2;
  left: 50%;
  bottom: 12px;
  width: 42px;
  height: 2px;
  border-radius: 999px;
  background: rgba(255, 255, 255, .38);
  box-shadow: 0 1px 0 rgba(125, 72, 43, .05);
  transform: translateX(-50%);
}

.resource-folder__back svg,
.resource-folder__front svg {
  width: 100%;
  height: 100%;
}

.resource-folder__back path {
  fill: #ffd9bd;
}

.resource-folder__front path {
  fill: #ffb77f;
  transition: fill 340ms ease;
}

.resource-folder.is-research .resource-folder__back path,
.resource-folder.is-custom .resource-folder__back path {
  fill: #dce7ff;
}

.resource-folder.is-research .resource-folder__front path,
.resource-folder.is-custom .resource-folder__front path {
  fill: #9db9f5;
}

.resource-folder.is-public .resource-folder__back path {
  fill: #e9ecf2;
}

.resource-folder.is-public .resource-folder__front path {
  fill: #aeb6c5;
}

.resource-folder.is-public .resource-folder__front {
  filter: drop-shadow(0 10px 11px rgba(75, 84, 101, .18));
}

.resource-folder.is-public .resource-folder__front::after {
  background: rgba(255, 255, 255, .5);
}

.resource-folder:hover .resource-folder__front,
.resource-folder:focus-visible .resource-folder__front {
  filter: drop-shadow(0 13px 13px rgba(118, 73, 46, .11));
  transform: translateX(-50%) translateY(7px) rotateX(-18deg);
}

.resource-folder.is-public:hover .resource-folder__front,
.resource-folder.is-public:focus-visible .resource-folder__front {
  filter: drop-shadow(0 16px 14px rgba(75, 84, 101, .23));
  transform: translateX(-50%) translateY(9px) rotateX(-23deg);
}

.resource-folder.is-public:hover .resource-folder__front path,
.resource-folder.is-public:focus-visible .resource-folder__front path {
  fill: #9da7b8;
}

.resource-folder__drop-copy {
  position: absolute;
  z-index: 8;
  inset: auto 14px 16px;
  min-height: 32px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  background: rgba(239, 76, 35, .94);
  color: #fff;
  font-size: 12px;
  font-weight: 850;
  box-shadow: 0 8px 18px rgba(239, 76, 35, .24);
}

.resource-folder__copy {
  min-width: 0;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
}

.resource-folder__copy span,
.resource-folder__copy strong,
.resource-folder__copy small {
  min-width: 0;
  display: block;
}

.resource-folder__copy strong {
  overflow: hidden;
  color: #222832;
  font-size: 13px;
  font-weight: 820;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.resource-folder__copy small {
  margin-top: 4px;
  color: #858c98;
  font-size: 11px;
}

.resource-folder__copy button {
  width: 30px;
  height: 30px;
  border: 0;
  border-radius: 9px;
  background: transparent;
  color: #8b919c;
  cursor: pointer;
  font-weight: 900;
}

.resource-folder__copy button:hover {
  background: #f0f2f5;
  color: #343944;
}

.resource-folder__copy > i {
  color: #a7adb7;
  font-size: 20px;
  font-style: normal;
}

@media (prefers-reduced-motion: reduce) {
  .resource-folder,
  .resource-folder__cover,
  .resource-folder__back,
  .resource-folder__front {
    transition-duration: 1ms;
  }

  .resource-folder:hover,
  .resource-folder:focus-visible,
  .resource-folder.is-drop-target {
    transform: none;
  }

  .resource-folder:hover .resource-folder__front,
  .resource-folder:focus-visible .resource-folder__front {
    filter: drop-shadow(0 9px 10px rgba(118, 73, 46, .14));
    transform: translateX(-50%);
  }

  .resource-folder.is-public:hover .resource-folder__front,
  .resource-folder.is-public:focus-visible .resource-folder__front {
    filter: drop-shadow(0 10px 11px rgba(75, 84, 101, .18));
    transform: translateX(-50%);
  }

  .resource-folder:hover .resource-folder__cover,
  .resource-folder:focus-visible .resource-folder__cover {
    bottom: 37px;
    width: var(--teaser-width);
    height: var(--teaser-height);
  }

  .resource-folder:hover .resource-folder__cover.is-layer-1,
  .resource-folder:focus-visible .resource-folder__cover.is-layer-1 {
    transform: translateX(-50%) translateY(-1px) rotate(-1deg);
  }

  .resource-folder:hover .resource-folder__cover.is-layer-2,
  .resource-folder:focus-visible .resource-folder__cover.is-layer-2 {
    transform: translateX(-54%) translateY(1px) rotate(-3deg);
  }

  .resource-folder:hover .resource-folder__cover.is-layer-3,
  .resource-folder:focus-visible .resource-folder__cover.is-layer-3 {
    transform: translateX(-46%) translateY(2px) rotate(3deg);
  }

  .resource-folder:hover .resource-folder__stage.has-1-covers .resource-folder__cover.is-layer-1,
  .resource-folder:focus-visible .resource-folder__stage.has-1-covers .resource-folder__cover.is-layer-1 {
    transform: translateX(-50%) translateY(-1px) rotate(-2deg);
  }

  .resource-folder:hover .resource-folder__stage.has-2-covers .resource-folder__cover.is-layer-1,
  .resource-folder:focus-visible .resource-folder__stage.has-2-covers .resource-folder__cover.is-layer-1 {
    transform: translateX(-47%) translateY(-1px) rotate(2deg);
  }

  .resource-folder:hover .resource-folder__stage.has-2-covers .resource-folder__cover.is-layer-2,
  .resource-folder:focus-visible .resource-folder__stage.has-2-covers .resource-folder__cover.is-layer-2 {
    transform: translateX(-53%) translateY(1px) rotate(-3deg);
  }
}
</style>
