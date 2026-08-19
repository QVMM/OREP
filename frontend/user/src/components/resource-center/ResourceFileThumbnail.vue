<template>
  <span
    ref="rootRef"
    class="resource-file-thumbnail"
    :class="[`is-${kind}`, { 'is-loading': loading, 'has-image': Boolean(thumbnailUrl) }]"
  >
    <img
      v-if="thumbnailUrl"
      :src="thumbnailUrl"
      :alt="file.name || '文件缩略图'"
      loading="lazy"
      @error="showFallback"
    />
    <span v-else-if="loading" class="resource-file-thumbnail__skeleton" aria-hidden="true">
      <i></i>
      <i></i>
      <i></i>
      <i></i>
    </span>
    <span v-else class="resource-file-thumbnail__fallback" aria-hidden="true">
      <component :is="fallbackIcon" />
      <i>{{ extensionLabel }}</i>
      <b>{{ file.name || '项目资料' }}</b>
    </span>
  </span>
</template>

<script setup>
import { computed, markRaw, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import {
  DataAnalysis,
  Document,
  Film,
  Grid,
  PictureFilled
} from '@element-plus/icons-vue'
import { authHeadersForMedia, withAuthMediaUrl } from '../../utils/mediaUrl'

const props = defineProps({
  file: { type: Object, required: true }
})

const thumbnailCache = globalThis.__orepResourceThumbnailCache
  || (globalThis.__orepResourceThumbnailCache = new Map())
const pendingCache = globalThis.__orepResourceThumbnailPending
  || (globalThis.__orepResourceThumbnailPending = new Map())

const rootRef = ref(null)
const thumbnailUrl = ref('')
const loading = ref(false)
let observer = null
let loadSequence = 0

const extension = computed(() => {
  const explicit = String(props.file?.ext || '').toLowerCase().replace(/^\./, '')
  if (explicit) return explicit
  const name = String(props.file?.name || '')
  const parts = name.split('.')
  return parts.length > 1 ? parts.pop().toLowerCase() : ''
})

const kind = computed(() => {
  const ext = extension.value
  const mime = String(props.file?.mimeType || '').toLowerCase()
  if (ext === 'pdf' || mime.includes('pdf')) return 'pdf'
  if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(ext) || mime.startsWith('image/')) return 'image'
  if (['mp4', 'webm', 'mov', 'mkv', 'avi'].includes(ext) || mime.startsWith('video/')) return 'video'
  if (['xls', 'xlsx', 'csv'].includes(ext) || mime.includes('sheet') || mime.includes('excel')) return 'sheet'
  if (['ppt', 'pptx'].includes(ext) || mime.includes('presentation') || mime.includes('powerpoint')) return 'slides'
  return 'document'
})

const sourceUrl = computed(() => (
  props.file?.previewUrl
  || props.file?.downloadUrl
  || props.file?.url
  || ''
))

const cacheKey = computed(() => [
  props.file?.id || props.file?.name || 'resource',
  sourceUrl.value,
  kind.value
].join(':'))

const extensionLabel = computed(() => {
  const label = extension.value.toUpperCase() || 'FILE'
  return label.length > 5 ? 'FILE' : label
})

const fallbackIcon = computed(() => {
  if (kind.value === 'image') return markRaw(PictureFilled)
  if (kind.value === 'video') return markRaw(Film)
  if (kind.value === 'sheet') return markRaw(Grid)
  if (kind.value === 'slides') return markRaw(DataAnalysis)
  return markRaw(Document)
})

function showFallback() {
  thumbnailUrl.value = ''
  loading.value = false
}

function beginObserving() {
  observer?.disconnect()
  observer = null
  if (!rootRef.value) return
  if (typeof IntersectionObserver === 'undefined') {
    loadThumbnail()
    return
  }
  observer = new IntersectionObserver((entries) => {
    if (!entries.some(entry => entry.isIntersecting)) return
    observer?.disconnect()
    observer = null
    loadThumbnail()
  }, { rootMargin: '160px' })
  observer.observe(rootRef.value)
}

async function loadThumbnail() {
  const sequence = ++loadSequence
  const key = cacheKey.value
  const url = sourceUrl.value
  if (!url || !['pdf', 'image', 'video'].includes(kind.value)) {
    showFallback()
    return
  }
  const cached = thumbnailCache.get(key)
  if (cached) {
    thumbnailUrl.value = cached
    return
  }

  loading.value = true
  try {
    let pending = pendingCache.get(key)
    if (!pending) {
      pending = createThumbnail(kind.value, url)
      pendingCache.set(key, pending)
    }
    const result = await pending
    if (result) thumbnailCache.set(key, result)
    if (sequence === loadSequence) {
      thumbnailUrl.value = result || ''
    }
  } catch (error) {
    if (import.meta.env.DEV) {
      console.warn(
        `资源文件缩略图生成失败：${props.file?.id || 'unknown'} / ${kind.value} / ${error?.message || String(error)}`
      )
    }
    if (sequence === loadSequence) thumbnailUrl.value = ''
  } finally {
    pendingCache.delete(key)
    if (sequence === loadSequence) loading.value = false
  }
}

async function createThumbnail(fileKind, url) {
  if (fileKind === 'image') return withAuthMediaUrl(url)
  if (fileKind === 'pdf') return renderPdfThumbnail(url)
  if (fileKind === 'video') return renderVideoThumbnail(url)
  return ''
}

let pdfWorkerObjectUrl = globalThis.__orepPdfWorkerObjectUrl || ''

async function resolvePdfWorkerSrc() {
  const { default: assetUrl } = await import('pdfjs-dist/build/pdf.worker.min.mjs?url')
  if (import.meta.env.DEV) return assetUrl
  if (pdfWorkerObjectUrl) return pdfWorkerObjectUrl
  try {
    const response = await fetch(assetUrl)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const contentType = String(response.headers.get('content-type') || '').toLowerCase()
    if (contentType.includes('text/html')) throw new Error('PDF worker asset returned HTML')
    const bytes = await response.arrayBuffer()
    if (bytes.byteLength < 1024) throw new Error('PDF worker asset is empty')
    pdfWorkerObjectUrl = URL.createObjectURL(new Blob([bytes], { type: 'application/javascript' }))
    globalThis.__orepPdfWorkerObjectUrl = pdfWorkerObjectUrl
    return pdfWorkerObjectUrl
  } catch {
    return assetUrl
  }
}

async function renderPdfThumbnail(url) {
  const [workerSrc, pdfjsLib] = await Promise.all([
    resolvePdfWorkerSrc(),
    import('pdfjs-dist')
  ])
  pdfjsLib.GlobalWorkerOptions.workerSrc = workerSrc
  const loadingTask = pdfjsLib.getDocument({
    url: withAuthMediaUrl(url),
    httpHeaders: authHeadersForMedia(url)
  })
  const document = await loadingTask.promise
  try {
    const page = await document.getPage(1)
    const baseViewport = page.getViewport({ scale: 1 })
    const displayWidth = 220
    const displayScale = Math.min(1.4, displayWidth / Math.max(1, baseViewport.width))
    const pixelRatio = Math.min(2, window.devicePixelRatio || 1)
    const viewport = page.getViewport({ scale: displayScale * pixelRatio })
    const canvas = window.document.createElement('canvas')
    canvas.width = Math.ceil(viewport.width)
    canvas.height = Math.ceil(viewport.height)
    const context = canvas.getContext('2d', { alpha: false })
    context.fillStyle = '#ffffff'
    context.fillRect(0, 0, canvas.width, canvas.height)
    await page.render({ canvasContext: context, viewport }).promise
    return canvas.toDataURL('image/jpeg', 0.84)
  } finally {
    if (typeof document.destroy === 'function') await document.destroy()
  }
}

function renderVideoThumbnail(url) {
  return new Promise((resolve) => {
    const video = window.document.createElement('video')
    const timeout = window.setTimeout(() => finish(''), 6000)
    let settled = false

    function finish(result) {
      if (settled) return
      settled = true
      window.clearTimeout(timeout)
      video.removeAttribute('src')
      video.load()
      resolve(result)
    }

    video.muted = true
    video.playsInline = true
    video.preload = 'metadata'
    video.src = withAuthMediaUrl(url)
    video.addEventListener('error', () => finish(''), { once: true })
    video.addEventListener('loadedmetadata', () => {
      video.currentTime = Math.min(0.35, Math.max(0, (video.duration || 1) * 0.04))
    }, { once: true })
    video.addEventListener('seeked', () => {
      try {
        const canvas = window.document.createElement('canvas')
        const width = 240
        const ratio = video.videoWidth > 0 ? video.videoHeight / video.videoWidth : 0.625
        canvas.width = width
        canvas.height = Math.max(120, Math.round(width * ratio))
        const context = canvas.getContext('2d', { alpha: false })
        context.drawImage(video, 0, 0, canvas.width, canvas.height)
        finish(canvas.toDataURL('image/jpeg', 0.82))
      } catch {
        finish('')
      }
    }, { once: true })
  })
}

watch(cacheKey, () => {
  loadSequence += 1
  thumbnailUrl.value = ''
  loading.value = false
  beginObserving()
})

onMounted(beginObserving)
onBeforeUnmount(() => {
  loadSequence += 1
  observer?.disconnect()
})
</script>

<style scoped>
.resource-file-thumbnail {
  position: relative;
  width: 100%;
  height: 100%;
  display: block;
  overflow: hidden;
  border-radius: inherit;
  background: #fff;
}

.resource-file-thumbnail img {
  width: 100%;
  height: 100%;
  display: block;
  object-fit: cover;
  object-position: top center;
}

.resource-file-thumbnail__skeleton {
  width: 100%;
  height: 100%;
  display: grid;
  align-content: center;
  gap: 8px;
  padding: 14px 12px;
  background: linear-gradient(105deg, #fff 12%, #f4f6f9 38%, #fff 64%);
  background-size: 220% 100%;
  animation: resource-thumbnail-loading 1.2s ease-in-out infinite;
}

.resource-file-thumbnail__skeleton i {
  height: 4px;
  border-radius: 99px;
  background: #dde2e9;
}

.resource-file-thumbnail__skeleton i:nth-child(1) {
  width: 45%;
  height: 7px;
  background: #cfd6df;
}

.resource-file-thumbnail__skeleton i:nth-child(3) {
  width: 72%;
}

.resource-file-thumbnail__fallback {
  width: 100%;
  height: 100%;
  display: grid;
  grid-template-columns: 24px minmax(0, 1fr);
  grid-template-rows: 24px 1fr;
  align-content: start;
  gap: 8px;
  padding: 11px 10px;
  color: #566173;
  background:
    linear-gradient(180deg, rgba(244, 247, 251, .3), rgba(235, 240, 246, .82)),
    #fff;
}

.resource-file-thumbnail__fallback svg {
  width: 22px;
  height: 22px;
}

.resource-file-thumbnail__fallback i {
  justify-self: end;
  color: #9aa4b2;
  font-size: 8px;
  font-style: normal;
  font-weight: 850;
  letter-spacing: .05em;
}

.resource-file-thumbnail__fallback b {
  grid-column: 1 / -1;
  align-self: end;
  display: -webkit-box;
  overflow: hidden;
  color: #5f6876;
  font-size: 8px;
  font-weight: 760;
  line-height: 1.35;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.resource-file-thumbnail.is-pdf .resource-file-thumbnail__fallback svg {
  color: #e95b4d;
}

.resource-file-thumbnail.is-sheet .resource-file-thumbnail__fallback svg {
  color: #2e9b72;
}

.resource-file-thumbnail.is-slides .resource-file-thumbnail__fallback svg {
  color: #e57c3d;
}

.resource-file-thumbnail.is-video .resource-file-thumbnail__fallback svg {
  color: #7967d9;
}

.resource-file-thumbnail.is-image .resource-file-thumbnail__fallback svg {
  color: #517acb;
}

@keyframes resource-thumbnail-loading {
  from { background-position: 110% 0; }
  to { background-position: -110% 0; }
}

@media (prefers-reduced-motion: reduce) {
  .resource-file-thumbnail__skeleton {
    animation: none;
  }
}
</style>
