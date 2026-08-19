import { expect, test } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('orep_user_token', 'course-redirect-token'))
  await page.route('**/api/training-camps/current/plan', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 200, data: { hasCamp: false, message: '暂无训练营' } })
  }))
})

test('独立课程学习入口已合并到训练任务', async ({ page }) => {
  await page.goto('/course-learning/12/lesson/3')

  await expect(page).toHaveURL(/\/training\/today$/)
  await expect(page.getByRole('heading', { name: '训练任务', exact: true })).toBeVisible()
  await expect(page.locator('.workspace-module-nav__label', { hasText: '课程学习' })).toHaveCount(0)
})
