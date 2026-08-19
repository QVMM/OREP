<template>
  <section class="ipp" aria-label="竞赛大脑首页演示">
    <div class="ipp-app">
      <!-- 真实侧栏：图标 + 文案，与 WorkspaceSidebar 一致 -->
      <aside class="ipp-rail" aria-label="主导航">
        <div class="ipp-rail-brand">
          <img src="/brand/competition-brain-mark.svg?v=20260723" alt="" />
        </div>
        <nav class="ipp-rail-nav">
          <button
            v-for="item in navItems"
            :key="item.key"
            type="button"
            class="ipp-rail-item"
            :class="{ 'is-active': panel === item.key }"
            :title="item.label"
            @click="setPanel(item.key)"
          >
            <span class="ipp-rail-icon" aria-hidden="true">
              <WorkspaceModuleIcon :name="item.group" variant="filled" />
            </span>
            <span>{{ item.label }}</span>
          </button>
        </nav>
      </aside>

      <div class="ipp-stage">
        <!-- 真实顶栏 -->
        <header class="ipp-topbar">
          <label class="ipp-search">
            <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="6.5"/><path d="m16 16 4 4"/></svg>
            <input v-model="search" type="search" placeholder="搜索课程、任务、文件、报告" readonly />
          </label>
          <div class="ipp-top-actions">
            <button type="button" class="ipp-icon-btn" aria-label="通知" @click="toast = '暂无新通知'">
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9a6 6 0 1 1 12 0c0 4 2 5 2 5H4s2-1 2-5"/><path d="M10 19a2 2 0 0 0 4 0"/></svg>
            </button>
            <button type="button" class="ipp-icon-btn" aria-label="帮助" @click="toast = '演示模式'">
              <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M9.5 9.5a2.5 2.5 0 1 1 3.6 2.2c-.8.4-1.1.8-1.1 1.8"/><circle cx="12" cy="17" r=".8" fill="currentColor" stroke="none"/></svg>
            </button>
            <button type="button" class="ipp-user-chip" @click="setPanel('profile')">
              <span class="ipp-user-avatar">a</span>
              <span>admin</span>
              <svg viewBox="0 0 24 24" aria-hidden="true"><path d="m8 10 4 4 4-4"/></svg>
            </button>
          </div>
        </header>

        <div class="ipp-content">
          <Transition name="ipp-fade" mode="out-in">
            <!-- 首页：对齐 StudentHome 截图 -->
            <div v-if="panel === 'home'" key="home" class="ipp-home">
              <header class="home-hero">
                <div class="home-hero__identity">
                  <div>
                    <h1>admin，今天是你备赛的第 7 天</h1>
                    <p>继续保持节奏，你今天完成的每一步，都在为赛场上的从容积累底气。</p>
                    <div class="home-hero__actions">
                      <button type="button" class="btn-primary" @click="setPanel('training')">
                        查看今日任务
                        <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>
                      </button>
                    </div>
                  </div>
                </div>
                <div class="home-countdown">
                  <span>距离备赛结束</span>
                  <strong>14<small>天</small></strong>
                  <p>8/7 结束</p>
                </div>
              </header>

              <div class="home-grid">
                <!-- 本周学习时长 -->
                <section class="home-card progress-card">
                  <div class="card-head">
                    <div class="card-title">
                      <span data-tone="training" aria-hidden="true">
                        <WorkspaceModuleIcon name="progress" variant="outline" />
                      </span>
                      <h2>本周学习时长</h2>
                    </div>
                  </div>
                  <div class="learning-duration">
                    <div class="learning-duration__summary">
                      <div>
                        <span>本周累计</span>
                        <strong>55 分</strong>
                      </div>
                      <div>
                        <span>日均时长</span>
                        <strong>15 分/天</strong>
                      </div>
                    </div>
                    <div class="learning-duration-chart" role="img" aria-label="本周学习时长柱状图">
                      <div class="learning-duration-axis" aria-hidden="true">
                        <span>30 分</span>
                        <span>15 分</span>
                        <span>0</span>
                      </div>
                      <div class="learning-duration-grid">
                        <i class="gridline is-top" aria-hidden="true" />
                        <i class="gridline is-middle" aria-hidden="true" />
                        <i class="gridline is-bottom" aria-hidden="true" />
                        <div
                          v-for="d in weekBars"
                          :key="d.day"
                          class="bar-point"
                          :class="{ 'is-today': d.today, 'is-future': d.future }"
                          :style="{ '--bar-ratio': barsReady ? d.ratio : 0 }"
                          @click="selectBar(d)"
                        >
                          <span class="bar-value">{{ d.label }}</span>
                          <div class="bar-plot" aria-hidden="true"><i /></div>
                          <strong>{{ d.weekday }}</strong>
                          <small>{{ d.date }}</small>
                        </div>
                      </div>
                    </div>
                  </div>
                </section>

                <!-- 今天练什么 -->
                <section class="home-card today-card">
                  <div class="card-head">
                    <div class="card-title">
                      <span data-tone="learning" aria-hidden="true">
                        <WorkspaceModuleIcon name="learning" variant="outline" />
                      </span>
                      <h2>今天练什么</h2>
                    </div>
                  </div>
                  <h3>阶段成果封包与复盘</h3>
                  <p class="today-summary">整理第一周成果、问题清单和下一周改进重点。</p>
                   <div class="today-meta">
                    <div>
                      <span>截止</span>
                      <strong>7/24 22:00</strong>
                    </div>
                    <div>
                      <span>小队</span>
                      <strong>user01、user02 · 5人</strong>
                    </div>
                   </div>
                   <ol class="today-requirements">
                     <li><span>必交</span><strong>第一周成果封包与问题清单</strong></li>
                   </ol>
                   <div class="today-actions">
                    <button type="button" class="btn-primary" @click="toast = '演示：进入今日训练'">
                      去完成
                      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>
                    </button>
                   </div>
                </section>

                <!-- 下场路演 -->
                <section class="home-card roadshow-card">
                  <div class="card-head">
                    <div class="card-title">
                      <span data-tone="roadshow" aria-hidden="true">
                        <WorkspaceModuleIcon name="roadshow" variant="outline" />
                      </span>
                      <h2>下场路演</h2>
                    </div>
                    <small class="roadshow-chip">本周 1 场</small>
                  </div>
                  <div class="roadshow-body">
                    <div class="roadshow-panel" data-tone="improve">
                      <span class="roadshow-panel__badge">待改进</span>
                      <strong>开场 30 秒再压一遍</strong>
                      <p>最近 61.0 分 · 改一处后再录一轮，对比更明显。</p>
                    </div>
                    <ol class="roadshow-steps" aria-hidden="true">
                      <li class="is-done"><span class="roadshow-steps__mark">✓</span><em>准备</em></li>
                      <li class="is-done"><span class="roadshow-steps__mark">✓</span><em>练习</em></li>
                      <li class="is-current"><span class="roadshow-steps__mark">3</span><em>改进</em></li>
                    </ol>
                  </div>
                  <div class="roadshow-card__actions has-secondary">
                    <button type="button" class="btn-primary roadshow-cta" @click="setPanel('roadshow')">
                      按建议再练一场
                      <svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>
                    </button>
                    <button type="button" class="btn-secondary roadshow-cta-secondary" @click="setPanel('review')">
                      查看报告
                    </button>
                  </div>
                </section>

                <!-- AI 路演评分 -->
                <section class="home-card score-card">
                  <div class="card-head">
                    <div class="card-title">
                      <span data-tone="review" aria-hidden="true">
                        <WorkspaceModuleIcon name="review" variant="outline" />
                      </span>
                      <h2>AI 路演评分</h2>
                    </div>
                  </div>
                  <div class="score-summary">
                    <div>
                      <strong :class="{ 'is-pop': scorePop }">55.2</strong><span>/100</span>
                      <p>重点改进</p>
                    </div>
                    <p class="score-tip">AI 演示环节出现 94 秒严重故障冷场，破坏讲解连贯性和专业性。</p>
                  </div>
                  <div class="score-dimensions">
                    <div v-for="d in scoreDims" :key="d.label">
                      <span>{{ d.label }}</span>
                      <strong>{{ d.value }}</strong>
                    </div>
                  </div>
                  <button type="button" class="btn-secondary score-cta" @click="setPanel('review')">
                    查看 AI 评分与建议
                  </button>
                </section>
              </div>
            </div>

            <!-- 其他导航：真实模块占位页 -->
            <div v-else :key="panel" class="ipp-module">
              <header class="module-hero">
                <div>
                  <p>{{ currentNav.label }}</p>
                  <h2>{{ moduleCopy.title }}</h2>
                  <span>{{ moduleCopy.desc }}</span>
                </div>
                <button type="button" class="btn-primary" @click="setPanel('home')">返回首页</button>
              </header>
              <div class="module-grid">
                <article
                  v-for="card in moduleCopy.cards"
                  :key="card.title"
                  class="module-card"
                  @click="toast = `演示：${card.title}`"
                >
                  <span>{{ card.badge }}</span>
                  <strong>{{ card.title }}</strong>
                  <p>{{ card.desc }}</p>
                  <em>{{ card.meta }}</em>
                </article>
              </div>
            </div>
          </Transition>
        </div>
      </div>
    </div>

    <p class="ipp-caption">
      演示界面对齐真实学生端首页 · 可点击侧栏与卡片
      <span v-if="toast" class="ipp-toast">{{ toast }}</span>
    </p>
  </section>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { OREP_NAV_ITEMS } from '../../composables/apple/useOrepNavigation'
import WorkspaceModuleIcon from '../workspace/WorkspaceModuleIcon.vue'

const panel = ref('home')
const search = ref('')
const barsReady = ref(false)
const scorePop = ref(false)
const toast = ref('')
let toastTimer

const navItems = OREP_NAV_ITEMS.map((item) => ({
  key: item.group,
  label: item.label,
  group: item.group,
}))

// 对齐真实首页示意：周一空、周二 3 分、周三四有柱、周五今天橙色、周末未到
const weekBars = [
  { day: 'mon', weekday: '一', date: '7/20', label: '0 分', ratio: 0.02, minutes: 0 },
  { day: 'tue', weekday: '二', date: '7/21', label: '3 分', ratio: 0.22, minutes: 3 },
  { day: 'wed', weekday: '三', date: '7/22', label: '12 分', ratio: 0.38, minutes: 12 },
  { day: 'thu', weekday: '四', date: '7/23', label: '16 分', ratio: 0.55, minutes: 16 },
  { day: 'fri', weekday: '五', date: '7/24', label: '0 分', ratio: 0.4, minutes: 12, today: true },
  { day: 'sat', weekday: '六', date: '7/25', label: '未到', ratio: 0, minutes: 0, future: true },
  { day: 'sun', weekday: '日', date: '7/26', label: '未到', ratio: 0, minutes: 0, future: true },
]

const scoreDims = [
  { label: '技能水平', value: '33 / 60' },
  { label: '职业素养', value: '6.6 / 10' },
  { label: '应用价值', value: '5.6 / 10' },
  { label: '团队协作', value: '5 / 10' },
  { label: '创新能力', value: '5 / 10' },
]

const currentNav = computed(() => navItems.find((n) => n.key === panel.value) || navItems[0])

const modulePages = {
  training: {
    title: '训练营',
    desc: '按日开放训练任务与学习资源，跟项目短板走。',
    cards: [
      { badge: '今天', title: '阶段成果封包与复盘', desc: '截止 7/24 22:00', meta: '去完成' },
      { badge: 'Day 8', title: '用户验证材料整理', desc: '待开放', meta: '查看计划' },
      { badge: '课程', title: '路演表达专题', desc: '进度 60%', meta: '继续学' },
    ],
  },
  roadshow: {
    title: '路演训练',
    desc: '反复练习、录制回放与视频上传评分。',
    cards: [
      { badge: '路演', title: '周五彩排场', desc: '14:00 · 可加入', meta: '进入路演' },
      { badge: '回放', title: '周五彩排回放', desc: '已转写', meta: '回看' },
      { badge: '上传', title: '视频评分', desc: '支持 mp4', meta: '去评分' },
    ],
  },
  review: {
    title: '复盘',
    desc: '评分报告、改进建议与维度证据。',
    cards: [
      { badge: '61.0', title: '最新 AI 评分', desc: '重点改进：操作规范', meta: '看报告' },
      { badge: '待办', title: '6 条改进建议', desc: '2 条高优先', meta: '处理' },
      { badge: '趋势', title: '近 5 轮得分', desc: '示意数据', meta: '对比' },
    ],
  },
  collaboration: {
    title: '协作',
    desc: '任务管理、团队成员与资源中心。',
    cards: [
      { badge: '任务', title: '2 项待处理', desc: '训练营 + 整改', meta: '任务管理' },
      { badge: '文件', title: '项目材料库', desc: 'PPT / 讲稿 / 证据', meta: '资源中心' },
      { badge: '成员', title: '5 人小队', desc: 'user01、user02…', meta: '查看' },
    ],
  },
  profile: {
    title: '我的',
    desc: '学习时长、奖状与整改记录。',
    cards: [
      { badge: '时长', title: '本周 55 分钟', desc: '日均 15 分', meta: '学习记录' },
      { badge: '奖状', title: '我的奖状', desc: '个人 / 团队荣誉', meta: '查看' },
      { badge: '账号', title: 'admin', desc: '学生端', meta: '资料' },
    ],
  },
}

const moduleCopy = computed(() => modulePages[panel.value] || modulePages.training)

function setPanel(key) {
  panel.value = key
  if (key === 'home') nextTick(triggerBars)
  if (key === 'review' || key === 'home') nextTick(() => {
    scorePop.value = false
    requestAnimationFrame(() => { scorePop.value = true })
  })
}

function selectBar(d) {
  if (d.future) {
    showToast('未到日期')
    return
  }
  showToast(`${d.weekday} ${d.date} · ${d.minutes || d.label}`)
}

function showToast(msg) {
  toast.value = msg
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => { toast.value = '' }, 1600)
}

function triggerBars() {
  barsReady.value = false
  requestAnimationFrame(() => {
    requestAnimationFrame(() => { barsReady.value = true })
  })
}

watch(panel, (key) => {
  if (key === 'home') triggerBars()
})

onMounted(() => {
  triggerBars()
  scorePop.value = true
})

onUnmounted(() => clearTimeout(toastTimer))
</script>

<style scoped>
.ipp {
  --orange: #e84a1c;
  --orange-btn: #d94a1f;
  --ink: #12141a;
  --muted: #6f7684;
  --faint: #9aa1ad;
  --line: rgba(18, 20, 26, 0.08);
  --surface: #ffffff;
  --canvas: #f3f4f7;
  --home-card-padding: 16px;
  --home-card-gap: 14px;
  --home-content-gap: 10px;
  --home-action-gap: 14px;
  width: min(1180px, calc(100% - 28px));
  margin: 12px auto 0;
  border-radius: 22px;
  overflow: hidden;
  border: 1px solid rgba(18, 20, 26, 0.06);
  background: var(--canvas);
  box-shadow:
    0 36px 90px rgba(29, 42, 57, 0.14),
    0 8px 24px rgba(29, 42, 57, 0.06);
}

.ipp-app {
  display: grid;
  grid-template-columns: 76px minmax(0, 1fr);
  min-height: clamp(640px, 72vw, 860px);
  height: auto;
  background:
    radial-gradient(circle at 70% 0%, rgba(255, 255, 255, 0.9), transparent 40%),
    linear-gradient(180deg, #f7f8fb 0%, #eef0f4 100%);
}

/* ---- Rail (match real collapsed sidebar) ---- */
.ipp-rail {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 10px 8px 16px;
  background: rgba(255, 255, 255, 0.94);
  border-right: 1px solid rgba(29, 29, 31, 0.08);
  backdrop-filter: blur(20px);
}

.ipp-rail-brand {
  width: 100%;
  height: 56px;
  display: grid;
  place-items: center;
  margin-bottom: 8px;
}

.ipp-rail-brand img {
  width: 40px;
  height: 40px;
  display: block;
  object-fit: contain;
}

.ipp-rail-nav {
  width: 100%;
  display: grid;
  gap: 6px;
}

.ipp-rail-item {
  width: 100%;
  min-height: 52px;
  padding: 6px 4px;
  border: 0;
  border-radius: 14px;
  background: transparent;
  color: #6b7280;
  display: grid;
  justify-items: center;
  gap: 2px;
  font-size: 10px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease, transform 0.15s ease;
}

.ipp-rail-item:hover {
  background: rgba(232, 74, 28, 0.06);
  color: var(--ink);
}

.ipp-rail-item.is-active {
  color: var(--orange);
  background: #fff1eb;
  box-shadow: inset 0 0 0 1px rgba(232, 74, 28, 0.08);
}

.ipp-rail-icon {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  border-radius: 10px;
  color: inherit;
}

.ipp-rail-icon :deep(svg) {
  width: 18px;
  height: 18px;
}

.ipp-rail-item.is-active .ipp-rail-icon {
  color: var(--orange);
  background: rgba(255, 255, 255, 0.7);
}

/* ---- Stage ---- */
.ipp-stage {
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.ipp-topbar {
  height: 64px;
  padding: 0 20px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  background: transparent;
}

.ipp-search {
  flex: 1;
  max-width: 420px;
  height: 40px;
  padding: 0 14px;
  display: flex;
  align-items: center;
  gap: 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
  border: 1px solid rgba(18, 20, 26, 0.06);
  box-shadow: 0 2px 8px rgba(18, 20, 26, 0.04);
}

.ipp-search svg {
  width: 16px;
  height: 16px;
  fill: none;
  stroke: #9aa1ad;
  stroke-width: 1.7;
  flex: 0 0 auto;
}

.ipp-search input {
  width: 100%;
  border: 0;
  outline: none;
  background: transparent;
  color: var(--ink);
  font-size: 13px;
}

.ipp-search input::placeholder { color: #9aa1ad; }

.ipp-top-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ipp-icon-btn {
  width: 36px;
  height: 36px;
  border: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.8);
  color: #667085;
  display: grid;
  place-items: center;
  cursor: pointer;
}

.ipp-icon-btn svg {
  width: 18px;
  height: 18px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.7;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.ipp-user-chip {
  height: 36px;
  padding: 0 10px 0 4px;
  border: 0;
  border-radius: 999px;
  background: #fff;
  display: inline-flex;
  align-items: center;
  gap: 8px;
  color: var(--ink);
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(18, 20, 26, 0.05);
}

.ipp-user-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  color: #fff;
  background: var(--orange);
  font-size: 12px;
  font-weight: 800;
}

.ipp-user-chip svg {
  width: 14px;
  height: 14px;
  fill: none;
  stroke: #98a2b3;
  stroke-width: 1.8;
}

.ipp-content {
  flex: 1;
  min-height: 0;
  padding: 0 18px 18px;
  overflow: visible;
  display: flex;
  flex-direction: column;
}

/* ---- Home layout matching StudentHome ---- */
.ipp-home {
  display: flex;
  flex-direction: column;
  gap: var(--home-card-gap);
  flex: 1 1 auto;
  min-height: 0;
  width: 100%;
}

.home-hero {
  flex: 0 0 auto;
  min-height: 0;
  padding: 18px 22px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 20px;
  border-radius: 18px;
  background: var(--surface);
  box-shadow: 2px 4px 12px rgba(18, 20, 26, 0.08);
}

.home-hero h1 {
  margin: 0 !important;
  color: var(--ink) !important;
  font-size: 22px !important;
  font-weight: 800 !important;
  letter-spacing: -0.03em !important;
  line-height: 1.25 !important;
}

.home-grid {
  flex: 1 1 auto;
  min-height: 0;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  grid-template-rows: repeat(2, minmax(230px, auto));
  gap: var(--home-card-gap);
}

.home-hero__identity p {
  margin: 8px 0 0 !important;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.5;
  max-width: 36em;
}

.home-hero__actions {
  margin-top: 14px;
}

.home-countdown {
  min-width: 150px;
  padding-left: 20px;
  border-left: 1px solid var(--line);
  text-align: left;
}

.home-countdown > span,
.home-countdown p {
  margin: 0;
  color: var(--muted);
  font-size: 12px;
  font-weight: 600;
}

.home-countdown strong {
  display: block;
  margin: 6px 0 4px;
  color: var(--orange);
  font-size: 40px;
  font-weight: 800;
  letter-spacing: -0.04em;
  line-height: 1;
  font-variant-numeric: tabular-nums;
}

.home-countdown strong small {
  margin-left: 4px;
  color: var(--muted);
  font-size: 13px;
  font-weight: 700;
}

.progress-card { grid-column: 1; grid-row: 1; }
.today-card { grid-column: 2; grid-row: 1; }
.roadshow-card { grid-column: 1; grid-row: 2; }
.score-card { grid-column: 2; grid-row: 2; }

.home-card {
  min-width: 0;
  min-height: 0;
  padding: var(--home-card-padding);
  border-radius: 18px;
  background: var(--surface);
  box-shadow: 2px 4px 12px rgba(18, 20, 26, 0.08);
  display: flex;
  flex-direction: column;
  gap: var(--home-content-gap);
}

.card-head { min-height: 28px; }
.card-title {
  display: flex;
  align-items: center;
  gap: 10px;
}
.card-title > span {
  width: 28px;
  height: 28px;
  border-radius: 9px;
  display: grid;
  place-items: center;
}
.card-title > span[data-tone="training"] { color: #e84a1c; background: #fff1eb; }
.card-title > span[data-tone="learning"] { color: #3b82f6; background: #eff6ff; }
.card-title > span[data-tone="roadshow"] { color: #8b5cf6; background: #f5f3ff; }
.card-title > span[data-tone="review"] { color: #0d9488; background: #f0fdfa; }
.card-title > span :deep(svg) { width: 15px; height: 15px; }
.card-title h2 {
  margin: 0;
  color: var(--ink);
  font-size: 15px;
  font-weight: 800;
}

/* Learning chart */
.learning-duration {
  flex: 1;
  min-height: 0;
  display: grid;
  grid-template-rows: auto minmax(0, 1fr);
  gap: var(--home-content-gap);
}
.learning-duration__summary {
  display: flex;
  justify-content: space-between;
  gap: 12px;
}
.learning-duration__summary > div {
  display: flex;
  align-items: baseline;
  gap: 6px;
}
.learning-duration__summary span {
  color: var(--faint);
  font-size: 11px;
  font-weight: 600;
}
.learning-duration__summary strong {
  color: var(--ink);
  font-size: 13px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}
.learning-duration-chart {
  min-height: 0;
  display: grid;
  grid-template-columns: 36px minmax(0, 1fr);
  gap: 6px;
}
.learning-duration-axis {
  height: 100%;
  min-height: 110px;
  max-height: 140px;
  padding: 12px 0 26px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  align-items: flex-end;
  color: var(--faint);
  font-size: 9px;
  font-weight: 600;
}
.learning-duration-grid {
  position: relative;
  height: 100%;
  min-height: 110px;
  max-height: 140px;
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 4px;
  align-items: end;
  padding-bottom: 0;
}
.gridline {
  position: absolute;
  left: 0;
  right: 0;
  height: 1px;
  background: rgba(18, 20, 26, 0.06);
  pointer-events: none;
}
.gridline.is-top { top: 14px; }
.gridline.is-middle { top: 50%; }
.gridline.is-bottom { bottom: 30px; }

.bar-point {
  position: relative;
  z-index: 1;
  height: 100%;
  display: grid;
  grid-template-rows: 16px 1fr auto auto;
  justify-items: center;
  gap: 2px;
  padding-top: 0;
  border: 0;
  background: transparent;
  cursor: pointer;
}
.bar-value {
  color: var(--faint);
  font-size: 9px;
  font-weight: 700;
  white-space: nowrap;
}
.bar-point.is-today .bar-value { color: var(--orange); }
.bar-plot {
  width: 100%;
  min-height: 0;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  padding-bottom: 2px;
}
.bar-plot i {
  width: 18px;
  max-width: 70%;
  height: calc(var(--bar-ratio) * 100px);
  min-height: 0;
  border-radius: 6px 6px 4px 4px;
  background: #c5cad3;
  transition: height 0.65s cubic-bezier(0.22, 1, 0.36, 1);
}
.bar-point.is-today .bar-plot i {
  background: linear-gradient(180deg, #f0733d, var(--orange));
}
.bar-point.is-future .bar-plot i {
  background: #e8eaee;
  min-height: 4px;
  height: 4px;
}
.bar-point strong {
  color: var(--ink);
  font-size: 11px;
  font-weight: 800;
}
.bar-point.is-today strong { color: var(--orange); }
.bar-point small {
  color: var(--faint);
  font-size: 9px;
}

/* Today card */
.today-card h3 {
  margin: 0;
  color: var(--ink);
  font-size: 18px;
  font-weight: 800;
  letter-spacing: -0.02em;
  line-height: 1.3;
}
.today-summary {
  margin: 0;
  color: var(--muted);
  font-size: 13px;
  line-height: 1.55;
}
.today-meta {
  margin-top: 0;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.today-meta > div {
  padding: 10px 12px;
  border-radius: 12px;
  background: #f6f7f9;
}
.today-meta span {
  display: block;
  color: var(--faint);
  font-size: 11px;
  font-weight: 600;
}
.today-meta strong {
  display: block;
  margin-top: 4px;
  color: var(--ink);
  font-size: 13px;
  font-weight: 750;
}
.today-actions {
  margin-top: auto;
  padding-top: var(--home-action-gap);
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}
.today-requirements {
  margin: 0;
  padding: 0;
  list-style: none;
}
.today-requirements li {
  min-height: 28px;
  display: flex;
  align-items: center;
  gap: 8px;
  border-bottom: 1px solid var(--line);
  color: var(--ink);
  font-size: 11px;
}
.today-requirements li span {
  padding: 2px 7px;
  border-radius: 999px;
  color: #b93613;
  background: #fff0e9;
  font-weight: 800;
}
.today-requirements li strong { font-weight: 700; }

/* 下场路演 focus card */
.roadshow-card {
  display: flex;
  flex-direction: column;
}
.roadshow-chip {
  padding: 4px 9px;
  border-radius: 999px;
  color: var(--muted);
  background: #f3f4f6;
  font-size: 10px;
  font-weight: 750;
}
.roadshow-body {
  flex: 1;
  margin-top: 0;
  display: flex;
  flex-direction: column;
  gap: var(--home-content-gap);
}
.roadshow-panel {
  min-height: 96px;
  padding: 12px 14px 13px;
  border-radius: 14px;
  border: 1px solid rgba(90, 70, 220, 0.12);
  background: linear-gradient(155deg, rgba(241, 239, 255, 0.98) 0%, #fff 100%);
}
.roadshow-panel__badge {
  display: inline-flex;
  margin-bottom: 7px;
  padding: 2px 8px;
  border-radius: 999px;
  color: #4f46b8;
  background: rgba(99, 91, 220, 0.12);
  font-size: 10px;
  font-weight: 800;
}
.roadshow-panel strong {
  display: block;
  color: var(--ink);
  font-size: 15px;
  font-weight: 800;
  line-height: 1.35;
}
.roadshow-panel p {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.45;
}
.roadshow-steps {
  margin: 0;
  padding: 8px 6px 2px;
  list-style: none;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  position: relative;
}
.roadshow-steps::before {
  content: '';
  position: absolute;
  left: calc(16.66% + 10px);
  right: calc(16.66% + 10px);
  top: 19px;
  height: 2px;
  background: #e7e9ee;
}
.roadshow-steps > li {
  position: relative;
  z-index: 1;
  display: grid;
  justify-items: center;
  gap: 6px;
}
.roadshow-steps__mark {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: grid;
  place-items: center;
  border: 1.5px solid #e1e4ea;
  background: #fff;
  color: #98a2b3;
  font-size: 11px;
  font-weight: 800;
}
.roadshow-steps > li em {
  color: #98a2b3;
  font-size: 11px;
  font-style: normal;
  font-weight: 700;
}
.roadshow-steps > li.is-done .roadshow-steps__mark {
  color: #fff;
  border-color: #16a071;
  background: #16a071;
}
.roadshow-steps > li.is-done em { color: #0b7753; }
.roadshow-steps > li.is-current .roadshow-steps__mark {
  color: #fff;
  border-color: var(--orange);
  background: var(--orange);
  box-shadow: 0 0 0 4px rgba(217, 57, 20, 0.12);
}
.roadshow-steps > li.is-current em { color: var(--orange); }
.roadshow-card__actions {
  margin-top: auto;
  padding-top: var(--home-action-gap);
  display: grid;
  gap: 8px;
}
.roadshow-card__actions.has-secondary {
  grid-template-columns: 1.35fr 1fr;
}
.roadshow-cta,
.roadshow-cta-secondary {
  width: 100%;
  justify-content: center;
  min-height: 36px;
}

/* Score card */
.score-summary {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 14px;
  align-items: start;
  margin-top: 0;
}
.score-summary strong {
  color: var(--orange);
  font-size: 40px;
  font-weight: 800;
  letter-spacing: -0.04em;
  line-height: 1;
  font-variant-numeric: tabular-nums;
  transition: transform 0.25s ease;
}
.score-summary strong.is-pop {
  transform: scale(1.04);
}
.score-summary > div > span {
  margin-left: 2px;
  color: var(--faint);
  font-size: 13px;
  font-weight: 700;
}
.score-summary > div > p {
  margin: 6px 0 0;
  color: var(--muted);
  font-size: 12px;
  font-weight: 700;
}
.score-tip {
  margin: 4px 0 0;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.5;
}
.score-dimensions {
  margin-top: 0;
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 6px;
}
.score-dimensions > div {
  min-width: 0;
  text-align: center;
}
.score-dimensions span {
  display: block;
  color: var(--faint);
  font-size: 10px;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.score-dimensions strong {
  display: block;
  margin-top: 4px;
  color: var(--ink);
  font-size: 12px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}
.score-cta {
  width: 100%;
  margin-top: auto;
  justify-content: center;
}

/* Buttons */
.btn-primary,
.btn-secondary {
  min-height: 38px;
  padding: 0 16px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  font-weight: 750;
  cursor: pointer;
  border: 0;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.btn-primary:hover,
.btn-secondary:hover { transform: translateY(-1px); }
.btn-primary {
  color: #fff;
  background: linear-gradient(180deg, #e85a2f, var(--orange-btn));
  box-shadow: 0 8px 18px rgba(217, 74, 31, 0.22);
}
.btn-primary svg,
.btn-secondary svg {
  width: 15px;
  height: 15px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.9;
  stroke-linecap: round;
}
.btn-secondary {
  color: var(--ink);
  background: #fff;
  border: 1px solid rgba(18, 20, 26, 0.1);
}

/* Module pages */
.ipp-module {
  display: grid;
  gap: 14px;
}
.module-hero {
  padding: 20px 22px;
  border-radius: 18px;
  background: var(--surface);
  box-shadow: 2px 4px 12px rgba(18, 20, 26, 0.08);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}
.module-hero p {
  margin: 0;
  color: var(--orange);
  font-size: 12px;
  font-weight: 800;
}
.module-hero h2 {
  margin: 6px 0 0;
  color: var(--ink);
  font-size: 22px;
  letter-spacing: -0.03em;
}
.module-hero span {
  display: block;
  margin-top: 6px;
  color: var(--muted);
  font-size: 13px;
}
.module-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}
.module-card {
  padding: 16px;
  border-radius: 18px;
  background: var(--surface);
  box-shadow: 2px 4px 12px rgba(18, 20, 26, 0.08);
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.module-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 14px 28px rgba(18, 20, 26, 0.1);
}
.module-card > span {
  display: inline-flex;
  height: 24px;
  padding: 0 8px;
  align-items: center;
  border-radius: 999px;
  color: var(--orange);
  background: #fff1eb;
  font-size: 11px;
  font-weight: 800;
}
.module-card strong {
  display: block;
  margin-top: 12px;
  color: var(--ink);
  font-size: 15px;
}
.module-card p {
  margin: 8px 0 0;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.5;
}
.module-card em {
  display: inline-block;
  margin-top: 14px;
  color: var(--orange);
  font-size: 12px;
  font-style: normal;
  font-weight: 800;
}

.ipp-caption {
  margin: 0;
  padding: 10px 14px 12px;
  text-align: center;
  color: #8b919c;
  background: #fafbfc;
  border-top: 1px solid var(--line);
  font-size: 11px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  min-height: 38px;
}
.ipp-toast {
  padding: 4px 10px;
  border-radius: 999px;
  color: var(--orange);
  background: #fff1eb;
  font-weight: 750;
}

.ipp-fade-enter-active,
.ipp-fade-leave-active {
  transition: opacity 0.2s ease, transform 0.2s ease;
}
.ipp-fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.ipp-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}

@media (max-width: 900px) {
  .ipp-app {
    grid-template-columns: 1fr;
    height: auto;
    min-height: 520px;
    max-height: none;
  }
  .ipp-rail {
    flex-direction: row;
    overflow-x: auto;
    height: auto;
    padding: 8px;
  }
  .ipp-rail-brand { display: none; }
  .ipp-rail-nav {
    display: flex;
    gap: 4px;
  }
  .ipp-rail-item {
    min-width: 64px;
    min-height: 52px;
  }
  .ipp-home {
    height: auto;
  }
  .home-grid {
    grid-template-columns: 1fr;
    grid-template-rows: none;
  }
  .home-hero,
  .progress-card,
  .today-card,
  .roadshow-card,
  .score-card {
    grid-column: auto;
    grid-row: auto;
  }
  .module-grid { grid-template-columns: 1fr; }
  .score-dimensions { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}

@media (max-width: 1100px) and (min-width: 901px) {
  .ipp { width: min(100%, calc(100% - 20px)); }
  .ipp-app { min-height: 780px; }
  .home-grid { grid-template-rows: repeat(2, minmax(250px, auto)); }
  .score-summary { grid-template-columns: 110px 1fr; }
  .score-dimensions { grid-template-columns: repeat(3, minmax(0, 1fr)); }
}
</style>
