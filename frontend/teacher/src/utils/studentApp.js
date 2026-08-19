/**
 * 学生端公开入口基址（会议、评分报告结果页等）。
 * 禁止写死 localhost；优先环境变量，开发态按端口推断，生产同域。
 *
 * 配置示例：
 *   VITE_STUDENT_APP_URL=https://app.example.com
 *   或开发：VITE_STUDENT_APP_URL=http://192.168.1.10:5174
 */

function stripTrailingSlash(url) {
  return String(url || '').replace(/\/+$/, '')
}

/**
 * @returns {string} 学生端 origin（无尾斜杠），如 https://host:5174
 */
export function getStudentAppBase() {
  const fromEnv = import.meta.env.VITE_STUDENT_APP_URL || import.meta.env.VITE_STUDENT_ORIGIN || ''
  if (fromEnv) return stripTrailingSlash(fromEnv)

  if (typeof window === 'undefined') return ''

  const { protocol, hostname, port } = window.location

  // 教师端 Vite 默认 5175 → 学生端 5174
  if (port === '5175') {
    return `${protocol}//${hostname}:5174`
  }
  // 偶发教师走 5176 等
  if (port && port !== '80' && port !== '443' && port !== '') {
    // 同 host 无端口时可能是反代；有端口且不是常见生产端口时，尝试 5174
    if (['5173', '5176', '4173'].includes(port)) {
      return `${protocol}//${hostname}:5174`
    }
  }

  // 生产：同域根路径即学生端（教师在 /teacher/）
  return `${protocol}//${hostname}${port ? `:${port}` : ''}`
}

/**
 * @param {string} path 以 / 开头的学生端路径
 */
export function studentAppUrl(path = '/') {
  const base = getStudentAppBase()
  const p = path.startsWith('/') ? path : `/${path}`
  if (!base) return p
  return `${base}${p}`
}

export function studentMeetingUrl(meetingId) {
  return studentAppUrl(`/meeting/${meetingId}`)
}

export function studentAiReportUrl({ reportId, sessionId, meetingId } = {}) {
  if (reportId) return studentAppUrl(`/ai-score/report-id/${reportId}/result`)
  if (sessionId) return studentAppUrl(`/ai-score/report/${sessionId}/result`)
  if (meetingId) return studentAppUrl(`/ai-score/${meetingId}/result`)
  return ''
}

export function studentCourseUrl(courseId) {
  return studentAppUrl(`/course-learning/${courseId}`)
}
