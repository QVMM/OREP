import { expect, test } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('orep_user_token', 'workspace-shell-stability-token')
  })

  await page.route('**/api/student/home', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      code: 200,
      data: {
        profile: { username: '李林峰' },
        camp: { currentDay: 2, totalDays: 21, remainingDays: 19 },
        todayTraining: { hasTrainingDay: false },
        roadshow: { hasRoadshow: false },
        latestScore: { hasReport: false },
        nextActions: []
      }
    })
  }))
  await page.route('**/api/notifications', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 200, data: { items: [], unreadCount: 0 } })
  }))
  await page.route('**/api/collaboration/summary', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      code: 200,
      data: {
        pendingInvitations: 0,
        unreadMessages: 0,
        activeSessions: 0,
        items: []
      }
    })
  }))
  await page.route('**/api/meeting/**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 200, data: [] })
  }))
})

test('从首页进入路演训练时工作区外壳不发生垂直位移', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 })
  await page.goto('/')

  const workspace = page.locator('.workspace-app')
  await expect(workspace).toHaveCSS('transform', 'none')
  const before = await workspace.boundingBox()

  await page.getByRole('link', { name: '路演训练', exact: true }).click()
  await expect(page).toHaveURL(/\/online-meeting$/)

  const after = await workspace.boundingBox()
  await expect(workspace).toHaveCSS('transform', 'none')
  expect(Math.abs(after.y - before.y)).toBeLessThan(0.1)
})
