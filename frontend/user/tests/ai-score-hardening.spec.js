import { test, expect } from '@playwright/test'

const sessionId = process.env.OREP_E2E_SESSION_ID || '26'
const username = process.env.OREP_E2E_USERNAME || 'admin'
const password = process.env.OREP_E2E_PASSWORD || 'admin123'
const captureScreenshots = process.env.OREP_E2E_CAPTURE === '1'

async function captureVerificationScreenshot(page, name) {
  if (!captureScreenshots) return
  await page.screenshot({
    path: `../../docs/verification/screenshots/session-${sessionId}-${name}.png`,
    fullPage: true
  })
}

const forbidden = [
  'rubric_hash',
  'rubricPath',
  'rubric_path',
  'internal_version',
  'internalVersion',
  'prompt',
  'weight',
  'rule_formula',
  'score_threshold',
  'ruleEngineVersion'
]

function containsForbiddenField(value) {
  if (!value || typeof value !== 'object') return false
  if (Array.isArray(value)) return value.some(containsForbiddenField)
  return Object.entries(value).some(([key, child]) => {
    const normalized = key.replace(/[-_\s]/g, '').toLowerCase()
    if (forbidden.some(item => normalized === item.replace(/[-_\s]/g, '').toLowerCase())) return true
    return containsForbiddenField(child)
  })
}

test.beforeEach(async ({ page, request }) => {
  const response = await request.post('/api/auth/login', {
    data: { username, password }
  })
  expect(response.ok()).toBe(true)
  const payload = await response.json()
  expect(payload?.code).toBe(200)
  expect(payload?.data?.token).toBeTruthy()

  await page.addInitScript(({ token, user }) => {
    localStorage.setItem('orep_user_token', token)
    localStorage.setItem('orep_user', JSON.stringify(user))
    localStorage.setItem('user', JSON.stringify(user))
  }, {
    token: payload.data.token,
    user: payload.data.user
  })
})

test('AI score report page hides internal rule fields and keeps jury as review layer', async ({ page }) => {
  const apiPayloads = []
  page.on('response', async response => {
    const url = response.url()
    if (!url.includes('/api/ai-score') && !url.includes('/api/ai-jury')) return
    const contentType = response.headers()['content-type'] || ''
    if (!contentType.includes('application/json')) return
    try {
      apiPayloads.push(await response.json())
    } catch {
      // Ignore non-json bodies even if the content type is incorrect.
    }
  })

  await page.goto(`/ai-score/report/${sessionId}/result`)
  await expect(page.getByRole('heading', { name: /评分总结/ })).toBeVisible()

  const bodyText = await page.locator('body').innerText()
  expect(bodyText).not.toContain('rubric_hash')
  expect(bodyText).not.toContain('internal_version')
  expect(bodyText).not.toContain('规则 hash')
  expect(bodyText).not.toContain('prompt')

  for (const payload of apiPayloads) {
    expect(containsForbiddenField(payload)).toBe(false)
  }
})

test('session 26 explains the entire 50.5 point gap across all three report pages', async ({ page }) => {
  const reportResponsePromise = page.waitForResponse(response => (
    response.request().method() === 'GET' &&
    response.url().includes(`/api/ai-score/reports/by-session/${sessionId}`)
  ))

  await page.goto(`/ai-score/report/${sessionId}/result`)
  const reportResponse = await reportResponsePromise
  expect(reportResponse.ok()).toBe(true)
  const payload = await reportResponse.json()
  const report = payload?.data || payload
  const expectedTaskCount = Array.isArray(report?.remediationTasks) ? report.remediationTasks.length : 0
  expect(expectedTaskCount).toBeGreaterThan(0)

  await expect(page.getByRole('heading', { name: /评分总结 49\.5/ })).toBeVisible()
  await expect(page.getByText('距离满分', { exact: true })).toBeVisible()
  await expect(page.getByText('50.5', { exact: true })).toBeVisible()
  await expect(page.getByText(/本报告识别 19 条失分账目.*覆盖当前全部 50\.5 分差距/)).toBeVisible()
  await expect(page.locator('[data-testid="priority-task"]')).toHaveCount(Math.min(3, expectedTaskCount))
  await captureVerificationScreenshot(page, 'result')

  await page.getByRole('link', { name: /查看全部 .* 项整改/ }).click()
  // Linear-style master-detail: compact list + one detail pane.
  await expect(page.getByRole('tab', { name: /待处理/ })).toBeVisible()
  await expect(page.locator('[data-testid="todo-detail"]')).toBeVisible()
  await expect(page.locator('[data-testid="todo-row"]').first()).toBeVisible()
  await expect(page.getByText('完整问题一次公开，按优先级逐项兑现。', { exact: true })).toHaveCount(0)

  // Full inventory lives under「全部」view.
  await page.getByRole('tab', { name: /全部/ }).click()
  await expect(page.locator('[data-testid="todo-row"]')).toHaveCount(expectedTaskCount)
  await expect(page.locator('[data-testid="todo-coverage-strip"]')).toContainText('50.5 分差距')
  await expect(page.getByText('涉及观测点', { exact: true })).toHaveCount(0)
  await expect(page.getByText('失分账目', { exact: true })).toHaveCount(0)
  await expect(page.getByText('整改任务', { exact: true })).toHaveCount(0)
  await expect(page.getByText('当前差距覆盖率', { exact: true })).toHaveCount(0)

  const todosLayout = await page.evaluate(() => {
    const workspace = document.querySelector('[data-testid="todos-workspace"]')
    const layout = document.querySelector('[data-testid="todos-layout"]')
    const list = document.querySelector('[data-testid="todo-list"]')
    const detail = document.querySelector('[data-testid="todo-detail"]')
    const rows = document.querySelectorAll('[data-testid="todo-row"]')
    return {
      hasBoard: Boolean(workspace && layout && list && detail),
      hasRows: rows.length > 0,
      // List and detail should each be able to scroll without nesting body text in every row.
      listIsScrollContainer: list ? getComputedStyle(list).overflowY !== 'visible' : false
    }
  })
  expect(todosLayout.hasBoard).toBe(true)
  expect(todosLayout.hasRows).toBe(true)
  expect(todosLayout.listIsScrollContainer).toBe(true)
  await captureVerificationScreenshot(page, 'todos')

  await page.getByRole('link', { name: '依据', exact: true }).click()
  await expect(page.getByRole('heading', { name: '逐段核验评分依据' })).toBeVisible()
  await expect(page.getByText('完整失分账本', { exact: true })).toBeVisible()
  await expect(page.getByText('19 项 · 合计 −50.5 分', { exact: true })).toBeVisible()
  await expect(page.locator('[data-testid="score-event"]')).toHaveCount(19)
  await expect(page.getByText('1 个已定位评分事件', { exact: true })).toBeVisible()
  await expect.poll(async () => page.locator('[data-testid="roadshow-video"]').evaluate(video => (
    Number.isFinite(video.duration) ? video.duration : 0
  ))).toBeGreaterThan(3200)

  const layout = await page.evaluate(() => {
    const stage = document.querySelector('[data-testid="review-stage"]')
    const timeline = document.querySelector('[data-testid="timeline-card"]')
    const video = document.querySelector('[data-testid="roadshow-video"]')
    const panel = document.querySelector('[data-testid="panel-scroll"]')
    return {
      stageNoVerticalScroll: stage ? stage.scrollHeight <= stage.clientHeight + 1 : false,
      timelineVisible: timeline ? timeline.getBoundingClientRect().bottom <= window.innerHeight + 1 : false,
      videoVisible: video ? video.getBoundingClientRect().height > 180 : false,
      rightPanelScrolls: panel ? panel.scrollHeight > panel.clientHeight : false
    }
  })
  expect(layout.stageNoVerticalScroll).toBe(true)
  expect(layout.timelineVisible).toBe(true)
  expect(layout.videoVisible).toBe(true)
  expect(layout.rightPanelScrolls).toBe(true)

  await expect(page.locator('[data-testid="timeline-event"]')).toHaveCount(1)
  await page.locator('[data-testid="timeline-event"]').click()
  await expect.poll(async () => page.locator('[data-testid="roadshow-video"]').evaluate(video => video.currentTime))
    .toBeGreaterThan(2390)
  await captureVerificationScreenshot(page, 'why')
})

test('upload video score page does not expose scoring rule version selector', async ({ page }) => {
  await page.goto('/ai-score-upload')
  await expect(page.getByRole('heading', { name: '上传评分', level: 1 })).toBeVisible()
  const bodyText = await page.locator('body').innerText()

  expect(bodyText).toContain('上传')
  expect(bodyText).toContain('最大 5GB')
  expect(bodyText).toContain('单个最大 200MB，合计最大 1GB')
  expect(bodyText).not.toContain('评分规则版本')
  expect(bodyText).not.toContain('rubric')
  expect(bodyText).not.toContain('hash')
})
