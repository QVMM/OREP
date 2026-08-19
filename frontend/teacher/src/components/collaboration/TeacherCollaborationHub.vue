<template>
  <Transition name="teacher-collaboration-panel">
    <section
      v-if="store.isOpen"
      ref="panel"
      class="teacher-collaboration-panel"
      role="dialog"
      aria-modal="false"
      aria-labelledby="teacher-collaboration-title"
      tabindex="-1"
      @keydown.esc="store.close"
    >
      <header class="teacher-collaboration-panel__head">
        <button v-if="currentView" type="button" aria-label="返回协作列表" @click="store.back">
          <svg viewBox="0 0 24 24"><path d="m15 6-6 6 6 6" /></svg>
        </button>
        <CollaborationBrandMark v-else />
        <div>
          <h2 id="teacher-collaboration-title">{{ currentView ? viewTitle : '协作工作台' }}</h2>
          <p>{{ currentView ? '处理后状态会实时同步给团队' : '发布协调任务并验收团队成果' }}</p>
        </div>
        <button type="button" aria-label="关闭协作工作台" @click="store.close">
          <svg viewBox="0 0 24 24"><path d="m6 6 12 12M18 6 6 18" /></svg>
        </button>
      </header>

      <template v-if="!currentView">
        <div class="teacher-collaboration-panel__scope">
          <label>
            <span>团队范围</span>
            <select :value="store.activeTeamId" @change="store.setTeam($event.target.value)">
              <option value="all">全部队伍</option>
              <option v-for="team in store.teams" :key="team.id" :value="team.id">
                {{ team.name }}
              </option>
            </select>
          </label>
          <button type="button" @click="store.showTaskForm">+ 发布任务</button>
        </div>
        <nav class="teacher-collaboration-panel__tabs" role="tablist" aria-label="协作任务范围">
          <button
            v-for="tab in tabs"
            :key="tab.value"
            type="button"
            role="tab"
            :aria-selected="store.activeTab === tab.value"
            :class="{ 'is-active': store.activeTab === tab.value }"
            @click="store.setTab(tab.value)"
          >
            {{ tab.label }}
            <em v-if="tab.value === 'ACTION_REQUIRED' && store.actionCount">
              {{ store.actionCount > 99 ? '99+' : store.actionCount }}
            </em>
          </button>
        </nav>
      </template>

      <div class="teacher-collaboration-panel__body">
        <TeacherTaskForm v-if="currentView?.type === 'task-form'" />
        <TeacherReviewDetail v-else-if="currentView?.type === 'review'" :view="currentView" />
        <template v-else>
          <div v-if="store.loading" class="teacher-collaboration-panel__loading">
            <span v-for="n in 4" :key="n"></span>
          </div>
          <div v-else-if="store.error" class="teacher-collaboration-panel__state">
            <strong>任务暂时无法加载</strong>
            <p>{{ store.error }}</p>
            <button type="button" @click="store.refresh">重新加载</button>
          </div>
          <div v-else-if="!store.visibleItems.length" class="teacher-collaboration-panel__state">
            <strong>{{ store.activeTab === 'ACTION_REQUIRED' ? '没有待你处理的任务' : '当前范围暂无任务' }}</strong>
            <p>训练、团队、老师或协作任务有变化时，会集中显示在这里。</p>
          </div>
          <div v-else class="teacher-collaboration-panel__list">
            <article
              v-for="item in store.visibleItems"
              :key="item.key || `${item.entityType}:${item.id}`"
              :class="[`is-source-${sourceTone(item)}`, { 'is-action': item.actionRequired }]"
            >
              <button type="button" @click="openItem(item)">
                <i aria-hidden="true"></i>
                <span>
                  <small>
                    <b>{{ item.sourceLabel || '团队任务' }}</b>
                    <em>{{ item.statusLabel || itemStatus(item) }}</em>
                  </small>
                  <strong>{{ item.title }}</strong>
                  <span>{{ itemMeta(item) }}</span>
                </span>
                <mark v-if="primaryActionLabel(item)">{{ primaryActionLabel(item) }}</mark>
                <svg viewBox="0 0 24 24"><path d="m9 6 6 6-6 6" /></svg>
              </button>
              <footer v-if="item.canAccept || item.canWithdraw">
                <button v-if="item.canWithdraw" type="button" @click="store.withdrawRequest(item.id)">
                  撤回
                </button>
                <template v-if="item.canAccept">
                  <button type="button" @click="declineRequest(item)">婉拒</button>
                  <button class="is-primary" type="button" @click="store.acceptRequest(item.id)">
                    接受
                  </button>
                </template>
              </footer>
            </article>
          </div>
        </template>
      </div>

      <footer v-if="!currentView" class="teacher-collaboration-panel__foot">
        <span>仅显示你管理范围内的团队</span>
        <button type="button" @click="syncTeam">跟随顶部团队</button>
      </footer>
    </section>
  </Transition>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useTeacherContextStore } from '../../stores/context'
import { useTeacherCollaborationStore } from '../../stores/collaboration'
import CollaborationBrandMark from './CollaborationBrandMark.vue'
import TeacherReviewDetail from './TeacherReviewDetail.vue'
import TeacherTaskForm from './TeacherTaskForm.vue'

const store = useTeacherCollaborationStore()
const context = useTeacherContextStore()
const router = useRouter()
const panel = ref(null)
const tabs = [
  { value: 'ACTION_REQUIRED', label: '待我处理' },
  { value: 'IN_PROGRESS', label: '进行中' },
  { value: 'CREATED_BY_ME', label: '我发起的' },
  { value: 'ALL', label: '全部' },
]
const currentView = computed(() => store.navigationStack.at(-1) || null)
const viewTitle = computed(() => currentView.value?.type === 'task-form' ? '发布任务' : '成果审核')

onMounted(async () => {
  store.start()
  await store.loadTeams().catch(() => {})
})
onBeforeUnmount(() => store.stop())

watch(
  () => store.isOpen,
  async open => {
    if (!open) return
    await nextTick()
    panel.value?.focus({ preventScroll: true })
    store.refresh().catch(() => {})
  }
)

function itemStatus(item) {
  const key = String(item?.status || '').toUpperCase()
  return {
    PENDING: '待回应',
    PENDING_REVIEW: '待审核',
    TODO: '待开始',
    IN_PROGRESS: '进行中',
    REVIEWING: '待审核',
    CHANGES_REQUESTED: '需修改',
    DONE: '已完成',
    COMPLETED: '已完成',
    CANCELLED: '已取消',
  }[key] || (/[\u4e00-\u9fff]/.test(String(item?.status || '')) ? item.status : '任务')
}

function sourceTone(item) {
  return {
    TRAINING_DAY: 'training',
    TEAM_TASK: 'team',
    TEACHER_ASSIGNMENT: 'teacher',
    PEER_COLLABORATION: 'peer',
  }[item.sourceType] || 'team'
}

function itemMeta(item) {
  const team = item.teamName || '项目团队'
  const actor = item.createdByCurrentUser
    ? '你发布'
    : `${item.creatorName || item.requesterName || '团队成员'}发布`
  const due = item.dueAt
    ? ` · 截止 ${String(item.dueAt).replace('T', ' ').slice(5, 16)}`
    : ''
  return `${team} · ${actor}${due}`
}

function primaryActionLabel(item) {
  if (item.canAccept || item.canWithdraw) return ''
  return {
    REVIEW: '审核',
    SUBMIT: '查看',
    OPEN: '查看',
  }[item.primaryAction] || ''
}

function openItem(item) {
  if (item.primaryAction === 'REVIEW' && item.latestSubmissionId) {
    store.showReview(item).catch(() => {})
    return
  }
  if (item.entityType === 'TASK' && item.targetPath) {
    store.close()
    router.push(item.targetPath)
  }
}

function declineRequest(item) {
  const reason = window.prompt('可填写婉拒说明（选填）', '') ?? null
  if (reason === null) return
  store.declineRequest(item.id, reason).catch(() => {})
}

function syncTeam() {
  store.setTeam(context.teamId || 'all')
}
</script>

<style scoped>
.teacher-collaboration-panel {
  position: fixed;
  z-index: 100;
  left: 98px;
  bottom: 16px;
  width: min(448px, calc(100vw - 114px));
  min-height: 520px;
  max-height: min(740px, calc(100vh - 32px));
  border: 1px solid var(--ds-card-border);
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  color: var(--ds-ink);
  background: rgba(255,255,255,.98);
  box-shadow: 0 18px 48px rgba(29,29,31,.14), 0 2px 8px rgba(29,29,31,.06);
}

.teacher-collaboration-panel:focus { outline:none; }
.teacher-collaboration-panel__head { min-height:76px; padding:14px 16px; border-bottom:1px solid var(--ds-line); display:flex; align-items:center; gap:11px; }
.teacher-collaboration-panel__head > div { min-width:0; flex:1; }
.teacher-collaboration-panel__head h2 { margin:0; font-size:16px; }
.teacher-collaboration-panel__head p { margin:4px 0 0; color:var(--ds-muted); font-size:11px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
.teacher-collaboration-panel__head > button { flex:0 0 34px; width:34px; height:34px; border:0; border-radius:9px; display:grid; place-items:center; color:var(--ds-muted); background:transparent; cursor:pointer; }
.teacher-collaboration-panel__head > button:hover { color:var(--ds-ink); background:var(--ds-surface-soft); }
.teacher-collaboration-panel__head svg { width:18px; fill:none; stroke:currentColor; stroke-width:1.8; stroke-linecap:round; }
.teacher-collaboration-panel__scope { min-height:58px; padding:10px 16px; border-bottom:1px solid var(--ds-line); display:flex; align-items:center; gap:10px; }
.teacher-collaboration-panel__scope label { min-width:0; flex:1; display:flex; align-items:center; gap:8px; }
.teacher-collaboration-panel__scope label span { flex:0 0 auto; color:var(--ds-muted); font-size:10px; font-weight:700; }
.teacher-collaboration-panel__scope select { min-width:0; flex:1; height:34px; border:1px solid var(--ds-line-strong); border-radius:9px; padding:0 9px; color:var(--ds-ink-2); background:#fff; font:600 11px var(--ds-font-sans); }
.teacher-collaboration-panel__scope > button { height:34px; border:1px solid var(--ds-orange-deep); border-radius:9px; padding:0 11px; color:#fff; background:var(--ds-orange-deep); font:700 11px var(--ds-font-sans); cursor:pointer; }
.teacher-collaboration-panel__tabs { min-height:44px; padding:0 16px; border-bottom:1px solid var(--ds-line); display:flex; gap:18px; overflow-x:auto; }
.teacher-collaboration-panel__tabs button { position:relative; flex:0 0 auto; height:44px; border:0; padding:0; color:var(--ds-muted); background:transparent; font:700 11px var(--ds-font-sans); cursor:pointer; }
.teacher-collaboration-panel__tabs button.is-active { color:var(--ds-ink); }
.teacher-collaboration-panel__tabs button.is-active::after { content:""; position:absolute; left:0; right:0; bottom:-1px; height:2px; background:var(--ds-orange); }
.teacher-collaboration-panel__tabs em { min-width:16px; height:16px; margin-left:3px; padding:0 3px; border-radius:999px; display:inline-grid; place-items:center; color:#fff; background:var(--ds-orange-deep); font-size:9px; font-style:normal; }
.teacher-collaboration-panel__body { min-height:0; flex:1; padding:18px; overflow-y:auto; }
.teacher-collaboration-panel__loading { display:grid; gap:9px; }
.teacher-collaboration-panel__loading span { height:78px; border-radius:10px; background:#f1f2f4; }
.teacher-collaboration-panel__state { min-height:250px; border:1px dashed var(--ds-line-strong); border-radius:11px; display:flex; flex-direction:column; align-items:center; justify-content:center; padding:24px; text-align:center; background:#fafafb; }
.teacher-collaboration-panel__state strong { font-size:13px; }
.teacher-collaboration-panel__state p { margin:7px 0 14px; color:var(--ds-muted); font-size:11px; }
.teacher-collaboration-panel__state button { height:32px; border:1px solid var(--ds-line-strong); border-radius:8px; padding:0 11px; background:#fff; font:700 11px var(--ds-font-sans); cursor:pointer; }
.teacher-collaboration-panel__list article { --task-source:#2d6cdf; border-bottom:1px solid var(--ds-line); }
.teacher-collaboration-panel__list article:first-child { border-top:1px solid var(--ds-line); }
.teacher-collaboration-panel__list article.is-source-training { --task-source:var(--ds-orange); }
.teacher-collaboration-panel__list article.is-source-teacher { --task-source:#159a73; }
.teacher-collaboration-panel__list article.is-source-peer { --task-source:#7657d6; }
.teacher-collaboration-panel__list article.is-action { margin:0 -6px; padding:0 6px; border-radius:11px; background:linear-gradient(90deg,rgba(229,72,29,.055),transparent); }
.teacher-collaboration-panel__list article > button { width:100%; min-height:88px; border:0; padding:12px 3px; display:flex; align-items:flex-start; gap:10px; color:inherit; background:transparent; text-align:left; cursor:pointer; }
.teacher-collaboration-panel__list i { flex:0 0 7px; width:7px; height:7px; margin-top:8px; border-radius:50%; background:var(--task-source); box-shadow:0 0 0 4px color-mix(in srgb,var(--task-source) 10%,transparent); }
.teacher-collaboration-panel__list article > button > span { min-width:0; flex:1; display:grid; gap:5px; }
.teacher-collaboration-panel__list small { display:flex; align-items:center; gap:7px; color:var(--ds-muted); font-size:10px; }
.teacher-collaboration-panel__list small b { color:var(--task-source); }
.teacher-collaboration-panel__list small em { padding:2px 5px; border-radius:999px; color:var(--ds-ink-2); background:var(--ds-surface-soft); font-style:normal; }
.teacher-collaboration-panel__list article > button strong { overflow:hidden; font-size:13px; text-overflow:ellipsis; white-space:nowrap; }
.teacher-collaboration-panel__list article > button span > span { overflow:hidden; color:var(--ds-muted); font-size:10px; text-overflow:ellipsis; white-space:nowrap; }
.teacher-collaboration-panel__list mark { flex:0 0 auto; margin-top:31px; color:var(--task-source); background:transparent; font-size:10px; font-weight:800; }
.teacher-collaboration-panel__list article > button > svg { width:17px; margin-top:29px; fill:none; stroke:var(--ds-faint); stroke-width:1.8; stroke-linecap:round; stroke-linejoin:round; }
.teacher-collaboration-panel__list article > footer { padding:0 4px 10px 27px; display:flex; justify-content:flex-end; gap:7px; }
.teacher-collaboration-panel__list article > footer button { height:30px; border:1px solid var(--ds-line-strong); border-radius:8px; padding:0 10px; background:#fff; font:700 10px var(--ds-font-sans); cursor:pointer; }
.teacher-collaboration-panel__list article > footer button.is-primary { border-color:var(--ds-orange-deep); color:#fff; background:var(--ds-orange-deep); }
.teacher-collaboration-panel__foot { min-height:50px; padding:9px 18px; border-top:1px solid var(--ds-line); display:flex; align-items:center; justify-content:space-between; gap:10px; }
.teacher-collaboration-panel__foot span { color:var(--ds-faint); font-size:10px; }
.teacher-collaboration-panel__foot button { border:0; padding:6px 0; color:var(--ds-orange-deep); background:transparent; font:700 10px var(--ds-font-sans); cursor:pointer; }
.teacher-collaboration-panel button:focus-visible,.teacher-collaboration-panel select:focus-visible { outline:2px solid var(--ds-orange); outline-offset:2px; }
.teacher-collaboration-panel-enter-active,.teacher-collaboration-panel-leave-active { transition:opacity .18s ease,transform .18s ease; }
.teacher-collaboration-panel-enter-from,.teacher-collaboration-panel-leave-to { opacity:0; transform:translateY(8px) scale(.985); }

@media(max-width:720px){
  .teacher-collaboration-panel { left:8px; right:8px; top:66px; bottom:8px; width:auto; min-height:0; max-height:none; border-radius:18px; }
  .teacher-collaboration-panel__body { padding:16px; }
}

@media(prefers-reduced-motion:reduce){
  .teacher-collaboration-panel-enter-active,.teacher-collaboration-panel-leave-active { transition-duration:.01ms; }
}
</style>
