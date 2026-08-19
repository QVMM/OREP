import { expect, test } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('orep_user_token', 'exam-topbar-token')
    localStorage.setItem('orep_user', JSON.stringify({ username: '李林峰', role: 'STUDENT' }))
  })
  await page.route('**/api/training-camps/current/plan', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 200, data: { hasCamp: false, weeks: [] } })
  }))
})

test('历史答题链接不再渲染考试界面', async ({ page }) => {
  await page.setViewportSize({ width: 1284, height: 892 })
  await page.goto('/exam-system/take/7')

  await expect(page).toHaveURL(/\/training\/today$/)
  await expect(page.locator('.exam-topbar')).toHaveCount(0)
  await expect(page.getByRole('heading', { name: '训练任务', exact: true })).toBeVisible()
})
