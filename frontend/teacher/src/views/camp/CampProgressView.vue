<template>
  <div class="teacher-page progress-page" :class="{ 'is-ready': !loading && hasCamp }">
    <header class="teacher-page__head progress-hero">
      <div>
        <h1>训练进度</h1>
        <p>
          {{ camp.campName || ctx.campName || '训练营' }}
          · {{ camp.teamName || ctx.projectName || '项目' }}
          · 第 {{ currentDayNo }} / {{ days.length || '—' }} 天
        </p>
      </div>
      <div class="teacher-page__actions">
        <button type="button" class="teacher-btn teacher-btn--secondary" :disabled="loading" @click="load">
          {{ loading ? '刷新中…' : '刷新数据' }}
        </button>
        <button
          type="button"
          class="teacher-btn teacher-btn--primary"
          :disabled="sending || !missingCount || !camp.campId"
          @click="remindMissing"
        >
          提醒未交{{ missingCount ? ` · ${missingCount}` : '' }}
        </button>
      </div>
    </header>

    <p v-if="banner" class="plan-notice" :class="{ 'is-error': bannerError }" role="status">{{ banner }}</p>

    <!-- 骨架屏 -->
    <div v-if="loading" class="progress-skeleton" aria-busy="true" aria-label="加载中">
      <div class="sk-row sk-metrics">
        <div v-for="n in 5" :key="n" class="sk-card" />
      </div>
      <div class="sk-row sk-charts">
        <div class="sk-card sk-lg" />
        <div class="sk-card sk-md" />
      </div>
      <div class="sk-card sk-table" />
    </div>

    <template v-else-if="!hasCamp">
      <section class="teacher-card progress-empty">
        <div class="progress-empty__glow" aria-hidden="true" />
        <h2>暂无训练营进度</h2>
        <p>创建训练营并发布每日计划后，这里会呈现提交趋势、完成热力与风险名单。</p>
        <router-link class="teacher-btn teacher-btn--primary" to="/camp/create">创建训练营</router-link>
      </section>
    </template>

    <template v-else>
      <!-- KPI 指标带 -->
      <section class="kpi-strip" aria-label="关键指标">
        <article
          v-for="(kpi, index) in kpis"
          :key="kpi.key"
          class="kpi-card"
          :style="{ '--delay': `${index * 55}ms` }"
        >
          <div class="kpi-card__top">
            <span class="kpi-card__icon" :data-tone="kpi.tone">{{ kpi.icon }}</span>
            <small>{{ kpi.label }}</small>
          </div>
          <div class="kpi-card__value">
            <strong>{{ kpi.display }}</strong>
            <em v-if="kpi.suffix">{{ kpi.suffix }}</em>
          </div>
          <div class="kpi-card__foot">
            <i class="kpi-spark" aria-hidden="true">
              <b :style="{ width: `${kpi.bar}%` }" />
            </i>
            <span>{{ kpi.hint }}</span>
          </div>
        </article>
      </section>

      <!-- 图表区 -->
      <div class="progress-charts">
        <section class="teacher-card glass-card chart-card">
          <div class="teacher-card__head">
            <div>
              <h2>训练完成趋势</h2>
              <p class="card-sub">已开放训练日 · 实时聚合</p>
            </div>
            <div class="seg" role="tablist">
              <button
                type="button"
                role="tab"
                :aria-selected="trendMode === 'rate'"
                :class="{ 'is-active': trendMode === 'rate' }"
                @click="trendMode = 'rate'"
              >
                完成率
              </button>
              <button
                type="button"
                role="tab"
                :aria-selected="trendMode === 'count'"
                :class="{ 'is-active': trendMode === 'count' }"
                @click="trendMode = 'count'"
              >
                提交人数
              </button>
            </div>
          </div>
          <div class="teacher-card__body chart-body">
            <div
              class="trend-chart"
              role="img"
              :aria-label="trendMode === 'rate' ? '完成率趋势' : '提交人数趋势'"
              @mousemove="onChartMove"
              @mouseleave="hoverIndex = -1"
            >
              <!-- 轴标签用 HTML，避免 SVG 拉伸导致文字变形 -->
              <div class="trend-chart__y" aria-hidden="true">
                <span>{{ yAxisTop }}</span>
                <span>{{ yAxisMid }}</span>
                <span>0</span>
              </div>

              <div class="trend-chart__main">
                <div class="trend-chart__plot">
                  <div class="trend-chart__grid" aria-hidden="true">
                    <i /><i /><i /><i />
                  </div>

                  <!-- 仅绘制路径的归一化坐标系；线条用 non-scaling-stroke 防变形 -->
                  <svg
                    v-if="trendPoints.length"
                    class="trend-chart__svg"
                    viewBox="0 0 100 100"
                    preserveAspectRatio="none"
                  >
                    <defs>
                      <linearGradient id="trendAreaFill" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stop-color="rgba(232,74,28,0.22)" />
                        <stop offset="100%" stop-color="rgba(232,74,28,0)" />
                      </linearGradient>
                    </defs>
                    <path v-if="trendAreaPath" class="chart-area" :d="trendAreaPath" fill="url(#trendAreaFill)" />
                    <path
                      v-if="trendPath"
                      class="chart-line"
                      :d="trendPath"
                      fill="none"
                      stroke="var(--ds-orange)"
                      stroke-width="2.25"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      vector-effect="non-scaling-stroke"
                    />
                  </svg>

                  <div
                    v-if="hoverPoint"
                    class="trend-chart__cross"
                    :style="{ left: `${hoverPoint.x}%` }"
                    aria-hidden="true"
                  />

                  <button
                    v-for="(pt, i) in trendPoints"
                    :key="pt.dayNo"
                    type="button"
                    class="trend-chart__dot"
                    :class="{ 'is-hot': hoverIndex === i }"
                    :style="{ left: `${pt.x}%`, top: `${pt.y}%` }"
                    :aria-label="`第 ${pt.dayNo} 天 ${pt.valueLabel}`"
                    @mouseenter="hoverIndex = i"
                    @focus="hoverIndex = i"
                  />

                  <div
                    v-if="hoverPoint"
                    class="chart-tip"
                    :style="{ left: `${hoverPoint.x}%` }"
                  >
                    <strong>第 {{ hoverPoint.dayNo }} 天</strong>
                    <span>{{ hoverPoint.valueLabel }}</span>
                  </div>

                  <div v-if="!trendPoints.length" class="chart-empty">暂无已开放训练日数据</div>
                </div>

                <div class="trend-chart__x" aria-hidden="true">
                  <span
                    v-for="pt in trendPoints"
                    :key="`x-${pt.dayNo}`"
                    :style="{ left: `${pt.x}%` }"
                    :class="{ 'is-hot': hoverPoint?.dayNo === pt.dayNo }"
                  >
                    D{{ pt.dayNo }}
                  </span>
                </div>
              </div>
            </div>
          </div>
        </section>

        <section class="teacher-card glass-card">
          <div class="teacher-card__head">
            <div>
              <h2>当日提交分布</h2>
              <p class="card-sub">第 {{ currentDayNo }} 天 · 环形视图</p>
            </div>
          </div>
          <div class="teacher-card__body donut-panel">
            <div class="donut-wrap">
              <svg viewBox="0 0 120 120" class="donut-svg" aria-hidden="true">
                <circle class="donut-track" cx="60" cy="60" r="46" />
                <circle
                  v-for="seg in donutSegments"
                  :key="seg.key"
                  class="donut-seg"
                  cx="60"
                  cy="60"
                  r="46"
                  :stroke="seg.color"
                  :stroke-dasharray="seg.dash"
                  :stroke-dashoffset="seg.offset"
                  :style="{ '--seg-delay': seg.delay }"
                />
              </svg>
              <div class="donut-center">
                <strong>{{ rows.length }}</strong>
                <small>参训</small>
              </div>
            </div>
            <div class="dist-legend">
              <div v-for="item in distribution" :key="item.key" class="dist-row">
                <i :style="{ background: item.color }" />
                <span>{{ item.label }}</span>
                <b>{{ item.count }}</b>
                <em>{{ item.pct }}%</em>
              </div>
            </div>
          </div>
        </section>
      </div>

      <!-- 中段 -->
      <div class="progress-mid">
        <section class="teacher-card glass-card">
          <div class="teacher-card__head">
            <div>
              <h2>学生完成率</h2>
              <p class="card-sub">按已开放训练日 · 低→高</p>
            </div>
          </div>
          <div class="teacher-card__body rate-list">
            <div
              v-for="(row, i) in memberRates"
              :key="row.userId"
              class="rate-row"
              :style="{ '--delay': `${i * 30}ms` }"
            >
              <span class="rate-avatar" :data-tone="row.rate >= 80 ? 'ok' : row.rate >= 40 ? 'mid' : 'low'">
                {{ avatarText(row.username) }}
              </span>
              <div class="rate-meta">
                <strong>{{ row.username }}</strong>
                <small>{{ row.positionName || '成员' }}</small>
              </div>
              <div class="rate-bar" aria-hidden="true">
                <b :style="{ width: animateBars ? `${row.rate}%` : '0%' }" />
              </div>
              <em>{{ row.rate }}%</em>
            </div>
            <div v-if="!memberRates.length" class="teacher-empty soft-empty">暂无成员</div>
          </div>
        </section>

        <section class="teacher-card glass-card missing-card">
          <div class="teacher-card__head">
            <div>
              <h2>学生缺交情况</h2>
              <p class="card-sub">按「已开放训练日里未交了几天」分组，看有多少人</p>
            </div>
          </div>
          <div class="teacher-card__body">
            <p class="missing-explain">
              每位学生统计：在已开放的训练日中，有几天是<strong>未提交 / 已过期</strong>。
              缺得越多，越需要老师催交或一对一跟进。
            </p>
            <div class="missing-rows">
              <div
                v-for="(bucket, i) in missingBuckets"
                :key="bucket.key"
                class="missing-row"
                :data-level="bucket.level"
                :style="{ '--delay': `${i * 50}ms` }"
              >
                <div class="missing-row__label">
                  <strong>{{ bucket.title }}</strong>
                  <small>{{ bucket.desc }}</small>
                </div>
                <div class="missing-row__bar" aria-hidden="true">
                  <i :style="{ width: animateBars ? `${bucket.width}%` : '0%' }" />
                </div>
                <div class="missing-row__count">
                  <em>{{ bucket.count }}</em>
                  <span>人</span>
                </div>
                <span class="missing-row__tag">{{ bucket.tag }}</span>
              </div>
            </div>
            <p class="missing-summary">
              <template v-if="missingStudentCount">
                共 <b>{{ missingStudentCount }}</b> 人存在缺交；
                建议优先处理「缺交 2 天及以上」的
                <b>{{ highRiskMissingCount }}</b> 人。
              </template>
              <template v-else>
                目前所有学生在已开放训练日均已提交，无需催交。
              </template>
            </p>
          </div>
        </section>

        <section class="teacher-card glass-card focus-card">
          <div class="teacher-card__head">
            <div>
              <h2>当前需关注</h2>
              <p class="card-sub">缺交天数多的学生优先</p>
            </div>
            <router-link class="teacher-link" to="/camp/review-queue">去批改 →</router-link>
          </div>
          <div class="teacher-card__body focus-list">
            <article
              v-for="(row, i) in focusRows"
              :key="row.userId"
              class="focus-item"
              :style="{ '--delay': `${i * 40}ms` }"
            >
              <span class="rate-avatar" data-tone="low">{{ avatarText(row.username) }}</span>
              <div>
                <strong>{{ row.username }}</strong>
                <small>{{ row.positionName || '成员' }} · 完成率 {{ row.rate }}%</small>
              </div>
              <span class="focus-tag">缺 {{ row.missing }} 天</span>
            </article>
            <div v-if="!focusRows.length" class="focus-ok">
              <span>✓</span>
              <p>当前没有高风险缺交学生</p>
            </div>
          </div>
        </section>
      </div>

      <!-- 热力矩阵 -->
      <section class="teacher-card glass-card matrix-card">
        <div class="teacher-card__head">
          <div>
            <h2>成员 × 训练日热力</h2>
            <p class="card-sub">近 {{ matrixDays.length }} 个已开放日 · 悬停查看状态</p>
          </div>
          <div class="heat-legend" aria-label="图例">
            <span><i class="is-ok" />已通过</span>
            <span><i class="is-pending" />待批</span>
            <span><i class="is-revise" />需改</span>
            <span><i class="is-miss" />未交</span>
          </div>
        </div>
        <div class="teacher-card__body matrix-scroll">
          <table v-if="rows.length" class="heat-table">
            <thead>
              <tr>
                <th class="sticky-col">成员</th>
                <th>岗位</th>
                <th v-for="day in matrixDays" :key="day.dayId" class="day-col">
                  <span>D{{ day.dayNo }}</span>
                </th>
                <th>进度</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(row, ri) in rows" :key="row.userId" :style="{ '--delay': `${ri * 25}ms` }">
                <td class="sticky-col member-cell">
                  <span class="rate-avatar is-sm">{{ avatarText(row.username) }}</span>
                  {{ row.username }}
                </td>
                <td class="pos-cell">{{ row.positionName || '—' }}</td>
                <td
                  v-for="day in matrixDays"
                  :key="`${row.userId}-${day.dayId}`"
                  class="heat-cell"
                >
                  <button
                    type="button"
                    class="heat-dot"
                    :class="cellClass(dayState(row, day.dayNo))"
                    :title="`第${day.dayNo}天 · ${statusLabel(dayState(row, day.dayNo))}`"
                  >
                    <span class="sr-only">{{ statusLabel(dayState(row, day.dayNo)) }}</span>
                  </button>
                </td>
                <td class="prog-cell">
                  <span class="mini-bar"><b :style="{ width: animateBars ? `${memberRateMap[row.userId] || 0}%` : '0%' }" /></span>
                  <em>{{ row.submittedDays || 0 }}/{{ openDayCount }}</em>
                </td>
              </tr>
            </tbody>
          </table>
          <div v-else class="teacher-empty soft-empty">暂无成员进度</div>
        </div>
      </section>
    </template>
  </div>
</template>

<script setup>
import { computed, nextTick, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { fetchTeacherCamp, sendTeacherReminder } from '../../api'
import { useTeacherContextStore } from '../../stores/context'

const route = useRoute()
const ctx = useTeacherContextStore()

const loading = ref(true)
const sending = ref(false)
const banner = ref('')
const bannerError = ref(false)
const hasCamp = ref(false)
const rows = ref([])
const days = ref([])
const camp = ref({})
const trendMode = ref('rate')
const hoverIndex = ref(-1)
const animateBars = ref(false)

const currentDayNo = computed(() => Number(camp.value.currentDay) || days.value[0]?.dayNo || 1)
const openDayCount = computed(() => {
  const cur = currentDayNo.value
  return days.value.filter((d) => Number(d.dayNo) <= cur).length || days.value.length
})
const publishedDays = computed(() => days.value.filter((d) => String(d.status).toUpperCase() === 'PUBLISHED').length)

const matrixDays = computed(() => {
  const cur = currentDayNo.value
  return days.value.filter((d) => Number(d.dayNo) <= cur).slice(-12)
})

function dayState(member, dayNo) {
  const d = (member.days || []).find((x) => Number(x.dayNo) === Number(dayNo))
  return d?.status || 'NOT_SUBMITTED'
}

function isSubmitted(status) {
  return !['NOT_SUBMITTED', 'EXPIRED'].includes(String(status || '').toUpperCase())
}

function isPending(status) {
  return ['PENDING_REVIEW', 'REVIEWING'].includes(String(status || '').toUpperCase())
}

function isMissing(status) {
  return ['NOT_SUBMITTED', 'EXPIRED'].includes(String(status || '').toUpperCase())
}

const dayStats = computed(() => {
  const cur = currentDayNo.value
  return days.value
    .filter((d) => Number(d.dayNo) <= cur)
    .map((day) => {
      const dayNo = Number(day.dayNo)
      let submitted = 0
      let pending = 0
      let missing = 0
      rows.value.forEach((member) => {
        const st = dayState(member, dayNo)
        if (isSubmitted(st)) submitted += 1
        if (isPending(st)) pending += 1
        if (isMissing(st)) missing += 1
      })
      const total = rows.value.length || 1
      return {
        dayNo,
        submitted,
        pending,
        missing,
        rate: Math.round((submitted / total) * 100),
      }
    })
})

const maxSubmitCount = computed(() => Math.max(1, ...dayStats.value.map((d) => d.submitted), rows.value.length || 1))

const yAxisTop = computed(() => (trendMode.value === 'rate' ? '100%' : String(maxSubmitCount.value)))
const yAxisMid = computed(() => {
  if (trendMode.value === 'rate') return '50%'
  return String(Math.round(maxSubmitCount.value / 2))
})

/** 绘图内边距：避免 0/100% 数据点贴边被 overflow 裁掉半个圆 */
const PLOT_PAD_X = 3
const PLOT_PAD_Y = 5

/** 归一化到 0–100 的绘图坐标（x 左→右，y 上=0 下=100），避免 SVG 文字被拉伸 */
const trendPoints = computed(() => {
  const stats = dayStats.value
  if (!stats.length) return []
  const n = stats.length
  const padX = n === 1 ? 50 : PLOT_PAD_X
  const yMin = PLOT_PAD_Y
  const yMax = 100 - PLOT_PAD_Y
  return stats.map((s, i) => {
    const ratio = trendMode.value === 'rate' ? s.rate / 100 : s.submitted / maxSubmitCount.value
    const t = Math.max(0, Math.min(1, ratio))
    const x = n === 1 ? 50 : padX + ((100 - padX * 2) * i) / (n - 1)
    // 0 值落在 yMax（靠下但不贴边），100% 落在 yMin
    const y = yMax - t * (yMax - yMin)
    const value = trendMode.value === 'rate' ? s.rate : s.submitted
    return {
      x,
      y,
      dayNo: s.dayNo,
      value,
      valueLabel: trendMode.value === 'rate' ? `${value}% 完成` : `${value} 人提交`,
    }
  })
})

function clamp(n, min, max) {
  return Math.max(min, Math.min(max, n))
}

/** 平滑三次贝塞尔；控制点 Y 钳制在 0–100，避免曲线出框 */
function buildSmoothPath(pts) {
  if (!pts.length) return ''
  if (pts.length === 1) return `M ${pts[0].x.toFixed(2)} ${pts[0].y.toFixed(2)}`
  if (pts.length === 2) {
    return `M ${pts[0].x.toFixed(2)} ${pts[0].y.toFixed(2)} L ${pts[1].x.toFixed(2)} ${pts[1].y.toFixed(2)}`
  }
  let d = `M ${pts[0].x.toFixed(2)} ${pts[0].y.toFixed(2)}`
  for (let i = 0; i < pts.length - 1; i += 1) {
    const p0 = pts[i === 0 ? 0 : i - 1]
    const p1 = pts[i]
    const p2 = pts[i + 1]
    const p3 = pts[i + 2] || p2
    const cp1x = p1.x + (p2.x - p0.x) / 6
    const cp1y = clamp(p1.y + (p2.y - p0.y) / 6, 0, 100)
    const cp2x = p2.x - (p3.x - p1.x) / 6
    const cp2y = clamp(p2.y - (p3.y - p1.y) / 6, 0, 100)
    d += ` C ${cp1x.toFixed(2)} ${cp1y.toFixed(2)}, ${cp2x.toFixed(2)} ${cp2y.toFixed(2)}, ${p2.x.toFixed(2)} ${p2.y.toFixed(2)}`
  }
  return d
}

const trendPath = computed(() => buildSmoothPath(trendPoints.value))

const trendAreaPath = computed(() => {
  const pts = trendPoints.value
  if (!pts.length) return ''
  const line = buildSmoothPath(pts)
  if (!line) return ''
  // 面积落到绘图底边（与 0 轴对齐的内边距底线）
  const baseY = 100 - PLOT_PAD_Y
  return `${line} L ${pts[pts.length - 1].x.toFixed(2)} ${baseY.toFixed(2)} L ${pts[0].x.toFixed(2)} ${baseY.toFixed(2)} Z`
})

const hoverPoint = computed(() => (hoverIndex.value >= 0 ? trendPoints.value[hoverIndex.value] : null))

function onChartMove(event) {
  const pts = trendPoints.value
  if (!pts.length) return
  const plot = event.currentTarget.querySelector('.trend-chart__plot')
  if (!plot) return
  const rect = plot.getBoundingClientRect()
  if (!rect.width) return
  const xPct = ((event.clientX - rect.left) / rect.width) * 100
  let best = 0
  let bestDist = Infinity
  pts.forEach((p, i) => {
    const d = Math.abs(p.x - xPct)
    if (d < bestDist) {
      bestDist = d
      best = i
    }
  })
  hoverIndex.value = best
}

const distribution = computed(() => {
  const dayNo = currentDayNo.value
  let complete = 0
  let pending = 0
  let missing = 0
  let revise = 0
  rows.value.forEach((m) => {
    const st = String(dayState(m, dayNo)).toUpperCase()
    if (st === 'APPROVED') complete += 1
    else if (st === 'CHANGES_REQUESTED') revise += 1
    else if (isPending(st)) pending += 1
    else missing += 1
  })
  const total = Math.max(1, rows.value.length)
  return [
    { key: 'ok', label: '已通过', count: complete, color: '#0f9f6e', pct: Math.round((complete / total) * 100) },
    { key: 'pending', label: '待批改', count: pending, color: '#e84a1c', pct: Math.round((pending / total) * 100) },
    { key: 'revise', label: '需修改', count: revise, color: '#d98200', pct: Math.round((revise / total) * 100) },
    { key: 'missing', label: '未提交', count: missing, color: '#c5c9d1', pct: Math.round((missing / total) * 100) },
  ]
})

/** SVG 圆环：周长 2πr ≈ 289 */
const DONUT_C = 2 * Math.PI * 46
const donutSegments = computed(() => {
  const total = Math.max(1, rows.value.length)
  let acc = 0
  return distribution.value
    .filter((d) => d.count > 0)
    .map((item, i) => {
      const len = (item.count / total) * DONUT_C
      const offset = DONUT_C * 0.25 - acc
      acc += len
      return {
        key: item.key,
        color: item.color,
        dash: `${len} ${DONUT_C - len}`,
        offset,
        delay: `${i * 80}ms`,
      }
    })
})

const memberRates = computed(() => {
  const open = openDayCount.value || 1
  return rows.value
    .map((m) => {
      const submitted = Number(m.submittedDays || 0)
      const rate = Math.round((submitted / open) * 100)
      const missing = (m.days || []).filter((d) => Number(d.dayNo) <= currentDayNo.value && isMissing(d.status)).length
      return {
        userId: m.userId,
        username: m.username,
        positionName: m.positionName,
        rate: Math.min(100, rate),
        missing,
      }
    })
    .sort((a, b) => a.rate - b.rate)
})

const memberRateMap = computed(() => {
  const map = {}
  memberRates.value.forEach((m) => {
    map[m.userId] = m.rate
  })
  return map
})

const missingBuckets = computed(() => {
  const counts = [0, 0, 0, 0]
  memberRates.value.forEach((m) => {
    if (m.missing <= 0) counts[0] += 1
    else if (m.missing === 1) counts[1] += 1
    else if (m.missing === 2) counts[2] += 1
    else counts[3] += 1
  })
  const max = Math.max(1, ...counts)
  const defs = [
    {
      key: 'ok',
      level: 'ok',
      title: '全部交齐',
      desc: '已开放日均已提交',
      tag: '正常',
    },
    {
      key: 'm1',
      level: 'low',
      title: '缺交 1 天',
      desc: '偶发漏交，可提醒',
      tag: '留意',
    },
    {
      key: 'm2',
      level: 'mid',
      title: '缺交 2 天',
      desc: '连续风险上升',
      tag: '催交',
    },
    {
      key: 'm3',
      level: 'high',
      title: '缺交 3 天及以上',
      desc: '建议重点跟进',
      tag: '重点',
    },
  ]
  return defs.map((d, i) => ({
    ...d,
    count: counts[i],
    width: counts[i] ? Math.max(8, Math.round((counts[i] / max) * 100)) : 0,
  }))
})

const missingStudentCount = computed(() =>
  memberRates.value.filter((m) => m.missing > 0).length
)
const highRiskMissingCount = computed(() =>
  memberRates.value.filter((m) => m.missing >= 2).length
)

const focusRows = computed(() =>
  memberRates.value
    .filter((m) => m.missing > 0)
    .sort((a, b) => b.missing - a.missing || a.rate - b.rate)
    .slice(0, 6)
)

const overallSubmitRate = computed(() => {
  if (!dayStats.value.length) return 0
  const avg = dayStats.value.reduce((s, d) => s + d.rate, 0) / dayStats.value.length
  return Math.round(avg)
})

const pendingReviewCount = computed(() =>
  rows.value.reduce((sum, m) => sum + (m.days || []).filter((d) => isPending(d.status)).length, 0)
)

const riskCount = computed(() => memberRates.value.filter((m) => m.missing >= 2).length)
const missingCount = computed(() =>
  rows.value.filter((r) => isMissing(dayState(r, currentDayNo.value))).length
)

const kpis = computed(() => [
  {
    key: 'students',
    label: '参训学生',
    display: rows.value.length,
    suffix: '人',
    hint: '当前项目成员',
    bar: Math.min(100, rows.value.length * 12),
    tone: 'ink',
    icon: '人',
  },
  {
    key: 'days',
    label: '已发布训练日',
    display: `${publishedDays.value}`,
    suffix: `/ ${days.value.length}`,
    hint: '计划发布进度',
    bar: days.value.length ? Math.round((publishedDays.value / days.value.length) * 100) : 0,
    tone: 'blue',
    icon: '日',
  },
  {
    key: 'rate',
    label: '整体提交率',
    display: overallSubmitRate.value,
    suffix: '%',
    hint: '开放日均值',
    bar: overallSubmitRate.value,
    tone: 'green',
    icon: '率',
  },
  {
    key: 'pending',
    label: '待批改',
    display: pendingReviewCount.value,
    suffix: '份',
    hint: '队列积压',
    bar: Math.min(100, pendingReviewCount.value * 8),
    tone: 'orange',
    icon: '批',
  },
  {
    key: 'risk',
    label: '连续缺交风险',
    display: riskCount.value,
    suffix: '人',
    hint: '缺交 ≥ 2 天',
    bar: rows.value.length ? Math.round((riskCount.value / rows.value.length) * 100) : 0,
    tone: 'warn',
    icon: '险',
  },
])

function avatarText(name) {
  const s = String(name || '?').trim()
  return s.slice(0, 1)
}

function statusLabel(status) {
  const map = {
    APPROVED: '已通过',
    PENDING_REVIEW: '待批',
    REVIEWING: '批改中',
    CHANGES_REQUESTED: '需改',
    EXPIRED: '过期',
    NOT_SUBMITTED: '未交',
  }
  const s = String(status || '').toUpperCase()
  return map[s] || (/[\u4e00-\u9fff]/.test(String(status || '')) ? status : '—')
}

function cellClass(status) {
  const s = String(status || '').toUpperCase()
  if (isMissing(s)) return 'is-miss'
  if (isPending(s)) return 'is-pending'
  if (s === 'CHANGES_REQUESTED') return 'is-revise'
  if (s === 'APPROVED') return 'is-ok'
  return ''
}

async function remindMissing() {
  if (!camp.value.campId) return
  sending.value = true
  bannerError.value = false
  try {
    const res = await sendTeacherReminder({
      targetType: 'TRAINING_CAMP',
      targetId: camp.value.campId,
      message: '你有训练任务尚未提交，请在截止日期前完成。',
    })
    banner.value = `已发送催交提醒，触达 ${res?.recipientCount ?? 0} 人`
  } catch (err) {
    bannerError.value = true
    banner.value = err?.response?.data?.message || err?.message || '提醒失败'
  } finally {
    sending.value = false
  }
}

async function load() {
  loading.value = true
  animateBars.value = false
  banner.value = ''
  bannerError.value = false
  try {
    const data = await fetchTeacherCamp(route.query.campId || ctx.campId || '')
    hasCamp.value = Boolean(data?.hasCamp)
    rows.value = data?.progress || []
    days.value = data?.days || []
    camp.value = data?.camp || {}
  } catch (err) {
    hasCamp.value = false
    rows.value = []
    days.value = []
    camp.value = {}
    bannerError.value = true
    banner.value = err?.response?.data?.message || err?.message || '训练进度加载失败'
  } finally {
    loading.value = false
    await nextTick()
    requestAnimationFrame(() => {
      animateBars.value = true
    })
  }
}

watch(() => [route.query.campId, ctx.campId, ctx.loaded], load, { immediate: true })
</script>

<style scoped>
.progress-page {
  max-width: 1400px;
}

.progress-hero h1 {
  letter-spacing: -0.03em;
}

.plan-notice {
  margin: 0 0 14px;
  padding: 11px 14px;
  border-radius: 11px;
  color: #0b7753;
  background: #e5f6ef;
  font-size: 12px;
  font-weight: 700;
  animation: fade-up 0.28s ease both;
}
.plan-notice.is-error {
  color: #a33a24;
  background: #fff0ec;
}

/* —— 骨架 —— */
.progress-skeleton {
  display: grid;
  gap: 14px;
}
.sk-row {
  display: grid;
  gap: 12px;
}
.sk-metrics {
  grid-template-columns: repeat(5, minmax(0, 1fr));
}
.sk-charts {
  grid-template-columns: 1.4fr 0.8fr;
}
.sk-card {
  min-height: 108px;
  border-radius: 16px;
  background: linear-gradient(90deg, #eceef1 0%, #f7f8fa 45%, #eceef1 90%);
  background-size: 200% 100%;
  animation: shimmer 1.2s ease infinite;
}
.sk-lg { min-height: 320px; }
.sk-md { min-height: 320px; }
.sk-table { min-height: 240px; }

.progress-empty {
  position: relative;
  overflow: hidden;
  padding: 56px 28px;
  text-align: center;
}
.progress-empty__glow {
  position: absolute;
  inset: -40% auto auto 50%;
  width: 280px;
  height: 280px;
  transform: translateX(-50%);
  border-radius: 50%;
  background: radial-gradient(circle, rgba(232, 74, 28, 0.14), transparent 70%);
  pointer-events: none;
}
.progress-empty h2 {
  margin: 0 0 8px;
  position: relative;
}
.progress-empty p {
  margin: 0 auto 18px;
  max-width: 420px;
  color: var(--ds-muted);
  position: relative;
}

/* —— KPI —— */
.kpi-strip {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}
.kpi-card {
  position: relative;
  overflow: hidden;
  padding: 14px 16px 12px;
  border-radius: 16px;
  border: 1px solid rgba(29, 29, 31, 0.06);
  background:
    linear-gradient(165deg, rgba(255, 255, 255, 0.95), rgba(255, 255, 255, 0.82)),
    var(--ds-card-bg);
  box-shadow: 0 1px 2px rgba(18, 20, 26, 0.04), 0 10px 28px rgba(18, 20, 26, 0.035);
  opacity: 0;
  transform: translateY(12px);
  animation: fade-up 0.45s cubic-bezier(0.22, 1, 0.36, 1) forwards;
  animation-delay: var(--delay, 0ms);
  transition: transform 0.22s ease, box-shadow 0.22s ease, border-color 0.22s ease;
}
.kpi-card::after {
  content: '';
  position: absolute;
  right: -20px;
  top: -24px;
  width: 88px;
  height: 88px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(232, 74, 28, 0.08), transparent 70%);
  pointer-events: none;
}
.kpi-card:hover {
  transform: translateY(-2px);
  border-color: rgba(232, 74, 28, 0.18);
  box-shadow: 0 12px 32px rgba(18, 20, 26, 0.07);
}
.kpi-card__top {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.kpi-card__top small {
  color: var(--ds-muted);
  font-size: 12px;
  font-weight: 700;
}
.kpi-card__icon {
  width: 28px;
  height: 28px;
  border-radius: 9px;
  display: grid;
  place-items: center;
  font-size: 12px;
  font-weight: 800;
  background: #f1f2f4;
  color: #4b515a;
}
.kpi-card__icon[data-tone='orange'],
.kpi-card__icon[data-tone='warn'] {
  background: var(--ds-orange-wash);
  color: var(--ds-orange-deep);
}
.kpi-card__icon[data-tone='green'] {
  background: #e5f6ef;
  color: #0b7753;
}
.kpi-card__icon[data-tone='blue'] {
  background: #eef3ff;
  color: #3558c7;
}
.kpi-card__value {
  display: flex;
  align-items: baseline;
  gap: 4px;
}
.kpi-card__value strong {
  font-size: 28px;
  font-family: var(--ds-font-num);
  letter-spacing: -0.03em;
  line-height: 1;
  color: var(--ds-ink);
}
.kpi-card__value em {
  font-style: normal;
  color: var(--ds-muted);
  font-size: 13px;
  font-weight: 700;
}
.kpi-card__foot {
  display: grid;
  gap: 6px;
  margin-top: 12px;
}
.kpi-card__foot span {
  color: var(--ds-faint);
  font-size: 11px;
}
.kpi-spark {
  display: block;
  height: 4px;
  border-radius: 99px;
  background: #eef0f2;
  overflow: hidden;
}
.kpi-spark b {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, var(--ds-orange), #ff8a5c);
  transition: width 0.8s cubic-bezier(0.22, 1, 0.36, 1);
}

.glass-card {
  border: 1px solid rgba(29, 29, 31, 0.06);
  background: rgba(255, 255, 255, 0.88);
  backdrop-filter: blur(10px);
  box-shadow: 0 1px 2px rgba(18, 20, 26, 0.03), 0 14px 36px rgba(18, 20, 26, 0.04);
  transition: transform 0.22s ease, box-shadow 0.22s ease, border-color 0.22s ease;
}
.glass-card:hover {
  border-color: rgba(29, 29, 31, 0.1);
  box-shadow: 0 16px 40px rgba(18, 20, 26, 0.06);
}

.card-sub {
  margin: 4px 0 0;
  color: var(--ds-faint);
  font-size: 12px;
  font-weight: 500;
}

.progress-charts {
  display: grid;
  grid-template-columns: minmax(0, 1.45fr) minmax(300px, 0.75fr);
  gap: 14px;
  margin-bottom: 14px;
}
.progress-mid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 14px;
}

.seg {
  display: flex;
  gap: 3px;
  padding: 3px;
  border-radius: 11px;
  background: #f0f1f3;
}
.seg button {
  min-height: 32px;
  padding: 0 12px;
  border: 0;
  border-radius: 9px;
  background: transparent;
  font-size: 12px;
  font-weight: 700;
  color: var(--ds-muted);
  cursor: pointer;
  transition: background 0.18s ease, color 0.18s ease, box-shadow 0.18s ease, transform 0.15s ease;
}
.seg button:hover {
  color: var(--ds-ink-2);
}
.seg button.is-active {
  background: #fff;
  color: var(--ds-ink);
  box-shadow: 0 2px 8px rgba(30, 35, 42, 0.1);
}

.chart-body {
  padding-top: 4px;
  padding-bottom: 8px;
}

/* 趋势图：HTML 坐标轴 + 归一化 SVG 路径，文字不再被拉伸 */
.trend-chart {
  display: grid;
  grid-template-columns: 44px minmax(0, 1fr);
  gap: 8px;
  min-height: 260px;
  user-select: none;
}
.trend-chart__y {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding: 4px 0 28px;
  text-align: right;
  color: #9aa1ad;
  font-size: 11px;
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  line-height: 1;
}
.trend-chart__main {
  min-width: 0;
  display: grid;
  grid-template-rows: minmax(0, 1fr) 24px;
  gap: 6px;
}
.trend-chart__plot {
  position: relative;
  min-height: 220px;
  border-radius: 12px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.6), rgba(248, 249, 250, 0.9));
  border: 1px solid rgba(29, 29, 31, 0.05);
  /* 可见溢出，避免贴边圆点被裁半；tooltip 仍在 plot 内定位 */
  overflow: visible;
}
.trend-chart__grid {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  pointer-events: none;
  padding: 0;
}
.trend-chart__grid i {
  display: block;
  height: 1px;
  background: rgba(28, 26, 22, 0.06);
}
.trend-chart__grid i:nth-child(2),
.trend-chart__grid i:nth-child(3) {
  background: repeating-linear-gradient(
    90deg,
    rgba(28, 26, 22, 0.05) 0 4px,
    transparent 4px 9px
  );
  height: 1px;
}
.trend-chart__svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  overflow: visible;
}
.chart-line {
  opacity: 0;
  animation: fade-in 0.45s ease 0.08s forwards;
}
.chart-area {
  opacity: 0;
  animation: fade-in 0.55s ease 0.12s forwards;
}
.trend-chart__cross {
  position: absolute;
  top: 0;
  bottom: 0;
  width: 1px;
  background: rgba(232, 74, 28, 0.28);
  transform: translateX(-50%);
  pointer-events: none;
  z-index: 1;
}
.trend-chart__dot {
  position: absolute;
  width: 6px;
  height: 6px;
  margin: 0;
  padding: 0;
  border: 1.5px solid var(--ds-orange);
  border-radius: 50%;
  background: #fff;
  transform: translate(-50%, -50%);
  box-shadow: none;
  cursor: pointer;
  z-index: 2;
  transition: transform 0.12s ease, background 0.12s ease, box-shadow 0.12s ease;
}
.trend-chart__dot:hover,
.trend-chart__dot.is-hot {
  background: var(--ds-orange);
  transform: translate(-50%, -50%) scale(1.35);
  box-shadow: 0 0 0 3px rgba(232, 74, 28, 0.14);
}
.trend-chart__x {
  position: relative;
  height: 22px;
}
.trend-chart__x span {
  position: absolute;
  top: 0;
  transform: translateX(-50%);
  color: #9aa1ad;
  font-size: 11px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  transition: color 0.15s ease;
}
.trend-chart__x span.is-hot {
  color: var(--ds-orange-deep);
}
.chart-tip {
  position: absolute;
  top: 10px;
  transform: translateX(-50%);
  padding: 8px 11px;
  border-radius: 10px;
  background: rgba(18, 20, 26, 0.92);
  color: #fff;
  font-size: 12px;
  pointer-events: none;
  box-shadow: 0 10px 28px rgba(0, 0, 0, 0.18);
  animation: fade-in 0.12s ease both;
  white-space: nowrap;
  z-index: 3;
}
.chart-tip strong {
  display: block;
  font-size: 12px;
}
.chart-tip span {
  opacity: 0.88;
  font-size: 11px;
}
.chart-empty {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  color: var(--ds-muted);
  font-size: 13px;
}

/* 环形图 */
.donut-panel {
  display: grid;
  grid-template-columns: 150px 1fr;
  gap: 18px;
  align-items: center;
  min-height: 240px;
}
.donut-wrap {
  position: relative;
  width: 140px;
  height: 140px;
}
.donut-svg {
  width: 100%;
  height: 100%;
  transform: rotate(-90deg);
}
.donut-track {
  fill: none;
  stroke: #eef0f2;
  stroke-width: 12;
}
.donut-seg {
  fill: none;
  stroke-width: 12;
  stroke-linecap: butt;
  transform-origin: 60px 60px;
  animation: donut-in 0.85s cubic-bezier(0.22, 1, 0.36, 1) both;
  animation-delay: var(--seg-delay, 0ms);
}
.donut-center {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  text-align: center;
  pointer-events: none;
}
.donut-center strong {
  font-size: 26px;
  font-family: var(--ds-font-num);
  line-height: 1;
}
.donut-center small {
  margin-top: 4px;
  color: var(--ds-muted);
  font-size: 11px;
  font-weight: 700;
}
.dist-legend {
  display: grid;
  gap: 10px;
}
.dist-row {
  display: grid;
  grid-template-columns: 10px minmax(0, 1fr) auto auto;
  gap: 8px;
  align-items: center;
  font-size: 13px;
  padding: 8px 10px;
  border-radius: 10px;
  background: #fafafa;
  transition: background 0.15s ease, transform 0.15s ease;
}
.dist-row:hover {
  background: #f3f4f6;
  transform: translateX(2px);
}
.dist-row i {
  width: 10px;
  height: 10px;
  border-radius: 99px;
}
.dist-row b {
  font-variant-numeric: tabular-nums;
  font-weight: 800;
}
.dist-row em {
  font-style: normal;
  color: var(--ds-faint);
  font-size: 12px;
  min-width: 36px;
  text-align: right;
}

/* 完成率列表 */
.rate-list {
  display: grid;
  gap: 10px;
  max-height: 320px;
  overflow: auto;
}
.rate-row {
  display: grid;
  grid-template-columns: 34px minmax(64px, 0.7fr) minmax(0, 1.2fr) 40px;
  gap: 10px;
  align-items: center;
  padding: 8px;
  border-radius: 12px;
  opacity: 0;
  transform: translateY(8px);
  animation: fade-up 0.4s cubic-bezier(0.22, 1, 0.36, 1) forwards;
  animation-delay: var(--delay, 0ms);
  transition: background 0.15s ease;
}
.rate-row:hover {
  background: #f7f8f9;
}
.rate-avatar {
  width: 34px;
  height: 34px;
  border-radius: 11px;
  display: grid;
  place-items: center;
  font-size: 13px;
  font-weight: 800;
  background: #eceef0;
  color: #4b515a;
}
.rate-avatar.is-sm {
  width: 28px;
  height: 28px;
  border-radius: 9px;
  font-size: 12px;
}
.rate-avatar[data-tone='ok'] {
  background: #e5f6ef;
  color: #0b7753;
}
.rate-avatar[data-tone='mid'] {
  background: #fff4e5;
  color: #b77400;
}
.rate-avatar[data-tone='low'] {
  background: var(--ds-orange-wash);
  color: var(--ds-orange-deep);
}
.rate-meta strong {
  display: block;
  font-size: 13px;
}
.rate-meta small {
  display: block;
  margin-top: 2px;
  color: var(--ds-faint);
  font-size: 11px;
}
.rate-bar {
  height: 8px;
  border-radius: 99px;
  background: #eceef0;
  overflow: hidden;
}
.rate-bar b {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #ff8a5c, var(--ds-orange));
  transition: width 0.85s cubic-bezier(0.22, 1, 0.36, 1);
}
.rate-row em {
  font-style: normal;
  text-align: right;
  font-variant-numeric: tabular-nums;
  font-size: 12px;
  font-weight: 800;
  color: var(--ds-ink-2);
}

/* 学生缺交情况：横向清单，语义优先 */
.missing-explain {
  margin: 0 0 14px;
  padding: 10px 12px;
  border-radius: 10px;
  background: #f6f7f9;
  color: var(--ds-ink-2);
  font-size: 12px;
  line-height: 1.55;
}
.missing-explain strong {
  color: var(--ds-ink);
  font-weight: 800;
}
.missing-rows {
  display: grid;
  gap: 8px;
}
.missing-row {
  display: grid;
  grid-template-columns: minmax(110px, 1.1fr) minmax(0, 1.4fr) auto auto;
  gap: 10px;
  align-items: center;
  padding: 10px 12px;
  border-radius: 12px;
  background: #fafafa;
  opacity: 0;
  animation: fade-up 0.4s cubic-bezier(0.22, 1, 0.36, 1) forwards;
  animation-delay: var(--delay, 0ms);
  transition: background 0.15s ease;
}
.missing-row:hover {
  background: #f3f4f6;
}
.missing-row__label strong {
  display: block;
  font-size: 13px;
  color: var(--ds-ink);
}
.missing-row__label small {
  display: block;
  margin-top: 2px;
  color: var(--ds-faint);
  font-size: 11px;
  line-height: 1.35;
}
.missing-row__bar {
  height: 8px;
  border-radius: 99px;
  background: #e8eaed;
  overflow: hidden;
}
.missing-row__bar i {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: #9aa1ad;
  transition: width 0.85s cubic-bezier(0.22, 1, 0.36, 1);
}
.missing-row[data-level='ok'] .missing-row__bar i {
  background: linear-gradient(90deg, #5dcea0, #0f9f6e);
}
.missing-row[data-level='low'] .missing-row__bar i {
  background: linear-gradient(90deg, #f0c14d, #d98200);
}
.missing-row[data-level='mid'] .missing-row__bar i {
  background: linear-gradient(90deg, #ff9a6b, #e84a1c);
}
.missing-row[data-level='high'] .missing-row__bar i {
  background: linear-gradient(90deg, #ff8a8a, #d64545);
}
.missing-row__count {
  display: flex;
  align-items: baseline;
  gap: 2px;
  min-width: 36px;
  justify-content: flex-end;
}
.missing-row__count em {
  font-style: normal;
  font-size: 18px;
  font-family: var(--ds-font-num);
  font-weight: 800;
  color: var(--ds-ink);
  line-height: 1;
}
.missing-row__count span {
  color: var(--ds-muted);
  font-size: 11px;
  font-weight: 700;
}
.missing-row__tag {
  min-height: 24px;
  padding: 0 8px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  font-size: 11px;
  font-weight: 800;
  background: #eef0f2;
  color: #5f656d;
  white-space: nowrap;
}
.missing-row[data-level='ok'] .missing-row__tag {
  background: #e5f6ef;
  color: #0b7753;
}
.missing-row[data-level='low'] .missing-row__tag {
  background: #fff4e5;
  color: #b77400;
}
.missing-row[data-level='mid'] .missing-row__tag {
  background: var(--ds-orange-wash);
  color: var(--ds-orange-deep);
}
.missing-row[data-level='high'] .missing-row__tag {
  background: #ffe8e8;
  color: #b42318;
}
.missing-summary {
  margin: 12px 0 0;
  padding-top: 12px;
  border-top: 1px dashed rgba(29, 29, 31, 0.08);
  color: var(--ds-muted);
  font-size: 12px;
  line-height: 1.55;
}
.missing-summary b {
  color: var(--ds-ink);
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}

/* 关注名单 */
.focus-list {
  display: grid;
  gap: 8px;
}
.focus-item {
  display: grid;
  grid-template-columns: 34px minmax(0, 1fr) auto;
  gap: 10px;
  align-items: center;
  padding: 10px;
  border-radius: 12px;
  background: #fafafa;
  opacity: 0;
  animation: fade-up 0.4s cubic-bezier(0.22, 1, 0.36, 1) forwards;
  animation-delay: var(--delay, 0ms);
  transition: background 0.15s ease, transform 0.15s ease;
}
.focus-item:hover {
  background: #fff5f1;
  transform: translateX(2px);
}
.focus-item strong {
  display: block;
  font-size: 13px;
}
.focus-item small {
  display: block;
  margin-top: 2px;
  color: var(--ds-muted);
  font-size: 11px;
}
.focus-tag {
  min-height: 26px;
  padding: 0 10px;
  border-radius: 999px;
  background: var(--ds-orange-wash);
  color: var(--ds-orange-deep);
  font-size: 11px;
  font-weight: 800;
  display: inline-flex;
  align-items: center;
}
.focus-ok {
  padding: 28px 12px;
  text-align: center;
  color: var(--ds-muted);
}
.focus-ok span {
  display: grid;
  width: 40px;
  height: 40px;
  margin: 0 auto 10px;
  place-items: center;
  border-radius: 50%;
  background: #e5f6ef;
  color: #0b7753;
  font-weight: 800;
}
.focus-ok p {
  margin: 0;
  font-size: 13px;
}

/* 热力表 */
.matrix-card .teacher-card__head {
  align-items: flex-start;
}
.matrix-scroll {
  overflow: auto;
  padding-top: 8px;
}
.heat-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  font-size: 11px;
  font-weight: 700;
  color: var(--ds-muted);
}
.heat-legend span {
  display: inline-flex;
  align-items: center;
  gap: 5px;
}
.heat-legend i {
  width: 10px;
  height: 10px;
  border-radius: 3px;
  display: inline-block;
}
.heat-legend i.is-ok { background: #0f9f6e; }
.heat-legend i.is-pending { background: #e84a1c; }
.heat-legend i.is-revise { background: #d98200; }
.heat-legend i.is-miss { background: #d7dbe2; }

.heat-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 12px;
}
.heat-table th {
  position: sticky;
  top: 0;
  z-index: 1;
  padding: 8px 10px;
  text-align: left;
  color: var(--ds-muted);
  font-weight: 700;
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(6px);
  border-bottom: 1px solid rgba(29, 29, 31, 0.06);
}
.heat-table td {
  padding: 10px;
  border-bottom: 1px solid rgba(29, 29, 31, 0.04);
  vertical-align: middle;
}
.heat-table tbody tr {
  opacity: 0;
  animation: fade-up 0.35s ease forwards;
  animation-delay: var(--delay, 0ms);
  transition: background 0.15s ease;
}
.heat-table tbody tr:hover {
  background: rgba(232, 74, 28, 0.03);
}
.sticky-col {
  position: sticky;
  left: 0;
  z-index: 2;
  background: #fff;
  min-width: 120px;
}
.member-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 700;
  color: var(--ds-ink);
}
.pos-cell {
  color: var(--ds-muted);
  white-space: nowrap;
}
.day-col {
  text-align: center !important;
  min-width: 42px;
}
.heat-cell {
  text-align: center;
}
.heat-dot {
  width: 22px;
  height: 22px;
  margin: 0 auto;
  border: 0;
  border-radius: 7px;
  background: #e8eaed;
  cursor: default;
  transition: transform 0.15s ease, box-shadow 0.15s ease, filter 0.15s ease;
}
.heat-dot:hover {
  transform: scale(1.18);
  box-shadow: 0 4px 12px rgba(18, 20, 26, 0.12);
}
.heat-dot.is-ok {
  background: linear-gradient(145deg, #2ecf8a, #0f9f6e);
}
.heat-dot.is-pending {
  background: linear-gradient(145deg, #ff7a45, #e84a1c);
}
.heat-dot.is-revise {
  background: linear-gradient(145deg, #f0b429, #d98200);
}
.heat-dot.is-miss {
  background: #e4e7ec;
}
.prog-cell {
  display: grid;
  grid-template-columns: 72px auto;
  gap: 8px;
  align-items: center;
  min-width: 120px;
}
.mini-bar {
  display: block;
  height: 6px;
  border-radius: 99px;
  background: #eceef0;
  overflow: hidden;
}
.mini-bar b {
  display: block;
  height: 100%;
  border-radius: inherit;
  background: var(--ds-orange);
  transition: width 0.85s cubic-bezier(0.22, 1, 0.36, 1);
}
.prog-cell em {
  font-style: normal;
  font-variant-numeric: tabular-nums;
  font-size: 12px;
  font-weight: 700;
  color: var(--ds-ink-2);
}

.soft-empty {
  padding: 28px !important;
  color: var(--ds-muted);
}

.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  border: 0;
}

@keyframes fade-up {
  from {
    opacity: 0;
    transform: translateY(12px);
  }
  to {
    opacity: 1;
    transform: none;
  }
}
@keyframes fade-in {
  from { opacity: 0; }
  to { opacity: 1; }
}
@keyframes donut-in {
  from {
    opacity: 0;
    stroke-dasharray: 0 289;
  }
  to {
    opacity: 1;
  }
}
@keyframes shimmer {
  0% { background-position: 100% 0; }
  100% { background-position: -100% 0; }
}

@media (max-width: 1180px) {
  .kpi-strip {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
  .progress-charts,
  .progress-mid,
  .sk-charts {
    grid-template-columns: 1fr;
  }
  .sk-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
@media (max-width: 720px) {
  .kpi-strip {
    grid-template-columns: 1fr 1fr;
  }
  .donut-panel {
    grid-template-columns: 1fr;
    justify-items: center;
  }
  .rate-row {
    grid-template-columns: 34px minmax(0, 1fr) 40px;
  }
  .rate-bar {
    display: none;
  }
  .missing-row {
    grid-template-columns: minmax(0, 1fr) auto auto;
  }
  .missing-row__bar {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .kpi-card,
  .rate-row,
  .missing-row,
  .focus-item,
  .heat-table tbody tr,
  .chart-line,
  .chart-area,
  .donut-seg,
  .plan-notice {
    animation: none !important;
    opacity: 1 !important;
    transform: none !important;
  }
  .rate-bar b,
  .missing-row__bar i,
  .mini-bar b,
  .kpi-spark b {
    transition: none !important;
  }
}
</style>
