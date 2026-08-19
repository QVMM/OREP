import { expect, test } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('orep_user_token', 'meeting-alignment-token'))
  await page.route('**/api/**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 200, data: {} })
  }))
  await page.route('**/api/meeting/my-history', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 200, data: [] })
  }))
  await page.route('**/api/recording/my', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 200, data: [] })
  }))
})

test('路演号单列报错时加入字段仍保持顶部对齐', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/online-meeting')
  await page.getByPlaceholder('密码').fill('123456')
  await page.getByRole('button', { name: '进入路演' }).click()

  await expect(page.getByText('请输入路演号', { exact: true })).toBeVisible()

  const fields = page.locator('.fields')
  const codeField = fields.locator('.field').nth(0)
  const passwordField = fields.locator('.field').nth(1)
  const metrics = await fields.evaluate(container => {
    const rows = container.querySelectorAll('.field')
    const codeLabel = rows[0].querySelector('.el-form-item__label').getBoundingClientRect()
    const passwordLabel = rows[1].querySelector('.el-form-item__label').getBoundingClientRect()
    const codeInput = rows[0].querySelector('.el-input__wrapper').getBoundingClientRect()
    const passwordInput = rows[1].querySelector('.el-input__wrapper').getBoundingClientRect()
    const error = rows[0].querySelector('.el-form-item__error').getBoundingClientRect()
    return {
      labelDelta: Math.abs(codeLabel.top - passwordLabel.top),
      inputDelta: Math.abs(codeInput.top - passwordInput.top),
      errorBelowInput: error.top >= codeInput.bottom
    }
  })

  expect(metrics.labelDelta).toBeLessThanOrEqual(1)
  expect(metrics.inputDelta).toBeLessThanOrEqual(1)
  expect(metrics.errorBelowInput).toBe(true)
  await expect(codeField).toBeVisible()
  await expect(passwordField).toBeVisible()
})

test('路演训练和路演回放使用统一页头名称', async ({ page }) => {
  await page.goto('/online-meeting')
  await expect(page.getByRole('heading', { name: '路演训练', level: 1 })).toBeVisible()
  await expect(page.locator('.page-head .page-kicker')).toHaveCount(0)

  await page.goto('/my-recordings')
  await expect(page.getByRole('heading', { name: '路演回放', level: 1 })).toBeVisible()
  await expect(page.locator('.archive-page-head .page-kicker')).toHaveCount(0)
})

test('路演页面不再渲染二级菜单且其他模块菜单保持不变', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })

  await page.goto('/online-meeting')
  await expect(page.locator('.workspace-module-nav')).toHaveCount(0)
  await expect(page.locator('.workspace-app')).not.toHaveClass(/\bhas-module-nav\b/)

  await page.goto('/my-recordings')
  await expect(page.locator('.workspace-module-nav')).toHaveCount(0)
  await expect(page.locator('.workspace-app')).not.toHaveClass(/\bhas-module-nav\b/)

  await page.route('**/api/**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 200, data: {} })
  }))

  await page.goto('/statistics')
  await expect(page).toHaveURL('/online-meeting?tab=reports')
  await expect(page.locator('.workspace-module-nav')).toHaveCount(0)
  await expect(page.getByRole('tab', { name: '评分报告', exact: true })).toHaveAttribute('aria-selected', 'true')

  await page.goto('/project-team')
  await expect(page.getByRole('navigation', { name: '团队协作二级导航' })).toBeVisible()
})

test('路演训练与路演回放可通过页头操作双向切换', async ({ page }) => {
  await page.goto('/online-meeting')
  await page.getByRole('button', { name: '路演回放', exact: true }).click()
  await expect(page).toHaveURL('/my-recordings')

  const returnLink = page.getByRole('link', { name: '返回路演训练', exact: true })
  await expect(returnLink).toBeVisible()
  await returnLink.click()
  await expect(page).toHaveURL('/online-meeting')
})

test('路演回放页头操作在窄屏保持完整且不产生横向滚动', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/my-recordings')

  await expect(page.getByRole('link', { name: '返回路演训练', exact: true })).toBeVisible()
  await expect(page.getByRole('button', { name: '刷新', exact: true })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390)
})
