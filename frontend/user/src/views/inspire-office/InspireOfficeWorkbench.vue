<template>
  <div class="io-wb">
    <!-- 单行顶栏：返回 + 标签 + 分屏/打开/新建（压高度） -->
    <header class="io-wb__chrome" role="banner">
      <RouterLink class="io-wb__back" to="/inspire-office" title="返回文档库">
        <span aria-hidden="true">←</span>
      </RouterLink>

      <div ref="tabsScrollRef" class="io-wb__tabs-scroll" role="tablist" aria-label="已打开文档">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          type="button"
          role="tab"
          class="io-wb__tab"
          :class="{
            'is-active': tab.id === focusedId,
            'is-in-pane': isInLayout(tab.id),
          }"
          :aria-selected="tab.id === focusedId"
          :title="tab.title || '未命名'"
          @click="focusTab(tab.id)"
          @dblclick="closeTab(tab.id)"
        >
          <span class="io-wb__tab-type" :data-type="tab.documentType" aria-hidden="true">{{ typeMark(tab) }}</span>
          <span class="io-wb__tab-title">{{ tab.title || '未命名' }}</span>
          <span
            v-if="layout !== 'single' && tab.id === paneA"
            class="io-wb__tab-slot"
            title="左/上窗格"
          >A</span>
          <span
            v-if="layout !== 'single' && tab.id === paneB"
            class="io-wb__tab-slot is-b"
            title="右/下窗格"
          >B</span>
          <span
            class="io-wb__tab-close"
            role="button"
            tabindex="0"
            aria-label="关闭标签"
            @click.stop="closeTab(tab.id)"
            @keydown.enter.stop="closeTab(tab.id)"
          >×</span>
        </button>
        <button type="button" class="io-wb__tab-add" title="打开文档" aria-label="打开文档" @click="openPicker('add')">+</button>
      </div>

      <div class="io-wb__chrome-right">
        <div class="io-wb__split-group" role="group" aria-label="窗口布局">
          <button
            type="button"
            class="io-wb__tool is-icon"
            :class="{ 'is-active': layout === 'single' }"
            title="单屏"
            @click="setLayout('single')"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="5" width="16" height="14" rx="2" fill="none" stroke="currentColor" stroke-width="1.8"/></svg>
          </button>
          <button
            type="button"
            class="io-wb__tool is-icon"
            :class="{ 'is-active': layout === 'horizontal' }"
            title="左右分屏"
            @click="setLayout('horizontal')"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="3.5" y="5" width="7.5" height="14" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.8"/><rect x="13" y="5" width="7.5" height="14" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.8"/></svg>
          </button>
          <button
            type="button"
            class="io-wb__tool is-icon"
            :class="{ 'is-active': layout === 'vertical' }"
            title="上下分屏"
            @click="setLayout('vertical')"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true"><rect x="4" y="3.5" width="16" height="7" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.8"/><rect x="4" y="13.5" width="16" height="7" rx="1.5" fill="none" stroke="currentColor" stroke-width="1.8"/></svg>
          </button>
        </div>
        <button
          v-if="layout === 'single' && focusedId && focusedSupportsMarkup"
          type="button"
          class="io-wb__tool is-icon"
          :class="{ 'is-active': focusedMarkupVisible }"
          :title="focusedMarkupVisible ? '隐藏修订标记（颜色/下划线）' : '显示修订标记'"
          :aria-label="focusedMarkupVisible ? '隐藏修订标记' : '显示修订标记'"
          :aria-pressed="focusedMarkupVisible"
          @click="toggleFocusedMarkup"
        >
          <svg v-if="focusedMarkupVisible" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M4 17.5 14.2 7.3a2.1 2.1 0 0 1 3 0l.9.9a2.1 2.1 0 0 1 0 3L8 20.5H4v-3Z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/>
            <path d="M12.8 8.7 15.7 11.6" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" aria-hidden="true">
            <path d="M4 17.5 14.2 7.3a2.1 2.1 0 0 1 3 0l.9.9a2.1 2.1 0 0 1 0 3L8 20.5H4v-3Z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" opacity="0.55"/>
            <path d="M5 5 19 19" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
          </svg>
        </button>
        <button
          v-if="layout === 'single' && focusedId"
          type="button"
          class="io-wb__tool is-icon"
          :class="{ 'is-active': focusedVersionOpen }"
          :title="focusedVersionOpen ? '收起版本' : '版本存档'"
          :aria-label="focusedVersionOpen ? '收起版本' : '版本存档'"
          @click="toggleFocusedVersion"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="12" cy="12" r="8.2" fill="none" stroke="currentColor" stroke-width="1.7"/>
            <path d="M12 8.2v4.2l2.8 1.7" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
        <InspireOfficeShareBubble
          v-if="focusedId"
          :doc-id="focusedId"
          :inviter="auth.user?.username || ''"
          :title="focusedTab?.title || ''"
          :team-name="focusedTab?.teamName || ''"
          :scope="focusedTab?.scope || ''"
          :ext="focusedTab?.ext || ''"
          :type="focusedTab?.documentType || ''"
          trigger-class="io-wb__tool is-icon"
          trigger-title="分享邀请"
        />
        <button type="button" class="io-wb__tool is-primary is-compact" title="新建" @click="showCreate = true">新建</button>
      </div>
    </header>

    <!-- 编辑区 -->
    <div v-if="!tabs.length" class="io-wb__empty">
      <strong>还没有打开的文档</strong>
      <p>从文档库打开，或在此新建 / 选择已有文档。</p>
      <div class="io-wb__empty-actions">
        <button type="button" class="io-wb__tool is-primary" @click="showCreate = true">新建文档</button>
        <button type="button" class="io-wb__tool" @click="openPicker('add')">打开文档</button>
        <RouterLink class="io-wb__tool" to="/inspire-office">返回文档库</RouterLink>
      </div>
    </div>

    <div
      v-else
      class="io-wb__stage"
      :class="`is-${layout}`"
      :style="stageStyle"
    >
      <div
        class="io-wb__pane-wrap is-a"
        :class="{ 'is-focused': focusedId === paneA }"
        @pointerdown="focusedId = paneA; lastFocusedPane = 'a'"
      >
        <InspireOfficePane
          v-if="paneA"
          :ref="(el) => setPaneRef(paneA, el)"
          :key="`pane-a-${paneA}`"
          :document-id="paneA"
          :ext="tabById(paneA)?.ext || ''"
          :document-type="tabById(paneA)?.documentType || ''"
          :focused="focusedId === paneA"
          :visible="true"
          :show-bar="layout !== 'single'"
          @title="(t) => updateTabTitle(paneA, t)"
          @meta="(m) => updateTabMeta(paneA, m)"
        />
      </div>

      <div
        v-if="layout !== 'single'"
        class="io-wb__splitter"
        role="separator"
        :aria-orientation="layout === 'horizontal' ? 'vertical' : 'horizontal'"
        :aria-valuenow="Math.round(splitRatio * 100)"
        tabindex="0"
        @pointerdown="onSplitPointerDown"
        @keydown="onSplitKeydown"
      >
        <i></i>
      </div>

      <div
        v-if="layout !== 'single'"
        class="io-wb__pane-wrap is-b"
        :class="{ 'is-focused': focusedId === paneB }"
        @pointerdown="focusedId = paneB; lastFocusedPane = 'b'"
      >
        <InspireOfficePane
          v-if="paneB"
          :ref="(el) => setPaneRef(paneB, el)"
          :key="`pane-b-${paneB}`"
          :document-id="paneB"
          :ext="tabById(paneB)?.ext || ''"
          :document-type="tabById(paneB)?.documentType || ''"
          :focused="focusedId === paneB"
          :visible="true"
          :show-bar="true"
          @title="(t) => updateTabTitle(paneB, t)"
          @meta="(m) => updateTabMeta(paneB, m)"
        />
        <div v-else class="io-wb__pane-empty">
          <p>第二窗格为空</p>
          <button type="button" class="io-wb__tool is-primary" @click="openPicker('paneB')">选择文档</button>
        </div>
      </div>
    </div>

    <!-- 打开文档选择器 -->
    <div v-if="pickerOpen" class="io-wb-modal" role="dialog" aria-modal="true" @click.self="pickerOpen = false">
      <div class="io-wb-dialog">
        <header>
          <h2>{{ pickerMode === 'paneB' ? '为第二窗格选择文档' : '打开文档' }}</h2>
          <button type="button" class="io-wb__icon-x" aria-label="关闭" @click="pickerOpen = false">×</button>
        </header>
        <div class="io-wb-dialog__body">
          <input
            v-model="pickerKeyword"
            type="search"
            class="io-wb-dialog__search"
            placeholder="搜索标题"
            aria-label="搜索文档"
          />
          <div v-if="pickerLoading" class="io-wb-dialog__empty">加载中…</div>
          <ul v-else-if="pickerDocs.length" class="io-wb-dialog__list">
            <li v-for="doc in pickerDocs" :key="doc.id">
              <button type="button" @click="pickDoc(doc)">
                <span class="io-wb__tab-type" :data-type="doc.documentType || guessType(doc.ext)">{{ typeMark(doc) }}</span>
                <span>
                  <strong>{{ doc.title }}</strong>
                  <small>{{ guessTypeLabel(doc) }} · {{ doc.scope || '' }} · v{{ doc.version || 1 }}</small>
                </span>
              </button>
            </li>
          </ul>
          <div v-else class="io-wb-dialog__empty">没有可打开的文档</div>
        </div>
      </div>
    </div>

    <!-- 简易新建 -->
    <div v-if="showCreate" class="io-wb-modal" role="dialog" aria-modal="true" @click.self="showCreate = false">
      <div class="io-wb-dialog is-sm">
        <header>
          <h2>新建文档</h2>
          <button type="button" class="io-wb__icon-x" aria-label="关闭" @click="showCreate = false">×</button>
        </header>
        <div class="io-wb-dialog__body io-wb-create">
          <label>
            <span>标题</span>
            <input v-model="createForm.title" type="text" maxlength="200" placeholder="未命名文档" />
          </label>
          <div class="io-wb-create__types" role="radiogroup" aria-label="类型">
            <button
              v-for="opt in typeOptions"
              :key="opt.ext"
              type="button"
              :class="{ 'is-active': createForm.ext === opt.ext }"
              @click="createForm.ext = opt.ext"
            >
              <b :data-type="opt.type">{{ opt.mark }}</b>
              {{ opt.label }}
            </button>
          </div>
          <button type="button" class="io-wb__tool is-primary is-block" :disabled="createBusy" @click="createDoc">
            {{ createBusy ? '创建中…' : '创建并打开' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import InspireOfficePane from '../../components/inspire-office/InspireOfficePane.vue'
import {
  createBlankInspireOfficeDocument,
  listInspireOfficeDocuments,
} from '../../services/inspireOfficeClient'
import InspireOfficeShareBubble from '../../components/inspire-office/InspireOfficeShareBubble.vue'
import { useAuthStore } from '../../stores/auth'

const STORAGE_KEY = 'inspire-office-workbench-v1'
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const tabs = ref([])
const focusedId = ref(null)
const layout = ref('single') // single | horizontal | vertical
const paneA = ref(null)
const paneB = ref(null)
const splitRatio = ref(0.5)
/** 最近操作的窗格，用于点标签时替换到哪一侧 */
const lastFocusedPane = ref('a')

const pickerOpen = ref(false)
const pickerMode = ref('add') // add | paneB
const pickerLoading = ref(false)
const pickerKeyword = ref('')
const allDocs = ref([])
const showCreate = ref(false)
const createBusy = ref(false)
const createForm = reactive({ title: '', ext: 'docx' })
const typeOptions = [
  { ext: 'sdoc', label: '智能文档', mark: '智', type: 'sdoc' },
  { ext: 'docx', label: 'Word', mark: 'W', type: 'word' },
  { ext: 'xlsx', label: '表格', mark: 'X', type: 'sheet' },
  { ext: 'pptx', label: '演示', mark: 'P', type: 'slide' },
]

const tabsScrollRef = ref(null)
const paneRefMap = new Map()
/** 单屏时顶栏「版本」按钮的展开态 */
const focusedVersionOpen = ref(false)
/** 与窗格意图同步；默认 true（产品默认显示修订标记） */
const focusedMarkupVisible = ref(true)
let dragging = false
let markupPollTimer = 0

function setPaneRef(id, el) {
  if (!id) return
  if (el) paneRefMap.set(String(id), el)
  else paneRefMap.delete(String(id))
}

function syncFocusedVersionOpen() {
  const id = focusedId.value
  if (!id || layout.value !== 'single') {
    focusedVersionOpen.value = false
    return
  }
  const pane = paneRefMap.get(String(id))
  focusedVersionOpen.value = !!pane?.panelOpen
}

function syncFocusedMarkupVisible() {
  const id = focusedId.value
  if (!id) {
    focusedMarkupVisible.value = true
    return
  }
  const pane = paneRefMap.get(String(id))
  if (pane && typeof pane.markupVisible !== 'undefined') {
    focusedMarkupVisible.value = !!pane.markupVisible
  }
}

function startMarkupPoll() {
  stopMarkupPoll()
  // 打开后短时同步顶栏按钮（窗格 init 完成后会变 true）
  let n = 0
  markupPollTimer = window.setInterval(() => {
    syncFocusedMarkupVisible()
    n += 1
    if (n > 12) stopMarkupPoll()
  }, 400)
}

function stopMarkupPoll() {
  if (markupPollTimer) {
    clearInterval(markupPollTimer)
    markupPollTimer = 0
  }
}

function toggleFocusedVersion() {
  const id = focusedId.value
  if (!id) return
  const pane = paneRefMap.get(String(id))
  pane?.togglePanel?.()
  // 下一帧读 expose，确保 panelOpen 已翻转
  requestAnimationFrame(syncFocusedVersionOpen)
}

function toggleFocusedMarkup() {
  const id = focusedId.value
  if (!id) return
  const pane = paneRefMap.get(String(id))
  pane?.toggleMarkupVisible?.()
  requestAnimationFrame(syncFocusedMarkupVisible)
  window.setTimeout(syncFocusedMarkupVisible, 100)
  window.setTimeout(syncFocusedMarkupVisible, 350)
}

const focusedTab = computed(() => {
  const id = focusedId.value
  if (!id) return null
  return tabs.value.find((t) => String(t.id) === String(id)) || null
})

const focusedSupportsMarkup = computed(() => {
  const t = focusedTab.value
  if (!t) return false
  const kind = t.documentType || guessType(t.ext)
  return kind === 'word'
})

const pickerDocs = computed(() => {
  const q = pickerKeyword.value.trim().toLowerCase()
  let list = allDocs.value || []
  if (q) list = list.filter((d) => String(d.title || '').toLowerCase().includes(q))
  return list
})

const stageStyle = computed(() => {
  if (layout.value === 'horizontal') {
    return {
      gridTemplateColumns: `${splitRatio.value}fr 6px ${1 - splitRatio.value}fr`,
      gridTemplateRows: 'minmax(0, 1fr)',
    }
  }
  if (layout.value === 'vertical') {
    return {
      gridTemplateColumns: 'minmax(0, 1fr)',
      gridTemplateRows: `${splitRatio.value}fr 6px ${1 - splitRatio.value}fr`,
    }
  }
  return {
    gridTemplateColumns: 'minmax(0, 1fr)',
    gridTemplateRows: 'minmax(0, 1fr)',
  }
})

function guessType(ext) {
  const e = String(ext || '').replace(/^\./, '').toLowerCase()
  if (e === 'sdoc') return 'sdoc'
  if (['pptx', 'ppt', 'odp'].includes(e)) return 'slide'
  if (['xlsx', 'xls', 'ods', 'csv'].includes(e)) return 'sheet'
  return 'word'
}

function typeMark(doc) {
  const t = doc.documentType || guessType(doc.ext)
  return ({ word: 'W', sheet: 'X', slide: 'P', sdoc: '智' }[t] || 'D')
}

function guessTypeLabel(doc) {
  const t = doc.documentType || guessType(doc.ext)
  return ({ word: 'Word', sheet: '表格', slide: '演示', sdoc: '智能文档' }[t] || '文档')
}

function tabById(id) {
  return tabs.value.find((t) => String(t.id) === String(id)) || null
}

function isInLayout(id) {
  if (layout.value === 'single') return id === paneA.value
  return id === paneA.value || id === paneB.value
}

function persist() {
  try {
    sessionStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        tabs: tabs.value,
        focusedId: focusedId.value,
        layout: layout.value,
        paneA: paneA.value,
        paneB: paneB.value,
        splitRatio: splitRatio.value,
      })
    )
  } catch {
    // ignore
  }
}

function restore() {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY)
    if (!raw) return
    const data = JSON.parse(raw)
    if (Array.isArray(data.tabs)) tabs.value = data.tabs
    focusedId.value = data.focusedId || null
    layout.value = data.layout || 'single'
    paneA.value = data.paneA || null
    paneB.value = data.paneB || null
    splitRatio.value = typeof data.splitRatio === 'number' ? data.splitRatio : 0.5
  } catch {
    // ignore
  }
}

function openTab(doc, { focusPane = 'auto' } = {}) {
  const id = String(doc.id)
  const exists = tabs.value.find((t) => String(t.id) === id)
  if (!exists) {
    tabs.value.push({
      id,
      title: doc.title || '未命名',
      ext: doc.ext,
      documentType: doc.documentType || guessType(doc.ext),
    })
  } else if (doc.title) {
    exists.title = doc.title
  }

  focusedId.value = id
  if (layout.value === 'single' || focusPane === 'a') {
    paneA.value = id
    lastFocusedPane.value = 'a'
  } else if (focusPane === 'b') {
    paneB.value = id
    lastFocusedPane.value = 'b'
  } else if (!paneA.value) {
    paneA.value = id
    lastFocusedPane.value = 'a'
  } else if (layout.value !== 'single' && !paneB.value) {
    paneB.value = id
    lastFocusedPane.value = 'b'
  } else if (layout.value !== 'single' && lastFocusedPane.value === 'b') {
    paneB.value = id
  } else {
    paneA.value = id
    lastFocusedPane.value = 'a'
  }
  persist()
  // 第二窗格新开文档后，给两边各补一次修订显示（避免后开的把先开的状态搅乱）
  if (layout.value !== 'single') {
    nextTick(() => {
      ;[600, 1600, 3200].forEach((ms) => {
        window.setTimeout(() => ensureAllPanesMarkup(), ms)
      })
    })
  }
}

function focusTab(id) {
  focusedId.value = id
  if (layout.value === 'single') {
    paneA.value = id
    lastFocusedPane.value = 'a'
  } else if (id === paneA.value) {
    lastFocusedPane.value = 'a'
  } else if (id === paneB.value) {
    lastFocusedPane.value = 'b'
  } else if (lastFocusedPane.value === 'b') {
    paneB.value = id
  } else {
    paneA.value = id
  }
  persist()
}

function closeTab(id) {
  const idx = tabs.value.findIndex((t) => String(t.id) === String(id))
  if (idx < 0) return
  tabs.value.splice(idx, 1)
  if (paneA.value === id) paneA.value = tabs.value[0]?.id || null
  if (paneB.value === id) paneB.value = tabs.value.find((t) => t.id !== paneA.value)?.id || null
  if (focusedId.value === id) focusedId.value = paneA.value || paneB.value || null
  if (layout.value !== 'single' && (!paneA.value || !paneB.value)) {
    // 只剩一个时退回单屏
    if (tabs.value.length <= 1) {
      layout.value = 'single'
      paneA.value = tabs.value[0]?.id || null
      paneB.value = null
    }
  }
  persist()
  if (!tabs.value.length) {
    router.replace({ name: 'InspireOffice' })
  }
}

function setLayout(mode) {
  layout.value = mode
  if (mode === 'single') {
    paneA.value = focusedId.value || paneA.value || tabs.value[0]?.id || null
    paneB.value = null
  } else {
    if (!paneA.value) paneA.value = focusedId.value || tabs.value[0]?.id || null
    if (!paneB.value) {
      paneB.value = tabs.value.find((t) => t.id !== paneA.value)?.id || null
      if (!paneB.value) {
        ElMessage.info('请再打开一个文档到第二窗格（Word + PPT 等可并排查看）')
        openPicker('paneB')
      }
    }
  }
  persist()
  // 分屏后两个 iframe 可能互相干扰修订显示：对各窗格做安全补强
  nextTick(() => {
    ;[400, 1200, 2500].forEach((ms) => {
      window.setTimeout(() => ensureAllPanesMarkup(), ms)
    })
  })
}

/** 分屏/开第二文档后：让每个 Word 窗格修订标记保持显示 */
function ensureAllPanesMarkup() {
  paneRefMap.forEach((pane) => {
    try {
      pane?.ensureMarkupVisible?.()
    } catch {
      // ignore
    }
  })
}

function updateTabTitle(id, title) {
  const tab = tabs.value.find((t) => String(t.id) === String(id))
  if (tab && title) {
    tab.title = title
    persist()
  }
}

function updateTabMeta(id, meta) {
  const tab = tabs.value.find((t) => String(t.id) === String(id))
  if (!tab || !meta) return
  if (meta.title) tab.title = meta.title
  if (meta.ext) tab.ext = meta.ext
  if (meta.documentKind) tab.documentType = meta.documentKind
  else if (meta.ext) tab.documentType = guessType(meta.ext)
  if (meta.scope) tab.scope = meta.scope
  if (meta.teamName) tab.teamName = meta.teamName
  if (meta.teamId != null) tab.teamId = meta.teamId
  persist()
}

async function openPicker(mode) {
  pickerMode.value = mode
  pickerOpen.value = true
  pickerKeyword.value = ''
  pickerLoading.value = true
  try {
    allDocs.value = await listInspireOfficeDocuments({ scope: 'all' })
  } catch (e) {
    ElMessage.error(e?.message || '加载文档失败')
    allDocs.value = []
  } finally {
    pickerLoading.value = false
  }
}

function pickDoc(doc) {
  if (pickerMode.value === 'paneB') {
    openTab(doc, { focusPane: 'b' })
    focusedId.value = String(doc.id)
  } else {
    openTab(doc, { focusPane: 'auto' })
  }
  pickerOpen.value = false
}

async function createDoc() {
  createBusy.value = true
  try {
    const doc = await createBlankInspireOfficeDocument({
      title: createForm.title || undefined,
      ext: createForm.ext,
      scope: 'personal',
    })
    showCreate.value = false
    createForm.title = ''
    createForm.ext = 'docx'
    if (doc?.id) openTab(doc)
  } catch (e) {
    ElMessage.error(e?.message || '创建失败')
  } finally {
    createBusy.value = false
  }
}

function onSplitPointerDown(event) {
  dragging = true
  event.currentTarget.setPointerCapture?.(event.pointerId)
  window.addEventListener('pointermove', onSplitPointerMove)
  window.addEventListener('pointerup', onSplitPointerUp)
}

function onSplitPointerMove(event) {
  if (!dragging) return
  const stage = document.querySelector('.io-wb__stage')
  if (!stage) return
  const rect = stage.getBoundingClientRect()
  let ratio
  if (layout.value === 'horizontal') {
    ratio = (event.clientX - rect.left) / rect.width
  } else {
    ratio = (event.clientY - rect.top) / rect.height
  }
  splitRatio.value = Math.min(0.8, Math.max(0.2, ratio))
}

function onSplitPointerUp() {
  dragging = false
  window.removeEventListener('pointermove', onSplitPointerMove)
  window.removeEventListener('pointerup', onSplitPointerUp)
  persist()
}

function onSplitKeydown(event) {
  const step = event.shiftKey ? 0.08 : 0.04
  if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') {
    splitRatio.value = Math.max(0.2, splitRatio.value - step)
    persist()
    event.preventDefault()
  }
  if (event.key === 'ArrowRight' || event.key === 'ArrowDown') {
    splitRatio.value = Math.min(0.8, splitRatio.value + step)
    persist()
    event.preventDefault()
  }
}

onMounted(() => {
  restore()
  const routeId = route.params.id
  if (routeId) {
    openTab({
      id: String(routeId),
      title: route.query.title || '文档',
      ext: route.query.ext,
      documentType: route.query.type,
    })
    if (route.name === 'InspireOfficeEditor') {
      router.replace({
        name: 'InspireOfficeWorkbench',
        query: {
          focus: String(routeId),
          title: route.query.title,
          ext: route.query.ext,
          type: route.query.type,
        },
      })
    }
  } else if (route.query.focus) {
    const id = String(route.query.focus)
    if (!tabs.value.find((t) => String(t.id) === id)) {
      openTab({
        id,
        title: route.query.title || '文档',
        ext: route.query.ext,
        documentType: route.query.type,
      })
    } else {
      focusTab(id)
    }
  }
  if (!paneA.value && tabs.value[0]) paneA.value = tabs.value[0].id
  if (layout.value !== 'single' && !paneB.value) {
    paneB.value = tabs.value.find((t) => t.id !== paneA.value)?.id || null
  }
  if (!focusedId.value) focusedId.value = paneA.value
})

onBeforeUnmount(() => {
  onSplitPointerUp()
  stopMarkupPoll()
  persist()
})

watch(
  () => [tabs.value, focusedId.value, layout.value, paneA.value, paneB.value, splitRatio.value],
  () => persist(),
  { deep: true }
)

watch([focusedId, layout], () => {
  // 切标签/布局时同步顶栏按钮状态
  requestAnimationFrame(() => {
    syncFocusedVersionOpen()
    syncFocusedMarkupVisible()
    if (layout.value === 'single' && focusedSupportsMarkup.value) startMarkupPoll()
    else stopMarkupPoll()
  })
})
</script>

<style scoped>
.io-wb {
  --line: #e5e7eb;
  --ink: #111827;
  --muted: #6b7280;
  --accent: #e5481d;
  --chrome: #f3f4f6;
  --chrome-h: 32px;
  box-sizing: border-box;
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-rows: var(--chrome-h) minmax(0, 1fr);
  background: #e8eaed;
  overflow: hidden;
}

.io-wb__chrome {
  display: flex;
  align-items: center;
  gap: 4px;
  min-height: var(--chrome-h);
  height: var(--chrome-h);
  padding: 0 6px 0 4px;
  background: #fff;
  border-bottom: 1px solid var(--line);
}

.io-wb__chrome-right {
  display: flex;
  align-items: center;
  gap: 4px;
  flex: 0 0 auto;
  margin-left: auto;
}

.io-wb__back {
  flex: 0 0 auto;
  width: 26px;
  height: 26px;
  display: inline-grid;
  place-items: center;
  color: var(--muted);
  text-decoration: none;
  font-size: 13px;
  font-weight: 700;
  border-radius: 6px;
}

.io-wb__back:hover {
  background: #f3f4f6;
  color: var(--ink);
}

.io-wb__split-group {
  display: inline-flex;
  padding: 1px;
  border: 1px solid var(--line);
  border-radius: 6px;
  background: #f8fafc;
  gap: 0;
}

.io-wb__tool {
  appearance: none;
  border: 1px solid var(--line);
  background: #fff;
  color: var(--ink);
  border-radius: 6px;
  padding: 0 7px;
  min-height: 24px;
  font: 650 11px/1 inherit;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 3px;
  text-decoration: none;
}

.io-wb__tool.is-icon {
  width: 24px;
  min-height: 24px;
  padding: 0;
  justify-content: center;
  border: 0;
  background: transparent;
  border-radius: 5px;
}

/* 分享气泡触发器：scoped 样式需 :deep 才能作用到子组件内按钮 */
:deep(.io-share__trigger.io-wb__tool) {
  appearance: none;
  border: 1px solid var(--line);
  background: #fff;
  color: var(--ink);
  border-radius: 6px;
  padding: 0 7px;
  min-height: 24px;
  font: 650 11px/1 inherit;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  gap: 3px;
}
:deep(.io-share__trigger.io-wb__tool.is-icon) {
  width: 24px;
  min-height: 24px;
  padding: 0;
  justify-content: center;
  border: 0;
  background: transparent;
  border-radius: 5px;
}
:deep(.io-share__trigger.io-wb__tool.is-icon:hover) {
  background: #f3f4f6;
}
:deep(.io-share__trigger.io-wb__tool svg) {
  width: 13px;
  height: 13px;
}

.io-wb__tool svg {
  width: 12px;
  height: 12px;
}

.io-wb__split-group .io-wb__tool.is-icon.is-active {
  background: #fff;
  color: var(--accent);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}

.io-wb__tool:hover {
  background: #f3f4f6;
}

.io-wb__tool.is-active {
  color: var(--accent);
  border-color: color-mix(in srgb, var(--accent) 40%, var(--line));
  background: #fff7f3;
}

.io-wb__tool.is-primary {
  border-color: transparent;
  background: var(--accent);
  color: #fff;
  padding: 0 9px;
}

.io-wb__tool.is-compact {
  padding: 0 8px;
}

.io-wb__tool.is-block {
  width: 100%;
  justify-content: center;
  min-height: 36px;
}

.io-wb__tabs-scroll {
  flex: 1 1 auto;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 2px;
  overflow-x: auto;
  scrollbar-width: none;
  mask-image: linear-gradient(90deg, #000 0, #000 calc(100% - 12px), transparent);
}

.io-wb__tabs-scroll::-webkit-scrollbar {
  display: none;
}

.io-wb__tab {
  position: relative;
  flex: 0 1 auto;
  max-width: 140px;
  min-width: 64px;
  height: 24px;
  margin: 0;
  padding: 0 20px 0 6px;
  border: 1px solid transparent;
  border-radius: 6px;
  background: transparent;
  color: var(--muted);
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font: 650 11px/1 inherit;
  cursor: pointer;
}

.io-wb__tab:hover {
  background: #f3f4f6;
  color: var(--ink);
}

.io-wb__tab.is-active {
  background: #f3f4f6;
  color: var(--ink);
  border-color: var(--line);
}

.io-wb__tab-type {
  width: 15px;
  height: 15px;
  border-radius: 4px;
  display: grid;
  place-items: center;
  color: #fff;
  font-size: 9px;
  font-weight: 800;
  background: #64748b;
  flex: 0 0 auto;
}

.io-wb__tab-type[data-type='word'] { background: #2b579a; }
.io-wb__tab-type[data-type='sheet'] { background: #217346; }
.io-wb__tab-type[data-type='slide'] { background: #b7472a; }
.io-wb__tab-type[data-type='sdoc'] { background: #c43a12; }

.io-wb__tab-title {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.io-wb__tab-slot {
  flex: 0 0 auto;
  min-width: 14px;
  height: 14px;
  padding: 0 3px;
  border-radius: 3px;
  background: #e0e7ff;
  color: #3730a3;
  font-size: 9px;
  font-weight: 800;
  display: grid;
  place-items: center;
}

.io-wb__tab-slot.is-b {
  background: #ffedd5;
  color: #9a3412;
}

.io-wb__tab-close {
  position: absolute;
  top: 50%;
  right: 3px;
  width: 16px;
  height: 16px;
  margin-top: -8px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: var(--muted);
  font-size: 13px;
  line-height: 1;
}

.io-wb__tab-close:hover {
  background: #fee2e2;
  color: #b91c1c;
}

.io-wb__tab-add {
  flex: 0 0 24px;
  width: 24px;
  height: 24px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--muted);
  font-size: 15px;
  cursor: pointer;
  line-height: 1;
}

.io-wb__tab-add:hover {
  background: #f3f4f6;
  color: var(--ink);
}

.io-wb__stage {
  min-height: 0;
  padding: 0;
  display: grid;
  gap: 0;
  background: #e8eaed;
}

/* 分屏时留细缝，方便辨认窗格边界 */
.io-wb__stage.is-horizontal,
.io-wb__stage.is-vertical {
  padding: 3px;
  gap: 0;
}

.io-wb__pane-wrap {
  min-width: 0;
  min-height: 0;
  overflow: hidden;
}

/* 单屏贴满：去掉卡片边距，把高度全给 Collabora */
.io-wb__stage.is-single .io-wb__pane-wrap {
  border-radius: 0;
}

.io-wb__splitter {
  position: relative;
  z-index: 2;
  display: grid;
  place-items: center;
  background: transparent;
  touch-action: none;
  cursor: col-resize;
}

.io-wb__stage.is-vertical .io-wb__splitter {
  cursor: row-resize;
}

.io-wb__splitter i {
  display: block;
  border-radius: 99px;
  background: #cbd5e1;
}

.io-wb__stage.is-horizontal .io-wb__splitter i {
  width: 4px;
  height: 48px;
}

.io-wb__stage.is-vertical .io-wb__splitter i {
  width: 48px;
  height: 4px;
}

.io-wb__splitter:hover i,
.io-wb__splitter:focus-visible i {
  background: var(--accent);
}

.io-wb__pane-empty {
  height: 100%;
  display: grid;
  place-content: center;
  justify-items: center;
  gap: 12px;
  background: #fff;
  border: 1px dashed var(--line);
  border-radius: 10px;
  color: var(--muted);
  font-size: 13px;
}

.io-wb__empty {
  min-height: 0;
  display: grid;
  place-content: center;
  justify-items: center;
  gap: 8px;
  text-align: center;
  color: var(--ink);
}

.io-wb__empty p {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
}

.io-wb__empty-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  margin-top: 8px;
}

.io-wb-modal {
  position: fixed;
  inset: 0;
  z-index: 1200;
  background: rgba(15, 23, 42, 0.35);
  display: grid;
  place-items: center;
  padding: 16px;
}

.io-wb-dialog {
  width: min(520px, 100%);
  max-height: min(72vh, 640px);
  background: #fff;
  border-radius: 14px;
  box-shadow: 0 20px 50px rgba(15, 23, 42, 0.18);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.io-wb-dialog.is-sm {
  width: min(400px, 100%);
}

.io-wb-dialog header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 14px;
  border-bottom: 1px solid var(--line);
}

.io-wb-dialog h2 {
  margin: 0;
  font-size: 15px;
}

.io-wb__icon-x {
  border: 0;
  background: transparent;
  font-size: 20px;
  line-height: 1;
  color: var(--muted);
  cursor: pointer;
  width: 32px;
  height: 32px;
}

.io-wb-dialog__body {
  padding: 12px 14px 16px;
  overflow: auto;
  min-height: 0;
}

.io-wb-dialog__search {
  width: 100%;
  height: 36px;
  margin-bottom: 10px;
  border: 1px solid var(--line);
  border-radius: 9px;
  padding: 0 10px;
  font: inherit;
  font-size: 13px;
}

.io-wb-dialog__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 4px;
}

.io-wb-dialog__list button {
  width: 100%;
  border: 0;
  border-radius: 10px;
  padding: 10px;
  display: flex;
  align-items: center;
  gap: 10px;
  text-align: left;
  background: transparent;
  cursor: pointer;
  font: inherit;
}

.io-wb-dialog__list button:hover {
  background: #f3f4f6;
}

.io-wb-dialog__list strong {
  display: block;
  font-size: 13px;
}

.io-wb-dialog__list small {
  display: block;
  margin-top: 2px;
  color: var(--muted);
  font-size: 11px;
}

.io-wb-dialog__empty {
  padding: 28px 12px;
  text-align: center;
  color: var(--muted);
  font-size: 13px;
}

.io-wb-create {
  display: grid;
  gap: 12px;
}

.io-wb-create label {
  display: grid;
  gap: 6px;
  font-size: 12px;
  color: var(--muted);
}

.io-wb-create input {
  height: 36px;
  border: 1px solid var(--line);
  border-radius: 9px;
  padding: 0 10px;
  font: inherit;
  font-size: 13px;
}

.io-wb-create__types {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}

.io-wb-create__types button {
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #fff;
  padding: 10px 8px;
  display: grid;
  justify-items: center;
  gap: 6px;
  cursor: pointer;
  font: 650 12px/1 inherit;
}

.io-wb-create__types button.is-active {
  border-color: color-mix(in srgb, var(--accent) 50%, var(--line));
  background: #fff7f3;
}

.io-wb-create__types b {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  display: grid;
  place-items: center;
  color: #fff;
  background: #64748b;
}

.io-wb-create__types b[data-type='word'] { background: #2b579a; }
.io-wb-create__types b[data-type='sheet'] { background: #217346; }
.io-wb-create__types b[data-type='slide'] { background: #b7472a; }
.io-wb-create__types b[data-type='sdoc'] { background: #c43a12; }

@media (max-width: 720px) {
  .io-wb__chrome {
    padding: 0 6px;
  }
  .io-wb__tab {
    max-width: 110px;
    min-width: 64px;
  }
}
</style>
