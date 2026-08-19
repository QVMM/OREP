<template>
  <div class="teacher-page review-page">
    <header class="teacher-page__head">
      <div>
        <h1>提交与批改</h1>
        <p>按训练日查看学生交了什么、谁还没交、哪些等你批改。通过或打回后学生端会同步。</p>
      </div>
      <div class="teacher-page__actions">
        <router-link class="teacher-btn teacher-btn--secondary" to="/camp">返回训练营</router-link>
        <button
          type="button"
          class="teacher-btn teacher-btn--secondary"
          :disabled="loading"
          @click="load"
        >
          刷新
        </button>
        <button
          type="button"
          class="teacher-btn teacher-btn--primary"
          :disabled="reminding || !missingCount"
          @click="remindMissing"
        >
          提醒未提交{{ missingCount ? `（${missingCount}）` : '' }}
        </button>
      </div>
    </header>

    <p v-if="banner" class="review-banner" :class="{ 'is-error': bannerError }" aria-live="polite">
      {{ banner }}
    </p>

    <section v-if="loading" class="teacher-card teacher-empty">正在加载提交与批改…</section>

    <section v-else-if="!hasCamp" class="teacher-card review-empty">
      <strong>还没有可批改的训练营</strong>
      <p>先创建训练营并发布训练日，学生提交后会出现在这里。</p>
      <router-link class="teacher-btn teacher-btn--primary" to="/camp/create">创建训练营</router-link>
    </section>

    <template v-else>
      <!-- 1. 训练日选择：老师第一眼能切换「看哪一天」 -->
      <section class="teacher-card review-days" aria-label="选择训练日">
        <div class="review-days__head">
          <div>
            <strong>{{ camp.campName || ctx.campName || '当前训练营' }}</strong>
            <small>
              {{ formatDate(camp.startDate) }} – {{ formatDate(camp.endDate) }}
              · 共 {{ days.length }} 天
            </small>
          </div>
          <button
            v-if="Number(selectedDayNo) !== Number(currentDayNo)"
            type="button"
            class="teacher-btn teacher-btn--secondary teacher-btn--sm"
            @click="selectedDayNo = currentDayNo"
          >
            回到今日（第 {{ currentDayNo }} 天）
          </button>
        </div>
        <div ref="dayScrollerEl" class="review-days__scroller" role="tablist" aria-label="训练日列表">
          <button
            v-for="day in days"
            :key="day.dayId || day.dayNo"
            type="button"
            role="tab"
            class="day-chip"
            :class="{
              'is-active': Number(day.dayNo) === Number(selectedDayNo),
              'is-today': Number(day.dayNo) === Number(currentDayNo),
            }"
            :data-day-no="day.dayNo"
            :aria-selected="Number(day.dayNo) === Number(selectedDayNo)"
            @click="selectedDayNo = Number(day.dayNo)"
          >
            <span class="day-chip__no">
              第 {{ day.dayNo }} 天
              <em v-if="Number(day.dayNo) === Number(currentDayNo)">今天</em>
            </span>
            <strong class="day-chip__title">{{ day.title || '未命名主题' }}</strong>
            <small class="day-chip__meta">
              {{ formatDate(day.trainingDate) }}
              · {{ dayStatusLabel(day.status) }}
            </small>
            <span v-if="Number(day.pendingCount) > 0" class="day-chip__badge">
              待批 {{ day.pendingCount }}
            </span>
          </button>
        </div>
      </section>

      <!-- 2. 当日概览：可点指标 = 筛选 -->
      <section class="teacher-card review-summary" aria-label="当日概况">
        <div class="review-summary__title">
          <div>
            <h2>
              第 {{ selectedDayNo }} 天
              <template v-if="selectedDay?.title"> · {{ selectedDay.title }}</template>
            </h2>
            <p>
              {{ formatDate(selectedDay?.trainingDate) }}
              · 任务要求 {{ taskCount }} 项
              · 成员 {{ people.length }} 人
            </p>
          </div>
        </div>
        <div class="review-kpis" role="group" aria-label="快捷筛选">
          <button
            type="button"
            class="review-kpi"
            :class="{ 'is-active': quickFilter === 'pending' }"
            @click="toggleQuick('pending')"
          >
            <small>待我批改</small>
            <strong class="is-accent">{{ stats.pending }}</strong>
            <em>优先处理</em>
          </button>
          <button
            type="button"
            class="review-kpi"
            :class="{ 'is-active': quickFilter === 'missing' }"
            @click="toggleQuick('missing')"
          >
            <small>未提交</small>
            <strong>{{ stats.missing }}</strong>
            <em>可一键提醒</em>
          </button>
          <button
            type="button"
            class="review-kpi"
            :class="{ 'is-active': quickFilter === 'recheck' }"
            @click="toggleQuick('recheck')"
          >
            <small>需修改</small>
            <strong>{{ stats.recheck }}</strong>
            <em>学生重交后复核</em>
          </button>
          <button
            type="button"
            class="review-kpi"
            :class="{ 'is-active': quickFilter === 'reviewed' }"
            @click="toggleQuick('reviewed')"
          >
            <small>已通过</small>
            <strong>{{ stats.reviewed }}</strong>
            <em>可回看</em>
          </button>
          <button
            type="button"
            class="review-kpi"
            :class="{ 'is-active': quickFilter === 'all' }"
            @click="toggleQuick('all')"
          >
            <small>全部成员</small>
            <strong>{{ people.length }}</strong>
            <em>已交 {{ stats.submitted }}</em>
          </button>
        </div>
      </section>

      <!-- 3. 学生列表 -->
      <section class="teacher-card review-list-card">
        <div class="review-list-toolbar">
          <div>
            <strong>{{ listTitle }}</strong>
            <span>显示 {{ visible.length }} / {{ people.length }} 人 · 待办优先排序</span>
          </div>
          <div class="review-list-toolbar__tools">
            <input
              v-model.trim="keyword"
              type="search"
              placeholder="搜索姓名 / 岗位"
              aria-label="搜索学生"
            />
          </div>
        </div>

        <div v-if="visible.length" class="review-table-wrap">
          <table class="teacher-table review-table">
            <thead>
              <tr>
                <th>学生</th>
                <th>提交</th>
                <th>批改</th>
                <th>最近提交</th>
                <th>说明</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="person in visible" :key="person.key">
                <td>
                  <div class="review-person">
                    <span
                      class="review-person__avatar"
                      :style="{ background: avatarColor(person.userId || person.name) }"
                      aria-hidden="true"
                    >{{ initial(person.name) }}</span>
                    <span>
                      <strong>{{ person.name }}</strong>
                      <small>{{ person.role }}</small>
                    </span>
                  </div>
                </td>
                <td>
                  <span
                    class="status-pill"
                    :data-tone="person.hasSubmission ? 'ok' : 'danger'"
                  >
                    {{ person.hasSubmission ? '已提交' : '未提交' }}
                  </span>
                </td>
                <td>
                  <span class="status-pill" :data-tone="markTone(person.mark)">
                    {{ person.markLabel }}
                  </span>
                </td>
                <td>
                  <div class="review-time-cell">
                    <strong>{{ person.time }}</strong>
                    <small v-if="person.versionLabel">{{ person.versionLabel }}</small>
                  </div>
                </td>
                <td>
                  <span class="review-note">{{ person.note }}</span>
                </td>
                <td class="review-actions">
                  <button
                    v-if="!person.hasSubmission"
                    type="button"
                    class="teacher-btn teacher-btn--secondary teacher-btn--sm"
                    :disabled="reminding"
                    @click="remindOne(person)"
                  >
                    提醒提交
                  </button>
                  <button
                    v-else
                    type="button"
                    class="teacher-btn teacher-btn--sm"
                    :class="person.mark === 'reviewed' ? 'teacher-btn--secondary' : 'teacher-btn--primary'"
                    @click="openReview(person)"
                  >
                    {{ actionLabel(person) }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="review-list-empty">
          <strong>{{ emptyTitle }}</strong>
          <p>{{ emptyHint }}</p>
          <button
            v-if="quickFilter !== 'all'"
            type="button"
            class="teacher-btn teacher-btn--secondary teacher-btn--sm"
            @click="quickFilter = 'all'"
          >
            查看全部成员
          </button>
        </div>
      </section>

      <p class="review-footer-tip">
        批改流程：选训练日 → 先处理「待我批改」→ 打开提交查看附件 → 通过或打回并写反馈。
        未交学生可单独提醒，也可顶部批量提醒。
      </p>
    </template>

    <!-- 批改抽屉 -->
    <Teleport to="body">
      <div
        v-if="active"
        class="drawer-mask teacher-overlay-mask"
        role="presentation"
        @click.self="closeDrawer"
        @keydown.esc.prevent="closeDrawer"
      >
        <aside
          class="review-drawer"
          role="dialog"
          aria-modal="true"
          :aria-label="`${actionLabel(active)} · ${active.name}`"
        >
          <header class="review-drawer__head">
            <div>
              <span class="status-pill" :data-tone="markTone(active.mark)">{{ active.markLabel }}</span>
              <h2>{{ active.name }}</h2>
              <p>
                第 {{ selectedDayNo }} 天
                <template v-if="selectedDay?.title"> · {{ selectedDay.title }}</template>
                · {{ active.role }}
              </p>
            </div>
            <button type="button" class="teacher-btn teacher-btn--secondary teacher-btn--sm" @click="closeDrawer">
              关闭
            </button>
          </header>

          <div v-if="detailLoading" class="teacher-empty">正在加载提交详情…</div>

          <template v-else-if="detail">
            <div class="review-drawer__body">
              <section v-if="requirements.length" class="drawer-section">
                <h3>本日本次任务要求</h3>
                <ul class="req-list">
                  <li v-for="req in requirements" :key="req.id || req.title">
                    <strong>{{ req.title || '要求' }}</strong>
                    <span v-if="req.description">{{ req.description }}</span>
                    <em v-if="req.required">必交</em>
                  </li>
                </ul>
              </section>

              <section class="drawer-section">
                <h3>学生提交内容</h3>
                <p class="drawer-content">{{ detail.content || '本次未填写文字说明。' }}</p>
                <div v-if="detailAssets.length" class="asset-list">
                  <a
                    v-for="asset in detailAssets"
                    :key="asset.id || asset.fileUrl || asset.fileName"
                    class="asset-link"
                    :href="asset.fileUrl || asset.attachmentUrl || '#'"
                    target="_blank"
                    rel="noopener"
                  >
                    <span>{{ asset.fileName || asset.attachmentName || '附件' }}</span>
                    <small>打开 ›</small>
                  </a>
                </div>
                <p v-else class="drawer-muted">未附带文件</p>
              </section>

              <section v-if="historyRows.length" class="drawer-section">
                <h3>提交版本</h3>
                <ul class="history-list">
                  <li v-for="h in historyRows" :key="h.submissionId || h.id">
                    <strong>v{{ h.versionNo || '—' }}</strong>
                    <span>{{ statusLabel(h.status) }}</span>
                    <em>{{ formatDateTime(h.submittedAt || h.createdAt) }}</em>
                  </li>
                </ul>
              </section>

              <section v-if="previousComment" class="drawer-section drawer-section--soft">
                <h3>上次教师反馈</h3>
                <p class="drawer-content">{{ previousComment }}</p>
              </section>

              <section v-if="canReviewActive" class="drawer-section drawer-section--action">
                <h3>本次批改</h3>
                <div class="result-toggle" role="group" aria-label="批改结果">
                  <button
                    type="button"
                    :class="{ 'is-active': result === 'pass' }"
                    @click="result = 'pass'"
                  >
                    通过
                  </button>
                  <button
                    type="button"
                    :class="{ 'is-active': result === 'revise', 'is-warn': true }"
                    @click="result = 'revise'"
                  >
                    需修改重交
                  </button>
                </div>
                <label class="field">
                  <span>给学生的反馈 <i v-if="result === 'revise'">（建议必填）</i></span>
                  <textarea
                    v-model="comment"
                    rows="5"
                    :placeholder="
                      result === 'pass'
                        ? '可选：肯定做得好的地方，或补充建议'
                        : '请写清楚要改什么、怎么改，学生才能重交'
                    "
                  />
                </label>
              </section>

              <section v-else class="drawer-section drawer-section--soft">
                <h3>批改状态</h3>
                <p class="drawer-content">
                  {{
                    active.mark === 'reviewed'
                      ? '该提交已通过，可查看历史与附件。'
                      : '当前版本不可再批（可能已有更新版本，或状态已结束）。'
                  }}
                </p>
                <p v-if="detail.reviewComment" class="drawer-content">
                  <strong>反馈：</strong>{{ detail.reviewComment }}
                </p>
              </section>
            </div>

            <footer class="review-drawer__foot">
              <p v-if="done" class="review-done">{{ done }}</p>
              <div class="review-drawer__actions">
                <button type="button" class="teacher-btn teacher-btn--secondary" @click="closeDrawer">
                  {{ canReviewActive ? '取消' : '关闭' }}
                </button>
                <button
                  v-if="canReviewActive"
                  type="button"
                  class="teacher-btn teacher-btn--primary"
                  :disabled="submitting || !active.submissionId || (result === 'revise' && !comment.trim())"
                  @click="submitReview"
                >
                  {{
                    submitting
                      ? '提交中…'
                      : result === 'pass'
                        ? '确认通过'
                        : '打回并通知学生'
                  }}
                </button>
              </div>
            </footer>
          </template>
        </aside>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import {
  fetchTeacherCamp,
  fetchTeacherReviewQueue,
  fetchTeacherSubmission,
  reviewSubmission,
  sendTeacherReminder,
} from '../../api'
import { useTeacherContextStore } from '../../stores/context'
import { anyRoleLabel, dayStatusLabel, submissionStatusLabel } from '../../utils/labels'

const AVATAR_COLORS = ['#e84a1c', '#2563eb', '#0f766e', '#7c3aed', '#b45309', '#db2777', '#0e7490']

const ctx = useTeacherContextStore()
const loading = ref(true)
const banner = ref('')
const bannerError = ref(false)
const hasCamp = ref(false)
const camp = ref({})
const days = ref([])
const progress = ref([])
const queueBySubmission = ref(new Map())
const selectedDayNo = ref(null)
/** 上次加载对应的营 ID：换营/首次进入时默认定位当天 */
const boundCampId = ref(null)
const dayScrollerEl = ref(null)
const keyword = ref('')
const quickFilter = ref('pending')
const reminding = ref(false)

const active = ref(null)
const detail = ref(null)
const detailLoading = ref(false)
const comment = ref('')
const result = ref('pass')
const done = ref('')
const submitting = ref(false)

const currentDayNo = computed(() => {
  const n = Number(camp.value.currentDay)
  if (Number.isFinite(n) && n > 0) return n
  return Number(days.value[0]?.dayNo) || 1
})
const selectedDay = computed(
  () => days.value.find((d) => Number(d.dayNo) === Number(selectedDayNo.value)) || null
)

/** 进入页/换营时落到当天；若当天不在列表则取最近合法日 */
function resolveDefaultDayNo() {
  const today = currentDayNo.value
  const nos = days.value.map((d) => Number(d.dayNo)).filter((n) => Number.isFinite(n) && n > 0)
  if (!nos.length) return today || 1
  if (nos.includes(today)) return today
  // 营未开始（currentDay=0）→ 第 1 天；已结束但 currentDay 被夹在 totalDays → 上面 includes 会命中
  if (today <= 0) return nos[0]
  // 找不到当天时取不超过 today 的最大 dayNo，否则取第一天
  const past = nos.filter((n) => n <= today)
  return past.length ? past[past.length - 1] : nos[0]
}

/** 横向滚动条定位到当前选中日（默认当天），避免内容已是当天但滚动条还停在第一天 */
function scrollDayChipIntoView(behavior = 'smooth') {
  const scroller = dayScrollerEl.value
  if (!scroller || selectedDayNo.value == null) return
  const chip = scroller.querySelector(`[data-day-no="${selectedDayNo.value}"]`)
  if (!chip) return
  // 优先居中，让老师一眼看到当前日前后几天
  const scrollerRect = scroller.getBoundingClientRect()
  const chipRect = chip.getBoundingClientRect()
  const delta =
    chipRect.left - scrollerRect.left - (scrollerRect.width / 2 - chipRect.width / 2)
  const nextLeft = scroller.scrollLeft + delta
  if (typeof scroller.scrollTo === 'function') {
    scroller.scrollTo({ left: nextLeft, behavior })
  } else {
    scroller.scrollLeft = nextLeft
  }
}
const taskCount = computed(() => {
  const reqs = selectedDay.value?.requirements
  return Array.isArray(reqs) && reqs.length ? reqs.length : 1
})

const people = computed(() => {
  const dayNo = Number(selectedDayNo.value)
  return (progress.value || []).map((member) => {
    const dayState = (member.days || []).find((d) => Number(d.dayNo) === dayNo) || {}
    const submissionId = dayState.submissionId || null
    const rawStatus = dayState.status || 'NOT_SUBMITTED'
    const upper = String(rawStatus).toUpperCase()
    const hasSubmission =
      Boolean(submissionId) || !['NOT_SUBMITTED', 'EXPIRED'].includes(upper)
    const mapped = mapMark(rawStatus, hasSubmission)
    const queueRow = submissionId ? queueBySubmission.value.get(Number(submissionId)) : null
    const versionNo = dayState.versionNo || queueRow?.versionNo
    return {
      key: `${member.userId}-${dayNo}`,
      userId: member.userId,
      name: member.username || member.name || `用户${member.userId}`,
      role: member.positionName || anyRoleLabel(member.roleInTeam || member.systemRole) || '成员',
      hasSubmission,
      submissionId: submissionId || queueRow?.submissionId || null,
      rawStatus,
      mark: mapped.mark,
      markLabel: mapped.label,
      time: formatDateTime(dayState.submittedAt || queueRow?.submittedAt),
      versionLabel: versionNo != null ? `第 ${versionNo} 版` : hasSubmission ? '已交' : '',
      note: personNote(mapped.mark, hasSubmission, upper),
      sort: markSort(mapped.mark, hasSubmission),
    }
  })
})

const stats = computed(() => {
  const list = people.value
  return {
    pending: list.filter((p) => p.mark === 'pending' || p.mark === 'reviewing').length,
    missing: list.filter((p) => !p.hasSubmission).length,
    recheck: list.filter((p) => p.mark === 'recheck').length,
    reviewed: list.filter((p) => p.mark === 'reviewed').length,
    submitted: list.filter((p) => p.hasSubmission).length,
  }
})

const visible = computed(() => {
  const q = keyword.value.toLowerCase()
  return people.value
    .filter((person) => {
      if (quickFilter.value === 'pending' && !(person.mark === 'pending' || person.mark === 'reviewing')) {
        return false
      }
      if (quickFilter.value === 'missing' && person.hasSubmission) return false
      if (quickFilter.value === 'recheck' && person.mark !== 'recheck') return false
      if (quickFilter.value === 'reviewed' && person.mark !== 'reviewed') return false
      if (!q) return true
      return `${person.name} ${person.role}`.toLowerCase().includes(q)
    })
    .slice()
    .sort((a, b) => a.sort - b.sort || String(a.name).localeCompare(String(b.name), 'zh'))
})

const missingCount = computed(() => stats.value.missing)

const listTitle = computed(() => {
  return (
    {
      pending: '待我批改',
      missing: '未提交学生',
      recheck: '需修改（待学生重交或复核）',
      reviewed: '已通过',
      all: '全部成员',
    }[quickFilter.value] || '学生提交'
  )
})

const emptyTitle = computed(() => {
  if (keyword.value) return '没有匹配的学生'
  return (
    {
      pending: '当前没有待批改',
      missing: '该日所有人都已提交',
      recheck: '没有需修改的记录',
      reviewed: '还没有已通过的提交',
      all: '暂无成员',
    }[quickFilter.value] || '暂无数据'
  )
})

const emptyHint = computed(() => {
  if (keyword.value) return '试试清空搜索，或换一个训练日。'
  return (
    {
      pending: '可以看看「未提交」是否需要提醒，或切换到其他训练日。',
      missing: '真棒。可以去处理待批改，或查看已通过记录。',
      recheck: '学生按你的反馈重交后会出现在待批改里。',
      reviewed: '批改通过后会出现在这里。',
      all: '确认项目团队是否已添加学生成员。',
    }[quickFilter.value] || ''
  )
})

const detailAssets = computed(() => {
  if (!detail.value) return []
  if (Array.isArray(detail.value.assets) && detail.value.assets.length) return detail.value.assets
  if (detail.value.attachmentUrl) {
    return [
      {
        fileName: detail.value.attachmentName || '附件',
        fileUrl: detail.value.attachmentUrl,
      },
    ]
  }
  return []
})

const requirements = computed(() => {
  const list = detail.value?.requirements
  return Array.isArray(list) ? list : []
})

const historyRows = computed(() => {
  const list = detail.value?.history
  return Array.isArray(list) ? list.slice(0, 6) : []
})

const previousComment = computed(() => {
  const hist = historyRows.value
  const withComment = hist.find((h) => h.reviewComment && Number(h.submissionId) !== Number(detail.value?.submissionId || detail.value?.id))
  return withComment?.reviewComment || ''
})

const canReviewActive = computed(() => {
  if (!detail.value || !active.value) return false
  if (detail.value.canReview === true) return true
  if (detail.value.canReview === false) return false
  return ['pending', 'reviewing', 'recheck'].includes(active.value.mark) && !!active.value.submissionId
})

function toggleQuick(key) {
  quickFilter.value = quickFilter.value === key && key !== 'all' ? 'all' : key
}

function personNote(mark, hasSubmission, upper) {
  if (!hasSubmission) {
    return upper === 'EXPIRED' ? '已过截止仍未交' : '尚未提交，可提醒'
  }
  if (mark === 'pending' || mark === 'reviewing') return '等你批改'
  if (mark === 'recheck') return '已打回，等待学生修改'
  if (mark === 'reviewed') return '已通过'
  return submissionStatusLabel(upper)
}

function markSort(mark, hasSubmission) {
  if (mark === 'pending' || mark === 'reviewing') return 0
  if (mark === 'recheck') return 1
  if (!hasSubmission) return 2
  if (mark === 'reviewed') return 3
  return 4
}

function mapMark(rawStatus, hasSubmission) {
  const s = String(rawStatus || '').toUpperCase()
  if (!hasSubmission || s === 'NOT_SUBMITTED' || s === 'EXPIRED') {
    return { mark: 'none', label: '—' }
  }
  if (s === 'PENDING_REVIEW') return { mark: 'pending', label: '待批改' }
  if (s === 'REVIEWING') return { mark: 'reviewing', label: '批改中' }
  if (s === 'CHANGES_REQUESTED') return { mark: 'recheck', label: '需修改' }
  if (s === 'APPROVED') return { mark: 'reviewed', label: '已通过' }
  return { mark: 'pending', label: submissionStatusLabel(s) }
}

function actionLabel(person) {
  if (person.mark === 'reviewed') return '查看'
  if (person.mark === 'reviewing') return '继续批改'
  if (person.mark === 'recheck') return '查看 / 复核'
  return '开始批改'
}

function markTone(mark) {
  if (mark === 'reviewed') return 'ok'
  if (mark === 'pending' || mark === 'reviewing' || mark === 'recheck') return 'warn'
  if (mark === 'none') return 'muted'
  return 'muted'
}

function statusLabel(status) {
  const s = String(status || '').toUpperCase()
  if (['DRAFT', 'PUBLISHED', 'CLOSED'].includes(s)) return dayStatusLabel(status)
  return submissionStatusLabel(status)
}

function formatDate(value) {
  return value ? String(value).slice(0, 10) : '—'
}

function formatDateTime(value) {
  return value ? String(value).replace('T', ' ').slice(0, 16) : '—'
}

function initial(name) {
  const s = String(name || '').trim()
  return s ? s.slice(0, 1) : '?'
}

function avatarColor(seed) {
  const s = String(seed ?? '')
  let hash = 0
  for (let i = 0; i < s.length; i += 1) hash = (hash * 31 + s.charCodeAt(i)) >>> 0
  return AVATAR_COLORS[hash % AVATAR_COLORS.length]
}

async function remindOne(person) {
  if (!person?.userId) return
  reminding.value = true
  bannerError.value = false
  try {
    const res = await sendTeacherReminder({
      targetType: 'USER',
      targetId: person.userId,
      message: `请尽快提交第 ${selectedDayNo.value} 天训练任务「${selectedDay.value?.title || ''}」。`,
    })
    banner.value = `已提醒 ${person.name}${res?.recipientCount != null ? `（触达 ${res.recipientCount} 人）` : ''}`
  } catch (err) {
    bannerError.value = true
    banner.value = err?.response?.data?.message || err?.message || '提醒失败'
  } finally {
    reminding.value = false
  }
}

async function remindMissing() {
  if (!camp.value.campId) return
  reminding.value = true
  bannerError.value = false
  try {
    const res = await sendTeacherReminder({
      targetType: 'TRAINING_CAMP',
      targetId: camp.value.campId,
      message: `第 ${selectedDayNo.value} 天训练任务尚未提交，请尽快完成。`,
    })
    banner.value = `已向未交学生发送提醒（触达 ${res?.recipientCount ?? 0} 人）`
  } catch (err) {
    bannerError.value = true
    banner.value = err?.response?.data?.message || err?.message || '提醒失败'
  } finally {
    reminding.value = false
  }
}

async function openReview(person) {
  active.value = person
  detail.value = null
  detailLoading.value = true
  done.value = ''
  comment.value = ''
  result.value = person.mark === 'recheck' ? 'revise' : 'pass'
  try {
    if (!person.submissionId) throw new Error('缺少提交记录')
    detail.value = await fetchTeacherSubmission(person.submissionId)
  } catch (err) {
    bannerError.value = true
    banner.value = err?.response?.data?.message || err?.message || '提交详情加载失败'
    active.value = null
  } finally {
    detailLoading.value = false
  }
}

function closeDrawer() {
  active.value = null
  detail.value = null
  done.value = ''
}

async function submitReview() {
  if (!active.value?.submissionId) return
  if (result.value === 'revise' && !comment.value.trim()) {
    bannerError.value = true
    banner.value = '打回重交时请填写反馈，方便学生修改'
    return
  }
  submitting.value = true
  try {
    await reviewSubmission(active.value.submissionId, {
      result: result.value,
      status: result.value === 'pass' ? 'APPROVED' : 'CHANGES_REQUESTED',
      reviewComment: comment.value,
    })
    done.value = result.value === 'pass' ? '已通过，学生端已同步' : '已打回，学生会收到修改要求'
    await load()
    setTimeout(closeDrawer, 700)
  } catch (err) {
    bannerError.value = true
    banner.value = err?.response?.data?.message || err?.message || '批改提交失败'
  } finally {
    submitting.value = false
  }
}

async function load() {
  loading.value = true
  banner.value = ''
  bannerError.value = false
  try {
    const contextCampId = ctx.campId || ''
    const [campRes, queue] = await Promise.all([
      fetchTeacherCamp(contextCampId),
      fetchTeacherReviewQueue().catch(() => []),
    ])
    hasCamp.value = Boolean(campRes?.hasCamp)
    camp.value = campRes?.camp || {}
    days.value = campRes?.days || []
    progress.value = campRes?.progress || []
    const map = new Map()
    ;(queue || []).forEach((row) => {
      if (row.submissionId != null) map.set(Number(row.submissionId), row)
    })
    queueBySubmission.value = map

    const resolvedCampId = camp.value.campId ?? campRes?.camp?.campId ?? contextCampId ?? null
    const campChanged = boundCampId.value !== resolvedCampId
    const selectedMissing = !days.value.some(
      (d) => Number(d.dayNo) === Number(selectedDayNo.value)
    )
    // 首次进入或切换训练营：默认当天；批改后刷新保留当前选中日
    if (campChanged || selectedMissing || selectedDayNo.value == null) {
      selectedDayNo.value = resolveDefaultDayNo()
      boundCampId.value = resolvedCampId
    }
  } catch (err) {
    hasCamp.value = false
    camp.value = {}
    days.value = []
    progress.value = []
    queueBySubmission.value = new Map()
    bannerError.value = true
    banner.value = err?.response?.data?.message || err?.message || '提交与批改数据加载失败'
  } finally {
    loading.value = false
    // 列表渲染后再滚到选中日（当天）
    await nextTick()
    scrollDayChipIntoView('auto')
  }
}

watch(
  () => [ctx.campId, ctx.projectId],
  () => {
    load()
  },
  { immediate: true }
)

// 换训练日时：清空搜索，并滚到对应 chip
watch(selectedDayNo, async () => {
  keyword.value = ''
  await nextTick()
  scrollDayChipIntoView('smooth')
})
</script>

<style scoped>
.review-banner {
  margin: 0 0 14px;
  padding: 11px 14px;
  border-radius: 11px;
  color: #0b7753;
  background: #e5f6ef;
  font-size: 12px;
  font-weight: 700;
}
.review-banner.is-error {
  color: #a33a24;
  background: #fff0ec;
}

.review-empty {
  text-align: center;
  padding: 48px 24px;
  display: grid;
  gap: 10px;
  justify-items: center;
}
.review-empty strong {
  font-size: 16px;
}
.review-empty p {
  margin: 0;
  color: var(--ds-muted);
  font-size: 13px;
}

/* 训练日条 */
.review-days {
  padding: 16px 18px 14px;
  margin-bottom: 14px;
}
.review-days__head {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: flex-start;
  margin-bottom: 12px;
}
.review-days__head strong {
  display: block;
  font-size: 15px;
}
.review-days__head small {
  display: block;
  margin-top: 4px;
  color: var(--ds-muted);
  font-size: 12px;
}
.review-days__scroller {
  display: flex;
  gap: 10px;
  overflow-x: auto;
  padding-bottom: 4px;
  scrollbar-width: thin;
}
.day-chip {
  flex: 0 0 auto;
  width: 168px;
  display: grid;
  gap: 4px;
  padding: 12px 12px 14px;
  border: 1px solid var(--ds-line);
  border-radius: 14px;
  background: #fafbfc;
  text-align: left;
  cursor: pointer;
  font: inherit;
  color: inherit;
  position: relative;
  transition: border-color 0.15s, background 0.15s, box-shadow 0.15s;
}
.day-chip:hover {
  border-color: rgba(232, 74, 28, 0.28);
  background: #fff;
}
.day-chip.is-active {
  border-color: var(--ds-orange);
  background: var(--ds-orange-wash);
  box-shadow: inset 3px 0 0 var(--ds-orange);
}
.day-chip.is-today:not(.is-active) {
  border-color: rgba(37, 99, 235, 0.28);
}
.day-chip__no {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  font-weight: 800;
  color: var(--ds-muted);
}
.day-chip__no em {
  font-style: normal;
  padding: 1px 6px;
  border-radius: 999px;
  background: #dbeafe;
  color: #1d4ed8;
  font-size: 10px;
}
.day-chip__title {
  font-size: 13px;
  line-height: 1.35;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.day-chip__meta {
  color: var(--ds-faint);
  font-size: 11px;
}
.day-chip__badge {
  position: absolute;
  top: 8px;
  right: 8px;
  min-height: 20px;
  padding: 0 7px;
  border-radius: 999px;
  background: var(--ds-orange);
  color: #fff;
  font-size: 10px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
}

/* 概况 KPI */
.review-summary {
  padding: 16px 18px 8px;
  margin-bottom: 14px;
}
.review-summary__title h2 {
  margin: 0;
  font-size: 17px;
}
.review-summary__title p {
  margin: 6px 0 0;
  color: var(--ds-muted);
  font-size: 12px;
}
.review-kpis {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 0;
  margin-top: 14px;
  border-top: 1px solid var(--ds-line);
}
.review-kpi {
  display: grid;
  gap: 4px;
  padding: 14px 12px;
  border: 0;
  border-right: 1px dashed var(--ds-line);
  background: transparent;
  text-align: left;
  cursor: pointer;
  font: inherit;
  color: inherit;
  transition: background 0.12s;
}
.review-kpi:last-child {
  border-right: 0;
}
.review-kpi:hover {
  background: rgba(15, 23, 42, 0.03);
}
.review-kpi.is-active {
  background: var(--ds-orange-wash);
}
.review-kpi small {
  color: var(--ds-muted);
  font-size: 12px;
  font-weight: 700;
}
.review-kpi strong {
  font-size: 24px;
  font-family: var(--ds-font-num);
  line-height: 1.1;
}
.review-kpi strong.is-accent {
  color: var(--ds-orange);
}
.review-kpi em {
  font-style: normal;
  color: var(--ds-faint);
  font-size: 11px;
}

/* 列表 */
.review-list-card {
  padding: 16px 18px 8px;
}
.review-list-toolbar {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 12px;
  align-items: center;
}
.review-list-toolbar strong {
  font-size: 15px;
}
.review-list-toolbar span {
  margin-left: 8px;
  color: var(--ds-muted);
  font-size: 12px;
}
.review-list-toolbar__tools input {
  min-height: 38px;
  min-width: 200px;
  padding: 0 12px;
  border: 1px solid var(--ds-line-strong);
  border-radius: 10px;
  background: #fff;
  font-size: 13px;
}
.review-table-wrap {
  overflow-x: auto;
}
.review-table th {
  white-space: nowrap;
}
.review-person {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.review-person__avatar {
  width: 32px;
  height: 32px;
  flex: none;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: #fff;
  font-size: 13px;
  font-weight: 800;
}
.review-person strong {
  display: block;
  font-size: 13px;
}
.review-person small {
  display: block;
  margin-top: 2px;
  color: var(--ds-muted);
  font-size: 12px;
}
.status-pill {
  display: inline-flex;
  min-height: 24px;
  align-items: center;
  padding: 0 9px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 750;
  background: #f1f2f4;
  color: #626974;
}
.status-pill[data-tone='ok'] {
  background: var(--ds-green-soft);
  color: var(--ds-green);
}
.status-pill[data-tone='warn'] {
  background: var(--ds-orange-wash);
  color: var(--ds-orange-deep);
}
.status-pill[data-tone='danger'] {
  background: #fff0ec;
  color: #a33a24;
}
.status-pill[data-tone='muted'] {
  background: #f1f2f4;
  color: #8b8b90;
}
.review-time-cell strong {
  display: block;
  font-size: 13px;
}
.review-time-cell small {
  display: block;
  margin-top: 2px;
  color: var(--ds-muted);
  font-size: 12px;
}
.review-note {
  color: var(--ds-muted);
  font-size: 12px;
  line-height: 1.4;
}
.review-actions {
  text-align: right;
  white-space: nowrap;
}
.review-list-empty {
  padding: 40px 16px;
  text-align: center;
  display: grid;
  gap: 8px;
  justify-items: center;
}
.review-list-empty strong {
  font-size: 15px;
}
.review-list-empty p {
  margin: 0;
  color: var(--ds-muted);
  font-size: 13px;
  max-width: 360px;
}

.review-footer-tip {
  margin: 14px 4px 0;
  color: var(--ds-faint);
  font-size: 12px;
  line-height: 1.55;
}

/* 抽屉 */
.drawer-mask {
  display: grid;
  justify-content: end;
}
.review-drawer {
  box-sizing: border-box;
  width: min(520px, 100vw);
  height: 100%;
  max-height: 100dvh;
  background: #fff;
  box-shadow: -16px 0 48px rgba(0, 0, 0, 0.18);
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.review-drawer__head {
  flex: none;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  padding: 18px 20px 14px;
  border-bottom: 1px solid var(--ds-line);
}
.review-drawer__head h2 {
  margin: 8px 0 0;
  font-size: 18px;
}
.review-drawer__head p {
  margin: 6px 0 0;
  color: var(--ds-muted);
  font-size: 12px;
}
.review-drawer__body {
  flex: 1;
  min-height: 0;
  overflow: auto;
  padding: 16px 20px 12px;
  display: grid;
  gap: 14px;
  align-content: start;
}
.drawer-section {
  padding: 14px;
  border-radius: 14px;
  border: 1px solid var(--ds-line);
  background: #fafbfc;
}
.drawer-section--soft {
  background: #f6f6f8;
}
.drawer-section--action {
  background: #fff;
  border-color: rgba(232, 74, 28, 0.22);
}
.drawer-section h3 {
  margin: 0 0 10px;
  font-size: 13px;
  font-weight: 800;
}
.drawer-content {
  margin: 0;
  font-size: 13px;
  line-height: 1.65;
  color: var(--ds-ink-2);
  white-space: pre-wrap;
}
.drawer-muted {
  margin: 8px 0 0;
  color: var(--ds-muted);
  font-size: 12px;
}
.req-list,
.history-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 8px;
}
.req-list li,
.history-list li {
  display: grid;
  gap: 2px;
  padding: 8px 10px;
  border-radius: 10px;
  background: #fff;
  border: 1px solid var(--ds-line);
}
.req-list strong,
.history-list strong {
  font-size: 13px;
}
.req-list span,
.history-list span,
.history-list em {
  font-size: 12px;
  color: var(--ds-muted);
  font-style: normal;
}
.req-list em {
  color: var(--ds-orange-deep);
  font-weight: 750;
  font-style: normal;
  font-size: 11px;
}
.asset-list {
  display: grid;
  gap: 8px;
  margin-top: 10px;
}
.asset-link {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 12px;
  border-radius: 10px;
  border: 1px solid rgba(232, 74, 28, 0.18);
  background: #fff;
  color: var(--ds-orange-deep);
  text-decoration: none;
  font-weight: 750;
  font-size: 13px;
}
.asset-link:hover {
  background: var(--ds-orange-wash);
}
.result-toggle {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 12px;
}
.result-toggle button {
  min-height: 40px;
  border: 1px solid var(--ds-line-strong);
  border-radius: 11px;
  background: #fff;
  font: 750 13px var(--ds-font-sans);
  cursor: pointer;
  color: var(--ds-ink-2);
}
.result-toggle button.is-active {
  border-color: var(--ds-orange);
  background: var(--ds-orange-wash);
  color: var(--ds-orange-deep);
}
.result-toggle button.is-active.is-warn {
  border-color: #c2410c;
  background: #fff0ec;
  color: #9a3412;
}
.field {
  display: grid;
  gap: 6px;
  font-size: 12px;
  font-weight: 700;
  color: var(--ds-muted);
}
.field i {
  font-style: normal;
  color: var(--ds-orange-deep);
  font-weight: 750;
}
.field textarea {
  border: 1px solid rgba(29, 29, 31, 0.14);
  border-radius: 12px;
  padding: 10px 12px;
  font: inherit;
  font-size: 14px;
  font-weight: 500;
  resize: vertical;
  min-height: 110px;
}
.review-drawer__foot {
  flex: none;
  padding: 12px 20px 18px;
  border-top: 1px solid var(--ds-line);
  background: #fff;
}
.review-drawer__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.review-done {
  margin: 0 0 10px;
  color: #0b7753;
  font-size: 12px;
  font-weight: 750;
}

@media (max-width: 1100px) {
  .review-kpis {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  .review-kpi:nth-child(3) {
    border-right: 0;
  }
}
@media (max-width: 720px) {
  .review-kpis {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .day-chip {
    width: 148px;
  }
  .review-drawer {
    width: 100vw;
  }
}
</style>
