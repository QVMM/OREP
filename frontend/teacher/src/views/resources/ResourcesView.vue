<template>
  <div class="teacher-page">
    <header class="teacher-page__head">
      <div>
        <h1>{{ scopeTitle }}</h1>
        <p>{{ scopeDesc }}</p>
      </div>
      <div class="teacher-page__actions">
        <button type="button" class="teacher-btn teacher-btn--primary" @click="open = true">{{ scope === 'public' ? '发布公共资源' : '上传资源' }}</button>
      </div>
    </header>
    <p v-if="msg" class="teacher-tag is-info" style="margin-bottom: 12px">{{ msg }}</p>
    <section class="teacher-card">
      <div class="teacher-card__body" style="padding-top: 8px">
        <table class="teacher-table">
          <thead>
            <tr>
              <th>文件</th>
              <th>所属空间</th>
              <th>类型</th>
              <th>审核状态</th>
              <th>更新</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="f in list" :key="f.id">
              <td>{{ f.name }}</td>
              <td>{{ scope === 'public' ? '平台公共资源' : (f.teamName || context.projectName) }}</td>
              <td>{{ materialTypeLabel(f.materialType) }}</td>
              <td><span class="teacher-tag" :class="f.reviewStatus === 'APPROVED' ? 'is-ok' : 'is-info'">{{ materialReviewLabel(f.reviewStatus) }}</span></td>
              <td>{{ formatDate(f.updatedAt) }}</td>
              <td><a v-if="f.fileUrl" class="teacher-link" :href="f.fileUrl" target="_blank" rel="noopener">打开</a><span v-else class="teacher-muted">无文件链接</span></td>
            </tr>
            <tr v-if="!list.length"><td colspan="6" class="teacher-empty">{{ scope === 'public' ? '尚无公共资源' : '尚无项目资源' }}</td></tr>
          </tbody>
        </table>
      </div>
    </section>
    <Teleport to="body">
      <div
        v-if="open"
        class="teacher-modal teacher-overlay-mask"
        role="presentation"
        @click.self="open = false"
      >
        <section class="teacher-modal__panel" role="dialog" aria-modal="true" aria-label="新建资源">
          <div class="teacher-card__head"><h2>{{ scope === 'public' ? '发布公共资源' : '上传项目资源' }}</h2><button class="teacher-link" type="button" @click="open = false">关闭</button></div>
          <div class="teacher-card__body form-grid">
            <label><span>所属项目</span><select v-model="form.teamId"><option v-for="team in teams" :key="team.id" :value="team.id">{{ team.name }}</option></select></label>
            <label><span>资源名称</span><input v-model="form.name" placeholder="例如：路演讲稿 v2" /></label>
            <label><span>资源类型</span><select v-model="form.materialType"><option value="DOCS">文档</option><option value="PPT">PPT</option><option value="SCRIPT">讲稿</option><option value="VIDEO">视频</option><option value="LINK">链接</option></select></label>
            <label><span>文件或链接地址</span><input v-model="form.fileUrl" placeholder="/uploads/... 或 https://..." /></label>
            <label class="span-2"><span>说明</span><textarea v-model="form.description" rows="3" /></label>
            <div class="span-2 modal-actions"><button class="teacher-btn teacher-btn--secondary" type="button" @click="open = false">取消</button><button class="teacher-btn teacher-btn--primary" type="button" :disabled="saving || !form.teamId || !form.name" @click="save">确认创建</button></div>
          </div>
        </section>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'
import { createTeamMaterial, fetchMyTeams, fetchTeacherResources } from '../../api'
import { useTeacherContextStore } from '../../stores/context'
import { materialReviewLabel, materialTypeLabel } from '../../utils/labels'
const route = useRoute()
const context = useTeacherContextStore()
const list = ref([])
const teams = ref([])
const msg = ref('')
const open = ref(false)
const saving = ref(false)
const form = reactive({ teamId: '', name: '', materialType: 'DOCS', fileUrl: '', description: '' })
const scope = computed(() => (route.query.scope === 'public' ? 'public' : 'team'))
const scopeTitle = computed(() => (scope.value === 'public' ? '公共资源' : '团队资源'))
const scopeDesc = computed(() =>
  scope.value === 'public'
    ? '面向学生的平台公共资源：评分标准、优秀案例、课程与视频等。'
    : `按当前项目展示资源目录与文件列表。当前项目：${context.projectName}。`
)

function formatDate(value) { return value ? new Date(value).toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' }) : '—' }
async function load() {
  [list.value, teams.value] = await Promise.all([fetchTeacherResources(), fetchMyTeams()])
  if (!form.teamId) {
    const preferredId = context.teamId !== 'all' ? context.teamId : context.projectId
    form.teamId = teams.value.some((team) => String(team.id) === String(preferredId)) ? preferredId : (teams.value[0]?.id || '')
  }
}
async function save() { saving.value = true; try { await createTeamMaterial(form.teamId, { name: form.name, materialType: form.materialType, fileUrl: form.fileUrl || null, description: form.description }); open.value = false; msg.value = '资源已写入数据库，学生文件中心可同步查看'; form.name = ''; form.fileUrl = ''; form.description = ''; await load() } finally { saving.value = false } }
onMounted(load)
</script>

<style scoped>
.teacher-modal{display:grid;place-items:center}
.teacher-modal__panel{width:min(620px,calc(100vw - 32px));border-radius:18px;background:#fff;box-shadow:0 24px 70px rgba(29,29,31,.22)}
.form-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.form-grid label{display:grid;gap:6px;font-size:12px;font-weight:700;color:var(--ds-muted)}.form-grid input,.form-grid select,.form-grid textarea{border:1px solid var(--ds-line);border-radius:10px;padding:10px 12px;font:inherit;color:var(--ds-ink);background:#fff}.span-2{grid-column:1/-1}.modal-actions{display:flex;justify-content:flex-end;gap:10px}
</style>
