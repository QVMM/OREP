import { expect, test } from '@playwright/test'

const studentPages = [
  'collab.html',
  'course-player.html',
  'exam-take.html',
  'files.html',
  'index.html',
  'invite.html',
  'map.html',
  'meeting-history.html',
  'meeting-room.html',
  'ppt-workbench.html',
  'profile.html',
  'review-report.html',
  'review.html',
  'roadshow-meeting.html',
  'roadshow-ppt.html',
  'roadshow-script.html',
  'roadshow.html',
  'score-upload.html',
  'script-editor.html',
  'task-detail.html',
  'tasks.html',
  'topic.html',
  'training-course.html',
  'training-day.html',
  'training-exam.html',
  'training.html',
]

test('学生首页采用分层白玻璃并保留橙色品牌锚点', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/user/index.html')

  const themeLink = page.locator('link[href="css/student-glass.css"]')
  await expect(themeLink).toHaveCount(1)
  await expect(page.locator('body')).toHaveAttribute('data-portal', 'student')
  await expect(page.locator('.hd-card').first()).toBeVisible()

  const material = await page.evaluate(() => {
    const card = getComputedStyle(document.querySelector('.hd-card'))
    const shell = getComputedStyle(document.querySelector('.workspace-topbar'))
    const logo = getComputedStyle(document.querySelector('.arch-rail__brand'))
    const primary = getComputedStyle(document.querySelector('.hd-btn-primary'))
    return {
      cardBackgroundColor: card.backgroundColor,
      cardBackground: card.backgroundImage,
      cardFilter: card.backdropFilter || card.webkitBackdropFilter,
      cardShadow: card.boxShadow,
      cardBorder: card.border,
      cardRadius: card.borderRadius,
      shellBackgroundColor: shell.backgroundColor,
      shellBackground: shell.backgroundImage,
      shellFilter: shell.backdropFilter || shell.webkitBackdropFilter,
      shellShadow: shell.boxShadow,
      logoBackgroundColor: logo.backgroundColor,
      logoBackground: logo.backgroundImage,
      logoShadow: logo.boxShadow,
      primaryBackgroundColor: primary.backgroundColor,
      primaryBackground: primary.backgroundImage,
      primaryShadow: primary.boxShadow,
    }
  })

  expect(material.cardBackground).toBe('none')
  expect(material.cardBackgroundColor).toBe('rgb(255, 255, 255)')
  expect(material.cardFilter).toBe('none')
  expect(material.cardShadow).toBe('rgba(0, 0, 0, 0.08) 2px 4px 12px 0px')
  expect(material.cardBorder).toContain('0px')
  expect(material.cardRadius).toBe('18px')
  expect(material.shellBackgroundColor).toBe('rgba(255, 255, 255, 0.8)')
  expect(material.shellBackground).toBe('none')
  expect(material.shellFilter).toBe('saturate(1.8) blur(20px)')
  expect(material.shellShadow).toBe('none')
  expect(material.logoBackgroundColor).toBe('rgb(232, 74, 28)')
  expect(material.logoBackground).toBe('none')
  expect(material.logoShadow).toBe('none')
  expect(material.primaryBackgroundColor).toBe('rgb(196, 58, 18)')
  expect(material.primaryBackground).toBe('none')
  expect(material.primaryShadow).toBe('none')

  await page.waitForTimeout(900)
  await page.screenshot({
    path: testInfo.outputPath('student-home-white-glass.png'),
    fullPage: true,
  })
})

for (const viewport of [
  { width: 1440, height: 900 },
  { width: 1280, height: 800 },
  { width: 1024, height: 768 },
  { width: 979, height: 1004 },
  { width: 375, height: 812 },
]) {
  test(`学生端 26 页在 ${viewport.width}px 下主题完整且无页面级横向溢出`, async ({ page }) => {
    await page.setViewportSize(viewport)
    const pageErrors = []
    page.on('pageerror', (error) => pageErrors.push(error.message))

    for (const path of studentPages) {
      await page.goto(`/user/${path}`)
      await expect(page.locator('body')).toHaveAttribute('data-portal', 'student')
      await expect(page.locator('link[href="css/student-glass.css"]')).toHaveCount(1)
      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - window.innerWidth,
      )
      expect(overflow, `${path} should not overflow at ${viewport.width}px`).toBeLessThanOrEqual(1)
    }

    expect(pageErrors).toEqual([])
  })
}

test('登录、教师端和管理员端不加载学生毛玻璃主题', async ({ page }) => {
  for (const path of [
    '/user/login.html',
    '/teacher/index.html',
    '/admin/index.html',
  ]) {
    await page.goto(path)
    await expect(page.locator('link[href*="student-glass.css"]')).toHaveCount(0)
  }
})

test('979px 预览宽度保持侧栏和正文同屏', async ({ page }) => {
  await page.setViewportSize({ width: 979, height: 1004 })
  await page.goto('/user/index.html')
  await page.waitForTimeout(900)

  const geometry = await page.evaluate(() => {
    const rect = (selector) => document.querySelector(selector).getBoundingClientRect()
    const app = getComputedStyle(document.querySelector('.workspace-app'))
    return {
      appDisplay: app.display,
      rail: rect('.arch-rail').toJSON(),
      main: rect('.workspace-main').toJSON(),
      card: rect('.hd-card').toJSON(),
    }
  })

  expect(geometry.appDisplay).toBe('grid')
  expect(geometry.rail.width).toBeLessThanOrEqual(72.5)
  expect(geometry.main.x).toBeGreaterThanOrEqual(71)
  expect(geometry.main.y).toBeLessThan(70)
  expect(geometry.card.y).toBeLessThan(260)
})

test('路演室保持深色舞台，仅控制层使用玻璃材质', async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/user/meeting-room.html')

  const material = await page.evaluate(() => {
    const stage = getComputedStyle(document.querySelector('.mr'))
    const top = getComputedStyle(document.querySelector('.mr-top'))
    const button = getComputedStyle(document.querySelector('.mr-btn'))
    return {
      stageBackground: stage.backgroundColor,
      topFilter: top.backdropFilter || top.webkitBackdropFilter,
      buttonBackground: button.backgroundColor,
      buttonBackgroundImage: button.backgroundImage,
      buttonBorderWidth: button.borderTopWidth,
      buttonShadow: button.boxShadow,
      buttonFilter: button.backdropFilter || button.webkitBackdropFilter,
    }
  })

  expect(material.stageBackground).toBe('rgb(18, 20, 26)')
  expect(material.topFilter).toContain('saturate(1.8) blur(20px)')
  expect(material.buttonBackground).toBe('rgba(210, 210, 215, 0.18)')
  expect(material.buttonBackgroundImage).toBe('none')
  expect(material.buttonBorderWidth).toBe('0px')
  expect(material.buttonShadow).toBe('none')
  expect(material.buttonFilter).toContain('saturate(1.8) blur(20px)')
  await page.screenshot({
    path: testInfo.outputPath('student-roadshow-room-glass-controls.png'),
    fullPage: true,
  })
})
