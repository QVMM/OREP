<template>
  <div class="teacher-page camp-create-page">
    <header class="teacher-page__head">
      <div>
        <h1>创建集训营</h1>
        <p>确定参训团队与日期后，系统会生成逐日草稿；学生只能看到老师正式发布的任务。</p>
      </div>
      <router-link class="teacher-btn teacher-btn--secondary" to="/camp">返回集训营</router-link>
    </header>

    <section v-if="loading" class="teacher-card teacher-empty">正在读取团队信息…</section>
    <section v-else-if="!teams.length" class="teacher-card camp-empty">
      <span class="camp-empty__mark">营</span>
      <h2>先创建一支备赛团队</h2>
      <p>集训营必须关联真实团队，训练任务才能准确下发到学生。</p>
      <router-link class="teacher-btn teacher-btn--primary" to="/projects/create">新建项目</router-link>
    </section>
    <section v-else class="teacher-card create-card">
      <div class="create-card__intro">
        <span>01</span>
        <div><h2>集训基本信息</h2><p>日期默认继承所选团队的备赛周期，可在创建前调整。</p></div>
        <strong>{{ totalDays }} 天</strong>
      </div>

      <div class="create-form">
        <label class="camp-field full"><span>集训营名称 *</span><input v-model.trim="form.name" placeholder="例如：智慧养老项目 · 第一阶段集训" /></label>
        <label class="camp-field full"><span>集训说明</span><textarea v-model.trim="form.subtitle" rows="3" placeholder="本阶段要解决的问题和预期成果" /></label>
        <fieldset class="team-picker full">
          <legend>参训团队 *</legend>
          <label v-for="team in teams" :key="team.id" :class="{ 'is-selected': form.teamIds.includes(Number(team.id)) }">
            <input v-model="form.teamIds" type="checkbox" :value="Number(team.id)" />
            <span><strong>{{ team.name }}</strong><small>{{ team.trackName || '未设置赛道' }} · {{ dateText(team) }}</small></span>
            <em>{{ form.teamIds.includes(Number(team.id)) ? '已选择' : '选择' }}</em>
          </label>
        </fieldset>
        <label class="camp-field full">
          <span>集训日期 *</span>
          <el-date-picker
            v-model="form.dateRange"
            type="daterange"
            value-format="YYYY-MM-DD"
            format="YYYY/MM/DD"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            unlink-panels
          />
          <small>将生成 {{ totalDays }} 个训练日，每 7 天自动分为一周；所有训练日初始为草稿。</small>
        </label>
      </div>

      <div class="create-actions">
        <router-link class="teacher-btn teacher-btn--secondary" to="/camp">取消</router-link>
        <button
          type="button"
          class="teacher-btn teacher-btn--primary"
          :disabled="saving || !canCreate"
          @click="submit"
        >
          {{ saving ? '创建中…' : '创建并生成草稿' }}
        </button>
      </div>
      <p v-if="error" class="plan-notice is-error">{{ error }}</p>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElDatePicker } from 'element-plus'
import { createTeacherCamp, fetchMyTeams } from '../../api'

const router = useRouter()
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const teams = ref([])

const form = reactive({
  name: '',
  subtitle: '',
  teamIds: [],
  dateRange: [],
})

const totalDays = computed(() => {
  const [start, end] = form.dateRange || []
  if (!start || !end) return 0
  const a = new Date(`${start}T00:00:00`)
  const b = new Date(`${end}T00:00:00`)
  if (Number.isNaN(a.getTime()) || Number.isNaN(b.getTime()) || b < a) return 0
  return Math.floor((b - a) / 86400000) + 1
})

const canCreate = computed(
  () => form.name.trim() && form.teamIds.length && totalDays.value > 0
)

function dateText(team) {
  if (team.startDate && team.endDate) return `${String(team.startDate).slice(0, 10)} – ${String(team.endDate).slice(0, 10)}`
  return '未设置备赛周期'
}

async function loadTeams() {
  loading.value = true
  error.value = ''
  try {
    const rows = await fetchMyTeams()
    teams.value = Array.isArray(rows) ? rows : []
    if (teams.value.length === 1) {
      form.teamIds = [Number(teams.value[0].id)]
      if (teams.value[0].startDate && teams.value[0].endDate) {
        form.dateRange = [
          String(teams.value[0].startDate).slice(0, 10),
          String(teams.value[0].endDate).slice(0, 10),
        ]
      }
    }
  } catch (err) {
    error.value = err?.message || '团队列表加载失败'
    teams.value = []
  } finally {
    loading.value = false
  }
}

async function submit() {
  if (!canCreate.value || saving.value) return
  saving.value = true
  error.value = ''
  try {
    const [startDate, endDate] = form.dateRange
    const camp = await createTeacherCamp({
      name: form.name.trim(),
      subtitle: form.subtitle.trim() || undefined,
      teamIds: form.teamIds,
      startDate,
      endDate,
    })
    const campId = camp?.campId || camp?.id
    if (campId) router.replace({ path: '/camp', query: { campId: String(campId), tab: 'plan' } })
    else router.replace('/camp')
  } catch (err) {
    error.value = err?.response?.data?.message || err?.message || '创建失败'
  } finally {
    saving.value = false
  }
}

onMounted(loadTeams)
</script>

<style scoped>
.create-card {
  padding: 20px;
}
.create-card__intro {
  display: grid;
  grid-template-columns: 40px minmax(0, 1fr) auto;
  gap: 12px;
  align-items: center;
  margin-bottom: 18px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--ds-line);
}
.create-card__intro > span {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  background: var(--ds-orange-wash);
  color: var(--ds-orange-deep);
  font-weight: 800;
  font-size: 13px;
}
.create-card__intro h2 {
  margin: 0;
  font-size: 16px;
}
.create-card__intro p {
  margin: 4px 0 0;
  color: var(--ds-muted);
  font-size: 12px;
}
.create-card__intro strong {
  font-size: 20px;
  font-weight: 800;
  color: var(--ds-orange-deep);
}
.create-form {
  display: grid;
  gap: 14px;
}
.camp-field {
  display: grid;
  gap: 8px;
  min-width: 0;
  color: var(--ds-muted);
  font-size: 12px;
  font-weight: 700;
}
.camp-field.full {
  width: 100%;
}
.camp-field input,
.camp-field textarea {
  box-sizing: border-box;
  width: 100%;
  border: 1px solid var(--ds-input-border, #d4d4d8);
  border-radius: var(--ds-input-radius, 12px);
  padding: 11px 13px;
  background: #fff;
  color: var(--ds-ink);
  font: 500 14px/1.5 var(--ds-font-sans);
}
.camp-field textarea {
  border-radius: var(--ds-textarea-radius, 12px);
  min-height: 96px;
  resize: vertical;
  line-height: 1.55;
}
.camp-field input:focus,
.camp-field textarea:focus {
  outline: none;
  border-color: var(--ds-orange);
  box-shadow: var(--ds-input-focus-ring, 0 0 0 3px rgba(232, 74, 28, 0.12));
}
.camp-field small {
  color: var(--ds-muted);
  font-size: 11px;
  font-weight: 500;
}
.camp-field :deep(.el-date-editor) {
  width: 100%;
}
.camp-field :deep(.el-date-editor.el-input__wrapper) {
  min-height: 44px;
  border-radius: var(--ds-input-radius, 12px);
  box-shadow: 0 0 0 1px var(--ds-input-border, #d4d4d8) inset;
}
.team-picker {
  margin: 0;
  padding: 12px;
  border: 1px solid var(--ds-line);
  border-radius: 12px;
}
.team-picker legend {
  padding: 0 6px;
  font-size: 12px;
  font-weight: 700;
  color: var(--ds-muted);
}
.team-picker label {
  display: grid;
  grid-template-columns: auto minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  padding: 10px 12px;
  border-radius: 10px;
  cursor: pointer;
}
.team-picker label.is-selected {
  background: #fff7f2;
}
.team-picker label strong {
  display: block;
  font-size: 13px;
  color: var(--ds-ink);
}
.team-picker label small {
  display: block;
  margin-top: 2px;
  font-size: 11px;
  color: var(--ds-muted);
}
.team-picker label em {
  font-style: normal;
  font-size: 12px;
  font-weight: 700;
  color: var(--ds-muted);
}
.team-picker label.is-selected em {
  color: var(--ds-orange-deep);
}
.create-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 18px;
  padding-top: 16px;
  border-top: 1px solid var(--ds-line);
}
.camp-empty {
  padding: 40px 24px;
  text-align: center;
  display: grid;
  justify-items: center;
  gap: 10px;
}
.camp-empty__mark {
  width: 48px;
  height: 48px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  background: var(--ds-orange-wash);
  color: var(--ds-orange-deep);
  font-weight: 800;
}
.plan-notice.is-error {
  margin-top: 12px;
  padding: 10px 12px;
  border-radius: 10px;
  color: #a33a24;
  background: #fff0ec;
  font-size: 12px;
  font-weight: 700;
}
</style>
