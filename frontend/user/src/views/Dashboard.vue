<template>
  <div
    class="home-page workspace-page"
    :class="{ 'is-home-pending': isHomePending, 'is-home-ready': isHomeReady }"
  >
    <div class="home-inner">
      <!-- 顶栏：左问候 / 右团队（右对齐） -->
      <header class="context">
        <div class="context-left">
          <h1>{{ greetingText }}，{{ displayName }}</h1>
          <div class="meta">
            <strong>{{ projectTitle }}</strong>
            <template v-if="currentStageTitle">
              <span class="sep">·</span>
              <span class="with-led">
                <i class="led" :class="stageLed" aria-hidden="true" />
                {{ currentStageTitle }}
              </span>
            </template>
            <template v-if="deadlineInfo.tone === 'warning' || deadlineInfo.tone === 'late'">
              <span class="sep">·</span>
              <span class="warn with-led">
                <i class="led led-warn" aria-hidden="true" />
                {{ deadlineInfo.text }}
              </span>
            </template>
            <template v-else-if="deadlineInfo.text && deadlineInfo.tone !== 'neutral'">
              <span class="sep">·</span>
              <span>{{ deadlineInfo.text }}</span>
            </template>
          </div>
        </div>

        <div class="context-right">
          <div v-if="memberCount" class="team-pill" title="当前项目团队">
            <div class="stack">
              <span
                v-for="m in teamPreview"
                :key="m.key"
                class="av"
                :style="{ background: m.color }"
              >{{ m.label }}</span>
            </div>
            <div class="info">
              团队 {{ memberCount }} 人
              <small>{{ teamActiveHint }}</small>
            </div>
            <button type="button" class="invite" @click="go(projectTeamPath)">邀请</button>
          </div>
          <button
            v-else
            type="button"
            class="team-empty"
            @click="go(projectTeamPath)"
          >
            组建团队
          </button>
        </div>
      </header>

      <!-- 主区：左点评 · 中五维 · 右总分 -->
      <section
        class="hero-stage neo-raised"
        :class="{ 'has-mid': showRadarMid }"
        aria-label="最新点评"
      >
        <div class="stage-left">
          <template v-if="hasScore">
            <div class="tag">
              <svg class="tag-ico" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M12 3.5 13.8 9h5.7l-4.6 3.4 1.8 5.6L12 14.8 7.3 18l1.8-5.6L4.5 9h5.7L12 3.5Z" />
              </svg>
              最新点评 · AI
            </div>
            <h2 class="judge">{{ judgmentTitle }}</h2>
            <p class="lead">{{ judgmentLead }}</p>
            <div class="next-block">
              <div class="lab with-led">
                <i class="led led-warn" aria-hidden="true" />
                下一刀 · 本周优先
              </div>
              <strong>{{ nextCut.title }}</strong>
              <p v-if="nextCut.desc">{{ nextCut.desc }}</p>
              <!--
                负责人：用姓名、不用头像。
                顶栏团队已有头像叠放；此处再摆头像会重复。
                姓名回答「谁推进」，与顶栏「谁在队里」分工。
              -->
              <div v-if="nextCutOwnerNames" class="owners-line" aria-label="负责人">
                <span class="owners-lab">负责人</span>
                <span class="owners-names">{{ nextCutOwnerNames }}</span>
              </div>
            </div>
            <!-- 操作下沉：贴近底栏，拉开与点评/下一刀的呼吸感 -->
            <div class="stage-actions acts">
              <button type="button" class="btn-text has-ico" @click="go(nextCut.path)">
                <svg class="btn-ico" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M5 12h12" />
                  <path d="m13 6 6 6-6 6" />
                </svg>
                去做下一刀
              </button>
              <button
                v-if="juryPath"
                type="button"
                class="btn-text quiet"
                @click="go(juryPath)"
              >
                多维评委
              </button>
              <button type="button" class="btn-text quiet" @click="go('/ai-score-upload')">
                再评一场
              </button>
            </div>
            <!-- 主路径入口：贴底，与「下一刀」动作区分 -->
            <div class="stage-primary-bar">
              <button type="button" class="btn-text primary has-ico" @click="go('/online-meeting')">
                <svg class="btn-ico" viewBox="0 0 24 24" aria-hidden="true">
                  <rect x="2.5" y="5" width="13.5" height="14" rx="2.2" />
                  <path d="M16 10.2 21.5 7.4v9.2L16 13.8" />
                  <circle cx="9.2" cy="11" r="1.55" fill="currentColor" stroke="none" />
                  <path d="M6.5 15.4c.45-1.15 1.35-1.75 2.7-1.75s2.25.6 2.7 1.75" />
                </svg>
                路演训练
              </button>
              <span class="stage-primary-hint">进入路演练习或正式展示</span>
            </div>
          </template>
          <!-- 冷启动：整卡柔光占位，不出现空白文案块 -->
          <template v-else-if="isHomePending">
            <div class="stage-soft-load" aria-busy="true" aria-label="首页加载中">
              <div class="soft-bar w-sm" />
              <div class="soft-bar w-lg" />
              <div class="soft-bar w-md" />
              <div class="soft-panel" />
              <div class="soft-actions">
                <span class="soft-chip" />
                <span class="soft-chip sm" />
              </div>
            </div>
          </template>
          <template v-else>
            <div class="tag">
              <svg class="tag-ico" viewBox="0 0 24 24" aria-hidden="true">
                <circle cx="12" cy="12" r="8.5" />
                <path d="M12 8v4.5l3 1.8" />
              </svg>
              怎么开始
            </div>
            <h2 class="judge">还没有本场得分。一场就够，不用准备完美。</h2>
            <p class="lead">上传路演或开演练。有了分数，后面的改法才有依据。</p>
            <ul class="empty-steps">
              <li><b>1</b><span><strong>交一场路演</strong>：视频或在线演练</span></li>
              <li><b>2</b><span><strong>出本场得分</strong>：按赛道规则</span></li>
              <li><b>3</b><span><strong>看总结、改一刀</strong>，再评</span></li>
            </ul>
            <div class="acts">
              <button type="button" class="btn-text primary has-ico" @click="go('/ai-score-upload')">
                <svg class="btn-ico" viewBox="0 0 24 24" aria-hidden="true">
                  <path d="M12 16V5" />
                  <path d="m8 8.5 4-4 4 4" />
                  <path d="M5 16.5V18a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-1.5" />
                </svg>
                开始评分
              </button>
              <button type="button" class="btn-text has-ico" @click="go('/online-meeting')">
                <svg class="btn-ico" viewBox="0 0 24 24" aria-hidden="true">
                  <rect x="2.5" y="5" width="13.5" height="14" rx="2.2" />
                  <path d="M16 10.2 21.5 7.4v9.2L16 13.8" />
                  <circle cx="9.2" cy="11" r="1.55" fill="currentColor" stroke="none" />
                  <path d="M6.5 15.4c.45-1.15 1.35-1.75 2.7-1.75s2.25.6 2.7 1.75" />
                </svg>
                路演训练
              </button>
            </div>
          </template>
        </div>

        <!-- 中栏：五维雷达，桥接左点评 / 右总分 -->
        <div
          v-if="showRadarMid"
          class="stage-mid"
          aria-label="五维评分"
        >
          <div class="radar-wrap" :class="{ 'is-live': hasScore }">
            <svg
              class="radar-svg"
              viewBox="0 0 248 248"
              role="img"
              :aria-label="hasScore ? '本场五维评分雷达图' : '五维评分占位'"
            >
              <defs>
                <linearGradient id="homeRadarFill" x1="0%" y1="0%" x2="100%" y2="100%">
                  <stop offset="0%" stop-color="rgba(232, 74, 28, 0.28)" />
                  <stop offset="100%" stop-color="rgba(232, 74, 28, 0.08)" />
                </linearGradient>
              </defs>
              <g class="radar-grid">
                <!-- 网格环 -->
                <polygon
                  v-for="(ring, i) in radarRings"
                  :key="`ring-${i}`"
                  :points="ring"
                  class="radar-ring"
                  :class="{ outer: i === radarRings.length - 1 }"
                />
                <!-- 轴线 -->
                <line
                  v-for="(axis, i) in radarAxes"
                  :key="`axis-${i}`"
                  :x1="radarCenter"
                  :y1="radarCenter"
                  :x2="axis.x"
                  :y2="axis.y"
                  class="radar-axis"
                />
              </g>
              <!-- 数据面 -->
              <polygon
                v-if="radarDataPoints"
                :points="radarDataPoints"
                class="radar-data"
              />
              <!-- 数据点 -->
              <circle
                v-for="(p, i) in radarVertices"
                :key="`pt-${i}`"
                :cx="p.x"
                :cy="p.y"
                r="3.4"
                class="radar-dot"
                :class="{ weak: p.weak }"
                :style="{ '--dot-i': i }"
              />
              <!-- 维度名 + 分数 -->
              <g
                v-for="(lab, i) in radarLabels"
                :key="`lab-${i}`"
                class="radar-label"
                :class="{ weak: lab.weak }"
              >
                <text
                  :x="lab.x"
                  :y="lab.nameY"
                  class="radar-label-name"
                  text-anchor="middle"
                  dominant-baseline="middle"
                >{{ lab.text }}</text>
                <text
                  v-if="lab.score"
                  :x="lab.x"
                  :y="lab.scoreY"
                  class="radar-label-score"
                  text-anchor="middle"
                  dominant-baseline="middle"
                >{{ lab.score }}</text>
              </g>
            </svg>
          </div>
          <p v-if="hasScore && weakestDimLabel" class="mid-hint">
            最弱 · <b>{{ weakestDimLabel.name }}</b>
            <span class="n">{{ weakestDimLabel.score }}</span>
          </p>
          <p v-else-if="!hasScore" class="mid-hint muted">出分后显示五维</p>
          <p v-else class="mid-hint muted">五维较均衡</p>
        </div>

        <aside class="stage-right" aria-label="本场得分">
          <div class="mascot-deco">
            <BrainMascot
              ref="mascotRef"
              chip-only
              :mood="mascotMood"
              :enable-look="true"
              @tap="onMascotTap"
            />
          </div>
          <template v-if="isHomePending">
            <div class="score-soft-load" aria-hidden="true">
              <div class="soft-bar w-sm center" />
              <div class="soft-score" />
              <div class="soft-bar w-xs center" />
              <div class="soft-cta" />
            </div>
          </template>
          <template v-else>
            <div class="score-lab">
              <svg class="score-lab-ico" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M4 19V5" />
                <path d="M4 19h16" />
                <path d="M8 15v-4" />
                <path d="M12 15V8" />
                <path d="M16 15v-6" />
              </svg>
              本场得分
            </div>
            <div v-if="scoreMedalTier" class="score-medal-slot">
              <ScoreMedal :tier="scoreMedalTier" />
            </div>
            <div class="big num" :class="{ ghost: !hasScore }">
              {{ scoreDisplay }}<small>/100</small>
            </div>
            <div class="level with-led">
              <i class="led" :class="scoreLevelLed" aria-hidden="true" />
              {{ scoreLevelLabel }}
            </div>
            <div v-if="hasScore" class="stage-stats">
              <div v-if="juryAverageDisplay">
                <b>{{ juryAverageDisplay }}</b>
                <span>评委均</span>
              </div>
              <div v-if="scoreDiffDisplay">
                <b :class="{ up: scoreDiffPositive }">{{ scoreDiffDisplay }}</b>
                <span>相差</span>
              </div>
              <div v-if="openTaskCount">
                <b>{{ openTaskCount }}</b>
                <span>待办</span>
              </div>
            </div>
            <p v-if="summarySyncLine" class="sync-line">{{ summarySyncLine }}</p>
            <button
              v-if="hasScore"
              type="button"
              class="btn-text primary has-ico stage-cta"
              @click="openScoreSummary"
            >
              <svg class="btn-ico" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M7 3.5h7.5L19 8v12.5H7A1.5 1.5 0 0 1 5.5 19V5A1.5 1.5 0 0 1 7 3.5Z" />
                <path d="M14.5 3.5V8H19" />
                <path d="M9 13h6M9 16.5h4" />
              </svg>
              打开评分总结
            </button>
            <button
              v-else
              type="button"
              class="btn-text primary has-ico stage-cta"
              @click="go('/ai-score-upload')"
            >
              <svg class="btn-ico" viewBox="0 0 24 24" aria-hidden="true">
                <path d="M12 16V5" />
                <path d="m8 8.5 4-4 4 4" />
                <path d="M5 16.5V18a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2v-1.5" />
              </svg>
              开始评分
            </button>
            <div class="stage-live with-led">
              <i class="led" :class="brainLiveLed" aria-hidden="true" />
              {{ hasScore ? '本场已读完' : '待命' }}
              <template v-if="scoreReadAt"> · {{ scoreReadAt }}</template>
            </div>
          </template>
        </aside>
      </section>

      <!-- 备赛脉搏：真实活动 + 动态缺项，不再展示不可解释的总体进度 -->
      <section class="readiness-pulse neo-raised home-reveal" aria-label="备赛脉搏与上场缺项" :aria-busy="isHomePending">
        <div class="pulse-side">
          <div class="pulse-head">
            <div><p class="pulse-kicker">{{ projectTitle }} · 备赛状态</p><h3>备赛脉搏</h3></div>
            <button type="button" class="pulse-link" @click="go(projectTeamPath)">查看项目</button>
          </div>
          <div class="pulse-body">
            <div class="pulse-chart" :aria-label="activityLabel">
              <strong>{{ activityLabel }}</strong>
              <svg viewBox="0 0 420 112" role="img" :aria-label="activityLabel">
                <defs><linearGradient id="pulseArea" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="rgba(232, 74, 28, .22)" /><stop offset="100%" stop-color="rgba(232, 74, 28, 0)" /></linearGradient></defs>
                <path v-if="activityAreaPath" :d="activityAreaPath" class="pulse-area" />
                <polyline :points="activityPolyline" class="pulse-line" />
                <circle v-for="point in activityChartPoints" :key="point.key" :cx="point.x" :cy="point.y" r="3.2" class="pulse-dot" />
              </svg>
              <div class="pulse-axis" aria-hidden="true"><span v-for="day in activityDays" :key="day.date">{{ day.label }}</span></div>
            </div>
            <div class="pulse-updates">
              <span class="pulse-subtitle">近期动态</span>
              <ul v-if="readinessUpdates.length">
                <li v-for="item in readinessUpdates" :key="item.key">
                  <span class="update-ico" :class="`is-${item.kind}`" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M6 3.5h8l4 4V20H6z" /><path d="M14 3.5V8h4M9 12h6M9 15.5h5" /></svg></span>
                  <span class="update-copy"><b>{{ item.title }}</b><small>{{ item.when }}</small></span>
                </li>
              </ul>
              <p v-else class="pulse-empty">最近 7 天暂无项目更新，完成任务或上传材料后会自动出现。</p>
            </div>
          </div>
        </div>
        <div class="gap-side">
          <div class="gap-head">
            <div><p class="pulse-kicker">规则、材料与路演联合判断</p><h3>上场前还缺什么</h3></div>
            <div class="deadline-chip" :class="`is-${readinessDeadline.tone}`">{{ readinessDeadline.label }}</div>
            <button v-if="readinessGaps.length" type="button" class="gap-cta" @click="go(readinessGaps[0].actionPath)">补齐材料</button>
          </div>
          <div v-if="readinessGaps.length" class="gap-list">
            <button v-for="gap in readinessGaps" :key="gap.key" type="button" class="gap-item" @click="go(gap.actionPath)">
              <i class="gap-led" :class="`is-${gap.severity}`" aria-hidden="true" />
              <span class="gap-icon" aria-hidden="true"><svg viewBox="0 0 24 24"><path d="M7 3.5h7.5L19 8v12.5H7A1.5 1.5 0 0 1 5.5 19V5A1.5 1.5 0 0 1 7 3.5Z" /><path d="M14.5 3.5V8H19M9 13h6M9 16.5h4" /></svg></span>
              <span class="gap-copy"><b>{{ gap.title }}</b><small>{{ gap.description }}</small></span>
              <svg class="gap-arrow" viewBox="0 0 24 24" aria-hidden="true"><path d="m9 5 7 7-7 7" /></svg>
            </button>
          </div>
          <div v-else class="gap-ready"><i class="led led-ok" aria-hidden="true" /><div><b>关键上场项已齐备</b><span>当前没有从材料、赛道证据或最近评分中识别到阻塞项。</span></div></div>
        </div>
      </section>

      <!-- 最近 + 怎么练 -->
      <div class="below home-reveal">
        <section class="panel is-feed neo-raised" aria-label="最近事项">
          <div class="panel-head">
            <div>
              <h3>最近发生了什么</h3>
              <p class="why">按时间回看备赛动作，方便对齐「我们刚做完什么」。</p>
            </div>
            <button type="button" class="link" @click="go(projectTeamPath)">全部</button>
          </div>
          <ul class="timeline">
            <li
              v-for="item in recentMatters"
              :key="item.key"
              :class="timelineClass(item.led)"
            >
              <div class="row-main">
                <div class="what">{{ item.title }}</div>
                <div class="when">{{ item.when }}</div>
              </div>
            </li>
          </ul>
        </section>

        <section class="panel is-practice neo-raised" aria-label="怎么练">
          <div class="panel-head">
            <div>
              <h3>分数之后，怎么练</h3>
              <p class="why">
                评分指出方向；这里把「补能力」拆成可点的路径。
                按你现在最需要的一项进。
              </p>
            </div>
          </div>
          <div class="practice-list">
            <button
              type="button"
              class="practice-item"
              :class="{ rec: hasScore && openTaskCount > 0 }"
              @click="openTodoHub"
            >
              <span class="ic" aria-hidden="true">
                <svg viewBox="0 0 24 24">
                  <path d="M9 6h11M9 12h11M9 18h11" />
                  <path d="M4.5 6.2 5.8 7.5 8 5" />
                  <path d="M4.5 12.2 5.8 13.5 8 11" />
                  <rect x="3.5" y="16.2" width="4" height="4" rx="1" />
                </svg>
              </span>
              <span class="txt">
                <strong>待办中心{{ hasScore && openTaskCount > 0 ? ' · 推荐' : '' }}</strong>
                <span>今日日报、训练与待处理事项集中在这里，清完红点再收工。</span>
              </span>
              <span class="go">去处理 →</span>
            </button>
            <button type="button" class="practice-item" @click="go('/online-meeting')">
              <span class="ic" aria-hidden="true">
                <svg viewBox="0 0 24 24">
                  <rect x="3" y="4" width="18" height="13" rx="2" />
                  <path d="M8 21h8M12 17v4" />
                  <path d="M10 8.5v4l4-2-4-2Z" fill="currentColor" stroke="none" />
                </svg>
              </span>
              <span class="txt">
                <strong>路演训练</strong>
                <span>计时彩排、对回现场，检查改完是否真的更顺。</span>
              </span>
              <span class="go">去练 →</span>
            </button>
          </div>
          <p class="practice-tip">
            <b>建议路径：</b>先在任务里钉死下一刀 → 课程补洞 → 路演练一遍 → 再评一场看分是否上去。
          </p>
        </section>
      </div>

      <section class="appendix-power" aria-label="大脑引擎能力">
        <div class="appendix-label">附录 · 引擎</div>
        <div class="power-line">
          <span><strong>按规则打分</strong></span>
          <span class="sep">·</span>
          <span>对回现场</span>
          <span class="sep">·</span>
          <span>多维评委</span>
          <span class="sep">·</span>
          <span>变成下一步</span>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onActivated, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useCollaborationStore } from '../stores/collaboration'
import BrainMascot from '../components/BrainMascot.vue'
import ScoreMedal from '../components/ScoreMedal.vue'
import request from '../utils/request'

defineOptions({ name: 'DashboardHome' })

const AVATAR_COLORS = ['#e07a5f', '#3d5a80', '#81b29a', '#c9a227', '#9b5de5', '#4a90a4']

/**
 * 模块级会话缓存（SWR）：
 * 离开首页再回来时先回填上次数据，避免「无分」空态闪一下；
 * 再后台拉最新，保证准确度。不写 localStorage，避免脏数据与隐私残留。
 * @type {{
 *   ready: boolean,
 *   homeData: object,
 *   teams: array,
 *   teamDashboard: object|null
 * }}
 */
const homeSessionCache = {
  ready: false,
  homeData: {},
  teams: [],
  teamDashboard: null
}

const router = useRouter()
const authStore = useAuthStore()
const collaborationStore = useCollaborationStore()
const displayName = computed(() => (authStore.user?.username ? `${authStore.user.username}` : '同学'))

const homeData = ref(homeSessionCache.ready ? homeSessionCache.homeData : {})
const teams = ref(homeSessionCache.ready ? homeSessionCache.teams : [])
const teamDashboard = ref(homeSessionCache.ready ? homeSessionCache.teamDashboard : null)
/** 首次请求结束前：不展示「无数据」空态（可有缓存则直接有数据） */
const homeSettled = ref(homeSessionCache.ready)
/** 冷启动且尚无任何可展示数据 */
const isHomePending = computed(() => !homeSettled.value && !hasScoreProxy())
const isHomeReady = computed(() => homeSettled.value || hasScoreProxy())
const now = ref(new Date())
const mascotRef = ref(null)
const mascotCelebrate = ref(false)
let clockTimer = null
let celebrateTimer = null
let loadSeq = 0
let hasActivatedOnce = false

/** setup 阶段缓存是否已带出分（避免 computed 循环依赖 hasScore） */
function hasScoreProxy() {
  const roadshow = teamDashboard.value?.roadshow || {}
  const n = Number(roadshow.score ?? roadshow.aiScore)
  if (Number.isFinite(n) && n > 0) return true
  const m = Number(teamDashboard.value?.metrics?.roadshowScore)
  return Number.isFinite(m) && m > 0
}

const team = computed(() => teamDashboard.value?.team || teams.value[0] || null)
const metrics = computed(() => teamDashboard.value?.metrics || {})
const members = computed(() => teamDashboard.value?.members || [])
const stages = computed(() => teamDashboard.value?.stages || [])
const tasks = computed(() => teamDashboard.value?.tasks || [])
const submissions = computed(() => teamDashboard.value?.submissions || [])
const materials = computed(() => teamDashboard.value?.materials || [])
const reviewIssues = computed(() => teamDashboard.value?.reviewIssues || [])
const roadshow = computed(() => teamDashboard.value?.roadshow || {})
const competitionReadiness = computed(() => teamDashboard.value?.competitionReadiness || {})
const homePriority = computed(() => homeData.value?.priority || {})

const activeTeamId = computed(() => team.value?.id || teams.value[0]?.id || null)
const projectTeamPath = computed(() => (activeTeamId.value ? `/project-team?teamId=${activeTeamId.value}` : '/project-team'))
const projectTitle = computed(() => team.value?.name || '还没有参赛项目')

const currentStage = computed(() => {
  const key = String(team.value?.currentStage || '').toUpperCase()
  return stages.value.find((item) => String(item.stageKey || '').toUpperCase() === key)
    || stages.value.find((item) => ['IN_PROGRESS', 'ACTIVE'].includes(String(item.status || '').toUpperCase()))
    || stages.value[0]
    || null
})
const currentStageTitle = computed(() => currentStage.value?.title || stageText(team.value?.currentStage) || '')
const currentDeadline = computed(() => currentStage.value?.dueDate || team.value?.endDate)
const deadlineInfo = computed(() => buildDeadlineInfo(currentDeadline.value))
const greetingText = computed(() => greetingByHour(now.value.getHours()))
const memberCount = computed(() => members.value.length || Number(team.value?.memberCount || 0))
const openTaskCount = computed(() => {
  const open = tasks.value.filter((task) => !isDone(task.status)).length
  return open || Number(homePriority.value.pendingTasks || 0)
})

const teamPreview = computed(() => {
  const list = members.value.length ? members.value : []
  return list.slice(0, 5).map((m, index) => ({
    key: m.id || m.userId || m.username || index,
    label: memberInitial(m),
    color: AVATAR_COLORS[index % AVATAR_COLORS.length],
    name: memberDisplayName(m)
  }))
})
const teamActiveHint = computed(() => {
  if (!memberCount.value) return '可邀请队友一起备赛'
  return '一起备赛中'
})

/**
 * 下一刀负责人：只显示姓名，不显示头像。
 * 顶栏 team-pill 已用头像表达「谁在队里」；此处用名字回答「谁推进下一刀」。
 */
const nextCutOwnerNames = computed(() => {
  const names = members.value
    .map((m) => memberDisplayName(m))
    .filter((n) => n && n !== '成员')
  return names.length ? names.join(' · ') : ''
})

const materialsReady = computed(() => materials.value.length > 0)

const activityDays = computed(() => {
  const source = competitionReadiness.value?.activity?.days
  if (Array.isArray(source) && source.length) {
    return source.slice(-7).map((day, index) => ({
      date: String(day.date || index),
      label: String(day.label || ''),
      count: Math.max(0, Number(day.count || 0))
    }))
  }
  return Array.from({ length: 7 }, (_, index) => {
    const date = new Date(now.value)
    date.setDate(date.getDate() - (6 - index))
    return { date: date.toISOString().slice(0, 10), label: `${date.getMonth() + 1}/${date.getDate()}`, count: 0 }
  })
})
const activityLabel = computed(() => {
  const label = competitionReadiness.value?.activity?.label
  if (label) return String(label)
  return `近 7 天 ${activityDays.value.reduce((sum, day) => sum + day.count, 0)} 次更新`
})
const activityChartPoints = computed(() => {
  const max = Math.max(1, ...activityDays.value.map((day) => day.count))
  return activityDays.value.map((day, index) => ({
    key: day.date,
    x: 12 + (index * 396) / Math.max(1, activityDays.value.length - 1),
    y: 96 - (day.count / max) * 76
  }))
})
const activityPolyline = computed(() => activityChartPoints.value.map((p) => `${p.x},${p.y}`).join(' '))
const activityAreaPath = computed(() => {
  const points = activityChartPoints.value
  if (!points.length) return ''
  return `M ${points[0].x} 102 L ${points.map((p) => `${p.x} ${p.y}`).join(' L ')} L ${points.at(-1).x} 102 Z`
})
const readinessUpdates = computed(() => {
  const source = competitionReadiness.value?.recentUpdates
  if (!Array.isArray(source)) return []
  return source.slice(0, 3).map((item, index) => ({
    key: `${item.kind || 'update'}-${item.eventAt || index}`,
    kind: String(item.kind || 'update'),
    title: String(item.title || '项目有更新'),
    when: relativeTime(item.eventAt)
  }))
})
const readinessDeadline = computed(() => {
  const source = competitionReadiness.value?.deadline
  if (source?.label) return { label: String(source.label), tone: String(source.tone || 'neutral') }
  return { label: deadlineInfo.value.text || '比赛日期待设置', tone: deadlineInfo.value.tone || 'neutral' }
})
const readinessGaps = computed(() => {
  const source = competitionReadiness.value?.gaps
  if (Array.isArray(source)) {
    return source.slice(0, 3).map((gap, index) => ({
      key: String(gap.key || index),
      title: String(gap.title || '待补齐项目'),
      description: String(gap.description || gap.source || '打开项目查看详情。'),
      severity: String(gap.severity || 'medium'),
      actionPath: String(gap.actionPath || projectTeamPath.value)
    }))
  }
  const fallback = []
  const issue = reviewIssues.value.find((item) => !isDone(item.status) && String(item.severity).toUpperCase() === 'HIGH')
  if (issue) fallback.push({ key: 'review-risk', title: issue.title, description: issue.description || '高风险复盘项待闭环。', severity: 'high', actionPath: scoreReportPath.value })
  if (!hasScore.value) fallback.push({ key: 'roadshow', title: '完成一次计时路演并生成评分', description: '当前还没有可用于复盘的路演评分。', severity: 'high', actionPath: '/online-meeting' })
  if (!materialsReady.value) fallback.push({ key: 'materials', title: '补齐项目与赛道佐证材料', description: '当前项目材料库仍为空。', severity: 'medium', actionPath: '/resource-center' })
  return fallback.slice(0, 3)
})

const summarySyncLine = computed(() => {
  if (!hasScore.value || !memberCount.value) return ''
  return `团队 ${memberCount.value} 人 · 建议同步评分总结`
})

const sessionScore = computed(() => {
  const n = firstNumber(
    roadshow.value?.score,
    roadshow.value?.aiScore,
    metrics.value?.roadshowScore
  )
  return n
})
const hasScore = computed(() => {
  const status = String(roadshow.value?.status || '').toUpperCase()
  if (['AI_COMPLETED', 'MANUAL_SCORE'].includes(status) && sessionScore.value != null && sessionScore.value > 0) {
    return true
  }
  return sessionScore.value != null && sessionScore.value > 0
})
const scoreDisplay = computed(() => {
  if (!hasScore.value) return '—.—'
  const n = sessionScore.value
  return Number.isInteger(n) ? String(n) : Number(n).toFixed(1)
})
const scoreLevelLabel = computed(() => {
  if (!hasScore.value) return '待生成'
  const n = Number(sessionScore.value)
  if (n >= 85) return '表现较好'
  if (n >= 70) return '还有空间'
  return '待提升'
})
/** 与首页分数档位对齐：≥85 金 / ≥70 银 / 其余铜 */
const scoreMedalTier = computed(() => {
  if (!hasScore.value) return null
  const n = Number(sessionScore.value)
  if (!Number.isFinite(n)) return null
  if (n >= 85) return 'gold'
  if (n >= 70) return 'silver'
  return 'bronze'
})
const scoreLevelLed = computed(() => {
  if (!hasScore.value) return 'led-idle'
  const n = Number(sessionScore.value)
  if (n >= 70) return 'led-ok'
  return 'led-warn'
})
const brainLiveLed = computed(() => (hasScore.value ? 'led-pulse' : 'led-idle'))
const stageLed = computed(() => {
  if (deadlineInfo.value.tone === 'warning' || deadlineInfo.value.tone === 'late') return 'led-warn'
  return 'led-ok'
})

const mascotMood = computed(() => {
  if (mascotCelebrate.value) return 3
  if (!hasScore.value) return 0
  if (openTaskCount.value > 0 || scoreLevelLabel.value === '待提升') return 2
  return 1
})

function openScoreSummary() {
  triggerMascotCelebrate()
  go(scoreReportPath.value)
}

function onMascotTap() {
  triggerMascotCelebrate()
}

function triggerMascotCelebrate() {
  mascotCelebrate.value = true
  mascotRef.value?.celebrate?.()
  clearTimeout(celebrateTimer)
  celebrateTimer = window.setTimeout(() => {
    mascotCelebrate.value = false
  }, 1400)
}

const meetingId = computed(() => firstPresent(roadshow.value?.meetingId, roadshow.value?.meeting_id, null))
const scoreReportPath = computed(() => {
  if (meetingId.value) return `/ai-score/${meetingId.value}/result`
  if (hasScore.value) return '/statistics'
  return '/ai-score-upload'
})
const juryPath = computed(() => (meetingId.value ? `/ai-score/${meetingId.value}/jury` : ''))

const scoreReadAt = computed(() => {
  if (!hasScore.value) return ''
  const t = firstPresent(roadshow.value?.endTime, roadshow.value?.boundAt, roadshow.value?.startTime)
  if (!t) return '近期'
  return relativeTime(t)
})

const juryAverageDisplay = computed(() => {
  const n = firstNumber(
    roadshow.value?.juryAverage,
    roadshow.value?.jury_average,
    roadshow.value?.trimmedAverage,
    metrics.value?.juryAverage
  )
  if (n == null) return ''
  return Number.isInteger(n) ? String(n) : Number(n).toFixed(1)
})
const scoreDiffDisplay = computed(() => {
  if (!hasScore.value || !juryAverageDisplay.value) return ''
  const d = Number(juryAverageDisplay.value) - Number(sessionScore.value)
  if (!Number.isFinite(d)) return ''
  const abs = Math.abs(d).toFixed(1)
  return d > 0.05 ? `+${abs}` : d < -0.05 ? `-${abs}` : '0'
})
const scoreDiffPositive = computed(() => {
  const d = Number(juryAverageDisplay.value) - Number(sessionScore.value)
  return Number.isFinite(d) && d > 0.05
})

const dimensionBars = computed(() => {
  const raw = Array.isArray(roadshow.value?.dimensions) ? roadshow.value.dimensions : []
  return raw.slice(0, 5).map((item, index) => {
    const name = String(item.name || item.key || `维度${index + 1}`)
    const score = firstNumber(item.score, item.value, 0) ?? 0
    const maxScore = firstNumber(item.maxScore, item.max_score, 0)
    const percent = firstNumber(item.percent)
      ?? (maxScore > 0 ? Math.round((score / maxScore) * 100) : Math.min(100, Math.round(Number(score))))
    const weak = percent < 55
    return {
      key: item.key || name,
      shortName: shortDimName(name),
      percent: Math.max(0, Math.min(100, percent)),
      weak,
      scoreLabel: maxScore > 0 ? `${formatDimScore(score)}` : formatDimScore(score)
    }
  })
})
const dimCount = computed(() => dimensionBars.value.length)

/** 中栏五维：有分或有维度数据时显示；冷启动占位也显示骨架感 */
const showRadarMid = computed(() => isHomePending.value || hasScore.value || dimCount.value > 0)

const RADAR_CX = 124
const RADAR_CY = 124
const RADAR_R = 76
const radarCenter = RADAR_CX

/** 补齐到 5 维，便于稳定五边形 */
const radarDims = computed(() => {
  const base = dimensionBars.value.slice(0, 5)
  if (base.length >= 3) return base
  const placeholders = ['技能', '素养', '应用', '团队', '创新']
  return placeholders.map((name, i) => ({
    key: `ph-${i}`,
    shortName: name,
    percent: 0,
    weak: false,
    scoreLabel: '—',
    placeholder: true
  }))
})

function radarPoint(index, count, radius) {
  const angle = (-Math.PI / 2) + (index * 2 * Math.PI) / count
  return {
    x: RADAR_CX + radius * Math.cos(angle),
    y: RADAR_CY + radius * Math.sin(angle)
  }
}

function pointsToAttr(pts) {
  return pts.map((p) => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ')
}

const radarRings = computed(() => {
  const n = radarDims.value.length || 5
  return [0.35, 0.55, 0.75, 1].map((scale) => {
    const pts = Array.from({ length: n }, (_, i) => radarPoint(i, n, RADAR_R * scale))
    return pointsToAttr(pts)
  })
})

const radarAxes = computed(() => {
  const n = radarDims.value.length || 5
  return Array.from({ length: n }, (_, i) => radarPoint(i, n, RADAR_R))
})

/** 有真实分才画数据面；无分只保留网格 + 维度名 */
const radarVertices = computed(() => {
  if (!hasScore.value) return []
  const dims = radarDims.value
  const n = dims.length || 5
  return dims.map((d, i) => {
    const p = radarPoint(i, n, RADAR_R * (Math.max(8, d.percent) / 100))
    return { ...p, weak: d.weak }
  })
})

const radarDataPoints = computed(() => {
  if (!radarVertices.value.length) return ''
  return pointsToAttr(radarVertices.value)
})

const radarLabels = computed(() => {
  const dims = radarDims.value
  const n = dims.length || 5
  /* 贴图但留缝：过远显散，过近贴顶点 */
  const labelR = RADAR_R + 18
  const showScore = hasScore.value
  return dims.map((d, i) => {
    const p = radarPoint(i, n, labelR)
    return {
      x: p.x,
      nameY: showScore ? p.y - 5 : p.y,
      scoreY: p.y + 8,
      text: d.shortName,
      score: showScore ? d.scoreLabel : '',
      weak: Boolean(showScore && d.weak)
    }
  })
})

const weakDims = computed(() => dimensionBars.value.filter((d) => d.weak).map((d) => d.shortName))
const strongDims = computed(() => dimensionBars.value.filter((d) => !d.weak && d.percent >= 70).map((d) => d.shortName))
const weakestDimLabel = computed(() => {
  const weak = dimensionBars.value.filter((d) => d.weak)
  if (!weak.length) return null
  const first = weak[0]
  return { name: first.shortName, score: first.scoreLabel }
})

const judgmentTitle = computed(() => {
  if (weakDims.value.length >= 2) {
    return `${weakDims.value.slice(0, 2).join('、')}还偏弱，整体还能再抬一档。`
  }
  if (weakDims.value.length === 1) {
    return `${weakDims.value[0]}还没钉死，其他段可以托一把。`
  }
  if (strongDims.value.length) {
    return '主线能跟上，细处仍值得再磨一轮。'
  }
  return '本场已出分。先看弱项，再决定下一场怎么讲。'
})

const judgmentLead = computed(() => {
  const parts = []
  if (strongDims.value.length) {
    parts.push(`${strongDims.value.slice(0, 2).join('、')}相对更好`)
  }
  if (weakDims.value.length) {
    parts.push(`拉分主要在${weakDims.value.slice(0, 2).join('、')}`)
  }
  if (!parts.length) {
    return '对照赛道规则读完了本场。打开评分总结，看清该先改哪一段。'
  }
  return `${parts.join('。')}。听得懂在做什么，还要把结论钉得更牢。`
})

const nextCut = computed(() => {
  const issue = reviewIssues.value.find((item) => !isDone(item.status))
  if (issue?.title) {
    return {
      title: '先处理复盘里最靠前的一项',
      desc: '',
      path: scoreReportPath.value
    }
  }
  if (weakDims.value.length) {
    return {
      title: `先补「${weakDims.value[0]}」相关表达`,
      desc: '别加长演讲。把这一段讲清楚，够听众信一轮。',
      path: scoreReportPath.value
    }
  }
  const task = sortedTasks().find((item) => !isDone(item.status))
  if (task) {
    return {
      title: '推进一件当前待办',
      desc: '类型级提醒，详情在任务里打开。',
      path: projectTeamPath.value
    }
  }
  return {
    title: '打开评分总结，定下一刀',
    desc: '看完扣分位置，再决定先练什么。',
    path: scoreReportPath.value
  }
})

const recentMatters = computed(() => {
  const rows = []
  if (hasScore.value) {
    rows.push({
      key: 'score',
      title: `本场得分已出 · ${scoreDisplay.value} 分`,
      when: scoreReadAt.value || '近期',
      led: 'led-ok',
      time: timeValue(roadshow.value?.endTime || roadshow.value?.boundAt) || Date.now()
    })
  }
  sortedTasks().slice(0, 3).forEach((task, index) => {
    rows.push({
      key: `t-${task.id || index}`,
      title: abstractTaskType(task),
      when: isDone(task.status) ? '已完成' : taskStatusBrief(task.status),
      led: isDone(task.status) ? 'led-ok' : needsAttention(task.status) ? 'led-warn' : 'led-ok',
      time: timeValue(task.dueAt || task.updatedAt)
    })
  })
  if (submissions.value.length) {
    rows.push({
      key: 'sub',
      title: '有成果提交',
      when: '本周',
      led: 'led-idle',
      time: timeValue(submissions.value[0]?.createdAt)
    })
  }
  if (materials.value.length) {
    rows.push({
      key: 'mat',
      title: '有材料更新',
      when: '本周',
      led: 'led-idle',
      time: timeValue(materials.value[0]?.updatedAt)
    })
  }
  if (reviewIssues.value.length) {
    rows.push({
      key: 'iss',
      title: '有复盘事项待跟',
      when: '待处理',
      led: 'led-warn',
      time: timeValue(reviewIssues.value[0]?.updatedAt)
    })
  }
  const sorted = rows.sort((a, b) => (b.time || 0) - (a.time || 0)).slice(0, 5)
  if (sorted.length) return sorted
  return [{ key: 'empty', title: '暂无最近事项', when: '—', led: 'led-idle' }]
})

onMounted(() => {
  // 有会话缓存则 setup 已回填，这里静默刷新；无缓存则柔光占位至 settled
  loadDashboard({ silent: homeSessionCache.ready })
  clockTimer = setInterval(() => {
    now.value = new Date()
  }, 60000)
})

/** keep-alive 再次进入：只后台刷新，不卸 UI、不闪空 */
onActivated(() => {
  if (!hasActivatedOnce) {
    hasActivatedOnce = true
    return
  }
  loadDashboard({ silent: true })
})

onUnmounted(() => {
  if (clockTimer) clearInterval(clockTimer)
  clearTimeout(celebrateTimer)
})

function applyHomePayload({ home, teamList, dashboard }) {
  homeData.value = home
  teams.value = teamList
  teamDashboard.value = dashboard
  homeSessionCache.ready = true
  homeSessionCache.homeData = home
  homeSessionCache.teams = teamList
  homeSessionCache.teamDashboard = dashboard
}

/**
 * @param {{ silent?: boolean }} [opts]
 * silent：已有展示数据时后台刷新，不把 settled 打回 false
 */
async function loadDashboard(opts = {}) {
  const silent = Boolean(opts.silent)
  const seq = ++loadSeq
  try {
    const [homeRes, teamsRes] = await Promise.allSettled([
      request.get('/api/home/dashboard', { silentError: true }),
      request.get('/api/project-teams/my', { silentError: true })
    ])
    if (seq !== loadSeq) return

    const home = homeRes.status === 'fulfilled' ? (homeRes.value?.data || {}) : (homeSessionCache.homeData || {})
    const teamList = teamsRes.status === 'fulfilled' ? (teamsRes.value?.data || []) : (homeSessionCache.teams || [])

    let dashboard = homeSessionCache.teamDashboard
    const teamId = teamList[0]?.id
    if (teamId) {
      try {
        const dashboardRes = await request.get(`/api/project-teams/${teamId}/dashboard`, { silentError: true })
        if (seq !== loadSeq) return
        dashboard = dashboardRes.data || null
      } catch {
        if (!homeSessionCache.ready) dashboard = null
      }
    } else if (teamsRes.status === 'fulfilled') {
      dashboard = null
    }

    if (seq !== loadSeq) return
    applyHomePayload({ home, teamList, dashboard })
  } catch {
    if (seq !== loadSeq) return
    // 失败时保留缓存，避免误清空
    if (!homeSessionCache.ready && !silent) {
      teamDashboard.value = null
    }
  } finally {
    if (seq === loadSeq) homeSettled.value = true
  }
}

function go(path) {
  if (path) router.push(path)
}

/** 首页唤起待办中心（今日必做 / 待我处理 / 日报） */
function openTodoHub() {
  if (collaborationStore.isFeatureEnabled) {
    collaborationStore.activeTab = 'TODAY'
    collaborationStore.open()
    return
  }
  go(projectTeamPath.value)
}

function timelineClass(led) {
  if (led === 'led-ok') return 'ok'
  if (led === 'led-warn') return 'warn'
  return ''
}

function sortedTasks() {
  return [...tasks.value].sort((a, b) => {
    if (isDone(a.status) !== isDone(b.status)) return isDone(a.status) ? 1 : -1
    return timeValue(a.dueAt) - timeValue(b.dueAt)
  })
}

function memberDisplayName(m) {
  return String(m.displayName || m.name || m.realName || m.username || m.nickname || '成员')
}

function memberInitial(m) {
  const name = memberDisplayName(m)
  const ch = name.trim().charAt(0)
  return ch || '?'
}

function abstractTaskType(task) {
  const type = String(task.taskType || task.task_type || task.stageKey || '').toUpperCase()
  const map = {
    COURSE: '课程学习相关',
    EXAM: '考试练习相关',
    MATERIAL: '材料准备相关',
    ROADSHOW: '路演练习相关',
    REVIEW: '复盘改进相关',
    OTHER_BUSINESS: '其他业务相关',
    OTHER: '其他事项'
  }
  if (map[type]) return map[type]
  const label = String(task.taskTypeLabel || task.task_type_label || '')
  if (/材料|资料|PPT|稿/.test(label)) return '材料准备相关'
  if (/路演|演练|彩排/.test(label)) return '路演练习相关'
  if (/课/.test(label)) return '课程学习相关'
  if (/考|测/.test(label)) return '考试练习相关'
  return '项目事项'
}

function taskStatusBrief(status) {
  const map = {
    TODO: '待处理',
    IN_PROGRESS: '进行中',
    REVIEWING: '待处理',
    CHANGES_REQUESTED: '待处理',
    DONE: '已完成'
  }
  return map[String(status || '').toUpperCase()] || '进行中'
}

function needsAttention(status) {
  return ['TODO', 'REVIEWING', 'CHANGES_REQUESTED'].includes(String(status || '').toUpperCase())
}

function shortDimName(name) {
  const n = String(name || '')
  if (n.includes('技能')) return '技能'
  if (n.includes('素养') || n.includes('职业')) return '素养'
  if (n.includes('应用') || n.includes('价值')) return '应用'
  if (n.includes('团队') || n.includes('合作')) return '团队'
  if (n.includes('创新') || n.includes('创意')) return '创新'
  return n.slice(0, 2) || '维度'
}

function formatDimScore(value) {
  const n = Number(value)
  if (!Number.isFinite(n)) return '—'
  return Number.isInteger(n) ? String(n) : n.toFixed(0)
}

function isDone(status) {
  return ['DONE', 'APPROVED', 'COMPLETED', '完成', '已完成'].includes(String(status || '').toUpperCase())
}

function shortDate(value) {
  if (!value) return '未设置'
  const raw = String(value)
  const match = raw.match(/(\d{4})[-/](\d{1,2})[-/](\d{1,2})/)
  if (match) return `${Number(match[2])}月${Number(match[3])}日`
  return raw.slice(0, 10)
}

/** 减压说辞：提示紧，不点名「已超 N 天」 */
function buildDeadlineInfo(value) {
  if (!value) {
    return { text: '', detail: '', railHint: '', tone: 'neutral' }
  }
  const target = parseDate(value)
  if (!target) {
    return { text: `节点 ${shortDate(value)}`, detail: `计划节点 ${shortDate(value)}`, railHint: '', tone: 'neutral' }
  }
  const today = startOfDay(now.value)
  const targetDay = startOfDay(target)
  const diff = Math.round((targetDay.getTime() - today.getTime()) / 86400000)
  const due = shortDate(value)
  if (diff > 7) {
    return {
      text: `距节点还有 ${diff} 天`,
      detail: `计划节点 ${due}`,
      railHint: '',
      tone: 'normal'
    }
  }
  if (diff > 3) {
    return {
      text: `距节点 ${diff} 天 · 可稳步推进`,
      detail: `计划节点 ${due}`,
      railHint: '',
      tone: 'normal'
    }
  }
  if (diff > 0) {
    return {
      text: '节奏偏紧 · 宜优先推进',
      detail: `计划节点 ${due}`,
      railHint: '节奏偏紧，建议本周内优先收束下一刀，再安排彩排。',
      tone: 'warning'
    }
  }
  if (diff === 0) {
    return {
      text: '今日节点 · 宜收束推进',
      detail: `计划节点 ${due}`,
      railHint: '今日为计划节点，建议优先收束关键动作。',
      tone: 'warning'
    }
  }
  return {
    text: '节奏偏紧 · 宜优先推进',
    detail: `计划节点 ${due}`,
    railHint: '计划节点在身后，节奏偏紧，建议本周内优先收束下一刀，再安排彩排。',
    tone: 'late'
  }
}

function parseDate(value) {
  if (!value) return null
  const raw = String(value)
  const match = raw.match(/(\d{4})[-/](\d{1,2})[-/](\d{1,2})/)
  const date = match ? new Date(Number(match[1]), Number(match[2]) - 1, Number(match[3])) : new Date(value)
  return Number.isNaN(date.getTime()) ? null : date
}

function startOfDay(value) {
  const date = new Date(value)
  date.setHours(0, 0, 0, 0)
  return date
}

function greetingByHour(hour) {
  if (hour >= 5 && hour < 9) return '早安'
  if (hour >= 9 && hour < 12) return '上午好'
  if (hour >= 12 && hour < 14) return '中午好'
  if (hour >= 14 && hour < 18) return '下午好'
  if (hour >= 18 && hour < 23) return '晚上好'
  return '夜深了'
}

function relativeTime(value) {
  if (!value) return '最近'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return String(value).slice(0, 16)
  const diff = Date.now() - date.getTime()
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  if (diff < 86400000 * 7) return `${Math.floor(diff / 86400000)} 天前`
  return date.toLocaleDateString('zh-CN')
}

function timeValue(value) {
  if (!value) return 0
  const time = new Date(value).getTime()
  return Number.isNaN(time) ? 0 : time
}

function stageText(value) {
  const map = {
    COURSE: '课程学习',
    EXAM: '测评训练',
    MATERIAL: '材料准备',
    ROADSHOW: '路演训练',
    REVIEW: '复盘改进'
  }
  return map[String(value || '').toUpperCase()] || String(value || '')
}

function firstPresent(...values) {
  return values.find((value) => value !== undefined && value !== null && value !== '')
}

function firstNumber(...values) {
  for (const value of values) {
    if (value === undefined || value === null || value === '') continue
    const number = Number(value)
    if (Number.isFinite(number)) return number
  }
  return null
}
</script>

<style scoped>
.home-page {
  /* 用户端页面底：纯白，无渐变 */
  --canvas: #ffffff;
  --canvas-deep: #ffffff;
  --ink: var(--ds-ink, #12141a);
  --ink-2: var(--ds-ink-2, #2c3038);
  --muted: #7a7580;
  --faint: #a39aa3;
  --line: rgba(120, 90, 70, 0.08);
  --line-strong: rgba(120, 90, 70, 0.12);
  --orange: var(--ds-orange, #e84a1c);
  --orange-deep: var(--ds-orange-deep, #c43a12);
  --orange-soft: #fde8de;
  --orange-wash: #fff4ee;
  --green: var(--ds-green, #0f9f6e);
  --font: var(--ds-font-sans);
  --num: var(--ds-font-num);
  --max: var(--ds-page-max, 1280px);
  /* 软阴影：橙色调（约减半透明度，更淡） */
  --neo-dark: rgba(232, 74, 28, 0.05);
  --neo-dark-soft: rgba(232, 74, 28, 0.03);
  --neo-light: rgba(255, 255, 255, 0.95);
  --neo-inset-dark: rgba(232, 74, 28, 0.03);
  --neo-inset-light: rgba(255, 255, 255, 0.85);

  color: var(--ink);
  font-family: var(--font);
  font-style: normal;
  font-synthesis: none;
  -webkit-font-smoothing: antialiased;
  background-color: #ffffff;
  background-image: none;
  min-height: 100%;
  /* 页边距由 .workspace-main 唯一提供 */
  padding: 0 0 var(--ds-space-6, 24px);
}

.home-page :deep(em),
.home-page :deep(i) {
  font-style: normal;
}

.home-inner {
  max-width: var(--max);
  width: 100%;
  margin: 0 auto;
  padding: 0 0 8px;
}

/* 对齐 biji：白底 + 冷灰线 + 轻 elevation */
.neo-raised {
  background: #ffffff;
  border: 1px solid var(--ds-card-border, #e2e4ea);
  border-radius: var(--ds-card-radius, 14px);
  backdrop-filter: none;
  -webkit-backdrop-filter: none;
  box-shadow: none;
}

.led {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
  vertical-align: middle;
  background: #c5c9d1;
}
.led-ok {
  background: var(--green);
  box-shadow: 0 0 0 2px rgba(15, 159, 110, 0.12);
}
.led-warn {
  background: var(--orange);
  box-shadow: 0 0 0 2px rgba(232, 74, 28, 0.12);
}
.led-idle { background: #c5c9d1; }
.led-pulse {
  background: var(--green);
  box-shadow: 0 0 0 0 rgba(15, 159, 110, 0.35);
  animation: ledPulse 2.4s ease infinite;
}
@keyframes ledPulse {
  0% { box-shadow: 0 0 0 0 rgba(15, 159, 110, 0.35); }
  70% { box-shadow: 0 0 0 6px rgba(15, 159, 110, 0); }
  100% { box-shadow: 0 0 0 0 rgba(15, 159, 110, 0); }
}
.with-led {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

/* —— 顶栏 —— */
.context {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 14px 24px;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--line);
}
@media (max-width: 900px) {
  .context { grid-template-columns: 1fr; }
}
.context-left h1 {
  margin: 0;
  font-size: var(--ds-text-h1, clamp(22px, 1.8vw, 28px));
  font-weight: 700;
  letter-spacing: -0.025em;
  line-height: 1.2;
}
.context-left .meta {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px 10px;
  margin-top: 8px;
  font-size: 14px;
  color: var(--muted);
  font-weight: 500;
}
.context-left .meta .sep { color: var(--faint); }
.context-left .meta strong { color: var(--ink); font-weight: 700; }
.context-left .meta .warn { color: var(--orange-deep); font-weight: 600; }

.context-right {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  justify-self: end;
  margin-left: auto;
  gap: 10px 12px;
  min-width: 0;
}

.team-pill {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 6px 10px 6px 8px;
  border-radius: 999px;
  margin-left: auto;
  background: linear-gradient(
    145deg,
    rgba(255, 255, 255, 0.58) 0%,
    rgba(255, 248, 244, 0.28) 100%
  );
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  box-shadow:
    0 6px 16px var(--neo-dark),
    inset 0 1px 0 rgba(255, 255, 255, 0.65);
  border: 1px solid rgba(255, 255, 255, 0.45);
}
.team-pill .stack { display: flex; }
.team-pill .av {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  margin-left: -8px;
  border: 2px solid var(--canvas);
  display: grid;
  place-items: center;
  font-size: 11px;
  font-weight: 800;
  color: #fff;
}
.team-pill .stack .av:first-child { margin-left: 0; }
.team-pill .info {
  font-size: 12.5px;
  font-weight: 700;
  color: var(--ink-2);
  line-height: 1.25;
}
.team-pill .info small {
  display: block;
  font-size: 11px;
  font-weight: 500;
  color: var(--faint);
}
.team-pill .invite {
  height: 28px;
  padding: 0 11px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  background: var(--orange-wash);
  color: var(--orange-deep);
  border: 1px solid rgba(232, 74, 28, 0.14);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.8);
}
.team-pill .invite:hover { background: var(--orange-soft); }
.team-empty {
  height: 36px;
  margin-left: auto;
  padding: 0 14px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  color: var(--orange-deep);
  background: var(--orange-wash);
  box-shadow:
    4px 5px 12px var(--neo-dark),
    -3px -3px 10px var(--neo-light);
}

.btn-text {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: var(--ds-btn-font, 15px);
  font-weight: 700;
  color: var(--orange);
  background: none;
  border: 0;
  padding: 0;
  cursor: pointer;
  font-family: inherit;
  line-height: 1;
}
.btn-text:hover { color: var(--orange-deep); }
.btn-text.primary {
  justify-content: center;
  height: var(--ds-btn-height, 40px);
  padding: 0 var(--ds-btn-padding-x, 18px);
  border-radius: var(--ds-radius-pill, 999px);
  background: var(--ds-btn-primary-bg, var(--orange));
  color: var(--ds-btn-primary-fg, #fff);
  box-shadow: none;
  font-size: var(--ds-btn-font, 14px);
}
.btn-text.primary:hover {
  background: var(--ds-btn-primary-bg-hover, var(--orange-deep));
  color: var(--ds-btn-primary-fg, #fff);
}
.btn-text.primary:active {
  background: var(--ds-btn-primary-bg-active, var(--orange-deep));
}
.btn-text.quiet { color: var(--faint); font-weight: 600; }
.btn-text.quiet:hover { color: var(--muted); }

/* 按钮图标：主 17px / 次 15px，线框统一 */
.btn-ico {
  width: 15px;
  height: 15px;
  flex-shrink: 0;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.75;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.btn-text.primary .btn-ico {
  width: 17px;
  height: 17px;
}
.btn-text.has-ico {
  gap: 7px;
}

.num {
  font-family: var(--num);
  font-variant-numeric: tabular-nums;
}
.num.ghost { color: var(--faint); }

/* 冷启动柔光占位 + 内容就绪淡入（非传统 spinner） */
.home-page.is-home-pending .home-reveal {
  opacity: 0.55;
  filter: saturate(0.92);
  transition: opacity 0.45s ease, filter 0.45s ease;
}
.home-page.is-home-ready .home-reveal {
  opacity: 1;
  filter: none;
  transition: opacity 0.45s ease, filter 0.45s ease;
}
.home-page.is-home-ready .hero-stage {
  animation: homeContentIn 0.48s cubic-bezier(0.22, 1, 0.36, 1) both;
}
@keyframes homeContentIn {
  from {
    opacity: 0.72;
    transform: translateY(6px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.stage-soft-load {
  padding: 4px 0 8px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  flex: 1;
}
.stage-soft-load.compact {
  padding-top: 8px;
  gap: 10px;
}
.soft-bar {
  height: 12px;
  border-radius: 999px;
  background: linear-gradient(
    100deg,
    rgba(255, 255, 255, 0.28) 0%,
    rgba(255, 255, 255, 0.62) 40%,
    rgba(255, 244, 238, 0.45) 60%,
    rgba(255, 255, 255, 0.28) 100%
  );
  background-size: 220% 100%;
  animation: homeSoftShimmer 1.6s ease-in-out infinite;
}
.soft-bar.w-lg { width: min(92%, 20em); height: 26px; border-radius: 10px; }
.soft-bar.w-md { width: min(78%, 26em); }
.soft-bar.w-sm { width: 5.5em; height: 10px; }
.soft-bar.w-xs { width: 4em; height: 10px; }
.soft-bar.center { margin-left: auto; margin-right: auto; }
.soft-panel {
  margin-top: 8px;
  height: 96px;
  border-radius: 16px;
  background: linear-gradient(
    100deg,
    rgba(255, 255, 255, 0.22) 0%,
    rgba(255, 255, 255, 0.5) 45%,
    rgba(255, 255, 255, 0.22) 100%
  );
  background-size: 220% 100%;
  animation: homeSoftShimmer 1.6s ease-in-out infinite;
}
.soft-actions {
  display: flex;
  gap: 10px;
  margin-top: auto;
  padding-top: 8px;
}
.soft-chip {
  height: 36px;
  width: 108px;
  border-radius: 999px;
  background: linear-gradient(
    100deg,
    rgba(232, 74, 28, 0.18) 0%,
    rgba(232, 74, 28, 0.32) 50%,
    rgba(232, 74, 28, 0.18) 100%
  );
  background-size: 220% 100%;
  animation: homeSoftShimmer 1.6s ease-in-out infinite;
}
.soft-chip.sm {
  width: 72px;
  background: linear-gradient(
    100deg,
    rgba(255, 255, 255, 0.25) 0%,
    rgba(255, 255, 255, 0.5) 50%,
    rgba(255, 255, 255, 0.25) 100%
  );
  background-size: 220% 100%;
}
.score-soft-load {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 28px 12px 8px;
  flex: 1;
}
.soft-score {
  width: 120px;
  height: 72px;
  border-radius: 16px;
  background: linear-gradient(
    100deg,
    rgba(255, 255, 255, 0.25) 0%,
    rgba(255, 255, 255, 0.55) 45%,
    rgba(255, 255, 255, 0.25) 100%
  );
  background-size: 220% 100%;
  animation: homeSoftShimmer 1.6s ease-in-out infinite;
}
.soft-cta {
  margin-top: 8px;
  width: min(100%, 200px);
  height: 40px;
  border-radius: 999px;
  background: linear-gradient(
    100deg,
    rgba(232, 74, 28, 0.22) 0%,
    rgba(232, 74, 28, 0.4) 50%,
    rgba(232, 74, 28, 0.22) 100%
  );
  background-size: 220% 100%;
  animation: homeSoftShimmer 1.6s ease-in-out infinite;
}
@keyframes homeSoftShimmer {
  0% { background-position: 100% 0; }
  100% { background-position: -100% 0; }
}
@media (prefers-reduced-motion: reduce) {
  .soft-bar,
  .soft-panel,
  .soft-chip,
  .soft-score,
  .soft-cta {
    animation: none;
  }
  .home-page.is-home-ready .hero-stage {
    animation: none;
  }
}

.empty-steps {
  margin: 0 0 16px;
  padding: 0;
  list-style: none;
}
.empty-steps li {
  display: flex;
  gap: 12px;
  padding: 7px 0;
  font-size: 15px;
  color: var(--muted);
  font-weight: 500;
}
.empty-steps b {
  font-family: var(--num);
  font-size: 14px;
  color: var(--faint);
  font-weight: 700;
  min-width: 1.1em;
}
.empty-steps strong { color: var(--ink); font-weight: 700; }

/* —— 分屏舞台：左点评 | 中五维 | 右总分 —— */
.hero-stage {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(260px, 0.82fr);
  gap: 0;
  min-height: 380px;
  margin-bottom: 0;
  border-radius: var(--ds-radius-xl, 20px);
  overflow: hidden;
}
.hero-stage.has-mid {
  grid-template-columns:
    minmax(0, 1fr)
    minmax(260px, 0.9fr)
    minmax(220px, 0.78fr);
}
@media (max-width: 1100px) {
  .hero-stage.has-mid {
    grid-template-columns:
      minmax(0, 1fr)
      minmax(236px, 0.82fr)
      minmax(200px, 0.72fr);
  }
}
@media (max-width: 960px) {
  .hero-stage,
  .hero-stage.has-mid {
    grid-template-columns: 1fr;
    min-height: 0;
  }
}

/*
  三栏仍是独立块，但不画分界线。
  左右沿用各自渐变范围；中栏横向桥接，接缝处色值对齐，视觉上成一块。
*/
.hero-stage.has-mid .stage-left,
.hero-stage.has-mid .stage-mid,
.hero-stage.has-mid .stage-right {
  border-right: 0;
}

.stage-left {
  padding: 26px 28px 22px;
  background: linear-gradient(
    165deg,
    rgba(255, 255, 255, 0.68) 0%,
    rgba(255, 255, 255, 0.38) 50%,
    rgba(255, 246, 240, 0.24) 100%
  );
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.hero-stage.has-mid .stage-left {
  /* 右缘略暖，与中栏左缘对齐，去掉硬切 */
  background: linear-gradient(
    100deg,
    rgba(255, 255, 255, 0.68) 0%,
    rgba(255, 255, 255, 0.42) 58%,
    rgba(255, 248, 242, 0.36) 100%
  );
}
@media (max-width: 960px) {
  .stage-left {
    border-bottom: 1px solid rgba(120, 90, 70, 0.06);
  }
}

/* 中栏：横向渐变桥接左浅 / 右暖，不抢戏 */
.stage-mid {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px 8px 16px;
  min-width: 0;
  background:
    linear-gradient(
      90deg,
      rgba(255, 248, 242, 0.36) 0%,
      rgba(255, 244, 236, 0.55) 48%,
      rgba(250, 240, 232, 0.78) 100%
    );
}
@media (max-width: 960px) {
  .stage-mid {
    border-bottom: 1px solid rgba(120, 90, 70, 0.06);
    padding: 18px 16px 16px;
  }
}
.mid-lab {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.08em;
  color: var(--orange-deep);
  margin-bottom: 4px;
}
.radar-wrap {
  width: min(100%, 292px);
  aspect-ratio: 1;
  cursor: default;
}
.radar-svg {
  width: 100%;
  height: 100%;
  display: block;
  overflow: visible;
}
.radar-grid {
  transform-origin: 124px 124px;
  animation: homeRadarGridIn 0.7s cubic-bezier(0.22, 1, 0.36, 1) both;
}
.radar-ring {
  fill: none;
  stroke: rgba(120, 90, 70, 0.1);
  stroke-width: 1;
}
.radar-ring.outer {
  stroke: rgba(232, 74, 28, 0.16);
}
.radar-axis {
  stroke: rgba(120, 90, 70, 0.08);
  stroke-width: 1;
}
.radar-data {
  fill: url(#homeRadarFill);
  stroke: rgba(232, 74, 28, 0.55);
  stroke-width: 1.6;
  stroke-linejoin: round;
  transform-origin: 124px 124px;
  animation: homeRadarShapeIn 0.85s cubic-bezier(0.22, 1, 0.36, 1) 0.12s both;
}
.radar-wrap.is-live .radar-data {
  animation:
    homeRadarShapeIn 0.85s cubic-bezier(0.22, 1, 0.36, 1) 0.12s both,
    homeRadarBreathe 5.2s ease-in-out 1.1s infinite;
}
.radar-dot {
  fill: #fff;
  stroke: var(--orange);
  stroke-width: 1.6;
  transform-origin: center;
  transform-box: fill-box;
  animation: homeRadarDotIn 0.55s cubic-bezier(0.22, 1, 0.36, 1) both;
  animation-delay: calc(0.28s + var(--dot-i, 0) * 0.05s);
}
.radar-dot.weak {
  stroke: var(--orange-deep);
  fill: var(--orange-soft);
  animation:
    homeRadarDotIn 0.55s cubic-bezier(0.22, 1, 0.36, 1) both,
    homeRadarWeakPulse 3.2s ease-in-out infinite;
  animation-delay:
    calc(0.28s + var(--dot-i, 0) * 0.05s),
    calc(1s + var(--dot-i, 0) * 0.12s);
}
/* 维度名常显；分数默认隐藏，悬停再显 */
.radar-label {
  pointer-events: none;
}
/*
  SVG 字号会随图放大；用约 9px，屏上约等于 10–11px，
  小于「五维画像」标题，避免抢层级。
*/
.radar-label-name {
  font-size: 9px;
  font-weight: 600;
  fill: var(--orange);
  font-family: var(--font);
  letter-spacing: 0.04em;
}
.radar-label-score {
  font-size: 8.5px;
  font-weight: 600;
  font-family: var(--num);
  fill: var(--orange-deep);
  opacity: 0;
  transition: opacity 0.22s ease;
}
.radar-wrap:hover .radar-label-score,
.radar-wrap:focus-within .radar-label-score {
  opacity: 1;
}
.radar-label.weak .radar-label-name {
  fill: var(--orange-deep);
  font-weight: 700;
}
.radar-label.weak .radar-label-score {
  fill: var(--orange-deep);
}
/* 触控无悬停：分数常显，避免看不到 */
@media (hover: none) {
  .radar-label-score {
    opacity: 1;
  }
}
@keyframes homeRadarGridIn {
  from { opacity: 0; transform: scale(0.96); }
  to { opacity: 1; transform: scale(1); }
}
@keyframes homeRadarShapeIn {
  from {
    opacity: 0;
    transform: scale(0.9);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}
/* 幅度克制：只呼吸透明度，不改形状，避免图表读数晃动 */
@keyframes homeRadarBreathe {
  0%, 100% { fill-opacity: 1; stroke-opacity: 0.92; }
  50% { fill-opacity: 0.78; stroke-opacity: 1; }
}
@keyframes homeRadarDotIn {
  from {
    opacity: 0;
    transform: scale(0.55);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}
@keyframes homeRadarWeakPulse {
  0%, 100% {
    stroke-opacity: 1;
    filter: drop-shadow(0 0 0 transparent);
  }
  50% {
    stroke-opacity: 0.88;
    filter: drop-shadow(0 0 2.5px rgba(232, 74, 28, 0.35));
  }
}
@media (prefers-reduced-motion: reduce) {
  .radar-grid,
  .radar-data,
  .radar-dot,
  .radar-dot.weak {
    animation: none !important;
    opacity: 1;
    transform: none;
    filter: none;
    fill-opacity: 1;
    stroke-opacity: 1;
  }
  .radar-label-score {
    transition: none;
  }
}
.mid-hint {
  margin: 4px 0 0;
  font-size: 12px;
  font-weight: 600;
  color: var(--muted);
  text-align: center;
}
.mid-hint b {
  color: var(--ink-2);
  font-weight: 700;
}
.mid-hint .n {
  margin-left: 4px;
  color: var(--orange-deep);
  font-weight: 800;
}
.mid-hint.muted {
  color: var(--faint);
  font-weight: 500;
}
.stage-left .tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.06em;
  color: var(--orange-deep);
  margin-bottom: 10px;
}
.tag-ico {
  width: 13px;
  height: 13px;
  flex-shrink: 0;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.7;
  stroke-linecap: round;
  stroke-linejoin: round;
}
/* 星标标签用轻微填充，更易识别 */
.stage-left .tag .tag-ico path:first-child {
  fill: rgba(232, 74, 28, 0.12);
}
.stage-left .judge {
  margin: 0 0 8px;
  font-size: var(--ds-text-h2, clamp(20px, 2vw, 26px));
  font-weight: 700;
  letter-spacing: -0.02em;
  line-height: 1.3;
  max-width: 16em;
}
.stage-left .lead {
  margin: 0 0 14px;
  font-size: var(--ds-text-body, 15px);
  line-height: 1.62;
  color: var(--muted);
  font-weight: 500;
  max-width: 38em;
}
/* 下一刀：只承载说明；操作按钮下沉到底栏上方 */
.next-block {
  padding: 16px 0 0;
  border-top: 1px solid var(--line);
  margin-bottom: 0;
}
.next-block .lab {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.07em;
  color: var(--orange-deep);
  margin-bottom: 10px;
}
.next-block strong {
  display: block;
  font-size: 16px;
  font-weight: 700;
  line-height: 1.45;
  margin-bottom: 8px;
  max-width: 22em;
}
.next-block p {
  margin: 0 0 8px;
  font-size: 14px;
  color: var(--muted);
  line-height: 1.55;
  font-weight: 500;
}
.owners-line {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 6px 8px;
  margin: 0;
  font-size: 13px;
  line-height: 1.5;
}
.owners-lab {
  flex-shrink: 0;
  font-weight: 600;
  color: var(--muted);
}
.owners-names {
  font-weight: 700;
  color: var(--ink-2);
}

/* 拼图布局等其它区域的 acts */
.acts {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 18px;
  align-items: center;
  margin-bottom: 14px;
}
/* 左栏操作：顶开空白，落在会议室入口上方 */
.stage-left .stage-actions {
  margin: auto 0 0;
  padding-top: 20px;
  margin-bottom: 0;
  gap: 12px 20px;
}
/* 主卡下沿：在线会议室主入口，贴底不显空 */
.stage-primary-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px 16px;
  margin-top: 14px;
  padding-top: 16px;
  border-top: 1px solid var(--line);
}
.stage-primary-bar .btn-text.primary {
  min-width: 132px;
}
.stage-primary-hint {
  font-size: 13px;
  font-weight: 500;
  color: var(--faint);
}

.stage-right {
  position: relative;
  isolation: isolate;
  padding: 28px 20px 18px;
  background:
    radial-gradient(ellipse 80% 50% at 50% 22%, rgba(232, 74, 28, 0.06), transparent 58%),
    linear-gradient(165deg, rgba(255, 248, 242, 0.55) 0%, rgba(255, 240, 230, 0.35) 45%, transparent 70%),
    linear-gradient(180deg, #faf0e8 0%, #f3e6dc 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  overflow: hidden;
}
.hero-stage.has-mid .stage-right {
  /* 左缘与中栏右缘对齐；暖色范围仍落在右栏内 */
  background:
    radial-gradient(ellipse 80% 50% at 50% 22%, rgba(232, 74, 28, 0.06), transparent 58%),
    linear-gradient(100deg, rgba(250, 240, 232, 0.78) 0%, rgba(255, 248, 242, 0.45) 28%, transparent 58%),
    linear-gradient(180deg, #faf0e8 0%, #f3e6dc 100%);
}
.stage-right > :not(.mascot-deco) {
  position: relative;
  z-index: 1;
}

/*
  只放芯片本体，无浅白外框、无双层底
  尺寸加大；本体颜色由 BrainMascot chipOnly 渐变与右栏区分
*/
.mascot-deco {
  position: absolute;
  top: 10px;
  right: 10px;
  z-index: 2;
  width: 92px;
  height: 92px;
  padding: 0;
  border: 0;
  background: transparent;
  box-shadow: none;
  pointer-events: auto;
  display: block;
  overflow: visible;
}
.mascot-deco :deep(.signal-mod) {
  width: 100%;
  height: 100%;
}
.score-lab {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.1em;
  color: var(--orange-deep);
  margin: 4px 0 2px;
}
.score-lab-ico {
  width: 13px;
  height: 13px;
  flex-shrink: 0;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.7;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.score-medal-slot {
  display: flex;
  justify-content: center;
  margin: 2px 0 4px;
}
.stage-right .big {
  font-size: clamp(52px, 6.5vw, 74px);
  font-weight: 700;
  letter-spacing: -0.05em;
  line-height: 0.9;
  margin-bottom: 6px;
}
.stage-right .big small {
  font-size: 16px;
  font-weight: 600;
  color: var(--faint);
  margin-left: 4px;
  letter-spacing: 0;
}
.stage-right .level {
  font-size: 14px;
  font-weight: 600;
  color: var(--muted);
  margin-bottom: 14px;
}
.stage-stats {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 12px 18px;
  margin-bottom: 12px;
  font-size: 12.5px;
  color: var(--muted);
  font-weight: 500;
}
.stage-stats b {
  display: block;
  font-family: var(--num);
  font-size: 17px;
  font-weight: 700;
  color: var(--ink);
  margin-bottom: 2px;
}
.stage-stats b.up { color: var(--green); }
.sync-line {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--muted);
  margin: 0 0 12px;
}
.stage-cta {
  width: min(100%, 220px);
  margin-bottom: 12px;
}
.stage-live {
  margin-top: auto;
  padding-top: 12px;
  font-size: 12px;
  font-weight: 600;
  color: var(--faint);
}

/* —— 备赛脉搏：活动事实 × 动态缺项 —— */
.readiness-pulse { margin-top: 12px; padding: 18px; border-radius: 20px; display: grid; grid-template-columns: minmax(0, 1.05fr) minmax(420px, 1fr); align-items: stretch; }
.pulse-side { min-width: 0; padding-right: 22px; border-right: 1px solid var(--line); }
.gap-side { min-width: 0; padding-left: 22px; }
.pulse-head, .gap-head { display: flex; align-items: flex-start; gap: 10px 14px; margin-bottom: 12px; }
.pulse-head > div:first-child, .gap-head > div:first-child { margin-right: auto; min-width: 0; }
.pulse-head h3, .gap-head h3 { margin: 0; font-size: 17px; font-weight: 800; letter-spacing: -0.015em; }
.pulse-kicker { margin: 0 0 3px; font-size: 11px; font-weight: 650; color: var(--muted); }
.pulse-link { padding: 4px 0; border: 0; background: none; color: var(--orange); font: 700 12.5px var(--font); cursor: pointer; }
.pulse-body { display: grid; grid-template-columns: minmax(0, 1.35fr) minmax(180px, .75fr); gap: 18px; min-height: 150px; }
.pulse-chart { padding: 13px 14px 10px; border-radius: 14px; background: rgba(255, 255, 255, 0.34); border: 1px solid rgba(120, 90, 70, 0.08); }
.pulse-chart strong { display: block; font-size: 12.5px; font-weight: 750; color: var(--ink-2); }
.pulse-chart svg { display: block; width: 100%; height: 94px; overflow: visible; }
.pulse-area { fill: url(#pulseArea); }
.pulse-line { fill: none; stroke: var(--orange); stroke-width: 2; stroke-linecap: round; stroke-linejoin: round; }
.pulse-dot { fill: #fff; stroke: var(--orange); stroke-width: 2; }
.pulse-axis { display: flex; justify-content: space-between; color: var(--faint); font-size: 10px; font-family: var(--num); }
.pulse-updates { min-width: 0; }
.pulse-subtitle { display: block; margin-bottom: 9px; font-size: 11px; font-weight: 700; color: var(--muted); }
.pulse-updates ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 10px; }
.pulse-updates li { display: flex; align-items: center; gap: 9px; min-width: 0; }
.update-ico { width: 31px; height: 31px; border-radius: 10px; display: grid; place-items: center; flex: 0 0 auto; color: var(--orange-deep); background: var(--orange-wash); }
.update-ico.is-material { color: #277a57; background: #edf8f3; }
.update-ico.is-roadshow { color: #7650b5; background: #f4effb; }
.update-ico svg, .gap-icon svg { width: 16px; height: 16px; fill: none; stroke: currentColor; stroke-width: 1.7; stroke-linecap: round; stroke-linejoin: round; }
.update-copy { min-width: 0; }
.update-copy b, .update-copy small { display: block; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.update-copy b { font-size: 12px; color: var(--ink-2); font-weight: 700; }
.update-copy small { margin-top: 2px; font-size: 10.5px; color: var(--faint); }
.pulse-empty { margin: 12px 0 0; font-size: 12px; line-height: 1.5; color: var(--faint); }
.deadline-chip { flex: 0 0 auto; padding: 5px 9px; border-radius: 999px; font-size: 11px; font-weight: 750; color: var(--muted); background: rgba(255, 255, 255, .48); border: 1px solid var(--line); }
.deadline-chip.is-warning, .deadline-chip.is-late { color: var(--orange-deep); background: var(--orange-wash); }
.gap-cta { flex: 0 0 auto; height: 31px; padding: 0 13px; border: 0; border-radius: 999px; color: #fff; background: var(--orange); font: 700 12px var(--font); cursor: pointer; }
.gap-list { border: 1px solid rgba(120, 90, 70, 0.09); border-radius: 14px; overflow: hidden; background: rgba(255, 255, 255, .28); }
.gap-item { width: 100%; display: grid; grid-template-columns: 6px 34px minmax(0, 1fr) 18px; gap: 9px; align-items: center; min-height: 52px; padding: 8px 12px; border: 0; border-bottom: 1px solid var(--line); background: transparent; color: inherit; text-align: left; font-family: inherit; cursor: pointer; transition: background .2s ease; }
.gap-item:last-child { border-bottom: 0; }
.gap-item:hover, .gap-item:focus-visible { background: rgba(255, 255, 255, .52); outline: none; }
.gap-led { width: 7px; height: 7px; border-radius: 50%; background: #d3a31d; }
.gap-led.is-high { background: var(--orange); }
.gap-led.is-low { background: var(--green); }
.gap-icon { width: 32px; height: 32px; border-radius: 10px; display: grid; place-items: center; color: var(--ink-2); background: rgba(255, 255, 255, .62); border: 1px solid rgba(120, 90, 70, .08); }
.gap-copy { min-width: 0; }
.gap-copy b, .gap-copy small { display: block; }
.gap-copy b { font-size: 12.5px; font-weight: 750; color: var(--ink-2); }
.gap-copy small { margin-top: 2px; font-size: 10.5px; line-height: 1.35; color: var(--muted); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.gap-arrow { width: 16px; height: 16px; fill: none; stroke: var(--muted); stroke-width: 1.8; stroke-linecap: round; stroke-linejoin: round; }
.gap-ready { min-height: 138px; display: flex; align-items: center; justify-content: center; gap: 12px; padding: 22px; border: 1px solid rgba(15, 159, 110, .12); border-radius: 14px; background: rgba(237, 248, 243, .5); }
.gap-ready b, .gap-ready span { display: block; }
.gap-ready b { font-size: 13px; }
.gap-ready span { margin-top: 4px; font-size: 11px; color: var(--muted); }
@media (max-width: 1080px) {
  .readiness-pulse { grid-template-columns: 1fr; }
  .pulse-side { padding-right: 0; padding-bottom: 18px; border-right: 0; border-bottom: 1px solid var(--line); }
  .gap-side { padding: 18px 0 0; }
}
@media (max-width: 680px) {
  .readiness-pulse { padding: 14px; }
  .pulse-body { grid-template-columns: 1fr; }
  .gap-head { flex-wrap: wrap; }
  .gap-head > div:first-child { flex-basis: 100%; }
  .gap-copy small { white-space: normal; }
}
@media (prefers-reduced-motion: reduce) { .gap-item { transition: none; } }

/* —— 下方二栏：等高对齐；左卡时间线可滚动 —— */
.below {
  display: grid;
  grid-template-columns: 1fr 1.15fr;
  gap: 12px;
  margin-top: 12px;
  align-items: stretch;
}
@media (max-width: 900px) {
  .below { grid-template-columns: 1fr; }
}
.panel {
  border-radius: 16px;
  padding: 16px 16px 14px;
  min-height: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
}
.panel-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 4px;
}
.panel-head h3 {
  margin: 0 0 4px;
  font-size: 15px;
  font-weight: 800;
}
.panel-head .why {
  margin: 0;
  font-size: 12.5px;
  color: var(--muted);
  font-weight: 500;
  line-height: 1.45;
  max-width: 28em;
}
.panel-head .link {
  font-size: 12.5px;
  font-weight: 700;
  color: var(--orange);
  white-space: nowrap;
  padding-top: 2px;
  font-family: inherit;
  cursor: pointer;
  background: none;
  border: 0;
}

/* 时间线：左内边距留足，圆点完整可见、不被裁切 */
.panel.is-feed {
  padding-left: 16px;
  padding-right: 12px;
}
.timeline {
  list-style: none;
  margin: 10px 0 0;
  /* 左边多留：圆点半径 + 描边，不被 overflow 裁一半 */
  padding: 2px 6px 2px 10px;
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  overscroll-behavior: contain;
  scrollbar-width: thin;
  scrollbar-color: rgba(120, 90, 70, 0.16) transparent;
}
.timeline::-webkit-scrollbar {
  width: 5px;
}
.timeline::-webkit-scrollbar-thumb {
  background: rgba(120, 90, 70, 0.14);
  border-radius: 999px;
}
.timeline li {
  position: relative;
  padding: 9px 2px 9px 16px;
  border-left: 1.5px solid rgba(120, 90, 70, 0.1);
}
.timeline li:first-child {
  padding-top: 6px;
}
.timeline li:last-child {
  padding-bottom: 4px;
  border-left-color: transparent;
}
.timeline li::before {
  content: "";
  position: absolute;
  left: -4.5px;
  top: 15px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #c5c9d1;
  box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.75);
}
.timeline li:first-child::before {
  top: 12px;
}
.timeline li.ok::before {
  background: var(--green);
  box-shadow: 0 0 0 2px rgba(15, 159, 110, 0.15);
}
.timeline li.warn::before {
  background: var(--orange);
  box-shadow: 0 0 0 2px rgba(232, 74, 28, 0.15);
}
.timeline .row-main {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 8px 10px;
  width: 100%;
  min-width: 0;
  box-sizing: border-box;
}
.timeline .what {
  font-size: 13.5px;
  font-weight: 700;
  color: var(--ink-2);
  line-height: 1.4;
  min-width: 0;
  flex: 1 1 auto;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.timeline .when {
  flex: 0 0 auto;
  max-width: 5.2em;
  font-size: 11.5px;
  font-weight: 600;
  color: var(--faint);
  white-space: nowrap;
  text-align: right;
  overflow: hidden;
  text-overflow: ellipsis;
}

.panel.is-practice {
  background: linear-gradient(
    168deg,
    rgba(255, 255, 255, 0.68) 0%,
    rgba(255, 255, 255, 0.36) 48%,
    rgba(255, 246, 240, 0.22) 100%
  );
}
.practice-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 12px;
}
.practice-item {
  display: grid;
  grid-template-columns: 40px 1fr auto;
  gap: 12px;
  align-items: center;
  padding: 12px;
  border-radius: 14px;
  text-align: left;
  font-family: inherit;
  cursor: pointer;
  color: inherit;
  background: linear-gradient(
    160deg,
    rgba(255, 255, 255, 0.58) 0%,
    rgba(255, 250, 246, 0.28) 100%
  );
  border: 1px solid rgba(255, 255, 255, 0.52);
  box-shadow: 0 4px 14px var(--neo-dark);
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.practice-item:hover {
  transform: translateY(-1px);
  background: linear-gradient(
    160deg,
    rgba(255, 255, 255, 0.72) 0%,
    rgba(255, 250, 246, 0.4) 100%
  );
  box-shadow: 0 8px 22px rgba(232, 74, 28, 0.07);
}
.practice-item .ic {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: grid;
  place-items: center;
  background: #fff4ee;
  color: var(--ink-2);
  box-shadow: none;
}
.practice-item .ic svg {
  width: 20px;
  height: 20px;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.75;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.practice-item.rec .ic {
  background: var(--orange-soft);
  color: var(--orange-deep);
}
.practice-item.on .ic {
  background: #e5f6ef;
  color: var(--green);
}
.practice-item .txt strong {
  display: block;
  font-size: 13.5px;
  font-weight: 800;
  color: var(--ink);
  margin-bottom: 2px;
}
.practice-item .txt span {
  font-size: 12px;
  font-weight: 500;
  color: var(--muted);
  line-height: 1.4;
}
.practice-item .go {
  font-size: 12px;
  font-weight: 700;
  color: var(--orange);
  white-space: nowrap;
}
.practice-item.rec .go { color: var(--orange-deep); }
.practice-tip {
  margin: 12px 0 0;
  padding: 10px 12px;
  border-radius: 10px;
  font-size: 12.5px;
  color: var(--muted);
  font-weight: 500;
  line-height: 1.45;
  background: rgba(255, 248, 244, 0.55);
  border: 1px solid rgba(255, 255, 255, 0.55);
  box-shadow: none;
}
.practice-tip b { color: var(--ink-2); font-weight: 700; }

.appendix-power {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--line);
  font-size: 13px;
  color: var(--faint);
  font-weight: 500;
}
.appendix-label {
  font-size: 11.5px;
  font-weight: 700;
  letter-spacing: 0.06em;
  margin-bottom: 6px;
}
.power-line {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 10px;
  align-items: center;
}
.power-line strong { color: var(--muted); font-weight: 700; }
.power-line .sep { color: var(--line-strong); }
</style>
