import { expect, test } from '@playwright/test'

const ok = data => ({
  status: 200,
  contentType: 'application/json',
  body: JSON.stringify({ code: 200, data }),
})

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    const user = { id: 21, username: '李林峰', role: 'STUDENT' }
    const token = 'e30.eyJzdWIiOjIxLCJleHAiOjk5OTk5OTk5OTl9.x'
    localStorage.setItem('orep_user_token', token)
    localStorage.setItem('orep_user', JSON.stringify(user))
    localStorage.setItem('token', token)
    localStorage.setItem('user', JSON.stringify(user))
  })

  await page.route('**/api/**', route => route.fulfill(ok({})))
  await page.route('**/api/notifications', route => route.fulfill(ok({ items: [], unreadCount: 0 })))
  await page.route('**/api/collaboration/summary', route => route.fulfill(ok({
    actionRequired: 3,
    inProgress: 1,
    createdByMe: 0,
    completed: 0,
    total: 1,
  })))
  await page.route('**/api/collaboration/items**', route => route.fulfill(ok({
    items: [{
      key: 'REQUEST:42',
      entityType: 'REQUEST',
      id: 42,
      teamId: 8,
      teamName: '应用攻坚队',
      requesterId: 22,
      requesterName: '王同学',
      recipientId: 21,
      recipientName: '李林峰',
      title: '完善路演稿第 3 部分',
      description: '补齐市场数据和演示说明。',
      priority: 'HIGH',
      status: 'PENDING',
      statusLabel: '待接受',
      sourceType: 'PEER_COLLABORATION',
      sourceLabel: '学生协作',
      dueAt: '2026-08-02T20:00:00',
      actionRequired: true,
      canAccept: true,
      canDecline: true,
      canWithdraw: false,
      recipientIsCurrentUser: true,
    }, {
      key: 'TASK:88',
      entityType: 'TASK',
      id: 88,
      linkedTaskId: 88,
      teamId: 8,
      teamName: '应用攻坚队',
      title: '完整路演第一次彩排',
      sourceType: 'TRAINING_DAY',
      sourceLabel: '今日训练',
      status: 'TODO',
      statusLabel: '待开始',
      creatorName: '训练营',
      dueAt: '2026-07-30T22:00:00',
      actionRequired: true,
      primaryAction: 'SUBMIT',
      targetPath: '/training/tasks/88?dayId=8',
    }, {
      key: 'TASK:89',
      entityType: 'TASK',
      id: 89,
      linkedTaskId: 89,
      teamId: 8,
      teamName: '应用攻坚队',
      title: '补齐市场数据与来源说明',
      sourceType: 'TEACHER_ASSIGNMENT',
      sourceLabel: '老师任务',
      status: 'TODO',
      statusLabel: '待开始',
      creatorName: '张老师',
      dueAt: '2026-08-03T20:00:00',
      actionRequired: true,
      primaryAction: 'SUBMIT',
      targetPath: '/project-team/details/task-89',
    }],
    hasMore: false,
  })))
  await page.route('**/api/project-teams/my', route => route.fulfill(ok([
    { id: 8, name: '应用攻坚队' },
  ])))
  await page.route('**/api/project-teams/8/dashboard', route => route.fulfill(ok({
    members: [
      { userId: 21, username: '李林峰', positionName: '产品经理' },
      { userId: 22, username: '王同学', positionName: '视觉设计' },
      { userId: 23, username: '陈同学', positionName: '前端开发' },
      { userId: 24, username: '赵同学', positionName: '市场调研' },
    ],
  })))
})

test('桌面协作入口打开全局工作台并能接受同学任务', async ({ page }) => {
  let accepted = false
  await page.route('**/api/collaboration/requests/42/accept', route => {
    accepted = true
    return route.fulfill(ok({
      id: 42,
      teamId: 8,
      title: '完善路演稿第 3 部分',
      status: 'ACCEPTED',
      linkedTaskId: 55,
    }))
  })

  await page.setViewportSize({ width: 1280, height: 900 })
  await page.goto('/training/today')

  const entry = page.locator('.workspace-collaboration-entry').getByRole('button')
  await expect(entry).toHaveAccessibleName(/协作/)
  await entry.click()

  const panel = page.getByRole('dialog', { name: '协作工作台' })
  await expect(panel).toBeVisible()
  await expect(panel).toHaveCSS('width', '448px')
  await expect(panel.getByText('完善路演稿第 3 部分', { exact: true })).toBeVisible()
  await panel.getByRole('button', { name: '接受', exact: true }).click()
  expect(accepted).toBe(true)
})

test('发起协作支持搜索并邀请多名团队成员', async ({ page }) => {
  let payload = null
  let idempotencyKey = null
  await page.route('**/api/collaboration/requests/batch', async route => {
    payload = route.request().postDataJSON()
    idempotencyKey = route.request().headers()['idempotency-key']
    return route.fulfill(ok({
      count: 2,
      items: payload.recipientUserIds.map((recipientId, index) => ({
        id: 66 + index,
        teamId: 8,
        requesterId: 21,
        recipientId,
        title: payload.title,
        status: 'PENDING',
      })),
    }))
  })

  await page.setViewportSize({ width: 1280, height: 900 })
  await page.goto('/training/today')
  await page.locator('.workspace-collaboration-entry').getByRole('button').click()
  const panel = page.getByRole('dialog', { name: '协作工作台' })
  await panel.getByRole('button', { name: '发起', exact: true }).click()
  const form = page.getByRole('dialog', { name: '发起协作' })

  await form.getByLabel('项目团队 *').selectOption('8')
  await form.getByRole('combobox', { name: '协作成员 *' }).click()
  await form.getByRole('option', { name: /王同学/ }).click()
  await form.getByLabel('搜索团队成员').fill('前端')
  await form.getByRole('option', { name: /陈同学/ }).click()
  await form.getByLabel('任务标题 *').fill('核对答辩数据')
  await form.getByLabel('任务说明').fill('请核对第三页的市场规模数据来源。')
  await form.getByRole('button', { name: '向 2 人发送协作申请' }).click()

  expect(payload).toMatchObject({
    teamId: 8,
    recipientUserIds: [22, 23],
    title: '核对答辩数据',
  })
  expect(idempotencyKey).toBeTruthy()
  await expect(form.getByText('已向 2 人发送协作申请')).toBeVisible()
})

test('批量发送失败后保留成员和任务草稿', async ({ page }) => {
  await page.route('**/api/collaboration/requests/batch', route => route.fulfill({
    status: 500,
    contentType: 'application/json',
    body: JSON.stringify({ message: '服务暂时不可用' }),
  }))

  await page.setViewportSize({ width: 1280, height: 900 })
  await page.goto('/training/today')
  await page.locator('.workspace-collaboration-entry').getByRole('button').click()
  const panel = page.getByRole('dialog', { name: '协作工作台' })
  await panel.getByRole('button', { name: '发起', exact: true }).click()
  const form = page.getByRole('dialog', { name: '发起协作' })

  await form.getByLabel('项目团队 *').selectOption('8')
  await form.getByRole('combobox', { name: '协作成员 *' }).click()
  await form.getByRole('option', { name: /王同学/ }).click()
  await form.getByLabel('任务标题 *').fill('保留这份草稿')
  await form.getByRole('button', { name: '发送协作申请' }).click()

  await expect(form.getByRole('alert')).toContainText('服务暂时不可用')
  await expect(form.getByLabel('任务标题 *')).toHaveValue('保留这份草稿')
  await expect(form.getByRole('combobox', { name: '协作成员 *' })).toContainText('王同学')
})

test('协作工作台统一展示训练任务和老师任务并进入真实任务路由', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 })
  await page.goto('/training/today')
  await page.locator('.workspace-collaboration-entry').getByRole('button').click()

  const panel = page.getByRole('dialog', { name: '协作工作台' })
  await expect(panel.getByText('今日训练', { exact: true })).toBeVisible()
  await expect(panel.getByText('老师任务', { exact: true })).toBeVisible()
  await panel.getByRole('button', { name: /今日训练：完整路演第一次彩排/ }).click()

  await expect(page).toHaveURL(/\/training\/tasks\/88\?dayId=8/)
})

test('三百九十像素下协作工作台无横向滚动', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/training/today')

  await page.getByRole('navigation', { name: '移动端主导航' })
    .getByRole('button', { name: /协作/ })
    .click()

  const panel = page.getByRole('dialog', { name: '协作工作台' })
  await expect(panel).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true)
})
