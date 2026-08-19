<template>
  <div class="teacher-page camp-workspace">
    <header class="teacher-page__head camp-workspace__head">
      <div>
        <h1>训练营</h1>
        <p>
          <template v-if="hasCamp">
            {{ projectTitle }} · {{ campTitle }}
            <span v-if="dateRangeLabel"> · {{ dateRangeLabel }}</span>
            <span v-if="campMeta.currentDay"> · 第 {{ campMeta.currentDay }} 天</span>
          </template>
          <template v-else>
            创建训练营后，在这里编排每日任务、查看提交概况
          </template>
        </p>
      </div>
      <div class="teacher-page__actions">
        <template v-if="hasCamp">
          <div class="camp-manage" @keydown.esc="manageOpen = false">
            <button
              type="button"
              class="teacher-btn teacher-btn--secondary"
              :aria-expanded="manageOpen"
              @click="manageOpen = !manageOpen"
            >
              管理
            </button>
            <div v-if="manageOpen" class="camp-manage__menu" role="menu">
              <button type="button" role="menuitem" @click="openExtendDialog">延长训练天数</button>
              <button type="button" role="menuitem" @click="openScheduleDialog">调整开始日期</button>
              <button type="button" role="menuitem" class="is-danger" @click="openDeleteDialog">删除训练营</button>
            </div>
          </div>
          <router-link class="teacher-btn teacher-btn--secondary" to="/camp/review-queue">
            提交与批改
          </router-link>
          <router-link class="teacher-btn teacher-btn--secondary" to="/camp/progress">
            训练进度
          </router-link>
        </template>
        <router-link v-else class="teacher-btn teacher-btn--primary" to="/camp/create">
          创建训练营
        </router-link>
      </div>
    </header>

    <!-- 有营：计划 / 概览 分段；默认计划 -->
    <nav v-if="hasCamp" class="camp-workspace__tabs workspace-tabs" aria-label="训练营分区">
      <button
        type="button"
        :class="{ 'is-active': activeTab === 'plan' }"
        @click="setTab('plan')"
      >
        计划
      </button>
      <button
        type="button"
        :class="{ 'is-active': activeTab === 'overview' }"
        @click="setTab('overview')"
      >
        概览
      </button>
    </nav>

    <!-- 无营：统一空状态（只引导一次） -->
    <section v-if="!loadingShell && !hasCamp" class="teacher-card camp-empty-state">
      <span aria-hidden="true">营</span>
      <h2>还没有训练营</h2>
      <p>选择项目与日期后生成逐日草稿；在「计划」里写任务并发布，学生端会同步看到。</p>
      <router-link class="teacher-btn teacher-btn--primary" to="/camp/create">创建训练营</router-link>
    </section>

    <template v-else-if="hasCamp">
      <p v-if="campEnded" class="camp-extend-hint">
        当前训练营已到原定结束日，但仍可继续加天。新增训练日会以草稿加入计划，发布后学生才能看到。
        <button type="button" class="teacher-link text-button" @click="openExtendDialog">延长天数</button>
      </p>
      <CampPlanView
        v-show="activeTab === 'plan'"
        embedded
        :camp-id-prop="effectiveCampId"
        :reload-nonce="planNonce"
        @extend-days="openExtendDialog"
      />
      <CampOverviewPanel
        v-show="activeTab === 'overview'"
        :camp-id-prop="effectiveCampId"
        @open-schedule="openScheduleDialog"
        @open-delete="openDeleteDialog"
        @goto-plan="setTab('plan')"
      />
    </template>

    <section v-else-if="loadingShell" class="teacher-card teacher-empty">正在加载训练营…</section>

    <el-dialog
      v-model="extendDialog"
      title="延长训练天数"
      width="520px"
      append-to-body
      :close-on-click-modal="false"
    >
      <div class="lifecycle-dialog">
        <div class="schedule-grid">
          <div>
            <span>当前周期</span>
            <strong>{{ fullDate(campMeta.startDate) }} 至 {{ fullDate(campMeta.endDate) }}</strong>
          </div>
          <div>
            <span>当前天数</span>
            <strong>{{ totalDays }} 天</strong>
          </div>
        </div>
        <label class="lifecycle-field">
          <span>再增加天数</span>
          <input
            v-model.number="addedDays"
            type="number"
            min="1"
            max="364"
            step="1"
            inputmode="numeric"
            @input="syncTotalFromAdded"
          />
        </label>
        <label class="lifecycle-field">
          <span>或直接改为总天数</span>
          <input
            v-model.number="targetTotalDays"
            type="number"
            :min="totalDays + 1"
            max="365"
            step="1"
            inputmode="numeric"
            @input="syncAddedFromTotal"
          />
        </label>
        <div class="schedule-preview">
          <span>延长后周期</span>
          <strong>
            {{
              previewTotalDays > totalDays
                ? `${fullDate(campMeta.startDate)} 至 ${fullDate(previewEndDate)} · 共 ${previewTotalDays} 天`
                : '请输入要增加的天数'
            }}
          </strong>
          <small>只在营期后面追加新的训练日草稿，已有任务、提交和批改记录保持不变。老师编好后发布，学生端才会看到新的一天。</small>
        </div>
        <p v-if="previewStillEnded" class="lifecycle-warning">
          按这个天数延长后，结束日仍早于今天。若训练还要继续，建议至少加到 {{ suggestedTotalDays }} 天。
        </p>
      </div>
      <template #footer>
        <button type="button" class="teacher-btn teacher-btn--secondary" @click="extendDialog = false">
          取消
        </button>
        <button
          type="button"
          class="teacher-btn teacher-btn--primary"
          :disabled="extending || previewTotalDays <= totalDays"
          @click="saveExtend"
        >
          {{ extending ? '正在延长…' : `确认延长到 ${previewTotalDays} 天` }}
        </button>
      </template>
    </el-dialog>

    <!-- 生命周期对话框（改期 / 删除）挂在工作台壳层，计划与概览共用 -->
    <el-dialog
      v-model="scheduleDialog"
      title="调整开始日期"
      width="520px"
      append-to-body
      :close-on-click-modal="false"
    >
      <div class="lifecycle-dialog">
        <div class="schedule-grid">
          <div>
            <span>当前周期</span>
            <strong>{{ fullDate(campMeta.startDate) }} 至 {{ fullDate(campMeta.endDate) }}</strong>
          </div>
          <div>
            <span>训练天数</span>
            <strong>{{ totalDays }} 天</strong>
          </div>
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
          <strong>
            {{ newStartDate ? `${fullDate(newStartDate)} 至 ${fullDate(newEndDate)}` : '请选择开始日期' }}
          </strong>
          <small>结束日期、每日开放与截止时间会按原总天数整体平移。</small>
        </div>
        <p v-if="hasSubmissions" class="lifecycle-warning">
          已有学生提交，不能直接改期。请保留归档，或彻底删除后重新创建。
        </p>
      </div>
      <template #footer>
        <button type="button" class="teacher-btn teacher-btn--secondary" @click="scheduleDialog = false">
          取消
        </button>
        <button
          type="button"
          class="teacher-btn teacher-btn--primary"
          :disabled="
            saving ||
            hasSubmissions ||
            !newStartDate ||
            newStartDate === String(campMeta.startDate || '').slice(0, 10)
          "
          @click="saveSchedule"
        >
          {{ saving ? '正在调整…' : '确认调整' }}
        </button>
      </template>
    </el-dialog>

    <el-dialog
      v-model="deleteDialog"
      title="删除集训"
      width="560px"
      append-to-body
      :close-on-click-modal="false"
    >
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
            <span>请输入完整集训名称：{{ campMeta.campName }}</span>
            <input
              v-model.trim="deleteForm.confirmationName"
              :placeholder="campMeta.campName || '集训名称'"
              autocomplete="off"
            />
          </label>
        </div>
      </div>
      <template #footer>
        <button type="button" class="teacher-btn teacher-btn--secondary" @click="deleteDialog = false">
          取消
        </button>
        <button
          type="button"
          class="teacher-btn"
          :class="deleteForm.mode === 'PURGE' ? 'lifecycle-danger-btn' : 'teacher-btn--primary'"
          :disabled="deleting || !canDelete"
          @click="confirmDelete"
        >
          {{ deleting ? '正在处理…' : deleteForm.mode === 'PURGE' ? '永久删除' : '确认归档' }}
        </button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { ElDatePicker, ElDialog, ElMessage, ElRadioButton, ElRadioGroup } from 'element-plus'
import { useRoute, useRouter } from 'vue-router'
import { deleteTeacherCamp, extendTeacherCamp, fetchTeacherCamp, rescheduleTeacherCamp } from '../../api'
import { useTeacherContextStore } from '../../stores/context'
import CampPlanView from './CampPlanView.vue'
import CampOverviewPanel from './CampOverviewPanel.vue'

const ctx = useTeacherContextStore()
const route = useRoute()
const router = useRouter()

const loadingShell = ref(true)
const shellData = ref({ hasCamp: false, camp: {}, submissionCount: 0, days: [] })
const manageOpen = ref(false)
const scheduleDialog = ref(false)
const extendDialog = ref(false)
const deleteDialog = ref(false)
const saving = ref(false)
const extending = ref(false)
const deleting = ref(false)
const newStartDate = ref('')
const addedDays = ref(7)
const targetTotalDays = ref(0)
const planNonce = ref(0)
const deleteForm = reactive({ mode: 'ARCHIVE', confirmationName: '' })

const effectiveCampId = computed(() => String(route.query.campId || ctx.campId || ''))
const hasCamp = computed(() => Boolean(shellData.value.hasCamp && shellData.value.camp?.campId))
const campMeta = computed(() => shellData.value.camp || {})
const projectTitle = computed(() => ctx.projectName || '当前项目')
const campTitle = computed(() => campMeta.value.campName || ctx.campName || '训练营')
const dateRangeLabel = computed(() => {
  const s = campMeta.value.startDate
  const e = campMeta.value.endDate
  if (!s || !e) return ''
  return `${String(s).slice(0, 10)} 至 ${String(e).slice(0, 10)}`
})
const totalDays = computed(() => Number(campMeta.value.totalDays || shellData.value.days?.length || 0))
const newEndDate = computed(() => addDays(newStartDate.value, Math.max(0, totalDays.value - 1)))
const previewTotalDays = computed(() => {
  const target = Number(targetTotalDays.value)
  if (Number.isFinite(target) && target > totalDays.value) return Math.min(365, Math.floor(target))
  return totalDays.value
})
const previewEndDate = computed(() => addDays(campMeta.value.startDate, Math.max(0, previewTotalDays.value - 1)))
const todayText = computed(() => {
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
})
const campEnded = computed(() => {
  const end = String(campMeta.value.endDate || '').slice(0, 10)
  return Boolean(end && end < todayText.value)
})
const previewStillEnded = computed(() => {
  const end = String(previewEndDate.value || '').slice(0, 10)
  return previewTotalDays.value > totalDays.value && Boolean(end && end < todayText.value)
})
const suggestedTotalDays = computed(() => {
  const start = String(campMeta.value.startDate || '').slice(0, 10)
  if (!start) return totalDays.value + 7
  const [y, m, d] = start.split('-').map(Number)
  const startUtc = Date.UTC(y, m - 1, d)
  const [ty, tm, td] = todayText.value.split('-').map(Number)
  const todayUtc = Date.UTC(ty, tm - 1, td)
  const elapsed = Math.floor((todayUtc - startUtc) / 86400000) + 1
  return Math.max(totalDays.value + 1, Math.min(365, elapsed + 7))
})
const hasSubmissions = computed(() => Number(shellData.value.submissionCount || 0) > 0)
const canDelete = computed(
  () =>
    deleteForm.mode === 'ARCHIVE' ||
    (deleteForm.confirmationName && deleteForm.confirmationName === campMeta.value.campName)
)

const activeTab = computed(() => {
  const t = String(route.query.tab || 'plan').toLowerCase()
  return t === 'overview' ? 'overview' : 'plan'
})

function setTab(tab) {
  const next = tab === 'overview' ? 'overview' : 'plan'
  const query = { ...route.query, tab: next }
  if (effectiveCampId.value) query.campId = effectiveCampId.value
  router.replace({ path: '/camp', query })
}

function fullDate(value) {
  return value ? String(value).slice(0, 10).replaceAll('-', '/') : '—'
}

function addDays(value, days) {
  if (!value) return ''
  const [year, month, day] = String(value).slice(0, 10).split('-').map(Number)
  const date = new Date(Date.UTC(year, month - 1, day + days))
  return date.toISOString().slice(0, 10)
}

function openScheduleDialog() {
  manageOpen.value = false
  newStartDate.value = String(campMeta.value.startDate || '').slice(0, 10)
  scheduleDialog.value = true
}

function syncAddedFromTotal() {
  const next = Number(targetTotalDays.value)
  if (!Number.isFinite(next)) return
  addedDays.value = Math.max(1, Math.floor(next) - totalDays.value)
}

function syncTotalFromAdded() {
  const extra = Number(addedDays.value)
  if (!Number.isFinite(extra) || extra < 1) return
  targetTotalDays.value = Math.min(365, totalDays.value + Math.floor(extra))
}

function openExtendDialog() {
  manageOpen.value = false
  addedDays.value = campEnded.value ? Math.max(1, suggestedTotalDays.value - totalDays.value) : 7
  targetTotalDays.value = Math.min(365, totalDays.value + Number(addedDays.value || 1))
  extendDialog.value = true
}

async function saveExtend() {
  const nextTotal = previewTotalDays.value
  if (!campMeta.value.campId || nextTotal <= totalDays.value) return
  extending.value = true
  try {
    await extendTeacherCamp(campMeta.value.campId, { totalDays: nextTotal })
    extendDialog.value = false
    planNonce.value += 1
    await loadShell()
    ElMessage.success(`训练营已延长到 ${nextTotal} 天，新的训练日已加入计划草稿`)
  } catch (error) {
    ElMessage.error(error?.response?.data?.message || error?.message || '延长训练营失败')
  } finally {
    extending.value = false
  }
}

function openDeleteDialog() {
  manageOpen.value = false
  deleteForm.mode = 'ARCHIVE'
  deleteForm.confirmationName = ''
  deleteDialog.value = true
}

async function saveSchedule() {
  if (!campMeta.value.campId || !newStartDate.value || hasSubmissions.value) return
  saving.value = true
  try {
    await rescheduleTeacherCamp(campMeta.value.campId, newStartDate.value)
    scheduleDialog.value = false
    await loadShell()
    ElMessage.success('集训日期已整体调整')
  } catch (error) {
    ElMessage.error(error?.response?.data?.message || error?.message || '调整集训日期失败')
  } finally {
    saving.value = false
  }
}

async function confirmDelete() {
  if (!campMeta.value.campId || !canDelete.value) return
  deleting.value = true
  try {
    await deleteTeacherCamp(campMeta.value.campId, {
      mode: deleteForm.mode,
      confirmationName: deleteForm.mode === 'PURGE' ? deleteForm.confirmationName : undefined,
    })
    deleteDialog.value = false
    ctx.setCamp('')
    await router.replace('/camp')
    await loadShell()
    ElMessage.success(deleteForm.mode === 'PURGE' ? '集训已永久删除' : '集训已归档')
  } catch (error) {
    ElMessage.error(error?.response?.data?.message || error?.message || '删除集训失败')
  } finally {
    deleting.value = false
  }
}

async function loadShell() {
  loadingShell.value = true
  try {
    const campId = effectiveCampId.value
    shellData.value = await fetchTeacherCamp(campId)
    if (shellData.value?.camp?.campId) {
      ctx.setCamp(String(shellData.value.camp.campId))
    }
  } catch {
    shellData.value = { hasCamp: false, camp: {}, submissionCount: 0, days: [] }
  } finally {
    loadingShell.value = false
  }
}

function onDocClick(e) {
  if (!manageOpen.value) return
  const el = e.target
  if (el?.closest?.('.camp-manage')) return
  manageOpen.value = false
}

watch([() => route.query.campId, () => ctx.campId, () => ctx.loaded], loadShell, { immediate: true })

onMounted(() => {
  document.addEventListener('click', onDocClick)
  // 旧书签 /camp?tab= 规范化
  if (!route.query.tab && route.path === '/camp') {
    // 默认 plan，不写 URL 也行；若带 overview 则保留
  }
})

onUnmounted(() => {
  document.removeEventListener('click', onDocClick)
})
</script>

<style scoped>
.camp-workspace__head {
  margin-bottom: 12px;
}

.camp-workspace__tabs {
  margin-bottom: 14px;
}
.camp-extend-hint {
  margin: 0 0 12px;
  padding: 10px 12px;
  border: 1px solid #f0d7a8;
  border-radius: 10px;
  background: #fff8ec;
  color: #8a5300;
  font-size: 13px;
  line-height: 1.6;
}
.camp-extend-hint .teacher-link {
  margin-left: 8px;
}
.text-button {
  border: 0;
  background: transparent;
  cursor: pointer;
  font: inherit;
}

.camp-empty-state {
  padding: 64px 24px;
  text-align: center;
}
.camp-empty-state > span {
  width: 56px;
  height: 56px;
  margin: auto;
  border-radius: 16px;
  display: grid;
  place-items: center;
  color: var(--ds-orange-deep);
  background: var(--ds-orange-wash);
  font-weight: 900;
  font-size: 18px;
}
.camp-empty-state h2 {
  margin: 16px 0 6px;
  font-size: 20px;
}
.camp-empty-state p {
  margin: 0 auto 20px;
  max-width: 480px;
  color: var(--ds-muted);
  font-size: 13px;
  line-height: 1.7;
}

.camp-manage {
  position: relative;
}
.camp-manage__menu {
  position: absolute;
  z-index: 20;
  top: calc(100% + 8px);
  right: 0;
  width: 176px;
  padding: 6px;
  border: 1px solid var(--ds-line);
  border-radius: 12px;
  background: #fff;
  box-shadow: 0 12px 32px rgba(15, 23, 42, 0.12);
}
.camp-manage__menu button {
  width: 100%;
  height: 38px;
  padding: 0 10px;
  border: 0;
  border-radius: 8px;
  background: transparent;
  color: var(--ds-ink);
  font: 700 13px/1 var(--ds-font-sans);
  text-align: left;
  cursor: pointer;
}
.camp-manage__menu button:hover {
  background: #f4f4f5;
}
.camp-manage__menu button.is-danger {
  color: #c9382b;
}

.lifecycle-dialog {
  display: grid;
  gap: 18px;
}
.schedule-grid {
  display: grid;
  grid-template-columns: 1fr 120px;
  gap: 12px;
}
.schedule-grid > div,
.schedule-preview,
.delete-explain {
  padding: 14px;
  border: 1px solid var(--ds-line);
  border-radius: 12px;
  background: #f7f7f8;
}
.schedule-grid span,
.schedule-grid strong,
.schedule-preview span,
.schedule-preview strong,
.schedule-preview small {
  display: block;
}
.schedule-grid span,
.schedule-preview span {
  color: var(--ds-muted);
  font-size: 12px;
}
.schedule-grid strong,
.schedule-preview strong {
  margin-top: 5px;
  font-size: 14px;
}
.schedule-preview small {
  margin-top: 7px;
  color: var(--ds-muted);
  font-size: 11px;
  line-height: 1.6;
}
.lifecycle-field {
  display: grid;
  gap: 8px;
  color: var(--ds-muted);
  font-size: 12px;
  font-weight: 700;
}
.lifecycle-field :deep(.el-date-editor) {
  width: 100%;
}
.lifecycle-field input {
  width: 100%;
  height: 42px;
  box-sizing: border-box;
  padding: 0 12px;
  border: 1px solid var(--ds-input-border);
  border-radius: 12px;
  background: #fff;
  color: var(--ds-ink);
  font: 500 13px/1 var(--ds-font-sans);
}
.lifecycle-warning {
  margin: 0;
  padding: 12px;
  border-left: 3px solid #d98200;
  background: #fff7e8;
  color: #8a5300;
  font-size: 12px;
  line-height: 1.6;
}
.delete-mode {
  width: 100%;
}
.delete-mode :deep(.el-radio-button) {
  width: 50%;
}
.delete-mode :deep(.el-radio-button__inner) {
  width: 100%;
}
.delete-explain {
  color: var(--ds-muted);
  font-size: 12px;
  line-height: 1.7;
}
.delete-explain.is-danger {
  display: grid;
  gap: 8px;
  border-color: rgba(201, 56, 43, 0.24);
  background: #fff6f4;
}
.delete-explain.is-danger > strong {
  color: #b42318;
  font-size: 14px;
}
.lifecycle-danger-btn {
  color: #fff;
  background: #c9382b;
  border-color: #c9382b;
}
.lifecycle-danger-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

@media (max-width: 680px) {
  .schedule-grid {
    grid-template-columns: 1fr;
  }
  .camp-manage__menu {
    left: 0;
    right: auto;
  }
}
</style>
