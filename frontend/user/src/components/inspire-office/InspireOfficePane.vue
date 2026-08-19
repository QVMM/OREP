<template>
  <div class="io-pane" :class="{ 'is-focused': focused, 'is-barless': !showBar }">
    <header v-if="showBar" class="io-pane__bar">
      <div class="io-pane__title">
        <span class="io-pane__type" :data-type="documentType" aria-hidden="true">{{ typeMark }}</span>
        <strong>{{ title }}</strong>
        <small v-if="subtitle">{{ subtitle }}</small>
      </div>
      <div class="io-pane__actions">
        <button
          v-if="supportsTrackChanges"
          type="button"
          class="io-pane__btn is-icon"
          :class="{ 'is-active': markupVisible }"
          :title="markupVisible ? '隐藏修订标记（颜色/下划线）' : '显示修订标记'"
          :aria-label="markupVisible ? '隐藏修订标记' : '显示修订标记'"
          :aria-pressed="markupVisible"
          @click="toggleMarkupVisible"
        >
          <!-- 显示中：高亮笔迹；隐藏：斜线 -->
          <svg v-if="markupVisible" viewBox="0 0 24 24" aria-hidden="true">
            <path d="M4 17.5 14.2 7.3a2.1 2.1 0 0 1 3 0l.9.9a2.1 2.1 0 0 1 0 3L8 20.5H4v-3Z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round"/>
            <path d="M12.8 8.7 15.7 11.6" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round"/>
          </svg>
          <svg v-else viewBox="0 0 24 24" aria-hidden="true">
            <path d="M4 17.5 14.2 7.3a2.1 2.1 0 0 1 3 0l.9.9a2.1 2.1 0 0 1 0 3L8 20.5H4v-3Z" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linejoin="round" opacity="0.55"/>
            <path d="M5 5 19 19" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"/>
          </svg>
        </button>
        <InspireOfficeShareBubble
          :doc-id="documentId"
          :inviter="auth.user?.username || ''"
          :title="title || meta?.title || ''"
          :team-name="meta?.teamName || ''"
          :scope="meta?.scope || ''"
          :ext="meta?.ext || ''"
          :type="documentType"
          trigger-class="io-pane__btn is-icon"
          trigger-title="分享邀请"
        />
        <button
          type="button"
          class="io-pane__btn is-icon"
          :class="{ 'is-active': panelOpen }"
          :title="panelOpen ? '收起版本' : '版本存档'"
          :aria-label="panelOpen ? '收起版本' : '版本存档'"
          @click="togglePanel"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <circle cx="12" cy="12" r="8.2" fill="none" stroke="currentColor" stroke-width="1.7"/>
            <path d="M12 8.2v4.2l2.8 1.7" fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </button>
      </div>
    </header>

    <div class="io-pane__body">
      <div class="io-pane__stage">
        <div v-if="!isSmartDoc && loading" class="io-pane__state" role="status">
          <div class="io-pane__spinner" aria-hidden="true" />
          <span>正在打开…</span>
        </div>
        <div v-else-if="!isSmartDoc && error" class="io-pane__state is-error" role="alert">
          <strong>无法打开</strong>
          <p>{{ error }}</p>
          <button type="button" class="io-pane__btn is-primary" @click="loadEditor">重试</button>
        </div>
        <SdocStudentHost v-if="isSmartDoc">
          <SmartDocEditor
            :key="`sdoc-${documentId}-${sdocEpoch}`"
            ref="sdocRef"
            :document-id="documentId"
            embedded
            class="io-pane__sdoc"
            @title="onSmartTitle"
            @meta="onSmartMeta"
          />
        </SdocStudentHost>
        <iframe
          v-else-if="!loading && !error"
          ref="frame"
          class="io-pane__frame"
          :title="title || '启发 Office 编辑器'"
          allow="fullscreen; clipboard-read; clipboard-write"
          @load="onFrameLoad"
        />
      </div>

      <aside v-if="panelOpen" class="io-pane__history" aria-label="版本存档">
        <div class="io-pane__history-head">
          <strong>版本</strong>
          <button type="button" class="io-pane__btn is-ghost" :disabled="historyLoading" @click="refreshHistory">
            刷新
          </button>
        </div>
        <p class="io-pane__hint" v-html="historyHintHtml"></p>
        <div class="io-pane__history-toolbar">
          <input
            v-model="snapshotLabel"
            type="text"
            maxlength="80"
            :placeholder="snapshotPlaceholder"
            class="io-pane__input"
          />
          <button type="button" class="io-pane__btn is-primary" :disabled="snapshotting" @click="doSnapshot">
            {{ snapshotting ? '…' : '存档' }}
          </button>
        </div>
        <ul v-if="versions.length" class="io-pane__versions">
          <li v-for="v in versions" :key="v.id || v.versionNo">
            <div>
              <strong>v{{ v.versionNo }}</strong>
              <span>{{ v.sourceLabel || v.source }}</span>
              <small>{{ formatTime(v.createdAt) }}</small>
            </div>
            <button
              type="button"
              class="io-pane__btn is-ghost is-sm"
              :disabled="restoring === v.versionNo"
              @click="doRestore(v)"
            >
              {{ restoring === v.versionNo ? '…' : '恢复' }}
            </button>
          </li>
        </ul>
        <p v-else class="io-pane__empty">{{ historyLoading ? '加载中…' : '暂无版本' }}</p>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createInspireOfficeSnapshot,
  fetchInspireOfficeEditorSession,
  fetchSmartDoc,
  listInspireOfficeVersions,
  reportInspireOfficePresence,
  restoreInspireOfficeVersion,
} from '../../services/inspireOfficeClient'
import { useAuthStore } from '../../stores/auth'
import InspireOfficeShareBubble from './InspireOfficeShareBubble.vue'
import SmartDocEditor from '../../views/inspire-office/smart-doc/SmartDocEditor.vue'
import SdocStudentHost from '../../views/inspire-office/smart-doc/SdocStudentHost.vue'

const props = defineProps({
  documentId: { type: [String, Number], required: true },
  ext: { type: String, default: '' },
  documentType: { type: String, default: '' },
  /** 是否为当前焦点窗格（分屏时仅焦点窗格计编辑活跃） */
  focused: { type: Boolean, default: true },
  /** 是否挂在可见布局中（隐藏标签不卸载时传 false 暂停计时） */
  visible: { type: Boolean, default: true },
  /** 单屏时由工作台顶栏承担标题，可隐藏本条以省高度 */
  showBar: { type: Boolean, default: true },
})

const emit = defineEmits(['meta', 'title'])
const auth = useAuthStore()

const loading = ref(true)
const error = ref('')
const title = ref('文档编辑')
const meta = ref(null)
const frame = ref(null)
const panelOpen = ref(false)
/**
 * Word 修订标记显示意图（按钮态）。
 * 产品默认：显示标记。读不到编辑器状态时以本值为准。
 */
const markupVisible = ref(true)
/** 用户是否手动切换过（此后不再自动 ensure） */
const markupUserToggled = ref(false)
const versions = ref([])
const historyLoading = ref(false)
const snapshotLabel = ref('')
const snapshotting = ref(false)
const restoring = ref(null)

let editorReadyArmed = false
let collaboraOrigin = ''
let readyTimers = []
let markupInitTimers = []
/** 已确认编辑器处于「显示修订」 */
let markupInitDone = false
/** 读不到状态时是否已盲发过一次 toggle（分屏多窗格时绝不可多发） */
let markupBlindSendDone = false
/** 当前文档是否已走过 Document_Loaded 主流程（防重复 reset） */
let documentFullyReady = false
/** 是否已隐藏 Help 页签 */
let helpTabHidden = false
/** Host_PostmessageReady 是否已发 */
let hostPostMessageReadySent = false
const presenceSessionId = globalThis.crypto?.randomUUID?.()
  || `io_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`
let presenceTimer = 0
let lastPresenceActiveAt = Date.now()
let lastEditActiveAt = 0
let pageVisible = typeof document === 'undefined' ? true : !document.hidden

const probedSmart = ref(null)
const sdocEpoch = ref(0)
const sdocRef = ref(null)

const isSmartDoc = computed(() => {
  if (probedSmart.value === true) return true
  if (probedSmart.value === false) return false
  const e = String(props.ext || meta.value?.ext || '').replace(/^\./, '').toLowerCase()
  const t = String(props.documentType || meta.value?.documentKind || '').toLowerCase()
  return e === 'sdoc' || t === 'sdoc'
})

const documentType = computed(() => {
  if (isSmartDoc.value) return 'sdoc'
  if (meta.value?.documentKind) return meta.value.documentKind
  const e = String(meta.value?.ext || props.ext || '').replace(/^\./, '').toLowerCase()
  if (['pptx', 'ppt', 'odp'].includes(e)) return 'slide'
  if (['xlsx', 'xls', 'ods', 'csv'].includes(e)) return 'sheet'
  if (e === 'sdoc') return 'sdoc'
  return 'word'
})

const typeMark = computed(() => ({ word: 'W', sheet: 'X', slide: 'P', sdoc: '智' }[documentType.value] || 'D'))

const isPresentation = computed(() => documentType.value === 'slide')
const supportsTrackChanges = computed(() => {
  if (meta.value?.supportsTrackChanges != null) return !!meta.value.supportsTrackChanges
  return documentType.value === 'word'
})

const subtitle = computed(() => {
  if (!meta.value) return ''
  const scopeMap = { personal: '个人', project: '项目', team: '团队' }
  const scope = scopeMap[meta.value.scope] || meta.value.scope || ''
  const ext = meta.value.ext ? String(meta.value.ext).replace(/^\./, '') : ''
  const ver = meta.value.version != null ? `v${meta.value.version}` : ''
  return [scope, ext, ver].filter(Boolean).join(' · ')
})

const historyHintHtml = computed(() => {
  if (isPresentation.value) return '演示无修订痕迹。自动保存会生成版本；重要节点可手动存档。'
  if (supportsTrackChanges.value) return 'Word 修订写在文件内。此处是整文件版本存档与恢复。'
  return '协同保存会自动快照；重要节点可手动存档。'
})

const snapshotPlaceholder = computed(() => (isPresentation.value ? '备注，如：终稿前' : '备注（可选）'))

function formatTime(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return String(value).replace('T', ' ').slice(0, 19)
  return d.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function togglePanel() {
  panelOpen.value = !panelOpen.value
  if (panelOpen.value) refreshHistory()
}

/**
 * 将修订标记设为显示/隐藏（只影响视图）。
 * - 能读到编辑器状态：仅在不一致时 toggle 一次
 * - 读不到：按本地意图更新按钮；盲发最多一次
 */
function setMarkupVisible(next) {
  if (!supportsTrackChanges.value) return false
  const want = !!next
  const ok = applyTrackedMarkupVisible(want)
  markupVisible.value = want
  window.setTimeout(() => {
    const actual = readTrackedMarkupVisible()
    if (actual != null) markupVisible.value = actual
  }, 280)
  return ok
}

function toggleMarkupVisible() {
  if (!supportsTrackChanges.value) {
    ElMessage.warning('当前文档不支持修订标记显示切换')
    return
  }
  markupUserToggled.value = true
  const actual = readTrackedMarkupVisible()
  const current = actual != null ? actual : markupVisible.value
  const want = !current
  // 用户手动切换允许再发 UNO（不受 blind 限制）
  markupBlindSendDone = false
  const ok = setMarkupVisible(want)
  ElMessage({
    type: ok === false ? 'warning' : 'success',
    message: ok === false
      ? '未能切换修订显示，请稍后重试'
      : (want ? '已显示修订标记' : '已隐藏修订标记'),
    duration: 1800,
    customClass: 'io-share-toast',
    offset: 56,
  })
}

/** 供工作台分屏后调用：在需要显示时把本窗格修订标记补上 */
function ensureMarkupVisible() {
  if (!supportsTrackChanges.value || markupUserToggled.value) return
  if (!markupVisible.value) return
  ensureMarkupVisibleSafe()
}

defineExpose({
  togglePanel,
  toggleMarkupVisible,
  setMarkupVisible,
  ensureMarkupVisible,
  get panelOpen() {
    return panelOpen.value
  },
  get markupVisible() {
    return markupVisible.value
  },
  get supportsTrackChanges() {
    return supportsTrackChanges.value
  },
})

async function refreshHistory() {
  if (!props.documentId) return
  historyLoading.value = true
  try {
    versions.value = await listInspireOfficeVersions(props.documentId)
  } catch (e) {
    ElMessage.error(e?.message || '加载版本失败')
  } finally {
    historyLoading.value = false
  }
}

async function doSnapshot() {
  if (!props.documentId) return
  snapshotting.value = true
  try {
    await sdocRef.value?.flushSave?.()
    await createInspireOfficeSnapshot(props.documentId, snapshotLabel.value || undefined)
    snapshotLabel.value = ''
    ElMessage.success('已存档')
    await refreshHistory()
  } catch (e) {
    ElMessage.error(e?.message || '存档失败')
  } finally {
    snapshotting.value = false
  }
}

async function doRestore(v) {
  try {
    await ElMessageBox.confirm(
      `将当前文档恢复为 v${v.versionNo}？会生成新版本。恢复后将重新加载编辑器。`,
      '恢复版本',
      { type: 'warning', confirmButtonText: '恢复', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  restoring.value = v.versionNo
  try {
    await restoreInspireOfficeVersion(props.documentId, v.versionNo)
    ElMessage.success(`已恢复至 v${v.versionNo}`)
    await refreshHistory()
    if (isSmartDoc.value) {
      sdocEpoch.value += 1
      return
    }
    await loadEditor()
  } catch (e) {
    ElMessage.error(e?.message || '恢复失败')
  } finally {
    restoring.value = null
  }
}

function postToCollabora(message) {
  const win = frame.value?.contentWindow
  if (!win) return
  const target = collaboraOrigin || '*'
  try {
    win.postMessage(JSON.stringify(message), target)
  } catch {
    try {
      win.postMessage(JSON.stringify(message), '*')
    } catch {
      // ignore
    }
  }
}

/** 读取 Collabora 当前是否显示修订标记；无法读取时返回 null */
function readTrackedMarkupVisible() {
  try {
    const win = frame.value?.contentWindow
    const handler = win?.app?.map?.stateChangeHandler
    if (!handler?.getItemValue) return null
    const v = handler.getItemValue('.uno:ShowTrackedChanges')
    if (v === 'true' || v === true) return true
    if (v === 'false' || v === false || v === '' || v == null) return false
    // 其它字符串按布尔语义
    return String(v).toLowerCase() === 'true'
  } catch {
    // 跨域等
  }
  return null
}

function sendShowTrackedChangesUno() {
  const win = frame.value?.contentWindow
  if (!win) return false

  // 1) 同源 sendUnoCommand（最可靠）
  try {
    const map = win.app?.map
    if (map && typeof map.sendUnoCommand === 'function') {
      map.sendUnoCommand('.uno:ShowTrackedChanges')
      return true
    }
  } catch {
    // continue
  }

  // 2) 同源 socket
  try {
    if (typeof win.app?.socket?.sendMessage === 'function') {
      win.app.socket.sendMessage('uno .uno:ShowTrackedChanges')
      return true
    }
  } catch {
    // continue
  }

  // 3) postMessage API
  postToCollabora({
    MessageId: 'Send_UNO_Command',
    SendTime: Date.now(),
    Values: { Command: '.uno:ShowTrackedChanges' },
  })
  return true
}

/**
 * 把修订标记设为显示/隐藏。
 * ShowTrackedChanges 是 toggle：
 * - 能读状态：仅不一致时发
 * - 读不到：全会话最多盲发一次（防分屏双窗格连环 toggle）
 */
function applyTrackedMarkupVisible(wantShow) {
  const win = frame.value?.contentWindow
  if (!win) return false

  const cur = readTrackedMarkupVisible()
  if (cur === wantShow) return true

  if (cur === true || cur === false) {
    return sendShowTrackedChangesUno()
  }

  // cur === null
  if (markupBlindSendDone) return true
  markupBlindSendDone = true
  return sendShowTrackedChangesUno()
}

/**
 * 安全 ensure「显示修订」：
 * - 已是 true：标记完成
 * - 明确 false：toggle 一次打开
 * - 读不到：最多盲发一次
 * 绝不会在已是 true 时再 toggle。
 */
function ensureMarkupVisibleSafe() {
  if (!supportsTrackChanges.value || markupUserToggled.value) return
  if (!editorReadyArmed || !frame.value?.contentWindow) return

  const cur = readTrackedMarkupVisible()
  if (cur === true) {
    markupVisible.value = true
    markupInitDone = true
    return
  }
  if (cur === false) {
    sendShowTrackedChangesUno()
    markupVisible.value = true
    // 短暂后再确认
    markupInitTimers.push(setTimeout(() => {
      if (markupUserToggled.value) return
      const after = readTrackedMarkupVisible()
      if (after === true) {
        markupVisible.value = true
        markupInitDone = true
      } else if (after === false) {
        // 仍关：再补一枪（仍是「从 false→true」，不会在 true 上误关）
        sendShowTrackedChangesUno()
        markupVisible.value = true
      }
    }, 350))
    return
  }
  // null：编辑器未就绪或跨域读不到
  if (!markupBlindSendDone) {
    markupBlindSendDone = true
    sendShowTrackedChangesUno()
  }
  markupVisible.value = true
}

function scheduleMarkupEnsure() {
  if (!supportsTrackChanges.value || markupUserToggled.value) return
  // 只清 markup 定时器，不影响 toolbar 定时器
  markupInitTimers.forEach((t) => clearTimeout(t))
  markupInitTimers = []
  // 分阶段探测：每阶段只在「确认关闭」时 toggle，避免闪烁
  ;[600, 1400, 2800, 4500].forEach((ms) => {
    markupInitTimers.push(setTimeout(() => {
      if (markupInitDone && readTrackedMarkupVisible() === true) return
      ensureMarkupVisibleSafe()
    }, ms))
  })
}

function hideCollaboraHelpTab() {
  // 只隐藏一次。重复 Hide_NotebookTab 会触发
  // notebookbar.refreshContextTabsVisibility is not a function
  if (helpTabHidden) return
  helpTabHidden = true
  postToCollabora({
    MessageId: 'Hide_NotebookTab',
    SendTime: Date.now(),
    Values: { id: 'Help' },
  })
}

function clearReadyTimers() {
  readyTimers.forEach((t) => clearTimeout(t))
  readyTimers = []
  markupInitTimers.forEach((t) => clearTimeout(t))
  markupInitTimers = []
}

function forceShowCollaboraToolbar() {
  try {
    const win = frame.value?.contentWindow
    const doc = frame.value?.contentDocument
    if (!doc) return
    const row = doc.getElementById('toolbar-row')
    if (row) {
      row.style.removeProperty('display')
      row.style.setProperty('display', 'block', 'important')
      row.style.setProperty('visibility', 'visible', 'important')
      row.style.setProperty('height', '82px', 'important')
    }
    doc.getElementById('document-container')?.classList?.remove('tabs-collapsed')
    const prefs = win?.prefs || win?.app?.prefs
    if (prefs && typeof prefs.set === 'function') {
      try {
        prefs.set('text.ShowToolbar', true)
        prefs.set('spreadsheet.ShowToolbar', true)
        prefs.set('presentation.ShowToolbar', true)
      } catch {
        // ignore
      }
    }
    const ui = win?.app?.map?.uiManager
    if (ui) {
      try {
        ui._notebookbarShouldBeCollapsed = false
      } catch {
        // ignore
      }
      if (typeof ui.extendNotebookbar === 'function') ui.extendNotebookbar()
    }
    injectCollaboraAvatarStyles(doc)
  } catch {
    // ignore
  }
}

/** Collabora 默认头像描边偏粗、偏深；压细、变浅，避免「厚圈 + 内空白」 */
function injectCollaboraAvatarStyles(doc) {
  if (!doc?.head) return
  const id = 'orep-io-avatar-styles'
  if (doc.getElementById(id)) return
  const style = doc.createElement('style')
  style.id = id
  style.textContent = `
    /* 工具栏跟随头像 / 用户列表 */
    .avatar-img,
    img.avatar-img,
    #userListHeader .avatar,
    #userListHeader img,
    .user-list-item .avatar-img,
    .user-list-item img.avatar-img,
    .main-nav .avatar,
    .main-nav img[class*="avatar"],
    .jsdialog img.avatar-img,
    .ui-user .avatar-img {
      border-width: 1px !important;
      box-shadow: none !important;
      outline: none !important;
    }
    /* 跟随/选中态描边：细 + 浅灰蓝，去掉厚蓝圈感 */
    .avatar-img[style*="border"],
    .selected-user .avatar-img,
    .following .avatar-img,
    #userListHeader .avatar-img {
      border-color: #b8c0cc !important;
    }
  `
  doc.head.appendChild(style)
}

function onDocumentReady() {
  forceShowCollaboraToolbar()
  hideCollaboraHelpTab()

  // 同一文档多次 Document_Loaded / Initialized：不要 clear 掉已有 ensure，不要重置状态
  if (!documentFullyReady) {
    documentFullyReady = true
    ;[700, 2000].forEach((ms) => {
      readyTimers.push(setTimeout(() => forceShowCollaboraToolbar(), ms))
    })
    if (supportsTrackChanges.value) {
      markupVisible.value = true
      // 不重置 markupUserToggled：仅 loadEditor 时重置
      markupInitDone = false
      markupBlindSendDone = false
      scheduleMarkupEnsure()
    }
  } else if (supportsTrackChanges.value && !markupUserToggled.value && markupVisible.value) {
    // 后续 ready 信号：只做安全补强（已是显示则不动）
    ensureMarkupVisibleSafe()
  }
}

function isCollaboraOrigin(origin) {
  if (!origin) return false
  if (collaboraOrigin && origin === collaboraOrigin) return true
  const o = String(origin)
  return o.includes('9980') || o.includes('collabora') || o === window.location.origin
}

function onCollaboraMessage(event) {
  if (!editorReadyArmed || !props.visible) return
  // 分屏关键：同源双 iframe 会互相收到对方 postMessage，必须按 source 过滤
  const myWin = frame.value?.contentWindow
  if (myWin && event.source && event.source !== myWin) return
  if (!isCollaboraOrigin(event.origin)) return
  let data = event.data
  if (typeof data === 'string') {
    try {
      data = JSON.parse(data)
    } catch {
      return
    }
  }
  if (!data || !data.MessageId) return
  markPresenceActive()
  if (isEditSignalMessage(data.MessageId, data.Values)) markEditActive()
  if (data.MessageId === 'App_LoadingStatus') {
    const status = data.Values?.Status || data.Values?.status
    if (status === 'Document_Loaded' || status === 'Initialized') {
      onDocumentReady()
      markPresenceActive()
      startPresenceTracking()
    }
  }
}

function isEditSignalMessage(messageId, values) {
  const id = String(messageId || '')
  if (['Doc_ModifiedStatus', 'Action_Save', 'Action_SaveAs', 'Action_Save_Resp', 'UI_SaveAs'].includes(id)) {
    return true
  }
  if (/Modified/i.test(id)) return true
  if (values && (values.Modified === true || values.modified === true || values.Status === 'Modified')) {
    return true
  }
  return false
}

function markPresenceActive() {
  lastPresenceActiveAt = Date.now()
}
function markEditActive() {
  lastEditActiveAt = Date.now()
  lastPresenceActiveAt = Date.now()
}
function handlePresenceVisibility() {
  pageVisible = !document.hidden
  if (pageVisible) markPresenceActive()
}
function isPresenceActive() {
  return Date.now() - lastPresenceActiveAt < 120000
}
function isEditingActive() {
  return lastEditActiveAt > 0 && Date.now() - lastEditActiveAt < 90000
}

async function flushPresence(force = false) {
  if (!props.documentId || !props.visible || loading.value || error.value) return
  const visible = pageVisible && props.visible
  const active = isPresenceActive() && props.focused
  const editing = isEditingActive() && props.focused
  if (!force && (!visible || !active)) return
  try {
    await reportInspireOfficePresence(props.documentId, {
      sessionId: presenceSessionId,
      visible,
      active: active || force,
      editing: editing || false,
      reset: false,
    })
  } catch {
    // ignore
  }
}

function startPresenceTracking() {
  stopPresenceTracking()
  if (!props.documentId || !props.visible) return
  markPresenceActive()
  flushPresence(true).catch(() => {})
  presenceTimer = window.setInterval(() => {
    flushPresence(false).catch(() => {})
  }, 15000)
}

function stopPresenceTracking() {
  if (presenceTimer) {
    window.clearInterval(presenceTimer)
    presenceTimer = 0
  }
}

function handlePageHide() {
  flushPresence(true).catch(() => {})
}

function onFrameLoad() {
  if (hostPostMessageReadySent) return
  hostPostMessageReadySent = true
  postToCollabora({ MessageId: 'Host_PostmessageReady' })
}

function onSmartTitle(next) {
  if (!next) return
  title.value = next
  emit('title', next)
}

function onSmartMeta(payload) {
  if (!payload) return
  meta.value = { ...(meta.value || {}), ...payload, ext: 'sdoc', documentKind: 'sdoc' }
  if (payload.title) title.value = payload.title
  emit('meta', meta.value)
  emit('title', title.value)
}

async function resolveSmartDoc() {
  const e = String(props.ext || '').replace(/^\./, '').toLowerCase()
  const t = String(props.documentType || '').toLowerCase()
  if (e === 'sdoc' || t === 'sdoc') {
    probedSmart.value = true
    return true
  }
  if (e && e !== 'sdoc') {
    probedSmart.value = false
    return false
  }
  try {
    await fetchSmartDoc(props.documentId, { silent: true })
    probedSmart.value = true
    return true
  } catch {
    probedSmart.value = false
    return false
  }
}

async function bootPane() {
  const smart = await resolveSmartDoc()
  if (smart) {
    loading.value = false
    error.value = ''
    title.value = title.value || '智能文档'
    emit('meta', { ext: 'sdoc', documentKind: 'sdoc', title: title.value })
    return
  }
  await loadEditor()
}

async function loadEditor() {
  if (isSmartDoc.value) return
  loading.value = true
  error.value = ''
  editorReadyArmed = false
  clearReadyTimers()
  markupVisible.value = true
  markupUserToggled.value = false
  markupInitDone = false
  markupBlindSendDone = false
  documentFullyReady = false
  helpTabHidden = false
  hostPostMessageReadySent = false
  const id = props.documentId
  if (!id) {
    error.value = '缺少文档 ID'
    loading.value = false
    return
  }
  try {
    const payload = await fetchInspireOfficeEditorSession(id, 'edit')
    meta.value = payload
    title.value = payload?.title || '文档编辑'
    emit('meta', payload)
    emit('title', title.value)
    if (!payload?.editorUrl) throw new Error('未返回编辑地址')
    try {
      collaboraOrigin = new URL(payload.editorUrl).origin
    } catch {
      collaboraOrigin = ''
    }
    editorReadyArmed = true
    await Promise.resolve()
    if (frame.value) frame.value.src = payload.editorUrl
    markPresenceActive()
    startPresenceTracking()
    if (panelOpen.value) await refreshHistory()
  } catch (e) {
    error.value = e?.message || '打开编辑器失败'
    stopPresenceTracking()
  } finally {
    loading.value = false
  }
}

watch(
  () => props.documentId,
  () => {
    probedSmart.value = null
    bootPane()
  }
)

// 分屏切焦点 / 重新可见时：若用户要显示修订，安全补强本窗格（不会误关）
watch(
  () => [props.focused, props.visible],
  ([focused, visible]) => {
    if (!focused || !visible) return
    if (!supportsTrackChanges.value || markupUserToggled.value) return
    if (!markupVisible.value) return
    window.setTimeout(() => ensureMarkupVisibleSafe(), 200)
  }
)

watch(
  () => props.visible,
  (v) => {
    if (v) startPresenceTracking()
    else {
      flushPresence(true).catch(() => {})
      stopPresenceTracking()
    }
  }
)

onMounted(() => {
  window.addEventListener('message', onCollaboraMessage)
  document.addEventListener('visibilitychange', handlePresenceVisibility)
  window.addEventListener('pagehide', handlePageHide)
  window.addEventListener('beforeunload', handlePageHide)
  bootPane()
})

onBeforeUnmount(() => {
  flushPresence(true).catch(() => {})
  stopPresenceTracking()
  window.removeEventListener('message', onCollaboraMessage)
  document.removeEventListener('visibilitychange', handlePresenceVisibility)
  window.removeEventListener('pagehide', handlePageHide)
  window.removeEventListener('beforeunload', handlePageHide)
  editorReadyArmed = false
  clearReadyTimers()
})
</script>

<style scoped>
.io-pane {
  --line: #e8eaed;
  --ink: #111827;
  --muted: #6b7280;
  --accent: #e5481d;
  height: 100%;
  min-height: 0;
  min-width: 0;
  display: flex;
  flex-direction: column;
  background: #f4f5f7;
  border: 1px solid var(--line);
  border-radius: 8px;
  overflow: hidden;
}

/* 单屏：工作台顶栏已有标签，去掉窗格描边/圆角，编辑区贴满 */
.io-pane.is-barless {
  border: 0;
  border-radius: 0;
  box-shadow: none;
  background: #dfe3e8;
}

.io-pane.is-focused:not(.is-barless) {
  border-color: #9ca3af;
  box-shadow: 0 0 0 1px rgba(156, 163, 175, 0.35);
}

/* 分屏时的细标题条（单屏整条隐藏） */
.io-pane__bar {
  flex: 0 0 auto;
  min-height: 28px;
  height: 28px;
  padding: 0 6px 0 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 6px;
  background: #fff;
  border-bottom: 1px solid var(--line);
}

.io-pane__title {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.io-pane__type {
  flex: 0 0 auto;
  width: 16px;
  height: 16px;
  border-radius: 4px;
  display: grid;
  place-items: center;
  color: #fff;
  font-size: 9px;
  font-weight: 800;
  background: #64748b;
}

.io-pane__type[data-type='word'] { background: #2b579a; }
.io-pane__type[data-type='sheet'] { background: #217346; }
.io-pane__type[data-type='slide'] { background: #b7472a; }
.io-pane__type[data-type='sdoc'] { background: #c43a12; }

.io-pane__sdoc {
  width: 100%;
  height: 100%;
  min-height: 0;
  background: #fff;
}

.io-pane__title strong {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
  font-weight: 700;
  color: var(--ink);
}

.io-pane__title small {
  flex: 0 0 auto;
  color: var(--muted);
  font-size: 10px;
  white-space: nowrap;
}

.io-pane__actions {
  flex: 0 0 auto;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.io-pane__btn {
  appearance: none;
  border: 1px solid var(--line);
  background: #fff;
  color: var(--ink);
  border-radius: 6px;
  padding: 3px 8px;
  min-height: 22px;
  font: 650 11px/1 inherit;
  cursor: pointer;
}

.io-pane__btn.is-icon {
  width: 22px;
  min-height: 22px;
  padding: 0;
  display: inline-grid;
  place-items: center;
  border-color: transparent;
  background: transparent;
}

.io-pane__btn.is-icon svg {
  width: 13px;
  height: 13px;
  display: block;
}

:deep(.io-share__trigger.io-pane__btn) {
  appearance: none;
  border: 1px solid transparent;
  background: transparent;
  color: var(--ink);
  border-radius: 6px;
  width: 22px;
  min-height: 22px;
  padding: 0;
  display: inline-grid;
  place-items: center;
  cursor: pointer;
  font: 650 11px/1 inherit;
}
:deep(.io-share__trigger.io-pane__btn:hover) {
  background: #f8fafc;
}
:deep(.io-share__trigger.io-pane__btn svg) {
  width: 13px;
  height: 13px;
  display: block;
}

.io-pane__btn:hover:not(:disabled) { background: #f8fafc; }
.io-pane__btn:disabled { opacity: 0.5; cursor: not-allowed; }
.io-pane__btn.is-active {
  border-color: color-mix(in srgb, var(--accent) 45%, var(--line));
  color: var(--accent);
}
.io-pane__btn.is-icon.is-active {
  background: #fff7f3;
  border-color: color-mix(in srgb, var(--accent) 35%, var(--line));
}
.io-pane__btn.is-primary {
  border-color: transparent;
  background: var(--accent);
  color: #fff;
}
.io-pane__btn.is-ghost { background: transparent; }
.io-pane__btn.is-sm { padding: 4px 8px; font-size: 11px; }

.io-pane__body {
  flex: 1 1 auto;
  min-height: 0;
  display: flex;
  flex-direction: row;
}

.io-pane__stage {
  position: relative;
  flex: 1 1 auto;
  min-width: 0;
  min-height: 0;
  background: #dfe3e8;
}

.io-pane__frame {
  width: 100%;
  height: 100%;
  border: 0;
  background: #fff;
}

.io-pane__state {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  justify-items: center;
  gap: 10px;
  color: var(--muted);
  font-size: 13px;
  background: #f4f5f7;
}

.io-pane__state.is-error { color: var(--ink); }
.io-pane__state p {
  margin: 0;
  max-width: 280px;
  text-align: center;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.45;
}

.io-pane__spinner {
  width: 28px;
  height: 28px;
  border: 2px solid #e5e7eb;
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: io-spin 0.8s linear infinite;
}

@keyframes io-spin {
  to { transform: rotate(360deg); }
}

.io-pane__history {
  flex: 0 0 min(260px, 38%);
  min-width: 200px;
  border-left: 1px solid var(--line);
  background: #fff;
  display: flex;
  flex-direction: column;
  min-height: 0;
  overflow: auto;
  padding: 10px;
  gap: 8px;
}

.io-pane__history-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.io-pane__hint {
  margin: 0;
  color: var(--muted);
  font-size: 11px;
  line-height: 1.4;
}

.io-pane__history-toolbar {
  display: flex;
  gap: 6px;
}

.io-pane__input {
  flex: 1;
  min-width: 0;
  height: 32px;
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 0 8px;
  font: inherit;
  font-size: 12px;
}

.io-pane__versions {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 8px;
}

.io-pane__versions li {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  padding: 8px;
  border: 1px solid var(--line);
  border-radius: 8px;
}

.io-pane__versions strong {
  display: block;
  font-size: 12px;
}

.io-pane__versions span,
.io-pane__versions small {
  display: block;
  color: var(--muted);
  font-size: 11px;
  margin-top: 2px;
}

.io-pane__empty {
  margin: 12px 0 0;
  color: var(--muted);
  font-size: 12px;
  text-align: center;
}

@media (max-width: 720px) {
  .io-pane__body {
    flex-direction: column;
  }
  .io-pane__history {
    flex: 0 0 auto;
    max-height: 40%;
    border-left: 0;
    border-top: 1px solid var(--line);
  }
}
</style>
