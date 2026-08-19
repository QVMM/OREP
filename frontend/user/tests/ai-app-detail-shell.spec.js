import { expect, test } from '@playwright/test'

const unexpectedRequestsByPage = new WeakMap()

const restoredPptJob = {
  job_id: 'shell-workspace-job',
  deck_type: 'paper',
  render_engine: 'svg',
  status: 'complete',
  progress: 1,
  slides_completed: 0,
  total_slides: 0,
  file: { name: '统一外壳测试.pdf', size: 1024 },
}

const scriptFixture = {
  id: 81,
  title: '项目讲解稿',
  source_type: 'manual',
  content: JSON.stringify([
    {
      id: 'chapter-1',
      title: '项目开场',
      totalDuration: 3,
      steps: [
        {
          id: 'step-1',
          role: '主讲人',
          duration: 1,
          focus: '封面',
          content: '介绍项目背景与核心价值。',
          notes: '',
          transition: '',
        },
      ],
    },
  ]),
  roles: JSON.stringify([{ id: 'role-1', label: '主讲人', color: '#409eff' }]),
}

const templateFixture = {
  id: 7,
  name: '项目复盘模板',
  content: scriptFixture.content,
  roles: scriptFixture.roles,
}

const createdTemplateScript = {
  ...scriptFixture,
  id: 82,
  title: '新建讲稿',
}

const historyFixture = {
  task: {
    id: 55,
    project_name: '统一外壳历史项目',
    status: 'completed',
    domain: 'ai_iot',
    created_at: '2026-07-30T10:00:00Z',
  },
  html_pages: [],
  snapshots: [],
  deliverability: {
    status: 'ready',
    label: '可下载',
    short_hint: '当前版本可下载',
    blockers: [],
    warnings: [],
  },
}

async function installAuthenticatedUser(page, { restorePpt = false } = {}) {
  await page.addInitScript(({ job, shouldRestore }) => {
    const payload = btoa(JSON.stringify({
      sub: 9,
      exp: Math.floor(Date.now() / 1000) + 3600,
    }))
    const user = { id: 9, username: '统一外壳测试用户', role: 'STUDENT', tenantId: 1 }
    localStorage.setItem('orep_user_token', `test.${payload}.signature`)
    localStorage.setItem('orep_user', JSON.stringify(user))
    localStorage.setItem('user', JSON.stringify(user))
    if (shouldRestore) {
      localStorage.setItem(
        'orep:ppt-editor:last-job:9',
        JSON.stringify({ jobId: job.job_id, activePage: 1, updatedAt: Date.now() })
      )
      localStorage.setItem(
        'orep:ppt-editor:last-job:anonymous',
        JSON.stringify({ jobId: job.job_id, activePage: 1, updatedAt: Date.now() })
      )
    }
  }, { job: restoredPptJob, shouldRestore: restorePpt })
}

async function mockAiAppApis(page, {
  includeRestoredPpt = false,
  restoredPptDetailHandler = null,
} = {}) {
  const unexpectedRequests = []
  unexpectedRequestsByPage.set(page, unexpectedRequests)
  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url())
    const path = url.pathname
    const method = route.request().method()
    const fulfill = (data, { wrapped = true } = {}) => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(wrapped ? { code: 200, data } : data),
    })

    if (method === 'POST' && (path === '/api/monitor/heartbeat' || path === '/api/monitor/track')) {
      return fulfill({ accepted: true })
    }
    if (method === 'GET' && path === '/api/collaboration/summary') {
      return fulfill({
        pendingInvitations: 0,
        unreadMessages: 0,
        activeSessions: 0,
        items: [],
      })
    }
    if (method === 'GET' && path === '/api/notifications') {
      return fulfill({ items: [], unreadCount: 0 })
    }
    if (method === 'GET' && path === '/api/project-prep/bootstrap') {
      return fulfill({
        teams: [{ id: 1, name: '统一外壳项目组' }],
        activeTeamId: 1,
        dashboard: {},
        prepSession: null,
        scripts: [scriptFixture],
        scriptTemplates: [],
        resources: [],
      })
    }
    if (method === 'GET' && path === '/api/resource-center') {
      return fulfill({
        folders: [],
        teamFiles: [],
        publicFiles: [],
        rootFolderKey: 'root',
      })
    }
    if (path === '/api/script/81' && method === 'GET') return fulfill(scriptFixture)
    if (path === '/api/script/81' && method === 'PUT') {
      return fulfill({ ...scriptFixture, ...route.request().postDataJSON(), id: 81 })
    }
    if (method === 'GET' && path === '/api/script-template/7') return fulfill(templateFixture)
    if (method === 'POST' && path === '/api/script') {
      return fulfill({ ...createdTemplateScript, ...route.request().postDataJSON(), id: 82 })
    }
    if (method === 'GET' && path === '/api/script/82') return fulfill(createdTemplateScript)
    if (method === 'PUT' && path === '/api/script/82') {
      return fulfill({ ...createdTemplateScript, ...route.request().postDataJSON(), id: 82 })
    }
    if (method === 'GET' && path === '/api/ppt/history') {
      return fulfill({ jobs: includeRestoredPpt ? [restoredPptJob] : [] }, { wrapped: false })
    }
    if (method === 'GET' && path === `/api/ppt/history/${restoredPptJob.job_id}`) {
      if (restoredPptDetailHandler) return restoredPptDetailHandler(route)
      return fulfill({ job: restoredPptJob, events: [] }, { wrapped: false })
    }
    if (method === 'GET' && path === '/api/ppt/health') {
      return fulfill({ status: 'ok', image2_configured: true }, { wrapped: false })
    }
    if (method === 'GET' && path === '/api/ppt/providers') return fulfill({ providers: [] }, { wrapped: false })
    if (method === 'GET' && path === '/api/ppt/templates') return fulfill([], { wrapped: false })
    if (method === 'GET' && path === `/api/ppt/preview/${restoredPptJob.job_id}`) {
      return fulfill({ slides: [] }, { wrapped: false })
    }
    if (method === 'GET' && path === `/api/ppt/critic/${restoredPptJob.job_id}`) {
      return fulfill({ events: [] }, { wrapped: false })
    }
    if (method === 'GET' && path === `/api/ppt/versions/${restoredPptJob.job_id}`) {
      return fulfill({ versions: [] }, { wrapped: false })
    }
    if (method === 'GET' && path === '/api/ppt/themes') return fulfill([])
    if (method === 'GET' && path === '/api/ppt/user/9/tasks') return fulfill([])
    if (method === 'GET' && path === '/api/ppt/task/55/history-detail') return fulfill(historyFixture)
    if (method === 'GET' && path === '/api/student/home') {
      return fulfill({
        profile: { username: '统一外壳测试用户' },
        camp: { currentDay: 2, totalDays: 21, remainingDays: 19 },
        todayTraining: { hasTrainingDay: false },
        roadshow: { hasRoadshow: false },
        latestScore: { hasReport: false },
        nextActions: [],
      })
    }

    unexpectedRequests.push({ method, path })
    return route.abort('blockedbyclient')
  })
  return unexpectedRequests
}

test.afterEach(async ({ page }) => {
  expect(unexpectedRequestsByPage.get(page) || []).toEqual([])
})

async function expectSinglePageTitle(page, name) {
  const headings = page.getByRole('heading', { level: 1 })
  await expect(headings).toHaveCount(1)
  await expect(headings).toHaveAccessibleName(name)
}

async function expectNoDocumentOverflow(page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth - window.innerWidth
  )
  expect(overflow).toBeLessThanOrEqual(1)
}

async function expectShellInset(page, expectedPixels) {
  const shell = page.locator('.ai-app-shell')
  await expect(shell).toBeVisible()
  expect(await shell.evaluate(element => parseFloat(getComputedStyle(element).paddingLeft)))
    .toBe(expectedPixels)
}

test('desktop landing and task routes share one title, stable parents, and approved widths', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await installAuthenticatedUser(page)
  await mockAiAppApis(page)

  await page.goto('/ppt-editor')
  await expect(page.locator('.ai-app-shell')).toHaveClass(/is-landing/)
  await expect(page.locator('.ai-app-content')).toHaveClass(/is-wide/)
  await expectSinglePageTitle(page, 'PPT 制作')
  await expectShellInset(page, 40)
  await expect(page.locator('.ai-app-header__back')).toHaveAccessibleName('返回AI 应用中心')

  await page.getByRole('button', { name: '开始创建' }).click()
  await expect(page).toHaveURL(/\/ppt-editor\?view=setup$/)
  await expect(page.locator('.ai-app-shell')).toHaveClass(/is-task/)
  await expect(page.locator('.ai-app-content')).toHaveClass(/is-standard/)
  await expectSinglePageTitle(page, '创建 PPT')
  await page.locator('.ai-app-header__back').click()
  await expect(page).toHaveURL(/\/ppt-editor$/)
  await expect(page.locator('.ai-app-shell')).toHaveClass(/is-landing/)

  await page.goto('/script-editor')
  await expect(page.locator('.ai-app-shell')).toHaveClass(/is-landing/)
  await expect(page.locator('.ai-app-content')).toHaveClass(/is-wide/)
  await expectSinglePageTitle(page, '讲稿制作')
  await expect(page.locator('.ai-app-header__back')).toHaveAccessibleName('返回AI 应用中心')
  await expect(page.locator('.ai-app-header__actions')).toHaveCount(0)
  await expect(page.getByRole('button', { name: '新建讲稿' })).toHaveCount(1)

  await page.goto('/ppt-generator')
  await expect(page.locator('.ai-app-shell')).toHaveClass(/is-task/)
  await expect(page.locator('.ai-app-content')).toHaveClass(/is-standard/)
  await expectSinglePageTitle(page, '创建 PPT')
  await expect(page.locator('.ai-app-header__back')).toHaveAccessibleName('返回PPT 制作')
  await expect(page.locator('.ai-app-header__back')).toHaveAttribute('href', '/ppt-editor')

  await page.goto('/ppt-history/55')
  await expect(page.locator('.ai-app-shell')).toHaveClass(/is-task/)
  await expect(page.locator('.ai-app-content')).toHaveClass(/is-wide/)
  await expectSinglePageTitle(page, '统一外壳历史项目')
  await expect(page.locator('.ai-app-header__back')).toHaveAccessibleName('返回最近记录')
  await expect(page.locator('.ai-app-header__back')).toHaveAttribute('href', '/ppt-editor?view=history')

  await page.goto('/script-editor/detail/81')
  await expect(page.locator('.ai-app-shell')).toHaveClass(/is-workspace/)
  await expect(page.locator('.ai-app-content')).toHaveClass(/is-fluid/)
  await expectSinglePageTitle(page, '项目讲解稿')
  await expect(page.getByRole('textbox', { name: '讲稿标题' })).toBeEditable()
  await expect(page.locator('.ai-app-header__back')).toHaveAccessibleName('返回讲稿列表')
})

test('PPT workspace remains fluid at 1181px and scrolls to its lower work area at 1024px', async ({ page }) => {
  await installAuthenticatedUser(page, { restorePpt: true })
  await mockAiAppApis(page, { includeRestoredPpt: true })

  await page.setViewportSize({ width: 1181, height: 820 })
  await page.goto('/ppt-editor')
  await expect(page.locator('.ai-app-shell')).toHaveClass(/is-workspace/)
  await expect(page.locator('.ai-app-content')).toHaveClass(/is-fluid/)
  await expectSinglePageTitle(page, '未命名 PPT')
  await expectNoDocumentOverflow(page)
  expect(await page.locator('.ai-app-shell__body').evaluate(
    element => parseFloat(getComputedStyle(element).paddingLeft)
  )).toBe(24)

  const fluidGeometry = await page.locator('.ai-app-shell__body').evaluate(element => ({
    width: element.getBoundingClientRect().width,
    parentWidth: element.parentElement.getBoundingClientRect().width,
  }))
  expect(Math.abs(fluidGeometry.width - fluidGeometry.parentWidth)).toBeLessThanOrEqual(1)

  await page.setViewportSize({ width: 1024, height: 800 })
  const body = page.locator('.ai-app-shell__body')
  expect(await body.evaluate(element => parseFloat(getComputedStyle(element).paddingLeft))).toBe(24)
  const scrollMetrics = await body.evaluate(element => ({
    clientHeight: element.clientHeight,
    scrollHeight: element.scrollHeight,
  }))
  expect(scrollMetrics.scrollHeight).toBeGreaterThan(scrollMetrics.clientHeight)
  const lowerPanel = page.locator('.log-panel')
  await lowerPanel.scrollIntoViewIfNeeded()
  await expect(lowerPanel).toBeInViewport()
})

test('script workspace stacks by 1024px and reaches lower content', async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 800 })
  await installAuthenticatedUser(page)
  await mockAiAppApis(page)
  await page.goto('/script-editor/detail/81')

  await expect(page.locator('.ai-app-shell')).toHaveClass(/is-workspace/)
  await expect(page.locator('.ai-app-content')).toHaveClass(/is-fluid/)
  await expectSinglePageTitle(page, '项目讲解稿')
  const bodyColumns = await page.locator('.editor-body').evaluate(
    element => getComputedStyle(element).gridTemplateColumns
  )
  expect(bodyColumns.trim().split(/\s+/)).toHaveLength(1)

  const shellBody = page.locator('.ai-app-shell__body')
  const lowerContent = page.locator('.support-fields')
  const lowerContentHandle = await lowerContent.elementHandle()
  const beforeScroll = await shellBody.evaluate((body, target) => {
    const bodyRect = body.getBoundingClientRect()
    const targetRect = target.getBoundingClientRect()
    return {
      bodyBottom: bodyRect.bottom,
      clientHeight: body.clientHeight,
      scrollHeight: body.scrollHeight,
      scrollTop: body.scrollTop,
      targetTop: targetRect.top,
    }
  }, lowerContentHandle)
  expect(beforeScroll.scrollHeight).toBeGreaterThan(beforeScroll.clientHeight)
  expect(beforeScroll.targetTop).toBeGreaterThanOrEqual(beforeScroll.bodyBottom)
  await shellBody.evaluate((body, target) => {
    const bodyTop = body.getBoundingClientRect().top
    const targetTop = target.getBoundingClientRect().top
    body.scrollTo({ top: body.scrollTop + targetTop - bodyTop, behavior: 'instant' })
  }, lowerContentHandle)
  const afterScroll = await shellBody.evaluate((body, target) => {
    const bodyRect = body.getBoundingClientRect()
    const targetRect = target.getBoundingClientRect()
    return {
      bodyBottom: bodyRect.bottom,
      bodyTop: bodyRect.top,
      scrollTop: body.scrollTop,
      targetBottom: targetRect.bottom,
      targetTop: targetRect.top,
    }
  }, lowerContentHandle)
  expect(afterScroll.scrollTop).toBeGreaterThan(beforeScroll.scrollTop)
  expect(afterScroll.targetTop).toBeLessThan(afterScroll.bodyBottom)
  expect(afterScroll.targetBottom).toBeGreaterThan(afterScroll.bodyTop)
})

test('script workspace exposes a pending state during the save debounce', async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 800 })
  await installAuthenticatedUser(page)
  await mockAiAppApis(page)
  await page.goto('/script-editor/detail/81')
  await expectSinglePageTitle(page, '项目讲解稿')

  const titleInput = page.getByRole('textbox', { name: '讲稿标题' })
  await titleInput.fill('项目讲解稿（修订）')
  await expect(page.locator('.ai-app-header__status')).toHaveText('等待保存')
})

test('script template creation stays in the workspace shell and resolves to a stable detail route', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await installAuthenticatedUser(page)
  await mockAiAppApis(page)
  await page.goto('/script-editor/template/7')

  await expect(page).toHaveURL(/\/script-editor\/detail\/82$/)
  await expect(page.locator('.ai-app-shell')).toHaveClass(/is-workspace/)
  await expect(page.locator('.ai-app-content')).toHaveClass(/is-fluid/)
  await expectSinglePageTitle(page, '新建讲稿')
  await expect(page.getByRole('textbox', { name: '讲稿标题' })).toBeEditable()
  await expect(page.locator('.ai-app-header__back')).toHaveAccessibleName('返回讲稿列表')
  await expect(page.locator('.ai-app-header__back')).toHaveAttribute('href', '/script-editor')
})

test('ordinary AI application pages use the exact approved responsive gutters', async ({ page }) => {
  await installAuthenticatedUser(page)
  await mockAiAppApis(page)
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/ppt-generator')
  await expectShellInset(page, 40)

  for (const [width, expectedInset] of [
    [1200, 32],
    [1181, 24],
    [1024, 24],
    [390, 16],
  ]) {
    await page.setViewportSize({ width, height: width === 390 ? 844 : 900 })
    await expectShellInset(page, expectedInset)
    await expectNoDocumentOverflow(page)
  }
})

test('390px landing, task, and workspace keep 16px gutters, safe space, actions, and no overflow', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await installAuthenticatedUser(page, { restorePpt: true })
  await mockAiAppApis(page, { includeRestoredPpt: true })

  await page.goto('/ppt-generator')
  await expectShellInset(page, 16)
  await expectSinglePageTitle(page, '创建 PPT')
  await expectNoDocumentOverflow(page)
  expect(await page.locator('.ai-app-shell').evaluate(
    element => parseFloat(getComputedStyle(element).paddingBottom)
  )).toBeGreaterThanOrEqual(96)

  await page.goto('/script-editor')
  await expectShellInset(page, 16)
  await expectSinglePageTitle(page, '讲稿制作')
  await expectNoDocumentOverflow(page)

  await page.goto('/ppt-editor')
  await expect(page.locator('.ai-app-shell')).toHaveClass(/is-workspace/)
  await expectSinglePageTitle(page, '未命名 PPT')
  await expectNoDocumentOverflow(page)
  const workspaceBodyPadding = await page.locator('.ai-app-shell__body').evaluate(element => ({
    bottom: parseFloat(getComputedStyle(element).paddingBottom),
    left: parseFloat(getComputedStyle(element).paddingLeft),
  }))
  expect(workspaceBodyPadding.bottom).toBeGreaterThanOrEqual(96)
  expect(workspaceBodyPadding.left).toBe(16)

  const actions = page.locator('.ai-app-header__actions')
  await expect(actions.getByRole('button', { name: '新建 PPT' })).toBeVisible()
  await expect(actions.getByRole('button', { name: '更多操作' })).toBeVisible()
  await expect(actions.locator('button:visible')).toHaveCount(2)
  await expect(actions.getByRole('button', { name: '最近记录' })).toBeHidden()
  await actions.getByRole('button', { name: '更多操作' }).click()
  await expect(page.getByRole('menuitem', { name: '最近记录' })).toBeVisible()
  await expect(page.getByRole('menuitem', { name: '调整生成设置' })).toBeVisible()
  await page.getByRole('menuitem', { name: '调整生成设置' }).click()
  await expect(page).toHaveURL(/\/ppt-editor\?view=setup$/)
  await page.goBack()
  await expect(page).toHaveURL(/\/ppt-editor$/)
  await expect(page.locator('.ai-app-header__back')).toHaveAccessibleName('返回PPT 列表')

  await page.goto('/script-editor/detail/81')
  const scriptActions = page.locator('.ai-app-header__actions')
  await expect(scriptActions.getByRole('button', { name: '导出 PDF' })).toBeVisible()
  await expect(scriptActions.getByRole('button', { name: '更多操作' })).toBeVisible()
  await expect(scriptActions.getByRole('button', { name: '存为模板' })).toBeHidden()
  await expect(scriptActions.locator('button:visible')).toHaveCount(2)
  const scriptActionLayout = await scriptActions.evaluate(element => ({
    clientWidth: element.clientWidth,
    scrollWidth: element.scrollWidth,
    children: Array.from(element.children).map(child => ({
      className: child.className,
      clientWidth: child.clientWidth,
      display: getComputedStyle(child).display,
      flex: getComputedStyle(child).flex,
    })),
  }))
  expect(
    scriptActionLayout.scrollWidth - scriptActionLayout.clientWidth,
    JSON.stringify(scriptActionLayout)
  ).toBeLessThanOrEqual(1)

  await scriptActions.getByRole('button', { name: '更多操作' }).click()
  const saveTemplateItem = page.getByRole('menuitem', { name: '存为模板' })
  await expect(saveTemplateItem).toBeVisible()
  await saveTemplateItem.click()
  await expect(page.getByRole('dialog', { name: '另存为模板' })).toBeVisible()
})

test('script workspace switches secondary actions exactly below the shared 768px header breakpoint', async ({ page }) => {
  await installAuthenticatedUser(page)
  await mockAiAppApis(page)

  await page.setViewportSize({ width: 767, height: 900 })
  await page.goto('/script-editor/detail/81')

  const actions = page.locator('.ai-app-header__actions')
  await expect(actions.getByRole('button', { name: '导出 PDF' })).toBeVisible()
  await expect(actions.getByRole('button', { name: '更多操作' })).toBeVisible()
  await expect(actions.getByRole('button', { name: '存为模板' })).toBeHidden()
  await expect(actions.locator('button:visible')).toHaveCount(2)
  expect(await actions.evaluate(
    element => element.scrollWidth - element.clientWidth
  )).toBeLessThanOrEqual(1)

  await page.setViewportSize({ width: 768, height: 900 })
  await expect(actions.getByRole('button', { name: '导出 PDF' })).toBeVisible()
  await expect(actions.getByRole('button', { name: '存为模板' })).toBeVisible()
  await expect(actions.getByRole('button', { name: '更多操作' })).toBeHidden()
  await expect(actions.locator('button:visible')).toHaveCount(2)
  expect(await actions.evaluate(
    element => element.scrollWidth - element.clientWidth
  )).toBeLessThanOrEqual(1)
})

test('PPT workspace switches secondary actions exactly below the shared 768px header breakpoint', async ({ page }) => {
  await installAuthenticatedUser(page, { restorePpt: true })
  await mockAiAppApis(page, { includeRestoredPpt: true })

  await page.setViewportSize({ width: 767, height: 900 })
  await page.goto('/ppt-editor')

  const actions = page.locator('.ai-app-header__actions')
  await expect(actions.getByRole('button', { name: '新建 PPT' })).toBeVisible()
  await expect(actions.getByRole('button', { name: '更多操作' })).toBeVisible()
  await expect(actions.getByRole('button', { name: '最近记录' })).toBeHidden()
  await expect(actions.getByRole('button', { name: '调整生成设置' })).toBeHidden()
  await expect(actions.locator('button:visible')).toHaveCount(2)
  expect(await actions.evaluate(
    element => element.scrollWidth - element.clientWidth
  )).toBeLessThanOrEqual(1)

  await page.setViewportSize({ width: 768, height: 900 })
  await expect(actions.getByRole('button', { name: '新建 PPT' })).toBeVisible()
  await expect(actions.getByRole('button', { name: '最近记录' })).toBeVisible()
  await expect(actions.getByRole('button', { name: '调整生成设置' })).toBeVisible()
  await expect(actions.getByRole('button', { name: '更多操作' })).toBeHidden()
  await expect(actions.locator('button:visible')).toHaveCount(3)
  expect(await actions.evaluate(
    element => element.scrollWidth - element.clientWidth
  )).toBeLessThanOrEqual(1)
})

test('closing PPT history before a delayed detail response keeps the landing view current', async ({ page }) => {
  let detailRequests = 0
  let releaseDetail
  const detailGate = new Promise(resolve => {
    releaseDetail = resolve
  })

  await installAuthenticatedUser(page)
  await mockAiAppApis(page, {
    includeRestoredPpt: true,
    restoredPptDetailHandler: async route => {
      detailRequests += 1
      await detailGate
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ job: restoredPptJob, events: [] }),
      })
    },
  })

  await page.goto('/ppt-editor?view=history')
  const historyDrawer = page.locator('.history-drawer')
  await historyDrawer.getByRole('button', { name: /统一外壳测试/ }).click()
  await expect.poll(() => detailRequests).toBe(1)

  await historyDrawer.locator('.el-drawer__close-btn').click()
  await expect(historyDrawer).toBeHidden()
  await expect(page).toHaveURL(/\/ppt-editor$/)

  releaseDetail()
  await page.waitForTimeout(300)

  await expect(page.locator('.ppt-agent-page')).toHaveClass(/is-landing-view/)
  await expectSinglePageTitle(page, 'PPT 制作')
  await expect(page.getByText('历史任务已打开', { exact: true })).toHaveCount(0)
  expect(await page.evaluate(
    () => localStorage.getItem('orep:ppt-editor:last-job:9')
  )).toBeNull()
})

test('leaving a delayed script template load cannot create or hijack a script route', async ({ page }) => {
  await page.setViewportSize({ width: 1024, height: 800 })
  await installAuthenticatedUser(page)
  await mockAiAppApis(page)

  let releaseTemplate
  let templateRequests = 0
  let createRequests = 0
  const templateGate = new Promise(resolve => {
    releaseTemplate = resolve
  })
  await page.route('**/api/script-template/7', async route => {
    templateRequests += 1
    await templateGate
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: 200, data: templateFixture }),
    })
  })
  await page.route('**/api/script', async route => {
    if (route.request().method() === 'POST') createRequests += 1
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: 200, data: createdTemplateScript }),
    })
  })

  await page.goto('/script-editor/template/7')
  await expect.poll(() => templateRequests).toBe(1)
  await page.locator('.ai-app-header__back').click()
  await expect(page).toHaveURL(/\/script-editor$/)

  releaseTemplate()
  await page.waitForTimeout(250)

  expect(createRequests).toBe(0)
  await expect(page).toHaveURL(/\/script-editor$/)
  await expect(page.locator('.el-message')).toHaveCount(0)
})

test('leaving during template creation cancels the pending save without blocking navigation', async ({ page }) => {
  await installAuthenticatedUser(page)
  await mockAiAppApis(page)

  let releaseCreate
  let createRequests = 0
  const createGate = new Promise(resolve => {
    releaseCreate = resolve
  })
  await page.route('**/api/script-template/7', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 200, data: templateFixture }),
  }))
  await page.route('**/api/script', async route => {
    createRequests += 1
    await createGate
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: 200, data: createdTemplateScript }),
    })
  })

  await page.goto('/script-editor/template/7')
  await expect.poll(() => createRequests).toBe(1)
  await page.locator('.ai-app-header__back').click()
  releaseCreate()

  await expect(page).toHaveURL(/\/script-editor$/)
  await expect(page.locator('.el-message')).toHaveCount(0)
})

test('resource center keeps the ordinary workspace gutter and flush routes release it on exit', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await installAuthenticatedUser(page)
  await mockAiAppApis(page)

  await page.goto('/resource-center')
  await expect(page.locator('.ai-app-shell')).toHaveCount(0)
  await expect(page.locator('.resource-browser__toolbar')).toBeVisible()
  const main = page.locator('.workspace-main')
  await expect(main).not.toHaveClass(/is-flush/)
  expect(await main.evaluate(element => parseFloat(getComputedStyle(element).paddingLeft))).toBe(40)

  await page.goto('/ppt-editor')
  await expect(main).toHaveClass(/is-flush/)
  expect(await main.evaluate(element => parseFloat(getComputedStyle(element).paddingLeft))).toBe(0)

  await page.goto('/ai-apps')
  await expect(main).not.toHaveClass(/is-flush/)
  expect(await main.evaluate(element => parseFloat(getComputedStyle(element).paddingLeft))).toBe(40)
})
