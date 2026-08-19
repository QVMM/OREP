<template>
  <div class="teacher-page">
    <header class="teacher-page__head">
      <div>
        <h1>训练营管理</h1>
        <p>{{ data.hasCamp ? `${camp.campName || ctx.campName} · 所属项目 ${ctx.projectName}` : '创建训练营后，在这里查看任务、提交和成员进度' }}</p>
      </div>
      <div v-if="data.hasCamp" class="teacher-page__actions">
        <div class="camp-manage">
          <button type="button" class="teacher-btn teacher-btn--secondary" @click="manageOpen = !manageOpen">管理训练营</button>
          <div v-if="manageOpen" class="camp-manage__menu">
            <button type="button" @click="openScheduleDialog">调整开始日期</button>
            <button type="button" class="is-danger" @click="openDeleteDialog">删除训练营</button>
          </div>
        </div>
        <router-link class="teacher-btn teacher-btn--secondary" :to="planLink">每日计划</router-link>
        <router-link class="teacher-btn teacher-btn--primary" to="/camp/review-queue">提交与批改</router-link>
      </div>
      <router-link v-else class="teacher-btn teacher-btn--primary" to="/camp/create">创建训练营</router-link>
    </header>

    <section v-if="!data.hasCamp" class="teacher-card camp-empty-state">
      <span>营</span>
      <h2>还没有训练营</h2>
      <p>选择所属项目和日期，系统会生成逐日草稿；老师发布后学生端立即同步。</p>
      <router-link class="teacher-btn teacher-btn--primary" to="/camp/create">创建第一个训练营</router-link>
    </section>

    <template v-else>
    <div class="teacher-stat-row">
      <div class="teacher-card teacher-stat"><span>今日提交</span><strong>{{ today?.submittedCount || 0 }}/{{ data.memberCount || 0 }}</strong></div>
      <div class="teacher-card teacher-stat"><span>待批改</span><strong class="is-accent">{{ data.pendingReviews || 0 }}</strong></div>
      <div class="teacher-card teacher-stat"><span>风险学生</span><strong>{{ riskCount }}</strong></div>
      <div class="teacher-card teacher-stat"><span>当前天</span><strong>第 {{ camp.currentDay || 0 }} 天</strong></div>
    </div>

    <section class="teacher-card">
      <div class="teacher-card__head">
        <h2>近几日任务</h2>
        <router-link class="teacher-link" :to="planLink">完整计划</router-link>
      </div>
      <div class="teacher-card__body" style="padding-top: 8px">
        <table class="teacher-table">
          <thead>
            <tr>
              <th>天</th>
              <th>日期</th>
              <th>任务</th>
              <th>提交</th>
              <th>状态</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="d in visibleDays" :key="d.dayNo">
              <td>第 {{ d.dayNo }} 天</td>
              <td>{{ formatDate(d.trainingDate) }}</td>
              <td>{{ d.title }}</td>
              <td>{{ d.submittedCount || 0 }}/{{ data.memberCount || 0 }}</td>
              <td><span class="teacher-tag" :class="d.pendingCount ? 'is-warn' : Number(d.submittedCount) >= Number(data.memberCount) ? 'is-ok' : ''">{{ statusLabel(d) }}</span></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
    </template>

    <el-dialog v-model="scheduleDialog" title="调整开始日期" width="520px" append-to-body :close-on-click-modal="false">
      <div class="lifecycle-dialog">
        <div class="schedule-grid">
          <div><span>当前周期</span><strong>{{ fullDate(camp.startDate) }} 至 {{ fullDate(camp.endDate) }}</strong></div>
          <div><span>训练天数</span><strong>{{ totalDays }} 天</strong></div>
        </div>
        <label class="lifecycle-field">
          <span>新的开始日期</span>
          <el-date-picker
            v-model="newStartDate"
            type="date"
            value-format="YYYY-MM-DD"
            format="YYYY/MM/DD"
            placeholder="选择新的开始日期"
          />
        </label>
        <div class="schedule-preview">
          <span>调整后周期</span>
          <strong>{{ newStartDate ? `${fullDate(newStartDate)} 至 ${fullDate(newEndDate)}` : '请选择开始日期' }}</strong>
          <small>结束日期、每日开放时间和截止时间会按原总天数整体平移。</small>
        </div>
        <p v-if="hasSubmissions" class="lifecycle-warning">已有学生提交，不能直接改期。请保留归档，或彻底删除后重新创建。</p>
      </div>
      <template #footer>
        <button type="button" class="teacher-btn teacher-btn--secondary" @click="scheduleDialog = false">取消</button>
        <button type="button" class="teacher-btn teacher-btn--primary" :disabled="saving || hasSubmissions || !newStartDate || newStartDate === camp.startDate" @click="saveSchedule">
          {{ saving ? '正在调整…' : '确认调整' }}
        </button>
      </template>
    </el-dialog>

    <el-dialog v-model="deleteDialog" title="删除集训" width="560px" append-to-body :close-on-click-modal="false">
      <div class="lifecycle-dialog">
        <el-radio-group v-model="deleteForm.mode" class="delete-mode">
          <el-radio-button value="ARCHIVE">归档保留记录</el-radio-button>
          <el-radio-button value="PURGE">彻底删除全部信息</el-radio-button>
        </el-radio-group>
        <div v-if="deleteForm.mode === 'ARCHIVE'" class="delete-explain">
          集训将从当前列表隐藏，学生提交、批改、成绩、附件和学习记录继续保留。
        </div>
        <div v-else class="delete-explain is-danger">
          <strong>此操作不可恢复</strong>
          <span>将删除本次集训的训练日、任务、提交、批改和专属资源，但不会删除团队与成员。</span>
          <label class="lifecycle-field">
            <span>请输入完整集训名称：{{ camp.campName }}</span>
            <input v-model.trim="deleteForm.confirmationName" :placeholder="camp.campName || '集训名称'" autocomplete="off" />
          </label>
        </div>
      </div>
      <template #footer>
        <button type="button" class="teacher-btn teacher-btn--secondary" @click="deleteDialog = false">取消</button>
        <button type="button" class="teacher-btn" :class="deleteForm.mode === 'PURGE' ? 'lifecycle-danger-btn' : 'teacher-btn--primary'" :disabled="deleting || !canDelete" @click="confirmDelete">
          {{ deleting ? '正在处理…' : deleteForm.mode === 'PURGE' ? '永久删除' : '确认归档' }}
        </button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch } from 'vue'
import { ElDatePicker, ElDialog, ElMessage, ElRadioButton, ElRadioGroup } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { useTeacherContextStore } from '../../stores/context'
import { deleteTeacherCamp, fetchTeacherCamp, rescheduleTeacherCamp } from '../../api'

const ctx = useTeacherContextStore()
const route = useRoute()
const router = useRouter()
const data = ref({ hasCamp: false, days: [], progress: [], memberCount: 0, pendingReviews: 0, submissionCount: 0, camp: {} })
const manageOpen = ref(false)
const scheduleDialog = ref(false)
const deleteDialog = ref(false)
const saving = ref(false)
const deleting = ref(false)
const newStartDate = ref('')
const deleteForm = reactive({ mode: 'ARCHIVE', confirmationName: '' })
const camp = computed(() => data.value.camp || {})
const totalDays = computed(() => Number(camp.value.totalDays || data.value.days?.length || 0))
const newEndDate = computed(() => addDays(newStartDate.value, Math.max(0, totalDays.value - 1)))
const hasSubmissions = computed(() => Number(data.value.submissionCount || 0) > 0)
const canDelete = computed(() => deleteForm.mode === 'ARCHIVE'
  || (deleteForm.confirmationName && deleteForm.confirmationName === camp.value.campName))
const planLink = computed(() => ({ path: '/camp/plan', query: camp.value.campId ? { campId: camp.value.campId } : {} }))
const today = computed(() => data.value.days?.find((d) => Number(d.dayNo) === Number(camp.value.currentDay)))
const visibleDays = computed(() => {
  const day = Number(camp.value.currentDay || 1)
  return (data.value.days || []).filter((d) => Math.abs(Number(d.dayNo) - day) <= 3)
})
const riskCount = computed(() => (data.value.progress || []).filter((m) => (m.days || []).some((d) => ['EXPIRED', 'NOT_SUBMITTED'].includes(d.status) && new Date(d.trainingDate) <= new Date())).length)
function formatDate(value) { return value ? String(value).slice(5).replace('-', '/') : '—' }
function fullDate(value) { return value ? String(value).slice(0, 10).replaceAll('-', '/') : '—' }
function addDays(value, days) {
  if (!value) return ''
  const [year, month, day] = String(value).slice(0, 10).split('-').map(Number)
  const date = new Date(Date.UTC(year, month - 1, day + days))
  return date.toISOString().slice(0, 10)
}
function statusLabel(day) {
  if (Number(day.pendingCount) > 0) return '批改中'
  if (Number(day.submittedCount) >= Number(data.value.memberCount) && Number(data.value.memberCount) > 0) return '已提交'
  if (Number(day.dayNo) === Number(camp.value.currentDay)) return '进行中'
  return Number(day.dayNo) < Number(camp.value.currentDay) ? '有缺交' : '未开始'
}
function openScheduleDialog() {
  manageOpen.value = false
  newStartDate.value = String(camp.value.startDate || '').slice(0, 10)
  scheduleDialog.value = true
}
function openDeleteDialog() {
  manageOpen.value = false
  deleteForm.mode = 'ARCHIVE'
  deleteForm.confirmationName = ''
  deleteDialog.value = true
}
async function saveSchedule() {
  if (!camp.value.campId || !newStartDate.value || hasSubmissions.value) return
  saving.value = true
  try {
    await rescheduleTeacherCamp(camp.value.campId, newStartDate.value)
    scheduleDialog.value = false
    await load()
    ElMessage.success('集训日期已整体调整')
  } catch (error) {
    ElMessage.error(error?.response?.data?.message || error?.message || '调整集训日期失败')
  } finally {
    saving.value = false
  }
}
async function confirmDelete() {
  if (!camp.value.campId || !canDelete.value) return
  deleting.value = true
  try {
    await deleteTeacherCamp(camp.value.campId, {
      mode: deleteForm.mode,
      confirmationName: deleteForm.mode === 'PURGE' ? deleteForm.confirmationName : undefined,
    })
    deleteDialog.value = false
    ctx.setCamp('')
    await router.replace('/camp')
    await load()
    ElMessage.success(deleteForm.mode === 'PURGE' ? '集训已永久删除' : '集训已归档')
  } catch (error) {
    ElMessage.error(error?.response?.data?.message || error?.message || '删除集训失败')
  } finally {
    deleting.value = false
  }
}
async function load() {
  const campId = route.query.campId || ctx.campId || ''
  data.value = await fetchTeacherCamp(campId)
}
watch([() => route.query.campId, () => ctx.campId], load, { immediate: true })
</script>

<style scoped>
.camp-empty-state{padding:64px 24px;text-align:center}.camp-empty-state>span{width:56px;height:56px;margin:auto;border-radius:18px;display:grid;place-items:center;color:var(--ds-orange);background:var(--ds-orange-wash);font-weight:900}.camp-empty-state h2{margin:16px 0 6px;font-size:20px}.camp-empty-state p{margin:0 auto 20px;max-width:500px;color:var(--ds-muted);font-size:13px;line-height:1.7}
.camp-manage{position:relative}.camp-manage__menu{position:absolute;z-index:20;top:calc(100% + 8px);right:0;width:156px;padding:6px;border:1px solid var(--ds-line);border-radius:8px;background:#fff;box-shadow:0 12px 32px rgba(15,23,42,.14)}.camp-manage__menu button{width:100%;height:38px;padding:0 10px;border:0;border-radius:6px;background:transparent;color:var(--ds-ink);font:700 13px/1 var(--ds-font-sans);text-align:left;cursor:pointer}.camp-manage__menu button:hover{background:var(--ds-surface-soft)}.camp-manage__menu button.is-danger{color:#c9382b}.lifecycle-dialog{display:grid;gap:18px}.schedule-grid{display:grid;grid-template-columns:1fr 120px;gap:12px}.schedule-grid>div,.schedule-preview,.delete-explain{padding:14px;border:1px solid var(--ds-line);border-radius:8px;background:var(--ds-surface-soft)}.schedule-grid span,.schedule-grid strong,.schedule-preview span,.schedule-preview strong,.schedule-preview small{display:block}.schedule-grid span,.schedule-preview span{color:var(--ds-muted);font-size:12px}.schedule-grid strong,.schedule-preview strong{margin-top:5px;font-size:14px}.schedule-preview small{margin-top:7px;color:var(--ds-muted);font-size:11px;line-height:1.6}.lifecycle-field{display:grid;gap:8px;color:var(--ds-muted);font-size:12px;font-weight:700}.lifecycle-field :deep(.el-date-editor){width:100%}.lifecycle-field input{width:100%;height:42px;box-sizing:border-box;padding:0 12px;border:1px solid var(--ds-input-border);border-radius:8px;background:#fff;color:var(--ds-ink);font:500 13px/1 var(--ds-font-sans)}.lifecycle-warning{margin:0;padding:12px;border-left:3px solid #d98200;background:#fff7e8;color:#8a5300;font-size:12px;line-height:1.6}.delete-mode{width:100%}.delete-mode :deep(.el-radio-button){width:50%}.delete-mode :deep(.el-radio-button__inner){width:100%}.delete-explain{color:var(--ds-muted);font-size:12px;line-height:1.7}.delete-explain.is-danger{display:grid;gap:8px;border-color:rgba(201,56,43,.24);background:#fff6f4}.delete-explain.is-danger>strong{color:#b42318;font-size:14px}.lifecycle-danger-btn{color:#fff;background:#c9382b;border-color:#c9382b}.lifecycle-danger-btn:disabled{opacity:.45;cursor:not-allowed}@media(max-width:680px){.teacher-page__actions{flex-wrap:wrap}.schedule-grid{grid-template-columns:1fr}.camp-manage__menu{left:0;right:auto}}
</style>
