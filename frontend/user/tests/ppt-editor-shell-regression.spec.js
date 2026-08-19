import { expect, test } from '@playwright/test'

const unexpectedRequestsByPage = new WeakMap()

const restoredJob = {
  job_id: 'job-restore',
  deck_type: 'paper',
  render_engine: 'svg',
  status: 'complete',
  progress: 1,
  slides_completed: 0,
  total_slides: 0,
  file: { name: '已保存的 PPT.pdf', size: 1024 }
}

async function mockPptEditorApis(page, {
  delayRestore = false,
  delayGenerate = false,
  delayDownload = false,
  job = restoredJob
} = {}) {
  let releaseRestore = () => {}
  let releaseGenerate = () => {}
  let releaseDownload = () => {}
  let markRestoreRequested = () => {}
  let markRestoreFulfilled = () => {}
  const jobRequests = []
  let generateRequests = 0
  let downloadRequests = 0
  const unexpectedRequests = []
  unexpectedRequestsByPage.set(page, unexpectedRequests)
  const restoreRequested = new Promise(resolve => { markRestoreRequested = resolve })
  const restoreFulfilled = new Promise(resolve => { markRestoreFulfilled = resolve })
  const restoreGate = delayRestore
    ? new Promise(resolve => { releaseRestore = resolve })
    : Promise.resolve()
  const generateGate = delayGenerate
    ? new Promise(resolve => { releaseGenerate = resolve })
    : Promise.resolve()
  const downloadGate = delayDownload
    ? new Promise(resolve => { releaseDownload = resolve })
    : Promise.resolve()

  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url())
    const method = route.request().method()
    const isRestoreDetail = url.pathname === `/api/ppt/history/${job.job_id}`
    if (url.pathname.includes(job.job_id)) jobRequests.push(url.pathname)
    let body = { code: 200, data: {} }

    if (method === 'POST' && ['/api/monitor/heartbeat', '/api/monitor/track'].includes(url.pathname)) {
      body = { code: 200, data: { accepted: true } }
    } else if (method === 'GET' && url.pathname === '/api/collaboration/summary') {
      body = { code: 200, data: { pendingInvitations: 0, unreadMessages: 0, activeSessions: 0, items: [] } }
    } else if (method === 'GET' && url.pathname === '/api/notifications') {
      body = { code: 200, data: { items: [], unreadCount: 0 } }
    } else if (method === 'GET' && url.pathname === '/api/ppt/history') {
      body = { jobs: [job] }
    } else if (method === 'GET' && url.pathname === `/api/ppt/history/${job.job_id}`) {
      markRestoreRequested()
      await restoreGate
      body = { job, events: [] }
    } else if (method === 'GET' && url.pathname === '/api/ppt/health') {
      body = { status: 'ok', image2_configured: true }
    } else if (method === 'GET' && url.pathname === '/api/ppt/providers') {
      body = { providers: [{ provider: 'mimo', models: [{ id: 'mimo-v2.5-pro', name: 'MiMo' }] }] }
    } else if (method === 'GET' && url.pathname === '/api/ppt/templates') {
      body = []
    } else if (method === 'GET' && url.pathname.startsWith(`/api/ppt/preview/${job.job_id}`)) {
      body = { slides: [] }
    } else if (method === 'GET' && url.pathname === `/api/ppt/critic/${job.job_id}`) {
      body = { events: [] }
    } else if (method === 'GET' && url.pathname === `/api/ppt/versions/${job.job_id}`) {
      body = { versions: [] }
    } else if (method === 'POST' && url.pathname === '/api/ppt/upload') {
      body = { session_id: 'uploaded-session', file_info: { name: 'source.pdf', size: 12 } }
    } else if (method === 'POST' && url.pathname === '/api/ppt/generate') {
      generateRequests += 1
      await generateGate
      body = { job_id: 'generated-job' }
    } else if (method === 'GET' && url.pathname === `/api/ppt/download/${job.job_id}`) {
      downloadRequests += 1
      await downloadGate
      return route.fulfill({
        status: 200,
        contentType: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        headers: { 'content-disposition': 'attachment; filename=\"generated.pptx\"' },
        body: 'ppt'
      })
    } else {
      unexpectedRequests.push({ method, path: url.pathname })
      return route.abort('blockedbyclient')
    }

    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(body)
    })
    if (isRestoreDetail) markRestoreFulfilled()
  })

  return {
    jobRequests,
    releaseRestore,
    restoreRequested,
    restoreFulfilled,
    releaseGenerate,
    releaseDownload,
    get generateRequests() { return generateRequests },
    get downloadRequests() { return downloadRequests }
  }
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(job => {
    localStorage.setItem('orep_user_token', 'ppt-shell-regression-token')
    localStorage.setItem(
      'orep:ppt-editor:last-job:anonymous',
      JSON.stringify({ jobId: job.job_id, activePage: 1, updatedAt: Date.now() })
    )
  }, restoredJob)
})

test.afterEach(async ({ page }) => {
  expect(unexpectedRequestsByPage.get(page) || []).toEqual([])
})

test('explicit setup intent wins over a delayed automatic history restore', async ({ page }) => {
  const {
    releaseRestore,
    restoreRequested,
    restoreFulfilled
  } = await mockPptEditorApis(page, { delayRestore: true })

  await page.goto('/ppt-editor')
  await restoreRequested
  await page.getByRole('button', { name: '开始创建' }).click()
  await expect(page).toHaveURL(/\/ppt-editor\?view=setup$/)
  await expect(page.locator('.ai-app-shell')).toHaveClass(/is-task/)

  releaseRestore()
  await restoreFulfilled
  await page.waitForTimeout(100)

  await expect(page.getByRole('heading', { level: 1, name: '创建 PPT' })).toBeVisible()
  await expect(page.locator('.ai-app-shell')).toHaveClass(/is-task/)
  await expect(page).toHaveURL(/\/ppt-editor\?view=setup$/)

  await page.getByRole('link', { name: '返回PPT 制作' }).click()
  await expect(page).toHaveURL(/\/ppt-editor$/)
  await expect(page.locator('.ai-app-shell')).toHaveClass(/is-landing/)

  await page.goBack()
  await expect(page).toHaveURL(/\/ppt-editor\?view=setup$/)
  await expect(page.locator('.ai-app-shell')).toHaveClass(/is-task/)

  await page.goForward()
  await expect(page).toHaveURL(/\/ppt-editor$/)
  await expect(page.locator('.ai-app-shell')).toHaveClass(/is-landing/)
})

test('1024px workspace lets the shell body scroll to the log panel', async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 800 })
  await mockPptEditorApis(page)

  await page.goto('/ppt-editor')
  await expect(page.locator('.ai-app-shell')).toHaveClass(/is-workspace/)

  const body = page.locator('.ai-app-shell__body')
  const metrics = await body.evaluate(element => ({
    clientHeight: element.clientHeight,
    scrollHeight: element.scrollHeight
  }))
  expect(metrics.scrollHeight).toBeGreaterThan(metrics.clientHeight)

  const logPanel = page.locator('.log-panel')
  await logPanel.scrollIntoViewIfNeeded()
  await expect(logPanel).toBeInViewport()
})

test('leaving PPT editor cancels an already-started automatic restore', async ({ page }) => {
  const runningJob = {
    ...restoredJob,
    job_id: 'j1',
    status: 'generation',
    progress: 0.45
  }
  const pptSockets = []
  page.on('websocket', socket => {
    if (socket.url().includes(`/api/ppt/ws/${runningJob.job_id}`)) {
      pptSockets.push(socket.url())
    }
  })
  await page.addInitScript(job => {
    localStorage.setItem(
      'orep:ppt-editor:last-job:anonymous',
      JSON.stringify({ jobId: job.job_id, activePage: 1, updatedAt: Date.now() })
    )
  }, runningJob)
  const {
    jobRequests,
    releaseRestore,
    restoreRequested,
    restoreFulfilled
  } = await mockPptEditorApis(page, { delayRestore: true, job: runningJob })

  await page.goto('/ppt-editor')
  await restoreRequested
  await page.getByRole('link', { name: '返回AI 应用中心' }).click()
  await expect(page).toHaveURL(/\/ai-apps$/)

  releaseRestore()
  await restoreFulfilled
  await page.waitForTimeout(250)

  expect(jobRequests).toEqual([`/api/ppt/history/${runningJob.job_id}`])
  expect(pptSockets).toEqual([])
})

test('PPT generation is single-flight even when the primary action is clicked twice', async ({ page }) => {
  const controls = await mockPptEditorApis(page, { delayGenerate: true })
  await page.goto('/ppt-editor?view=setup')

  const fileInput = page.locator('.file-drop input[type=file]')
  await fileInput.setInputFiles({
    name: 'source.pdf',
    mimeType: 'application/pdf',
    buffer: Buffer.from('%PDF-1.4')
  })
  const generate = page.getByRole('button', { name: /开始生成/ })
  await expect(generate).toBeEnabled()
  await generate.evaluate(button => {
    button.click()
    button.click()
  })

  await expect.poll(() => controls.generateRequests).toBe(1)
  controls.releaseGenerate()
})

test('leaving during a delayed PPT download produces no browser download or stale toast', async ({ page }) => {
  let browserDownloads = 0
  page.on('download', () => {
    browserDownloads += 1
  })
  const controls = await mockPptEditorApis(page, { delayDownload: true })
  await page.goto('/ppt-editor')
  await expect(page.locator('.ai-app-shell')).toHaveClass(/is-workspace/)
  await page.getByRole('button', { name: '下载 PPTX' }).click()
  await expect.poll(() => controls.downloadRequests).toBe(1)

  await page.locator('.ai-app-header__back').click()
  await expect(page).toHaveURL(/\/ppt-editor\?view=history$/)
  controls.releaseDownload()
  await page.waitForTimeout(250)

  expect(browserDownloads).toBe(0)
  await expect(page.locator('.el-message')).toHaveCount(0)
})
