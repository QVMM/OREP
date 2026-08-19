import { expect, test } from '@playwright/test'

const contrastRatio = (foreground, background) => {
  const parse = (value) => value.match(/[\d.]+/g).slice(0, 3).map(Number)
  const luminance = (value) => parse(value)
    .map(channel => channel / 255)
    .map(channel => channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4)
    .reduce((total, channel, index) => total + channel * [0.2126, 0.7152, 0.0722][index], 0)
  const values = [luminance(foreground), luminance(background)].sort((a, b) => b - a)
  return (values[0] + 0.05) / (values[1] + 0.05)
}

const homePayload = {
  profile: {
    username: '张志强',
    teamName: '智慧养老项目'
  },
  camp: {
    campId: 1,
    currentDay: 4,
    totalDays: 21,
    remainingDays: 17,
    endDate: '2026-08-05',
    teamName: '智慧养老项目'
  },
  todayTraining: {
    hasTrainingDay: true,
    title: '主功能组件封装与排障',
    summary: '今天只练一件事：能讲清模块怎么拆、卡点怎么排。',
    dueAt: '2026-07-21T22:00:00',
    primaryTask: {
      id: 1,
      requirements: [
        { id: 1, required: true, title: '组件结构说明' },
        { id: 2, required: true, title: '排障清单不少于 3 条' }
      ]
    }
  },
  team: {
    memberCount: 5,
    members: [
      { userId: 11, username: '张志强', roleInTeam: 'CAPTAIN', positionName: '项目负责人' },
      { userId: 12, username: '刘一星', roleInTeam: 'MEMBER', positionName: '产品设计' },
      { userId: 13, username: 'user01', roleInTeam: 'MEMBER', positionName: '技术开发' },
      { userId: 14, username: 'user02', roleInTeam: 'MEMBER', positionName: '数据分析' },
      { userId: 15, username: '王同学', roleInTeam: 'MEMBER', positionName: '路演表达' }
    ]
  },
  planSummary: {
    completedDays: 3,
    weeks: [{
      weekNo: 1,
      title: '基础搭建',
      startDate: '2026-07-18',
      endDate: '2026-07-24',
      days: Array.from({ length: 7 }, (_, index) => ({
        dayId: index + 1,
        dayNo: index + 1,
        trainingDate: `2026-07-${String(index + 18).padStart(2, '0')}`,
        progressStatus: index === 3 ? 'TODAY' : index < 3 ? 'SUBMITTED' : 'UPCOMING'
      }))
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
  roadshow: {
    hasRoadshow: true,
    hasScoreReport: true,
    title: '本周路演训练'
  },
  latestScore: {
    hasReport: true,
    reportId: 15,
    overallScore: 64.8,
    improvementPriorities: ['演示时补充真实数据证据。'],
    dimensions: {
      skill: { name: '技能水平', score: 35.5, maxScore: 60 },
      literacy: { name: '职业素养', score: 6.5, maxScore: 10 },
      value: { name: '应用价值', score: 7.25, maxScore: 10 },
      team: { name: '团队合作', score: 7.5, maxScore: 10 },
      innovation: { name: '创新创意', score: 8, maxScore: 10 }
    }
  },
  nextActions: [{
    type: 'training',
    taskId: 1,
    path: '/training/today',
    priority: 'primary',
    title: '完成今日训练',
    meta: '今天 22:00 截止'
  }]
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('orep_user_token', 'prototype-contract-token')
  })
  await page.route('**/api/student/home', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 200, data: homePayload })
  }))
})

test('桌面首页主任务优先，次要三卡承载可视化', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.goto('/')

  await expect(page.getByRole('heading', { name: '张志强，今天是你备赛的第 4 天' })).toBeVisible()
  await expect(page.getByText('继续保持节奏，你今天完成的每一步，都在为赛场上的从容积累底气。')).toBeVisible()
  await expect(page.locator('[data-testid="home-hero"] .home-avatar')).toHaveCount(0)
  await expect(page.locator('.workspace-search__kbd')).toHaveCount(0)

  const cards = {
    progress: page.getByTestId('home-progress-card'),
    today: page.getByTestId('home-today-card'),
    roadshow: page.getByTestId('home-roadshow-card'),
    score: page.getByTestId('home-score-card')
  }

  for (const card of Object.values(cards)) await expect(card).toBeVisible()
  await expect(page.getByTestId('home-rhythm-card')).toHaveCount(0)
  await expect(page.getByTestId('home-actions-card')).toHaveCount(0)
  await expect(page.getByRole('heading', { name: '训练日历' })).toHaveCount(0)
  await expect(page.getByRole('heading', { name: '现在可做' })).toHaveCount(0)
  await expect(page.getByRole('link', { name: /完整计划/ })).toHaveCount(0)

  // 主任务唯一高权重：现在最该做
  await expect(cards.today.getByText('现在最该做')).toBeVisible()
  await expect(cards.today.getByText('今日主任务')).toBeVisible()
  await expect(cards.today.getByRole('link', { name: '去完成任务' })).toBeVisible()
  await expect(cards.today.getByRole('link', { name: '查看全部任务' })).toBeVisible()

  // 状态条无主 CTA（避免与主任务双入口抢注意力）
  await expect(page.locator('[data-testid="home-hero"] .interactive-hover-button')).toHaveCount(0)
  await expect(page.getByTestId('home-countdown-panel')).toContainText('17')

  // 可视化：学习柱状图 + AI 雷达图
  await expect(page.getByTestId('weekly-learning-duration').locator('canvas')).toHaveCount(1)
  await expect(cards.score.locator('.home-score-radar canvas')).toHaveCount(1)
  await expect(cards.score.getByText('64.8')).toBeVisible()
  await expect(cards.score.getByText('演示时补充真实数据证据。')).toBeVisible()

  const layout = await page.evaluate(() => {
    const rect = testId => document.querySelector(`[data-testid="${testId}"]`).getBoundingClientRect()
    const secondary = document.querySelector('[data-testid="home-grid"]')
    return {
      secondaryColumns: getComputedStyle(secondary).gridTemplateColumns.split(' ').filter(Boolean).length,
      progress: rect('home-progress-card').toJSON(),
      today: rect('home-today-card').toJSON(),
      roadshow: rect('home-roadshow-card').toJSON(),
      score: rect('home-score-card').toJSON(),
      hero: document.querySelector('[data-testid="home-hero"]').getBoundingClientRect().toJSON(),
      countdown: document.querySelector('[data-testid="home-countdown-panel"]').getBoundingClientRect().toJSON()
    }
  })

  // 状态条：欢迎左、倒计时右
  expect(layout.hero.x).toBeLessThan(layout.countdown.x)
  expect(layout.countdown.right).toBeCloseTo(layout.hero.right, 0)

  // 主任务在次要三卡之上
  expect(layout.today.bottom).toBeLessThanOrEqual(layout.progress.top + 4)
  expect(layout.today.bottom).toBeLessThanOrEqual(layout.roadshow.top + 4)

  // 次要三卡同一行
  expect(layout.secondaryColumns).toBe(3)
  expect(layout.progress.y).toBeCloseTo(layout.roadshow.y, 0)
  expect(layout.roadshow.y).toBeCloseTo(layout.score.y, 0)
  expect(layout.progress.x).toBeLessThan(layout.roadshow.x)
  expect(layout.roadshow.x).toBeLessThan(layout.score.x)

  // 主 CTA 在今天练什么卡片内
  const primary = page.getByTestId('home-today-card').getByRole('link', { name: '去完成任务' })
  await expect(primary).toBeVisible()
  const defaultColors = await primary.evaluate(el => {
    const style = getComputedStyle(el)
    return { foreground: style.color, background: style.backgroundColor }
  })
  expect(contrastRatio(defaultColors.foreground, defaultColors.background)).toBeGreaterThanOrEqual(4.5)

  const primaryBox = await primary.boundingBox()
  await primary.hover()
  await expect(primary).toHaveCSS('color', 'rgb(255, 255, 255)')
  expect(await primary.boundingBox()).toEqual(primaryBox)
  await expect(primary.locator('.interactive-hover-button__default')).toHaveCSS('opacity', '0')
  await expect(primary.locator('.interactive-hover-button__reveal')).toHaveCSS('opacity', '1')
  await expect(primary.locator('.interactive-hover-button__fill')).toHaveCSS('transform', /matrix/)
  const hoverColors = await primary.evaluate(el => {
    const style = getComputedStyle(el)
    return { foreground: style.color, background: style.backgroundColor }
  })
  expect(contrastRatio(hoverColors.foreground, hoverColors.background)).toBeGreaterThanOrEqual(4.5)

  await page.screenshot({
    path: '../../docs/audits/student-prototype-contract-home-2026-07-21.png',
    fullPage: true
  })
  await page.locator('[data-testid="home-today-card"]').screenshot({
    path: '../../docs/audits/student-home-primary-hover-2026-07-21.png'
  })

  // 评分入口降级为文字链，不再用次级按钮抢主任务权重
  const scoreLink = page.getByRole('link', { name: /查看完整报告与建议/ })
  await expect(scoreLink).toBeVisible()
  await scoreLink.hover()
})

test('首页在中等和窄屏下按规范降列且核心操作保持可见', async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 900 })
  await page.goto('/')

  // 中等屏：次要区单列（≤1100px 断点）
  await expect(page.getByTestId('home-grid')).toHaveCSS('grid-template-columns', /.+/)
  await expect(page.getByRole('link', { name: '去完成任务' })).toBeVisible()

  await page.setViewportSize({ width: 820, height: 900 })
  const columns = await page.getByTestId('home-grid').evaluate(
    el => getComputedStyle(el).gridTemplateColumns.split(' ').filter(Boolean).length
  )
  expect(columns).toBe(1)
  await expect(page.getByRole('heading', { name: '张志强，今天是你备赛的第 4 天' })).toBeVisible()
  await expect(page.getByRole('link', { name: '去完成任务' })).toBeVisible()
  await expect.poll(() => page.evaluate(() => document.body.scrollWidth <= document.body.clientWidth)).toBe(true)
})

test('首页小队成员以跟随指针的动画头像提示呈现', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 1000 })
  await page.goto('/')

  const teamTooltip = page.getByTestId('team-animated-tooltip')
  const firstMember = page.getByTestId('team-member-avatar').first()

  await expect(teamTooltip).toBeVisible()
  await expect(page.getByTestId('team-member-avatar')).toHaveCount(5)
  await expect(teamTooltip).toContainText('5人')

  const memberBox = await firstMember.boundingBox()
  await page.mouse.move(memberBox.x + 3, memberBox.y + memberBox.height / 2)
  const popup = page.getByTestId('team-member-tooltip')
  await expect(popup).toBeVisible()
  await expect(popup).toContainText('张志强')
  await expect(popup).toContainText('项目负责人')
})
