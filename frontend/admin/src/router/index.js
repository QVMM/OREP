import { createRouter, createWebHistory } from 'vue-router'
import { getAdminRole, getAdminToken } from '../utils/authStorage'
import { canAccessAdmin, canAccessRoute } from '../utils/permissions'

const ADMIN_ROLES = ['ADMIN', 'SCHOOL_ADMIN', 'TEACHER']
const ADMIN_SHELL_ROLES = ['ADMIN', 'SCHOOL_ADMIN', 'TEACHER', 'EXPERT', 'REVIEWER']
const WRITE_ROLES = ['ADMIN', 'SCHOOL_ADMIN']
const TEACHER_OWNED_RESOURCE_ROLES = ['ADMIN', 'SCHOOL_ADMIN', 'TEACHER']
const USER_MANAGEMENT_ROLES = ['ADMIN', 'SCHOOL_ADMIN', 'TEACHER']
const ISSUE_ROLES = ['ADMIN', 'SCHOOL_ADMIN', 'TEACHER', 'EXPERT', 'REVIEWER']

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/no-access',
    name: 'NoAccess',
    component: () => import('../views/NoAccess.vue'),
    meta: { requiresAuth: false, title: '无权访问' }
  },
  {
    path: '/',
    component: () => import('../views/Layout.vue'),
    meta: { requiresAuth: true, roles: ADMIN_SHELL_ROLES },
    children: [
      {
        path: '',
        redirect: '/dashboard'
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { title: '统计概览', roles: ADMIN_ROLES }
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('../views/Users.vue'),
        meta: { title: '用户管理', roles: USER_MANAGEMENT_ROLES }
      },
      {
        path: 'organization',
        redirect: '/organization/units',
        meta: { title: '组织分组', roles: WRITE_ROLES, write: true }
      },
      {
        path: 'organization/units',
        name: 'OrganizationManagement',
        component: () => import('../views/OrganizationManagement.vue'),
        meta: { title: '组织架构', roles: WRITE_ROLES, write: true }
      },
      {
        path: 'organization/groups',
        name: 'UserGroupManagement',
        component: () => import('../views/UserGroupManagement.vue'),
        meta: { title: '用户组', roles: WRITE_ROLES, write: true }
      },
      {
        path: 'meetings',
        name: 'Meetings',
        component: () => import('../views/Meetings.vue'),
        meta: { title: '会议管理', roles: ADMIN_ROLES }
      },
      {
        path: 'scores',
        name: 'Scores',
        component: () => import('../views/Scores.vue'),
        meta: { title: '评分查看', roles: ADMIN_ROLES }
      },
      {
        path: 'ai-jury-personas',
        name: 'AiJuryPersonas',
        component: () => import('../views/AiJuryPersonas.vue'),
        meta: { title: 'AI评审团画像', roles: WRITE_ROLES, write: true }
      },
      {
        path: 'issues',
        name: 'Issues',
        component: () => import('../views/Issues.vue'),
        meta: { title: '问题跟踪', roles: ISSUE_ROLES }
      },
      {
        path: 'analytics',
        name: 'Analytics',
        component: () => import('../views/Analytics.vue'),
        meta: { title: '数据分析', roles: ADMIN_ROLES }
      },
      {
        path: 'monitor',
        name: 'DataMonitor',
        component: () => import('../views/DataMonitor.vue'),
        meta: { title: '数据监控', roles: ['ADMIN'] }
      },
      {
        path: 'resources',
        name: 'Resources',
        component: () => import('../views/Resources.vue'),
        meta: { title: '资源管理', roles: WRITE_ROLES, write: true }
      },
      {
        path: 'file-center-management',
        name: 'FileCenterManagement',
        component: () => import('../views/FileCenterManagement.vue'),
        meta: { title: '文件中心管理', roles: ['ADMIN'], write: true }
      },
      {
        path: 'home-banners',
        name: 'HomeBannerManagement',
        component: () => import('../views/HomeBannerManagement.vue'),
        meta: { title: '首页轮播', roles: WRITE_ROLES, write: true }
      },
      {
        path: 'course-management',
        name: 'CourseManagement',
        component: () => import('../views/CourseManagement.vue'),
        meta: { title: '课程管理', roles: TEACHER_OWNED_RESOURCE_ROLES, write: true }
      },
      {
        path: 'exam-management',
        name: 'ExamManagement',
        component: () => import('../views/ExamManagement.vue'),
        meta: { title: '考试管理', roles: TEACHER_OWNED_RESOURCE_ROLES, write: true }
      },
      {
        path: 'ppt-management',
        name: 'PptManagement',
        component: () => import('../views/PptManagement.vue'),
        meta: { title: 'PPT管理', roles: WRITE_ROLES, write: true }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes
})

router.beforeEach((to) => {
  const token = getAdminToken()
  const role = getAdminRole()

  if (to.path === '/login') {
    if (token && canAccessAdmin(role)) {
      return firstAccessiblePath(role)
    }
    return true
  }

  if (to.meta.requiresAuth === false) {
    return true
  }

  if (!token) {
    return '/login'
  }

  if (!canAccessAdmin(role)) {
    return '/no-access'
  }

  const requiredRoles = to.matched
    .map((record) => record.meta?.roles)
    .filter(Boolean)
    .flat()

  if (requiredRoles.length > 0 && !canAccessRoute(role, requiredRoles)) {
    return firstAccessiblePath(role)
  }

  return true
})

function firstAccessiblePath(role) {
  const shell = routes.find((item) => item.path === '/')
  const child = shell?.children?.find((item) => {
    if (!item.path || item.redirect) return false
    return canAccessRoute(role, item.meta?.roles || [])
  })
  return child ? `/${child.path}` : '/no-access'
}

export default router
