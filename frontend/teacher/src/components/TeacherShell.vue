<template>
  <div class="teacher-app-shell" @click="onShellClick">
    <!-- 侧栏 -->
    <aside class="teacher-sidebar" aria-label="教师端导航">
      <button class="teacher-sidebar__brand" type="button" title="返回首页" @click="router.push('/')">
        <img
          class="teacher-sidebar__logo"
          src="/brand/competition-brain-mark.svg?v=20260803"
          alt=""
          width="36"
          height="36"
        />
        <span class="teacher-sidebar__brand-text">
          <strong>启发·竞赛大脑</strong>
          <small>教师端</small>
        </span>
      </button>

      <nav class="teacher-sidebar__nav" aria-label="一级与二级导航">
        <template v-for="group in TEACHER_NAV" :key="group.key">
          <!-- 首页 / 小启AI：单页入口（与分组父级同高、同间距） -->
          <router-link
            v-if="group.path"
            :to="group.path"
            class="teacher-nav-link teacher-nav-link--leaf"
            :class="{
              'is-active': moduleKey === group.key,
              'is-xiaoqi-nav': group.icon === 'xiaoqi',
            }"
          >
            <span
              class="teacher-nav-link__icon"
              :class="{ 'teacher-nav-link__icon--xiaoqi': group.icon === 'xiaoqi' || group.key === 'assistant' }"
              aria-hidden="true"
            >
              <TeacherModuleIcon
                :name="group.icon === 'xiaoqi' ? 'assistant' : group.key"
                :variant="moduleKey === group.key ? 'filled' : 'outline'"
                :hoverable="true"
              />
            </span>
            <span class="teacher-nav-link__label">{{ group.label }}</span>
          </router-link>

          <!-- 分组：可展开 -->
          <section
            v-else
            class="teacher-nav-group"
            :class="{ 'is-open': openNav === group.key, 'is-current': moduleKey === group.key }"
          >
            <button
              type="button"
              class="teacher-nav-link teacher-nav-link--parent"
              :class="{ 'is-active': moduleKey === group.key && openNav === group.key }"
              :aria-expanded="openNav === group.key"
              @click.stop="toggleNav(group.key)"
            >
              <span class="teacher-nav-link__icon" aria-hidden="true">
                <TeacherModuleIcon
                  :name="group.key"
                  :variant="moduleKey === group.key ? 'filled' : 'outline'"
                />
              </span>
              <span class="teacher-nav-link__label">{{ group.label }}</span>
              <svg class="teacher-nav-link__chevron" viewBox="0 0 20 20" aria-hidden="true">
                <path d="m6 8 4 4 4-4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" />
              </svg>
            </button>
            <div class="teacher-nav-sub" :class="{ 'is-open': openNav === group.key }">
              <div class="teacher-nav-sub__inner">
                <router-link
                  v-for="child in group.children"
                  :key="child.key"
                  :to="toLocation(child.path, child.query)"
                  class="teacher-nav-sublink"
                  :class="{ 'is-active': isChildActive(child) }"
                >
                  <span class="teacher-nav-sublink__dot" aria-hidden="true" />
                  <span class="teacher-nav-sublink__label">{{ child.label }}</span>
                </router-link>
              </div>
            </div>
          </section>
        </template>
      </nav>

    </aside>

    <!-- 顶栏 -->
    <header class="teacher-topbar">
      <div class="teacher-topbar__left">
        <button
          type="button"
          class="teacher-context-btn"
          :aria-expanded="contextOpen"
          :disabled="!ctx.hasProjects && !ctx.hasCamps"
          @click.stop="toggleContext"
        >
          <span class="teacher-context-btn__icon" aria-hidden="true">
            <svg viewBox="0 0 24 24" width="18" height="18">
              <path d="M4 7h16M4 12h10M4 17h14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
            </svg>
          </span>
          <span class="teacher-context-btn__copy">
            <small>项目 / 训练营</small>
            <strong>
              <template v-if="ctx.hasProjects">{{ ctx.projectName }}</template>
              <template v-else>未选择</template>
              <em v-if="ctx.hasCamps"> / {{ ctx.campName }}</em>
            </strong>
          </span>
          <svg class="teacher-context-btn__chevron" viewBox="0 0 20 20" aria-hidden="true">
            <path d="m5 7.5 5 5 5-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </button>
        <span v-if="ctx.loadError" class="teacher-topbar__warn" :title="ctx.loadError">加载异常</span>
      </div>

      <div class="teacher-topbar__right">
        <button
          type="button"
          class="teacher-icon-btn"
          aria-label="消息"
          title="消息"
          @click.stop="toggleNotif"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true" width="18" height="18">
            <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
            <path d="M10 21h4" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
          </svg>
        </button>

        <button
          type="button"
          class="teacher-account-btn"
          :aria-expanded="accountOpen"
          @click.stop="toggleAccount"
        >
          <span class="teacher-account-btn__avatar">{{ avatarChar }}</span>
          <span class="teacher-account-btn__meta">
            <strong>{{ userName }}</strong>
            <small>{{ roleText }}</small>
          </span>
          <svg class="teacher-account-btn__chevron" viewBox="0 0 20 20" aria-hidden="true">
            <path d="m5 7.5 5 5 5-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </button>
      </div>

      <!-- 项目 / 训练营：极简双列，只留名字 -->
      <section v-if="contextOpen" class="teacher-popover teacher-popover--workspace" @click.stop>
        <div class="ctx-simple">
          <div class="ctx-simple__col">
            <div class="ctx-simple__label">项目</div>
            <button
              v-for="p in ctx.projects"
              :key="p.id"
              type="button"
              class="ctx-simple__item"
              :class="{ 'is-active': String(p.id) === String(ctx.projectId) }"
              @click="selectProject(p.id)"
            >
              {{ p.name }}
            </button>
            <p v-if="!ctx.projects.length" class="ctx-simple__empty">暂无项目</p>
          </div>
          <div class="ctx-simple__col">
            <div class="ctx-simple__label">训练营</div>
            <button
              v-for="c in ctx.camps"
              :key="c.id"
              type="button"
              class="ctx-simple__item"
              :class="{ 'is-active': String(c.id) === String(ctx.campId) }"
              @click="selectCamp(c.id)"
            >
              {{ c.name }}
            </button>
            <p v-if="ctx.hasProjects && !ctx.camps.length" class="ctx-simple__empty">
              暂无训练营
              <router-link to="/camp/create" @click="contextOpen = false">创建</router-link>
            </p>
            <p v-else-if="!ctx.hasProjects" class="ctx-simple__empty">先选项目</p>
          </div>
        </div>
      </section>

      <!-- 消息（真实接口未接时仅提示，不造未读数） -->
      <section v-if="notifOpen" class="teacher-popover teacher-popover--notif" @click.stop>
        <div class="teacher-popover__head">
          <strong>消息通知</strong>
        </div>
        <div class="teacher-empty-panel">
          <p>消息中心将接入教师提醒接口。当前可从「提交与批改」发送催交提醒。</p>
          <router-link class="teacher-btn teacher-btn--secondary teacher-btn--sm" to="/camp/review-queue" @click="notifOpen = false">
            打开提交与批改
          </router-link>
        </div>
      </section>

      <!-- 账户 -->
      <section v-if="accountOpen" class="teacher-popover teacher-popover--account" @click.stop>
        <div class="teacher-account-summary">
          <b>{{ avatarChar }}</b>
          <span>
            <strong>{{ userName }}</strong>
            <small>{{ roleText }} · 教师端</small>
          </span>
        </div>
        <div class="teacher-account-actions">
          <button type="button" @click="accountOpen = false">账号信息</button>
          <button type="button" class="is-danger" @click="logout">退出登录</button>
        </div>
      </section>
    </header>

    <main
      class="teacher-main"
      :class="{
        'is-workbench': route.path === '/',
        'is-assistant': isAssistantRoute,
      }"
    >
      <!-- 小启：稳定 key，避免切会话整页重挂载丢流式状态（与学生端一致） -->
      <router-view :key="assistantViewKey" />
    </main>

  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  TEACHER_NAV,
  childPathActive,
  resolveModuleKey,
  toLocation,
} from '../config/nav'
import { useTeacherContextStore } from '../stores/context'
import { clearAuth, getToken, getUser } from '../utils/auth'
import { userRoleLabel } from '../utils/labels'
import { fetchMyTeams, fetchTeacherCamps } from '../api'
import { campStatusLabel } from '../utils/labels'
import TeacherModuleIcon from './TeacherModuleIcon.vue'

const route = useRoute()
const router = useRouter()
const ctx = useTeacherContextStore()

const openNav = ref('')
const contextOpen = ref(false)
const accountOpen = ref(false)
const notifOpen = ref(false)

const moduleKey = computed(() => resolveModuleKey(route.path))
const isAssistantRoute = computed(
  () => route.path === '/assistant' || route.path.startsWith('/assistant/')
)
/** 小启会话切换不重挂载整页 */
const assistantViewKey = computed(() => (isAssistantRoute.value ? 'assistant-workspace' : route.fullPath))
const hasToken = computed(() => Boolean(getToken()))
const userName = computed(() => getUser()?.username || getUser()?.name || (hasToken.value ? '已登录' : '未登录'))
const roleText = computed(() => {
  const raw = getUser()?.role
  if (raw) {
    const label = userRoleLabel(raw)
    // userRoleLabel 对未知枚举可能回退原文；避免展示纯英文枚举
    if (label && label !== '—' && !/^[A-Z_]+$/.test(String(label))) return label
  }
  return ctx.roleLabel || '教师'
})
const avatarChar = computed(() => String(userName.value || '师').slice(0, 1))

function isChildActive(child) {
  return childPathActive(child.path, route.path, child.query || null, route.query || {})
}

function toggleNav(key) {
  openNav.value = openNav.value === key ? '' : key
}

function closePopovers() {
  contextOpen.value = false
  accountOpen.value = false
  notifOpen.value = false
}

function toggleContext() {
  const next = !contextOpen.value
  closePopovers()
  contextOpen.value = next
}

function toggleAccount() {
  const next = !accountOpen.value
  closePopovers()
  accountOpen.value = next
}

function toggleNotif() {
  const next = !notifOpen.value
  closePopovers()
  notifOpen.value = next
}

function onShellClick() {
  closePopovers()
}

function selectProject(id) {
  ctx.setProject(id)
}

function selectCamp(id) {
  ctx.setCamp(id)
  contextOpen.value = false
}

function logout() {
  clearAuth()
  accountOpen.value = false
  router.push('/login')
}

watch(
  () => route.fullPath,
  () => {
    const key = moduleKey.value
    // 带二级菜单的模块自动展开；首页 / 小启 不占用手风琴
    if (key !== 'workbench' && key !== 'assistant') openNav.value = key
  },
  { immediate: true }
)

onMounted(async () => {
  if (!hasToken.value) return
  try {
    const [teams, campRows] = await Promise.all([fetchMyTeams(), fetchTeacherCamps()])
    const teamRows = (teams || []).map((team) => ({
      ...team,
      projectId: team.id,
      id: team.id,
      name: team.projectName || team.name || team.teamName || `项目 ${team.id}`,
    }))
    const projects = teamRows.map((team) => ({
      id: team.id,
      name: team.name,
      members: Number(
        team.memberCount
          ?? team.studentMemberCount
          ?? team.totalMemberCount
          ?? team.members?.length
          ?? team.memberIds?.length
          ?? 0
      ) || 0,
      status: team.status || team.phase || team.currentStage || 'active',
      projectName: team.projectName || team.name,
      track: team.trackName || team.track || '',
      lead: team.mentorNames || team.mentorName || team.captainName || team.lead || '',
      leads: String(team.mentorNames || team.mentorName || '')
        .split(/[、,，;；|/]/)
        .map((n) => n.trim())
        .filter(Boolean),
    }))
    const camps = (campRows || []).map((camp) => ({
      ...camp,
      id: camp.campId,
      projectId: camp.teamId,
      name: camp.campName,
      meta: [campStatusLabel(camp.status), camp.startDate && camp.endDate ? `${String(camp.startDate).slice(0, 10)} — ${String(camp.endDate).slice(0, 10)}` : '']
        .filter(Boolean)
        .join(' · '),
      plan: camp.subtitle || (camp.totalDays ? `${camp.totalDays} 天` : '训练营'),
    }))
    ctx.setOptions({ projects, camps, teams: teamRows })
    const preferredCamp =
      camps.find((c) => String(c.projectId) === String(ctx.projectId)) ||
      camps[0]
    if (preferredCamp) {
      if (preferredCamp.projectId) ctx.setProject(String(preferredCamp.projectId))
      ctx.setCamp(String(preferredCamp.id))
    }
  } catch (err) {
    ctx.setOptions({ projects: [], camps: [], teams: [] })
    ctx.setLoadError(err?.response?.data?.message || err?.message || '项目/训练营加载失败')
  }
})
</script>
