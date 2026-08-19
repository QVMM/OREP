import { expect, test } from '@playwright/test'

const unexpectedRequestsByPage = new WeakMap()

function isApiRequest(method, path, expectedMethod, expectedPath) {
  return method === expectedMethod && path === expectedPath
}

async function fulfillSharedShellRequest(route) {
  const url = new URL(route.request().url())
  const method = route.request().method()
  let data
  let wrapped = true
  if (['/api/monitor/heartbeat', '/api/monitor/track'].some(
    path => isApiRequest(method, url.pathname, 'POST', path)
  )) {
    data = { accepted: true }
  } else if (isApiRequest(method, url.pathname, 'GET', '/api/collaboration/summary')) {
    data = { pendingInvitations: 0, unreadMessages: 0, activeSessions: 0, items: [] }
  } else if (isApiRequest(method, url.pathname, 'GET', '/api/notifications')) {
    data = { items: [], unreadCount: 0 }
  } else if (isApiRequest(method, url.pathname, 'GET', '/api/ppt/health')) {
    data = { status: 'ok', image2_configured: true }
    wrapped = false
  } else if (isApiRequest(method, url.pathname, 'GET', '/api/ppt/providers')) {
    data = { providers: [] }
    wrapped = false
  } else if (isApiRequest(method, url.pathname, 'GET', '/api/ppt/templates')) {
    data = []
    wrapped = false
  } else if (isApiRequest(method, url.pathname, 'GET', '/api/ppt/history')) {
    data = { jobs: [] }
    wrapped = false
  } else {
    return false
  }
  await route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(wrapped ? { code: 200, data } : data),
  })
  return true
}

async function abortUnexpected(page, route) {
  const url = new URL(route.request().url())
  unexpectedRequestsByPage.get(page).push({
    method: route.request().method(),
    path: url.pathname,
  })
  await route.abort('blockedbyclient')
}

test.beforeEach(async ({ page }) => {
  unexpectedRequestsByPage.set(page, [])
  await page.addInitScript(() => {
    const user = { id: 9, username: '交互测试用户', role: 'STUDENT', tenantId: 1 }
    const payload = btoa(JSON.stringify({ sub: 9, exp: Math.floor(Date.now() / 1000) + 3600 }))
    localStorage.setItem('orep_user_token', `test.${payload}.signature`)
    localStorage.setItem('orep_user', JSON.stringify(user))
    localStorage.setItem('user', JSON.stringify(user))
  })
})

test.afterEach(async ({ page }) => {
  expect(unexpectedRequestsByPage.get(page) || []).toEqual([])
})

test('PPT task cards support keyboard selection and backend actions stay single-flight', async ({ page }) => {
  let questionnaireRequests = 0
  let taskCreateRequests = 0
  let confirmRequests = 0
  let downloadRequests = 0
  let historyDetailRequests = 0
  let confirmed = false

  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url())
    const path = url.pathname
    const method = route.request().method()
    const fulfill = data => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: 200, data }),
    })

    if (isApiRequest(method, path, 'GET', '/api/ppt/themes')) {
      return fulfill([
        {
          theme_id: 'dark_tech',
          name: '深色科技',
          theme_config: { colors: { bg: '#fff7ed', card_bg: '#ffffff', primary: '#e84a1c' } },
        },
        {
          theme_id: 'warm_minimal',
          name: '暖色简约',
          theme_config: { colors: { bg: '#fffaf7', card_bg: '#fff7ed', primary: '#c43812' } },
        },
      ])
    }
    if (isApiRequest(method, path, 'GET', '/api/ppt/user/9/tasks')) {
      return fulfill([
        {
          id: 55,
          project_name: '历史键盘项目',
          created_at: '2026-07-30T10:00:00Z',
          domain: 'ai_iot',
          status: 'completed',
        },
      ])
    }
    if (isApiRequest(method, path, 'GET', '/api/ppt/forms/fintech')) {
      return fulfill({ form_schema: { sections: [] } })
    }
    if (isApiRequest(method, path, 'POST', '/api/ppt/questionnaire/submit')) {
      questionnaireRequests += 1
      await new Promise(resolve => setTimeout(resolve, 120))
      return fulfill({ questionnaire_id: 61 })
    }
    if (isApiRequest(method, path, 'POST', '/api/ppt/task/create')) {
      taskCreateRequests += 1
      return fulfill({ task_id: 77 })
    }
    if (isApiRequest(method, path, 'POST', '/api/ppt/task/77/confirm')) {
      confirmRequests += 1
      await new Promise(resolve => setTimeout(resolve, 120))
      confirmed = true
      return fulfill({ confirmed: true })
    }
    if (isApiRequest(method, path, 'GET', '/api/ppt/task/77/download')) {
      downloadRequests += 1
      await new Promise(resolve => setTimeout(resolve, 120))
      return route.fulfill({
        status: 200,
        contentType: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        body: 'ppt',
      })
    }
    if (isApiRequest(method, path, 'GET', '/api/ppt/task/77')) {
      return fulfill(confirmed
        ? { status: 'completed', progress: 100, current_step: '已完成' }
        : {
            status: 'outline_ready',
            progress: 50,
            current_step: '大纲已生成',
            outline_json: {
              project: { name: '键盘交互项目' },
              pages: [{ page_index: 1, section: '封面', layout: 'cover_page', data: { title: '封面' } }],
            },
          })
    }
    if (isApiRequest(method, path, 'GET', '/api/ppt/task/55/history-detail')) {
      historyDetailRequests += 1
      return fulfill({})
    }

    if (await fulfillSharedShellRequest(route)) return
    return abortUnexpected(page, route)
  })

  await page.goto('/ppt-generator')

  const fintech = page.getByRole('button', { name: /金融科技/ })
  await fintech.focus()
  await expect(fintech).toBeFocused()
  await fintech.press('Enter')
  await expect(fintech).toHaveAttribute('aria-pressed', 'true')

  await page.getByRole('button', { name: '下一步' }).click()
  const submit = page.getByRole('button', { name: '提交并生成大纲' })
  await expect(submit).toBeVisible()
  await submit.evaluate(button => {
    button.click()
    button.click()
  })
  await expect.poll(() => questionnaireRequests).toBe(1)
  await expect.poll(() => taskCreateRequests).toBe(1)

  const warmTheme = page.getByRole('button', { name: /暖色简约/ })
  await expect(warmTheme).toBeVisible({ timeout: 6_000 })
  await warmTheme.focus()
  await warmTheme.press('Space')
  await expect(warmTheme).toHaveAttribute('aria-pressed', 'true')

  const confirm = page.getByRole('button', { name: '确认生成 PPT' })
  await confirm.evaluate(button => {
    button.click()
    button.click()
  })
  await expect.poll(() => confirmRequests).toBe(1)

  const download = page.getByRole('button', { name: '下载 PPT' })
  await expect(download).toBeVisible({ timeout: 6_000 })
  await download.evaluate(button => {
    button.click()
    button.click()
  })
  await expect.poll(() => downloadRequests).toBe(1)

  await page.getByRole('button', { name: '生成新的PPT' }).click()
  const history = page.getByRole('button', { name: /历史键盘项目/ })
  await history.focus()
  await expect(history).toBeFocused()
  await history.press('Enter')
  await expect(page).toHaveURL(/\/ppt-history\/55$/)
  await expect.poll(() => historyDetailRequests).toBe(1)
})

test('PPT history download gate and file request share one full-flow lock', async ({ page }) => {
  let refreshRequests = 0
  let downloadRequests = 0
  const detail = {
    task: {
      id: 55,
      project_name: '历史下载防重',
      status: 'completed',
      domain: 'ai_iot',
      created_at: '2026-07-30T10:00:00Z',
    },
    html_pages: [],
    snapshots: [],
    deliverability: {
      status: 'ready',
      label: '可下载',
      short_hint: '当前版本可下载',
      blockers: [],
      warnings: [],
    },
  }

  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url())
    const path = url.pathname
    const method = route.request().method()
    const fulfill = data => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: 200, data }),
    })

    if (isApiRequest(method, path, 'GET', '/api/ppt/task/55/history-detail')) return fulfill(detail)
    if (isApiRequest(method, path, 'POST', '/api/ppt/task/55/workspace-refresh')) {
      refreshRequests += 1
      await new Promise(resolve => setTimeout(resolve, 120))
      return fulfill(detail)
    }
    if (isApiRequest(method, path, 'GET', '/api/ppt/task/55/download')) {
      downloadRequests += 1
      await new Promise(resolve => setTimeout(resolve, 120))
      return route.fulfill({
        status: 200,
        contentType: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        body: 'ppt',
      })
    }

    if (await fulfillSharedShellRequest(route)) return
    return abortUnexpected(page, route)
  })

  await page.goto('/ppt-history/55')
  const download = page.locator('.ai-app-header__actions').getByRole('button', { name: /下载 PPT/ })
  await expect(download).toBeVisible()
  await download.evaluate(button => {
    button.click()
    button.click()
  })

  await expect.poll(() => refreshRequests).toBe(1)
  await expect.poll(() => downloadRequests).toBe(1)
})

test('leaving PPT history during readiness refresh aborts the stale download chain', async ({ page }) => {
  let refreshRequests = 0
  let downloadRequests = 0
  let browserDownloads = 0
  let releaseRefresh
  const refreshGate = new Promise(resolve => {
    releaseRefresh = resolve
  })
  const detail = {
    task: {
      id: 55,
      project_name: '离页下载保护',
      status: 'completed',
      created_at: '2026-07-30T10:00:00Z',
    },
    html_pages: [],
    snapshots: [],
    deliverability: {
      status: 'ready',
      label: '可下载',
      short_hint: '当前版本可下载',
      blockers: [],
      warnings: [],
    },
  }
  page.on('download', () => {
    browserDownloads += 1
  })

  await page.route('**/api/**', async route => {
    const url = new URL(route.request().url())
    const path = url.pathname
    const method = route.request().method()
    const fulfill = data => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: 200, data }),
    })

    if (isApiRequest(method, path, 'GET', '/api/ppt/task/55/history-detail')) return fulfill(detail)
    if (isApiRequest(method, path, 'POST', '/api/ppt/task/55/workspace-refresh')) {
      refreshRequests += 1
      await refreshGate
      return fulfill(detail)
    }
    if (isApiRequest(method, path, 'GET', '/api/ppt/task/55/download')) {
      downloadRequests += 1
      return route.fulfill({
        status: 200,
        contentType: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        body: 'ppt',
      })
    }

    if (await fulfillSharedShellRequest(route)) return
    return abortUnexpected(page, route)
  })

  await page.goto('/ppt-history/55')
  await page.evaluate(() => {
    window.__observedElementMessages = []
    const recordMessages = node => {
      if (!(node instanceof Element)) return
      const messages = [
        ...(node.matches('.el-message') ? [node] : []),
        ...node.querySelectorAll('.el-message'),
      ]
      messages.forEach(message => {
        window.__observedElementMessages.push(message.textContent?.trim() || '')
      })
    }
    const observer = new MutationObserver(mutations => {
      mutations.forEach(mutation => {
        mutation.addedNodes.forEach(recordMessages)
      })
    })
    observer.observe(document.body, { childList: true, subtree: true })
    window.__elementMessageObserver = observer
  })
  const download = page.locator('.ai-app-header__actions').getByRole('button', { name: /下载 PPT/ })
  await download.click()
  await expect.poll(() => refreshRequests).toBe(1)

  await page.locator('.ai-app-header__back').click()
  await expect(page).toHaveURL(/\/ppt-editor\?view=history$/)
  releaseRefresh()
  await page.waitForTimeout(300)

  expect(refreshRequests).toBe(1)
  expect(downloadRequests).toBe(0)
  expect(browserDownloads).toBe(0)
  await expect(page.locator('.el-message')).toHaveCount(0)
  expect(await page.evaluate(() => window.__observedElementMessages)).toEqual([])
})

test('leaving PPT history before a delayed detail failure suppresses the stale error toast', async ({ page }) => {
  let detailRequests = 0
  let releaseDetail
  const detailGate = new Promise(resolve => {
    releaseDetail = resolve
  })

  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname
    const method = route.request().method()
    const fulfill = data => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: 200, data }),
    })

    if (isApiRequest(method, path, 'GET', '/api/ppt/task/55/history-detail')) {
      detailRequests += 1
      await detailGate
      return route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'delayed failure' }),
      })
    }
    if (await fulfillSharedShellRequest(route)) return
    return abortUnexpected(page, route)
  })

  await page.goto('/ppt-history/55')
  await expect.poll(() => detailRequests).toBe(1)
  await page.locator('.ai-app-header__back').click()
  await expect(page).toHaveURL(/\/ppt-editor\?view=history$/)
  releaseDetail()
  await page.waitForTimeout(300)

  await expect(page.getByText('加载 PPT 历史详情失败', { exact: true })).toHaveCount(0)
})

test('leaving PPT history closes an open download condition dialog without continuing', async ({ page }) => {
  let downloadRequests = 0
  const detail = {
    task: {
      id: 55,
      project_name: '离页弹窗保护',
      status: 'completed',
      created_at: '2026-07-30T10:00:00Z',
    },
    html_pages: [],
    snapshots: [],
    deliverability: {
      status: 'blocked',
      label: '暂不可下载',
      short_hint: '请先处理下载条件',
      summary: '还有关键下载条件未满足。',
      blockers: ['必备评分点覆盖率不足'],
      blocker_details: [],
      warnings: [],
    },
  }

  await page.route('**/api/**', async route => {
    const path = new URL(route.request().url()).pathname
    const method = route.request().method()
    const fulfill = data => route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ code: 200, data }),
    })

    if (isApiRequest(method, path, 'GET', '/api/ppt/task/55/history-detail')) return fulfill(detail)
    if (isApiRequest(method, path, 'GET', '/api/ppt/task/55/download')) {
      downloadRequests += 1
      return route.fulfill({
        status: 200,
        contentType: 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        body: 'ppt',
      })
    }
    if (await fulfillSharedShellRequest(route)) return
    return abortUnexpected(page, route)
  })

  await page.goto('/ppt-history/55')
  const download = page.locator('.ai-app-header__actions').getByRole('button', { name: /下载条件/ })
  await download.click()
  await expect(page.getByRole('dialog', { name: '下载条件未达标' })).toBeVisible()

  await page.locator('.ai-app-header__back').evaluate(button => button.click())
  await expect(page).toHaveURL(/\/ppt-editor\?view=history$/)
  await expect(page.getByRole('dialog', { name: '下载条件未达标' })).toHaveCount(0)
  expect(downloadRequests).toBe(0)
  await expect(page.getByText(/下载失败|继续处理并返回下载/)).toHaveCount(0)
})
