<template>
  <Transition name="collaboration-hub">
    <section
      v-if="store.isOpen"
      ref="panelRef"
      class="collaboration-hub"
      role="dialog"
      aria-modal="false"
      aria-labelledby="collaboration-hub-title"
      tabindex="-1"
      @keydown.esc="store.close"
    >
      <header class="collaboration-hub__header">
        <button
          v-if="currentView"
          class="collaboration-hub__icon-button"
          type="button"
          aria-label="返回列表"
          @click="store.back"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m15 6-6 6 6 6" /></svg>
        </button>
        <CollaborationBrandMark v-else />
        <div class="collaboration-hub__title">
          <Transition :name="viewTransitionName" mode="out-in">
            <div :key="headerContentKey">
              <h2 id="collaboration-hub-title">{{ currentView ? viewTitle : '待办中心' }}</h2>
              <p>{{ currentView ? '处理完可返回继续清红点' : '今天要做的事都在这里，清完红点再收工' }}</p>
            </div>
          </Transition>
        </div>
        <button
          class="collaboration-hub__icon-button"
          type="button"
          aria-label="关闭待办中心"
          @click="store.close"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m6 6 12 12M18 6 6 18" /></svg>
        </button>
      </header>

      <Transition name="collaboration-chrome">
        <div v-if="!currentView" class="collaboration-hub__toolbar">
          <div class="collaboration-hub__tabs" role="tablist" aria-label="待办范围">
            <button
              v-for="tab in tabs"
              :key="tab.value"
              type="button"
              role="tab"
              :aria-selected="store.activeTab === tab.value"
              :class="{ 'is-active': store.activeTab === tab.value }"
              @click="store.setActiveTab(tab.value)"
            >
              {{ tab.label }}
              <span v-if="tabBadge(tab) > 0">{{ tabBadge(tab) }}</span>
            </button>
          </div>
          <button class="collaboration-hub__create" type="button" @click="store.showRequestForm">
            <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14" /></svg>
            发起
          </button>
        </div>
      </Transition>

      <div class="collaboration-hub__body">
        <Transition :name="viewTransitionName" mode="out-in">
          <div :key="bodyContentKey" class="collaboration-hub__body-content">
            <CollaborationRequestForm v-if="currentView?.type === 'request-form'" />
            <CollaborationDetail
              v-else-if="currentView?.type === 'detail'"
              :item="currentView.item"
            />
            <template v-else-if="store.activeTab === 'TODAY'">
              <div v-if="todayLoading" class="collaboration-hub__loading" aria-live="polite">
                <span v-for="index in 3" :key="index"></span>
              </div>
              <div v-else-if="todayError" class="collaboration-hub__error" role="alert">
                <strong>今日待办暂时无法加载</strong>
                <p>{{ todayError }}</p>
                <button type="button" @click="reloadToday">重新加载</button>
              </div>
              <div v-else class="today-todo">
                <button
                  type="button"
                  class="today-todo__card"
                  :class="{ 'is-done': dailySubmitted }"
                  @click="openDaily"
                >
                  <span class="today-todo__badge" :class="dailySubmitted ? 'is-ok' : 'is-todo'">
                    {{ dailySubmitted ? '已交' : '待交' }}
                  </span>
                  <span class="today-todo__copy">
                    <strong>今日日报</strong>
                    <small>{{ dailySubmitted ? '已提交，可查看或修改' : '富文本 + 图片 · 约 3 分钟' }}</small>
                  </span>
                  <span class="today-todo__action">{{ dailySubmitted ? '查看' : '去填写' }}</span>
                </button>

                <button
                  v-if="hasTrainingDay"
                  type="button"
                  class="today-todo__card"
                  :class="{ 'is-done': trainingDone }"
                  @click="openTraining"
                >
                  <span class="today-todo__badge" :class="trainingDone ? 'is-ok' : 'is-todo'">
                    {{ trainingDone ? '已交' : '待交' }}
                  </span>
                  <span class="today-todo__copy">
                    <strong>今日训练</strong>
                    <small>{{ trainingTitle }}</small>
                  </span>
                  <span class="today-todo__action">{{ trainingDone ? '查看' : '去完成' }}</span>
                </button>

                <button type="button" class="today-todo__link" @click="openDailyCenter">
                  打开日报中心 · 历史与统计 →
                </button>

                <p v-if="!hasTrainingDay" class="today-todo__hint">
                  当前没有训练日任务；日报仍建议每天提交。
                </p>
              </div>
            </template>
            <template v-else>
              <div v-if="currentLoading" class="collaboration-hub__loading" aria-live="polite">
                <span v-for="index in 3" :key="index"></span>
              </div>
              <div v-else-if="currentError" class="collaboration-hub__error" role="alert">
                <strong>任务暂时无法加载</strong>
                <p>{{ currentError }}</p>
                <button type="button" @click="reload">重新加载</button>
              </div>
              <CollaborationEmptyState
                v-else-if="currentItems.length === 0"
                :title="emptyTitle"
                :description="emptyDescription"
              />
              <div v-else class="collaboration-hub__list">
                <CollaborationItemRow
                  v-for="(item, index) in currentItems"
                  :key="item.key || `${item.entityType || 'REQUEST'}:${item.id}`"
                  class="collaboration-hub__list-item"
                  :style="{ '--collaboration-item-index': Math.min(index, 7) }"
                  :item="item"
                  @open="openItem"
                  @accept="acceptItem"
                  @decline="declineItem"
                  @withdraw="withdrawItem"
                />
              </div>
            </template>
          </div>
        </Transition>
      </div>

      <Transition name="collaboration-chrome">
        <footer v-if="!currentView" class="collaboration-hub__footer">
          <span v-if="store.lastRefreshedAt">已同步最新待办</span>
          <div class="collaboration-hub__footer-actions">
            <button type="button" @click="openDailyCenter">日报中心</button>
            <button type="button" @click="openFullWorkspace">完整任务台</button>
          </div>
        </footer>
      </Transition>
    </section>
  </Transition>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useCollaborationStore } from '../../stores/collaboration'
import CollaborationBrandMark from './CollaborationBrandMark.vue'
import CollaborationDetail from './CollaborationDetail.vue'
import CollaborationEmptyState from './CollaborationEmptyState.vue'
import CollaborationItemRow from './CollaborationItemRow.vue'
import CollaborationRequestForm from './CollaborationRequestForm.vue'

const router = useRouter()
const store = useCollaborationStore()
const panelRef = ref(null)
const tabs = [
  { value: 'TODAY', label: '今日必做' },
  { value: 'ACTION_REQUIRED', label: '待我处理' },
  { value: 'IN_PROGRESS', label: '进行中' },
  { value: 'CREATED_BY_ME', label: '我发起的' },
]

const currentView = computed(() => store.navigationStack.at(-1) || null)
const headerContentKey = computed(() => currentView.value ? `view:${currentView.value.type}` : 'list')
const bodyContentKey = computed(() => {
  if (!currentView.value) return `list:${store.activeTab}`
  return currentView.value.type === 'detail'
    ? `detail:${currentView.value.id}`
    : currentView.value.type
})
const viewTransitionName = computed(() => (
  store.navigationDirection === 'back'
    ? 'collaboration-view-back'
    : 'collaboration-view-forward'
))
const viewTitle = computed(() => (
  currentView.value?.type === 'request-form' ? '发起请求' : '待办详情'
))
const currentKey = computed(() => store.cacheKey(store.activeTab))
const currentItems = computed(() => store.itemsByTab[currentKey.value] || [])
const currentLoading = computed(() => Boolean(store.loadingByTab[currentKey.value]))
const currentError = computed(() => store.errorByTab[currentKey.value] || '')
const todayLoading = computed(() => Boolean(store.loadingByTab['TODAY:all']))
const todayError = computed(() => store.errorByTab['TODAY:all'] || '')
const todayBundle = computed(() => store.todayBundle || {})
const dailySubmitted = computed(() => Boolean(todayBundle.value.dailyReport?.submitted))
const hasTrainingDay = computed(() => Boolean(todayBundle.value.training?.hasTrainingDay))
const trainingTitle = computed(() => {
  const t = todayBundle.value.training
  if (!t?.hasTrainingDay) return '今天没有训练任务'
  return t.title || t.primaryTask?.title || '完成今日训练并提交'
})
const trainingDone = computed(() => {
  const t = todayBundle.value.training
  if (!t?.hasTrainingDay) return true
  const tasks = Array.isArray(t.tasks) ? t.tasks : []
  if (tasks.length) return tasks.every((x) => x.latestSubmissionId)
  return Boolean(t.primaryTask?.latestSubmissionId)
})
const emptyTitle = computed(() => (
  store.activeTab === 'ACTION_REQUIRED' ? '没有待你处理的事项' : '这里暂时没有事项'
))
const emptyDescription = computed(() => (
  store.activeTab === 'ACTION_REQUIRED'
    ? '有人找你协作、老师派任务时，会出现在这里。'
    : '点击右上角“发起”，邀请队友一起推进。'
))

onMounted(() => store.start())
onBeforeUnmount(() => store.stop())

watch(
  () => store.isOpen,
  async isOpen => {
    if (!isOpen) return
    await nextTick()
    panelRef.value?.focus({ preventScroll: true })
    store.refreshCurrent().catch(() => {})
  }
)

function tabBadge(tab) {
  if (tab.value === 'TODAY') return Number(store.todayBundle?.pendingCount || store.summary?.todayPending || 0)
  if (tab.value === 'ACTION_REQUIRED') return Number(store.summary?.actionRequired || 0)
  return 0
}

function reload() {
  store.loadItems(store.activeTab, { force: true }).catch(() => {})
}

function reloadToday() {
  store.loadTodayBundle({ force: true }).catch(() => {})
}

function openDaily() {
  store.close()
  const report = todayBundle.value.dailyReport?.report
  if (dailySubmitted.value && report?.id) {
    router.push(`/daily-reports/${report.id}`)
    return
  }
  router.push('/daily-reports/write')
}

function openDailyCenter() {
  store.close()
  router.push('/daily-reports')
}

function openTraining() {
  const t = todayBundle.value.training
  store.close()
  if (t?.primaryTask?.taskId && t?.dayId) {
    router.push(`/training/tasks/${t.primaryTask.taskId}?dayId=${t.dayId}`)
    return
  }
  router.push('/training/today')
}

function openItem(item) {
  if (item.entityType === 'TASK') {
    store.close()
    router.push(item.targetPath || `/project-team/details/task-${item.linkedTaskId || item.id}`)
    return
  }
  store.showDetail(item)
}

function acceptItem(item) {
  store.accept(item.id).catch(() => openItem(item))
}

function declineItem(item) {
  openItem(item)
}

function withdrawItem(item) {
  store.withdraw(item.id).catch(() => openItem(item))
}

function openFullWorkspace() {
  store.close()
  router.push('/project-team')
}
</script>

<style scoped>
.collaboration-hub {
  position: fixed;
  z-index: calc(var(--z-fixed) + 10);
  left: calc(var(--workspace-sidebar-width) + 12px);
  bottom: 16px;
  width: min(448px, calc(100vw - var(--workspace-sidebar-width) - 32px));
  min-height: 500px;
  max-height: min(720px, calc(100vh - 32px));
  border: 1px solid var(--ds-card-border);
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  color: var(--ds-ink);
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 18px 48px rgba(29, 29, 31, 0.14), 0 2px 8px rgba(29, 29, 31, 0.06);
  transform-origin: left bottom;
}

.collaboration-hub:focus {
  outline: none;
}

.collaboration-hub__header {
  min-height: 80px;
  padding: 16px;
  border-bottom: 1px solid var(--ds-line);
  display: flex;
  align-items: center;
  gap: 12px;
}

.collaboration-hub__title {
  min-width: 0;
  flex: 1;
  overflow: hidden;
}

.collaboration-hub__title h2 {
  margin: 0;
  font-size: 17px;
  line-height: 1.3;
}

.collaboration-hub__title p {
  margin: 3px 0 0;
  overflow: hidden;
  color: var(--ds-muted);
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.collaboration-hub__icon-button {
  flex: 0 0 36px;
  width: 36px;
  height: 36px;
  border: 0;
  border-radius: 10px;
  display: grid;
  place-items: center;
  color: var(--ds-muted);
  background: transparent;
  cursor: pointer;
}

.collaboration-hub__icon-button:hover {
  color: var(--ds-ink);
  background: var(--ds-btn-ghost-bg-hover);
}

.collaboration-hub__icon-button svg,
.collaboration-hub__create svg {
  width: 20px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.collaboration-hub__toolbar {
  min-height: 50px;
  padding: 0 16px 0 20px;
  border-bottom: 1px solid var(--ds-line);
  display: flex;
  align-items: center;
  gap: 12px;
}

.collaboration-hub__tabs {
  min-width: 0;
  flex: 1;
  display: flex;
  gap: 16px;
  overflow-x: auto;
  scrollbar-width: none;
}

.collaboration-hub__tabs::-webkit-scrollbar {
  display: none;
}

.collaboration-hub__tabs button {
  position: relative;
  flex: 0 0 auto;
  height: 49px;
  border: 0;
  padding: 0;
  color: var(--ds-muted);
  background: transparent;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.collaboration-hub__tabs button.is-active {
  color: var(--ds-ink);
}

.collaboration-hub__tabs button.is-active::after {
  content: "";
  position: absolute;
  right: 0;
  bottom: -1px;
  left: 0;
  height: 2px;
  border-radius: 2px;
  background: var(--ds-orange-500);
}

.collaboration-hub__tabs span {
  min-width: 17px;
  height: 17px;
  margin-left: 3px;
  padding: 0 4px;
  border-radius: 999px;
  display: inline-grid;
  place-items: center;
  color: #fff;
  background: var(--ds-orange-700);
  font-size: 9px;
}

.collaboration-hub__create {
  flex: 0 0 auto;
  height: 34px;
  border: 1px solid var(--ds-orange-700);
  border-radius: 9px;
  padding: 0 11px;
  display: flex;
  align-items: center;
  gap: 5px;
  color: #fff;
  background: var(--ds-orange-700);
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  transition: transform 120ms ease, filter 120ms ease;
}

.collaboration-hub__create svg {
  width: 15px;
}

.collaboration-hub__create:active,
.collaboration-hub__icon-button:active {
  transform: scale(0.96);
}

.collaboration-hub__body {
  flex: 1;
  min-height: 0;
  padding: 20px;
  overflow-y: auto;
}

.collaboration-hub__body-content {
  min-height: 100%;
}

.collaboration-hub__list {
  display: grid;
}

.collaboration-hub__list-item {
  animation: collaboration-row-in 210ms var(--ds-motion-ease-out) both;
  animation-delay: calc(var(--collaboration-item-index) * 20ms);
}

.collaboration-hub__loading {
  display: grid;
  gap: 12px;
}

.collaboration-hub__loading span {
  height: 82px;
  border-radius: 10px;
  background: #f2f3f5;
  animation: collaboration-pulse 1.4s ease-in-out infinite alternate;
}

.collaboration-hub__error {
  min-height: 240px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
}

.collaboration-hub__error strong {
  font-size: 14px;
}

.collaboration-hub__error p {
  margin: 8px 0 16px;
  color: var(--ds-muted);
  font-size: 12px;
}

.collaboration-hub__error button {
  height: 34px;
  border: 1px solid var(--ds-btn-secondary-border);
  border-radius: 9px;
  padding: 0 12px;
  background: #fff;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.collaboration-hub__footer {
  min-height: 56px;
  padding: 10px 20px;
  border-top: 1px solid var(--ds-line);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.collaboration-hub__footer span {
  color: var(--ds-faint);
  font-size: 11px;
}

.collaboration-hub__footer button {
  border: 0;
  padding: 6px 0;
  color: var(--ds-orange-700);
  background: transparent;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
}

.today-todo {
  display: grid;
  gap: 12px;
}

.today-todo__card {
  width: 100%;
  display: grid;
  grid-template-columns: auto 1fr auto;
  align-items: center;
  gap: 12px;
  padding: 14px 14px;
  border: 1px solid var(--ds-card-border, #e8eaee);
  border-radius: 14px;
  background: #fff;
  text-align: left;
  cursor: pointer;
  transition: border-color 120ms ease, box-shadow 120ms ease, background 120ms ease;
}

.today-todo__card:hover {
  border-color: color-mix(in srgb, var(--ds-orange-400, #fb923c) 45%, var(--ds-card-border, #e8eaee));
  box-shadow: 0 6px 18px rgba(29, 29, 31, 0.06);
}

.today-todo__card.is-done {
  background: #f8fafc;
}

.today-todo__badge {
  flex: 0 0 auto;
  min-width: 40px;
  height: 28px;
  padding: 0 8px;
  border-radius: 999px;
  display: inline-grid;
  place-items: center;
  font-size: 11px;
  font-weight: 800;
  line-height: 1;
}

.today-todo__badge.is-todo {
  color: #9a3412;
  background: #ffedd5;
}

.today-todo__badge.is-ok {
  color: #047857;
  background: #d1fae5;
}

.today-todo__copy {
  min-width: 0;
  display: grid;
  gap: 3px;
}

.today-todo__copy strong {
  font-size: 14px;
  font-weight: 750;
  color: var(--ds-ink);
}

.today-todo__copy small {
  color: var(--ds-muted);
  font-size: 12px;
  line-height: 1.4;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.today-todo__action {
  color: var(--ds-orange-700, #c2410c);
  font-size: 12px;
  font-weight: 750;
  white-space: nowrap;
}

.today-todo__hint {
  margin: 4px 2px 0;
  color: var(--ds-faint, #9ca3af);
  font-size: 12px;
  line-height: 1.45;
}

.today-todo__link {
  border: 0;
  padding: 4px 2px;
  background: transparent;
  color: var(--ds-orange-700, #c2410c);
  font-size: 12px;
  font-weight: 750;
  text-align: left;
  cursor: pointer;
}

.collaboration-hub__footer-actions {
  display: flex;
  gap: 14px;
  align-items: center;
}

.collaboration-hub button:focus-visible {
  outline: var(--ds-focus-outline);
  outline-offset: var(--ds-focus-offset);
}

.collaboration-hub-enter-active {
  transition: opacity 220ms var(--ds-motion-ease-out),
    transform 220ms var(--ds-motion-ease-out);
}

.collaboration-hub-leave-active {
  transition: opacity 170ms ease-in,
    transform 170ms ease-in;
}

.collaboration-hub-enter-from,
.collaboration-hub-leave-to {
  opacity: 0;
  transform: translateY(8px) scale(0.985);
}

.collaboration-view-forward-enter-active,
.collaboration-view-back-enter-active {
  transition: opacity 180ms var(--ds-motion-ease-out),
    transform 180ms var(--ds-motion-ease-out);
}

.collaboration-view-forward-leave-active,
.collaboration-view-back-leave-active {
  transition: opacity 120ms ease-in,
    transform 120ms ease-in;
}

.collaboration-view-forward-enter-from {
  opacity: 0;
  transform: translateX(14px);
}

.collaboration-view-forward-leave-to {
  opacity: 0;
  transform: translateX(-10px);
}

.collaboration-view-back-enter-from {
  opacity: 0;
  transform: translateX(-14px);
}

.collaboration-view-back-leave-to {
  opacity: 0;
  transform: translateX(10px);
}

.collaboration-chrome-enter-active,
.collaboration-chrome-leave-active {
  transition: opacity 130ms ease, transform 150ms var(--ds-motion-ease-out);
}

.collaboration-chrome-enter-from,
.collaboration-chrome-leave-to {
  opacity: 0;
  transform: translateY(-3px);
}

@keyframes collaboration-pulse {
  to { opacity: 0.52; }
}

@keyframes collaboration-row-in {
  from {
    opacity: 0;
    transform: translateY(5px);
  }
}

@media (max-width: 1023px) {
  .collaboration-hub {
    left: 8px;
    right: 8px;
    bottom: 82px;
    width: auto;
    min-height: min(540px, calc(100vh - 112px));
    max-height: calc(100vh - 96px);
    border-radius: 20px;
    transform-origin: center bottom;
  }
}

@media (max-width: 560px) {
  .collaboration-hub {
    top: 72px;
    bottom: 82px;
    min-height: 0;
  }

  .collaboration-hub__header {
    min-height: 72px;
  }

  .collaboration-hub__body {
    padding: 16px;
  }

  .collaboration-hub__tabs {
    gap: 13px;
  }
}

@media (prefers-reduced-motion: reduce) {
  .collaboration-hub-enter-active,
  .collaboration-hub-leave-active,
  .collaboration-view-forward-enter-active,
  .collaboration-view-forward-leave-active,
  .collaboration-view-back-enter-active,
  .collaboration-view-back-leave-active,
  .collaboration-chrome-enter-active,
  .collaboration-chrome-leave-active {
    transition-duration: 0.01ms;
  }

  .collaboration-view-forward-enter-from,
  .collaboration-view-forward-leave-to,
  .collaboration-view-back-enter-from,
  .collaboration-view-back-leave-to,
  .collaboration-chrome-enter-from,
  .collaboration-chrome-leave-to {
    transform: none;
  }

  .collaboration-hub__list-item {
    animation: none;
  }

  .collaboration-hub__loading span {
    animation: none;
  }
}
</style>
