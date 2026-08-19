<template>
  <div class="teacher-page team-create-page">
    <header class="teacher-page__head">
      <div>
        <h1>组建备赛团队</h1>
        <p>一次完成项目、选人与岗位确认；可随时保存草稿。</p>
      </div>
      <router-link class="teacher-btn teacher-btn--secondary" to="/projects">退出向导</router-link>
    </header>

    <ol class="wizard-steps" aria-label="组建步骤">
      <li v-for="item in stepItems" :key="item.step" :class="{ 'is-active': step === item.step, 'is-done': step > item.step }">
        <span aria-hidden="true">{{ step > item.step ? '✓' : item.step }}</span>
        <strong>{{ item.label }}</strong>
      </li>
    </ol>

    <section class="teacher-card wizard-card">
      <template v-if="step === 1">
        <header class="wizard-head">
          <div><span>步骤 1 / 3</span><h2>团队与项目</h2><p>这里填的是学生之后看到的团队上下文。</p></div>
        </header>
        <div class="wizard-body form-grid">
          <label class="wizard-field"><span>团队名称 *</span><input v-model.trim="form.teamName" placeholder="例如：应用攻坚队" /></label>
          <label class="wizard-field"><span>项目名称 *</span><input v-model.trim="form.projectName" placeholder="例如：智慧养老项目" /></label>
          <label class="wizard-field full"><span>项目简介</span><textarea v-model.trim="form.summary" rows="4" placeholder="要解决什么问题、准备交付什么、路演方向是什么" /></label>
          <label class="wizard-field">
            <span>赛道 *</span>
            <el-select v-model="form.trackId" filterable clearable placeholder="搜索并选择赛道" no-match-text="未找到匹配赛道">
              <el-option v-for="track in tracks" :key="track.trackId" :label="track.trackName" :value="track.trackId" />
            </el-select>
            <small>共 {{ tracks.length }} 个正式赛道，可输入关键词搜索</small>
          </label>
          <label class="wizard-field">
            <span>备赛时间 *</span>
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
            <small v-if="periodDays">{{ form.dateRange[0] }} 至 {{ form.dateRange[1] }} · 共 {{ periodDays }} 天</small>
          </label>
        </div>
      </template>

      <template v-else-if="step === 2">
        <header class="wizard-head">
          <div><span>步骤 2 / 3</span><h2>选人与角色</h2><p>选择候选人；第一个选中成员默认设为队长，可随时调整。</p></div>
          <span class="teacher-tag is-info">已选 {{ form.members.length }} 人</span>
        </header>
        <div class="wizard-body">
          <label class="member-search"><span>搜索</span><input v-model.trim="keyword" placeholder="姓名或学号" /></label>
          <div class="candidate-list">
            <label v-for="member in filteredMembers" :key="member.id" class="candidate-row" :class="{ 'is-selected': isSelected(member.id) }">
              <input type="checkbox" :checked="isSelected(member.id)" @change="toggleMember(member)" />
              <span class="candidate-avatar">{{ member.name.slice(0, 1) }}</span>
              <span><strong>{{ member.name }}</strong><small>{{ member.studentNo }} · {{ member.status }}</small></span>
              <el-select
                v-if="isSelected(member.id)"
                class="candidate-role-picker"
                :model-value="memberRole(member.id)"
                filterable
                allow-create
                default-first-option
                :loading="savingRoleNames.has(memberRole(member.id))"
                placeholder="选择或输入角色"
                no-match-text="回车创建此角色"
                @change="setRole(member.id, $event)"
                @click.stop
              >
                <el-option v-for="role in roles" :key="role" :label="role" :value="role" />
              </el-select>
              <em v-if="form.captainId === member.id">队长</em>
              <button v-if="isSelected(member.id) && form.captainId !== member.id" type="button" @click.prevent="form.captainId = member.id">设为队长</button>
            </label>
          </div>
        </div>
      </template>

      <template v-else>
        <header class="wizard-head">
          <div><span>步骤 3 / 3</span><h2>确认创建</h2><p>确认团队、项目与成员信息；创建后继续设置集训周期与每日任务。</p></div>
        </header>
        <div class="wizard-body launch-options">
          <div class="launch-detail">
            创建后会立即建立团队、成员与岗位关系，并进入集训营创建页。训练日先生成草稿，由老师逐日确认后发布给学生。
          </div>
          <aside class="create-summary">
            <h3>创建摘要</h3>
            <dl>
              <div><dt>团队</dt><dd>{{ form.teamName }}</dd></div>
              <div><dt>项目</dt><dd>{{ form.projectName }}</dd></div>
              <div><dt>赛道</dt><dd>{{ selectedTrack?.trackName || '未设置' }}</dd></div>
              <div><dt>备赛时间</dt><dd>{{ form.dateRange?.[0] }} 至 {{ form.dateRange?.[1] }}（{{ periodDays }} 天）</dd></div>
              <div><dt>成员</dt><dd>{{ form.members.length }} 人</dd></div>
              <div><dt>队长</dt><dd>{{ captainName }}</dd></div>
            </dl>
          </aside>
        </div>
      </template>

      <footer class="wizard-footer">
        <button type="button" class="teacher-btn teacher-btn--secondary" @click="saveDraft">保存草稿</button>
        <span role="status" aria-live="polite">{{ message }}</span>
        <button v-if="step > 1" type="button" class="teacher-btn teacher-btn--secondary" @click="step -= 1">上一步</button>
        <button v-if="step < 3" type="button" class="teacher-btn teacher-btn--primary" :disabled="!canContinue" @click="next">下一步</button>
        <button v-else type="button" class="teacher-btn teacher-btn--primary" :disabled="saving || !canCreate" @click="create">{{ saving ? '创建中…' : '创建并设置集训营' }}</button>
      </footer>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElDatePicker, ElOption, ElSelect } from 'element-plus'
import { useRouter } from 'vue-router'
import { createPositionRole, createTeam, fetchCandidateMembers, fetchCompetitionTracks, fetchPositionRoles } from '../../api'

const DRAFT_KEY = 'orep_teacher_team_draft'
const MAX_ROLE_NAME_LENGTH = 80
const DEFAULT_ROLES = ['项目经理', '路演主讲', '前端开发工程师', '后端开发工程师', '项目成员']
const router = useRouter()
const step = ref(1)
const saving = ref(false)
const keyword = ref('')
const message = ref('')
const roles = ref([...DEFAULT_ROLES])
const savingRoleNames = reactive(new Set())
const tracks = ref([])
const stepItems = [{ step: 1, label: '团队与项目' }, { step: 2, label: '选人与角色' }, { step: 3, label: '确认创建' }]
const form = reactive({ teamName: '', projectName: '', summary: '', trackId: '', dateRange: defaultDateRange(), members: [], captainId: '' })
const candidates = ref([])
const filteredMembers = computed(() => candidates.value.filter((m) => !keyword.value || `${m.name}${m.studentNo}`.includes(keyword.value)))
const selectedTrack = computed(() => tracks.value.find((item) => item.trackId === form.trackId))
const periodDays = computed(() => inclusiveDays(form.dateRange))
const hasProjectContext = computed(() => Boolean(form.teamName && form.projectName && form.trackId && form.dateRange?.length === 2 && periodDays.value > 0))
const canContinue = computed(() => step.value === 1 ? hasProjectContext.value : step.value === 2 ? form.members.length > 0 : true)
const canCreate = computed(() => Boolean(hasProjectContext.value && form.members.length))
const captainName = computed(() => form.members.find((m) => m.id === form.captainId)?.name || '未设置')

function isSelected(id) { return form.members.some((m) => m.id === id) }
function memberRole(id) { return form.members.find((m) => m.id === id)?.role || '项目成员' }
function toggleMember(member) {
  if (isSelected(member.id)) {
    form.members = form.members.filter((m) => m.id !== member.id)
    if (form.captainId === member.id) form.captainId = form.members[0]?.id || ''
  } else {
    const role = form.members.length === 0 ? '项目经理' : '项目成员'
    form.members.push({ ...member, role })
    if (!form.captainId) form.captainId = member.id
  }
}
function normalizeRoleName(value) {
  return String(value ?? '').replace(/[\r\n\t]+/g, ' ').trim()
}
async function setRole(id, value) {
  const row = form.members.find((m) => m.id === id)
  if (!row) return
  const role = normalizeRoleName(value)
  if (!role) {
    message.value = '岗位名称不能为空'
    return
  }
  if (role.length > MAX_ROLE_NAME_LENGTH) {
    message.value = `岗位名称最多 ${MAX_ROLE_NAME_LENGTH} 个字符`
    return
  }
  row.role = role
  if (roles.value.includes(role) || savingRoleNames.has(role)) return

  savingRoleNames.add(role)
  message.value = `正在保存新岗位“${role}”…`
  try {
    const result = await createPositionRole({ name: role })
    const savedRole = normalizeRoleName(result?.name || result?.positionName || role)
    if (row.role === role) row.role = savedRole
    if (!roles.value.includes(savedRole)) roles.value = [...roles.value, savedRole]
    message.value = `新岗位“${savedRole}”已保存，之后可直接选择`
  } catch (error) {
    message.value = `岗位“${role}”保存失败：${error.message}；本次团队仍可使用该名称`
  } finally {
    savingRoleNames.delete(role)
  }
}
function formatLocalDate(date) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
function defaultDateRange() {
  const start = new Date()
  const end = new Date(start)
  end.setDate(end.getDate() + 20)
  return [formatLocalDate(start), formatLocalDate(end)]
}
function inclusiveDays(range) {
  if (!Array.isArray(range) || range.length !== 2 || !range[0] || !range[1]) return 0
  const toUtc = (value) => {
    const [year, month, day] = value.split('-').map(Number)
    return Date.UTC(year, month - 1, day)
  }
  return Math.floor((toUtc(range[1]) - toUtc(range[0])) / 86400000) + 1
}
function next() { if (canContinue.value) step.value += 1 }
function saveDraft() {
  localStorage.setItem(DRAFT_KEY, JSON.stringify({ ...form }))
  message.value = '草稿已保存'
  setTimeout(() => { message.value = '' }, 1800)
}
async function create() {
  if (!canCreate.value) return
  saving.value = true
  message.value = ''
  const payload = {
    name: form.teamName,
    description: [form.projectName, form.summary].filter(Boolean).join('\n'),
    trackId: form.trackId,
    trackName: selectedTrack.value?.trackName,
    startDate: form.dateRange[0],
    endDate: form.dateRange[1],
    captainUserId: form.captainId,
    captainPositionName: memberRole(form.captainId),
    memberUserIds: form.members.map((m) => m.id),
    memberAssignments: form.members.filter((m) => m.id !== form.captainId).map((m) => ({ userId: m.id, positionName: m.role })),
  }
  try {
    const result = await createTeam(payload)
    const teamId = result?.id || result?.teamId
    if (!teamId) throw new Error('创建结果缺少团队 ID')
    localStorage.removeItem(DRAFT_KEY)
    router.replace(`/camp/create?teamId=${teamId}`)
  } catch (e) {
    message.value = `创建失败：${e.message}`
  } finally {
    saving.value = false
  }
}
onMounted(async () => {
  try {
    const [memberRows, positionRows, trackRows] = await Promise.all([fetchCandidateMembers(), fetchPositionRoles(), fetchCompetitionTracks()])
    candidates.value = memberRows.filter((m) => String(m.role || m.systemRole).toUpperCase() === 'STUDENT').map((m) => ({ id: m.id || m.userId, name: m.username || m.name, studentNo: m.studentNo || m.username, status: m.teamName ? `已在 ${m.teamName}` : '可选' }))
    const positionNames = positionRows.map((r) => normalizeRoleName(r.name || r.positionName)).filter(Boolean)
    roles.value = [...new Set([...DEFAULT_ROLES, ...positionNames])]
    tracks.value = trackRows
  } catch (error) {
    message.value = `创建所需数据加载失败：${error.message}`
  }
  try {
    const draft = JSON.parse(localStorage.getItem(DRAFT_KEY) || 'null')
    if (draft) Object.assign(form, draft)
  } catch { /* ignore malformed draft */ }
})
</script>

<style scoped>
/* 新建项目向导 · 对齐学生端 token */
.wizard-steps {
  list-style: none;
  margin: 0 0 16px;
  padding: 0;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.wizard-steps li {
  min-height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  border-radius: var(--ds-card-radius, 16px);
  color: var(--ds-muted);
  background: var(--ds-card-bg, #fff);
  border: 1px solid var(--ds-card-border, #e4e4e7);
  box-shadow: var(--ds-card-shadow);
}
.wizard-steps li > span {
  width: 26px;
  height: 26px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: #f4f4f5;
  border: 1px solid var(--ds-line, #e4e4e7);
  font-size: 12px;
  font-weight: 750;
}
.wizard-steps li strong {
  font-size: 13px;
  font-weight: 750;
}
.wizard-steps li.is-active,
.wizard-steps li.is-done {
  color: var(--ds-orange-deep);
  background: var(--ds-orange-wash);
  border-color: rgba(232, 74, 28, 0.18);
  box-shadow: none;
}
.wizard-steps li.is-active > span,
.wizard-steps li.is-done > span {
  color: #fff;
  background: var(--ds-orange-action, var(--ds-orange));
  border-color: transparent;
}
.wizard-card {
  overflow: hidden;
  border-radius: var(--ds-card-radius, 16px);
}
.wizard-head {
  min-height: 88px;
  padding: 20px 22px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  border-bottom: 1px solid var(--ds-line, #e4e4e7);
}
.wizard-head > div > span {
  color: var(--ds-orange-deep);
  font-size: 11px;
  font-weight: 750;
  letter-spacing: 0.02em;
}
.wizard-head h2 {
  margin: 6px 0 4px;
  font-size: 18px;
  font-weight: 750;
  letter-spacing: -0.02em;
  color: var(--ds-ink);
}
.wizard-head p {
  margin: 0;
  color: var(--ds-muted);
  font-size: 13px;
  line-height: 1.5;
}
.wizard-body {
  min-height: 360px;
  padding: 22px;
}
.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 16px;
  align-content: start;
}
.wizard-field {
  min-width: 0;
  display: grid;
  gap: 8px;
  color: var(--ds-muted);
  font-size: 12px;
  font-weight: 700;
}
.wizard-field.full {
  grid-column: 1 / -1;
}
.wizard-field input,
.wizard-field select,
.wizard-field textarea,
.member-search input {
  box-sizing: border-box;
  width: 100%;
  border: 1px solid var(--ds-input-border, #d4d4d8);
  border-radius: var(--ds-input-radius, 12px);
  padding: 11px 13px;
  background: #fff;
  color: var(--ds-ink);
  font: 500 14px/1.5 var(--ds-font-sans);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
/* 多行：不用胶囊圆角 */
.wizard-field textarea {
  border-radius: var(--ds-textarea-radius, 12px);
  min-height: 104px;
  resize: vertical;
  line-height: 1.55;
}
.wizard-field input:hover,
.wizard-field select:hover,
.wizard-field textarea:hover,
.member-search input:hover {
  border-color: var(--ds-input-border-hover, #a1a1aa);
}
.wizard-field input:focus,
.wizard-field select:focus,
.wizard-field textarea:focus,
.member-search input:focus {
  outline: none;
  border-color: var(--ds-input-focus-border, var(--ds-orange-700));
  box-shadow: var(--ds-input-focus-ring);
}
.wizard-field small {
  color: var(--ds-muted);
  font-size: 11px;
  font-weight: 500;
}
.wizard-field :deep(.el-select),
.wizard-field :deep(.el-date-editor) {
  width: 100%;
}
.wizard-field :deep(.el-select__wrapper),
.wizard-field :deep(.el-date-editor.el-input__wrapper) {
  min-height: 44px;
  border-radius: var(--ds-input-radius, 12px);
  background: #fff;
  box-shadow: 0 0 0 1px var(--ds-input-border, #d4d4d8) inset;
}
.wizard-field :deep(.el-select__wrapper.is-focused),
.wizard-field :deep(.el-date-editor.is-active) {
  box-shadow: var(--ds-input-focus-ring), 0 0 0 1px var(--ds-orange-700) inset;
}
.member-search {
  max-width: 360px;
  display: grid;
  grid-template-columns: auto 1fr;
  align-items: center;
  gap: 10px;
  color: var(--ds-muted);
  font-size: 12px;
  font-weight: 700;
}
.candidate-list {
  margin-top: 16px;
  display: grid;
  gap: 8px;
}
.candidate-row {
  min-height: 62px;
  padding: 10px 12px;
  display: grid;
  grid-template-columns: 22px 38px minmax(0, 1fr) minmax(176px, 220px) auto;
  gap: 10px;
  align-items: center;
  border: 1px solid var(--ds-card-border, #e4e4e7);
  border-radius: 14px;
  background: #fff;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}
.candidate-row.is-selected {
  border-color: rgba(232, 74, 28, 0.28);
  background: var(--ds-orange-wash);
}
.candidate-avatar {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: grid;
  place-items: center;
  color: var(--ds-orange-deep);
  background: var(--ds-orange-soft, #fee9df);
  font-weight: 800;
}
.candidate-row strong,
.candidate-row small {
  display: block;
}
.candidate-row strong {
  font-size: 13px;
  font-weight: 750;
  color: var(--ds-ink);
}
.candidate-row small {
  margin-top: 3px;
  color: var(--ds-muted);
  font-size: 11px;
}
.candidate-role-picker {
  width: 100%;
}
.candidate-role-picker :deep(.el-select__wrapper) {
  min-height: 36px;
  border-radius: 10px;
  background: #fff;
  box-shadow: 0 0 0 1px var(--ds-input-border) inset;
  font-size: 12px;
}
.candidate-role-picker :deep(.el-select__wrapper.is-focused) {
  box-shadow: var(--ds-input-focus-ring), 0 0 0 1px var(--ds-orange-700) inset;
}
.candidate-row em {
  color: var(--ds-orange-deep);
  font-size: 11px;
  font-style: normal;
  font-weight: 750;
}
.candidate-row button {
  border: 0;
  background: none;
  color: var(--ds-orange-action, var(--ds-orange));
  font: 700 11px var(--ds-font-sans);
  cursor: pointer;
}
.launch-options {
  display: grid;
  gap: 10px;
  align-content: start;
}
.launch-detail {
  padding: 13px 16px;
  border-radius: 12px;
  color: var(--ds-ink-2);
  background: #f7f7f8;
  border: 1px solid var(--ds-line);
  font-size: 13px;
  line-height: 1.55;
}
.create-summary {
  margin-top: 8px;
  padding: 16px;
  border-radius: var(--ds-card-radius, 16px);
  background: #f7f7f8;
  border: 1px solid var(--ds-line);
}
.create-summary h3 {
  margin: 0 0 12px;
  font-size: 14px;
  font-weight: 750;
}
.create-summary dl {
  margin: 0;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px 12px;
}
.create-summary dt {
  color: var(--ds-muted);
  font-size: 11px;
  font-weight: 650;
}
.create-summary dd {
  margin: 4px 0 0;
  font-size: 13px;
  font-weight: 750;
  color: var(--ds-ink);
}
.wizard-footer {
  min-height: 72px;
  padding: 14px 22px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  border-top: 1px solid var(--ds-line);
  background: #fafafa;
}
.wizard-footer > span {
  margin-right: auto;
  color: var(--ds-muted);
  font-size: 12px;
  font-weight: 600;
}
@media (max-width: 760px) {
  .form-grid {
    grid-template-columns: 1fr;
  }
  .wizard-field.full {
    grid-column: auto;
  }
  .candidate-row {
    grid-template-columns: 22px 38px 1fr;
  }
  .candidate-role-picker,
  .candidate-row em,
  .candidate-row button {
    width: 100%;
    grid-column: 3;
  }
  .create-summary dl {
    grid-template-columns: 1fr 1fr;
  }
  .wizard-steps {
    grid-template-columns: 1fr;
  }
}
</style>
