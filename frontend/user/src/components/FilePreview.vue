<template>
  <Teleport to="body" :disabled="inline">
    <div
      v-if="visible"
      class="fp-overlay"
      :class="{ 'fp-overlay--inline': inline }"
      @click.self="inline ? undefined : close()"
    >
      <div
        class="fp-dialog"
        :class="{ 'fp-dialog--inline': inline }"
        :role="inline ? 'region' : 'dialog'"
        :aria-modal="inline ? undefined : 'true'"
        :aria-label="`预览：${fileName}`"
      >
        <div class="fp-head">
          <div class="fp-head-info">
            <span class="fp-kicker">{{ kindLabel }}</span>
            <h3>{{ fileName }}</h3>
          </div>
          <div class="fp-head-actions">
            <div v-if="supportPages" class="fp-page-tools" aria-label="PDF 分页">
              <button type="button" class="fp-icon-btn" :disabled="currentPage <= 1" aria-label="上一页" @click="prevPage">
                <span>&lsaquo;</span>
              </button>
              <span class="fp-page-info">{{ currentPage }} / {{ totalPages }}</span>
              <button type="button" class="fp-icon-btn" :disabled="currentPage >= totalPages" aria-label="下一页" @click="nextPage">
                <span>&rsaquo;</span>
              </button>
            </div>
            <button v-if="!inline" type="button" class="fp-btn fp-btn-close" @click="close">关闭</button>
          </div>
        </div>
        <div class="fp-body" ref="bodyRef">
          <!-- Loading -->
          <div v-if="loading && !officeRenderActive && renderType !== 'pdf'" class="fp-loading">
            <div class="fp-spinner"></div>
            <span>正在加载文件预览...</span>
          </div>

          <!-- Error -->
          <div v-else-if="error" class="fp-error">
            <strong>无法预览此文件</strong>
            <p>{{ error }}</p>
            <button type="button" class="fp-btn fp-btn-download" @click="download">下载文件</button>
          </div>

          <!-- PDF -->
          <div v-else-if="renderType === 'pdf'" class="fp-pdf-container">
            <div v-if="loading" class="fp-loading fp-pdf-loading">
              <div class="fp-spinner"></div>
              <span>{{ pdfDoc ? '正在渲染当前页...' : '正在加载 PDF...' }}</span>
            </div>
            <canvas ref="pdfCanvasRef"></canvas>
          </div>

          <!-- DOCX -->
          <div v-else-if="renderType === 'docx' && docxTextFallback" class="fp-doc-text-container">
            <div class="fp-preview-note">
              <div>
                <strong>安全文本预览</strong>
                <span>{{ previewNotice }}</span>
              </div>
              <button type="button" class="fp-btn fp-btn-download" @click="download">下载原文件</button>
            </div>
            <pre>{{ textContent }}</pre>
          </div>
          <div v-else-if="renderType === 'docx'" class="fp-doc-container">
            <div v-if="loading" class="fp-loading fp-loading-inline">
              <div class="fp-spinner"></div>
              <span>正在生成原格式预览...</span>
            </div>
            <vue-office-docx
              v-if="officeSrc"
              :src="officeSrc"
              :options="docxOptions"
              @rendered="onOfficeRendered('docx')"
              @error="onOfficeError($event, 'docx')"
            />
          </div>

          <!-- XLSX -->
          <div v-else-if="renderType === 'xlsx'" class="fp-xls-container">
            <div v-if="loading" class="fp-loading fp-loading-inline">
              <div class="fp-spinner"></div>
              <span>正在生成表格预览...</span>
            </div>
            <vue-office-excel v-if="officeSrc" :src="officeSrc" @rendered="onOfficeRendered('xlsx')" @error="onOfficeError($event, 'xlsx')" />
          </div>

          <!-- PPTX -->
          <div v-else-if="renderType === 'pptx'" ref="pptContainerRef" class="fp-ppt-container">
            <div v-if="loading" class="fp-loading fp-loading-inline">
              <div class="fp-spinner"></div>
              <span>正在生成演示预览...</span>
            </div>
            <vue-office-pptx
              v-if="officeSrc && pptRenderReady"
              :key="pptRenderKey"
              :src="officeSrc"
              :options="pptxOptions"
              @rendered="onOfficeRendered('pptx')"
              @error="onOfficeError($event, 'pptx')"
            />
          </div>

          <!-- Video -->
          <div v-else-if="renderType === 'video'" class="fp-video-container">
            <video ref="videoRef" controls preload="metadata" @loadedmetadata="seekMediaStart">
              <source :src="mediaSrc" />
              您的浏览器不支持视频播放
            </video>
          </div>

          <!-- Audio -->
          <div v-else-if="renderType === 'audio'" class="fp-audio-container">
            <audio ref="audioRef" controls preload="metadata" @loadedmetadata="seekMediaStart">
              <source :src="mediaSrc" />
              您的浏览器不支持音频播放
            </audio>
          </div>

          <!-- Image -->
          <div v-else-if="renderType === 'image'" class="fp-image-container">
            <img :src="mediaSrc" :alt="fileName" />
          </div>

          <!-- Markdown -->
          <div v-else-if="renderType === 'md'" class="fp-md-container" v-html="mdHtml"></div>

          <!-- Text -->
          <div v-else-if="renderType === 'text'" class="fp-text-container">
            <pre>{{ textContent }}</pre>
          </div>

          <!-- Unsupported -->
          <div v-else class="fp-error">
            <strong>不支持预览此文件类型</strong>
            <p>{{ ext?.toUpperCase() }} 格式暂不支持在线预览，请下载后查看。</p>
            <button type="button" class="fp-btn fp-btn-download" @click="download">下载文件</button>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, watch, computed, nextTick, onBeforeUnmount } from 'vue'
import VueOfficeDocx from '@vue-office/docx'
import VueOfficeExcel from '@vue-office/excel'
import VueOfficePptx from '@vue-office/pptx'
import '@vue-office/docx/lib/index.css'
import '@vue-office/excel/lib/index.css'
import DOMPurify from 'dompurify'
import { getUserToken } from '../utils/authStorage'
import { authHeadersForMedia, isProtectedUploadUrl, normalizeMediaUrl, withAuthMediaUrl } from '../utils/mediaUrl'

const props = defineProps({
  visible: { type: Boolean, default: false },
  fileUrl: { type: String, default: '' },
  fileName: { type: String, default: '文件预览' },
  fileType: { type: String, default: '' },
  startTime: { type: Number, default: 0 },
  inline: { type: Boolean, default: false }
})

const emit = defineEmits(['update:visible', 'download'])

const bodyRef = ref(null)
const pdfCanvasRef = ref(null)
const videoRef = ref(null)
const audioRef = ref(null)
const pptContainerRef = ref(null)
const pptRenderWidth = ref(0)
const pptRenderHeight = ref(0)
const loading = ref(false)
const error = ref('')
const currentPage = ref(1)
const totalPages = ref(1)
const mdHtml = ref('')
const textContent = ref('')
const previewNotice = ref('')
const officeSrc = ref(null)
const docxTextFallback = ref(false)
let pdfDoc = null

const ext = computed(() => {
  const name = props.fileName || ''
  const parts = name.split('.')
  return parts.length > 1 ? parts.pop().toLowerCase() : ''
})

const kindLabel = computed(() => {
  const map = {
    pdf: 'PDF 文档',
    doc: 'WORD 文档',
    docx: 'WORD 文档',
    xls: 'EXCEL 表格',
    xlsx: 'EXCEL 表格',
    csv: 'CSV 表格',
    ppt: 'PPT 演示',
    pptx: 'PPT 演示',
    mp4: '视频',
    webm: '视频',
    mov: '视频',
    mkv: '视频',
    avi: '视频',
    png: '图片',
    jpg: '图片',
    jpeg: '图片',
    gif: '图片',
    webp: '图片',
    mp3: '音频',
    wav: '音频',
    m4a: '音频',
    aac: '音频',
    ogg: '音频',
    md: 'MARKDOWN',
    txt: '文本'
  }
  return map[ext.value] || '文件'
})

const renderType = computed(() => {
  const e = ext.value
  const t = (props.fileType || '').toLowerCase()
  if (t.startsWith('audio/')) return 'audio'
  if (e === 'pdf') return 'pdf'
  if (e === 'docx') return 'docx'
  if (e === 'xlsx') return 'xlsx'
  if (e === 'pptx') return 'pptx'
  if (['mp4', 'webm', 'mov', 'mkv', 'avi'].includes(e)) return 'video'
  if (['png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'].includes(e)) return 'image'
  if (e === 'md') return 'md'
  if (['txt', 'csv'].includes(e)) return 'text'
  // Fallback: check MIME type
  if (t.includes('pdf')) return 'pdf'
  if (t.includes('word') || t.includes('document')) return 'docx'
  if (t.includes('sheet') || t.includes('excel')) return 'xlsx'
  if (t.includes('presentation') || t.includes('powerpoint')) return 'pptx'
  if (t.startsWith('video/')) return 'video'
  if (t.startsWith('image/')) return 'image'
  if (['mp3', 'wav', 'm4a', 'aac', 'ogg'].includes(e)) return 'audio'
  return ''
})

const supportPages = computed(() => renderType.value === 'pdf' && totalPages.value > 1)
const officeRenderActive = computed(() => ['docx', 'xlsx', 'pptx'].includes(renderType.value) && !docxTextFallback.value)
const pptRenderReady = computed(() => pptRenderWidth.value > 0 && pptRenderHeight.value > 0)
const pptRenderKey = computed(() => `pptx-${pptRenderWidth.value}x${pptRenderHeight.value}`)
const pptxOptions = computed(() => ({
  width: pptRenderWidth.value,
  height: pptRenderHeight.value
}))
const docxOptions = {
  inWrapper: true,
  ignoreLastRenderedPageBreak: true
}

function normalizeUrl(url) {
  return normalizeMediaUrl(url)
}

function authHeadersFor(url) {
  return authHeadersForMedia(url)
}

/** URL for native tags (video/audio/img) and direct download links. */
const mediaSrc = computed(() => withAuthMediaUrl(props.fileUrl))

function close() {
  emit('update:visible', false)
  cleanup()
}

async function download() {
  emit('download')
  const url = normalizeUrl(props.fileUrl)
  if (!url) return
  if (url.startsWith('/api/') || isProtectedUploadUrl(url)) {
    try {
      const resp = await fetch(url.startsWith('/api/') ? url : withAuthMediaUrl(url), {
        headers: authHeadersFor(url)
      })
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
      const blob = await resp.blob()
      const blobUrl = URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = blobUrl
      link.download = props.fileName || 'download'
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.setTimeout(() => URL.revokeObjectURL(blobUrl), 1000)
    } catch (e) {
      error.value = `文件下载失败：${e.message || '网络错误'}`
    }
    return
  }
  const link = document.createElement('a')
  link.href = withAuthMediaUrl(url)
  link.download = props.fileName || 'download'
  document.body.appendChild(link)
  link.click()
  link.remove()
}

function cleanup() {
  if (pdfDoc) {
    if (typeof pdfDoc.destroy === 'function') pdfDoc.destroy()
    pdfDoc = null
  }
  if (officeLoadTimer) {
    clearTimeout(officeLoadTimer)
    officeLoadTimer = null
  }
  error.value = ''
  loading.value = false
  currentPage.value = 1
  totalPages.value = 1
  mdHtml.value = ''
  textContent.value = ''
  previewNotice.value = ''
  officeSrc.value = null
  docxTextFallback.value = false
}

function seekMediaStart() {
  const start = Number(props.startTime || 0)
  if (!Number.isFinite(start) || start <= 0) return
  const media = renderType.value === 'audio' ? audioRef.value : videoRef.value
  if (!media) return
  try {
    media.currentTime = Math.max(0, start)
  } catch (e) {
    // Some browsers reject seeking until enough metadata is available; safe to ignore.
  }
}

let pdfWorkerObjectUrl = ''

/**
 * pdf.js loads its worker via dynamic import()/module Worker.
 * Some reverse proxies serve .mjs as application/octet-stream; with
 * X-Content-Type-Options: nosniff the browser then rejects the module.
 * Re-wrap the worker bytes as a JS Blob so the Content-Type is correct.
 */
async function resolvePdfWorkerSrc() {
  const { default: assetUrl } = await import('pdfjs-dist/build/pdf.worker.min.mjs?url')
  // Vite injects /@vite/client into module responses in development. Wrapping
  // that transformed source in a Blob breaks its root-relative import, while
  // the original dev-server URL works correctly as a module worker.
  if (import.meta.env.DEV) return assetUrl
  if (pdfWorkerObjectUrl) return pdfWorkerObjectUrl
  try {
    const resp = await fetch(assetUrl)
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const contentType = (resp.headers.get('content-type') || '').toLowerCase()
    // SPA fallback sometimes returns HTML for missing assets
    if (contentType.includes('text/html')) {
      throw new Error('PDF worker asset returned HTML')
    }
    const bytes = await resp.arrayBuffer()
    if (bytes.byteLength < 1024) throw new Error('PDF worker asset is empty')
    pdfWorkerObjectUrl = URL.createObjectURL(
      new Blob([bytes], { type: 'application/javascript' })
    )
    return pdfWorkerObjectUrl
  } catch {
    // Last resort: use the asset URL directly (works when MIME is correct)
    return assetUrl
  }
}

// PDF rendering
async function loadPdf() {
  if (ext.value !== 'pdf') return
  loading.value = true
  error.value = ''
  try {
    const [workerSrc, pdfjsLib] = await Promise.all([
      resolvePdfWorkerSrc(),
      import('pdfjs-dist')
    ])
    pdfjsLib.GlobalWorkerOptions.workerSrc = workerSrc
    const url = withAuthMediaUrl(props.fileUrl)
    const loadingTask = pdfjsLib.getDocument({
      url,
      httpHeaders: authHeadersFor(props.fileUrl)
    })
    pdfDoc = await loadingTask.promise
    totalPages.value = pdfDoc.numPages
    currentPage.value = 1
    await nextTick()
    await renderPdfPage(1)
  } catch (e) {
    error.value = e.message || 'PDF 加载失败'
  } finally {
    loading.value = false
  }
}

async function renderPdfPage(pageNum) {
  if (!pdfDoc) return
  loading.value = true
  try {
    const page = await pdfDoc.getPage(pageNum)
    const canvas = await waitForPdfCanvas()
    const containerWidth = Math.max(320, (bodyRef.value?.clientWidth || 960) - 80)
    const unscaled = page.getViewport({ scale: 1 })
    const scale = Math.min(1.62, Math.max(0.92, containerWidth / unscaled.width))
    const viewport = page.getViewport({ scale })
    const ctx = canvas.getContext('2d')
    const pixelRatio = window.devicePixelRatio || 1
    canvas.width = Math.floor(viewport.width * pixelRatio)
    canvas.height = Math.floor(viewport.height * pixelRatio)
    canvas.style.width = `${Math.floor(viewport.width)}px`
    canvas.style.height = `${Math.floor(viewport.height)}px`
    ctx.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0)
    ctx.clearRect(0, 0, viewport.width, viewport.height)
    await page.render({ canvasContext: ctx, viewport }).promise
  } finally {
    loading.value = false
  }
}

async function waitForPdfCanvas() {
  for (let i = 0; i < 12; i++) {
    await nextTick()
    await new Promise(resolve => requestAnimationFrame(resolve))
    if (pdfCanvasRef.value) return pdfCanvasRef.value
  }
  throw new Error('PDF 预览画布尚未准备好，请重新打开预览。')
}

function prevPage() {
  if (currentPage.value > 1) {
    currentPage.value--
    renderPdfPage(currentPage.value)
  }
}

function nextPage() {
  if (currentPage.value < totalPages.value) {
    currentPage.value++
    renderPdfPage(currentPage.value)
  }
}

// Office document rendered callback. Some DOCX files trigger the library's
// rendered event even though no page content was produced, so verify the
// rendered surface before treating the preview as successful.
async function onOfficeRendered(type) {
  if (type === 'docx') {
    await nextTick()
    await new Promise(resolve => requestAnimationFrame(() => requestAnimationFrame(resolve)))
    const surface = bodyRef.value?.querySelector('.docx-wrapper section.docx')
    const hasVisibleContent = Boolean(
      surface && (surface.textContent?.trim() || surface.querySelector('img, canvas, svg'))
    )
    if (!hasVisibleContent) {
      if (officeLoadTimer) {
        clearTimeout(officeLoadTimer)
        officeLoadTimer = null
      }
      await loadServerTextPreview('原格式预览为空，已切换为安全文本预览。')
      return
    }
  }
  loading.value = false
  if (officeLoadTimer) {
    clearTimeout(officeLoadTimer)
    officeLoadTimer = null
  }
}

// Office document error callback
function onOfficeError(err, type) {
  if (officeLoadTimer) {
    clearTimeout(officeLoadTimer)
    officeLoadTimer = null
  }
  const msg = err?.message || err?.toString() || ''
  if (type === 'docx') {
    loadServerTextPreview(`原格式渲染失败${msg ? '：' + msg : ''}，已切换为安全文本预览。`)
    return
  }
  loading.value = false
  error.value = `${type.toUpperCase()} 文档加载失败${msg ? '：' + msg : ''}，请尝试下载后查看。`
}

let officeLoadTimer = null
let pptResizeObserver = null
let pptMeasureFrame = 0

function stopPptResizeObserver({ reset = false } = {}) {
  if (pptResizeObserver) {
    pptResizeObserver.disconnect()
    pptResizeObserver = null
  }
  if (pptMeasureFrame) {
    if (typeof window !== 'undefined') window.cancelAnimationFrame(pptMeasureFrame)
    pptMeasureFrame = 0
  }
  if (reset) {
    pptRenderWidth.value = 0
    pptRenderHeight.value = 0
  }
}

function measurePptViewport() {
  pptMeasureFrame = 0
  const container = pptContainerRef.value
  if (!container || typeof window === 'undefined') return
  const style = window.getComputedStyle(container)
  const horizontalPadding = Number.parseFloat(style.paddingLeft || 0) + Number.parseFloat(style.paddingRight || 0)
  const verticalPadding = Number.parseFloat(style.paddingTop || 0) + Number.parseFloat(style.paddingBottom || 0)
  const width = Math.max(1, Math.floor(container.clientWidth - horizontalPadding))
  const height = Math.max(280, Math.floor(container.clientHeight - verticalPadding))
  if (width === pptRenderWidth.value && height === pptRenderHeight.value) return
  pptRenderWidth.value = width
  pptRenderHeight.value = height
}

function schedulePptMeasurement() {
  if (typeof window === 'undefined') return
  if (pptMeasureFrame) window.cancelAnimationFrame(pptMeasureFrame)
  pptMeasureFrame = window.requestAnimationFrame(measurePptViewport)
}

async function observePptViewport() {
  stopPptResizeObserver()
  await nextTick()
  const container = pptContainerRef.value
  if (!container) return
  schedulePptMeasurement()
  if (typeof ResizeObserver !== 'undefined') {
    pptResizeObserver = new ResizeObserver(schedulePptMeasurement)
    pptResizeObserver.observe(container)
  }
}

async function loadServerTextPreview(notice) {
  loading.value = true
  error.value = ''
  textContent.value = ''
  previewNotice.value = ''
  docxTextFallback.value = true
  try {
    const token = getUserToken()
    const resp = await fetch(`/api/file-preview?url=${encodeURIComponent(props.fileUrl)}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    })
    const result = await resp.json().catch(() => null)
    if (!resp.ok || result?.code !== 200) {
      throw new Error(result?.message || `HTTP ${resp.status}`)
    }
    const data = result.data || {}
    textContent.value = data.text || ''
    previewNotice.value = notice || (data.truncated
      ? '原格式预览暂不可用，已提取正文前 16000 字，完整内容请下载原文件查看。'
      : '原格式预览暂不可用，已提取正文内容，版式、图片和批注请下载原文件查看。')
    if (!textContent.value.trim()) {
      throw new Error('未解析到可预览正文')
    }
  } catch (e) {
    error.value = `文本预览生成失败：${e.message || '服务不可用'}，请下载后查看。`
  } finally {
    loading.value = false
  }
}

async function loadOfficeFile(type) {
  loading.value = true
  error.value = ''
  officeSrc.value = null
  docxTextFallback.value = false
  try {
    const url = withAuthMediaUrl(props.fileUrl)
    const resp = await fetch(url, { headers: authHeadersFor(props.fileUrl) })
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    const buf = await resp.arrayBuffer()
    officeSrc.value = buf
    officeLoadTimer = setTimeout(() => {
      if (type === 'docx') {
        loadServerTextPreview('原格式渲染等待时间过长，已切换为安全文本预览。')
      } else {
        loading.value = false
        error.value = '文件渲染超时，请检查文件格式是否正确，或尝试下载后查看。'
      }
    }, type === 'docx' ? 12000 : 30000)
  } catch (e) {
    loading.value = false
    error.value = `文件加载失败：${e.message || '网络错误'}，请尝试下载后查看。`
  }
}

// Markdown rendering
async function loadMarkdown() {
  if (ext.value !== 'md') return
  loading.value = true
  try {
    const { marked } = await import('marked')
    const url = withAuthMediaUrl(props.fileUrl)
    const resp = await fetch(url, { headers: authHeadersFor(props.fileUrl) })
    if (!resp.ok) throw new Error('文件加载失败')
    const text = await resp.text()
    mdHtml.value = DOMPurify.sanitize(marked(text))
  } catch (e) {
    error.value = e.message || 'Markdown 加载失败'
  } finally {
    loading.value = false
  }
}

// Text loading
async function loadText() {
  if (!['txt', 'csv'].includes(ext.value)) return
  loading.value = true
  try {
    const url = withAuthMediaUrl(props.fileUrl)
    const resp = await fetch(url, { headers: authHeadersFor(props.fileUrl) })
    if (!resp.ok) throw new Error('文件加载失败')
    textContent.value = await resp.text()
  } catch (e) {
    error.value = e.message || '文本加载失败'
  } finally {
    loading.value = false
  }
}

// Watch for visibility changes
watch(
  () => [props.visible, props.fileUrl],
  async ([visible]) => {
    if (visible && props.fileUrl) {
      cleanup()
      const rt = renderType.value
      if (rt === 'pdf') {
        await loadPdf()
      } else if (rt === 'md') {
        await loadMarkdown()
      } else if (rt === 'text') {
        await loadText()
      } else if (['docx', 'xlsx', 'pptx'].includes(rt)) {
        await loadOfficeFile(rt)
      }
    }
  },
  { immediate: true }
)

watch(
  () => [props.visible, renderType.value],
  async ([visible, type]) => {
    if (!visible || type !== 'pptx') {
      stopPptResizeObserver({ reset: true })
      return
    }
    await observePptViewport()
  },
  { immediate: true, flush: 'post' }
)

// Keyboard ESC to close
function onKeydown(e) {
  if (e.key === 'Escape' && props.visible && !props.inline) close()
}
if (typeof window !== 'undefined') {
  window.addEventListener('keydown', onKeydown)
}
onBeforeUnmount(() => {
  stopPptResizeObserver({ reset: true })
  cleanup()
  if (officeLoadTimer) {
    clearTimeout(officeLoadTimer)
    officeLoadTimer = null
  }
  if (typeof window !== 'undefined') {
    window.removeEventListener('keydown', onKeydown)
  }
})
</script>

<style scoped>
.fp-overlay {
  position: fixed;
  inset: 0;
  z-index: var(--z-modal, 1050);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: clamp(14px, 3vh, 28px) clamp(14px, 5vw, 68px);
  background: oklch(0.25 0.008 60 / 0.52);
  backdrop-filter: blur(6px);
}

.fp-overlay--inline {
  position: relative;
  inset: auto;
  z-index: 0;
  width: 100%;
  height: 100%;
  min-height: 0;
  display: block;
  padding: 0;
  background: transparent;
  backdrop-filter: none;
}

.fp-dialog {
  width: min(1160px, 100%);
  height: min(87vh, 900px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid oklch(0.87 0.018 62);
  border-radius: 10px;
  background: oklch(0.985 0.006 62);
  box-shadow: 0 24px 70px oklch(0.24 0.008 60 / 0.24);
}

.fp-dialog--inline {
  width: 100%;
  height: 100%;
  min-height: 0;
  border: 0;
  border-radius: 0;
  background: #fff;
  box-shadow: none;
}

.fp-dialog--inline .fp-head {
  min-height: 54px;
  padding: 9px 12px 9px 16px;
}

.fp-dialog--inline .fp-head-info h3 {
  font-size: 14px;
}

.fp-head {
  min-height: 58px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 14px;
  padding: 10px 12px 10px 18px;
  border-bottom: 1px solid oklch(0.9 0.014 62);
  background: linear-gradient(180deg, oklch(0.996 0.004 62), oklch(0.982 0.007 62));
  flex-shrink: 0;
}

.fp-head-info {
  min-width: 0;
  display: grid;
  gap: 4px;
}

.fp-kicker {
  color: oklch(0.54 0.028 58);
  font-size: 11px;
  font-weight: 850;
  letter-spacing: 0;
}

.fp-head-info h3 {
  margin: 0;
  min-width: 0;
  color: oklch(0.24 0.012 65);
  font-size: 17px;
  font-weight: 860;
  line-height: 1.25;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.fp-head-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex-shrink: 0;
}

.fp-page-tools {
  height: 34px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px;
  border: 1px solid oklch(0.86 0.018 62);
  border-radius: 8px;
  background: oklch(0.972 0.009 62);
  white-space: nowrap;
}

.fp-page-info {
  min-width: 50px;
  color: oklch(0.36 0.016 62);
  font-size: 12px;
  font-weight: 850;
  text-align: center;
  white-space: nowrap;
}

.fp-icon-btn {
  width: 28px;
  height: 28px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: oklch(0.39 0.016 62);
  cursor: pointer;
  transition: background 160ms ease, color 160ms ease;
}

.fp-icon-btn:hover:not(:disabled) {
  background: oklch(0.94 0.035 48);
  color: oklch(0.57 0.17 42);
}

.fp-icon-btn:disabled {
  cursor: not-allowed;
  opacity: 0.38;
}

.fp-icon-btn span {
  font-size: 20px;
  line-height: 1;
}

.fp-btn {
  width: auto;
  min-width: 36px;
  height: 34px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 12px;
  border: 1px solid oklch(0.86 0.018 62);
  border-radius: 8px;
  background: oklch(0.99 0.004 62);
  color: oklch(0.35 0.014 62);
  cursor: pointer;
  font-weight: 850;
  font-size: 12px;
  white-space: nowrap;
  transition: border-color 160ms ease, background 160ms ease, color 160ms ease;
}

.fp-btn:hover:not(:disabled) {
  border-color: oklch(0.78 0.12 45);
  background: oklch(0.975 0.024 48);
  color: oklch(0.58 0.16 42);
}

.fp-btn:disabled {
  cursor: not-allowed;
  opacity: 0.42;
}

.fp-btn span {
  font-size: 18px;
  line-height: 1;
}

.fp-btn-close {
  min-width: 58px;
  border-color: oklch(0.84 0.022 62);
}

.fp-btn-download {
  border-color: oklch(0.78 0.12 45);
  background: oklch(0.96 0.04 45);
  color: oklch(0.55 0.16 42);
}

.fp-btn-download:hover {
  border-color: oklch(0.7 0.17 42);
  background: oklch(0.93 0.07 45);
}

.fp-body {
  flex: 1;
  overflow: auto;
  min-height: 0;
  background: oklch(0.955 0.008 62);
}

/* Loading */
.fp-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 80px 20px;
  color: oklch(0.5 0.014 65);
  font-size: 13px;
}

.fp-loading-inline {
  position: absolute;
  inset: 0;
  z-index: 2;
  min-height: 280px;
  background: oklch(0.985 0.006 62 / 0.84);
  backdrop-filter: blur(2px);
}

.fp-spinner {
  width: 32px;
  height: 32px;
  border: 2px solid oklch(0.88 0.018 65);
  border-top-color: oklch(0.62 0.18 42);
  border-radius: 50%;
  animation: fp-spin 0.8s linear infinite;
}

@keyframes fp-spin {
  to { transform: rotate(360deg); }
}

/* Error */
.fp-error {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 80px 20px;
  text-align: center;
}

.fp-error strong {
  color: oklch(0.28 0.012 65);
  font-size: 18px;
}

.fp-error p {
  margin: 0;
  color: oklch(0.52 0.014 65);
  font-size: 13px;
  max-width: 400px;
}

/* PDF */
.fp-pdf-container {
  position: relative;
  min-height: 100%;
  display: grid;
  justify-items: center;
  align-items: start;
  padding: 28px 28px 40px;
  background:
    linear-gradient(180deg, oklch(0.974 0.006 62), oklch(0.94 0.008 62));
}

.fp-pdf-loading {
  position: absolute;
  inset: 0;
  z-index: 2;
  min-height: 0;
  padding: 0;
  background: oklch(0.965 0.008 62 / 0.78);
  backdrop-filter: blur(2px);
}

.fp-pdf-container canvas {
  max-width: 100%;
  height: auto;
  display: block;
  border: 1px solid oklch(0.89 0.012 62);
  background: oklch(0.995 0.004 62);
  box-shadow: 0 10px 32px oklch(0.27 0.01 62 / 0.14);
}

/* DOCX text preview */
.fp-doc-container {
  position: relative;
  min-height: 520px;
  padding: 18px;
  background: oklch(0.95 0.008 65);
}

.fp-doc-container :deep(.vue-office-docx) {
  height: auto;
  min-height: 480px;
  overflow: visible;
}

.fp-doc-container :deep(.docx-wrapper) {
  min-height: 480px;
  border-radius: 8px;
}

.fp-doc-container :deep(.docx-wrapper > section.docx) {
  max-width: 100%;
}

.fp-doc-text-container {
  padding: 24px;
}

.fp-preview-note {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
  padding: 14px 16px;
  border: 1px solid oklch(0.84 0.08 48);
  border-radius: 8px;
  background: oklch(0.97 0.035 48);
}

.fp-preview-note > div {
  display: grid;
  gap: 4px;
}

.fp-preview-note strong {
  color: oklch(0.32 0.035 65);
  font-size: 14px;
}

.fp-preview-note span {
  color: oklch(0.48 0.018 65);
  font-size: 12px;
  line-height: 1.6;
}

.fp-doc-text-container pre {
  margin: 0;
  min-height: 360px;
  padding: 28px 32px;
  border: 1px solid rgba(240, 240, 250, 0.12);
  border-radius: 8px;
  background: oklch(0.995 0.004 62);
  color: oklch(0.31 0.012 65);
  font-size: 14px;
  line-height: 1.95;
  white-space: pre-wrap;
  word-break: break-word;
  font-family: inherit;
}

/* XLSX */
.fp-xls-container {
  position: relative;
  min-height: 420px;
  padding: 16px;
  overflow: auto;
  background: oklch(0.965 0.006 65);
}

.fp-xls-container :deep(.excel-sheet) {
  border-radius: 4px;
}

/* PPTX */
.fp-ppt-container {
  position: relative;
  box-sizing: border-box;
  width: 100%;
  height: 100%;
  min-width: 0;
  min-height: 420px;
  display: flex;
  justify-content: center;
  padding: 24px;
  overflow: hidden;
  background: oklch(0.955 0.008 65);
}

.fp-ppt-container :deep(.vue-office-pptx),
.fp-ppt-container :deep(.vue-office-pptx-main) {
  width: 100% !important;
  height: 100% !important;
  min-width: 0;
  overflow: hidden;
}

.fp-ppt-container :deep(.pptx-preview-wrapper) {
  max-width: 100%;
  overflow-x: hidden !important;
  overflow-y: auto !important;
}

/* Video */
.fp-video-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 24px;
  background: oklch(0.955 0.008 65);
}

.fp-video-container video {
  max-width: 100%;
  max-height: calc(100vh - 180px);
  border-radius: 6px;
  outline: none;
}

/* Audio */
.fp-audio-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 220px;
  padding: 32px;
  background: oklch(0.955 0.008 65);
}

.fp-audio-container audio {
  width: min(620px, 100%);
  outline: none;
}

/* Image */
.fp-image-container {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 24px;
  background: oklch(0.955 0.008 65);
  min-height: 200px;
}

.fp-image-container img {
  max-width: 100%;
  max-height: calc(100vh - 180px);
  object-fit: contain;
  border-radius: 4px;
}

/* Markdown */
.fp-md-container {
  padding: 28px 32px;
  color: oklch(0.31 0.012 65);
  line-height: 1.8;
  font-size: 14px;
}

.fp-md-container :deep(h1),
.fp-md-container :deep(h2),
.fp-md-container :deep(h3) {
  color: oklch(0.24 0.012 65);
  margin: 24px 0 12px;
}

.fp-md-container :deep(h1) { font-size: 26px; }
.fp-md-container :deep(h2) { font-size: 22px; }
.fp-md-container :deep(h3) { font-size: 18px; }

.fp-md-container :deep(p) {
  margin: 0 0 12px;
}

.fp-md-container :deep(code) {
  padding: 2px 6px;
  border-radius: 4px;
  background: oklch(0.94 0.018 65);
  color: oklch(0.52 0.15 42);
  font-size: 13px;
}

.fp-md-container :deep(pre) {
  padding: 16px;
  border-radius: 8px;
  background: oklch(0.94 0.018 65);
  overflow-x: auto;
}

.fp-md-container :deep(pre code) {
  padding: 0;
  background: none;
  color: oklch(0.31 0.012 65);
}

.fp-md-container :deep(blockquote) {
  margin: 12px 0;
  padding: 8px 16px;
  border: 1px solid oklch(0.84 0.08 48);
  background: oklch(0.97 0.035 48);
  border-radius: 8px;
}

.fp-md-container :deep(table) {
  width: 100%;
  border-collapse: collapse;
  margin: 12px 0;
}

.fp-md-container :deep(th),
.fp-md-container :deep(td) {
  padding: 8px 12px;
  border: 1px solid oklch(0.88 0.018 65);
  text-align: left;
}

.fp-md-container :deep(th) {
  background: oklch(0.95 0.012 65);
  font-weight: 850;
}

.fp-md-container :deep(a) {
  color: oklch(0.55 0.16 42);
  text-decoration: none;
}

.fp-md-container :deep(a:hover) {
  text-decoration: underline;
}

/* Text */
.fp-text-container {
  padding: 24px;
}

.fp-text-container pre {
  margin: 0;
  padding: 20px;
  border-radius: 8px;
  background: oklch(0.995 0.004 62);
  color: oklch(0.31 0.012 65);
  font-size: 13px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-all;
  font-family: 'SF Mono', 'Fira Code', 'Consolas', monospace;
}

/* Responsive */
@media (max-width: 760px) {
  .fp-overlay {
    padding: 10px;
  }

  .fp-dialog {
    height: calc(100dvh - 20px);
  }

  .fp-head {
    grid-template-columns: 1fr;
    align-items: flex-start;
    gap: 10px;
  }

  .fp-head-info h3 {
    max-width: 100%;
    font-size: 15px;
  }

  .fp-head-actions {
    width: 100%;
    justify-content: space-between;
    flex-wrap: wrap;
  }

  .fp-page-tools {
    max-width: calc(100vw - 110px);
  }

  .fp-pdf-container {
    padding: 18px 12px 28px;
  }
}
</style>
