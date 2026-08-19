import { defineStore } from 'pinia'

/**
 * 教师端全局上下文：项目 / 训练营
 * 仅承载后端真实数据，不内置演示样例。
 */
export const useTeacherContextStore = defineStore('teacherContext', {
  state: () => ({
    projectId: '',
    campId: '',
    teamId: 'all',
    roleLabel: '主指导老师',
    projectRows: [],
    campRows: [],
    teamRows: [],
    loaded: false,
    loadError: '',
  }),
  getters: {
    projects: (state) => state.projectRows,
    camps(state) {
      return state.campRows.filter((c) => !state.projectId || String(c.projectId) === String(state.projectId))
    },
    allCamps: (state) => state.campRows,
    teams(state) {
      return state.teamRows.filter((t) => !state.projectId || String(t.projectId) === String(state.projectId))
    },
    projectName(state) {
      return state.projectRows.find((p) => String(p.id) === String(state.projectId))?.name || '未选择项目'
    },
    campName(state) {
      return state.campRows.find((c) => String(c.id) === String(state.campId))?.name || '未选择训练营'
    },
    campMeta(state) {
      const camp = state.campRows.find((c) => String(c.id) === String(state.campId))
      if (!camp) return ''
      if (camp.meta) return camp.meta
      const parts = []
      if (camp.status) parts.push(camp.status)
      if (camp.startDate && camp.endDate) parts.push(`${String(camp.startDate).slice(0, 10)} — ${String(camp.endDate).slice(0, 10)}`)
      return parts.join(' · ')
    },
    projectSummary(state) {
      const p = state.projectRows.find((row) => String(row.id) === String(state.projectId))
      if (!p) return ''
      const n = p.members ?? p.memberCount
      return n != null ? `${n} 人` : ''
    },
    hasProjects: (state) => state.projectRows.length > 0,
    hasCamps: (state) => state.campRows.length > 0,
  },
  actions: {
    setOptions({ projects = [], camps = [], teams = [] }) {
      this.projectRows = Array.isArray(projects) ? projects : []
      this.campRows = Array.isArray(camps) ? camps : []
      this.teamRows = Array.isArray(teams) && teams.length
        ? teams
        : this.projectRows.map((p) => ({ id: p.id, name: p.name, projectId: p.id }))
      this.loaded = true
      this.loadError = ''

      if (!this.projectRows.some((item) => String(item.id) === String(this.projectId))) {
        this.projectId = this.projectRows[0]?.id || ''
      }
      const campsForProject = this.campRows.filter((c) => String(c.projectId) === String(this.projectId))
      if (!campsForProject.some((item) => String(item.id) === String(this.campId))) {
        this.campId = campsForProject[0]?.id || this.campRows[0]?.id || ''
      }
      if (this.teamId !== 'all' && !this.teamRows.some((item) => String(item.id) === String(this.teamId))) {
        this.teamId = 'all'
      }
    },
    setLoadError(message) {
      this.loadError = message || '上下文加载失败'
      this.loaded = true
    },
    setProject(id) {
      this.projectId = id
      const camps = this.campRows.filter((c) => String(c.projectId) === String(id))
      if (!camps.some((c) => String(c.id) === String(this.campId))) {
        this.campId = camps[0]?.id || ''
      }
      const teams = this.teamRows.filter((t) => String(t.projectId) === String(id))
      if (this.teamId !== 'all' && !teams.some((t) => String(t.id) === String(this.teamId))) {
        this.teamId = 'all'
      }
    },
    setCamp(id) {
      this.campId = id
      const camp = this.campRows.find((c) => String(c.id) === String(id))
      if (camp?.projectId && String(camp.projectId) !== String(this.projectId)) {
        this.projectId = camp.projectId
      }
    },
    setTeam(id) {
      this.teamId = id
    },
  },
})
