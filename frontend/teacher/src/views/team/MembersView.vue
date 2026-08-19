<template>
  <div class="teacher-page members-page">
    <header class="teacher-page__head">
      <div>
        <h1>成员管理</h1>
        <p>
          管理项目成员与本班账号。创建学生账号时，系统会自动落到你所属的组织与班级，无法跨班创建。
        </p>
      </div>
      <div class="teacher-page__actions">
        <button type="button" class="teacher-btn teacher-btn--secondary" :disabled="loading" @click="refreshAll">
          刷新
        </button>
        <button type="button" class="teacher-btn teacher-btn--primary" @click="openCreateDrawer">
          创建账号
        </button>
        <router-link
          v-if="effectiveProjectId && effectiveProjectId !== 'all'"
          class="teacher-btn teacher-btn--secondary"
          :to="`/projects/${effectiveProjectId}`"
        >
          在项目详情中管理
        </router-link>
      </div>
    </header>

    <p v-if="error" class="plan-notice is-error" role="alert">{{ error }}</p>
    <p v-if="notice" class="plan-notice is-ok" role="status">{{ notice }}</p>

    <section class="teacher-metric-strip is-5">
      <article class="teacher-card teacher-metric-card"><small>项目成员</small><strong>{{ filtered.length }}</strong></article>
      <article class="teacher-card teacher-metric-card"><small>本班用户</small><strong>{{ classUsers.length }}</strong></article>
      <article class="teacher-card teacher-metric-card"><small>所属项目数</small><strong>{{ projectCount }}</strong></article>
      <article class="teacher-card teacher-metric-card"><small>待分配岗位</small><strong class="is-accent">{{ pendingPositionCount }}</strong></article>
      <article class="teacher-card teacher-metric-card">
        <small>组织范围</small>
        <strong class="scope-metric">{{ scopeSummary }}</strong>
      </article>
    </section>

    <section class="teacher-card">
      <div class="teacher-card__body">
        <div class="manager-toolbar">
          <div class="manager-toolbar__title">
            <div class="members-tabs" role="tablist">
              <button
                type="button"
                role="tab"
                :class="{ 'is-active': listTab === 'project' }"
                @click="listTab = 'project'"
              >
                项目成员
              </button>
              <button
                type="button"
                role="tab"
                :class="{ 'is-active': listTab === 'class' }"
                @click="listTab = 'class'"
              >
                本班用户
              </button>
            </div>
            <span>{{ listTab === 'project' ? scopeLabel : classScopeLabel }}</span>
          </div>
          <div class="manager-toolbar__tools">
            <input v-model.trim="keyword" type="search" placeholder="搜索姓名 / 岗位 / 账号" />
            <select v-if="listTab === 'project'" v-model="projectFilter">
              <option value="current">当前项目 · {{ ctx.projectName }}</option>
              <option v-for="p in ctx.projects" :key="p.id" :value="String(p.id)">{{ p.name }}</option>
              <option value="all">全部项目</option>
            </select>
          </div>
        </div>

        <div v-if="loading" class="teacher-empty">正在加载成员…</div>

        <!-- 项目成员 -->
        <template v-else-if="listTab === 'project'">
          <div class="teacher-table-wrap">
            <table class="teacher-table">
              <thead>
                <tr>
                  <th>成员</th>
                  <th>所属项目</th>
                  <th>项目岗位</th>
                  <th>学生账号</th>
                  <th>角色</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="m in filtered" :key="m.key">
                  <td>
                    <div class="member-cell">
                      <span
                        class="member-cell__avatar"
                        :style="{ background: avatarColor(m.userId || m.name) }"
                        aria-hidden="true"
                      >{{ memberInitial(m.name) }}</span>
                      <strong class="member-cell__name">{{ m.name }}</strong>
                    </div>
                  </td>
                  <td>{{ m.project }}</td>
                  <td>{{ m.position || '待分配' }}</td>
                  <td>{{ m.account || '—' }}</td>
                  <td>{{ anyRoleLabel(m.role) }}</td>
                  <td class="col-actions">
                    <router-link
                      v-if="canOpenStudentProfile(m)"
                      class="teacher-link"
                      :to="studentProfilePath(m.userId)"
                    >
                      档案
                    </router-link>
                    <router-link
                      class="teacher-link"
                      :to="projectMembersPath(m.projectId)"
                    >
                      岗位
                    </router-link>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="!filtered.length" class="teacher-empty">
            当前筛选下没有项目成员。可先创建学生账号，再在项目详情中加入团队。
          </div>
        </template>

        <!-- 本班用户 -->
        <template v-else>
          <div class="teacher-table-wrap">
            <table class="teacher-table">
              <thead>
                <tr>
                  <th>用户名</th>
                  <th>邮箱</th>
                  <th>角色</th>
                  <th>班级</th>
                  <th>用户组</th>
                  <th>创建时间</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="u in filteredClassUsers" :key="u.id">
                  <td>
                    <div class="member-cell">
                      <span
                        class="member-cell__avatar"
                        :style="{ background: avatarColor(u.id || u.username) }"
                        aria-hidden="true"
                      >{{ memberInitial(u.username) }}</span>
                      <strong class="member-cell__name">{{ u.username }}</strong>
                    </div>
                  </td>
                  <td>{{ u.email || '—' }}</td>
                  <td>
                    <span class="teacher-tag" :class="roleTagClass(u.role)">{{ userRoleLabel(u.role) }}</span>
                  </td>
                  <td>{{ u.className || operatorScope?.className || '—' }}</td>
                  <td>{{ u.groupNames || u.userGroup || '—' }}</td>
                  <td>{{ formatTime(u.createdAt) }}</td>
                  <td class="col-actions">
                    <router-link
                      v-if="isStudentRole(u.role)"
                      class="teacher-link"
                      :to="studentProfilePath(u.id)"
                    >
                      档案
                    </router-link>
                    <span v-else class="teacher-muted">—</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <div v-if="!filteredClassUsers.length" class="teacher-empty">
            <template v-if="!canCreateAccount">
              当前账号未配置可管辖班级。请联系管理员配置学校/学院/班级或「教学管辖范围」（可配置多个班级）。
            </template>
            <template v-else>
              本班还没有用户。点击右上角「创建账号」添加学生。
            </template>
          </div>
        </template>
      </div>
    </section>

    <!-- 创建账号抽屉 -->
    <Teleport to="body">
      <div
        v-if="createOpen"
        class="drawer-mask teacher-overlay-mask"
        role="presentation"
        @click.self="closeCreateDrawer"
        @keydown.esc.prevent="closeCreateDrawer"
      >
        <aside class="workspace-drawer workspace-drawer--task" role="dialog" aria-modal="true" aria-label="创建账号">
          <header class="workspace-drawer__head">
            <h2>创建账号</h2>
            <button type="button" class="teacher-btn teacher-btn--secondary teacher-btn--sm" @click="closeCreateDrawer">
              关闭
            </button>
          </header>

          <div class="task-drawer">
            <p class="drawer-tip">
              {{ createScopeTip }}
            </p>

            <div class="task-drawer__body">
              <div v-if="!canCreateAccount" class="create-blocked">
                <strong>无法创建账号</strong>
                <p>
                  你的账号尚未配置可管辖班级。教师只能在自己管辖的学校/班级下创建用户；
                  若你负责多个班，请管理员在后台用户归属中为你配置多个班级（teachingClassIds）。
                </p>
              </div>

              <template v-else>
                <div class="org-scope-card">
                  <span>将创建到</span>
                  <strong>{{ orgPathLabel }}</strong>
                  <small v-if="teachingScopes.length <= 1">教师仅可在自己管辖的班级下创建</small>
                  <small v-else>你可在以下管辖班级中选择其一</small>
                </div>

                <label v-if="teachingScopes.length > 1" class="drawer-field">
                  <span>归属班级 <i>*</i></span>
                  <select v-model="createForm.classId">
                    <option disabled value="">请选择班级</option>
                    <option v-for="s in teachingScopes" :key="s.classId" :value="String(s.classId)">
                      {{ [s.schoolName, s.collegeName, s.className].filter(Boolean).join(' / ') }}
                    </option>
                  </select>
                </label>

                <label class="drawer-field">
                  <span>用户名 <i>*</i></span>
                  <input
                    v-model.trim="createForm.username"
                    maxlength="20"
                    autocomplete="off"
                    placeholder="2–20 位，用于登录"
                    autofocus
                  />
                </label>

                <label class="drawer-field">
                  <span>邮箱 <i>*</i></span>
                  <input
                    v-model.trim="createForm.email"
                    type="email"
                    autocomplete="off"
                    placeholder="用于登录与通知"
                  />
                </label>

                <label class="drawer-field">
                  <span>初始密码 <i>*</i></span>
                  <input
                    v-model="createForm.password"
                    type="password"
                    maxlength="30"
                    autocomplete="new-password"
                    placeholder="6–30 位初始密码"
                  />
                </label>

                <label class="drawer-field">
                  <span>角色</span>
                  <select v-model="createForm.role">
                    <option value="STUDENT">学生</option>
                    <option v-if="!isStrictTeacher" value="TEACHER">教师</option>
                    <option v-if="!isStrictTeacher" value="REVIEWER">评委</option>
                    <option v-if="!isStrictTeacher" value="EXPERT">专家</option>
                  </select>
                  <small class="drawer-field-hint">
                    {{ isStrictTeacher ? '教师默认创建学生账号' : '管理员可分配更多角色' }}
                  </small>
                </label>
              </template>
            </div>

            <p v-if="formError" class="drawer-form-error" role="alert">{{ formError }}</p>

            <div class="drawer-actions">
              <button type="button" class="teacher-btn teacher-btn--secondary" :disabled="saving" @click="closeCreateDrawer">
                取消
              </button>
              <button
                type="button"
                class="teacher-btn teacher-btn--primary"
                :disabled="saving || !canCreateAccount || !createFormValid"
                @click="submitCreate"
              >
                {{ saving ? '创建中…' : '创建账号' }}
              </button>
            </div>
          </div>
        </aside>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, onUnmounted, reactive, ref, watch } from 'vue'
import {
  createOrgUser,
  fetchMyTeams,
  fetchOrgUsers,
  fetchOrganizationOptions,
  fetchTeamDashboard,
} from '../../api'
import { useTeacherContextStore } from '../../stores/context'
import { getUserRole } from '../../utils/auth'
import { anyRoleLabel, userRoleLabel } from '../../utils/labels'

const ctx = useTeacherContextStore()
const rows = ref([])
const classUsers = ref([])
const operatorScope = ref(null)
const loading = ref(true)
const error = ref('')
const notice = ref('')
const formError = ref('')
const keyword = ref('')
const projectFilter = ref('current')
const listTab = ref('project')
const createOpen = ref(false)
const saving = ref(false)

const createForm = reactive({
  username: '',
  email: '',
  password: '',
  role: 'STUDENT',
  classId: '',
})
const teachingScopes = ref([])

const operatorRole = computed(() => getUserRole())
const isStrictTeacher = computed(() => operatorRole.value === 'TEACHER')

const canCreateAccount = computed(() => {
  // 教师：至少有一个可管辖班级；管理员：有学校即可
  if (isStrictTeacher.value) return teachingScopes.value.length > 0
  return Boolean(operatorScope.value?.schoolId || teachingScopes.value.length)
})

const selectedScope = computed(() => {
  const id = createForm.classId ? Number(createForm.classId) : null
  if (id) {
    return teachingScopes.value.find((s) => Number(s.classId) === id) || null
  }
  return teachingScopes.value[0] || null
})

const orgPathLabel = computed(() => {
  const s = selectedScope.value || operatorScope.value || {}
  return [s.schoolName, s.collegeName, s.className].filter(Boolean).join(' / ') || '未配置组织'
})

const scopeSummary = computed(() => {
  if (teachingScopes.value.length > 1) return `${teachingScopes.value.length} 个班级`
  const s = teachingScopes.value[0] || operatorScope.value
  if (!s?.className && !s?.schoolName) return '未绑定'
  return s.className || s.collegeName || s.schoolName || '—'
})

const createScopeTip = computed(() => {
  if (!canCreateAccount.value) {
    return '创建账号需要配置可管辖班级。若你负责多个学校/班级，请联系管理员在后台为你配置「教学管辖范围」。'
  }
  if (teachingScopes.value.length > 1) {
    return `你管辖 ${teachingScopes.value.length} 个班级，请选择学生要归属的班级后再创建。不可创建到管辖范围以外的班级。`
  }
  return `新账号将创建在「${orgPathLabel.value}」下，学生可立即用于加入项目团队。`
})

const createFormValid = computed(() => {
  const u = createForm.username.trim()
  const e = createForm.email.trim()
  const p = createForm.password
  const needClass = teachingScopes.value.length > 1
  const classOk = !needClass || Boolean(createForm.classId)
  return classOk && u.length >= 2 && u.length <= 20 && e.includes('@') && p.length >= 6 && p.length <= 30
})

const effectiveProjectId = computed(() => {
  if (projectFilter.value === 'current') return ctx.projectId || ''
  if (projectFilter.value === 'all') return 'all'
  return projectFilter.value
})

const filtered = computed(() => {
  const q = keyword.value.toLowerCase()
  return rows.value.filter((m) => {
    if (effectiveProjectId.value !== 'all' && String(m.projectId) !== String(effectiveProjectId.value)) return false
    if (!q) return true
    return [m.name, m.position, m.account, m.project, m.role].join(' ').toLowerCase().includes(q)
  })
})

const filteredClassUsers = computed(() => {
  const q = keyword.value.toLowerCase()
  if (!q) return classUsers.value
  return classUsers.value.filter((u) =>
    [u.username, u.email, u.role, u.className, u.groupNames, u.userGroup].join(' ').toLowerCase().includes(q)
  )
})

const scopeLabel = computed(() => {
  if (effectiveProjectId.value === 'all') return `全部项目 · ${filtered.value.length} 人`
  return `${filtered.value[0]?.project || ctx.projectName} · ${filtered.value.length} 人`
})

const classScopeLabel = computed(() => {
  const name = operatorScope.value?.className || '本班'
  return `${name} · ${filteredClassUsers.value.length} 人`
})

const projectCount = computed(() => new Set(filtered.value.map((m) => m.projectId)).size)
const pendingPositionCount = computed(() => filtered.value.filter((m) => !m.position || m.position === '待分配').length)

const AVATAR_COLORS = ['#e84a1c', '#2563eb', '#0f766e', '#7c3aed', '#b45309', '#db2777', '#0e7490', '#c2410c']

function memberInitial(name) {
  const s = String(name || '').trim()
  return s ? s.slice(0, 1) : '?'
}

function avatarColor(seed) {
  const s = String(seed ?? '')
  let hash = 0
  for (let i = 0; i < s.length; i += 1) {
    hash = (hash * 31 + s.charCodeAt(i)) >>> 0
  }
  return AVATAR_COLORS[hash % AVATAR_COLORS.length]
}

function roleTagClass(role) {
  const r = String(role || '').toUpperCase()
  if (r === 'TEACHER' || r === 'ADMIN' || r === 'SCHOOL_ADMIN') return 'is-info'
  if (r === 'STUDENT') return ''
  return 'is-warn'
}

function isStudentRole(role) {
  const r = String(role || '').toUpperCase()
  return !r || r === 'STUDENT' || r === 'MEMBER'
}

/** 学生档案（从成员管理进入，返回链回本页） */
function studentProfilePath(userId) {
  return {
    path: `/analytics/students/${userId}`,
    query: { from: 'members' },
  }
}

/** 进项目的「成员与岗位」页签，不落在项目概览 */
function projectMembersPath(projectId) {
  return {
    path: `/projects/${projectId}`,
    query: { tab: 'members' },
  }
}

function canOpenStudentProfile(member) {
  if (!member?.userId) return false
  const system = String(member.systemRole || '').toUpperCase()
  if (system && system !== 'STUDENT') return false
  const teamRole = String(member.role || '').toUpperCase()
  // 指导教师 / 管理员不当作学生档案入口
  if (['MENTOR', 'TEACHER', 'ADMIN', 'SCHOOL_ADMIN'].includes(teamRole)) return false
  return true
}

function formatTime(value) {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return String(value)
  return d.toLocaleString('zh-CN', { month: 'numeric', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

function lockBodyScroll(locked) {
  if (typeof document === 'undefined') return
  document.body.style.overflow = locked ? 'hidden' : ''
}

function openCreateDrawer() {
  formError.value = ''
  createForm.username = ''
  createForm.email = ''
  createForm.password = ''
  createForm.role = 'STUDENT'
  createForm.classId = teachingScopes.value.length === 1
    ? String(teachingScopes.value[0].classId)
    : teachingScopes.value[0]
      ? String(teachingScopes.value[0].classId)
      : ''
  createOpen.value = true
  lockBodyScroll(true)
}

function closeCreateDrawer() {
  createOpen.value = false
  formError.value = ''
  lockBodyScroll(false)
}

async function submitCreate() {
  if (!canCreateAccount.value || !createFormValid.value || saving.value) return
  saving.value = true
  formError.value = ''
  try {
    const scope = selectedScope.value || operatorScope.value || {}
    const username = createForm.username.trim()
    const boundLabel = orgPathLabel.value
    await createOrgUser({
      username,
      email: createForm.email.trim(),
      password: createForm.password,
      role: createForm.role || 'STUDENT',
      schoolId: scope.schoolId || null,
      collegeId: scope.collegeId || null,
      classId: scope.classId || (createForm.classId ? Number(createForm.classId) : null),
      groupIds: [],
    })
    closeCreateDrawer()
    notice.value = `账号「${username}」已创建，并绑定到 ${boundLabel}`
    setTimeout(() => {
      if (notice.value) notice.value = ''
    }, 4000)
    await loadClassUsers()
    listTab.value = 'class'
  } catch (err) {
    formError.value = err?.message || '创建账号失败'
  } finally {
    saving.value = false
  }
}

async function loadProjectMembers() {
  const teams = await fetchMyTeams()
  const list = Array.isArray(teams) ? teams : []
  const targets =
    effectiveProjectId.value === 'all'
      ? list
      : list.filter((t) => String(t.id) === String(effectiveProjectId.value || ctx.projectId))
  const loadTargets = targets.length ? targets : list
  const dashboards = await Promise.all(
    loadTargets.map(async (team) => {
      try {
        const dash = await fetchTeamDashboard(team.id)
        return { team, dash }
      } catch {
        return { team, dash: null }
      }
    })
  )

  const next = []
  for (const { team, dash } of dashboards) {
    const projectName = team.projectName || team.name || `项目 ${team.id}`
    const members = dash?.members || dash?.memberList || team.members || []
    if (Array.isArray(members) && members.length) {
      members.forEach((m, index) => {
        const userId = m.userId ?? m.id ?? null
        next.push({
          key: `${team.id}-${userId || index}`,
          projectId: team.id,
          project: projectName,
          userId,
          name: m.username || m.name || m.realName || `成员${index + 1}`,
          position: m.positionName || m.position || m.roleName || '',
          role: m.roleInTeam || m.systemRole || m.role || '成员',
          systemRole: m.systemRole || m.role || '',
          account: m.username || m.account || m.studentNo || '',
        })
      })
    }
  }
  rows.value = next
}

async function loadClassUsers() {
  try {
    const [users, options] = await Promise.all([
      fetchOrgUsers().catch((err) => {
        console.warn('load org users failed', err)
        return []
      }),
      fetchOrganizationOptions().catch((err) => {
        console.warn('load org options failed', err)
        return {}
      }),
    ])
    classUsers.value = Array.isArray(users) ? users : []
    operatorScope.value = options?.operatorScope || null
    teachingScopes.value = Array.isArray(options?.teachingScopes) ? options.teachingScopes : []
    // 兼容：旧后端无 teachingScopes 时，用 operatorScope 拼一条
    if (!teachingScopes.value.length && operatorScope.value?.classId) {
      teachingScopes.value = [{ ...operatorScope.value }]
    }
  } catch {
    classUsers.value = []
    teachingScopes.value = []
  }
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    await Promise.all([loadProjectMembers(), loadClassUsers()])
  } catch (err) {
    error.value = err?.response?.data?.message || err?.message || '成员列表加载失败'
    rows.value = []
  } finally {
    loading.value = false
  }
}

async function refreshAll() {
  await load()
}

watch([() => ctx.projectId, () => ctx.loaded, projectFilter], load, { immediate: true })

onUnmounted(() => {
  lockBodyScroll(false)
})
</script>

<style scoped>
/* 工具栏 / Tab / 抽屉视觉由全局 teacher.css 统一（对齐学生端 token） */
.scope-metric {
  font-size: 14px !important;
  line-height: 1.3;
  word-break: break-all;
}
.col-actions {
  text-align: right;
  white-space: nowrap;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  align-items: center;
}

.member-cell {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
  max-width: 220px;
}
.member-cell__avatar {
  width: 32px;
  height: 32px;
  flex: none;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: #fff;
  font-size: 13px;
  font-weight: 800;
  line-height: 1;
  box-shadow: 0 1px 0 rgba(18, 20, 26, 0.06), 0 0 0 1px rgba(18, 20, 26, 0.04);
}
.member-cell__name {
  font-size: 13px;
  font-weight: 750;
  color: var(--ds-ink);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.task-drawer {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
}
.task-drawer .drawer-tip {
  margin: 14px 20px 0;
  flex-shrink: 0;
}
.task-drawer__body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 16px 20px 8px;
  display: grid;
  gap: 16px;
  align-content: start;
}
.create-blocked {
  padding: 20px 16px;
  border-radius: 12px;
  border: 1px dashed var(--ds-line-strong);
  background: #fafafa;
  text-align: center;
  display: grid;
  gap: 8px;
}
.create-blocked strong {
  font-size: 14px;
  color: var(--ds-ink);
}
.create-blocked p {
  margin: 0;
  color: var(--ds-muted);
  font-size: 12px;
  line-height: 1.55;
}
</style>
