import { expect, test } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('orep_user_token', 'training-copy-token')
    localStorage.setItem('orep_user', JSON.stringify({ username: '李林峰', role: 'STUDENT' }))
  })

  await page.route('**/api/training-camps/current/today-overview', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      code: 200,
      data: {
        hasCamp: true,
        hasTrainingDay: true,
        dayId: 1,
        dayNo: 1,
        weekNo: 1,
        trainingDate: '2026-07-22',
        title: '确定项目问题与用户需求',
        summary: '用真实访谈和场景证据明确项目边界。',
        dueAt: '2026-07-22T22:00:00',
        contentHtml: '<p>通过三次真实访谈确认用户痛点，并形成项目边界结论。</p>',
        camp: {
          teamName: '应用攻坚队',
          campName: '应用攻坚队 · 21天集训',
          remainingDays: 20
        },
        currentWeek: { weekNo: 1, days: [] },
        tasks: [],
        primaryTask: {
          taskId: 1,
          description: '任务描述纯文本回退',
          requirements: [{
            id: 1,
            title: '需求说明',
            description: '说明目标用户、核心问题和边界',
            required: true
          }]
        },
        attachments: [{
          id: 1,
          fileName: '需求访谈记录模板.pdf',
          fileSize: 627712,
          fileUrl: '/fixtures/interview-template.pdf',
          mimeType: 'application/pdf'
        }],
        submission: {},
        feedback: {},
        recentFeedback: {}
      }
    })
  }))
})

test('今日训练页统一使用“训练”文案', async ({ page }) => {
  await page.goto('/training/today')

  await expect(page.locator('.workspace-module-nav__head p')).toHaveText('训练模式 · 任务驱动')
  await expect(page.locator('.workspace-module-nav__label').first()).toHaveText('今日训练')
  await expect(page.locator('.training-page-head h1')).toHaveText('今日训练')
  const taskBook = page.locator('.training-focus-card')
  const side = page.locator('.training-side')

  await expect(taskBook.getByRole('heading', { name: '任务书' })).toBeVisible()
  await expect(taskBook.getByText('任务概要', { exact: true })).toBeVisible()
  await expect(taskBook.getByText('正式任务描述', { exact: true })).toBeVisible()
  await expect(taskBook.getByText('用真实访谈和场景证据明确项目边界。')).toBeVisible()
  await expect(taskBook.getByText('通过三次真实访谈确认用户痛点，并形成项目边界结论。')).toBeVisible()
  await expect(taskBook.getByText('任务附件', { exact: true })).toHaveCount(0)
  await expect(taskBook.getByText('需求说明', { exact: true })).toBeVisible()
  await expect(page.getByTestId('training-progress-steps')).toHaveCount(0)

  await expect(side.locator('section.student-card')).toHaveCount(2)
  await expect(side.getByRole('heading', { name: '任务附件' })).toBeVisible()
  await expect(side.getByRole('heading', { name: '提交成果' })).toBeVisible()
  await expect(side.getByRole('link', { name: /去提交成果/ })).toHaveCount(1)
  await expect(side.locator('.training-week-card')).toHaveCount(0)
  await expect(side.getByRole('link', { name: '训练计划' })).toHaveCount(0)

  const attachmentRow = side.locator('.training-attachment-item').filter({ hasText: '需求访谈记录模板.pdf' })
  await expect(attachmentRow.getByRole('button', { name: '预览' })).toBeVisible()
  const downloadLink = attachmentRow.getByRole('link', { name: '下载' })
  await expect(downloadLink).toHaveAttribute('href', '/fixtures/interview-template.pdf')
  await expect(downloadLink).toHaveAttribute('download', '需求访谈记录模板.pdf')

  await expect(side.getByText('交付要求', { exact: true })).toHaveCount(0)
  await expect(side.getByText('查看完整任务说明', { exact: true })).toHaveCount(0)
  await expect(side.getByText('先看课程', { exact: true })).toHaveCount(0)
  await expect(side.getByRole('heading', { name: '老师反馈' })).toHaveCount(0)
  await expect(side.getByRole('heading', { name: '接下来可以做' })).toHaveCount(0)
  await expect(page.locator('.training-page-head p')).toHaveText('应用攻坚队 · 应用攻坚队 · 21天训练 · 训练第 1 天')
  await expect(page.locator('body')).not.toContainText('集训')

  await expect.poll(() => page.evaluate(() => {
    const style = getComputedStyle(document.querySelector('.training-side'))
    return { position: style.position, top: style.top }
  })).toEqual({ position: 'sticky', top: '0px' })

  await page.setViewportSize({ width: 900, height: 900 })
  await expect.poll(() => page.evaluate(() => document.body.scrollWidth <= document.body.clientWidth)).toBe(true)
  await expect.poll(() => page.evaluate(() => {
    const style = getComputedStyle(document.querySelector('.training-side'))
    return { position: style.position, top: style.top }
  })).toEqual({ position: 'static', top: 'auto' })
  await expect(side.locator('section.student-card')).toHaveCount(2)
})
