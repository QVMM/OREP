<template>
  <div
    class="drop-file-upload"
    :class="[
      `is-${size}`,
      {
        'is-dragging': dragging,
        'is-disabled': disabled,
        'has-files': files.length > 0,
        'is-invalid': invalid,
      },
    ]"
    role="button"
    :tabindex="disabled ? -1 : 0"
    :aria-disabled="disabled ? 'true' : 'false'"
    :aria-label="ariaLabel"
    @click="openPicker"
    @keydown.enter.prevent="openPicker"
    @keydown.space.prevent="openPicker"
    @dragenter.prevent="onDragEnter"
    @dragover.prevent="onDragOver"
    @dragleave.prevent="onDragLeave"
    @drop.prevent="onDrop"
  >
    <div class="drop-file-upload__grid" aria-hidden="true" />
    <div class="drop-file-upload__shine" aria-hidden="true" />

    <input
      ref="inputEl"
      class="drop-file-upload__input"
      type="file"
      :accept="accept || undefined"
      :multiple="multiple"
      :disabled="disabled"
      @change="onInputChange"
      @click.stop
    />

    <div class="drop-file-upload__body">
      <div class="drop-file-upload__icon" aria-hidden="true">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round">
          <path d="M12 16V5" />
          <path d="M8.5 8.5 12 5l3.5 3.5" />
          <path d="M5 16.5v1A2.5 2.5 0 0 0 7.5 20h9a2.5 2.5 0 0 0 2.5-2.5v-1" />
        </svg>
      </div>

      <div class="drop-file-upload__copy">
        <strong>{{ headingText }}</strong>
        <p>{{ hintText }}</p>
        <span v-if="acceptHint" class="drop-file-upload__accept">{{ acceptHint }}</span>
      </div>

      <button
        type="button"
        class="drop-file-upload__browse"
        :disabled="disabled"
        @click.stop="openPicker"
      >
        选择文件
      </button>
    </div>

    <ul v-if="files.length" class="drop-file-upload__list" @click.stop>
      <li v-for="(file, index) in files" :key="fileKey(file, index)">
        <span class="drop-file-upload__badge" aria-hidden="true">{{ extOf(file) }}</span>
        <div class="drop-file-upload__meta">
          <strong :title="file.name">{{ file.name }}</strong>
          <small>{{ formatSize(file.size) }}</small>
        </div>
        <button
          type="button"
          class="drop-file-upload__remove"
          :disabled="disabled"
          :aria-label="`移除 ${file.name}`"
          @click="removeAt(index)"
        >
          ×
        </button>
      </li>
    </ul>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  /** v-model: File | File[] | null */
  modelValue: {
    type: [Object, Array, File],
    default: null,
  },
  multiple: { type: Boolean, default: false },
  accept: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
  /** sm | md | lg */
  size: { type: String, default: 'md' },
  title: { type: String, default: '' },
  hint: { type: String, default: '' },
  acceptHint: { type: String, default: '' },
  maxFiles: { type: Number, default: 20 },
  maxSizeMb: { type: Number, default: 0 },
  invalid: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue', 'change', 'error'])

const inputEl = ref(null)
const dragging = ref(false)
let dragDepth = 0

const files = computed(() => normalizeFiles(props.modelValue))

const headingText = computed(() => {
  if (props.title) return props.title
  if (files.value.length) {
    return props.multiple ? `已选择 ${files.value.length} 个文件` : files.value[0].name
  }
  return props.multiple ? '拖拽文件到此处，或点击选择' : '拖拽文件到此处，或点击选择'
})

const hintText = computed(() => {
  if (props.hint) return props.hint
  if (files.value.length && !props.multiple) {
    return formatSize(files.value[0].size)
  }
  return props.multiple ? '支持多选 · 松开鼠标即可添加' : '松开鼠标即可添加 · 也可点击选择'
})

const ariaLabel = computed(() => (props.multiple ? '拖拽或选择多个文件上传' : '拖拽或选择文件上传'))

watch(
  () => props.modelValue,
  () => {
    // keep native input in sync when cleared externally
    if (!files.value.length && inputEl.value) inputEl.value.value = ''
  }
)

function normalizeFiles(value) {
  if (!value) return []
  if (Array.isArray(value)) return value.filter(Boolean)
  if (value instanceof File) return [value]
  return []
}

function fileKey(file, index) {
  return `${file.name}-${file.size}-${file.lastModified || 0}-${index}`
}

function extOf(file) {
  const name = file?.name || ''
  const i = name.lastIndexOf('.')
  const ext = i >= 0 ? name.slice(i + 1) : ''
  return (ext || 'FILE').slice(0, 4).toUpperCase()
}

function formatSize(bytes) {
  const n = Number(bytes) || 0
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  if (n < 1024 * 1024 * 1024) return `${(n / (1024 * 1024)).toFixed(1)} MB`
  return `${(n / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

function openPicker() {
  if (props.disabled) return
  inputEl.value?.click()
}

function onDragEnter() {
  if (props.disabled) return
  dragDepth += 1
  dragging.value = true
}

function onDragOver(event) {
  if (props.disabled) return
  dragging.value = true
  if (event.dataTransfer) event.dataTransfer.dropEffect = 'copy'
}

function onDragLeave() {
  dragDepth = Math.max(0, dragDepth - 1)
  if (!dragDepth) dragging.value = false
}

function onDrop(event) {
  if (props.disabled) return
  dragDepth = 0
  dragging.value = false
  const list = event.dataTransfer?.files
  if (list?.length) applyFileList(list)
}

function onInputChange(event) {
  const list = event.target.files
  if (list?.length) applyFileList(list)
  // allow re-selecting same file
  event.target.value = ''
}

function acceptMatches(file) {
  const accept = (props.accept || '').trim()
  if (!accept) return true
  const name = (file.name || '').toLowerCase()
  const type = (file.type || '').toLowerCase()
  const tokens = accept.split(',').map((t) => t.trim().toLowerCase()).filter(Boolean)
  return tokens.some((token) => {
    if (token.startsWith('.')) return name.endsWith(token)
    if (token.endsWith('/*')) {
      const prefix = token.slice(0, -1)
      return type.startsWith(prefix)
    }
    return type === token || name.endsWith(`.${token}`)
  })
}

function applyFileList(fileList) {
  let next = Array.from(fileList || [])
  if (!next.length) return

  const rejectedType = next.filter((f) => !acceptMatches(f))
  if (rejectedType.length) {
    emit('error', { code: 'accept', message: '文件类型不符合要求', files: rejectedType })
    next = next.filter((f) => acceptMatches(f))
  }

  if (props.maxSizeMb > 0) {
    const maxBytes = props.maxSizeMb * 1024 * 1024
    const rejectedSize = next.filter((f) => f.size > maxBytes)
    if (rejectedSize.length) {
      emit('error', {
        code: 'size',
        message: `单个文件不能超过 ${props.maxSizeMb}MB`,
        files: rejectedSize,
      })
      next = next.filter((f) => f.size <= maxBytes)
    }
  }

  if (!next.length) return

  if (props.multiple) {
    const merged = [...files.value]
    for (const file of next) {
      const dup = merged.some(
        (x) => x.name === file.name && x.size === file.size && x.lastModified === file.lastModified
      )
      if (!dup) merged.push(file)
    }
    const limited = merged.slice(0, Math.max(1, props.maxFiles || 20))
    if (merged.length > limited.length) {
      emit('error', { code: 'count', message: `最多选择 ${props.maxFiles} 个文件` })
    }
    emitValue(limited)
  } else {
    emitValue(next[0])
  }
}

function emitValue(value) {
  emit('update:modelValue', value)
  emit('change', value)
}

function removeAt(index) {
  if (props.disabled) return
  if (props.multiple) {
    const next = files.value.filter((_, i) => i !== index)
    emitValue(next.length ? next : [])
  } else {
    emitValue(null)
  }
}
</script>

<style scoped>
.drop-file-upload {
  --dfu-border: color-mix(in srgb, var(--ds-border, #e5e7eb) 88%, #cbd5e1);
  --dfu-bg: #fafbfc;
  --dfu-ink: var(--ds-ink, #111827);
  --dfu-muted: var(--ds-muted, #6b7280);
  --dfu-accent: var(--ds-orange, #e5481d);
  --dfu-accent-soft: color-mix(in srgb, var(--dfu-accent) 12%, #fff);
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 12px;
  width: 100%;
  min-height: 148px;
  padding: 18px 16px;
  border: 1.5px dashed var(--dfu-border);
  border-radius: 16px;
  background:
    linear-gradient(165deg, rgba(255, 255, 255, 0.96), rgba(248, 250, 252, 0.92)),
    var(--dfu-bg);
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.85) inset,
    0 10px 28px rgba(15, 23, 42, 0.05);
  color: var(--dfu-ink);
  cursor: pointer;
  overflow: hidden;
  transition:
    border-color 0.18s ease,
    box-shadow 0.18s ease,
    transform 0.18s ease,
    background 0.18s ease;
  outline: none;
  user-select: none;
  box-sizing: border-box;
}

.drop-file-upload.is-sm {
  min-height: 112px;
  padding: 12px;
  border-radius: 12px;
  gap: 8px;
}

.drop-file-upload.is-lg {
  min-height: 180px;
  padding: 22px 18px;
}

.drop-file-upload:hover:not(.is-disabled),
.drop-file-upload:focus-visible:not(.is-disabled) {
  border-color: color-mix(in srgb, var(--dfu-accent) 55%, var(--dfu-border));
  box-shadow:
    0 1px 0 rgba(255, 255, 255, 0.9) inset,
    0 14px 32px rgba(15, 23, 42, 0.08);
  transform: translateY(-1px);
}

.drop-file-upload.is-dragging {
  border-style: solid;
  border-color: var(--dfu-accent);
  background: linear-gradient(165deg, #fff, var(--dfu-accent-soft));
  box-shadow:
    0 0 0 4px color-mix(in srgb, var(--dfu-accent) 14%, transparent),
    0 16px 36px rgba(15, 23, 42, 0.1);
  transform: scale(1.01);
}

.drop-file-upload.has-files {
  border-style: solid;
  border-color: color-mix(in srgb, var(--dfu-accent) 28%, var(--dfu-border));
}

.drop-file-upload.is-invalid {
  border-color: #ef4444;
  box-shadow: 0 0 0 3px rgba(239, 68, 68, 0.12);
}

.drop-file-upload.is-disabled {
  opacity: 0.58;
  cursor: not-allowed;
  transform: none !important;
  box-shadow: none;
}

.drop-file-upload__grid {
  pointer-events: none;
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(to right, rgba(148, 163, 184, 0.09) 1px, transparent 1px),
    linear-gradient(to bottom, rgba(148, 163, 184, 0.09) 1px, transparent 1px);
  background-size: 18px 18px;
  mask-image: radial-gradient(ellipse 80% 70% at 50% 40%, #000 20%, transparent 75%);
  opacity: 0.9;
}

.drop-file-upload__shine {
  pointer-events: none;
  position: absolute;
  inset: auto -20% 35% -20%;
  height: 55%;
  background: radial-gradient(ellipse at center, rgba(255, 255, 255, 0.75), transparent 68%);
  opacity: 0.7;
}

.drop-file-upload__input {
  position: absolute;
  width: 1px;
  height: 1px;
  opacity: 0;
  pointer-events: none;
}

.drop-file-upload__body {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  text-align: center;
  min-height: 96px;
}

.drop-file-upload.is-sm .drop-file-upload__body {
  min-height: 72px;
  gap: 6px;
}

.drop-file-upload__icon {
  width: 44px;
  height: 44px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  color: var(--dfu-accent);
  background: linear-gradient(180deg, #fff, var(--dfu-accent-soft));
  border: 1px solid color-mix(in srgb, var(--dfu-accent) 18%, #fff);
  box-shadow: 0 8px 16px color-mix(in srgb, var(--dfu-accent) 12%, transparent);
}

.drop-file-upload.is-sm .drop-file-upload__icon {
  width: 36px;
  height: 36px;
  border-radius: 11px;
}

.drop-file-upload__icon svg {
  width: 22px;
  height: 22px;
}

.drop-file-upload.is-sm .drop-file-upload__icon svg {
  width: 18px;
  height: 18px;
}

.drop-file-upload__copy {
  display: grid;
  gap: 4px;
  max-width: 36rem;
}

.drop-file-upload__copy strong {
  font-size: 14px;
  font-weight: 700;
  line-height: 1.35;
  word-break: break-word;
}

.drop-file-upload.is-sm .drop-file-upload__copy strong {
  font-size: 13px;
}

.drop-file-upload__copy p {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
  color: var(--dfu-muted);
}

.drop-file-upload__accept {
  font-size: 11px;
  color: color-mix(in srgb, var(--dfu-muted) 85%, #94a3b8);
}

.drop-file-upload__browse {
  appearance: none;
  border: 1px solid color-mix(in srgb, var(--dfu-accent) 35%, #e5e7eb);
  background: #fff;
  color: var(--dfu-accent);
  border-radius: 999px;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.15s ease, border-color 0.15s ease;
}

.drop-file-upload__browse:hover:not(:disabled) {
  background: var(--dfu-accent-soft);
  border-color: var(--dfu-accent);
}

.drop-file-upload__browse:disabled {
  cursor: not-allowed;
}

.drop-file-upload__list {
  position: relative;
  z-index: 1;
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 8px;
  width: 100%;
}

.drop-file-upload__list li {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid color-mix(in srgb, var(--dfu-border) 90%, #cbd5e1);
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.04);
}

.drop-file-upload__badge {
  flex: 0 0 auto;
  min-width: 38px;
  height: 28px;
  padding: 0 6px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.02em;
  color: #fff;
  background: linear-gradient(135deg, #f97316, #e5481d);
}

.drop-file-upload__meta {
  min-width: 0;
  flex: 1;
  display: grid;
  gap: 2px;
}

.drop-file-upload__meta strong {
  font-size: 12px;
  font-weight: 650;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.drop-file-upload__meta small {
  font-size: 11px;
  color: var(--dfu-muted);
}

.drop-file-upload__remove {
  flex: 0 0 auto;
  width: 28px;
  height: 28px;
  border: 0;
  border-radius: 8px;
  background: #f3f4f6;
  color: #6b7280;
  font-size: 16px;
  line-height: 1;
  cursor: pointer;
}

.drop-file-upload__remove:hover:not(:disabled) {
  background: #fee2e2;
  color: #b91c1c;
}

.drop-file-upload__remove:disabled {
  cursor: not-allowed;
}

@media (max-width: 640px) {
  .drop-file-upload {
    min-height: 132px;
  }
}
</style>
