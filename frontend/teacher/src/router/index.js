import { createRouter, createWebHistory } from 'vue-router'
import TeacherShell from '../components/TeacherShell.vue'
import { pathTitle } from '../config/nav'
import { canAccessTeacherPortal, clearAuth, isLoggedIn } from '../utils/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/LoginView.vue'),
    meta: { public: true, title: '登录' },
  },
  {
    path: '/',
    component: TeacherShell,
    children: [
      {
        path: '',
        name: 'Workbench',
        component: () => import('../views/WorkbenchView.vue'),
        meta: { title: '首页' },
      },

      // 项目团队
      {
        path: 'projects',
        name: 'ProjectList',
        component: () => import('../views/team/ProjectsView.vue'),
        meta: { title: '项目管理' },
      },
      {
        path: 'projects/create',
        name: 'ProjectCreate',
        component: () => import('../views/team/TeamCreateView.vue'),
        meta: { title: '新建项目' },
      },
      {
        path: 'projects/:projectId',
        name: 'ProjectDetail',
        component: () => import('../views/team/TeamWorkspaceView.vue'),
        meta: { title: '项目详情' },
      },
      {
        path: 'members',
        name: 'Members',
        component: () => import('../views/team/MembersView.vue'),
        meta: { title: '成员管理' },
      },
      // 旧路径兼容
      { path: 'team', redirect: '/projects' },
      { path: 'team/create', redirect: '/projects/create' },
      { path: 'team/members', redirect: '/members' },
      { path: 'team/tasks', redirect: '/members' },
      { path: 'team/:teamId', redirect: (to) => `/projects/${to.params.teamId}` },

      // 训练管理：训练营 = 计划（默认）+ 概览；旧 /camp/plan 重定向兼容
      {
        path: 'camp',
        name: 'CampWorkspace',
        component: () => import('../views/camp/CampWorkspaceView.vue'),
        meta: { title: '训练营' },
      },
      {
        path: 'camp/create',
        name: 'CampCreate',
        component: () => import('../views/camp/CampCreateView.vue'),
        meta: { title: '创建训练营' },
      },
      {
        path: 'camp/plan',
        name: 'CampPlan',
        redirect: (to) => ({
          path: '/camp',
          query: { ...to.query, tab: to.query.tab || 'plan' },
        }),
      },
      {
        path: 'camp/overview',
        redirect: (to) => ({
          path: '/camp',
          query: { ...to.query, tab: 'overview' },
        }),
      },
      {
        path: 'camp/review-queue',
        name: 'CampReviewQueue',
        component: () => import('../views/camp/CampReviewQueueView.vue'),
        meta: { title: '提交与批改' },
      },
      {
        path: 'camp/progress',
        name: 'CampProgress',
        component: () => import('../views/camp/CampProgressView.vue'),
        meta: { title: '训练进度' },
      },
      { path: 'camp/courses', redirect: '/camp' },
      {
        path: 'camp/exams',
        name: 'CampExams',
        component: () => import('../views/camp/CampExamsView.vue'),
        meta: { title: '题库与考试' },
      },

      // 路演管理
      {
        path: 'roadshow',
        name: 'RoadshowHome',
        component: () => import('../views/roadshow/RoadshowHomeView.vue'),
        meta: { title: '路演场次' },
      },
      // 兼容旧入口：录制回放并入路演场次子页
      {
        path: 'roadshow/recordings',
        redirect: { path: '/roadshow', query: { tab: 'recordings' } },
      },
      {
        path: 'roadshow/materials',
        name: 'RoadshowMaterials',
        component: () => import('../views/roadshow/RoadshowMaterialsView.vue'),
        meta: { title: '路演材料' },
      },
      { path: 'roadshow/ppt', redirect: '/ai/ppt' },
      { path: 'roadshow/scripts', redirect: '/ai/scripts' },

      // 评分 / 整改
      { path: 'review', redirect: '/review/reports' },
      {
        path: 'review/reports',
        name: 'ReviewReports',
        component: () => import('../views/review/ReviewReportsView.vue'),
        meta: { title: '评分报告' },
      },
      // 兼容旧入口：上传评分已嵌入评分报告子页
      {
        path: 'review/video-score',
        redirect: { path: '/review/reports', query: { tab: 'upload' } },
      },
      {
        path: 'review/ai-todos',
        name: 'ReviewAiTodos',
        component: () => import('../views/review/AiTodosView.vue'),
        meta: { title: '整改复盘' },
      },

      // 小启AI（与学生端同级独立入口；界面复用学生端工作台，教师权限）
      {
        path: 'assistant',
        name: 'Assistant',
        component: () => import('../views/ai/AssistantWorkspace.vue'),
        meta: { title: '小启AI', flushMain: true },
      },
      {
        path: 'assistant/c/:sessionId',
        name: 'AssistantSession',
        component: () => import('../views/ai/AssistantWorkspace.vue'),
        meta: { title: '小启AI', flushMain: true },
      },
      { path: 'ai/assistant', redirect: '/assistant' },

      // AI 应用（不含小启）
      {
        path: 'ai/ppt',
        name: 'AiPpt',
        component: () => import('../views/ai/PptManageView.vue'),
        meta: { title: 'PPT管理' },
      },
      {
        path: 'ai/scripts',
        name: 'AiScripts',
        component: () => import('../views/ai/ScriptManageView.vue'),
        meta: { title: '讲稿管理' },
      },

      // 资源
      {
        path: 'resources',
        name: 'Resources',
        component: () => import('../views/resources/ResourcesView.vue'),
        meta: { title: '资源管理' },
      },
      {
        path: 'inspire-office',
        name: 'TeacherInspireOffice',
        component: () => import('../views/inspire-office/TeacherInspireOfficeList.vue'),
        meta: { title: '启发 Office' },
      },
      {
        path: 'inspire-office/sdoc/:id',
        name: 'TeacherSmartDoc',
        component: () => import('../views/inspire-office/TeacherSmartDocPage.vue'),
        meta: { title: '智能文档', flushMain: true },
      },

      // 学情
      {
        path: 'analytics',
        name: 'Analytics',
        component: () => import('../views/analytics/AnalyticsView.vue'),
        meta: { title: '学情总览' },
      },
      {
        path: 'analytics/students',
        name: 'AnalyticsStudents',
        component: () => import('../views/analytics/StudentsView.vue'),
        meta: { title: '学生档案' },
      },
      {
        path: 'analytics/students/:userId',
        name: 'AnalyticsStudentProfile',
        component: () => import('../views/analytics/StudentProfileView.vue'),
        meta: { title: '学生详情' },
      },
      // 旧「荣誉与整改」已并入：荣誉→项目详情，整改→整改复盘
      {
        path: 'analytics/growth',
        redirect: '/analytics',
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

router.beforeEach((to) => {
  if (to.meta?.public) {
    // 已登录教师访问登录页 → 进工作台；学生 token 清掉避免串端
    if (to.path === '/login' && isLoggedIn()) {
      if (canAccessTeacherPortal()) return { path: '/' }
      clearAuth()
    }
    return true
  }
  if (!isLoggedIn()) return { path: '/login', query: { redirect: to.fullPath } }
  if (!canAccessTeacherPortal()) {
    clearAuth()
    return {
      path: '/login',
      query: { redirect: to.fullPath, reason: 'teacher-only' },
    }
  }
  return true
})

router.afterEach((to) => {
  const title = to.meta?.title || pathTitle(to.path, to.query || {})
  document.title = title ? `${title} · 启发·竞赛大脑` : '启发·竞赛大脑 · 教师端'
})

export default router
