import { test, expect } from '@playwright/test'

const basePath = '/prototypes/orep-unified-workspace/'

async function resetDemo(page) {
  await page.goto(`${basePath}#/home`)
  await page.evaluate(() => localStorage.removeItem('orep-v2-state'))
  await page.reload()
  await expect(page.locator('#main-content h1')).toBeVisible()
}

test.describe('OREP V2 product prototype', () => {
  test.beforeEach(async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' })
    await resetDemo(page)
  })

  test('core routes share one shell and render without runtime failures', async ({ page }) => {
    const errors = []
    page.on('pageerror', (error) => errors.push(error.message))
    page.on('console', (message) => {
      if (message.type() === 'error') errors.push(message.text())
    })

    const routes = [
      ['home', '今天，陈默'],
      ['tasks/task-cost-evidence', '任务工作台'],
      ['review', '提交审核'],
      ['learning', '学习中心'],
      ['roadshow', '路演中心'],
      ['score', '先解决问题，再看分数'],
      ['teacher', '教师工作台']
    ]

    for (const [route, title] of routes) {
      await page.goto(`${basePath}#/${route}`)
      await expect(page.locator('#main-content h1')).toHaveText(title)
      await expect(page.locator('.rail-nav__item')).toHaveCount(5)
      await expect(page.locator('.v2-island')).toBeVisible()
      await expect(page.locator('.island-action.is-primary')).toHaveCount(1)

      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
      expect(overflow, `${route} should not overflow horizontally`).toBeLessThanOrEqual(1)
    }

    expect(errors).toEqual([])
  })

  test('student submission, teacher return, resubmission, and approval stay synchronized', async ({ page }) => {
    await page.goto(`${basePath}#/tasks/task-cost-evidence`)
    await page.locator('.v2-island [data-action="open-submit"]').click()
    await page.locator('[name="submission-content"]').fill('已补齐三组试点样本、统计周期、人工成本口径和数据来源。')
    await page.locator('[name="submission-evidence"]').fill('南沙试点原始记录.xlsx\n成本收益敏感性分析.pdf')
    await page.locator('[data-action="submit-task"]').click()

    let sharedState = await page.evaluate(() => window.OREPV2App.getState())
    expect(sharedState.tasks.find((item) => item.id === 'task-cost-evidence').status).toBe('PENDING_REVIEW')
    expect(sharedState.teacherQueue.some((item) => item.taskId === 'task-cost-evidence' && item.status === 'PENDING_REVIEW')).toBeTruthy()

    await page.locator('[data-action="set-role"][data-role="teacher"]').click()
    await page.goto(`${basePath}#/review`)
    await page.locator('.v2-review-row').filter({ hasText: '补强成本收益证据' }).click()
    await expect(page).toHaveURL(/#\/review\/queue-/)
    await page.locator('#v2-return-reason').fill('请在敏感性分析中补充设备寿命为 3 年和 5 年的两组结果，并标注数据页码。')
    await page.locator('.v2-island [data-action="request-review-changes"]').click()

    sharedState = await page.evaluate(() => window.OREPV2App.getState())
    expect(sharedState.tasks.find((item) => item.id === 'task-cost-evidence').status).toBe('CHANGES_REQUESTED')

    await page.locator('[data-action="set-role"][data-role="student"]').click()
    await page.goto(`${basePath}#/tasks/task-cost-evidence`)
    await page.locator('.v2-island [data-action="open-submit"]').click()
    await page.locator('[name="submission-content"]').fill('已增加 3 年与 5 年设备寿命敏感性分析，并标注原始数据页码。')
    await page.locator('[name="submission-evidence"]').fill('成本收益敏感性分析_v2.pdf')
    await page.locator('[data-action="submit-task"]').click()

    await page.locator('[data-action="set-role"][data-role="teacher"]').click()
    await page.goto(`${basePath}#/review`)
    await page.locator('.v2-review-row').filter({ hasText: '补强成本收益证据' }).click()
    await expect(page).toHaveURL(/#\/review\/queue-/)
    await page.locator('.v2-island [data-action="approve-next-review"]').click()

    sharedState = await page.evaluate(() => window.OREPV2App.getState())
    expect(sharedState.tasks.find((item) => item.id === 'task-cost-evidence').status).toBe('DONE')
    expect(sharedState.teacherQueue.find((item) => item.taskId === 'task-cost-evidence').status).toBe('APPROVED')
  })

  test('score remediation and learning actions update the shared product state', async ({ page }) => {
    await page.goto(`${basePath}#/score`)
    await page.locator('.v2-issue-row').filter({ hasText: '成本模型缺少可核验依据' }).click()
    await page.locator('.v2-island [data-action="create-remediation"]').click()

    let sharedState = await page.evaluate(() => window.OREPV2App.getState())
    const scoreIssue = sharedState.score.issues.find((item) => item.id === 'issue-cost-model')
    expect(scoreIssue.remediationTaskId).toBeTruthy()
    expect(sharedState.tasks.some((item) => item.id === scoreIssue.remediationTaskId)).toBeTruthy()

    await page.goto(`${basePath}#/tasks/${scoreIssue.remediationTaskId}`)
    await expect(page.locator('#v2-active-task-title')).toContainText('整改：成本模型缺少可核验依据')

    await page.goto(`${basePath}#/learning`)
    const before = await page.evaluate(() => window.OREPV2App.getState().learning.items.find((item) => item.id === 'learning-unit-economics').progress)
    await page.locator('.v2-island [data-action="resume-learning"]').click()
    sharedState = await page.evaluate(() => window.OREPV2App.getState())
    expect(sharedState.learning.items.find((item) => item.id === 'learning-unit-economics').progress).toBeGreaterThan(before)
  })

  test('desktop and mobile visual captures keep the primary task in view', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 900 })
    await page.goto(`${basePath}#/home`)
    await expect(page.locator('.v2-focus-card')).toBeInViewport()
    await expect(page.locator('.v2-today-list')).toBeInViewport()
    await page.screenshot({ path: 'test-results/orep-v2-home.png', fullPage: true })

    await page.goto(`${basePath}#/tasks/task-cost-evidence`)
    await page.screenshot({ path: 'test-results/orep-v2-tasks.png', fullPage: true })

    await page.goto(`${basePath}#/learning`)
    await page.screenshot({ path: 'test-results/orep-v2-learning.png', fullPage: true })

    await page.goto(`${basePath}#/roadshow`)
    await page.screenshot({ path: 'test-results/orep-v2-roadshow.png', fullPage: true })

    await page.goto(`${basePath}#/score`)
    await page.screenshot({ path: 'test-results/orep-v2-score.png', fullPage: true })

    await page.locator('[data-action="set-role"][data-role="teacher"]').click()
    await page.goto(`${basePath}#/review`)
    await page.screenshot({ path: 'test-results/orep-v2-review.png', fullPage: true })

    await page.goto(`${basePath}#/teacher`)
    await page.screenshot({ path: 'test-results/orep-v2-teacher.png', fullPage: true })

    await page.setViewportSize({ width: 390, height: 844 })
    await page.locator('[data-action="set-role"][data-role="student"]').click()
    await page.goto(`${basePath}#/home`)
    await expect(page.locator('.v2-rail')).toBeVisible()
    await expect(page.locator('.v2-island')).toBeVisible()
    const mobileGeometry = await page.evaluate(() => {
      const nav = document.querySelector('.v2-rail').getBoundingClientRect()
      const island = document.querySelector('.v2-island').getBoundingClientRect()
      return {
        gap: nav.top - island.bottom,
        overflow: document.documentElement.scrollWidth - window.innerWidth
      }
    })
    expect(mobileGeometry.gap).toBeGreaterThanOrEqual(6)
    expect(mobileGeometry.overflow).toBeLessThanOrEqual(1)
    await page.screenshot({ path: 'test-results/orep-v2-home-mobile.png', fullPage: true })
  })
})
