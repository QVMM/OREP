<template>
  <div class="teacher-page">
    <header class="teacher-page__head">
      <div>
        <h1>项目管理</h1>
        <p>管理你指导的备赛项目，进入详情可编排成员、任务与材料。</p>
      </div>
      <div class="teacher-page__actions">
        <button type="button" class="teacher-btn teacher-btn--secondary" :disabled="loading" @click="load">刷新</button>
        <router-link class="teacher-btn teacher-btn--primary" to="/projects/create">新建项目</router-link>
      </div>
    </header>

    <p v-if="error" class="plan-notice is-error" role="alert">{{ error }}</p>

    <section class="teacher-metric-strip is-5">
      <article class="teacher-card teacher-metric-card"><small>项目总数</small><strong>{{ rows.length }}</strong></article>
      <article class="teacher-card teacher-metric-card"><small>训练中</small><strong>{{ counts.active }}</strong></article>
      <article class="teacher-card teacher-metric-card"><small>其他状态</small><strong>{{ counts.other }}</strong></article>
      <article class="teacher-card teacher-metric-card"><small>项目成员</small><strong>{{ counts.members }}</strong></article>
      <article class="teacher-card teacher-metric-card"><small>关联训练营</small><strong>{{ campCount }}</strong></article>
    </section>

    <section class="teacher-card">
      <div class="teacher-card__body">
        <div class="manager-toolbar">
          <div class="manager-toolbar__title">
            <strong>项目列表</strong>
            <span>共 {{ filtered.length }} 个</span>
          </div>
          <div class="manager-toolbar__tools">
            <input v-model.trim="keyword" type="search" placeholder="搜索项目 / 指导老师 / 赛道" />
            <select v-model="status">
              <option value="all">全部状态</option>
              <option value="active">训练中/进行中</option>
              <option value="other">其他</option>
            </select>
          </div>
        </div>

        <div v-if="loading" class="teacher-empty">正在加载项目…</div>
        <div v-else class="teacher-table-wrap">
          <table class="teacher-table teacher-table--clickable">
            <thead>
              <tr>
                <th>项目</th>
                <th>指导老师</th>
                <th>成员</th>
                <th>当前训练营</th>
                <th>状态</th>
                <th class="col-actions" aria-hidden="true"></th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="row in filtered"
                :key="row.id"
                class="is-row-link"
                role="link"
                tabindex="0"
                :aria-label="`进入项目 ${row.name}`"
                @click="openProject(row.id)"
                @keydown.enter.prevent="openProject(row.id)"
                @keydown.space.prevent="openProject(row.id)"
              >
                <td>
                  <strong>{{ row.name }}</strong>
                  <div class="teacher-muted row-sub">{{ row.track || '未填赛道' }}</div>
                </td>
                <td>
                  <template v-if="row.leads?.length">
                    <span
                      v-for="(name, idx) in row.leads"
                      :key="`${row.id}-mentor-${idx}`"
                      class="mentor-chip"
                    >{{ name }}</span>
                  </template>
                  <span v-else class="teacher-muted">—</span>
                </td>
                <td>{{ row.members ?? '—' }} 人</td>
                <td>
                  {{ row.campName || '—' }}
                  <div v-if="row.campProgress" class="teacher-muted row-sub">{{ row.campProgress }}</div>
                </td>
                <td>
                  <span class="teacher-tag" :class="isActive(row) ? 'is-ok' : 'is-warn'">{{ row.statusLabel }}</span>
                </td>
                <td class="col-actions" aria-hidden="true">
                  <span class="row-chevron">›</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="!loading && !filtered.length" class="teacher-empty">当前没有符合条件的项目</div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { fetchMyTeams, fetchTeacherCamps } from '../../api'
import { useTeacherContextStore } from '../../stores/context'
import { campStatusLabel, stageLabel, teamStatusLabel } from '../../utils/labels'

const router = useRouter()
const ctx = useTeacherContextStore()
const rows = ref([])
const camps = ref([])
const loading = ref(true)
const error = ref('')
const keyword = ref('')
const status = ref('all')

const campCount = computed(() => camps.value.length)
const counts = computed(() => ({
  active: rows.value.filter((r) => isActive(r)).length,
  other: rows.value.filter((r) => !isActive(r)).length,
  members: rows.value.reduce((sum, r) => sum + Number(r.members || 0), 0),
}))

const filtered = computed(() => {
  const q = keyword.value.toLowerCase()
  return rows.value.filter((row) => {
    if (status.value === 'active' && !isActive(row)) return false
    if (status.value === 'other' && isActive(row)) return false
    if (!q) return true
    return [row.name, row.lead, row.track, row.campName].join(' ').toLowerCase().includes(q)
  })
})

function isActive(row) {
  const s = String(row.status || '').toUpperCase()
  const label = String(row.statusLabel || '')
  return s === 'ACTIVE' || label.includes('进行') || label.includes('训练') || label.includes('集训') || label.includes('路演')
}

function openProject(id) {
  if (id == null || id === '') return
  router.push(`/projects/${id}`)
}

/** 汇总多个指导老师：mentorNames / mentorName / 数组字段 */
function parseMentorNames(team) {
  const raw = team.mentorNames ?? team.mentorName ?? team.lead ?? ''
  if (Array.isArray(raw)) {
    return raw.map((n) => String(n || '').trim()).filter(Boolean)
  }
  const text = String(raw || '').trim()
  if (!text) return []
  return text
    .split(/[、,，;；|/]/)
    .map((n) => n.trim())
    .filter(Boolean)
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [teams, campRows] = await Promise.all([fetchMyTeams(), fetchTeacherCamps()])
    camps.value = campRows || []
    const campByTeam = new Map()
    for (const camp of camps.value) {
      const key = String(camp.teamId)
      if (!campByTeam.has(key)) campByTeam.set(key, camp)
    }
    rows.value = (teams || []).map((team) => {
      const camp = campByTeam.get(String(team.id))
      const memberCount = Number(
        team.memberCount
          ?? team.studentMemberCount
          ?? team.totalMemberCount
          ?? team.members?.length
          ?? team.memberIds?.length
          ?? 0
      )
      const leads = parseMentorNames(team)
      return {
        id: team.id,
        name: team.projectName || team.name || team.teamName || `项目 ${team.id}`,
        leads,
        lead: leads.join('、') || '—',
        track: team.trackName || team.track || '',
        members: Number.isFinite(memberCount) ? memberCount : 0,
        status: team.status || team.phase || team.currentStage || '',
        statusLabel:
          team.statusLabel ||
          stageLabel(team.phase || team.currentStage) ||
          teamStatusLabel(team.status) ||
          '进行中',
        campName: camp?.campName || '',
        campProgress: camp
          ? `${campStatusLabel(camp.status)} · ${String(camp.startDate || '').slice(0, 10)} — ${String(camp.endDate || '').slice(0, 10)}`
          : '',
      }
    })
    ctx.setOptions({
      projects: rows.value.map((r) => ({
        id: r.id,
        name: r.name,
        members: r.members,
        status: r.status,
      })),
      camps: (campRows || []).map((camp) => ({
        ...camp,
        id: camp.campId,
        projectId: camp.teamId,
        name: camp.campName,
        meta: [campStatusLabel(camp.status), camp.startDate && camp.endDate ? `${String(camp.startDate).slice(0, 10)} — ${String(camp.endDate).slice(0, 10)}` : '']
          .filter(Boolean)
          .join(' · '),
        plan: camp.subtitle || (camp.totalDays ? `${camp.totalDays} 天` : ''),
      })),
      teams: (teams || []).map((t) => ({ ...t, projectId: t.id })),
    })
  } catch (err) {
    error.value = err?.response?.data?.message || err?.message || '项目列表加载失败'
    rows.value = []
    camps.value = []
  } finally {
    loading.value = false
  }
}

watch(() => ctx.loaded, load, { immediate: true })
</script>

<style scoped>
/* 列表页细节依赖全局 teacher.css（manager-toolbar / mentor-chip / plan-notice） */
.teacher-muted {
  color: var(--ds-muted, #71717a);
}
.row-sub {
  font-size: 12px;
  margin-top: 3px;
}
.teacher-table--clickable tbody tr.is-row-link {
  cursor: pointer;
  transition: background 0.12s ease;
}
.teacher-table--clickable tbody tr.is-row-link:hover td {
  background: rgba(15, 23, 42, 0.035);
}
.teacher-table--clickable tbody tr.is-row-link:focus-visible {
  outline: 2px solid var(--ds-orange, #e84a1c);
  outline-offset: -2px;
}
.teacher-table--clickable tbody tr.is-row-link:focus-visible td {
  background: rgba(232, 74, 28, 0.04);
}
.col-actions {
  width: 36px;
  text-align: right;
}
.row-chevron {
  color: var(--ds-faint, #a1a1aa);
  font-size: 18px;
  font-weight: 500;
  line-height: 1;
}
.teacher-table--clickable tbody tr.is-row-link:hover .row-chevron {
  color: var(--ds-orange-deep, #c2410c);
}
</style>
