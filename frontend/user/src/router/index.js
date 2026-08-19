import { createRouter, createWebHistory } from 'vue-router'
import { getUserToken } from '../utils/authStorage'

const routes = [
  {
    // 引导页下线：直接进登录
    path: '/intro',
    name: 'Intro',
    redirect: '/login',
  },
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false, publicShell: true }
  },
  {
    path: '/register',
    redirect: '/login'
  },
  {
    path: '/',
    name: 'Home',
    component: () => import('../modules/home/StudentHome.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/training/today',
    name: 'TrainingTasks',
    component: () => import('../modules/training/TrainingPlan.vue'),
    meta: { requiresAuth: true, moduleGroup: 'training' }
  },
  {
    path: '/training/plan',
    redirect: '/training/today'
  },
  {
    path: '/training/tasks/:taskId',
    name: 'TrainingTaskDetail',
    component: () => import('../modules/training/TrainingDayView.vue'),
    meta: { requiresAuth: true, moduleGroup: 'training' }
  },
  {
    path: '/training/days/:dayId',
    name: 'TrainingDayDetail',
    component: () => import('../modules/training/TrainingDayView.vue'),
    meta: { requiresAuth: true, moduleGroup: 'training' }
  },
  {
    path: '/training/submissions/:submissionId',
    name: 'TrainingSubmission',
    component: () => import('../modules/training/TrainingSubmission.vue'),
    meta: { requiresAuth: true, moduleGroup: 'training' }
  },
  {
    path: '/training/feedback/:submissionId',
    name: 'TrainingFeedback',
    component: () => import('../modules/training/TrainingFeedback.vue'),
    meta: { requiresAuth: true, moduleGroup: 'training' }
  },
  {
    path: '/track-match',
    redirect: '/training/today'
  },
  {
    path: '/course-learning/:pathMatch(.*)*',
    redirect: '/training/today'
  },
  {
    path: '/exam-system/:pathMatch(.*)*',
    redirect: '/training/today'
  },
  {
    path: '/online-meeting',
    name: 'OnlineMeeting',
    component: () => import('../views/OnlineMeeting.vue'),
    meta: { requiresAuth: true, title: '路演训练' }
  },
  {
    path: '/resource-center',
    name: 'ResourceCenter',
    component: () => import('../views/ScriptList.vue'),
    meta: { requiresAuth: true, moduleGroup: 'resources', defaultPrepTab: 'materials' }
  },
  {
    path: '/project-team/files',
    redirect: to => ({ path: '/resource-center', query: to.query })
  },
  {
    path: '/project-team/details/:workItemId',
    name: 'ProjectTaskDetail',
    component: () => import('../views/ProjectTeam.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/project-team',
    name: 'ProjectTeam',
    component: () => import('../views/ProjectTeam.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/meeting/:id',
    name: 'MeetingRoom',
    component: () => import('../views/MeetingRoom.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/meeting-history/:id',
    name: 'MeetingHistoryDetail',
    component: () => import('../views/MeetingReplay.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/score-result/:meetingId',
    name: 'ScoreResult',
    component: () => import('../views/ScoreResult.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/roadshow-chat/:meetingId',
    name: 'RoadshowChat',
    component: () => import('../views/RoadshowChat.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/assistant',
    name: 'AssistantHome',
    component: () => import('../views/assistant/AssistantWorkspace.vue'),
    meta: { requiresAuth: true, moduleGroup: 'assistant', flushMain: true, title: '小启AI' }
  },
  {
    path: '/assistant/c/:sessionId',
    name: 'AssistantChat',
    component: () => import('../views/assistant/AssistantWorkspace.vue'),
    meta: { requiresAuth: true, moduleGroup: 'assistant', flushMain: true, title: '小启AI' }
  },
  {
    path: '/ai-score/report/:sessionId',
    component: () => import('../views/ai-score-report/AiScoreReportLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: to => `/ai-score/report/${to.params.sessionId}/result` },
      { path: 'result', name: 'AiScoreReportResult', component: () => import('../views/ai-score-report/AiScoreReportResult.vue') },
      { path: 'todos', name: 'AiScoreReportTodos', component: () => import('../views/ai-score-report/AiScoreReportTodos.vue') },
      { path: 'why', name: 'AiScoreReportWhy', component: () => import('../views/ai-score-report/AiScoreReportWhy.vue') },
      { path: 'jury', name: 'AiScoreReportJury', component: () => import('../views/ai-score-report/AiScoreReportJury.vue') },
      { path: 'compare', name: 'AiScoreReportCompare', component: () => import('../views/ai-score-report/AiScoreReportCompare.vue') },
      // legacy redirects
      { path: 'overview', redirect: to => `/ai-score/report/${to.params.sessionId}/result` },
      { path: 'dimensions', redirect: to => `/ai-score/report/${to.params.sessionId}/why` },
      { path: 'evidence', redirect: to => `/ai-score/report/${to.params.sessionId}/why` },
      { path: 'voice', redirect: to => `/ai-score/report/${to.params.sessionId}/todos` },
      { path: 'presentation', redirect: to => `/ai-score/report/${to.params.sessionId}/todos` },
      { path: 'actions', redirect: to => `/ai-score/report/${to.params.sessionId}/todos` }
    ]
  },
  {
    path: '/ai-score/report-id/:reportId',
    component: () => import('../views/ai-score-report/AiScoreReportLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', redirect: to => `/ai-score/report-id/${to.params.reportId}/result` },
      { path: 'result', component: () => import('../views/ai-score-report/AiScoreReportResult.vue') },
      { path: 'todos', component: () => import('../views/ai-score-report/AiScoreReportTodos.vue') },
      { path: 'why', component: () => import('../views/ai-score-report/AiScoreReportWhy.vue') },
      { path: 'jury', component: () => import('../views/ai-score-report/AiScoreReportJury.vue') },
      { path: 'compare', component: () => import('../views/ai-score-report/AiScoreReportCompare.vue') },
      // legacy redirects
      { path: 'overview', redirect: to => `/ai-score/report-id/${to.params.reportId}/result` },
      { path: 'dimensions', redirect: to => `/ai-score/report-id/${to.params.reportId}/why` },
      { path: 'evidence', redirect: to => `/ai-score/report-id/${to.params.reportId}/why` },
      { path: 'voice', redirect: to => `/ai-score/report-id/${to.params.reportId}/todos` },
      { path: 'presentation', redirect: to => `/ai-score/report-id/${to.params.reportId}/todos` },
      { path: 'actions', redirect: to => `/ai-score/report-id/${to.params.reportId}/todos` }
    ]
  },
  {
    path: '/ai-score-upload',
    name: 'AiScoreUpload',
    component: () => import('../views/VideoScoreUpload.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/ai-score/report-prototype',
    redirect: '/statistics'
  },
  {
    path: '/ai-score/:meetingId',
    component: () => import('../views/ai-score-report/AiScoreReportLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      { path: '', name: 'AiScoreResult', redirect: to => `/ai-score/${to.params.meetingId}/result` },
      { path: 'result', component: () => import('../views/ai-score-report/AiScoreReportResult.vue') },
      { path: 'todos', component: () => import('../views/ai-score-report/AiScoreReportTodos.vue') },
      { path: 'why', component: () => import('../views/ai-score-report/AiScoreReportWhy.vue') },
      { path: 'jury', component: () => import('../views/ai-score-report/AiScoreReportJury.vue') },
      { path: 'compare', component: () => import('../views/ai-score-report/AiScoreReportCompare.vue') },
      // legacy redirects
      { path: 'overview', redirect: to => `/ai-score/${to.params.meetingId}/result` },
      { path: 'dimensions', redirect: to => `/ai-score/${to.params.meetingId}/why` },
      { path: 'evidence', redirect: to => `/ai-score/${to.params.meetingId}/why` },
      { path: 'voice', redirect: to => `/ai-score/${to.params.meetingId}/todos` },
      { path: 'presentation', redirect: to => `/ai-score/${to.params.meetingId}/todos` },
      { path: 'actions', redirect: to => `/ai-score/${to.params.meetingId}/todos` }
    ]
  },
  {
    path: '/statistics',
    name: 'Statistics',
    redirect: { path: '/online-meeting', query: { tab: 'reports' } }
  },
  {
    path: '/profile',
    name: 'Profile',
    component: () => import('../views/Profile.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/ai-apps',
    name: 'AiAppCenter',
    component: () => import('../views/AiAppCenter.vue'),
    meta: { requiresAuth: true, moduleGroup: 'aiApps' }
  },
  {
    path: '/inspire-office',
    name: 'InspireOffice',
    component: () => import('../views/inspire-office/InspireOfficeList.vue'),
    meta: { requiresAuth: true, moduleGroup: 'aiApps', flushMain: true, aiAppMode: 'landing' }
  },
  {
    path: '/inspire-office/workbench',
    name: 'InspireOfficeWorkbench',
    component: () => import('../views/inspire-office/InspireOfficeWorkbench.vue'),
    meta: { requiresAuth: true, moduleGroup: 'aiApps', flushMain: true, aiAppMode: 'workspace' }
  },
  {
    // 兼容旧链接：进入多标签工作台并聚焦该文档
    path: '/inspire-office/edit/:id',
    name: 'InspireOfficeEditor',
    component: () => import('../views/inspire-office/InspireOfficeWorkbench.vue'),
    meta: { requiresAuth: true, moduleGroup: 'aiApps', flushMain: true, aiAppMode: 'workspace' }
  },
  {
    path: '/inspire-office/sdoc/:id',
    name: 'InspireSmartDoc',
    component: () => import('../views/inspire-office/smart-doc/SmartDocPage.vue'),
    meta: { requiresAuth: true, moduleGroup: 'aiApps', flushMain: true, aiAppMode: 'workspace', title: '智能文档' }
  },
  {
    path: '/typing-practice',
    name: 'TypingPractice',
    component: () => import('../views/typing/TypingPracticeView.vue'),
    meta: { requiresAuth: true, moduleGroup: 'aiApps', flushMain: true, aiAppMode: 'landing' }
  },
  {
    path: '/typing-practice/play',
    name: 'TypingPlay',
    component: () => import('../views/typing/TypingPlayView.vue'),
    meta: { requiresAuth: true, moduleGroup: 'aiApps', flushMain: true, aiAppMode: 'workspace' }
  },
  {
    path: '/typing-practice/result',
    name: 'TypingResult',
    component: () => import('../views/typing/TypingResultView.vue'),
    meta: { requiresAuth: true, moduleGroup: 'aiApps', flushMain: true, aiAppMode: 'landing' }
  },
  {
    path: '/script-editor',
    name: 'ScriptList',
    component: () => import('../views/ScriptList.vue'),
    beforeEnter: (to) => {
      if (to.query.tab === 'topic') return '/training/today'
      if (to.query.tab === 'materials') {
        const query = { ...to.query }
        delete query.tab
        return { path: '/resource-center', query }
      }
      return true
    },
    meta: { requiresAuth: true, moduleGroup: 'aiApps', flushMain: true, aiAppMode: 'landing' }
  },
  {
    path: '/script-editor/detail/:scriptId',
    name: 'ScriptEditor',
    component: () => import('../views/ScriptEditor.vue'),
    meta: { requiresAuth: true, moduleGroup: 'aiApps', flushMain: true, aiAppMode: 'workspace' }
  },
  {
    path: '/script-editor/template/:templateId',
    name: 'ScriptEditorTemplate',
    component: () => import('../views/ScriptEditor.vue'),
    meta: { requiresAuth: true, moduleGroup: 'aiApps', flushMain: true, aiAppMode: 'workspace' }
  },
  {
    path: '/resources',
    name: 'Resources',
    component: () => import('../views/PptTemplate.vue'),
    meta: { requiresAuth: true, moduleGroup: 'aiApps' }
  },
  {
    // P2: converge entry — keep route name for old bookmarks, land on unified editor.
    path: '/ppt-generator',
    name: 'PptGenerator',
    redirect: (to) => ({
      path: '/ppt-editor',
      query: {
        ...to.query,
        view: to.query.view || 'setup'
      }
    }),
    meta: { requiresAuth: true, moduleGroup: 'aiApps', flushMain: true, aiAppMode: 'task' }
  },
  {
    path: '/roadshow',
    name: 'RoadshowGate',
    component: () => import('../views/roadshow/RoadshowGate.vue'),
    meta: { requiresAuth: true, moduleGroup: 'aiApps', flushMain: true, aiAppMode: 'landing' }
  },
  {
    path: '/roadshow/ingest',
    name: 'RoadshowIngest',
    component: () => import('../views/roadshow/RoadshowIngest.vue'),
    meta: { requiresAuth: true, moduleGroup: 'aiApps', flushMain: true, aiAppMode: 'landing' }
  },
  {
    path: '/roadshow/analyze/:id',
    name: 'RoadshowAnalyze',
    component: () => import('../views/roadshow/RoadshowAnalyze.vue'),
    meta: { requiresAuth: true, moduleGroup: 'aiApps', flushMain: true, aiAppMode: 'landing' }
  },
  {
    path: '/roadshow/fix/:id',
    name: 'RoadshowFix',
    component: () => import('../views/roadshow/RoadshowFix.vue'),
    meta: { requiresAuth: true, moduleGroup: 'aiApps', flushMain: true, aiAppMode: 'workspace' }
  },
  {
    path: '/roadshow/path/:id',
    name: 'RoadshowPath',
    component: () => import('../views/roadshow/RoadshowPath.vue'),
    meta: { requiresAuth: true, moduleGroup: 'aiApps', flushMain: true, aiAppMode: 'workspace' }
  },
  {
    path: '/roadshow/bind/:id',
    name: 'RoadshowBind',
    component: () => import('../views/roadshow/RoadshowBind.vue'),
    meta: { requiresAuth: true, moduleGroup: 'aiApps', flushMain: true, aiAppMode: 'workspace' }
  },
  {
    path: '/roadshow/print/:id',
    name: 'RoadshowPrint',
    component: () => import('../views/roadshow/RoadshowPrint.vue'),
    meta: { requiresAuth: true, moduleGroup: 'aiApps', flushMain: true, aiAppMode: 'workspace' }
  },
  {
    path: '/ppt-editor',
    name: 'PptEditor',
    component: () => import('../views/PptEditor.vue'),
    meta: { requiresAuth: true, moduleGroup: 'aiApps', flushMain: true, aiAppMode: 'landing' }
  },
  {
    // Legacy detail: still loads for numeric tasks; PptHistoryDetail falls back to editor for job ids.
    path: '/ppt-history/:id',
    name: 'PptHistoryDetail',
    component: () => import('../views/PptHistoryDetail.vue'),
    meta: { requiresAuth: true, moduleGroup: 'aiApps', flushMain: true, aiAppMode: 'task' }
  },
  {
    path: '/my-recordings',
    name: 'MyRecordings',
    component: () => import('../views/MyRecordings.vue'),
    meta: { requiresAuth: true, title: '路演回放' }
  },
  {
    path: '/daily-reports',
    name: 'DailyReportCenter',
    component: () => import('../views/daily-report/DailyReportCenter.vue'),
    meta: { requiresAuth: true, title: '日报中心' }
  },
  {
    path: '/daily-reports/write',
    name: 'DailyReportWrite',
    component: () => import('../views/daily-report/DailyReportWrite.vue'),
    meta: { requiresAuth: true, title: '写日报' }
  },
  {
    path: '/daily-reports/today',
    redirect: '/daily-reports/write'
  },
  {
    path: '/daily-reports/:id/edit',
    name: 'DailyReportEdit',
    component: () => import('../views/daily-report/DailyReportWrite.vue'),
    meta: { requiresAuth: true, title: '编辑日报' }
  },
  {
    path: '/daily-reports/:id',
    name: 'DailyReportDetail',
    component: () => import('../views/daily-report/DailyReportDetail.vue'),
    meta: { requiresAuth: true, title: '日报详情' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫：检查登录状态
router.beforeEach((to, from) => {
  const token = getUserToken()

  if (to.path === '/') {
    return token ? true : '/login'
  }

  // 登录页在已登录时：优先回到分享/深链目标，否则首页
  if (to.path === '/login' && token) {
    const redirect = safeInternalRedirect(to.query?.redirect)
    return redirect || '/'
  }

  if (to.meta.publicShell) {
    return true
  }

  if (to.meta.requiresAuth && !token) {
    // 保留目标路径，登录后直达（微信点分享链等场景）
    return {
      path: '/login',
      query: { redirect: to.fullPath },
    }
  }
})

/** 仅允许站内相对路径，防止 open redirect */
function safeInternalRedirect(raw) {
  if (raw == null || raw === '') return null
  let value = String(raw)
  try {
    value = decodeURIComponent(value)
  } catch {
    // keep raw
  }
  if (!value.startsWith('/') || value.startsWith('//')) return null
  if (value.startsWith('/login') || value.startsWith('/register')) return null
  return value
}

router.afterEach((to) => {
  document.title = to.meta.title ? `${to.meta.title}｜竞赛大脑` : '竞赛大脑'
  // 成功进入页面后清掉 chunk 重载标记，避免影响后续切换
  try {
    if (sessionStorage.getItem('orep_chunk_reload') === to.fullPath) {
      sessionStorage.removeItem('orep_chunk_reload')
    }
  } catch {
    /* ignore */
  }
})

/**
 * Vite dev 偶发 504 Outdated Optimize Dep / 动态 chunk 拉取失败时，
 * 动态 import 会抛错，表现为「点了菜单空白」。自动硬刷新一次目标路由。
 */
router.onError((error, to) => {
  const msg = String(error?.message || error || '')
  const isChunkError =
    msg.includes('Failed to fetch dynamically imported module')
    || msg.includes('Importing a module script failed')
    || msg.includes('Outdated Optimize Dep')
    || msg.includes('error loading dynamically imported module')
    || (error?.name === 'TypeError' && msg.includes('import'))

  if (!isChunkError || typeof window === 'undefined') {
    console.error('[router]', error)
    return
  }

  const target = to?.fullPath || window.location.pathname + window.location.search
  const key = 'orep_chunk_reload'
  try {
    const last = sessionStorage.getItem(key)
    if (last === target) {
      console.error('[router] dynamic import failed after reload:', error)
      return
    }
    sessionStorage.setItem(key, target)
  } catch {
    // ignore storage errors
  }
  window.location.assign(target)
})

export default router
