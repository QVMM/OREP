import { expect, test } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('orep_user_token', 'online-meeting-report-tabs-token'))

  await page.route('**/api/**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 200, data: {} })
  }))

  await page.route('**/api/meeting/my-history', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 200, data: [] })
  }))

  await page.route('**/api/ai-score/reports/summary?*', route => {
    const scope = new URL(route.request().url()).searchParams.get('scope')
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 200,
        data: scope === 'participant'
          ? [{
              sessionId: 26,
              title: '乡村振兴项目路演',
              completedAt: '2026-06-26T14:16:45',
              status: 'completed',
              sourceType: 'meeting_recording',
              totalScore: 88,
              issueCount: 3,
              highRiskCount: 1
            }]
          : []
      })
    })
  })
})

test('默认优先展示评分报告且路演记录仍可切换', async ({ page }) => {
  let reportRequests = 0
  const reportRequestScopes = []
  page.on('request', request => {
    if (request.url().includes('/api/ai-score/reports/summary?')) {
      reportRequests += 1
      reportRequestScopes.push(new URL(request.url()).searchParams.get('scope'))
    }
  })

  await page.goto('/online-meeting')

  const mainTabs = page.getByRole('tablist', { name: '路演训练内容' })
  await expect(mainTabs).toBeVisible()
  await expect(page.getByRole('heading', { name: '路演训练', level: 1 })).toBeVisible()
  await expect(page).toHaveTitle('路演训练｜竞赛大脑')
  await expect(mainTabs.getByRole('tab').nth(0)).toHaveText('评分报告')
  await expect(mainTabs.getByRole('tab').nth(1)).toHaveText('路演记录')
  await expect(mainTabs.getByRole('tab', { name: '评分报告', exact: true })).toHaveAttribute('aria-selected', 'true')
  await expect(mainTabs.getByRole('tab', { name: '路演记录', exact: true })).toHaveAttribute('aria-selected', 'false')
  await expect(page.getByRole('heading', { name: '报告记录', level: 2 })).toHaveCount(0)
  await expect(page.getByText(/共 \d+ 份已完成报告/)).toHaveCount(0)
  await expect(page.getByRole('region', { name: '评分报告列表' })).toBeVisible()
  await expect(page.locator('#reports-panel')).toHaveAttribute('role', 'tabpanel')
  await expect(page.locator('#reports-panel')).toHaveAttribute('aria-labelledby', 'reports-tab')
  const rangeTabsBox = await page.getByRole('tablist', { name: '评分报告范围' }).boundingBox()
  const uploadBox = await page.locator('.report-toolbar').getByRole('link', {
    name: '上传评分',
    exact: true
  }).boundingBox()
  expect(rangeTabsBox).not.toBeNull()
  expect(uploadBox).not.toBeNull()
  expect(rangeTabsBox.x).toBeLessThan(uploadBox.x)
  await expect.poll(() => reportRequests).toBe(2)
  expect(reportRequestScopes.sort()).toEqual(['participant', 'team'])
  await expect(page.getByRole('button', { name: '发起路演', exact: true })).toHaveCount(1)
  await expect(page.getByRole('button', { name: '进入路演', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: '没有会议？创建本场', exact: true })).toHaveCount(0)
  await expect(page.getByRole('button', { name: '上传视频评分', exact: true })).toHaveCount(0)
  await expect(page.locator('.join-foot')).toContainText('记住路演号与密码')

  await mainTabs.getByRole('tab', { name: '路演记录', exact: true }).click()

  await expect(page).toHaveURL('/online-meeting?tab=meetings')
  const meetingsPanel = page.locator('#meetings-panel')
  const historyFilters = page.getByRole('tablist', { name: '筛选参与记录' })
  await expect(historyFilters).toBeVisible()
  await expect(page.getByRole('heading', { name: '路演记录', level: 2 })).toHaveCount(0)
  await expect(page.getByText('继续进行中的路演，或查看已结束场次', { exact: true })).toHaveCount(0)
  await expect(meetingsPanel.locator('.list-head')).toHaveClass(/\bis-filter-only\b/)
  await expect(meetingsPanel).toHaveAttribute('role', 'tabpanel')
  await expect(meetingsPanel).toHaveAttribute('aria-labelledby', 'meetings-tab')

  const panelBox = await meetingsPanel.boundingBox()
  const filtersBox = await historyFilters.boundingBox()
  expect(panelBox).not.toBeNull()
  expect(filtersBox).not.toBeNull()
  expect(filtersBox.x - panelBox.x).toBeGreaterThanOrEqual(20)
  expect(filtersBox.x - panelBox.x).toBeLessThanOrEqual(28)
})

test('评分空状态只保留工具栏上传入口', async ({ page }) => {
  await page.unroute('**/api/ai-score/reports/summary?*')
  await page.route('**/api/ai-score/reports/summary?*', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 200, data: [] })
  }))

  await page.goto('/online-meeting?tab=reports')

  await expect(page.getByText('上传完整路演视频后，评分报告会显示在这里。', {
    exact: true
  })).toBeVisible()
  await expect(page.getByRole('link', { name: '上传评分', exact: true })).toHaveCount(1)
  await expect(page.locator('.empty-state .base-button')).toHaveCount(0)

  await page.getByRole('tab', { name: '我队伍的路演 0', exact: true }).click()
  await expect(page.getByText('团队完成路演评分后，报告会显示在这里。', {
    exact: true
  })).toBeVisible()
  await expect(page.getByRole('link', { name: '上传评分', exact: true })).toHaveCount(1)
  await expect(page.locator('.empty-state .base-button')).toHaveCount(0)
})

test('主标签使用 query 并支持浏览器前进后退', async ({ page }) => {
  const expectMeetingQuery = async tab => {
    await expect(page).toHaveURL(url =>
      url.pathname === '/online-meeting' &&
      url.searchParams.get('tab') === tab &&
      url.searchParams.get('context') === 'shared'
    )
  }

  await page.goto('/online-meeting?tab=meetings&context=shared')

  const mainTabs = page.getByRole('tablist', { name: '路演训练内容' })
  await expect(mainTabs.getByRole('tab', { name: '路演记录', exact: true })).toHaveAttribute('aria-selected', 'true')
  await expectMeetingQuery('meetings')

  await mainTabs.getByRole('tab', { name: '评分报告', exact: true }).click()
  await expectMeetingQuery('reports')

  await mainTabs.getByRole('tab', { name: '路演记录', exact: true }).click()
  await expectMeetingQuery('meetings')

  await page.goBack()
  await expectMeetingQuery('reports')
  await expect(mainTabs.getByRole('tab', { name: '评分报告', exact: true })).toHaveAttribute('aria-selected', 'true')

  await page.goBack()
  await expectMeetingQuery('meetings')
  await expect(mainTabs.getByRole('tab', { name: '路演记录', exact: true })).toHaveAttribute('aria-selected', 'true')

  await page.goForward()
  await expectMeetingQuery('reports')
  await expect(mainTabs.getByRole('tab', { name: '评分报告', exact: true })).toHaveAttribute('aria-selected', 'true')

  await page.goForward()
  await expectMeetingQuery('meetings')
  await expect(mainTabs.getByRole('tab', { name: '路演记录', exact: true })).toHaveAttribute('aria-selected', 'true')
})

test('评分标签复用报告内容且不重复独立页头', async ({ page }) => {
  await page.goto('/online-meeting?tab=reports')

  await expect(page.getByRole('heading', { name: '路演训练', level: 1 })).toBeVisible()
  await expect(page.getByRole('heading', { level: 1 })).toHaveCount(1)
  await expect(page.getByRole('heading', { name: '评分报告', level: 1 })).toHaveCount(0)
  await expect(page.getByRole('heading', { name: '报告记录', level: 2 })).toHaveCount(0)
  await expect(page.getByText(/共 \d+ 份已完成报告/)).toHaveCount(0)
  await expect(page.getByRole('tablist', { name: '评分报告范围' })).toBeVisible()
  await expect(page.getByText('乡村振兴项目路演', { exact: true })).toBeVisible()
  await expect(page.locator('.score-summary-page')).toHaveClass(/\bis-embedded\b/)
})

test('无效标签回退评分报告且窄屏不横向溢出', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/online-meeting?tab=unknown')

  const mainTabs = page.getByRole('tablist', { name: '路演训练内容' })
  await expect(mainTabs.getByRole('tab', { name: '评分报告', exact: true })).toHaveAttribute('aria-selected', 'true')
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390)

  await expect(page.getByRole('link', { name: '上传评分', exact: true })).toBeVisible()
  const reportRow = page.getByRole('button', { name: /乡村振兴项目路演/ })
  await reportRow.scrollIntoViewIfNeeded()
  const reportRowBox = await reportRow.boundingBox()
  const reportCardBox = await page.locator('.list-card').boundingBox()
  const reportContentBox = await page.locator('#reports-panel .summary-card').boundingBox()
  expect(reportRowBox).not.toBeNull()
  expect(reportCardBox).not.toBeNull()
  expect(reportContentBox).not.toBeNull()
  expect(reportRowBox.y).toBeGreaterThanOrEqual(0)
  expect(reportRowBox.y + reportRowBox.height).toBeLessThanOrEqual(844)
  expect(reportContentBox.y).toBeGreaterThanOrEqual(reportCardBox.y)
  expect(reportContentBox.y + reportContentBox.height).toBeLessThanOrEqual(reportCardBox.y + reportCardBox.height)
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390)

  await mainTabs.getByRole('tab', { name: '路演记录', exact: true }).click()
  await expect(page.getByRole('tablist', { name: '筛选参与记录' })).toBeVisible()
  await expect(page.getByRole('heading', { name: '路演记录', level: 2 })).toHaveCount(0)
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390)
})
