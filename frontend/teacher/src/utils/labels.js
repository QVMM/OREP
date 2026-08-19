/**
 * 教师端展示文案：接口枚举 → 中文
 * 禁止把 ACTIVE / DRAFT 等英文枚举直接展示给用户。
 */

const TEAM_STATUS = {
  ACTIVE: '进行中',
  INACTIVE: '已停用',
  ARCHIVED: '已归档',
  COMPLETED: '已完成',
  PREPARING: '准备中',
  DRAFT: '草稿',
}

const CAMP_STATUS = {
  ACTIVE: '进行中',
  PLANNED: '未开始',
  PLANNED_ACTIVE: '进行中',
  ARCHIVED: '已归档',
  COMPLETED: '已结束',
  ENDED: '已结束',
  DRAFT: '草稿',
}

const DAY_STATUS = {
  DRAFT: '草稿',
  PUBLISHED: '已发布',
  CLOSED: '已关闭',
  WITHDRAWN: '已撤回',
  UNPLANNED: '未规划',
}

const SUBMISSION_STATUS = {
  PENDING_REVIEW: '待批改',
  REVIEWING: '批改中',
  APPROVED: '已通过',
  CHANGES_REQUESTED: '需修改',
  REJECTED: '未通过',
  NOT_SUBMITTED: '未提交',
  EXPIRED: '过期未交',
  DRAFT: '草稿',
  SUBMITTED: '已提交',
}

const MATERIAL_REVIEW = {
  APPROVED: '已通过',
  PENDING_REVIEW: '待审核',
  DRAFT: '草稿',
  CHANGES_REQUESTED: '需修改',
  REJECTED: '未通过',
}

const MATERIAL_TYPE = {
  DOCS: '文档',
  DOC: '文档',
  PPT: 'PPT',
  SCRIPT: '讲稿',
  VIDEO: '视频',
  LINK: '链接',
  AUDIO: '音频',
  IMAGE: '图片',
  FILE: '文件',
}

const STAGE = {
  PREPARATION: '准备阶段',
  COURSE: '课程学习',
  TRAINING: '集训阶段',
  EXAM: '练习考试',
  MATERIAL: '材料准备',
  ROADSHOW: '路演阶段',
  REVIEW: '复盘阶段',
  COMPLETED: '已完成',
}

const TASK_STATUS = {
  TODO: '待开始',
  IN_PROGRESS: '进行中',
  REVIEWING: '待审核',
  PENDING_REVIEW: '待审核',
  CHANGES_REQUESTED: '需修改',
  DONE: '已完成',
  CANCELLED: '已取消',
  COMPLETED: '已完成',
}

const MEETING_STATUS = {
  CREATED: '已创建',
  RUNNING: '进行中',
  ENDED: '已结束',
  CANCELLED: '已取消',
  READY: '已就绪',
  PROCESSING: '处理中',
  RECORDING: '录制中',
  STARTING: '准备中',
  FAILED: '处理失败',
}

const CERT_STATUS = {
  ACTIVE: '有效',
  REVOKED: '已撤销',
  INACTIVE: '已失效',
}

const AI_TODO_STATUS = {
  not_started: '未开始',
  draft: '草稿',
  teacher_edited: '教师已改',
  published: '已发布',
  PUBLISHED: '已发布',
  DRAFT: '草稿',
  OPEN: '待处理',
  open: '待处理',
  DONE: '已完成',
  done: '已完成',
}

/** 系统账号角色（users.role） */
const USER_ROLE = {
  ADMIN: '平台管理员',
  SCHOOL_ADMIN: '校级管理员',
  TEACHER: '教师',
  STUDENT: '学生',
  REVIEWER: '评委',
  EXPERT: '专家',
  USER: '用户',
}

/** 项目团队内角色（roleInTeam） */
const TEAM_ROLE = {
  CAPTAIN: '队长',
  MENTOR: '指导教师',
  MEMBER: '成员',
  TEACHER: '指导教师',
  STUDENT: '学生',
}

const PRIORITY = {
  LOW: '低',
  MEDIUM: '中',
  HIGH: '高',
  URGENT: '紧急',
  NORMAL: '普通',
  P0: '紧急',
  P1: '高',
  P2: '中',
  P3: '低',
  '0': '紧急',
  '1': '高',
  '2': '中',
  '3': '低',
}

function pick(map, value, fallback = '—') {
  if (value == null || value === '') return fallback
  const raw = String(value)
  const upper = raw.toUpperCase()
  if (Object.prototype.hasOwnProperty.call(map, raw)) return map[raw]
  if (Object.prototype.hasOwnProperty.call(map, upper)) return map[upper]
  // 已是中文则原样返回
  if (/[\u4e00-\u9fff]/.test(raw)) return raw
  return fallback === '—' && map[upper] == null ? raw : (map[upper] || fallback)
}

export function teamStatusLabel(value) {
  return pick(TEAM_STATUS, value, '进行中')
}

export function campStatusLabel(value) {
  return pick(CAMP_STATUS, value, '进行中')
}

export function dayStatusLabel(value) {
  return pick(DAY_STATUS, value, '草稿')
}

export function submissionStatusLabel(value) {
  return pick(SUBMISSION_STATUS, value, '未知')
}

export function materialReviewLabel(value) {
  return pick(MATERIAL_REVIEW, value, '未知')
}

export function materialTypeLabel(value) {
  return pick(MATERIAL_TYPE, value, value || '文件')
}

export function stageLabel(value) {
  return pick(STAGE, value, '未设置阶段')
}

export function taskStatusLabel(value) {
  return pick(TASK_STATUS, value, value || '未知')
}

export function meetingStatusLabel(value) {
  return pick(MEETING_STATUS, value, value || '未知')
}

export function certificateStatusLabel(value) {
  return pick(CERT_STATUS, value, value || '未知')
}

export function aiTodoStatusLabel(value) {
  return pick(AI_TODO_STATUS, value, value || '待处理')
}

/** 系统角色中文（禁止直接展示 TEACHER/STUDENT 等英文枚举） */
export function userRoleLabel(value) {
  return pick(USER_ROLE, value, value || '—')
}

/** 团队内角色中文（CAPTAIN/MEMBER/MENTOR） */
export function teamRoleLabel(value) {
  return pick(TEAM_ROLE, value, value || '成员')
}

/** 角色展示：先系统角色，再团队角色 */
export function anyRoleLabel(value) {
  if (value == null || value === '') return '—'
  const raw = String(value)
  if (/[\u4e00-\u9fff]/.test(raw)) return raw
  const upper = raw.toUpperCase()
  if (USER_ROLE[upper]) return USER_ROLE[upper]
  if (TEAM_ROLE[upper]) return TEAM_ROLE[upper]
  return raw
}

export function priorityLabel(value) {
  return pick(PRIORITY, value, value || '—')
}

/** 通用：优先用专用映射，否则尽量中文化 */
export function statusLabel(value) {
  if (value == null || value === '') return '—'
  const raw = String(value)
  if (/[\u4e00-\u9fff]/.test(raw)) return raw
  const upper = raw.toUpperCase()
  return (
    TEAM_STATUS[upper] ||
    CAMP_STATUS[upper] ||
    DAY_STATUS[upper] ||
    SUBMISSION_STATUS[upper] ||
    MATERIAL_REVIEW[upper] ||
    TASK_STATUS[upper] ||
    MEETING_STATUS[upper] ||
    CERT_STATUS[upper] ||
    USER_ROLE[upper] ||
    TEAM_ROLE[upper] ||
    PRIORITY[upper] ||
    AI_TODO_STATUS[raw] ||
    AI_TODO_STATUS[upper] ||
    '未知'
  )
}
