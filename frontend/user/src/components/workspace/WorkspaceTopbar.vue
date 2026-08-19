<template>
  <!-- 仅移动端使用：桌面能力已迁入左侧轨 -->
  <header ref="rootRef" class="workspace-topbar">
    <div class="workspace-topbar__actions">
      <button class="workspace-icon-btn" type="button" aria-label="消息提醒" @click="togglePanel('messages')">
        <Bell />
        <span v-if="unreadCount" class="workspace-message-badge">{{ unreadCount > 99 ? '99+' : unreadCount }}</span>
      </button>
      <button class="workspace-icon-btn" type="button" aria-label="帮助" @click="togglePanel('help')">
        <QuestionFilled />
      </button>
      <button class="workspace-account-trigger" type="button" @click="togglePanel('account')">
        <span>{{ userInitial }}</span>
        <strong>{{ username }}</strong>
        <ArrowDown :class="{ 'is-open': activePanel === 'account' }" />
      </button>
    </div>

    <section v-if="activePanel === 'messages'" class="workspace-popover workspace-message-panel" role="dialog" aria-label="消息提醒">
      <div class="workspace-popover__head workspace-message-panel__head">
        <span>
          <strong>消息通知</strong>
          <small>{{ unreadCount ? `${unreadCount} 条未读` : '没有未读消息' }}</small>
        </span>
        <button v-if="unreadCount" type="button" @click="markAllNotificationsRead">全部已读</button>
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
    </section>

    <section v-if="activePanel === 'help'" class="workspace-popover workspace-help-panel" role="dialog" aria-label="帮助">
      <div class="workspace-popover__head">
        <strong>快捷入口</strong>
        <small>从备赛主路径开始</small>
      </div>
      <button type="button" @click="go('/training/today')"><Reading /><span><strong>查看训练任务</strong><small>查看全周期任务和当前进度</small></span></button>
      <button type="button" @click="go('/online-meeting')"><VideoCamera /><span><strong>路演训练</strong><small>发起路演、回看并获取评分</small></span></button>
      <button type="button" @click="go('/statistics')"><DataAnalysis /><span><strong>查看评分反馈</strong><small>找到最需要改进的地方</small></span></button>
    </section>

    <section v-if="activePanel === 'account'" class="workspace-popover workspace-account-menu" role="menu" aria-label="账户菜单">
      <div class="workspace-account-menu__profile">
        <span>{{ userInitial }}</span>
        <div><strong>{{ username }}</strong><small>{{ roleLabel }} · 用户端</small></div>
      </div>
      <button type="button" role="menuitem" @click="go('/profile')">
        <User />
        <span><strong>个人中心</strong><small>查看学习投入和成长记录</small></span>
      </button>
      <button type="button" role="menuitem" @click="openPasswordDialog">
        <Lock />
        <span><strong>修改密码</strong><small>更新当前登录密码</small></span>
      </button>
      <div class="workspace-account-menu__divider"></div>
      <button class="is-danger" type="button" role="menuitem" @click="handleLogout">
        <SwitchButton />
        <span><strong>退出登录</strong><small>退出当前用户端账号</small></span>
      </button>
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
  </header>
</template>

<script setup>
import { ref } from 'vue'
import {
  ArrowDown,
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
import { useWorkspaceChrome } from '../../composables/useWorkspaceChrome'

const rootRef = ref(null)
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
} = useWorkspaceChrome({ rootRef })
</script>

<style scoped>
.workspace-topbar {
  position: sticky;
  top: 0;
  left: 0;
  right: 0;
  width: 100%;
  height: 52px;
  min-height: 52px;
  padding: 0 12px;
  padding-top: env(safe-area-inset-top, 0px);
  box-sizing: content-box;
  border-bottom: 1px solid var(--ds-line, #e5e5e5);
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  background: rgba(247, 247, 248, 0.96);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  z-index: 320;
}

.workspace-topbar__actions {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-left: auto;
}

.workspace-icon-btn {
  position: relative;
  width: 42px;
  height: 42px;
  border: 0;
  border-radius: 999px;
  display: grid;
  place-items: center;
  color: var(--ds-muted, #737373);
  background: transparent;
  cursor: pointer;
}

.workspace-message-badge {
  position: absolute;
  top: 2px;
  right: 1px;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  border: 2px solid #fff;
  border-radius: 999px;
  display: grid;
  place-items: center;
  color: #fff;
  background: var(--ds-orange);
  font-size: 9px;
  font-weight: 800;
}

.workspace-icon-btn:hover {
  background: var(--ds-soft, #f5f5f5);
  color: var(--ds-ink, #0a0a0a);
}

.workspace-icon-btn svg {
  width: 18px;
}

.workspace-account-trigger {
  height: 40px;
  margin-left: 2px;
  border: 1px solid var(--ds-line);
  border-radius: 999px;
  padding: 0 8px 0 4px;
  display: flex;
  align-items: center;
  gap: 6px;
  color: var(--ds-ink);
  background: var(--ds-surface-solid);
  cursor: pointer;
}

.workspace-account-trigger > span {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: #fff;
  background: var(--ds-orange);
  font-size: 13px;
  font-weight: 700;
}

.workspace-account-trigger strong {
  max-width: 72px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12px;
}

.workspace-account-trigger > svg {
  width: 13px;
  color: var(--ds-faint);
  transition: transform 160ms ease;
}

.workspace-account-trigger > svg.is-open {
  transform: rotate(180deg);
}

.workspace-popover {
  position: absolute;
  top: calc(100% + 8px);
  right: 10px;
  left: 10px;
  width: auto;
  max-width: none;
  max-height: min(70dvh, 480px);
  overflow-y: auto;
  border: 1px solid var(--ds-line);
  border-radius: 16px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 16px 40px rgba(29, 29, 31, 0.14);
  z-index: 330;
}

.workspace-popover__head {
  padding: 4px 6px 10px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.workspace-popover__head strong {
  font-size: 13px;
}

.workspace-popover__head small {
  display: block;
  margin-top: 2px;
  color: var(--ds-muted);
  font-size: 11px;
}

.workspace-message-panel__head > button,
.workspace-message-retry {
  border: 0;
  border-radius: 999px;
  padding: 6px 10px;
  color: var(--ds-orange);
  background: rgba(232, 74, 28, 0.08);
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
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
}

.workspace-message-list {
  display: grid;
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
  width: 14px;
  margin-top: 4px;
  color: var(--ds-faint);
}

.workspace-help-panel > button,
.workspace-account-menu > button {
  width: 100%;
  min-height: 52px;
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

.workspace-help-panel > button:hover,
.workspace-account-menu > button:hover {
  background: #f7f7f8;
}

.workspace-help-panel > button > svg,
.workspace-account-menu > button > svg {
  width: 16px;
  height: 16px;
  flex: 0 0 16px;
  color: var(--ds-muted);
}

.workspace-help-panel span,
.workspace-account-menu span {
  min-width: 0;
  display: grid;
  gap: 2px;
}

.workspace-help-panel strong,
.workspace-account-menu strong {
  font-size: 12px;
}

.workspace-help-panel small,
.workspace-account-menu small {
  font-size: 11px;
  color: var(--ds-muted);
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

/* 桌面由 Shell v-if 隐藏；保险再藏一次 */
@media (min-width: 1024px) {
  .workspace-topbar {
    display: none !important;
  }
}
</style>
