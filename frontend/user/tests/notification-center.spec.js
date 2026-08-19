import { expect, test } from '@playwright/test'

const homePayload = {
  profile: { username: '李林峰' },
  camp: { currentDay: 2, totalDays: 21, remainingDays: 19 },
  todayTraining: { hasTrainingDay: false },
  roadshow: { hasRoadshow: false },
  latestScore: { hasReport: false },
  nextActions: []
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('orep_user_token', 'notification-contract-token')
  })
  await page.route('**/api/student/home', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 200, data: homePayload })
  }))
  await page.route('**/api/notifications', route => {
    if (route.request().method() === 'PATCH') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 200, data: { unreadCount: 0, updatedCount: 1 } })
      })
    }
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 200,
        data: {
          unreadCount: 1,
          items: [{
            id: 9,
            title: '集训任务提醒',
            message: '请完成今日训练',
            deadline: '今晚 22:00',
            isRead: false,
            targetPath: '/training/today',
            createdAt: '2026-07-23T10:00:00'
          }]
        }
      })
    })
  })
})

test('通知角标表示未读数，点击通知标记已读并进入训练任务', async ({ page }) => {
  let markedRead = false
  await page.route('**/api/notifications/9/read', route => {
    markedRead = true
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: 200, data: { id: 9, isRead: true } })
    })
  })

  await page.goto('/')

  await expect(page.locator('.workspace-message-badge')).toHaveText('1')
  await page.getByRole('button', { name: '消息提醒' }).click()
  const notification = page.getByRole('button', { name: /集训任务提醒/ })
  await expect(notification).toBeVisible()
  await expect(notification).toHaveClass(/is-unread/)

  await notification.click()

  await expect.poll(() => markedRead).toBe(true)
  await expect(page).toHaveURL(/\/training\/today$/)
})

test('全部已读清空角标', async ({ page }) => {
  let markedAllRead = false
  await page.route('**/api/notifications/read-all', route => {
    markedAllRead = true
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: 200, data: { unreadCount: 0, updatedCount: 1 } })
    })
  })

  await page.goto('/')
  await page.getByRole('button', { name: '消息提醒' }).click()
  await page.getByRole('button', { name: '全部已读' }).click()

  await expect.poll(() => markedAllRead).toBe(true)
  await expect(page.locator('.workspace-message-badge')).toHaveCount(0)
})
