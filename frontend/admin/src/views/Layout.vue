<template>
  <el-container class="layout-container">
    <el-aside width="220px" class="aside">
      <div class="logo">
        <div class="logo-mark">O</div>
        <div>
          <strong>竞赛备赛大脑</strong>
          <span>管理控制台</span>
        </div>
      </div>
      <el-menu
        :default-active="activeMenu"
        class="el-menu-vertical"
        :background-color="menuColors.background"
        :text-color="menuColors.text"
        :active-text-color="menuColors.active"
        router
      >
        <el-sub-menu v-if="showWorkbenchGroup" index="workbench-group">
          <template #title>
            <el-icon><DataAnalysis /></el-icon>
            <span>工作台</span>
          </template>
          <el-menu-item v-if="showMenu('/dashboard')" index="/dashboard">
            <span>统计概览</span>
          </el-menu-item>
        </el-sub-menu>

        <el-sub-menu v-if="showUserGroup" index="user-group">
          <template #title>
            <el-icon><User /></el-icon>
            <span>用户与组织</span>
          </template>
          <el-menu-item v-if="showMenu('/users')" index="/users">
            <span>用户管理</span>
          </el-menu-item>
          <el-menu-item v-if="showMenu('/organization/units')" index="/organization/units">
            <span>组织架构</span>
          </el-menu-item>
          <el-menu-item v-if="showMenu('/organization/groups')" index="/organization/groups">
            <span>用户组</span>
          </el-menu-item>
        </el-sub-menu>

        <el-sub-menu v-if="showReviewGroup" index="review-group">
          <template #title>
            <el-icon><VideoCamera /></el-icon>
            <span>路演评审</span>
          </template>
          <el-menu-item v-if="showMenu('/meetings')" index="/meetings">
            <span>会议管理</span>
          </el-menu-item>
          <el-menu-item v-if="showMenu('/scores')" index="/scores">
            <span>评分查看</span>
          </el-menu-item>
          <el-menu-item v-if="showMenu('/issues')" index="/issues">
            <span>问题跟踪</span>
          </el-menu-item>
          <el-menu-item v-if="showMenu('/ai-jury-personas')" index="/ai-jury-personas">
            <span>AI评审团</span>
          </el-menu-item>
        </el-sub-menu>

        <el-sub-menu v-if="showResourceGroup" index="resource-group">
          <template #title>
            <el-icon><FolderOpened /></el-icon>
            <span>内容资源</span>
          </template>
          <el-menu-item v-if="showMenu('/home-banners')" index="/home-banners">
            <el-icon><Picture /></el-icon>
            <span>首页轮播</span>
          </el-menu-item>
          <el-menu-item v-if="showMenu('/resources')" index="/resources">
            <el-icon><Document /></el-icon>
            <span>PPT 资源</span>
          </el-menu-item>
          <el-menu-item v-if="showMenu('/file-center-management')" index="/file-center-management">
            <el-icon><Folder /></el-icon>
            <span>文件中心</span>
          </el-menu-item>
          <el-menu-item v-if="showMenu('/course-management')" index="/course-management">
            <el-icon><Reading /></el-icon>
            <span>课程管理</span>
          </el-menu-item>
          <el-menu-item v-if="showMenu('/exam-management')" index="/exam-management">
            <el-icon><EditPen /></el-icon>
            <span>考试管理</span>
          </el-menu-item>
          <el-menu-item v-if="showMenu('/ppt-management')" index="/ppt-management">
            <el-icon><Picture /></el-icon>
            <span>PPT 任务</span>
          </el-menu-item>
        </el-sub-menu>

        <el-sub-menu v-if="showDataGroup" index="data-group">
          <template #title>
            <el-icon><PieChart /></el-icon>
            <span>数据运营</span>
          </template>
          <el-menu-item v-if="showMenu('/analytics')" index="/analytics">
            <span>数据分析</span>
          </el-menu-item>
          <el-menu-item v-if="showMenu('/monitor')" index="/monitor">
            <span>数据监控</span>
          </el-menu-item>
        </el-sub-menu>
      </el-menu>
    </el-aside>

    <!-- 主体区域 -->
    <el-container>
      <el-header class="header">
        <div>
          <div class="header-title">{{ currentTitle }}</div>
          <div class="header-subtitle">统一管理会议、用户、内容资源与评分闭环</div>
        </div>
        <div class="header-right">
          <el-tag v-if="userStore.readOnlyMode" size="small" type="warning" effect="light">只读模式</el-tag>
          <div class="user-chip">
            <span class="avatar">{{ usernameInitial }}</span>
            <div>
              <strong>{{ userStore.username || '管理员' }}</strong>
              <small>{{ userStore.roleDisplay || '管理成员' }}</small>
            </div>
          </div>
          <el-button plain size="small" @click="handleLogout">
            <el-icon><SwitchButton /></el-icon>
            退出登录
          </el-button>
        </div>
      </el-header>

      <!-- 内容区 -->
      <el-main class="main">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '../stores/user'
import { canAccessRoute } from '../utils/permissions'

const MENU_ROLE_MAP = {
  '/dashboard': ['ADMIN', 'SCHOOL_ADMIN', 'TEACHER'],
  '/users': ['ADMIN', 'SCHOOL_ADMIN', 'TEACHER'],
  '/organization': ['ADMIN', 'SCHOOL_ADMIN'],
  '/organization/units': ['ADMIN', 'SCHOOL_ADMIN'],
  '/organization/groups': ['ADMIN', 'SCHOOL_ADMIN'],
  '/meetings': ['ADMIN', 'SCHOOL_ADMIN', 'TEACHER'],
  '/scores': ['ADMIN', 'SCHOOL_ADMIN', 'TEACHER'],
  '/ai-jury-personas': ['ADMIN', 'SCHOOL_ADMIN'],
  '/issues': ['ADMIN', 'SCHOOL_ADMIN', 'TEACHER', 'EXPERT', 'REVIEWER'],
  '/analytics': ['ADMIN', 'SCHOOL_ADMIN', 'TEACHER'],
  '/monitor': ['ADMIN'],
  '/home-banners': ['ADMIN', 'SCHOOL_ADMIN'],
  '/resources': ['ADMIN', 'SCHOOL_ADMIN'],
  '/file-center-management': ['ADMIN'],
  '/course-management': ['ADMIN', 'SCHOOL_ADMIN', 'TEACHER'],
  '/exam-management': ['ADMIN', 'SCHOOL_ADMIN', 'TEACHER'],
  '/ppt-management': ['ADMIN', 'SCHOOL_ADMIN'],
}
import {
  DataAnalysis, User, VideoCamera,
  PieChart, SwitchButton, FolderOpened, Document, Picture, Reading, EditPen, Folder
} from '@element-plus/icons-vue'

const route = useRoute()
const navRouter = useRouter()
const userStore = useUserStore()

const menuColors = {
  background: 'var(--admin-sidebar)',
  text: 'var(--admin-sidebar-text)',
  active: 'var(--admin-sidebar-active)',
}

const routeRoleMap = MENU_ROLE_MAP

function showMenu(path) {
  const roles = routeRoleMap[path]
  return canAccessRoute(userStore.role, roles || ['ADMIN', 'SCHOOL_ADMIN', 'TEACHER'])
}

const showWorkbenchGroup = computed(() => showMenu('/dashboard'))
const showUserGroup = computed(() => (
  showMenu('/users')
  || showMenu('/organization/units')
  || showMenu('/organization/groups')
))
const showReviewGroup = computed(() => (
  showMenu('/meetings')
  || showMenu('/scores')
  || showMenu('/issues')
  || showMenu('/ai-jury-personas')
))
const showResourceGroup = computed(() => (
  showMenu('/home-banners')
  || showMenu('/resources')
  || showMenu('/file-center-management')
  || showMenu('/course-management')
  || showMenu('/exam-management')
  || showMenu('/ppt-management')
))
const showDataGroup = computed(() => (
  showMenu('/analytics')
  || showMenu('/monitor')
))

// 当前激活的菜单项
const activeMenu = computed(() => route.path)

// 当前页面标题
const currentTitle = computed(() => route.meta?.title || '竞赛大脑管理后台')
const usernameInitial = computed(() => (userStore.username || 'A').charAt(0).toUpperCase())

// 退出登录
function handleLogout() {
  userStore.logout()
  navRouter.push('/login')
}
</script>

<style scoped>
.layout-container {
  height: 100%;
}
.aside {
  background-color: var(--admin-sidebar);
  overflow: hidden;
  box-shadow: 10px 0 30px rgba(0, 0, 0, 0.08);
}
.logo {
  height: 72px;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 18px;
  color: #fff;
  background-color: var(--admin-sidebar-logo);
}

.logo-mark {
  width: 36px;
  height: 36px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  background: var(--admin-primary);
  color: #fff;
  font-weight: 900;
}

.logo strong {
  display: block;
  font-size: 15px;
  line-height: 1.2;
}

.logo span {
  display: block;
  margin-top: 4px;
  color: var(--admin-sidebar-muted);
  font-size: 12px;
}

.el-menu-vertical {
  border-right: none;
  height: calc(100% - 72px);
  padding: 10px 8px;
}

.el-menu-vertical :deep(.el-menu-item),
.el-menu-vertical :deep(.el-sub-menu__title) {
  height: 44px;
  margin: 4px 0;
  border-radius: 12px;
}

.el-menu-vertical :deep(.el-menu-item.is-active) {
  background: rgba(243, 107, 23, 0.14);
  font-weight: 800;
}
.header {
  background: var(--admin-surface);
  border-bottom: 1px solid var(--admin-border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 72px;
  padding: 0 24px;
  box-shadow: var(--admin-shadow-soft);
}
.header-title {
  font-size: 19px;
  font-weight: 800;
  color: var(--admin-text-strong);
}

.header-subtitle {
  margin-top: 4px;
  color: var(--admin-muted);
  font-size: 12px;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.user-chip {
  display: flex;
  align-items: center;
  gap: 9px;
  padding: 6px 10px;
  border: 1px solid var(--admin-border-soft);
  border-radius: 999px;
  background: var(--admin-surface-soft);
}

.avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  background: var(--admin-primary);
  color: #fff;
  font-weight: 800;
  font-size: 12px;
}

.user-chip strong,
.user-chip small {
  display: block;
  line-height: 1.2;
}

.user-chip strong {
  color: var(--admin-text-strong);
  font-size: 13px;
}

.user-chip small {
  margin-top: 2px;
  color: var(--admin-muted);
  font-size: 11px;
}
.main {
  background: var(--admin-bg);
  padding: 24px;
  overflow-y: auto;
}

.theme-toggle {
  border-color: var(--admin-border);
  background: var(--admin-surface-soft);
  color: var(--admin-text);
}

.theme-toggle:hover {
  border-color: var(--el-color-primary);
  color: var(--el-color-primary);
}
</style>
