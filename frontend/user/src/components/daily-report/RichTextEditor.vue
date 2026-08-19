<template>
  <div class="rte" :class="{ 'is-focus': focused, 'is-disabled': disabled }">
    <div class="rte__toolbar" role="toolbar" :aria-label="label || '富文本工具栏'">
      <button type="button" title="加粗" :disabled="disabled" @mousedown.prevent @click="cmd('bold')"><b>B</b></button>
      <button type="button" title="斜体" :disabled="disabled" @mousedown.prevent @click="cmd('italic')"><i>I</i></button>
      <button type="button" title="无序列表" :disabled="disabled" @mousedown.prevent @click="cmd('insertUnorderedList')">• 列表</button>
      <button type="button" title="有序列表" :disabled="disabled" @mousedown.prevent @click="cmd('insertOrderedList')">1. 列表</button>
      <button type="button" title="插入链接" :disabled="disabled" @mousedown.prevent @click="insertLink">链接</button>
      <button type="button" title="插入图片" :disabled="disabled || uploading" @mousedown.prevent @click="pickImage">
        {{ uploading ? '上传中…' : '图片' }}
      </button>
      <button type="button" title="清除格式" :disabled="disabled" @mousedown.prevent @click="cmd('removeFormat')">清除</button>
    </div>
    <div
      ref="editorRef"
      class="rte__body"
      :contenteditable="disabled ? 'false' : 'true'"
      role="textbox"
      aria-multiline="true"
      :aria-label="label || '编辑区'"
      :data-placeholder="placeholder"
      @input="onInput"
      @focus="focused = true"
      @blur="onBlur"
      @paste="onPaste"
      @dragover.prevent
      @drop.prevent="onDropImage"
    />
    <input
      ref="fileRef"
      type="file"
      accept="image/png,image/jpeg,image/gif,image/webp"
      class="rte__file"
      @change="onFile"
    />
    <p v-if="uploadError" class="rte__error">{{ uploadError }}</p>
  </div>
</template>

<script setup>
import { nextTick, onMounted, ref, watch } from 'vue'
import request from '../../utils/request'

const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '' },
  label: { type: String, default: '' },
  disabled: { type: Boolean, default: false },
})

const emit = defineEmits(['update:modelValue'])

const editorRef = ref(null)
const fileRef = ref(null)
const focused = ref(false)
const uploading = ref(false)
const uploadError = ref('')
let lastEmitted = ''
let syncing = false

onMounted(() => {
  setHtml(props.modelValue)
})

watch(() => props.modelValue, (v) => {
  if (v === lastEmitted) return
  if (focused.value) return
  setHtml(v)
})

function setHtml(html) {
  if (!editorRef.value) return
  syncing = true
  const next = html || ''
  if (editorRef.value.innerHTML !== next) {
    editorRef.value.innerHTML = next
  }
  lastEmitted = next
  nextTick(() => { syncing = false })
}

function onInput() {
  if (syncing) return
  const html = normalizeEmpty(editorRef.value?.innerHTML || '')
  lastEmitted = html
  emit('update:modelValue', html)
}

function onBlur() {
  focused.value = false
  onInput()
}

function normalizeEmpty(html) {
  const plain = html
    .replace(/<br\s*\/?>/gi, '')
    .replace(/&nbsp;/gi, ' ')
    .replace(/<p>\s*<\/p>/gi, '')
    .replace(/<div>\s*<\/div>/gi, '')
    .replace(/\s+/g, '')
  if (!plain) return ''
  return html
}

function cmd(name, value = null) {
  if (props.disabled) return
  editorRef.value?.focus()
  document.execCommand(name, false, value)
  onInput()
}

function insertLink() {
  if (props.disabled) return
  const url = window.prompt('输入链接地址（https://…）')
  if (!url) return
  cmd('createLink', url.trim())
}

function pickImage() {
  if (props.disabled || uploading.value) return
  uploadError.value = ''
  fileRef.value?.click()
}

async function uploadImageFile(file) {
  if (!file) return
  if (!file.type.startsWith('image/')) {
    uploadError.value = '请选择图片文件'
    return
  }
  if (file.size > 8 * 1024 * 1024) {
    uploadError.value = '图片请小于 8MB'
    return
  }
  uploading.value = true
  uploadError.value = ''
  try {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('category', 'daily-report')
    const res = await request.post('/api/upload', formData, { timeout: 60000 })
    // 拦截器返回 { code, data }，上传结果在 data 内
    const data = res?.data || {}
    const url = data.url
    if (!url) throw new Error(res?.message || '上传失败')
    editorRef.value?.focus()
    document.execCommand('insertImage', false, url)
    // 给图片加一点样式类
    const imgs = editorRef.value?.querySelectorAll(`img[src="${url}"]`)
    imgs?.forEach((img) => {
      img.setAttribute('style', 'max-width:100%;height:auto;border-radius:10px;margin:8px 0;')
      img.setAttribute('alt', file.name || '图片')
    })
    onInput()
  } catch (err) {
    uploadError.value = err?.message || '图片上传失败'
  } finally {
    uploading.value = false
  }
}

async function onFile(e) {
  const file = e.target?.files?.[0]
  if (e.target) e.target.value = ''
  await uploadImageFile(file)
}

function onDropImage(e) {
  if (props.disabled || uploading.value) return
  const file = Array.from(e.dataTransfer?.files || []).find((f) => f.type.startsWith('image/'))
  if (file) uploadImageFile(file)
}

function onPaste(e) {
  // 允许粘贴图片文件
  const items = e.clipboardData?.items
  if (!items) return
  for (const item of items) {
    if (item.type.startsWith('image/')) {
      e.preventDefault()
      const file = item.getAsFile()
      if (file) {
        const dt = new DataTransfer()
        dt.items.add(file)
        // 复用上传逻辑
        const fake = { target: { files: dt.files, value: '' } }
        onFile(fake)
      }
      return
    }
  }
}
</script>

<style scoped>
.rte {
  border: 1px solid var(--ds-line, #e5e7eb);
  border-radius: 12px;
  background: #fff;
  overflow: hidden;
  transition: border-color 120ms ease, box-shadow 120ms ease;
}

.rte.is-focus {
  border-color: color-mix(in srgb, var(--ds-orange-400, #fb923c) 55%, var(--ds-line));
  box-shadow: 0 0 0 3px rgba(249, 115, 22, 0.12);
}

.rte.is-disabled {
  opacity: 0.72;
  background: #f8fafc;
}

.rte__toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  padding: 8px 10px;
  border-bottom: 1px solid var(--ds-line, #eceff3);
  background: #fafbfc;
}

.rte__toolbar button {
  height: 30px;
  padding: 0 10px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--ds-ink-2, #374151);
  font: inherit;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.rte__toolbar button:hover:not(:disabled) {
  background: #eef2f7;
}

.rte__toolbar button:disabled {
  opacity: 0.5;
  cursor: default;
}

.rte__body {
  min-height: 140px;
  max-height: 420px;
  overflow: auto;
  padding: 12px 14px;
  font-size: 14px;
  line-height: 1.65;
  outline: none;
  word-break: break-word;
}

.rte__body:empty::before {
  content: attr(data-placeholder);
  color: #9ca3af;
  pointer-events: none;
}

.rte__body :deep(img) {
  max-width: 100%;
  height: auto;
  border-radius: 10px;
  display: block;
  margin: 8px 0;
}

.rte__body :deep(ul),
.rte__body :deep(ol) {
  margin: 0.4em 0;
  padding-left: 1.4em;
}

.rte__body :deep(a) {
  color: var(--ds-orange-700, #c2410c);
}

.rte__file {
  display: none;
}

.rte__error {
  margin: 0;
  padding: 6px 12px 10px;
  color: #b91c1c;
  font-size: 12px;
}
</style>
