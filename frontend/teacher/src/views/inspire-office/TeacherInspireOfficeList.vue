<template>
  <div class="teacher-page tio">
    <header class="teacher-page__head">
      <div>
        <h1>启发 Office</h1>
        <p>打开团队智能文档，与学生同一套编辑器。Word / 表格 / 演示仍走学生端协同编辑。</p>
      </div>
      <div class="teacher-page__actions">
        <button type="button" class="teacher-btn teacher-btn--primary" @click="showCreate = true">新建智能文档</button>
      </div>
    </header>

    <section class="teacher-card">
      <div class="teacher-card__body">
        <div v-if="loading" class="teacher-empty">加载中…</div>
        <table v-else class="teacher-table">
          <thead>
            <tr>
              <th>文档</th>
              <th>类型</th>
              <th>归属</th>
              <th>更新</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="doc in docs" :key="doc.id">
              <td>{{ doc.title || '未命名' }}</td>
              <td>{{ typeLabel(doc) }}</td>
              <td>{{ scopeLabel(doc) }}</td>
              <td>{{ formatTime(doc.updatedAt) }}</td>
              <td>
                <button v-if="isSdoc(doc)" type="button" class="teacher-link" @click="openDoc(doc)">打开</button>
                <span v-else class="teacher-muted">请在学生端打开</span>
              </td>
            </tr>
            <tr v-if="!docs.length">
              <td colspan="5" class="teacher-empty">还没有可访问的文档。新建一篇项目智能文档即可。</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <div v-if="showCreate" class="teacher-modal teacher-overlay-mask" @click.self="showCreate = false">
      <section class="teacher-modal__panel" role="dialog" aria-modal="true">
        <div class="teacher-card__head">
          <h2>新建智能文档</h2>
          <button type="button" class="teacher-link" @click="showCreate = false">关闭</button>
        </div>
        <div class="teacher-card__body form-grid">
          <label>
            <span>标题</span>
            <input v-model="createForm.title" maxlength="200" placeholder="未命名文档" />
          </label>
          <label>
            <span>项目 / 团队</span>
            <select v-model="createForm.teamId">
              <option value="">请选择</option>
              <option v-for="team in teams" :key="team.id" :value="String(team.id)">{{ team.name }}</option>
            </select>
          </label>
          <p v-if="createError" class="teacher-tag is-info">{{ createError }}</p>
          <div class="span-2 modal-actions">
            <button type="button" class="teacher-btn teacher-btn--secondary" @click="showCreate = false">取消</button>
            <button type="button" class="teacher-btn teacher-btn--primary" :disabled="creating" @click="createDoc">
              {{ creating ? '创建中…' : '创建并打开' }}
            </button>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { fetchMyTeams } from '../../api'
import { useTeacherContextStore } from '../../stores/context'
import {
  createBlankInspireOfficeDocument,
  listInspireOfficeDocuments,
} from '../../services/inspireOfficeClient'

const router = useRouter()
const context = useTeacherContextStore()
const docs = ref([])
const teams = ref([])
const loading = ref(true)
const showCreate = ref(false)
const creating = ref(false)
const createError = ref('')
const createForm = reactive({ title: '', teamId: '' })

function isSdoc(doc) {
  return doc?.ext === 'sdoc' || doc?.documentType === 'sdoc'
}

function typeLabel(doc) {
  if (isSdoc(doc)) return '智能文档'
  if (doc.documentType === 'cell' || doc.documentType === 'sheet') return '表格'
  if (doc.documentType === 'slide') return '演示'
  return 'Word'
}

function scopeLabel(doc) {
  const map = { personal: '个人', project: '项目', team: '团队' }
  const scope = map[doc.scope] || doc.scope || ''
  return [scope, doc.teamName].filter(Boolean).join(' · ')
}

function formatTime(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return String(value).slice(0, 16)
  return d.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function openDoc(doc) {
  router.push({ name: 'TeacherSmartDoc', params: { id: String(doc.id) } })
}

async function load() {
  loading.value = true
  try {
    docs.value = await listInspireOfficeDocuments({ scope: 'all' })
  } catch (err) {
    docs.value = []
    ElMessage.error(err?.message || '加载文档失败')
  } finally {
    loading.value = false
  }
}

async function createDoc() {
  if (!createForm.teamId) {
    createError.value = '请选择项目/团队，教师文档会进团队空间，学生才能一起写'
    return
  }
  creating.value = true
  createError.value = ''
  try {
    const doc = await createBlankInspireOfficeDocument({
      title: createForm.title || undefined,
      ext: 'sdoc',
      scope: 'project',
      teamId: Number(createForm.teamId),
    })
    showCreate.value = false
    createForm.title = ''
    if (doc?.id) openDoc(doc)
  } catch (err) {
    createError.value = err?.message || '创建失败'
  } finally {
    creating.value = false
  }
}

onMounted(async () => {
  try {
    teams.value = await fetchMyTeams()
  } catch {
    teams.value = []
  }
  const current = context.teamId && context.teamId !== 'all' ? String(context.teamId) : ''
  createForm.teamId = current || (teams.value[0] ? String(teams.value[0].id) : '')
  await load()
})
</script>

<style scoped>
.form-grid { display: grid; gap: 12px; }
.form-grid label { display: grid; gap: 6px; font-size: 13px; }
.form-grid input,
.form-grid select {
  height: 36px;
  border: 1px solid #e5e6ea;
  border-radius: 8px;
  padding: 0 10px;
}
.span-2 { grid-column: 1 / -1; }
.modal-actions { display: flex; justify-content: flex-end; gap: 8px; }
</style>
