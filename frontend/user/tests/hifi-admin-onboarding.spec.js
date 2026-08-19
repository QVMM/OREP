import { expect, test } from '@playwright/test'

function captureRuntimeErrors(page) {
  const pageErrors = []
  const consoleErrors = []
  page.on('pageerror', (error) => pageErrors.push(error.message))
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text())
  })
  return { pageErrors, consoleErrors }
}

async function resetAdminState(page) {
  await page.goto('/admin/index.html')
  await page.evaluate(() => {
    window.OREPAdminState.reset()
    localStorage.removeItem('orep-hifi-admin-wizard-draft:v1')
  })
  await page.reload()
}

async function fillSchoolWizard(page) {
  const school = {
    schoolName: '江城数字职业学院',
    shortName: '江城数职',
    code: 'JIANGCHENG-DIGITAL',
    region: '湖北 · 武汉',
    contactName: '吴晴',
    contactPhone: '13800003001',
  }
  for (const [name, value] of Object.entries(school)) {
    await page.locator(`[name="${name}"]`).fill(value)
  }
  await page.locator('[data-wizard-next]:visible').click()

  const admin = {
    adminName: '吴校管',
    adminPhone: '13800003002',
    adminEmail: 'wu@jiangcheng.edu.cn',
  }
  for (const [name, value] of Object.entries(admin)) {
    await page.locator(`[name="${name}"]`).fill(value)
  }
  await page.locator('[data-wizard-next]:visible').click()
  await expect(page.locator('[data-summary="schoolName"]')).toHaveText(school.schoolName)
  await expect(page.locator('[data-summary="adminName"]')).toHaveText(admin.adminName)
}

test.beforeEach(async ({ page }) => {
  await resetAdminState(page)
})

test.afterEach(async ({ page }) => {
  await page.goto('/admin/index.html')
  await page.evaluate(() => window.OREPAdminState.reset())
})

test('管理员总览以开通队列为主任务并使用共享状态', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)
  await page.goto('/admin/index.html')

  await expect(page).toHaveTitle('平台总览 · 管理员端')
  await expect(page.locator('.arch-rail__item.is-active')).toHaveAttribute('aria-current', 'page')
  await expect(page.locator('.module-list__item.is-active')).toHaveAttribute('aria-current', 'page')
  await expect(page.getByRole('searchbox', { name: '搜索学校、用户、操作记录' })).toBeVisible()
  await expect(page.getByRole('link', { name: /开通新学校/ })).toHaveCount(1)
  await expect(page.locator('[data-admin-metric="tenants"]')).toHaveText('3')
  await expect(page.locator('[data-admin-metric="configuring"]')).toHaveText('1')
  await expect(page.locator('[data-admin-onboarding-queue]')).toContainText('未来工程职业学院')
  await expect(page.locator('[data-admin-onboarding-queue]')).toContainText('17%')
  expect(runtimeErrors).toEqual({ pageErrors: [], consoleErrors: [] })
})

test('创建学校向导提供字段校验、草稿恢复和确认摘要', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)
  await page.goto('/admin/create-tenant.html')

  await page.locator('[data-wizard-next]:visible').click()
  await expect(page.locator('[data-error-for="schoolName"]')).toHaveText('请填写学校名称')
  await expect(page.locator('[name="schoolName"]')).toBeFocused()

  await page.locator('[name="schoolName"]').fill('江城数字职业学院')
  await page.locator('[name="code"]').fill('jiangcheng-digital')
  await page.reload()
  await expect(page.locator('[name="schoolName"]')).toHaveValue('江城数字职业学院')
  await expect(page.locator('[name="code"]')).toHaveValue('JIANGCHENG-DIGITAL')

  await fillSchoolWizard(page)
  await expect(page.locator('[data-wizard-panel="3"]')).toBeVisible()
  await expect(page.locator('[data-summary="schoolName"]')).toHaveText('江城数字职业学院')
  await expect(page.locator('[data-summary="code"]')).toHaveText('JIANGCHENG-DIGITAL')
  await expect(page.locator('[data-summary="adminEmail"]')).toHaveText('wu@jiangcheng.edu.cn')
  expect(runtimeErrors).toEqual({ pageErrors: [], consoleErrors: [] })
})

test('平台管理员完成学校开通、权限阻塞修复和跨页面审计闭环', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)
  await page.goto('/admin/create-tenant.html')
  await fillSchoolWizard(page)
  await page.locator('[data-wizard-submit]').click()
  await page.waitForURL('**/admin/tenant-workbench.html?tenant=*')

  const tenantId = new URL(page.url()).searchParams.get('tenant')
  expect(tenantId).toBeTruthy()
  await expect(page.locator('[data-workbench-title]')).toHaveText('江城数字职业学院')
  await expect(page.locator('[data-workbench-status]')).toHaveText('草稿')

  await page.getByRole('button', { name: '建立组织' }).click()
  await expect(page.locator('#orgDialog')).toBeVisible()
  await page.locator('#orgForm').getByRole('button', { name: '添加组织' }).click()
  await expect(page.locator('#organization')).toContainText('智能制造学院')

  await page.getByRole('button', { name: '演示导入' }).click()
  await expect(page.locator('#users')).toContainText('2 条成功，1 条重复手机号')
  await page.getByRole('button', { name: '确认配置' }).click()
  await page.getByRole('button', { name: '执行检查' }).click()

  await expect(page.locator('[data-workbench-status]')).toHaveText('待检查')
  await expect(page.locator('.acore-check.is-blocker')).toHaveCount(1)
  await expect(page.locator('.acore-check.is-blocker')).toContainText('角色均设置数据范围')
  await expect(page.locator('[data-open-activate]')).toBeDisabled()

  await page.locator('#permissions').getByRole('button', { name: '配置权限' }).click()
  const teacherRow = page.locator('[data-permission-user]').filter({ hasText: '陈敏' })
  await expect(teacherRow.locator('[data-scope]')).toHaveValue('')
  await teacherRow.locator('[data-scope]').selectOption('ORG')
  await page.locator('#permissionForm').getByRole('button', { name: '保存权限配置' }).click()

  await page.getByRole('button', { name: '执行检查' }).click()
  await expect(page.locator('[data-workbench-status]')).toHaveText('可启用')
  await expect(page.locator('.acore-check.is-blocker')).toHaveCount(0)
  await expect(page.locator('.acore-check.is-warning')).toContainText('学校品牌资料可在启用后补充')
  await expect(page.locator('[data-open-activate]')).toBeEnabled()

  await page.locator('[data-open-activate]').click()
  await page.locator('#activateForm').getByRole('button', { name: '确认正式启用' }).click()
  await expect(page.locator('[data-activate-error]')).toHaveText('请填写启用原因。')
  await page.locator('[name="reason"]').fill('完成校方验收，正式移交使用')
  await page.locator('#activateForm').getByRole('button', { name: '确认正式启用' }).click()
  await expect(page.locator('[data-workbench-status]')).toHaveText('已启用')
  await expect(page.locator('[data-open-activate]')).toBeDisabled()

  await page.goto('/admin/index.html')
  await expect(page.locator('[data-admin-metric="tenants"]')).toHaveText('4')
  await expect(page.locator('[data-admin-onboarding-queue]')).not.toContainText('江城数字职业学院')

  await page.goto('/admin/tenants.html')
  const tenantRow = page.locator('tbody tr').filter({ hasText: '江城数字职业学院' })
  await expect(tenantRow).toContainText('已启用')
  await expect(tenantRow).toContainText('100%')
  await expect(tenantRow).toContainText('吴校管')

  await page.goto(`/admin/users.html?tenant=${encodeURIComponent(tenantId)}`)
  await expect(page.locator('[data-user-table-body] tr')).toHaveCount(3)
  await expect(page.locator('[data-user-table-body]')).toContainText('陈敏')
  await expect(page.locator('[data-user-table-body]')).toContainText('指定组织')
  await expect(page.locator('[data-user-table-body]')).not.toContainText('待启用')

  await page.goto('/admin/system.html')
  await page.locator('[data-audit-tenant-filter]').selectOption(tenantId)
  await expect(page.locator('[data-audit-table-body]')).toContainText('正式启用学校')
  await expect(page.locator('[data-audit-table-body]')).toContainText('完成校方验收，正式移交使用')
  await expect(page.locator('[data-audit-table-body]')).toContainText('学校及 3 位首批用户')
  expect(runtimeErrors).toEqual({ pageErrors: [], consoleErrors: [] })
})

test('租户和用户筛选支持无结果状态，重置需要二次确认', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)
  await page.goto('/admin/tenants.html')
  await page.locator('[data-tenant-search]').fill('不存在的学校')
  await expect(page.locator('[data-tenant-table-body]')).toContainText('没有匹配的学校')
  await page.locator('[data-tenant-search]').fill('')
  await page.locator('[data-tenant-status]').selectOption('CONFIGURING')
  await expect(page.locator('[data-tenant-table-body] tr')).toHaveCount(1)
  await expect(page.locator('[data-tenant-table-body]')).toContainText('未来工程职业学院')

  await page.goto('/admin/users.html?status=PENDING')
  await expect(page.locator('[data-user-status-filter]')).toHaveValue('PENDING')
  await expect(page.locator('[data-user-table-body]')).toContainText('赵校管')
  await page.locator('[data-user-search]').fill('不存在')
  await expect(page.locator('[data-user-table-body]')).toContainText('没有匹配的用户')

  await page.locator('[data-admin-reset]').first().click()
  await expect(page.locator('#adminResetDialog')).toBeVisible()
  await page.locator('#adminResetDialog').getByRole('button', { name: '取消' }).click()
  await expect(page.locator('#adminResetDialog')).toBeHidden()
  await page.locator('[data-admin-reset]').first().click()
  await page.locator('#adminResetDialog').getByRole('button', { name: '确认重置' }).click()
  await expect(page.locator('#adminResetDialog')).toBeHidden()
  expect(runtimeErrors).toEqual({ pageErrors: [], consoleErrors: [] })
})

for (const viewport of [
  { width: 1440, height: 900 },
  { width: 1280, height: 800 },
  { width: 1024, height: 768 },
]) {
  test(`管理员八页在 ${viewport.width}px 下无页面级横向溢出`, async ({ page }) => {
    await page.setViewportSize(viewport)
    const runtimeErrors = captureRuntimeErrors(page)
    const paths = [
      'index.html',
      'tenants.html',
      'users.html',
      'content.html',
      'ops.html',
      'system.html',
      'create-tenant.html',
      'tenant-workbench.html',
    ]
    for (const path of paths) {
      await page.goto(`/admin/${path}`)
      const overflow = await page.evaluate(() => (
        document.documentElement.scrollWidth - window.innerWidth
      ))
      expect(overflow, `${path} should not overflow at ${viewport.width}px`).toBeLessThanOrEqual(1)
      await expect(page.locator('main#main')).toBeVisible()
      await expect(page.locator('.arch-rail__item.is-active')).toHaveCount(1)
    }
    if (viewport.width === 1024) {
      await page.goto('/admin/index.html')
      await expect(page.locator('[data-admin-module-toggle]')).toBeVisible()
      await expect(page.locator('.workspace-app')).toHaveClass(/acore-module-collapsed/)
      await expect(page.locator('[data-admin-module-toggle]')).toHaveAttribute('aria-expanded', 'false')
      await page.locator('[data-admin-module-toggle]').click()
      await expect(page.locator('.workspace-app')).not.toHaveClass(/acore-module-collapsed/)
      await expect(page.locator('[data-admin-module-toggle]')).toHaveAttribute('aria-expanded', 'true')
    }
    expect(runtimeErrors).toEqual({ pageErrors: [], consoleErrors: [] })
  })
}
