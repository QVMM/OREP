import request from '../utils/request'

function dataOf(res) {
  if (res && typeof res === 'object' && 'data' in res && 'code' in res) return res.data
  return res
}

export async function fetchDailyReportToday() {
  return dataOf(await request.get('/api/daily-reports/today', { silentError: true }))
}

export async function fetchDailyReportForDate(date) {
  return dataOf(await request.get('/api/daily-reports/for-date', {
    params: { date },
    silentError: true,
  }))
}

export async function fetchDailyReportHistory(limit = 60) {
  return dataOf(await request.get('/api/daily-reports', {
    params: { limit },
    silentError: true,
  })) || []
}

export async function fetchDailyReportStats() {
  return dataOf(await request.get('/api/daily-reports/stats', { silentError: true })) || {}
}

export async function fetchDailyReportDetail(id) {
  return dataOf(await request.get(`/api/daily-reports/${id}`))
}

export async function saveDailyReport(payload) {
  return dataOf(await request.post('/api/daily-reports', payload))
}
