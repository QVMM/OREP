import { expect, test } from '@playwright/test'

const ok = data => ({
  status: 200,
  contentType: 'application/json',
  body: JSON.stringify({ code: 200, data })
})

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    const user = { username: '李林峰', role: 'STUDENT' }
    localStorage.setItem('orep_user_token', 'collaboration-pages-design-token')
    localStorage.setItem('token', 'collaboration-pages-design-token')
    localStorage.setItem('orep_user', JSON.stringify(user))
    localStorage.setItem('user', JSON.stringify(user))
  })

  await page.route('**/api/project-teams/my', route => route.fulfill(ok([
    { id: 7, name: '应用攻坚队', myRoleInTeam: 'CAPTAIN' }
  ])))
  await page.route('**/api/project-teams/7/dashboard', route => route.fulfill(ok({
    team: { id: 7, name: '应用攻坚队' },
    myRoleInTeam: 'CAPTAIN',
    currentUserId: 11,
    canManage: true,
    managementPermissions: { ASSIGN_TASK: true },
    metrics: { overallProgress: 35 },
    members: [],
    stages: [],
    tasks: [],
    submissions: [],
    materials: [],
    reviewIssues: [],
    abilities: [],
    roadshowMeetings: []
  })))
  await page.route('**/api/project-teams/7/roadshow-memory', route => route.fulfill(ok({})))
  await page.route('**/api/project-teams/position-roles*', route => route.fulfill(ok([])))
  await page.route('**/api/project-teams/7/tasks/36', route => route.fulfill(ok({
    taskBook: {
      summary: '先明确问题，再用真实证据完成验证。',
      contentHtml: '<p>这是需要展开后查看的正式任务描述。</p>',
      requirements: [{ id: 1, title: '提交访谈记录', description: '至少三份真实访谈记录。', required: true }],
      attachments: []
    }
  })))

  await page.route('**/api/project-prep/bootstrap*', route => route.fulfill(ok({
    teams: [{ id: 7, name: '应用攻坚队' }],
    activeTeamId: 7,
    dashboard: { team: { id: 7, name: '应用攻坚队' }, materials: [] },
    resources: [{
      id: 31,
      name: '赛项评分标准.pdf',
      fileName: '赛项评分标准.pdf',
      fileType: 'application/pdf',
      updatedAt: '2026-07-22T10:00:00'
    }]
  })))
  await page.route('**/api/ppt-template/categories', route => route.fulfill(ok([])))
})

test('任务管理使用实色任务队列且不横向溢出', async ({ page }) => {
  await page.setViewportSize({ width: 1288, height: 892 })
  await page.goto('/project-team')

  await expect(page.getByRole('heading', { name: '任务管理', level: 1 })).toBeVisible()
  await expect(page.getByRole('button', { name: '新建任务' })).toBeVisible()

  const metrics = await page.locator('.focused-task-layout').evaluate(layout => {
    const card = document.querySelector('.focused-task-overview')
    return {
      columns: getComputedStyle(layout).gridTemplateColumns.split(' ').length,
      backdrop: getComputedStyle(card).backdropFilter,
      backgroundImage: getComputedStyle(card).backgroundImage,
      noOverflow: document.documentElement.scrollWidth <= window.innerWidth
    }
  })
  expect(metrics.columns).toBe(1)
  expect(metrics.backdrop).toBe('none')
  expect(metrics.backgroundImage).toBe('none')
  expect(metrics.noOverflow).toBe(true)
})

test('资源中心使用单栏资料库并按需展开文件详情', async ({ page }) => {
  await page.setViewportSize({ width: 1288, height: 892 })
  await page.goto('/script-editor?tab=materials')

  await expect(page.getByRole('heading', { name: '资源中心', level: 1 })).toBeVisible()
  await expect(page.getByRole('searchbox', { name: '搜索文件' })).toBeVisible()
  await expect(page.getByRole('button', { name: '上传文件' })).toBeVisible()
  await expect(page.getByRole('navigation', { name: '文件筛选' })).toBeVisible()
  await expect(page.locator('.finder-inspector')).toHaveCount(0)
  await expect(page.locator('.finder-detail-inline')).toHaveCount(0)

  const metrics = await page.locator('.finder-window').evaluate(windowEl => ({
    columns: getComputedStyle(windowEl).gridTemplateColumns.split(' ').length,
    backgroundImage: getComputedStyle(windowEl).backgroundImage,
    noOverflow: document.documentElement.scrollWidth <= window.innerWidth
  }))
  expect(metrics.columns).toBe(1)
  expect(metrics.backgroundImage).toBe('none')
  expect(metrics.noOverflow).toBe(true)

  const firstFileRow = page.locator('.finder-row').first()
  await expect(firstFileRow.getByRole('button', { name: '下载' })).toBeVisible()
  await expect(firstFileRow.getByRole('button', { name: '详情' })).toHaveCount(0)

  await firstFileRow.click()
  await expect(page.locator('.finder-detail-inline')).toBeVisible()
  await expect(page.getByRole('button', { name: '收起详情' })).toHaveCount(0)
  await expect(page.locator('.finder-detail-inline button')).toHaveCount(0)
  await expect(page.locator('.finder-detail-inline .material-status-row')).toHaveCount(0)
  await expect(page.locator('.finder-detail-inline .material-detail-head')).toHaveCount(0)
  await expect(page.locator('.finder-detail-inline .material-detail-section')).toHaveCount(2)
  await expect(page.locator('.finder-detail-inline').getByText('内容解析', { exact: true })).toBeVisible()
  await expect(page.locator('.finder-detail-inline').getByText('可引用片段', { exact: true })).toHaveCount(0)
  await expect(page.locator('.finder-detail-inline').getByText('建议用途', { exact: true })).toHaveCount(0)
  const detailPanelStyle = await page.locator('.finder-detail-inline').evaluate(panel => ({
    border: getComputedStyle(panel).borderTopWidth,
    radius: getComputedStyle(panel).borderRadius,
    marginLeft: getComputedStyle(panel).marginLeft,
    background: getComputedStyle(panel).backgroundColor
  }))
  expect(detailPanelStyle).toMatchObject({ border: '1px', radius: '12px', marginLeft: '16px' })
  expect(detailPanelStyle.background).not.toBe('rgba(0, 0, 0, 0)')

  await firstFileRow.click()
  await expect(page.locator('.finder-detail-inline')).toHaveCount(0)
})

test('协作两页在窄屏下切换为单栏且不横向溢出', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })

  await page.goto('/project-team')
  await expect(page.getByRole('heading', { name: '任务管理', level: 1 })).toBeVisible()
  const taskMetrics = await page.locator('.focused-task-layout').evaluate(layout => ({
    columns: getComputedStyle(layout).gridTemplateColumns.split(' ').length,
    noOverflow: document.documentElement.scrollWidth <= window.innerWidth
  }))
  expect(taskMetrics.columns).toBe(1)
  expect(taskMetrics.noOverflow).toBe(true)

  await page.goto('/script-editor?tab=materials')
  await expect(page.getByRole('heading', { name: '资源中心', level: 1 })).toBeVisible()
  const fileMetrics = await page.locator('.finder-window').evaluate(windowEl => ({
    columns: getComputedStyle(windowEl).gridTemplateColumns.split(' ').length,
    noOverflow: document.documentElement.scrollWidth <= window.innerWidth
  }))
  expect(fileMetrics.columns).toBe(1)
  expect(fileMetrics.noOverflow).toBe(true)
})

test('任务详情默认折叠完整任务书并在点击后显示', async ({ page }) => {
  await page.unroute('**/api/project-teams/7/dashboard')
  await page.route('**/api/project-teams/7/dashboard', route => route.fulfill(ok({
    team: { id: 7, name: '应用攻坚队' },
    myRoleInTeam: 'CAPTAIN',
    currentUserId: 11,
    canManage: true,
    managementPermissions: { ASSIGN_TASK: true },
    metrics: { overallProgress: 35 },
    members: [],
    stages: [],
    tasks: [{
      id: 36,
      title: '确定项目问题与用户需求',
      description: '用真实访谈和场景证据，讲清楚服务对象、核心问题与项目边界。',
      taskType: 'TRAINING_DAY',
      stageKey: 'TRAINING',
      status: 'TODO',
      priority: 'MEDIUM',
      ownerUserId: 11,
      ownerName: '李林峰',
      dueAt: '2026-07-23T22:00:00'
    }],
    submissions: [],
    materials: [],
    reviewIssues: [],
    abilities: [],
    roadshowMeetings: []
  })))
  await page.goto('/project-team/details/task-36?teamId=7')

  await expect(page.getByRole('heading', { name: '任务详情', level: 1 })).toBeVisible()
  const toggle = page.getByRole('button', { name: /展开完整任务书/ })
  await expect(toggle).toBeVisible()
  await expect(toggle).toHaveAttribute('aria-expanded', 'false')
  await expect(page.getByText('正式任务描述', { exact: true })).toHaveCount(0)

  await toggle.click()
  await expect(page.getByRole('button', { name: /收起完整任务书/ })).toHaveAttribute('aria-expanded', 'true')
  await expect(page.getByText('正式任务描述', { exact: true })).toBeVisible()
  await expect(page.getByText('提交访谈记录', { exact: true })).toBeVisible()

  await page.getByRole('button', { name: /收起完整任务书/ }).click()
  await expect(page.getByText('正式任务描述', { exact: true })).toHaveCount(0)
})
