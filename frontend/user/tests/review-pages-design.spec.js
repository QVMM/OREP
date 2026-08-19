import { expect, test } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('orep_user_token', 'review-pages-design-token')
    localStorage.setItem('orep_user', JSON.stringify({ username: '李林峰', role: 'STUDENT' }))
  })

  for (const path of [
    '/api/collaboration/summary',
    '/api/monitor/heartbeat',
    '/api/monitor/track',
    '/api/notifications'
  ]) {
    await page.route(`**${path}`, route => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: 200, data: [] })
    }))
  }

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
              title: '商贸赛道',
              completedAt: '2026-06-26T14:16:45',
              status: 'completed',
              sourceType: 'uploaded_video',
              totalScore: 35,
              issueCount: 3,
              highRiskCount: 0
            }]
          : []
      })
    })
  })

  await page.route('**/api/project-teams/my', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      code: 200,
      data: [{ id: 1, name: '应用攻坚队', myRoleInTeam: 'CAPTAIN' }]
    })
  }))

  await page.route('**/api/ai-score/upload-tasks?completedLimit=10', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 200, data: [] })
  }))
})

test('路演训练评分标签使用嵌入式报告表面并保留可读日期', async ({ page }) => {
  await page.setViewportSize({ width: 1288, height: 892 })
  await page.goto('/online-meeting?tab=reports')

  await expect(page.getByRole('heading', { name: '路演训练', level: 1 })).toBeVisible()
  await expect(page.getByRole('heading', { name: '评分报告', level: 1 })).toHaveCount(0)
  await expect(page.getByRole('link', { name: '上传评分', exact: true })).toBeVisible()
  await expect(page.getByText('2026.06.26 14:16', { exact: false })).toBeVisible()
  const sourceMeta = page.getByText('来源：上传视频', { exact: true })
  await expect(sourceMeta).toBeVisible()
  const sourceMetaMetrics = await sourceMeta.evaluate(element => {
    const style = getComputedStyle(element)
    return {
      tagName: element.tagName,
      role: element.getAttribute('role'),
      backgroundColor: style.backgroundColor,
      backgroundImage: style.backgroundImage,
      borderTopWidth: style.borderTopWidth,
      borderRightWidth: style.borderRightWidth,
      borderBottomWidth: style.borderBottomWidth,
      borderLeftWidth: style.borderLeftWidth,
      borderRadius: style.borderRadius,
      boxShadow: style.boxShadow,
      textAlign: style.textAlign
    }
  })
  expect(sourceMetaMetrics.tagName).toBe('SPAN')
  expect(sourceMetaMetrics.role).toBeNull()
  expect(sourceMetaMetrics.backgroundColor).toBe('rgba(0, 0, 0, 0)')
  expect(sourceMetaMetrics.backgroundImage).toBe('none')
  expect(sourceMetaMetrics.borderTopWidth).toBe('0px')
  expect(sourceMetaMetrics.borderRightWidth).toBe('0px')
  expect(sourceMetaMetrics.borderBottomWidth).toBe('0px')
  expect(sourceMetaMetrics.borderLeftWidth).toBe('0px')
  expect(sourceMetaMetrics.borderRadius).toBe('0px')
  expect(sourceMetaMetrics.boxShadow).toBe('none')
  expect(sourceMetaMetrics.textAlign).toBe('left')

  const metrics = await page.locator('.score-summary-page.is-embedded').evaluate(surface => {
    const card = surface.querySelector('.summary-card')
    return {
      borderTopWidth: getComputedStyle(card).borderTopWidth,
      borderRightWidth: getComputedStyle(card).borderRightWidth,
      borderBottomWidth: getComputedStyle(card).borderBottomWidth,
      borderLeftWidth: getComputedStyle(card).borderLeftWidth,
      boxShadow: getComputedStyle(card).boxShadow,
      noOverflow: document.documentElement.scrollWidth <= window.innerWidth
    }
  })
  expect(metrics.borderTopWidth).toBe('0px')
  expect(metrics.borderRightWidth).toBe('0px')
  expect(metrics.borderBottomWidth).toBe('0px')
  expect(metrics.borderLeftWidth).toBe('0px')
  expect(metrics.boxShadow).toBe('none')
  expect(metrics.noOverflow).toBe(true)
})

test('上传评分页采用全宽上传区和任务队列并由工作区唯一提供外边距', async ({ page }) => {
  await page.setViewportSize({ width: 1288, height: 892 })
  await page.goto('/ai-score-upload')

  await expect(page.getByRole('heading', { name: '上传评分', level: 1 })).toBeVisible()
  await expect(page.getByRole('link', { name: '返回评分报告' })).toBeVisible()
  await expect(page.getByRole('button', { name: '返回', exact: true })).toHaveCount(0)
  await expect(page.getByRole('button', { name: '关闭', exact: true })).toHaveCount(0)
  await expect(page.locator('.upload-side,.session-strip,.analysis-panel,.upload-progress-panel')).toHaveCount(0)
  await expect(page.getByRole('heading', { name: '评分任务', level: 2 })).toBeVisible()

  const metrics = await page.locator('.video-score-page').evaluate(root => {
    const main = root.querySelector('.upload-main-card').getBoundingClientRect()
    const queue = root.querySelector('.upload-task-queue').getBoundingClientRect()
    const style = getComputedStyle(root)
    return {
      widthDelta: Math.abs(main.width - queue.width),
      padding: style.padding,
      margin: style.margin,
      backgroundColor: style.backgroundColor,
      backgroundImage: style.backgroundImage,
      noOverflow: document.documentElement.scrollWidth <= window.innerWidth
    }
  })
  expect(metrics.widthDelta).toBeLessThanOrEqual(1)
  expect(metrics.padding).toBe('0px')
  expect(metrics.margin).toBe('0px')
  expect(metrics.backgroundColor).toBe('rgba(0, 0, 0, 0)')
  expect(metrics.backgroundImage).toBe('none')
  expect(metrics.noOverflow).toBe(true)
})

test('评分标签与上传页在窄屏下保持可达且不横向溢出', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })

  await page.goto('/online-meeting?tab=reports')
  await expect(page.getByRole('heading', { name: '报告记录', level: 2 })).toBeVisible()
  await expect(page.getByText('商贸赛道', { exact: true })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)

  await page.goto('/ai-score-upload')
  await expect(page.getByRole('heading', { name: '上传评分', level: 1 })).toBeVisible()
  const teamSelect = page.getByRole('combobox', { name: '项目团队' })
  await expect(teamSelect).toBeVisible()
  await expect(teamSelect).toHaveValue('1')
  await expect(teamSelect).toContainText('应用攻坚队')
  const uploadMetrics = await page.locator('.video-score-page').evaluate(root => {
    const main = root.querySelector('.upload-main-card').getBoundingClientRect()
    const queue = root.querySelector('.upload-task-queue').getBoundingClientRect()
    return {
      mainBottom: main.bottom,
      queueTop: queue.top,
      noOverflow: document.documentElement.scrollWidth <= window.innerWidth
    }
  })
  expect(uploadMetrics.queueTop).toBeGreaterThanOrEqual(uploadMetrics.mainBottom)
  expect(uploadMetrics.noOverflow).toBe(true)
})
