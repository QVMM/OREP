import { expect, test } from '@playwright/test'

const homePayload = {
  profile: { username: '张志强', teamName: '智慧养老项目' },
  camp: {
    campId: 1,
    currentDay: 4,
    totalDays: 21,
    remainingDays: 17,
    endDate: '2026-08-05'
  },
  todayTraining: {
    hasTrainingDay: true,
    dayId: 4,
    title: '主功能组件封装与排障',
    dueAt: '2026-07-21T22:00:00',
    primaryTask: { id: 1, title: '提交组件结构说明' }
  },
  planSummary: {
    completedDays: 3,
    weeks: [{
      weekNo: 1,
      title: '第 1 周',
      startDate: '2026-07-20',
      endDate: '2026-07-26',
      days: [{
        dayId: 4,
        dayNo: 4,
        trainingDate: '2026-07-22',
        title: '提交组件结构说明',
        progressStatus: 'TODAY'
      }]
    }]
  },
  weeklyLearning: {
    weekStart: '2026-07-20',
    weekEnd: '2026-07-26',
    serverDate: '2026-07-22',
    totalSeconds: 8100,
    activeDays: 3,
    daily: [1800, 3600, 2700, 0, 0, 0, 0].map((durationSeconds, index) => ({
      date: `2026-07-${String(index + 20).padStart(2, '0')}`,
      durationSeconds
    }))
  },
  roadshow: { hasRoadshow: true, hasScoreReport: true, title: '本周路演训练' },
  latestScore: {
    hasReport: true,
    reportId: 15,
    overallScore: 64.8,
    dimensions: {},
    improvementPriorities: ['补充真实数据证据。']
  },
  nextActions: [{
    type: 'TRAINING',
    taskId: 1,
    path: '/training/today',
    priority: 'PRIMARY',
    title: '完成今日训练',
    meta: '今天 22:00 截止'
  }]
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('orep_user_token', 'home-trend-token'))
  await page.route('**/api/student/home', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 200, data: homePayload })
  }))
})

test('首页用真实记录展示七日学习时长并收敛重复入口', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.goto('/')

  const trendCard = page.getByTestId('home-progress-card')
  const chart = page.getByTestId('weekly-learning-duration')
  const todayCard = page.getByTestId('home-today-card')

  // 主任务卡优先
  await expect(todayCard.getByText('现在最该做')).toBeVisible()
  await expect(todayCard.getByRole('heading', { name: '今天练什么' })).toBeVisible()
  await expect(todayCard.getByRole('link', { name: '去完成任务' })).toBeVisible()

  // 学习时长：汇总文案 + ECharts 可视化容器
  await expect(trendCard.getByRole('heading', { name: '本周学习时长' })).toBeVisible()
  await expect(trendCard.getByText('2.3')).toBeVisible()
  await expect(trendCard.getByText('小时')).toBeVisible()
  await expect(trendCard.getByText('45 分/天')).toBeVisible()
  await expect(chart).toHaveAttribute('role', 'img')
  await expect(chart).toHaveAttribute('aria-label', /本周学习时长/)
  await expect(chart.locator('canvas')).toHaveCount(1)

  await expect(page.getByRole('heading', { name: '张志强，今天是你备赛的第 4 天' })).toBeVisible()
  await expect(page.getByText('继续保持节奏，你今天完成的每一步，都在为赛场上的从容积累底气。')).toBeVisible()

  await expect(page.getByTestId('home-rhythm-card')).toHaveCount(0)
  await expect(page.getByTestId('home-actions-card')).toHaveCount(0)
  await expect(page.getByText('训练日历', { exact: true })).toHaveCount(0)
  await expect(page.getByText('现在可做', { exact: true })).toHaveCount(0)

  // 入口收敛：主任务 1 CTA + 文字链；路演 1；评分 1
  await expect(page.locator('.student-home a[href="/online-meeting"]')).toHaveCount(1)
  await expect(page.locator('.student-home a[href="/training/plan"]')).toHaveCount(0)
  // 路演次要链 + 评分卡文字链
  await expect(page.locator('.student-home a[href="/ai-score/report-id/15/result"]')).toHaveCount(2)
  // 主 CTA + 「查看全部任务」
  await expect(page.locator('.student-home a[href="/training/today"]')).toHaveCount(2)
  await expect(page.locator('.student-home a[href="/training/days/4"]')).toHaveCount(0)

  // 首屏主任务在次要卡上方
  const layout = await page.evaluate(() => {
    const today = document.querySelector('[data-testid="home-today-card"]').getBoundingClientRect()
    const progress = document.querySelector('[data-testid="home-progress-card"]').getBoundingClientRect()
    return { todayBottom: today.bottom, progressTop: progress.top }
  })
  expect(layout.todayBottom).toBeLessThanOrEqual(layout.progressTop + 2)

  await page.screenshot({
    path: '../../docs/audits/student-home-weekly-learning-duration-2026-07-22.png',
    fullPage: true
  })
})
