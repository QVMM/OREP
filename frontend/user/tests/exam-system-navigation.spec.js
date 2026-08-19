import { expect, test } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('orep_user_token', 'exam-navigation-token')
    localStorage.setItem('orep_user', JSON.stringify({ username: '李林峰', role: 'STUDENT' }))
  })
  await page.route('**/api/training-camps/current/plan', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 200, data: { hasCamp: false, weeks: [] } })
  }))
})

test('已停用的考试地址统一返回训练任务', async ({ page }) => {
  for (const path of [
    '/exam-system',
    '/exam-system/wrong-book',
    '/exam-system/favorites',
    '/exam-system/practice/wrong',
    '/exam-system/take/7'
  ]) {
    await page.goto(path)
    await expect(page).toHaveURL(/\/training\/today$/)
  }

  await expect(page.locator('.workspace-module-nav__label', { hasText: '练习考试' })).toHaveCount(0)
})
