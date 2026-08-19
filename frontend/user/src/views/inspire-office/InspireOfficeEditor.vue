<template>
  <AiAppShell mode="workspace" width="fluid" class="inspire-office-editor">
    <template #header>
      <AiAppHeader
        app="inspire-office"
        mode="workspace"
        back-label="文档列表"
        back-to="/inspire-office"
        :title="title"
        :subtitle="subtitle"
        context="启发 Office"
      >
        <template #actions>
          <button type="button" class="io-e-btn" :class="{ 'is-active': panelOpen }" @click="togglePanel">
            {{ panelOpen ? '收起' : '版本' }}
          </button>
        </template>
      </AiAppHeader>
    </template>

    <div class="io-workspace">
      <div class="io-editor-stage">
        <div v-if="loading" class="io-editor-state" role="status">
          <div class="io-e-spinner" aria-hidden="true" />
          <span>正在打开…</span>
        </div>
        <div v-else-if="error" class="io-editor-state is-error" role="alert">
          <strong>无法打开</strong>
          <p>{{ error }}</p>
          <button type="button" class="io-e-btn is-primary" @click="loadEditor">重试</button>
        </div>
        <iframe
          v-show="!loading && !error"
          ref="frame"
          class="io-editor-frame"
          title="启发 Office 编辑器"
          allow="fullscreen; clipboard-read; clipboard-write"
          @load="onFrameLoad"
        />
      </div>

      <aside v-if="panelOpen" class="io-history" aria-label="版本存档">
        <div class="io-history__head">
          <strong>版本</strong>
          <button type="button" class="io-e-btn is-ghost" :disabled="historyLoading" @click="refreshHistory">刷新</button>
        </div>
        <div class="io-history__body">
          <p class="io-history__hint" v-html="historyHintHtml"></p>
          <div class="io-history__toolbar">
            <input v-model="snapshotLabel" type="text" maxlength="80" :placeholder="snapshotPlaceholder" class="io-history__input" />
            <button type="button" class="io-e-btn is-primary" :disabled="snapshotting" @click="doSnapshot">
              {{ snapshotting ? '…' : '存档' }}
            </button>
          </div>
          <ul v-if="versions.length" class="io-history__list">
            <li v-for="v in versions" :key="v.id || v.versionNo" class="io-history__item">
              <div class="io-history__item-main">
                <strong>v{{ v.versionNo }}</strong>
                <span class="io-history__tag">{{ v.sourceLabel || v.source }}</span>
              </div>
              <div v-if="v.label" class="io-history__label">{{ v.label }}</div>
              <div class="io-history__meta">
                {{ formatTime(v.createdAt) }}
                <template v-if="v.sizeBytes != null"> · {{ formatSize(v.sizeBytes) }}</template>
              </div>
              <button
                type="button"
                class="io-e-btn is-ghost is-block"
                :disabled="restoring === v.versionNo"
                @click="doRestore(v)"
              >
                {{ restoring === v.versionNo ? '恢复中…' : '恢复此版本' }}
              </button>
            </li>
          </ul>
          <p v-else class="io-history__empty">{{ historyLoading ? '加载中…' : '暂无版本' }}</p>
        </div>
      </aside>
    </div>
  </AiAppShell>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import AiAppShell from '../../components/ai-apps/AiAppShell.vue'
import AiAppHeader from '../../components/ai-apps/AiAppHeader.vue'
import {
  createInspireOfficeSnapshot,
  fetchInspireOfficeEditorSession,
  listInspireOfficeVersions,
  reportInspireOfficePresence,
  restoreInspireOfficeVersion,
} from '../../services/inspireOfficeClient'

const route = useRoute()
const loading = ref(true)
const error = ref('')
const title = ref('文档编辑')
const meta = ref(null)
const frame = ref(null)

const panelOpen = ref(false)
const versions = ref([])
const historyLoading = ref(false)
const snapshotLabel = ref('')
const snapshotting = ref(false)
const restoring = ref(null)

let editorReadyArmed = false
let collaboraOrigin = ''
let readyTimers = []

/** 学习时长：在线（页可见+近期活跃）/ 编辑（Collabora 修改/保存信号） */
const presenceSessionId = globalThis.crypto?.randomUUID?.()
  || `io_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`
let presenceTimer = 0
let lastPresenceActiveAt = Date.now()
let lastEditActiveAt = 0
let pageVisible = typeof document === 'undefined' ? true : !document.hidden

const isPresentation = computed(() => {
  if (meta.value?.documentKind === 'slide') return true
  if (meta.value?.supportsTrackChanges === false && isSlideExt(meta.value?.ext)) return true
  return isSlideExt(meta.value?.ext)
})

const supportsTrackChanges = computed(() => {
  if (meta.value?.supportsTrackChanges != null) return !!meta.value.supportsTrackChanges
  return isWordExt(meta.value?.ext)
})

const subtitle = computed(() => {
  if (!meta.value) return ''
  const scopeMap = { personal: '个人', project: '项目', team: '团队' }
  const scope = scopeMap[meta.value.scope] || meta.value.scope || ''
  const ext = meta.value.ext ? String(meta.value.ext).replace(/^\./, '') : ''
  const ver = meta.value.version != null ? `v${meta.value.version}` : ''
  const mode = isPresentation.value ? '演示协同' : supportsTrackChanges.value ? '修订' : ''
  return [scope, ext, ver, mode].filter(Boolean).join(' · ')
})

const historyHintHtml = computed(() => {
  if (isPresentation.value) {
    return '演示无修订痕迹。自动保存会生成版本；重要节点可手动存档。'
  }
  if (supportsTrackChanges.value) {
    return 'Word 修订写在文件内。此处是整文件版本存档与恢复。'
  }
  return '协同保存会自动快照；重要节点可手动存档。'
})

const snapshotPlaceholder = computed(() =>
  isPresentation.value ? '备注，如：终稿前' : '备注（可选）'
)

function isSlideExt(ext) {
  const e = String(ext || '').replace(/^\./, '').toLowerCase()
  return ['pptx', 'ppt', 'odp', 'ppsx', 'potx'].includes(e)
}

function isWordExt(ext) {
  const e = String(ext || '').replace(/^\./, '').toLowerCase()
  return !e || ['docx', 'doc', 'odt', 'rtf'].includes(e)
}

function formatTime(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return String(value).replace('T', ' ').slice(0, 19)
  return d.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

function formatSize(bytes) {
  const n = Number(bytes) || 0
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

function togglePanel() {
  panelOpen.value = !panelOpen.value
  if (panelOpen.value) refreshHistory()
}

async function refreshHistory() {
  const id = route.params.id
  if (!id) return
  historyLoading.value = true
  try {
    versions.value = await listInspireOfficeVersions(id)
  } catch (e) {
    ElMessage.error(e?.message || '加载版本失败')
  } finally {
    historyLoading.value = false
  }
}

async function doSnapshot() {
  const id = route.params.id
  if (!id) return
  snapshotting.value = true
  try {
    await createInspireOfficeSnapshot(id, snapshotLabel.value || undefined)
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
      `将当前文档恢复为 v${v.versionNo}？会生成新版本，不删除历史。恢复后请重新打开编辑器。`,
      '恢复版本',
      { type: 'warning', confirmButtonText: '恢复', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  const id = route.params.id
  restoring.value = v.versionNo
  try {
    await restoreInspireOfficeVersion(id, v.versionNo)
    ElMessage.success(`已恢复至 v${v.versionNo}，正在重新加载编辑器`)
    await refreshHistory()
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

function enableTrackChangesInEditor() {
  // 仅 Word：显示修订痕迹（记录由 docx trackRevisions 保证）
  // Collabora 正确 API：Send_UNO_Command，或同源 sendUnoCommand
  try {
    const win = frame.value?.contentWindow
    const map = win?.app?.map
    if (map) {
      const on = map.stateChangeHandler?.getItemValue?.('.uno:ShowTrackedChanges') === 'true'
      if (!on && typeof map.sendUnoCommand === 'function') {
        map.sendUnoCommand('.uno:ShowTrackedChanges')
        return
      }
      if (!on && typeof map.uiManager?.actionsMap?.['viewchanges-inline'] === 'function') {
        map.uiManager.actionsMap['viewchanges-inline']()
        return
      }
      if (on) return
    }
  } catch {
    // fall through
  }
  postToCollabora({
    MessageId: 'Send_UNO_Command',
    SendTime: Date.now(),
    Values: { Command: '.uno:ShowTrackedChanges' },
  })
}

/** 隐藏 Collabora notebookbar「帮助」页签（Word/Excel/演示通用） */
function hideCollaboraHelpTab() {
  postToCollabora({
    MessageId: 'Hide_NotebookTab',
    SendTime: Date.now(),
    Values: { id: 'Help' },
  })
  try {
    const win = frame.value?.contentWindow
    const doc = frame.value?.contentDocument
    const ui = win?.app?.map?.uiManager
    if (ui && typeof ui.showNotebookTab === 'function') {
      ui.showNotebookTab('Help', false)
    }
    const el = doc?.getElementById('Help-tab-label')
    if (el) {
      el.style.setProperty('display', 'none', 'important')
      el.setAttribute('hidden', 'true')
      el.setAttribute('aria-hidden', 'true')
    }
  } catch {
    // ignore
  }
}

function clearReadyTimers() {
  readyTimers.forEach((t) => clearTimeout(t))
  readyTimers = []
}

/**
 * 同源 iframe：强制展开 notebookbar 工具行（branding.js 为主修复，这里再兜一层）。
 * Collabora 在 text.ShowToolbar=false 时会 $("#toolbar-row").css("display","none")。
 */
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
    // 跨域或未就绪时忽略
  }
}

/** Collabora 默认头像描边偏粗、偏深；压细、变浅 */
function injectCollaboraAvatarStyles(doc) {
  if (!doc?.head) return
  const id = 'orep-io-avatar-styles'
  if (doc.getElementById(id)) return
  const style = doc.createElement('style')
  style.id = id
  style.textContent = `
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
  clearReadyTimers()
  forceShowCollaboraToolbar()
  hideCollaboraHelpTab()
  ;[200, 500, 1000, 2000, 4000, 8000].forEach((ms) => {
    readyTimers.push(setTimeout(() => {
      forceShowCollaboraToolbar()
      hideCollaboraHelpTab()
    }, ms))
  })
  if (supportsTrackChanges.value) {
    readyTimers.push(setTimeout(() => enableTrackChangesInEditor(), 400))
    readyTimers.push(setTimeout(() => enableTrackChangesInEditor(), 1200))
  }
}

function isCollaboraOrigin(origin) {
  if (!origin) return false
  if (collaboraOrigin && origin === collaboraOrigin) return true
  const o = String(origin)
  return (
    o.includes('9980') ||
    o.includes('5174') ||
    o.includes('collabora') ||
    o === window.location.origin
  )
}

function onCollaboraMessage(event) {
  if (!editorReadyArmed) return
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

  // 任意 Collabora 消息视为「在线活跃」；修改/保存类视为「编辑」
  markPresenceActive()
  if (isEditSignalMessage(data.MessageId, data.Values)) {
    markEditActive()
  }

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
  if (
    id === 'Doc_ModifiedStatus' ||
    id === 'Action_Save' ||
    id === 'Action_SaveAs' ||
    id === 'Action_Save_Resp' ||
    id === 'UI_SaveAs' ||
    id === 'CallPythonScript'
  ) {
    return true
  }
  if (id === 'Doc_ModifiedStatus' || /Modified/i.test(id)) return true
  // ModifiedStatus 有时带 Modified:true
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
  const id = route.params.id
  if (!id || loading.value || error.value) return
  const visible = pageVisible
  const active = isPresenceActive()
  const editing = isEditingActive()
  if (!force && (!visible || !active)) return
  try {
    await reportInspireOfficePresence(id, {
      sessionId: presenceSessionId,
      visible,
      active: active || force,
      editing: editing || false,
      reset: false,
    })
  } catch {
    // 时长统计失败不影响编辑
  }
}

function startPresenceTracking() {
  stopPresenceTracking()
  if (!route.params.id) return
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
  postToCollabora({ MessageId: 'Host_PostmessageReady' })
}

async function loadEditor() {
  loading.value = true
  error.value = ''
  editorReadyArmed = false
  clearReadyTimers()
  const id = route.params.id
  if (!id) {
    error.value = '缺少文档 ID'
    loading.value = false
    return
  }
  try {
    const payload = await fetchInspireOfficeEditorSession(id, 'edit')
    meta.value = payload
    title.value = payload?.title || (isSlideExt(payload?.ext) ? '演示编辑' : '文档编辑')
    if (!payload?.editorUrl) throw new Error('未返回编辑地址')

    try {
      collaboraOrigin = new URL(payload.editorUrl).origin
    } catch {
      collaboraOrigin = ''
    }
    editorReadyArmed = true

    if (frame.value) {
      frame.value.src = payload.editorUrl
    }
    // 打开即开始在线计时；文档 Loaded 后继续心跳
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

onMounted(() => {
  window.addEventListener('message', onCollaboraMessage)
  document.addEventListener('visibilitychange', handlePresenceVisibility)
  window.addEventListener('pagehide', handlePageHide)
  window.addEventListener('beforeunload', handlePageHide)
  // 宿主页交互也算在线活跃（侧栏版本面板等）
  window.addEventListener('pointerdown', markPresenceActive, { passive: true })
  window.addEventListener('keydown', markPresenceActive, { passive: true })
  loadEditor()
})

onBeforeUnmount(() => {
  flushPresence(true).catch(() => {})
  stopPresenceTracking()
  window.removeEventListener('message', onCollaboraMessage)
  document.removeEventListener('visibilitychange', handlePresenceVisibility)
  window.removeEventListener('pagehide', handlePageHide)
  window.removeEventListener('beforeunload', handlePageHide)
  window.removeEventListener('pointerdown', markPresenceActive)
  window.removeEventListener('keydown', markPresenceActive)
  editorReadyArmed = false
  clearReadyTimers()
})
</script>

<style scoped>
.inspire-office-editor {
  --io-line: var(--ds-border, #e8eaed);
  --io-muted: var(--ds-muted, #6b7280);
  --io-ink: var(--ds-ink, #111827);
  --io-accent: var(--ds-orange, #e5481d);
  height: 100%;
  max-height: 100%;
  min-height: 0;
  overflow: hidden;
}

.inspire-office-editor :deep(.ai-app-header.is-workspace) {
  min-height: 44px;
  height: 44px;
  max-height: 44px;
  padding: 0 4px;
  align-items: center;
  overflow: hidden;
  box-sizing: border-box;
  border-bottom: 1px solid var(--io-line);
  background: #fff;
}

.inspire-office-editor :deep(.ai-app-header__main) {
  flex-wrap: nowrap;
  gap: 8px;
  min-width: 0;
}

.inspire-office-editor :deep(.ai-app-header__back) {
  min-height: 28px;
  font-size: 12px;
  padding: 0 4px 0 0;
  gap: 2px;
  color: var(--io-muted);
}

.inspire-office-editor :deep(.ai-app-header__context) {
  font-size: 11px;
  color: var(--io-muted);
}

.inspire-office-editor :deep(.ai-app-header__identity) {
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.inspire-office-editor :deep(.ai-app-header__icon) {
  width: 22px;
  height: 22px;
  flex-basis: 22px;
}

.inspire-office-editor :deep(.ai-app-header__icon svg) {
  width: 13px;
  height: 13px;
}

.inspire-office-editor :deep(.ai-app-header__copy) {
  display: flex;
  flex-direction: row;
  align-items: baseline;
  gap: 8px;
  min-width: 0;
  overflow: hidden;
}

.inspire-office-editor :deep(.ai-app-header__copy h1) {
  font-size: 14px;
  font-weight: 700;
  line-height: 1.2;
  flex: 0 1 auto;
  max-width: 42%;
  margin: 0;
}

.inspire-office-editor :deep(.ai-app-header__copy p) {
  font-size: 11px;
  line-height: 1.2;
  flex: 1 1 auto;
  min-width: 0;
  margin: 0;
  color: var(--io-muted);
}

.inspire-office-editor :deep(.ai-app-header__right),
.inspire-office-editor :deep(.ai-app-header__actions) {
  align-items: center;
  flex-shrink: 0;
}

.inspire-office-editor :deep(.ai-app-content) {
  height: 100%;
  min-height: 0;
  display: grid;
  grid-template-rows: 44px minmax(0, 1fr);
}

.inspire-office-editor :deep(.ai-app-shell__body) {
  margin: 0;
  padding: 0;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: #f4f5f7;
}

.io-e-btn {
  appearance: none;
  border: 1px solid var(--io-line);
  background: #fff;
  color: var(--io-ink);
  border-radius: 999px;
  padding: 5px 12px;
  font: 650 12px/1 inherit;
  cursor: pointer;
}
.io-e-btn:hover:not(:disabled) { background: #f8fafc; }
.io-e-btn:disabled { opacity: .5; cursor: not-allowed; }
.io-e-btn.is-active {
  border-color: color-mix(in srgb, var(--io-accent) 45%, var(--io-line));
  color: var(--io-accent);
  background: color-mix(in srgb, var(--io-accent) 8%, #fff);
}
.io-e-btn.is-primary {
  border-color: transparent;
  background: var(--io-accent);
  color: #fff;
}
.io-e-btn.is-ghost { background: transparent; }
.io-e-btn.is-block { width: 100%; }

.io-workspace {
  display: flex;
  gap: 0;
  flex: 1 1 auto;
  min-height: 0;
  height: 100%;
  overflow: hidden;
}

.io-editor-stage {
  position: relative;
  flex: 1 1 auto;
  min-width: 0;
  min-height: 0;
  height: 100%;
  overflow: hidden;
  background: #fff;
  border-right: 1px solid transparent;
}

.io-editor-frame {
  width: 100%;
  height: 100%;
  border: 0;
  background: #fff;
  display: block;
}

.io-editor-state {
  position: absolute;
  inset: 0;
  z-index: 2;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 24px;
  text-align: center;
  background: #fafbfc;
  color: var(--io-muted);
}
.io-editor-state.is-error { color: var(--io-ink); }
.io-editor-state strong { font-size: 15px; }
.io-editor-state p {
  margin: 0;
  max-width: 360px;
  font-size: 13px;
  color: var(--io-muted);
  line-height: 1.45;
}
.io-e-spinner {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  border: 2px solid #e5e7eb;
  border-top-color: var(--io-accent);
  animation: io-e-spin .7s linear infinite;
}
@keyframes io-e-spin { to { transform: rotate(360deg); } }

.io-history {
  width: min(280px, 38vw);
  flex: 0 0 auto;
  display: flex;
  flex-direction: column;
  min-height: 0;
  height: 100%;
  background: #fff;
  border-left: 1px solid var(--io-line);
  overflow: hidden;
}

.io-history__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 12px 12px 8px;
  flex-shrink: 0;
}
.io-history__head strong { font-size: 13px; font-weight: 700; }

.io-history__body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 0 12px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.io-history__toolbar {
  display: flex;
  gap: 6px;
  align-items: center;
}

.io-history__input {
  flex: 1;
  min-width: 0;
  height: 32px;
  border: 1px solid var(--io-line);
  border-radius: 8px;
  padding: 0 8px;
  font-size: 12px;
  background: #fafbfc;
}
.io-history__input:focus {
  outline: none;
  border-color: color-mix(in srgb, var(--io-accent) 45%, var(--io-line));
  background: #fff;
}

.io-history__hint {
  margin: 0;
  font-size: 11px;
  color: var(--io-muted);
  line-height: 1.45;
}

.io-history__list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.io-history__item {
  border: 1px solid var(--io-line);
  border-radius: 12px;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 5px;
  background: #fafbfc;
}

.io-history__item-main {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  font-size: 13px;
}

.io-history__tag {
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 999px;
  background: #eef2ff;
  color: #4338ca;
}

.io-history__label {
  font-size: 12px;
  color: var(--io-ink);
}

.io-history__meta {
  font-size: 11px;
  color: var(--io-muted);
}

.io-history__empty {
  margin: 18px 0;
  text-align: center;
  font-size: 12px;
  color: var(--io-muted);
}

@media (max-width: 720px) {
  .io-history { width: min(100%, 100vw); position: absolute; right: 0; top: 0; bottom: 0; z-index: 5; box-shadow: -8px 0 24px rgba(15,23,42,.08); }
}
</style>
