import { expect, test } from '@playwright/test'

const taskRoute = '**/api/ai-score/upload-tasks?completedLimit=10'

function ok(data) {
  return {
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 200, data })
  }
}

function scoringTask() {
  return {
    sessionId: 901,
    sessionNo: 'AIS-901',
    status: 'scoring',
    currentStage: 'model_scoring',
    progressPercent: 56
  }
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('orep_user_token', 'ai-score-upload-queue-token')
    localStorage.setItem('orep_user', JSON.stringify({ username: '队列测试用户', role: 'STUDENT' }))
  })

  for (const path of [
    '/api/collaboration/summary',
    '/api/monitor/heartbeat',
    '/api/monitor/track',
    '/api/notifications'
  ]) {
    await page.route(`**${path}`, route => route.fulfill(ok([])))
  }

  await page.route('**/api/project-teams/my', route => route.fulfill(ok([
    { id: 1, name: '应用攻坚队', myRoleInTeam: 'CAPTAIN' },
    { id: 2, name: '商贸先锋队', myRoleInTeam: 'MEMBER' }
  ])))
})

function uploadTasks() {
  return [
    {
      sessionId: 101,
      sessionNo: 'AIS-101',
      fileName: '智能仓储路演.mp4',
      teamId: 1,
      teamName: '应用攻坚队',
      trackName: '物流与供应链赛道',
      status: ' scoring ',
      currentStage: 'model_scoring',
      progressPercent: 46,
      createdAt: '2026-07-29T10:20:00'
    },
    {
      sessionId: 100,
      reportId: 8801,
      sessionNo: 'AIS-100',
      fileName: '养老服务方案.mp4',
      teamId: 1,
      teamName: '应用攻坚队',
      trackName: '健康养老与婴幼儿托育赛道',
      status: ' COMPLETED ',
      currentStage: 'completed',
      progressPercent: 100,
      createdAt: '2026-07-28T08:15:00'
    },
    {
      sessionId: 201,
      sessionNo: 'AIS-201',
      fileName: '商贸展示终稿.mov',
      teamId: 2,
      teamName: '商贸先锋队',
      trackName: '商贸赛道',
      status: ' Failed ',
      currentStage: 'failed',
      progressPercent: 37,
      useHistoryMemory: false,
      juryEnabled: true,
      errorMessage: '视频音轨无法识别，请检查文件后重试',
      createdAt: '2026-07-27T16:40:00'
    }
  ]
}

test('显示持久评分任务的完整状态与基于会话的报告入口', async ({ page }) => {
  await page.route(taskRoute, route => route.fulfill(ok(uploadTasks())))

  await page.goto('/ai-score-upload')

  await expect(page.getByRole('heading', { name: '评分任务', level: 2 })).toBeVisible()
  const activeRow = page.locator('.task-row').filter({ hasText: '智能仓储路演.mp4' })
  await expect(activeRow.getByText('应用攻坚队', { exact: false })).toBeVisible()
  await expect(activeRow.getByText('物流与供应链赛道')).toBeVisible()
  await expect(activeRow.getByText('模型评分中')).toBeVisible()
  await expect(activeRow.getByText('46%', { exact: true })).toBeVisible()
  await expect(activeRow.getByText('系统处理中', { exact: true })).toHaveCount(1)
  const completedRow = page.locator('.task-row').filter({ hasText: '养老服务方案.mp4' })
  await expect(completedRow.getByText('已完成', { exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: '查看报告' })).toHaveAttribute('href', '/ai-score/report/100')
  const failedRow = page.locator('.task-row').filter({ hasText: '商贸展示终稿.mov' })
  await expect(failedRow.getByText('商贸先锋队', { exact: false })).toBeVisible()
  await expect(failedRow.getByText('商贸赛道')).toBeVisible()
  await expect(failedRow.getByText('处理失败', { exact: true })).toBeVisible()
  await expect(failedRow.getByText('视频音轨无法识别，请检查文件后重试')).toBeVisible()
  await expect(page.getByRole('button', { name: '重新上传' })).toBeVisible()
})

test('采用全宽上传区与持久队列并遵守工作区外边距合同', async ({ page }) => {
  await page.route(taskRoute, route => route.fulfill(ok(uploadTasks())))
  await page.setViewportSize({ width: 1288, height: 892 })

  await page.goto('/ai-score-upload')

  await expect(page.getByText('处理流程')).toHaveCount(0)
  await expect(page.getByText('当前状态')).toHaveCount(0)
  await expect(page.getByText('系统会按赛道自动绑定内部评分规则。')).toHaveCount(0)
  await expect(page.locator('.upload-side,.session-strip,.analysis-panel,.upload-progress-panel')).toHaveCount(0)
  await expect(page.getByRole('button', { name: '评分偏好' })).toHaveAttribute('aria-expanded', 'false')
  await expect(page.getByRole('link', { name: '返回评分报告' })).toHaveAttribute('href', '/online-meeting?tab=reports')

  const metrics = await page.locator('.video-score-page').evaluate(root => {
    const upload = root.querySelector('.upload-main-card').getBoundingClientRect()
    const queue = root.querySelector('.upload-task-queue').getBoundingClientRect()
    const style = getComputedStyle(root)
    return {
      widthDelta: Math.abs(upload.width - queue.width),
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
  await expect(page.locator('.upload-main-card .upload-task-queue')).toHaveCount(0)
  await expect(page.locator('.upload-task-queue .upload-main-card')).toHaveCount(0)
  const taskRowSurface = await page.locator('.task-row').first().evaluate(row => ({
    boxShadow: getComputedStyle(row).boxShadow,
    borderRadius: getComputedStyle(row).borderRadius
  }))
  expect(taskRowSurface.boxShadow).toBe('none')
  expect(taskRowSurface.borderRadius).toBe('0px')
})

test('选择本地文件不会伪造上传进度', async ({ page }) => {
  await page.route(taskRoute, route => route.fulfill(ok([uploadTasks()[0]])))
  await page.goto('/ai-score-upload')

  await page.locator('input[type="file"]').first().setInputFiles({
    name: 'pitch.mp4',
    mimeType: 'video/mp4',
    buffer: Buffer.from('video')
  })

  const queueProgress = page.getByRole('progressbar', { name: '智能仓储路演.mp4 分析进度' })
  await expect(page.getByRole('progressbar', { name: '本地文件上传进度' })).toHaveCount(0)
  await expect(page.locator('.upload-main-card [role="progressbar"]')).toHaveCount(0)
  await expect(page.locator('.task-row [role="progressbar"]')).toHaveCount(1)
  await expect(queueProgress).toHaveAttribute('aria-valuenow', '46')
  expect(await queueProgress.evaluate(node => getComputedStyle(node).height)).toBe('4px')
})

test('本地进度只在真实 HTTP 传输期间显示并在请求完成后退出', async ({ page }) => {
  await page.addInitScript(() => {
    const originalSend = XMLHttpRequest.prototype.send
    XMLHttpRequest.prototype.send = function patchedSend(body) {
      if (body instanceof FormData) {
        this.upload.dispatchEvent(new ProgressEvent('progress', {
          lengthComputable: true,
          loaded: 512 * 1024,
          total: 1024 * 1024
        }))
      }
      return originalSend.call(this, body)
    }
  })
  let releaseUpload
  let markUploadStarted
  const uploadStarted = new Promise(resolve => {
    markUploadStarted = resolve
  })
  await page.route(taskRoute, route => route.fulfill(ok([])))
  await page.route('**/api/ai-score/upload-session', async route => {
    markUploadStarted()
    await new Promise(resolve => {
      releaseUpload = resolve
    })
    await route.fulfill(ok({
      sessionId: 305,
      sessionNo: 'AIS-305',
      status: 'queued',
      currentStage: 'queued',
      progressPercent: 0,
      fileName: 'transfer.mp4'
    }))
  })
  await page.goto('/ai-score-upload')

  await page.locator('input[type="file"]').first().setInputFiles({
    name: 'transfer.mp4',
    mimeType: 'video/mp4',
    buffer: Buffer.alloc(1024 * 1024, 1)
  })
  await page.getByRole('button', { name: '开始上传评分' }).click()
  await uploadStarted

  const localProgress = page.getByRole('progressbar', { name: '本地文件上传进度' })
  await expect(localProgress).toBeVisible()
  expect(await localProgress.evaluate(node => getComputedStyle(node).height)).toBe('4px')
  await expect(localProgress).toHaveAttribute('aria-valuenow', '50')

  releaseUpload()
  await expect(page.getByText('上传视频评分会话已创建')).toBeVisible()
  await expect(localProgress).toHaveCount(0)
})

test('排队任务只显示阶段文案而不显示虚假百分比或进度轨', async ({ page }) => {
  await page.route(taskRoute, route => route.fulfill(ok([{
    sessionId: 306,
    sessionNo: 'AIS-306',
    fileName: '等待评分.mp4',
    teamName: '应用攻坚队',
    trackName: '物流与供应链赛道',
    status: 'queued',
    currentStage: 'queued',
    progressPercent: 0,
    createdAt: '2026-07-30T09:00:00'
  }])))
  await page.goto('/ai-score-upload')

  const queuedRow = page.locator('.task-row').filter({ hasText: '等待评分.mp4' })
  await expect(queuedRow.getByText('排队中', { exact: true })).toBeVisible()
  await expect(queuedRow.getByText('0%', { exact: true })).toHaveCount(0)
  await expect(queuedRow.getByRole('progressbar')).toHaveCount(0)
})

test('失败任务重新上传会回填上下文、展开偏好并要求重新选择本地视频', async ({ page }) => {
  await page.route(taskRoute, route => route.fulfill(ok(uploadTasks())))
  await page.goto('/ai-score-upload')

  const videoInput = page.locator('input[type="file"]').first()
  const materialInput = page.locator('input[type="file"]').nth(1)
  await videoInput.setInputFiles({
    name: 'old.mov',
    mimeType: 'video/quicktime',
    buffer: Buffer.from('old video')
  })
  await materialInput.setInputFiles({
    name: '旧版佐证.pdf',
    mimeType: 'application/pdf',
    buffer: Buffer.from('valid evidence')
  })
  await expect(page.getByText('旧版佐证.pdf')).toBeVisible()
  await page.getByRole('button', { name: '重新上传' }).click()

  await expect(page.getByRole('combobox', { name: '项目团队' })).toHaveValue('2')
  await expect(page.getByRole('combobox', { name: '赛道' })).toHaveValue('商贸赛道')
  await expect(page.getByRole('button', { name: '评分偏好' })).toHaveAttribute('aria-expanded', 'true')
  await expect(page.getByRole('checkbox', { name: '引用历史评分记忆' })).not.toBeChecked()
  await expect(page.getByRole('checkbox', { name: '生成 AI 评审团复核' })).toHaveCount(0)
  await expect(page.getByRole('status').filter({ hasText: '请重新选择本地视频文件' })).toBeVisible()
  expect(await videoInput.evaluate(input => input.files.length)).toBe(0)
  expect(await materialInput.evaluate(input => input.files.length)).toBe(0)
  await expect(page.getByText('可选 PDF / PPT / Word')).toBeVisible()
  await videoInput.setInputFiles({
    name: 'replacement.mov',
    mimeType: 'video/quicktime',
    buffer: Buffer.from('replacement video')
  })
  await expect(page.getByText('请重新选择本地视频文件')).toHaveCount(0)
})

test('超限材料会清除已选合法材料且不会进入后续 multipart', async ({ page }) => {
  let multipartBody = ''
  await page.route(taskRoute, route => route.fulfill(ok([])))
  await page.route('**/api/ai-score/upload-session', route => {
    multipartBody = route.request().postDataBuffer()?.toString('utf8') || ''
    return route.fulfill(ok({
      sessionId: 303,
      sessionNo: 'AIS-303',
      status: 'queued',
      currentStage: 'queued',
      fileName: 'safe.mp4'
    }))
  })
  await page.goto('/ai-score-upload')

  const videoInput = page.locator('input[type="file"]').first()
  const materialInput = page.locator('input[type="file"]').nth(1)
  await materialInput.setInputFiles({
    name: '不应残留的合法材料.pdf',
    mimeType: 'application/pdf',
    buffer: Buffer.from('valid evidence')
  })
  await expect(page.getByText('不应残留的合法材料.pdf')).toBeVisible()

  await materialInput.evaluate((input, maxBytes) => {
    const oversized = new File(['x'], '超限材料.pdf', { type: 'application/pdf' })
    Object.defineProperty(oversized, 'size', { configurable: true, value: maxBytes + 1 })
    const transfer = new DataTransfer()
    transfer.items.add(oversized)
    input.files = transfer.files
    input.dispatchEvent(new Event('change', { bubbles: true }))
  }, 200 * 1024 * 1024)

  expect(await materialInput.evaluate(input => input.files.length)).toBe(0)
  await expect(page.getByText('可选 PDF / PPT / Word')).toBeVisible()
  await expect(page.getByRole('alert')).toContainText('单个佐证材料最大200MB')

  await videoInput.setInputFiles({
    name: 'safe.mp4',
    mimeType: 'video/mp4',
    buffer: Buffer.from('video')
  })
  await page.getByRole('button', { name: '开始上传评分' }).click()
  await expect.poll(() => multipartBody).not.toBe('')
  expect(multipartBody).not.toContain('不应残留的合法材料.pdf')
})

test('窄屏下任务行纵向排列且操作可达', async ({ page }) => {
  await page.route(taskRoute, route => route.fulfill(ok(uploadTasks())))
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/ai-score-upload')

  const failedRow = page.locator('.task-row').filter({ hasText: '商贸展示终稿.mov' })
  const mobileMetrics = await failedRow.evaluate(row => {
    const summary = row.querySelector('.task-summary').getBoundingClientRect()
    const actions = row.querySelector('.task-actions').getBoundingClientRect()
    return {
      actionsBelowSummary: actions.top >= summary.bottom,
      actionWithinViewport: actions.left >= 0 && actions.right <= window.innerWidth,
      noOverflow: document.documentElement.scrollWidth <= window.innerWidth
    }
  })
  expect(mobileMetrics.actionsBelowSummary).toBe(true)
  expect(mobileMetrics.actionWithinViewport).toBe(true)
  expect(mobileMetrics.noOverflow).toBe(true)
  await expect(page.getByRole('button', { name: '重新上传' })).toBeVisible()
  await page.getByRole('button', { name: '评分偏好' }).click()
  const touchTargetHeights = await page
    .locator('.base-button, .preference-toggle, .option-row label')
    .evaluateAll(nodes => nodes
      .filter(node => {
        const style = getComputedStyle(node)
        const rect = node.getBoundingClientRect()
        return style.display !== 'none' && style.visibility !== 'hidden' && rect.width > 0 && rect.height > 0
      })
      .map(node => ({
        text: node.textContent.trim(),
        height: node.getBoundingClientRect().height
      })))
  expect(touchTargetHeights.length).toBeGreaterThan(0)
  for (const target of touchTargetHeights) {
    expect(target.height, `${target.text} touch target`).toBeGreaterThanOrEqual(40)
  }
})

test('首次读取期间暴露忙碌状态并在完成后显示空状态', async ({ page }) => {
  let releaseRequest
  let markRequestStarted
  const requestStarted = new Promise(resolve => {
    markRequestStarted = resolve
  })
  await page.route(taskRoute, async route => {
    markRequestStarted()
    await new Promise(resolve => {
      releaseRequest = resolve
    })
    await route.fulfill(ok([]))
  })

  await page.goto('/ai-score-upload')
  await requestStarted
  const queue = page.locator('.upload-task-queue')
  await expect(queue).toHaveAttribute('aria-busy', 'true')
  await expect(page.getByRole('status', { name: '正在读取评分任务' })).toBeVisible()
  releaseRequest()
  await expect(queue).toHaveAttribute('aria-busy', 'false')
  await expect(page.getByRole('status').filter({ hasText: '还没有评分任务' })).toBeVisible()
})

test('首次读取失败使用警示状态说明任务不可读', async ({ page }) => {
  await page.route(taskRoute, route => route.fulfill({
    status: 500,
    contentType: 'application/json',
    body: JSON.stringify({ message: 'temporary failure' })
  }))

  await page.goto('/ai-score-upload')
  await expect(page.getByRole('alert')).toContainText('任务暂时无法读取')
})

test('手动刷新任务时刷新按钮进入禁用忙碌态', async ({ page }) => {
  let calls = 0
  let releaseRefresh
  let markRefreshStarted
  const refreshStarted = new Promise(resolve => {
    markRefreshStarted = resolve
  })
  await page.route(taskRoute, async route => {
    calls += 1
    if (calls === 1) {
      await route.fulfill(ok(uploadTasks()))
      return
    }
    markRefreshStarted()
    await new Promise(resolve => {
      releaseRefresh = resolve
    })
    await route.fulfill(ok(uploadTasks()))
  })

  await page.goto('/ai-score-upload')
  await expect(page.getByText('智能仓储路演.mp4')).toBeVisible()
  const refreshButton = page.getByRole('button', { name: '刷新任务' })
  await refreshButton.click()
  await refreshStarted
  await expect(refreshButton).toHaveAttribute('aria-busy', 'true')
  await expect(refreshButton).toBeDisabled()
  releaseRefresh()
  await expect(refreshButton).not.toHaveAttribute('aria-busy', 'true')
  await expect(refreshButton).toBeEnabled()
})

test('完成上传后重试失败任务会清除上一轮本地传输数据', async ({ page }) => {
  await page.route(taskRoute, route => route.fulfill(ok(uploadTasks())))
  await page.route('**/api/ai-score/upload-session', route => route.fulfill(ok({
    sessionId: 302,
    sessionNo: 'AIS-302',
    status: 'queued',
    currentStage: 'queued',
    progressPercent: 0,
    fileName: 'first-round.mp4',
    teamId: 1,
    teamName: '应用攻坚队',
    trackName: '物流与供应链赛道'
  })))

  await page.goto('/ai-score-upload')
  const videoInput = page.locator('input[type="file"]').first()
  await videoInput.setInputFiles({
    name: 'first-round.mp4',
    mimeType: 'video/mp4',
    buffer: Buffer.from('first round video')
  })
  await page.getByRole('button', { name: '开始上传评分' }).click()
  await expect(page.getByText('上传视频评分会话已创建')).toBeVisible()
  await expect(page.getByRole('progressbar', { name: '本地文件上传进度' })).toHaveCount(0)

  await page.getByRole('button', { name: '重新上传' }).click()
  await expect(page.getByRole('progressbar', { name: '本地文件上传进度' })).toHaveCount(0)

  await videoInput.setInputFiles({
    name: 'second-round.mp4',
    mimeType: 'video/mp4',
    buffer: Buffer.from('new')
  })
  await expect(page.getByRole('progressbar', { name: '本地文件上传进度' })).toHaveCount(0)
  await expect(page.getByText('请重新选择本地视频文件')).toHaveCount(0)
  await expect(page.getByText('00:00', { exact: false })).toHaveCount(0)
})

test('上传请求进行中禁用重试并使用提交瞬间的文件快照完成上传', async ({ page }) => {
  let releaseUpload
  let markUploadStarted
  let queueCalls = 0
  let releaseTrailingQueue
  const uploadStarted = new Promise(resolve => {
    markUploadStarted = resolve
  })
  await page.route(taskRoute, async route => {
    queueCalls += 1
    if (queueCalls === 1) {
      await route.fulfill(ok(uploadTasks()))
      return
    }
    await new Promise(resolve => {
      releaseTrailingQueue = resolve
    })
    await route.fulfill(ok(uploadTasks()))
  })
  await page.route('**/api/ai-score/upload-session', async route => {
    markUploadStarted()
    await new Promise(resolve => {
      releaseUpload = resolve
    })
    await route.fulfill(ok({
      sessionId: 304,
      sessionNo: 'AIS-304',
      status: 'queued',
      currentStage: 'queued',
      progressPercent: 0,
      fileName: '竞态上传.mp4',
      teamId: 1,
      teamName: '应用攻坚队',
      trackName: '物流与供应链赛道'
    }))
  })

  await page.goto('/ai-score-upload')
  const videoInput = page.locator('input[type="file"]').first()
  await videoInput.setInputFiles({
    name: '竞态上传.mp4',
    mimeType: 'video/mp4',
    buffer: Buffer.from('inflight video')
  })
  await page.getByRole('button', { name: '开始上传评分' }).click()
  await uploadStarted

  const retryButton = page.getByRole('button', { name: '重新上传' })
  await expect(retryButton).toBeDisabled()
  await expect(page.getByRole('combobox', { name: '项目团队' })).toBeDisabled()
  await expect(page.getByRole('button', { name: '评分偏好' })).toBeDisabled()
  await retryButton.dispatchEvent('click')
  expect(await videoInput.evaluate(input => input.files.length)).toBe(1)

  releaseUpload()
  await expect(page.getByText('上传视频评分会话已创建')).toBeVisible()
  await expect(page.locator('.task-row').filter({ hasText: '竞态上传.mp4' })).toBeVisible()
  await expect(page.getByText('上传失败', { exact: true })).toHaveCount(0)
  releaseTrailingQueue?.()
})

test('上传评分页挂载和刷新时恢复上传任务队列', async ({ page }) => {
  let calls = 0
  await page.route(taskRoute, route => {
    calls += 1
    return route.fulfill(ok([]))
  })

  await page.goto('/ai-score-upload')
  await expect.poll(() => calls).toBe(1)

  await page.reload()
  await expect.poll(() => calls).toBeGreaterThanOrEqual(2)
})

test('存在活跃上传任务时每三秒轮询', async ({ page }) => {
  let calls = 0
  await page.route(taskRoute, route => {
    calls += 1
    return route.fulfill(ok([scoringTask()]))
  })

  await page.goto('/ai-score-upload')
  await expect.poll(() => calls).toBe(1)
  await page.waitForTimeout(2650)
  expect(calls).toBe(1)
  await page.waitForTimeout(650)
  await expect.poll(() => calls, { timeout: 2000 }).toBe(2)
})

test('规范化后的终态队列停止轮询', async ({ page }) => {
  let calls = 0
  await page.route(taskRoute, route => {
    calls += 1
    return route.fulfill(ok([
      { ...scoringTask(), sessionId: 902, status: ' completed ', progressPercent: 100 },
      { ...scoringTask(), sessionId: 903, status: 'FAILED', progressPercent: 100 },
      { ...scoringTask(), sessionId: 904, status: 'Cancelled', progressPercent: 100 }
    ]))
  })

  await page.goto('/ai-score-upload')
  await expect.poll(() => calls).toBe(1)
  await page.waitForTimeout(3300)
  expect(calls).toBe(1)
})

test('连续两次失败后 focus 成功恢复三秒轮询', async ({ page }) => {
  let calls = 0
  await page.route(taskRoute, route => {
    calls += 1
    if (calls === 1) return route.fulfill(ok([scoringTask()]))
    if (calls === 4) return route.fulfill(ok([scoringTask()]))
    return route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ message: 'temporary failure' }) })
  })

  await page.goto('/ai-score-upload')
  await expect.poll(() => calls, { timeout: 10_000 }).toBe(3)
  await page.evaluate(() => window.dispatchEvent(new Event('focus')))
  await expect.poll(() => calls).toBe(4)
  await page.waitForTimeout(2650)
  expect(calls).toBe(4)
  await page.waitForTimeout(650)
  await expect.poll(() => calls, { timeout: 2000 }).toBe(5)
})

test('连续两次轮询失败后停止高频请求', async ({ page }) => {
  let calls = 0
  await page.route(taskRoute, route => {
    calls += 1
    if (calls === 1) return route.fulfill(ok([scoringTask()]))
    return route.fulfill({ status: 500, contentType: 'application/json', body: JSON.stringify({ message: 'temporary failure' }) })
  })

  await page.goto('/ai-score-upload')
  await expect.poll(() => calls, { timeout: 10_000 }).toBe(3)
  await page.waitForTimeout(3500)
  expect(calls).toBe(3)
})

test('后台队列 401 会清除登录状态并进入引导页', async ({ page }) => {
  await page.route(taskRoute, route => route.fulfill({
    status: 401,
    contentType: 'application/json',
    body: JSON.stringify({ message: 'expired token' })
  }))

  await page.goto('/ai-score-upload')
  await expect(page).toHaveURL(/\/intro$/)
  await expect.poll(() => page.evaluate(() => localStorage.getItem('orep_user_token'))).toBeNull()
})

test('首个队列请求飞行中收到 focus 会立即补发同步', async ({ page }) => {
  let calls = 0
  let releaseFirstRequest
  let markFirstRequest
  const firstRequestStarted = new Promise(resolve => {
    markFirstRequest = resolve
  })

  await page.route(taskRoute, async route => {
    calls += 1
    if (calls === 1) {
      markFirstRequest()
      await new Promise(resolve => {
        releaseFirstRequest = resolve
      })
    }
    await route.fulfill(ok([scoringTask()]))
  })

  await page.goto('/ai-score-upload')
  await firstRequestStarted
  await page.evaluate(() => window.dispatchEvent(new Event('focus')))
  releaseFirstRequest()
  await expect.poll(() => calls, { timeout: 1000 }).toBe(2)
})

test('真实上传完成时会补发被首个队列请求占用的刷新', async ({ page }) => {
  let calls = 0
  let uploadCalls = 0
  let releaseFirstRequest
  let markFirstRequest
  const firstRequestStarted = new Promise(resolve => {
    markFirstRequest = resolve
  })

  await page.route(taskRoute, async route => {
    calls += 1
    if (calls === 1) {
      markFirstRequest()
      await new Promise(resolve => {
        releaseFirstRequest = resolve
      })
      await route.fulfill(ok([]))
      return
    }
    await route.fulfill(ok([{ ...scoringTask(), sessionId: 999 }]))
  })
  await page.route('**/api/ai-score/upload-session', route => {
    uploadCalls += 1
    return route.fulfill(ok({
      sessionId: 999,
      sessionNo: 'AIS-999',
      status: 'queued',
      currentStage: 'queued',
      progressPercent: 0,
      fileName: 'pitch.mp4'
    }))
  })

  await page.goto('/ai-score-upload')
  await firstRequestStarted
  await page.locator('input[type="file"]').first().setInputFiles({
    name: 'pitch.mp4',
    mimeType: 'video/mp4',
    buffer: Buffer.from('video')
  })
  await page.getByRole('button', { name: '开始上传评分' }).click()
  await expect.poll(() => uploadCalls).toBe(1)
  releaseFirstRequest()
  await expect.poll(() => calls, { timeout: 1000 }).toBe(2)
})

test('页面卸载后不会由未完成同步重新启动轮询', async ({ page }) => {
  let calls = 0
  let releaseFirstRequest
  let markFirstRequest
  let markFirstResponseSent
  const firstRequestStarted = new Promise(resolve => {
    markFirstRequest = resolve
  })
  const firstResponseSent = new Promise(resolve => {
    markFirstResponseSent = resolve
  })

  await page.route('**/api/ai-score/reports/summary?*', route => route.fulfill(ok([])))
  await page.route('**/api/meeting/my-history', route => route.fulfill(ok([])))

  await page.route(taskRoute, async route => {
    calls += 1
    if (calls === 1) {
      markFirstRequest()
      await new Promise(resolve => {
        releaseFirstRequest = resolve
      })
    }
    await route.fulfill(ok([scoringTask()]))
    if (calls === 1) markFirstResponseSent()
  })

  await page.goto('/ai-score-upload')
  await firstRequestStarted
  await page.getByRole('link', { name: '返回评分报告' }).click()
  await expect(page).toHaveURL(/\/online-meeting\?tab=reports$/)
  releaseFirstRequest()
  await firstResponseSent
  await page.waitForTimeout(150)
  await page.waitForTimeout(3200)
  expect(calls).toBe(1)
})
