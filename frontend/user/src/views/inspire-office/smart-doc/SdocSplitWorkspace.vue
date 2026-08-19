<template>
  <div class="sdoc-split" :class="`is-${layout}`">
    <div ref="stageRef" class="sdoc-split__stage" :class="`is-${layout}`" :style="stageStyle">
      <div class="sdoc-split__pane is-a">
        <SmartDocEditor :document-id="primaryId" :embedded="layout !== 'single'" />
      </div>
      <div
        v-if="layout !== 'single'"
        class="sdoc-split__gutter"
        role="separator"
        :aria-orientation="layout === 'horizontal' ? 'vertical' : 'horizontal'"
        :aria-valuenow="Math.round(ratio * 100)"
        tabindex="0"
        @pointerdown="onDragStart"
        @keydown="onGutterKey"
      >
        <i />
      </div>
      <div v-if="layout !== 'single'" class="sdoc-split__pane is-b">
        <div class="sdoc-split__pane-bar">
          <strong>{{ paneBTitle }}</strong>
          <button type="button" @click="pickerOpen = true">换文档</button>
        </div>
        <SmartDocEditor
          v-if="paneB && paneBIsSdoc"
          :key="`b-sdoc-${paneB}`"
          :document-id="paneB"
          embedded
        />
        <SdocOfficeFrame
          v-else-if="paneB"
          :key="`b-office-${paneB}`"
          :document-id="paneB"
          :ext="paneBMeta.ext"
          :document-type="paneBMeta.documentType"
        />
      </div>
    </div>

    <div v-if="pickerOpen" class="sdoc-modal" role="dialog" aria-modal="true" @click.self="pickerOpen = false">
      <div class="sdoc-dialog">
        <header>
          <h2>第二窗格打开</h2>
          <button type="button" class="sdoc-dialog__x" aria-label="关闭" @click="pickerOpen = false">×</button>
        </header>
        <input v-model="keyword" class="sdoc-dialog__search" type="search" placeholder="搜索 Word / PPT / 表格 / 智能文档" />
        <ul v-if="filtered.length" class="sdoc-dialog__list">
          <li>
            <button type="button" @click="pickCurrent">
              <strong>当前文档（对照阅读）</strong>
              <small>同一篇智能文档，两边各自滚动</small>
            </button>
          </li>
          <li v-for="doc in filtered" :key="doc.id">
            <button type="button" @click="pick(doc)">
              <strong>{{ doc.title || '未命名文档' }}</strong>
              <small>{{ officeKindLabel(officeKind(doc)) }} · {{ doc.scope || '文档' }}{{ doc.teamName ? ` · ${doc.teamName}` : '' }}</small>
            </button>
          </li>
        </ul>
        <div v-else class="sdoc-dialog__empty">{{ loading ? '加载中…' : '没有可打开的文档' }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, provide, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import SmartDocEditor from './SmartDocEditor.vue'
import SdocOfficeFrame from './SdocOfficeFrame.vue'
import { useSdocHost } from './sdocHost'
import { SDOC_SPLIT_KEY, isSdocKind, officeKind, officeKindLabel } from './sdocSplit'

const props = defineProps({
  documentId: { type: [String, Number], default: '' },
})

const route = useRoute()
const host = useSdocHost()
const primaryId = computed(() => String(props.documentId || route.params.id || ''))
const layout = ref('single')
const paneB = ref('')
const ratio = ref(0.5)
const pickerOpen = ref(false)
const keyword = ref('')
const loading = ref(false)
const docs = ref([])
const paneBMeta = ref({ ext: 'sdoc', documentType: 'sdoc', title: '' })
const stageRef = ref(null)
const paneBIsSdoc = computed(() => isSdocKind(paneBMeta.value))
const paneBTitle = computed(() => {
  if (String(paneB.value) === primaryId.value) return '对照阅读'
  if (paneBMeta.value.title) return paneBMeta.value.title
  const hit = docs.value.find((d) => String(d.id) === String(paneB.value))
  return hit?.title || '第二窗格'
})

const filtered = computed(() => {
  const q = keyword.value.trim().toLowerCase()
  return docs.value.filter((doc) => {
    if (String(doc.id) === primaryId.value) return false
    if (!q) return true
    const hay = `${doc.title || ''} ${officeKindLabel(officeKind(doc))} ${doc.ext || ''}`
    return hay.toLowerCase().includes(q)
  })
})

const stageStyle = computed(() => {
  if (layout.value === 'horizontal') {
    return { gridTemplateColumns: `${ratio.value}fr 6px ${1 - ratio.value}fr` }
  }
  if (layout.value === 'vertical') {
    return { gridTemplateRows: `${ratio.value}fr 6px ${1 - ratio.value}fr` }
  }
  return {}
})

function setLayout(mode) {
  layout.value = mode
  if (mode === 'single') return
  if (!paneB.value) pickCurrent()
}

function pickCurrent() {
  paneB.value = primaryId.value
  paneBMeta.value = { ext: 'sdoc', documentType: 'sdoc', title: '对照阅读' }
  pickerOpen.value = false
}

function pick(doc) {
  paneB.value = String(doc.id)
  paneBMeta.value = {
    ext: doc.ext || '',
    documentType: doc.documentType || doc.documentKind || '',
    title: doc.title || '未命名文档',
  }
  pickerOpen.value = false
}

async function loadDocs() {
  if (!host.listDocuments) return
  loading.value = true
  try {
    const list = await host.listDocuments({ scope: 'all' })
    docs.value = Array.isArray(list) ? list : []
  } catch {
    docs.value = []
  } finally {
    loading.value = false
  }
}

let dragging = false
function onDragStart(event) {
  dragging = true
  event.currentTarget.setPointerCapture?.(event.pointerId)
  window.addEventListener('pointermove', onDragMove)
  window.addEventListener('pointerup', onDragEnd)
}
function onDragMove(event) {
  if (!dragging || !stageRef.value) return
  const rect = stageRef.value.getBoundingClientRect()
  const next = layout.value === 'horizontal'
    ? (event.clientX - rect.left) / rect.width
    : (event.clientY - rect.top) / rect.height
  ratio.value = Math.min(0.8, Math.max(0.2, next))
}
function onDragEnd() {
  dragging = false
  window.removeEventListener('pointermove', onDragMove)
  window.removeEventListener('pointerup', onDragEnd)
}
function onGutterKey(event) {
  const step = event.shiftKey ? 0.08 : 0.04
  if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
    ratio.value = Math.max(0.2, ratio.value - step)
    event.preventDefault()
  }
  if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
    ratio.value = Math.min(0.8, ratio.value + step)
    event.preventDefault()
  }
}

provide(SDOC_SPLIT_KEY, {
  layout,
  setLayout,
})

watch(pickerOpen, (open) => { if (open) loadDocs() })
watch(primaryId, (id) => {
  if (!id) return
  if (layout.value !== 'single' && !paneB.value) paneB.value = id
})

onMounted(loadDocs)
onBeforeUnmount(onDragEnd)
</script>
