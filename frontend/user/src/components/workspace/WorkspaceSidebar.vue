<template>
  <aside ref="rootRef" class="workspace-sidebar">
    <button class="workspace-brand" type="button" aria-label="返回首页" @click="router.push('/')">
      <img
        class="workspace-brand__mark"
        src="/brand/competition-brain-mark.svg?v=20260723"
        alt=""
        aria-hidden="true"
      />
      <span class="workspace-brand__text">
        <strong>竞赛大脑</strong>
        <small>AI Platform</small>
      </span>
    </button>

    <nav class="workspace-nav" aria-label="用户端主导航">
      <span class="workspace-nav__label">导航</span>
      <template v-for="item in navItems" :key="item.path">
        <!-- 待办中心：放在「我的」下方，点击打开待办面板 -->
        <button
          v-if="item.action === 'collaboration'"
          type="button"
          class="workspace-nav__item"
          :class="{ 'is-active': isCollaborationNavActive }"
          :aria-label="collaborationNavLabel"
          :aria-pressed="collaboration.isOpen"
          @click="openCollaboration"
          @pointerenter="showRailTip($event, '待办中心')"
          @pointerleave="hideRailTip"
          @focus="showRailTip($event, '待办中心')"
          @blur="hideRailTip"
        >
          <span class="workspace-nav__icon" aria-hidden="true">
            <WorkspaceModuleIcon
              name="collaboration"
              :variant="isCollaborationNavActive ? 'filled' : 'outline'"
            />
          </span>
          <span
            v-if="collaboration.actionCount"
            class="workspace-nav__badge"
            aria-hidden="true"
          >{{ collaboration.actionCount > 99 ? '99+' : collaboration.actionCount }}</span>
        </button>
        <router-link
          v-else
          :to="item.path"
          class="workspace-nav__item"
          :class="{
            'is-active': isOrepRouteActive(route, item.path),
            'is-xiaoqi-nav': item.group === 'assistant',
          }"
          :aria-label="item.label"
          :aria-current="isOrepRouteActive(route, item.path) ? 'page' : undefined"
          @pointerenter="showRailTip($event, item.label)"
          @pointerleave="hideRailTip"
          @focus="showRailTip($event, item.label)"
          @blur="hideRailTip"
        >
          <span class="workspace-nav__icon" aria-hidden="true">
            <WorkspaceModuleIcon
              :name="item.group"
              :variant="isOrepRouteActive(route, item.path) ? 'filled' : 'outline'"
            />
          </span>
        </router-link>
      </template>
    </nav>

    <div class="workspace-sidebar__footer">
      <!-- 唯一账户入口：消息 / 帮助 / 个人中心 / 待办 / 退出 都收进头像菜单 -->
      <button
        class="workspace-sidebar__avatar"
        type="button"
        :aria-label="avatarAriaLabel"
        :aria-pressed="activePanel === 'account'"
        :class="{ 'is-open': activePanel === 'account' }"
        @click="openAccountMenu"
        @pointerenter="showRailTip($event, username)"
        @pointerleave="hideRailTip"
        @focus="showRailTip($event, username)"
        @blur="hideRailTip"
      >
        <span class="workspace-sidebar__avatar-letter">{{ userInitial }}</span>
        <span
          v-if="unreadCount"
          class="workspace-sidebar__avatar-badge"
          aria-hidden="true"
        >{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
      </button>
    </div>

    <!-- Teleport 到 body，避开 app-container overflow:hidden 裁切 -->
    <Teleport to="body">
      <div
        v-show="railTip.visible"
        class="workspace-rail-tip"
        role="tooltip"
        :style="{ left: `${railTip.x}px`, top: `${railTip.y}px` }"
      >
        {{ railTip.text }}
      </div>
    </Teleport>

    <!-- 统一账户浮层：主菜单 / 消息 / 帮助 三级同容器 -->
    <section
      v-if="activePanel === 'account'"
      class="workspace-rail-popover workspace-account-menu"
      role="dialog"
      :aria-label="accountViewTitle"
    >
      <!-- 主菜单 -->
      <template v-if="accountView === 'root'">
        <div class="workspace-account-menu__profile">
          <span>{{ userInitial }}</span>
          <div>
            <strong>{{ username }}</strong>
            <small>{{ roleLabel }} · 用户端</small>
          </div>
        </div>
        <button type="button" role="menuitem" @click="openAccountView('messages')">
          <Bell />
          <span>
            <strong>消息通知</strong>
            <small>{{ unreadCount ? `${unreadCount} 条未读` : '查看老师提醒' }}</small>
          </span>
          <em v-if="unreadCount" class="workspace-account-menu__count">{{ unreadCount > 99 ? '99+' : unreadCount }}</em>
          <ArrowRight class="workspace-account-menu__chevron" />
        </button>
        <button type="button" role="menuitem" @click="openAccountView('help')">
          <QuestionFilled />
          <span>
            <strong>帮助与快捷入口</strong>
            <small>训练、路演、评分</small>
          </span>
          <ArrowRight class="workspace-account-menu__chevron" />
        </button>
        <div class="workspace-account-menu__divider"></div>
        <button type="button" role="menuitem" @click="go('/profile')">
          <User />
          <span><strong>个人中心</strong><small>学习投入和成长记录</small></span>
        </button>
        <button type="button" role="menuitem" @click="openPasswordDialog">
          <Lock />
          <span><strong>修改密码</strong><small>更新登录密码</small></span>
        </button>
        <div class="workspace-account-menu__divider"></div>
        <button class="is-danger" type="button" role="menuitem" @click="handleLogout">
          <SwitchButton />
          <span><strong>退出登录</strong><small>退出当前账号</small></span>
        </button>
      </template>

      <!-- 消息列表 -->
      <template v-else-if="accountView === 'messages'">
        <div class="workspace-account-subhead">
          <button type="button" class="workspace-account-back" aria-label="返回账户菜单" @click="accountView = 'root'">
            <ArrowLeft />
          </button>
          <div class="workspace-account-subhead__title">
            <strong>消息通知</strong>
            <small>{{ unreadCount ? `${unreadCount} 条未读` : '没有未读消息' }}</small>
          </div>
          <button
            v-if="unreadCount"
            type="button"
            class="workspace-account-subhead__action"
            @click="markAllNotificationsRead"
          >全部已读</button>
        </div>
        <div v-if="messagesLoading && !notifications.length" class="workspace-empty-panel">
          <strong>正在加载消息…</strong>
        </div>
        <div v-else-if="messagesError && !notifications.length" class="workspace-empty-panel">
          <strong>消息暂时加载失败</strong>
          <p>{{ messagesError }}</p>
          <button class="workspace-message-retry" type="button" @click="refreshNotifications">重新加载</button>
        </div>
        <div v-else-if="notifications.length" class="workspace-message-list">
          <button
            v-for="item in notifications"
            :key="item.id"
            type="button"
            :class="{ 'is-unread': !item.isRead }"
            @click="openNotification(item)"
          >
            <span class="workspace-message-item__dot"></span>
            <span class="workspace-message-item__content">
              <strong>{{ item.title }}</strong>
              <p>{{ item.message }}<template v-if="item.deadline"> · {{ item.deadline }}</template></p>
              <small>{{ formatMessageTime(item.createdAt) }}</small>
            </span>
            <ArrowRight class="workspace-message-item__arrow" />
          </button>
        </div>
        <div v-else class="workspace-empty-panel">
          <Bell />
          <strong>暂无新消息</strong>
          <p>老师发送提醒后会在这里出现。</p>
        </div>
      </template>

      <!-- 帮助快捷入口 -->
      <template v-else-if="accountView === 'help'">
        <div class="workspace-account-subhead">
          <button type="button" class="workspace-account-back" aria-label="返回账户菜单" @click="accountView = 'root'">
            <ArrowLeft />
          </button>
          <div class="workspace-account-subhead__title">
            <strong>帮助与快捷入口</strong>
            <small>从备赛主路径开始</small>
          </div>
        </div>
        <button type="button" @click="go('/training/today')">
          <Reading />
          <span><strong>查看训练任务</strong><small>全周期任务和当前进度</small></span>
        </button>
        <button type="button" @click="go('/online-meeting')">
          <VideoCamera />
          <span><strong>路演训练</strong><small>发起路演、回看与评分</small></span>
        </button>
        <button type="button" @click="go('/statistics')">
          <DataAnalysis />
          <span><strong>查看评分反馈</strong><small>找到最需要改进的地方</small></span>
        </button>
      </template>
    </section>

    <el-dialog v-model="passwordDialog" title="修改密码" width="420px" align-center append-to-body>
      <div class="password-form">
        <label>
          <span>当前密码</span>
          <input v-model="passwordForm.oldPassword" type="password" autocomplete="current-password">
        </label>
        <label>
          <span>新密码</span>
          <input v-model="passwordForm.newPassword" type="password" autocomplete="new-password">
        </label>
        <label>
          <span>确认新密码</span>
          <input v-model="passwordForm.confirmPassword" type="password" autocomplete="new-password">
        </label>
      </div>
      <template #footer>
        <button class="student-secondary-btn" type="button" @click="passwordDialog = false">取消</button>
        <button class="student-primary-btn" type="button" :disabled="changingPassword" @click="changePassword">
          {{ changingPassword ? '正在保存…' : '保存新密码' }}
        </button>
      </template>
    </el-dialog>
  </aside>
</template>

<script setup>
import { computed, onBeforeUnmount, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowLeft,
  ArrowRight,
  Bell,
  DataAnalysis,
  Lock,
  QuestionFilled,
  Reading,
  SwitchButton,
  User,
  VideoCamera,
} from '@element-plus/icons-vue'
import { OREP_NAV_ITEMS, isOrepRouteActive } from '../../composables/apple/useOrepNavigation'
import { useWorkspaceChrome } from '../../composables/useWorkspaceChrome'
import { useCollaborationStore } from '../../stores/collaboration'
import WorkspaceModuleIcon from './WorkspaceModuleIcon.vue'

const route = useRoute()
const router = useRouter()
const collaboration = useCollaborationStore()
const rootRef = ref(null)

const chrome = useWorkspaceChrome({ rootRef })
const {
  activePanel,
  passwordDialog,
  changingPassword,
  notifications,
  unreadCount,
  messagesLoading,
  messagesError,
  passwordForm,
  username,
  userInitial,
  roleLabel,
  togglePanel,
  refreshNotifications,
  openNotification,
  markAllNotificationsRead,
  formatMessageTime,
  go,
  openPasswordDialog,
  changePassword,
  handleLogout,
} = chrome

const navItems = OREP_NAV_ITEMS
/** 账户浮层内视图：主菜单 / 消息 / 帮助 */
const accountView = ref('root')

const isCollaborationNavActive = computed(() =>
  collaboration.isOpen || isOrepRouteActive(route, '/project-team')
)

const collaborationNavLabel = computed(() => {
  const n = collaboration.actionCount
  return n > 0 ? `待办中心，${n} 项待处理` : '待办中心'
})

const avatarAriaLabel = computed(() => {
  const base = `账户：${username.value}`
  return unreadCount.value
    ? `${base}，${unreadCount.value} 条未读消息`
    : base
})

const accountViewTitle = computed(() => ({
  root: '账户菜单',
  messages: '消息通知',
  help: '帮助与快捷入口',
}[accountView.value] || '账户菜单'))

/** 侧栏气泡：fixed + Teleport，避免被 overflow:hidden 祖先裁掉 */
const railTip = reactive({
  visible: false,
  text: '',
  x: 0,
  y: 0,
})
let tipHideTimer = 0

function showRailTip(event, text) {
  if (tipHideTimer) {
    window.clearTimeout(tipHideTimer)
    tipHideTimer = 0
  }
  const el = event?.currentTarget
  if (!el || !text) return
  const rect = el.getBoundingClientRect()
  railTip.text = String(text)
  railTip.x = Math.round(rect.right + 10)
  railTip.y = Math.round(rect.top + rect.height / 2)
  railTip.visible = true
}

function hideRailTip() {
  if (tipHideTimer) window.clearTimeout(tipHideTimer)
  tipHideTimer = window.setTimeout(() => {
    railTip.visible = false
    tipHideTimer = 0
  }, 40)
}

function openAccountMenu() {
  hideRailTip()
  if (activePanel.value === 'account') {
    togglePanel('account')
    accountView.value = 'root'
    return
  }
  accountView.value = 'root'
  togglePanel('account')
}

async function openAccountView(view) {
  accountView.value = view
  if (view === 'messages') await refreshNotifications()
}

function openCollaboration() {
  hideRailTip()
  if (activePanel.value === 'account') togglePanel('account')
  if (collaboration.isFeatureEnabled) {
    collaboration.toggle()
    return
  }
  router.push('/project-team')
}

watch(
  () => activePanel.value,
  (panel) => {
    hideRailTip()
    if (panel !== 'account') accountView.value = 'root'
  }
)

watch(
  () => route.fullPath,
  () => hideRailTip()
)

onBeforeUnmount(() => {
  if (tipHideTimer) window.clearTimeout(tipHideTimer)
  railTip.visible = false
})
</script>

<style scoped>
.workspace-sidebar {
  --rail-hit: var(--ds-sidebar-hit, 40px);
  --rail-icon: var(--ds-sidebar-icon, 20px);
  --rail-logo: var(--ds-sidebar-logo, 28px);
  position: relative;
  grid-column: 1;
  grid-row: 1 / -1;
  height: 100vh;
  min-height: 100vh;
  width: var(--workspace-sidebar-width, 56px);
  padding: 0 6px;
  display: flex;
  flex-direction: column;
  align-items: center;
  /* 必须 visible，否则气泡被裁切 */
  overflow: visible;
  background: var(--ds-sidebar-bg, #f3f3f4);
  border-right: 1px solid var(--ds-line, #e4e4e7);
  /* 高于主内容区，气泡可浮在页面内容之上 */
  z-index: 200;
  box-sizing: border-box;
}

.workspace-brand {
  flex: 0 0 auto;
  width: 100%;
  height: 52px;
  border: 0;
  background: transparent;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  cursor: pointer;
}

.workspace-brand:focus-visible {
  outline: 2px solid var(--ds-orange);
  outline-offset: 2px;
}

.workspace-brand__mark {
  width: var(--rail-logo);
  height: var(--rail-logo);
  display: block;
  object-fit: contain;
}

.workspace-brand__text {
  display: none;
}

.workspace-nav {
  flex: 1;
  min-height: 0;
  width: 100%;
  padding: 8px 0 10px;
  display: flex;
  flex-direction: column;
  align-items: center;
  /* 图标间距略拉开且全列统一，避免疏密不一 */
  gap: 8px;
  /*
   * 注意：overflow-y:auto 会把 overflow-x 也变成 auto，气泡横向伸出即被裁掉。
   * 导航项不多，保持 visible；超矮屏靠侧栏整体不滚动（项足够紧凑）。
   */
  overflow: visible;
}

.workspace-nav__label {
  display: none;
}

.workspace-nav__item {
  position: relative;
  flex: 0 0 var(--rail-hit);
  width: var(--rail-hit);
  height: var(--rail-hit);
  border-radius: 10px;
  padding: 0;
  display: grid;
  place-items: center;
  color: var(--ds-muted, #71717a);
  background: transparent;
  border: 1px solid transparent;
  text-decoration: none;
  font: inherit;
  cursor: pointer;
  transition:
    background-color var(--workspace-transition, 0.15s ease),
    color var(--workspace-transition, 0.15s ease),
    border-color var(--workspace-transition, 0.15s ease);
}

.workspace-nav__badge {
  position: absolute;
  top: 4px;
  right: 4px;
  min-width: 14px;
  height: 14px;
  padding: 0 3px;
  border: 2px solid var(--ds-sidebar-bg, #f3f3f4);
  border-radius: 999px;
  display: grid;
  place-items: center;
  color: #fff;
  background: #ef4444;
  font-size: 9px;
  font-weight: 800;
  line-height: 1;
  box-sizing: border-box;
}

.workspace-nav__item:hover {
  color: var(--ds-ink, #0a0a0a);
  background: #ebebec;
}

.workspace-nav__item.is-active {
  color: var(--ds-ink, #0a0a0a);
  background: #ffffff;
  border-color: #e4e4e7;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
}

.workspace-nav__item:focus-visible {
  outline: 2px solid oklch(64% 0.2 38);
  outline-offset: 2px;
}

.workspace-nav__icon {
  width: var(--rail-icon);
  height: var(--rail-icon);
  display: grid;
  place-items: center;
  color: currentColor;
  line-height: 0;
}

.workspace-nav__icon svg {
  width: var(--rail-icon);
  height: var(--rail-icon);
  display: block;
}

.workspace-nav__item.is-xiaoqi-nav {
  background: transparent !important;
  box-shadow: none !important;
  border-color: transparent !important;
}

.workspace-nav__item.is-xiaoqi-nav:hover,
.workspace-nav__item.is-xiaoqi-nav.is-active {
  background: #ebebec !important;
  box-shadow: none !important;
}

.workspace-nav__item.is-xiaoqi-nav .workspace-nav__icon {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  overflow: visible;
}

.workspace-nav__icon :deep(.xiaoqi-mark) {
  width: 26px !important;
  height: 26px !important;
  border: 0;
  background: transparent;
  box-shadow: none;
  transform: none; /* 去掉光学上移，保证槽内居中 */
}

.workspace-nav__icon :deep(.xiaoqi-mark__img) {
  object-position: center center;
  filter: drop-shadow(0 1px 2px rgba(100, 55, 10, 0.18));
}

.workspace-nav__icon :deep(.xiaoqi-mark svg) {
  width: 26px;
  height: 26px;
  display: block;
}

.workspace-sidebar__footer {
  flex: 0 0 auto;
  width: 100%;
  margin-top: auto;
  padding: 8px 0 12px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  border-top: 1px solid var(--ds-line, #e4e4e7);
  overflow: visible;
}

.workspace-sidebar__avatar {
  position: relative;
  flex: 0 0 auto;
  width: 32px;
  height: 32px;
  margin: 4px 0 0;
  padding: 0;
  border: 2px solid #fff;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: #fff;
  background: var(--ds-orange, #e84a1c);
  box-shadow: 0 0 0 1px rgba(0, 0, 0, 0.06);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  line-height: 1;
}

.workspace-sidebar__avatar-letter {
  display: grid;
  place-items: center;
  width: 100%;
  height: 100%;
}

.workspace-sidebar__avatar-badge {
  position: absolute;
  top: -4px;
  right: -5px;
  min-width: 15px;
  height: 15px;
  padding: 0 3px;
  border: 2px solid var(--ds-sidebar-bg, #f3f3f4);
  border-radius: 999px;
  display: grid;
  place-items: center;
  color: #fff;
  background: #ef4444;
  font-size: 9px;
  font-weight: 800;
  line-height: 1;
  box-sizing: border-box;
}

.workspace-sidebar__avatar.is-open,
.workspace-sidebar__avatar:hover {
  box-shadow: 0 0 0 2px rgba(232, 74, 28, 0.28);
}

.workspace-sidebar__avatar:focus-visible {
  outline: 2px solid oklch(64% 0.2 38);
  outline-offset: 2px;
}

/* —— 侧栏浮层（搜索/消息/帮助/账户） —— */
.workspace-rail-popover {
  position: absolute;
  left: calc(100% + 8px);
  z-index: 400;
  border: 1px solid var(--ds-line);
  border-radius: 16px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 16px 40px rgba(29, 29, 31, 0.14);
  backdrop-filter: blur(20px);
  box-sizing: border-box;
}

.workspace-message-panel,
.workspace-help-panel,
.workspace-account-menu {
  bottom: 12px;
  width: min(300px, calc(100vw - 72px));
}

/* 二级页头：返回 | 标题 | 操作 — 三列对齐，避免返回钮被套成胶囊 */
.workspace-account-subhead {
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr) auto;
  align-items: center;
  gap: 8px;
  padding: 2px 2px 12px;
  margin-bottom: 4px;
  border-bottom: 1px solid var(--ds-line);
}

.workspace-account-subhead__title {
  min-width: 0;
  display: grid;
  gap: 2px;
}

.workspace-account-subhead__title strong {
  display: block;
  font-size: 13px;
  font-weight: 750;
  color: var(--ds-ink);
  line-height: 1.25;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workspace-account-subhead__title small {
  display: block;
  color: var(--ds-muted);
  font-size: 11px;
  line-height: 1.3;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.workspace-account-subhead__action,
.workspace-message-retry {
  flex: 0 0 auto;
  border: 0;
  border-radius: 999px;
  padding: 6px 10px;
  color: var(--ds-orange);
  background: rgba(232, 74, 28, 0.08);
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  white-space: nowrap;
}

.workspace-account-subhead__action:hover,
.workspace-message-retry:hover {
  background: rgba(232, 74, 28, 0.14);
}

.workspace-empty-panel {
  padding: 24px 12px;
  color: #8e8e93;
  text-align: center;
  font-size: 12px;
}

.workspace-empty-panel svg {
  width: 22px;
  margin-bottom: 10px;
}

.workspace-empty-panel strong {
  display: block;
  color: var(--ds-ink);
  font-size: 13px;
}

.workspace-empty-panel p {
  margin: 6px 0 0;
  font-size: 12px;
  line-height: 1.4;
}

.workspace-message-list {
  display: grid;
  max-height: min(50vh, 340px);
  overflow: auto;
}

.workspace-message-list > button {
  width: 100%;
  border: 0;
  border-radius: 10px;
  padding: 10px 8px;
  display: flex;
  align-items: flex-start;
  gap: 8px;
  text-align: left;
  background: transparent;
  cursor: pointer;
  font: inherit;
}

.workspace-message-list > button:hover {
  background: #f7f7f8;
}

.workspace-message-list > button.is-unread {
  background: rgba(232, 74, 28, 0.04);
}

.workspace-message-item__dot {
  flex: 0 0 8px;
  width: 8px;
  height: 8px;
  margin-top: 6px;
  border-radius: 50%;
  background: transparent;
}

.workspace-message-list > button.is-unread .workspace-message-item__dot {
  background: var(--ds-orange);
}

.workspace-message-item__content {
  flex: 1;
  min-width: 0;
}

.workspace-message-item__content strong {
  display: block;
  font-size: 12px;
  color: var(--ds-ink);
}

.workspace-message-item__content p {
  margin: 3px 0 0;
  color: var(--ds-muted);
  font-size: 11px;
  line-height: 1.4;
}

.workspace-message-item__content small {
  display: block;
  margin-top: 4px;
  color: var(--ds-faint);
  font-size: 10px;
}

.workspace-message-item__arrow {
  flex: 0 0 14px;
  width: 14px;
  margin-top: 4px;
  color: var(--ds-faint);
}

.workspace-account-menu > button {
  width: 100%;
  min-height: 48px;
  border: 0;
  border-radius: 10px;
  padding: 8px 10px;
  display: flex;
  align-items: center;
  gap: 10px;
  text-align: left;
  background: transparent;
  cursor: pointer;
  font: inherit;
  color: inherit;
}

.workspace-account-menu > button:hover {
  background: #f7f7f8;
}

.workspace-account-menu > button > svg {
  width: 16px;
  height: 16px;
  flex: 0 0 16px;
  color: var(--ds-muted);
}

.workspace-account-menu > button > span {
  min-width: 0;
  flex: 1 1 auto;
  display: grid;
  gap: 2px;
}

.workspace-account-menu strong {
  font-size: 12px;
  color: var(--ds-ink);
}

.workspace-account-menu small {
  font-size: 11px;
  color: var(--ds-muted);
}

.workspace-account-menu__chevron {
  width: 14px !important;
  height: 14px !important;
  flex: 0 0 14px !important;
  color: var(--ds-faint) !important;
}

.workspace-account-menu__count {
  flex: 0 0 auto;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 999px;
  display: inline-grid;
  place-items: center;
  color: #fff;
  background: #ef4444;
  font-size: 10px;
  font-style: normal;
  font-weight: 800;
  line-height: 1;
}

.workspace-account-back {
  appearance: none;
  box-sizing: border-box;
  width: 32px !important;
  min-width: 32px !important;
  max-width: 32px !important;
  height: 32px !important;
  min-height: 32px !important;
  margin: 0;
  padding: 0 !important;
  border: 0;
  border-radius: 10px;
  display: inline-grid !important;
  place-items: center;
  flex: 0 0 32px !important;
  background: transparent;
  color: var(--ds-muted);
  cursor: pointer;
}

.workspace-account-back:hover {
  background: #f3f4f6 !important;
  color: var(--ds-ink);
}

.workspace-account-back > svg {
  width: 16px !important;
  height: 16px !important;
  flex: 0 0 16px !important;
  color: inherit !important;
}

.workspace-account-menu__profile {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 8px 12px;
  border-bottom: 1px solid var(--ds-line);
  margin-bottom: 6px;
}

.workspace-account-menu__profile > span {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: #fff;
  background: var(--ds-orange);
  font-size: 14px;
  font-weight: 700;
}

.workspace-account-menu__profile strong {
  display: block;
  font-size: 13px;
}

.workspace-account-menu__profile small {
  display: block;
  margin-top: 2px;
  color: var(--ds-muted);
  font-size: 11px;
}

.workspace-account-menu__divider {
  height: 1px;
  margin: 6px 0;
  background: var(--ds-line);
}

.workspace-account-menu > button.is-danger strong {
  color: #c2410c;
}

.password-form {
  display: grid;
  gap: 12px;
}

.password-form label {
  display: grid;
  gap: 6px;
  font-size: 12px;
  color: var(--ds-muted);
}

.password-form input {
  height: 40px;
  border: 1px solid var(--ds-line);
  border-radius: 10px;
  padding: 0 12px;
  font: inherit;
  font-size: 13px;
}

@media (prefers-reduced-motion: reduce) {
  .workspace-nav__item {
    transition-duration: 0.01ms;
  }
}
</style>

<!-- Teleport 气泡：非 scoped，挂 body 全局一层 -->
<style>
.workspace-rail-tip {
  position: fixed;
  z-index: 10050;
  min-height: 30px;
  padding: 0 11px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  color: #fafafa;
  background: #292b31;
  box-shadow: 0 8px 20px rgba(18, 20, 26, 0.18);
  font-size: 12px;
  font-weight: 650;
  line-height: 1;
  white-space: nowrap;
  pointer-events: none;
  transform: translateY(-50%);
}

.workspace-rail-tip::before {
  content: "";
  position: absolute;
  top: 50%;
  left: -3px;
  width: 6px;
  height: 6px;
  background: inherit;
  transform: translateY(-50%) rotate(45deg);
}


@media (max-height: 700px) and (min-width: 1024px) {
  .workspace-brand {
    height: 44px;
  }

  .workspace-nav {
    gap: 6px;
    padding: 4px 0;
  }

  .workspace-sidebar__footer {
    padding-bottom: 8px;
  }
}

@media (max-width: 1023px) {
  .workspace-sidebar {
    display: none;
  }
}
</style>
