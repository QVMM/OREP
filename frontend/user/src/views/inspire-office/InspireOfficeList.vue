<template>
  <AiAppShell mode="landing" width="wide" class="inspire-office-list">
    <template #header>
      <AiAppHeader
        app="inspire-office"
        mode="landing"
        back-label="AI 应用中心"
        back-to="/ai-apps"
        title="启发 Office"
        subtitle="在线协同编辑 Word、表格与演示"
      >
        <template #actions>
          <button type="button" class="io-btn io-btn--ghost" @click="openUploadModal">上传</button>
          <button type="button" class="io-btn io-btn--primary" @click="showCreate = true">新建</button>
        </template>
      </AiAppHeader>
    </template>

    <section v-if="statusHint" class="io-alert" role="status">
      <strong>{{ statusHintTitle }}</strong>
      <span>{{ statusHint }}</span>
    </section>

    <section class="io-toolbar">
      <nav class="io-tabs" aria-label="文档范围">
        <button
          v-for="tab in scopeTabs"
          :key="tab.key"
          type="button"
          :class="{ 'is-active': activeScope === tab.key }"
          @click="activeScope = tab.key"
        >
          {{ tab.label }}
        </button>
      </nav>
      <div class="io-toolbar__right">
        <select
          v-if="teams.length && (activeScope === 'project' || activeScope === 'team' || activeScope === 'all')"
          v-model="filterTeamId"
          class="io-control"
          aria-label="筛选团队"
        >
          <option value="">全部团队</option>
          <option v-for="team in teams" :key="team.id" :value="String(team.id)">{{ team.name }}</option>
        </select>
        <label class="io-search">
          <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
          <input v-model="keyword" type="search" placeholder="搜索文档" aria-label="搜索文档标题" />
        </label>
      </div>
    </section>

    <section v-if="loading" class="io-panel io-empty" role="status">
      <div class="io-spinner" aria-hidden="true" />
      <span>加载中…</span>
    </section>

    <section v-else-if="!filteredDocs.length" class="io-panel io-empty">
      <div class="io-empty__icon" aria-hidden="true">
        <svg viewBox="0 0 48 48" fill="none"><rect x="10" y="6" width="28" height="36" rx="4" stroke="currentColor" stroke-width="2"/><path d="M18 18h12M18 24h12M18 30h8" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg>
      </div>
      <strong>还没有文档</strong>
      <p>新建智能文档，或上传已有 Word / Excel / 演示文件。</p>
      <div class="io-empty__actions">
        <button type="button" class="io-btn io-btn--primary" @click="showCreate = true">新建文档</button>
        <button type="button" class="io-btn io-btn--ghost" @click="openUploadModal">上传文件</button>
      </div>
    </section>

    <section v-else class="io-panel io-list-wrap">
      <ul class="io-list">
        <li v-for="doc in filteredDocs" :key="doc.id" class="io-row">
          <button type="button" class="io-row__main" @click="openDoc(doc)">
            <span class="io-type" :data-type="doc.documentType" aria-hidden="true">{{ typeMark(doc) }}</span>
            <span class="io-row__body">
              <strong class="io-row__title">{{ doc.title }}</strong>
              <span class="io-row__meta">
                <em>{{ typeLabel(doc) }}</em>
                <em>{{ scopeLabel(doc.scope) }}</em>
                <em v-if="doc.teamName">{{ doc.teamName }}</em>
                <em v-if="doc.resourceId" class="is-sync">已同步</em>
                <em>v{{ doc.version || 1 }}</em>
                <em>{{ formatTime(doc.updatedAt) }}</em>
              </span>
            </span>
          </button>
          <div class="io-row__actions">
            <button type="button" class="io-btn io-btn--primary is-sm" @click="openDoc(doc)">打开</button>
            <InspireOfficeShareBubble
              :doc-id="doc.id"
              :inviter="auth.user?.username || ''"
              :title="doc.title || ''"
              :team-name="doc.teamName || ''"
              :scope="doc.scope || ''"
              :ext="doc.ext || ''"
              :type="doc.documentType || ''"
              trigger-class="io-btn io-btn--ghost is-sm is-icon"
              trigger-title="分享邀请"
            />
            <button type="button" class="io-btn io-btn--ghost is-sm" @click="downloadDoc(doc)">下载</button>
            <button type="button" class="io-btn io-btn--ghost is-sm" @click="openManage(doc)">管理</button>
          </div>
        </li>
      </ul>
    </section>

    <!-- 新建 -->
    <div v-if="showCreate" class="io-modal" role="dialog" aria-modal="true" @click.self="showCreate = false">
      <div class="io-dialog">
        <header class="io-dialog__head">
          <h2>新建文档</h2>
          <button type="button" class="io-icon-btn" aria-label="关闭" @click="showCreate = false">×</button>
        </header>
        <div class="io-dialog__body">
          <label class="io-field">
            <span>标题</span>
            <input v-model="createForm.title" type="text" maxlength="200" placeholder="未命名文档" class="io-control" />
          </label>
          <div class="io-field">
            <span>类型</span>
            <div class="io-choice" role="radiogroup" aria-label="文档类型">
              <button
                v-for="opt in typeOptions"
                :key="opt.ext"
                type="button"
                role="radio"
                :aria-checked="createForm.ext === opt.ext"
                :class="{ 'is-active': createForm.ext === opt.ext }"
                @click="createForm.ext = opt.ext"
              >
                <b :data-type="opt.type">{{ opt.mark }}</b>
                <span>{{ opt.label }}</span>
              </button>
            </div>
          </div>
          <div class="io-field">
            <span>归属</span>
            <div class="io-choice is-compact" role="radiogroup" aria-label="归属">
              <button
                v-for="s in scopeOptions"
                :key="s.key"
                type="button"
                role="radio"
                :aria-checked="createForm.scope === s.key"
                :class="{ 'is-active': createForm.scope === s.key }"
                @click="createForm.scope = s.key; onCreateScopeChange()"
              >{{ s.label }}</button>
            </div>
          </div>
          <label v-if="createForm.scope !== 'personal'" class="io-field">
            <span>团队</span>
            <select v-model="createForm.teamId" class="io-control">
              <option value="">请选择团队</option>
              <option v-for="team in teams" :key="team.id" :value="String(team.id)">{{ team.name }}</option>
            </select>
          </label>
          <p v-if="createForm.scope !== 'personal'" class="io-tip">项目 / 团队文档会同步到资源中心。</p>
          <p v-if="createError" class="io-error">{{ createError }}</p>
        </div>
        <footer class="io-dialog__foot">
          <button type="button" class="io-btn io-btn--ghost" :disabled="creating" @click="showCreate = false">取消</button>
          <button type="button" class="io-btn io-btn--primary" :disabled="creating" @click="submitCreate">
            {{ creating ? '创建中…' : '创建并打开' }}
          </button>
        </footer>
      </div>
    </div>

    <!-- 上传 -->
    <div v-if="showUpload" class="io-modal" role="dialog" aria-modal="true" aria-labelledby="io-upload-title" @click.self="closeUploadModal">
      <div class="io-dialog is-wide">
        <header class="io-dialog__head">
          <h2 id="io-upload-title">上传文档</h2>
          <button type="button" class="io-icon-btn" aria-label="关闭" :disabled="uploading" @click="closeUploadModal">×</button>
        </header>
        <div class="io-dialog__body">
          <DropFileUpload
            v-model="uploadForm.file"
            size="md"
            accept=".doc,.docx,.xls,.xlsx,.ppt,.pptx,.odt,.ods,.odp,.rtf,.txt,.csv"
            :disabled="uploading"
            title="拖拽文件到此处，或点击选择"
            hint="Word / Excel / 演示 等常见格式"
            accept-hint=".doc .docx .xls .xlsx .ppt .pptx"
            @change="onUploadFilePicked"
            @error="onUploadDropError"
          />
          <label class="io-field">
            <span>标题（可选）</span>
            <input v-model="uploadForm.title" type="text" maxlength="200" placeholder="默认使用文件名" class="io-control" />
          </label>
          <div class="io-field">
            <span>归属</span>
            <div class="io-choice is-compact" role="radiogroup" aria-label="归属">
              <button
                v-for="s in scopeOptions"
                :key="s.key"
                type="button"
                role="radio"
                :aria-checked="uploadForm.scope === s.key"
                :class="{ 'is-active': uploadForm.scope === s.key }"
                :disabled="uploading"
                @click="uploadForm.scope = s.key; onUploadScopeChange()"
              >{{ s.label }}</button>
            </div>
          </div>
          <label v-if="uploadForm.scope !== 'personal'" class="io-field">
            <span>团队</span>
            <select v-model="uploadForm.teamId" class="io-control" :disabled="uploading">
              <option value="">请选择团队</option>
              <option v-for="team in teams" :key="team.id" :value="String(team.id)">{{ team.name }}</option>
            </select>
          </label>
          <p class="io-tip" :class="{ 'is-muted': uploadForm.scope === 'personal' }">
            {{ uploadForm.scope === 'personal' ? '个人文档仅保存在启发 Office。' : '项目 / 团队文档会同步到资源中心。' }}
          </p>
          <p v-if="uploadError" class="io-error">{{ uploadError }}</p>
        </div>
        <footer class="io-dialog__foot">
          <button type="button" class="io-btn io-btn--ghost" :disabled="uploading" @click="closeUploadModal">取消</button>
          <button type="button" class="io-btn io-btn--primary" :disabled="uploading" @click="submitUpload">
            {{ uploading ? '上传中…' : '上传并打开' }}
          </button>
        </footer>
      </div>
    </div>

    <!-- 管理 -->
    <div v-if="showManage && manageDoc" class="io-modal" role="dialog" aria-modal="true" @click.self="closeManage">
      <div class="io-dialog is-wide">
        <header class="io-dialog__head">
          <div class="io-dialog__title">
            <h2>管理</h2>
            <p>{{ manageDoc.title }}</p>
          </div>
          <button type="button" class="io-icon-btn" aria-label="关闭" :disabled="manageBusy" @click="closeManage">×</button>
        </header>
        <div class="io-dialog__body">
          <div class="io-meta-chips">
            <span>{{ typeLabel(manageDoc) }}</span>
            <span>{{ scopeLabel(manageDoc.scope) }}</span>
            <span v-if="manageDoc.teamName">{{ manageDoc.teamName }}</span>
            <span v-if="manageDoc.resourceId" class="is-sync">已同步资源中心</span>
          </div>

          <section class="io-block">
            <h3>重命名</h3>
            <div class="io-inline">
              <input
                v-model="manageForm.title"
                type="text"
                maxlength="200"
                class="io-control"
                :disabled="!canManage || manageBusy"
                placeholder="文档标题"
              />
              <button type="button" class="io-btn io-btn--ghost is-sm" :disabled="!canManage || manageBusy" @click="submitRename">保存</button>
            </div>
          </section>

          <section class="io-block">
            <h3>迁移归属</h3>
            <div class="io-choice is-compact" role="radiogroup" aria-label="迁移归属">
              <button
                v-for="s in scopeOptions"
                :key="s.key"
                type="button"
                role="radio"
                :aria-checked="manageForm.scope === s.key"
                :class="{ 'is-active': manageForm.scope === s.key }"
                :disabled="!canManage || manageBusy"
                @click="manageForm.scope = s.key; onManageScopeChange()"
              >{{ s.label }}</button>
            </div>
            <label v-if="manageForm.scope !== 'personal'" class="io-field" style="margin-top:10px">
              <span>团队</span>
              <select v-model="manageForm.teamId" class="io-control" :disabled="!canManage || manageBusy">
                <option value="">请选择团队</option>
                <option v-for="team in teams" :key="team.id" :value="String(team.id)">{{ team.name }}</option>
              </select>
            </label>
            <p class="io-tip" :class="{ 'is-muted': manageForm.scope === 'personal' }">
              {{ manageForm.scope === 'personal'
                ? '迁到个人后解除资源中心关联，已有副本会保留。'
                : '迁到项目/团队后，会把当前文件同步到该团队资源中心。' }}
            </p>
            <button type="button" class="io-btn io-btn--primary is-sm" :disabled="!canManage || manageBusy" @click="submitMove">
              {{ manageBusy ? '处理中…' : '确认迁移' }}
            </button>
          </section>

          <section class="io-block">
            <h3>快捷操作</h3>
            <div class="io-actions-grid">
              <button
                type="button"
                class="io-action"
                :disabled="!canManage || manageBusy || !['project', 'team'].includes(manageDoc.scope)"
                @click="submitSyncResource"
              >
                <strong>同步资源中心</strong>
                <span>推送当前内容</span>
              </button>
              <button type="button" class="io-action" :disabled="manageBusy" @click="submitDuplicate">
                <strong>复制一份</strong>
                <span>默认到个人</span>
              </button>
              <button type="button" class="io-action" :disabled="manageBusy" @click="downloadDoc(manageDoc)">
                <strong>下载</strong>
                <span>保存到本地</span>
              </button>
              <button
                v-if="canManage"
                type="button"
                class="io-action is-danger"
                :disabled="manageBusy"
                @click="confirmDelete(manageDoc)"
              >
                <strong>删除</strong>
                <span>永久删除文件</span>
              </button>
            </div>
            <p v-if="!canManage" class="io-tip is-muted">你不是所有者：可打开、下载、复制；迁移与删除仅所有者可用。</p>
          </section>

          <p v-if="manageError" class="io-error">{{ manageError }}</p>
        </div>
        <footer class="io-dialog__foot">
          <button type="button" class="io-btn io-btn--ghost" :disabled="manageBusy" @click="closeManage">关闭</button>
          <InspireOfficeShareBubble
            v-if="manageDoc?.id"
            :doc-id="manageDoc.id"
            :inviter="auth.user?.username || ''"
            :title="manageDoc.title || ''"
            :team-name="manageDoc.teamName || ''"
            :scope="manageDoc.scope || ''"
            :ext="manageDoc.ext || ''"
            :type="manageDoc.documentType || ''"
            trigger-class="io-btn io-btn--ghost"
            trigger-title="分享邀请"
          >
            分享邀请
          </InspireOfficeShareBubble>
          <button type="button" class="io-btn io-btn--primary" :disabled="manageBusy" @click="openDoc(manageDoc); closeManage()">打开编辑</button>
        </footer>
      </div>
    </div>
  </AiAppShell>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import AiAppShell from '../../components/ai-apps/AiAppShell.vue'
import AiAppHeader from '../../components/ai-apps/AiAppHeader.vue'
import DropFileUpload from '../../components/base/DropFileUpload.vue'
import { useAuthStore } from '../../stores/auth'
import {
  createBlankInspireOfficeDocument,
  deleteInspireOfficeDocument,
  downloadInspireOfficeDocument,
  duplicateInspireOfficeDocument,
  fetchInspireOfficeStatus,
  fetchMyProjectTeams,
  listInspireOfficeDocuments,
  moveInspireOfficeDocument,
  renameInspireOfficeDocument,
  syncInspireOfficeToResource,
  uploadInspireOfficeDocument,
} from '../../services/inspireOfficeClient'
import InspireOfficeShareBubble from '../../components/inspire-office/InspireOfficeShareBubble.vue'

const router = useRouter()
const auth = useAuthStore()
const scopeTabs = [
  { key: 'all', label: '全部' },
  { key: 'personal', label: '个人' },
  { key: 'project', label: '项目' },
  { key: 'team', label: '团队' },
]
const scopeOptions = [
  { key: 'personal', label: '个人' },
  { key: 'project', label: '项目' },
  { key: 'team', label: '团队' },
]
const typeOptions = [
  { ext: 'sdoc', label: '智能文档', mark: '智', type: 'sdoc' },
  { ext: 'docx', label: 'Word', mark: 'W', type: 'word' },
  { ext: 'xlsx', label: '表格', mark: 'X', type: 'cell' },
  { ext: 'pptx', label: '演示', mark: 'P', type: 'slide' },
]

const docs = ref([])
const teams = ref([])
const loading = ref(true)
const activeScope = ref('all')
const filterTeamId = ref('')
const keyword = ref('')
const statusHint = ref('')
const statusHintTitle = ref('')
const showCreate = ref(false)
const creating = ref(false)
const createError = ref('')
const showUpload = ref(false)
const uploading = ref(false)
const uploadError = ref('')
const createForm = reactive({ title: '', ext: 'sdoc', scope: 'personal', teamId: '' })
const uploadForm = reactive({
  file: null,
  title: '',
  scope: 'personal',
  teamId: '',
})

const showManage = ref(false)
const manageDoc = ref(null)
const manageBusy = ref(false)
const manageError = ref('')
const manageForm = reactive({ title: '', scope: 'personal', teamId: '' })

const canManage = computed(() => manageDoc.value && isOwner(manageDoc.value))
const canSyncResource = computed(() => {
  if (!manageDoc.value || !canManage.value) return false
  const scope = manageForm.scope || manageDoc.value.scope
  return scope === 'project' || scope === 'team'
})

const filteredDocs = computed(() => {
  const q = keyword.value.trim().toLowerCase()
  return docs.value.filter((doc) => {
    if (activeScope.value !== 'all' && doc.scope !== activeScope.value) return false
    if (filterTeamId.value && String(doc.teamId || '') !== filterTeamId.value) return false
    if (q && !(doc.title || '').toLowerCase().includes(q)) return false
    return true
  })
})

function isOwner(doc) {
  const uid = auth.user?.id
  return uid != null && String(doc.ownerUserId) === String(uid)
}
function typeLabel(doc) {
  if (doc.documentType === 'sdoc' || doc.ext === 'sdoc') return '智能文档'
  if (doc.documentType === 'cell') return '表格'
  if (doc.documentType === 'slide') return '演示'
  return '文档'
}
function typeMark(doc) {
  if (doc.documentType === 'sdoc' || doc.ext === 'sdoc') return '智'
  if (doc.documentType === 'cell') return 'X'
  if (doc.documentType === 'slide') return 'P'
  return 'W'
}
function scopeLabel(scope) {
  if (scope === 'project') return '项目'
  if (scope === 'team') return '团队'
  return '个人'
}
function formatTime(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return String(value).replace('T', ' ').slice(0, 16)
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

async function loadDocs() {
  loading.value = true
  try {
    docs.value = await listInspireOfficeDocuments({
      scope: activeScope.value === 'all' ? undefined : activeScope.value,
      teamId: filterTeamId.value ? Number(filterTeamId.value) : undefined,
    })
  } catch (e) {
    docs.value = []
    ElMessage.error(e?.message || '加载文档列表失败')
  } finally {
    loading.value = false
  }
}

async function loadTeams() {
  try {
    teams.value = await fetchMyProjectTeams()
  } catch {
    teams.value = []
  }
}

async function checkStatus() {
  try {
    const st = await fetchInspireOfficeStatus()
    if (!st?.enabled) {
      statusHintTitle.value = '服务未启用'
      statusHint.value = '启发 Office 当前关闭。'
    } else if (!st.collaboraConfigured || !st.wopiBaseConfigured) {
      statusHintTitle.value = '编辑服务待配置'
      statusHint.value = '列表/上传可用；在线编辑需配置 Collabora 与 WOPI 基址。'
    } else if (st.collaboraReachable === false) {
      statusHintTitle.value = 'Collabora 未就绪'
      statusHint.value = '引擎暂时不可达，请确认 Docker 中 Collabora 已启动（默认 :9980）。'
    } else {
      statusHint.value = ''
      statusHintTitle.value = ''
    }
  } catch {
    statusHint.value = ''
  }
}

function openDoc(doc) {
  if (doc.ext === 'sdoc' || doc.documentType === 'sdoc') {
    router.push({ name: 'InspireSmartDoc', params: { id: String(doc.id) } })
    return
  }
  router.push({
    name: 'InspireOfficeWorkbench',
    query: {
      focus: String(doc.id),
      title: doc.title || undefined,
      ext: doc.ext || undefined,
      type: doc.documentType || undefined,
    },
  })
}

function downloadDoc(doc) {
  if (!doc?.id) return
  const name = doc.ext && doc.title && !String(doc.title).endsWith(`.${doc.ext}`)
    ? `${doc.title}.${doc.ext}`
    : (doc.title || 'document')
  downloadInspireOfficeDocument(doc.id, name)
  ElMessage.success('开始下载')
}

function openManage(doc) {
  manageDoc.value = doc
  manageError.value = ''
  manageForm.title = doc.title || ''
  manageForm.scope = doc.scope || 'personal'
  manageForm.teamId = doc.teamId != null ? String(doc.teamId) : ''
  showManage.value = true
}

function closeManage() {
  if (manageBusy.value) return
  showManage.value = false
  manageDoc.value = null
  manageError.value = ''
}

function onManageScopeChange() {
  if (manageForm.scope === 'personal') manageForm.teamId = ''
}

function patchLocalDoc(updated) {
  if (!updated?.id) return
  const i = docs.value.findIndex((d) => d.id === updated.id)
  if (i >= 0) docs.value[i] = { ...docs.value[i], ...updated }
  if (manageDoc.value?.id === updated.id) manageDoc.value = { ...manageDoc.value, ...updated }
}

async function submitRename() {
  if (!manageDoc.value || !canManage.value) return
  const title = manageForm.title.trim()
  if (!title) {
    manageError.value = '标题不能为空'
    return
  }
  manageBusy.value = true
  manageError.value = ''
  try {
    const updated = await renameInspireOfficeDocument(manageDoc.value.id, title)
    patchLocalDoc(updated)
    ElMessage.success('已重命名')
  } catch (e) {
    manageError.value = e?.message || '重命名失败'
  } finally {
    manageBusy.value = false
  }
}

async function submitMove() {
  if (!manageDoc.value || !canManage.value) return
  if (manageForm.scope !== 'personal' && !manageForm.teamId) {
    manageError.value = '请选择项目/团队'
    return
  }
  manageBusy.value = true
  manageError.value = ''
  try {
    const updated = await moveInspireOfficeDocument(manageDoc.value.id, {
      scope: manageForm.scope,
      teamId: manageForm.teamId ? Number(manageForm.teamId) : null,
      syncResource: manageForm.scope !== 'personal',
    })
    patchLocalDoc(updated)
    ElMessage.success(
      updated?.syncedToResourceCenter
        ? '已迁移归属，并同步到资源中心'
        : '已迁移归属'
    )
    await loadDocs()
  } catch (e) {
    manageError.value = e?.message || '迁移失败'
  } finally {
    manageBusy.value = false
  }
}

async function submitSyncResource() {
  if (!manageDoc.value || !canManage.value) return
  // 若表单里改了归属但未保存迁移，先提示
  const scopeChanged = manageForm.scope !== manageDoc.value.scope
    || String(manageForm.teamId || '') !== String(manageDoc.value.teamId || '')
  if (scopeChanged) {
    manageError.value = '归属有未保存的修改，请先点「确认迁移」'
    return
  }
  if (manageDoc.value.scope === 'personal') {
    manageError.value = '个人文档请先迁移到项目/团队再同步'
    return
  }
  manageBusy.value = true
  manageError.value = ''
  try {
    const updated = await syncInspireOfficeToResource(manageDoc.value.id)
    patchLocalDoc(updated)
    ElMessage.success('已同步当前内容到资源中心')
  } catch (e) {
    manageError.value = e?.message || '同步失败'
  } finally {
    manageBusy.value = false
  }
}

async function submitDuplicate() {
  if (!manageDoc.value) return
  manageBusy.value = true
  manageError.value = ''
  try {
    // 默认复制到个人，避免误入团队
    const copy = await duplicateInspireOfficeDocument(manageDoc.value.id, {
      title: `${manageDoc.value.title || '文档'} 副本`,
      scope: 'personal',
    })
    ElMessage.success('已复制到个人文档')
    closeManage()
    if (copy?.id) {
      openDoc(copy)
    }
    else await loadDocs()
  } catch (e) {
    manageError.value = e?.message || '复制失败'
  } finally {
    manageBusy.value = false
  }
}

function onCreateScopeChange() {
  if (createForm.scope === 'personal') createForm.teamId = ''
}

function openUploadModal() {
  uploadError.value = ''
  uploadForm.file = null
  uploadForm.title = ''
  uploadForm.scope = activeScope.value === 'project' || activeScope.value === 'team'
    ? activeScope.value
    : 'personal'
  uploadForm.teamId = filterTeamId.value || ''
  showUpload.value = true
}

function closeUploadModal() {
  if (uploading.value) return
  showUpload.value = false
  uploadError.value = ''
  uploadForm.file = null
  uploadForm.title = ''
}

function onUploadScopeChange() {
  if (uploadForm.scope === 'personal') uploadForm.teamId = ''
}

function onUploadFilePicked(file) {
  uploadError.value = ''
  if (file && !uploadForm.title.trim()) {
    uploadForm.title = String(file.name || '').replace(/\.[^.]+$/, '')
  }
}

function onUploadDropError(err) {
  uploadError.value = err?.message || '文件不符合要求'
}

async function submitCreate() {
  createError.value = ''
  if (createForm.scope !== 'personal' && !createForm.teamId) {
    createError.value = '请选择项目/团队'
    return
  }
  creating.value = true
  try {
    const doc = await createBlankInspireOfficeDocument({
      title: createForm.title || undefined,
      ext: createForm.ext,
      scope: createForm.scope,
      teamId: createForm.teamId ? Number(createForm.teamId) : null,
    })
    showCreate.value = false
    createForm.title = ''
    createForm.ext = 'sdoc'
    createForm.scope = 'personal'
    createForm.teamId = ''
    const synced = doc?.syncedToResourceCenter
    ElMessage.success(synced ? '已创建，并同步到资源中心' : '已创建')
    if (doc?.id) openDoc(doc)
    else await loadDocs()
  } catch (e) {
    createError.value = e?.message || '创建失败'
  } finally {
    creating.value = false
  }
}

async function submitUpload() {
  uploadError.value = ''
  if (!uploadForm.file) {
    uploadError.value = '请选择要上传的文件'
    return
  }
  if (uploadForm.scope !== 'personal' && !uploadForm.teamId) {
    uploadError.value = '请选择项目/团队'
    return
  }
  uploading.value = true
  try {
    const doc = await uploadInspireOfficeDocument({
      file: uploadForm.file,
      title: uploadForm.title || undefined,
      scope: uploadForm.scope,
      teamId: uploadForm.teamId ? Number(uploadForm.teamId) : null,
    })
    showUpload.value = false
    uploadForm.file = null
    uploadForm.title = ''
    uploadForm.scope = 'personal'
    uploadForm.teamId = ''
    const synced = doc?.syncedToResourceCenter
    ElMessage.success(synced ? '上传成功，已同步到资源中心' : '上传成功')
    if (doc?.id) {
      router.push({
        name: 'InspireOfficeWorkbench',
        query: { focus: String(doc.id), title: doc.title, ext: doc.ext, type: doc.documentType },
      })
    }
    else await loadDocs()
  } catch (e) {
    uploadError.value = e?.message || '上传失败'
  } finally {
    uploading.value = false
  }
}

async function confirmDelete(doc) {
  try {
    await ElMessageBox.confirm(
      `确定永久删除「${doc.title}」？文档文件与历史版本将从服务器清除，且无法恢复。资源中心中已同步的副本不会自动删除。`,
      '删除文档',
      { type: 'warning', confirmButtonText: '永久删除', cancelButtonText: '取消' }
    )
  } catch {
    return
  }
  manageBusy.value = true
  try {
    await deleteInspireOfficeDocument(doc.id)
    // 先本地移除，避免列表短暂回显
    docs.value = docs.value.filter((d) => String(d.id) !== String(doc.id))
    ElMessage.success('已永久删除')
    manageBusy.value = false
    if (manageDoc.value?.id === doc.id) {
      showManage.value = false
      manageDoc.value = null
    }
    await loadDocs()
  } catch (e) {
    ElMessage.error(e?.message || '删除失败')
    manageError.value = e?.message || '删除失败'
    manageBusy.value = false
  }
}

watch([activeScope, filterTeamId], () => loadDocs())
onMounted(async () => {
  await Promise.all([checkStatus(), loadTeams(), loadDocs()])
})
</script>

<style scoped>
.inspire-office-list {
  --io-ink: var(--ds-ink, #111827);
  --io-muted: var(--ds-muted, #6b7280);
  --io-line: var(--ds-border, #e8eaed);
  --io-soft: #f7f8fa;
  --io-accent: var(--ds-orange, #e5481d);
  --io-radius: 14px;
  width: 100%;
}

/* buttons */
.io-btn {
  appearance: none;
  border: 1px solid transparent;
  border-radius: 999px;
  padding: 8px 16px;
  font: 650 13px/1.2 var(--ds-font-sans, inherit);
  cursor: pointer;
  transition: background .15s ease, border-color .15s ease, color .15s ease, opacity .15s ease;
}
.io-btn:disabled { opacity: .5; cursor: not-allowed; }
.io-btn--primary { background: var(--io-accent); color: #fff; }
.io-btn--primary:hover:not(:disabled) { filter: brightness(.96); }
.io-btn--ghost {
  background: #fff;
  border-color: var(--io-line);
  color: var(--io-ink);
}
.io-btn--ghost:hover:not(:disabled) { background: var(--io-soft); }
.io-btn.is-sm { padding: 6px 12px; font-size: 12px; }
.io-btn.is-sm.is-icon {
  width: 30px;
  min-width: 30px;
  padding: 0;
  display: inline-grid;
  place-items: center;
}
.io-btn.is-sm.is-icon svg {
  display: block;
}

:deep(.io-share__trigger.io-btn) {
  appearance: none;
  border: 1px solid transparent;
  background: transparent;
  color: inherit;
  border-radius: 10px;
  cursor: pointer;
  font: inherit;
}
:deep(.io-share__trigger.io-btn.is-sm.is-icon) {
  width: 30px;
  min-width: 30px;
  min-height: 30px;
  padding: 0;
  display: inline-grid;
  place-items: center;
}
:deep(.io-share__trigger.io-btn.is-sm.is-icon:hover) {
  background: var(--io-soft, #f3f4f6);
}
:deep(.io-share__trigger.io-btn.io-btn--ghost:not(.is-icon)) {
  border: 1px solid var(--io-line, #e5e7eb);
  background: #fff;
  min-height: 36px;
  padding: 0 14px;
  border-radius: 10px;
  font: 650 13px/1 inherit;
}
:deep(.io-share__trigger.io-btn.io-btn--ghost:not(.is-icon):hover) {
  background: var(--io-soft, #f3f4f6);
}
.io-icon-btn {
  width: 32px; height: 32px; border: 0; border-radius: 10px;
  background: transparent; color: var(--io-muted); font-size: 20px; line-height: 1; cursor: pointer;
}
.io-icon-btn:hover { background: var(--io-soft); color: var(--io-ink); }

/* alert */
.io-alert {
  display: grid; gap: 2px; margin-bottom: 14px; padding: 12px 14px;
  border-radius: 12px; background: #fff8eb; border: 1px solid #fde7b8; font-size: 13px; color: #92400e;
}
.io-alert strong { font-weight: 700; }

/* toolbar */
.io-toolbar {
  display: flex; flex-wrap: wrap; align-items: center; justify-content: space-between;
  gap: 12px; margin-bottom: 14px;
}
.io-tabs {
  display: inline-flex; flex-wrap: wrap; gap: 2px; padding: 3px;
  border-radius: 999px; background: var(--io-soft); border: 1px solid var(--io-line);
}
.io-tabs button {
  border: 0; background: transparent; color: var(--io-muted);
  border-radius: 999px; padding: 7px 14px; font: 650 13px/1 inherit; cursor: pointer;
}
.io-tabs button.is-active {
  background: #fff; color: var(--io-ink);
  box-shadow: 0 1px 2px rgba(15, 23, 42, .06);
}
.io-toolbar__right { display: flex; flex-wrap: wrap; gap: 8px; align-items: center; }
.io-control {
  height: 36px; border: 1px solid var(--io-line); border-radius: 10px;
  padding: 0 12px; font-size: 13px; background: #fff; color: var(--io-ink);
}
.io-control:focus { outline: none; border-color: color-mix(in srgb, var(--io-accent) 50%, var(--io-line)); box-shadow: 0 0 0 3px color-mix(in srgb, var(--io-accent) 14%, transparent); }
.io-search {
  display: flex; align-items: center; gap: 8px; height: 36px; min-width: 180px;
  padding: 0 12px; border: 1px solid var(--io-line); border-radius: 999px; background: #fff;
}
.io-search svg { width: 15px; height: 15px; stroke: var(--io-muted); fill: none; stroke-width: 2; flex: 0 0 auto; }
.io-search input {
  border: 0; outline: none; background: transparent; width: 100%; min-width: 0;
  font-size: 13px; color: var(--io-ink);
}

/* panel / list */
.io-panel {
  border: 1px solid var(--io-line); border-radius: var(--io-radius);
  background: #fff; box-shadow: 0 1px 2px rgba(15, 23, 42, .03);
}
.io-list-wrap { overflow: hidden; }
.io-list { list-style: none; margin: 0; padding: 0; }
.io-row {
  display: flex; align-items: center; gap: 10px;
  padding: 4px 10px 4px 6px;
  border-bottom: 1px solid var(--io-line);
}
.io-row:last-child { border-bottom: 0; }
.io-row:hover { background: #fafbfc; }
.io-row__main {
  flex: 1; min-width: 0; display: flex; align-items: center; gap: 12px;
  border: 0; background: transparent; text-align: left; cursor: pointer;
  padding: 10px 8px; border-radius: 12px; color: inherit;
}
.io-row__main:hover { background: transparent; }
.io-type {
  flex: 0 0 auto; width: 40px; height: 40px; border-radius: 12px;
  display: grid; place-items: center; font: 800 14px/1 inherit; color: #fff;
  background: linear-gradient(145deg, #6366f1, #4f46e5);
}
.io-type[data-type='cell'] { background: linear-gradient(145deg, #10b981, #059669); }
.io-type[data-type='slide'] { background: linear-gradient(145deg, #f97316, #ea580c); }
.io-type[data-type='sdoc'] { background: linear-gradient(145deg, #c43a12, #e84a1c); }
.io-row__body { min-width: 0; display: grid; gap: 4px; }
.io-row__title {
  font-size: 14px; font-weight: 650; line-height: 1.35;
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}
.io-row__meta {
  display: flex; flex-wrap: wrap; gap: 6px 10px; color: var(--io-muted); font-size: 12px;
}
.io-row__meta em { font-style: normal; }
.io-row__meta em.is-sync { color: #2563eb; font-weight: 650; }
.io-row__actions {
  display: flex; flex-wrap: wrap; gap: 6px; flex: 0 0 auto;
  opacity: .72; transition: opacity .15s ease;
}
.io-row:hover .io-row__actions { opacity: 1; }

/* empty */
.io-empty {
  min-height: 280px; padding: 40px 20px;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
  gap: 8px; text-align: center; color: var(--io-muted);
}
.io-empty__icon { width: 56px; height: 56px; color: #c4c9d2; margin-bottom: 4px; }
.io-empty__icon svg { width: 100%; height: 100%; }
.io-empty strong { font-size: 16px; color: var(--io-ink); }
.io-empty p { margin: 0 0 10px; font-size: 13px; max-width: 320px; line-height: 1.5; }
.io-empty__actions { display: flex; gap: 10px; flex-wrap: wrap; justify-content: center; }
.io-spinner {
  width: 22px; height: 22px; border-radius: 50%;
  border: 2px solid #e5e7eb; border-top-color: var(--io-accent);
  animation: io-spin .7s linear infinite;
}
@keyframes io-spin { to { transform: rotate(360deg); } }

/* modal */
.io-modal {
  position: fixed; inset: 0; z-index: 1200; display: grid; place-items: center;
  background: rgba(15, 23, 42, .42); padding: 16px;
  backdrop-filter: blur(4px);
}
.io-dialog {
  width: min(420px, 100%); max-height: min(90vh, 760px);
  display: flex; flex-direction: column;
  background: #fff; border-radius: 18px;
  box-shadow: 0 24px 64px rgba(15, 23, 42, .18);
  overflow: hidden;
}
.io-dialog.is-wide { width: min(520px, 100%); }
.io-dialog__head {
  display: flex; align-items: flex-start; justify-content: space-between; gap: 12px;
  padding: 16px 18px 12px; border-bottom: 1px solid var(--io-line);
}
.io-dialog__head h2 { margin: 0; font-size: 17px; font-weight: 700; }
.io-dialog__title { min-width: 0; }
.io-dialog__title p {
  margin: 4px 0 0; font-size: 12px; color: var(--io-muted);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 360px;
}
.io-dialog__body {
  padding: 16px 18px; display: grid; gap: 14px; overflow: auto;
}
.io-dialog__foot {
  display: flex; justify-content: flex-end; gap: 8px;
  padding: 12px 18px 16px; border-top: 1px solid var(--io-line); background: #fafbfc;
}

.io-field { display: grid; gap: 6px; font-size: 12px; color: var(--io-muted); font-weight: 600; }
.io-field > .io-control, .io-field > :deep(.drop-file-upload) { font-weight: 400; }
.io-choice {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px;
}
.io-choice.is-compact { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.io-choice button {
  border: 1px solid var(--io-line); background: #fff; border-radius: 12px;
  padding: 12px 8px; cursor: pointer; display: grid; gap: 6px; place-items: center;
  color: var(--io-ink); font: 650 12px/1.2 inherit; transition: border-color .15s, background .15s, box-shadow .15s;
}
.io-choice.is-compact button { padding: 8px 10px; border-radius: 999px; }
.io-choice button b {
  width: 32px; height: 32px; border-radius: 10px; display: grid; place-items: center;
  color: #fff; font-size: 13px; background: #6366f1;
}
.io-choice button b[data-type='cell'] { background: #10b981; }
.io-choice button b[data-type='slide'] { background: #f97316; }
.io-choice button b[data-type='sdoc'] { background: #c43a12; }
.io-choice button.is-active {
  border-color: color-mix(in srgb, var(--io-accent) 55%, var(--io-line));
  background: color-mix(in srgb, var(--io-accent) 7%, #fff);
  box-shadow: 0 0 0 3px color-mix(in srgb, var(--io-accent) 12%, transparent);
}
.io-choice button:disabled { opacity: .5; cursor: not-allowed; }

.io-tip {
  margin: 0; padding: 8px 10px; border-radius: 10px; font-size: 12px; line-height: 1.45; font-weight: 400;
  color: #1e3a8a; background: #eff6ff; border: 1px solid #dbeafe;
}
.io-tip.is-muted { color: var(--io-muted); background: var(--io-soft); border-color: var(--io-line); }
.io-error { margin: 0; color: #b91c1c; font-size: 13px; font-weight: 600; }

.io-meta-chips { display: flex; flex-wrap: wrap; gap: 6px; }
.io-meta-chips span {
  font-size: 11px; font-weight: 650; padding: 3px 8px; border-radius: 999px;
  background: var(--io-soft); color: var(--io-muted);
}
.io-meta-chips span.is-sync { background: #eff6ff; color: #2563eb; }

.io-block {
  display: grid; gap: 10px; padding-top: 4px;
  border-top: 1px solid var(--io-line);
}
.io-block:first-of-type { border-top: 0; padding-top: 0; }
.io-block h3 { margin: 0; font-size: 13px; font-weight: 700; color: var(--io-ink); }
.io-inline { display: flex; gap: 8px; align-items: center; }
.io-inline .io-control { flex: 1; min-width: 0; }

.io-actions-grid {
  display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px;
}
.io-action {
  border: 1px solid var(--io-line); border-radius: 12px; background: #fff;
  padding: 12px; text-align: left; cursor: pointer; display: grid; gap: 3px;
  transition: border-color .15s, background .15s;
}
.io-action:hover:not(:disabled) { background: var(--io-soft); border-color: #d1d5db; }
.io-action:disabled { opacity: .45; cursor: not-allowed; }
.io-action strong { font-size: 13px; color: var(--io-ink); }
.io-action span { font-size: 11px; color: var(--io-muted); }
.io-action.is-danger strong { color: #b91c1c; }
.io-action.is-danger:hover:not(:disabled) { background: #fef2f2; border-color: #fecaca; }

@media (max-width: 720px) {
  .io-row { flex-direction: column; align-items: stretch; padding: 8px; gap: 4px; }
  .io-row__actions { opacity: 1; padding: 0 8px 8px; }
  .io-actions-grid { grid-template-columns: 1fr; }
  .io-dialog__title p { max-width: 70vw; }
}

/* header action alignment within AiAppHeader */
.inspire-office-list :deep(.ai-app-header__actions) {
  display: flex; gap: 8px; align-items: center;
}
</style>
