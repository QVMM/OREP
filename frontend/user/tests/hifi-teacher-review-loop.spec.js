import { expect, test } from '@playwright/test'

test.use({ viewport: { width: 1512, height: 744 } })

function captureRuntimeErrors(page) {
  const pageErrors = []
  const consoleErrors = []

  page.on('pageerror', (error) => pageErrors.push(error.message))
  page.on('console', (message) => {
    if (message.type() === 'error') consoleErrors.push(message.text())
  })

  return { pageErrors, consoleErrors }
}

function expectNoRuntimeErrors(runtimeErrors) {
  expect(runtimeErrors.pageErrors).toEqual([])
  expect(runtimeErrors.consoleErrors).toEqual([])
}

async function resetDashboard(page) {
  await page.goto('/teacher/index.html')
  await page.evaluate(() => window.OREPDemoState.reset())
  await page.reload()
}

async function approveCase(page, caseId) {
  await page.evaluate((approvedCaseId) => {
    window.OREPDemoState.dispatch({
      type: 'APPROVE',
      caseId: approvedCaseId,
      payload: {
        scores: {
          structure: 88,
          troubleshooting: 86,
          evidence: 82,
          clarity: 84,
        },
        comment: '结构与排障路径完整，证据能够支撑结论，可以进入下一阶段训练。',
        nextMove: '整理本轮排障证据，并转化为路演中的一分钟案例说明。',
      },
    })
  }, caseId)
}

async function requestChangesCase(page, caseId) {
  await page.evaluate((requestedCaseId) => {
    window.OREPDemoState.dispatch({
      type: 'REQUEST_CHANGES',
      caseId: requestedCaseId,
      payload: {
        scores: {
          structure: 80,
          troubleshooting: 78,
          evidence: 70,
          clarity: 76,
        },
        comment: '异常分支的证据还不够具体，请补齐组件对应关系后重新提交。',
        nextMove: '逐项标注异常现象、所属组件和可验证的回滚条件。',
        remediation: {
          issueType: '证据不足',
          evidenceLocation: '排障清单第 3、4 条',
          expectedResult: '每条异常分支对应组件截图和可验证回滚条件',
          dueAt: '2026-07-19T18:00:00+08:00',
          reason: '当前清单不能复现异常分支的处置过程',
        },
      },
    })
  }, caseId)
}

async function contrastRatio(locator, backgroundSelector) {
  return locator.evaluate((element, selector) => {
    function channels(value) {
      return value.match(/[\d.]+/g).slice(0, 3).map(Number)
    }

    function luminance(value) {
      return channels(value)
        .map((channel) => channel / 255)
        .map((channel) => (
          channel <= 0.04045
            ? channel / 12.92
            : ((channel + 0.055) / 1.055) ** 2.4
        ))
        .reduce((sum, channel, index) => sum + channel * [0.2126, 0.7152, 0.0722][index], 0)
    }

    const foreground = getComputedStyle(element).color
    const backgroundElement = selector ? document.querySelector(selector) : element
    const background = getComputedStyle(backgroundElement).backgroundColor
    const lighter = Math.max(luminance(foreground), luminance(background))
    const darker = Math.min(luminance(foreground), luminance(background))
    return (lighter + 0.05) / (darker + 0.05)
  }, backgroundSelector)
}

test('教师首页初始态与审核订阅联动', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)
  await resetDashboard(page)

  try {
    await expect(page).toHaveTitle('教师工作台 · 老师端')
    await expect(page.locator('.module-list')).toHaveCount(0)
    await expect(page.locator('.workspace-app.has-module-list')).toHaveCount(0)
    await expect(page.locator('.arch-rail__item.is-active'))
      .toHaveAttribute('aria-current', 'page')
    await expect(page.getByRole('searchbox', { name: '搜索课程、任务、文件、报告' })).toBeVisible()

    await expect(page.locator('[data-teacher-pending-count]')).toHaveText('3')

    const priorityCard = page.locator('[data-teacher-priority-card]')
    await expect(priorityCard).toContainText('张志强')
    await expect(priorityCard).toContainText('Day 4')
    await expect(priorityCard).toContainText('首次审核')

    const primaryButtons = page.locator('.tcore-dashboard .tcore-button--primary')
    await expect(primaryButtons).toHaveCount(1)
    await expect(primaryButtons).toHaveText('处理待评')
    await expect(primaryButtons).toHaveAttribute('href', 'review.html?item=zhang-day4#queue')
    expect(await primaryButtons.evaluate((element) => getComputedStyle(element).backgroundColor))
      .toBe('rgb(232, 74, 28)')
    expect(await contrastRatio(primaryButtons)).toBeGreaterThanOrEqual(4.5)
    expect(
      await contrastRatio(page.locator('.tcore-today-card__date'), '.tcore-today-card'),
    ).toBeGreaterThanOrEqual(4.5)

    const todayList = page.locator('[data-teacher-today-list]')
    await expect(todayList).toBeVisible()
    const viewportAudit = await page.evaluate(() => {
      function isInViewport(element) {
        const rect = element.getBoundingClientRect()
        return rect.top >= 0
          && rect.left >= 0
          && rect.bottom <= window.innerHeight
          && rect.right <= window.innerWidth
      }

      return {
        todayListInViewport: isInViewport(document.querySelector('[data-teacher-today-list]')),
        todayCardInViewport: isInViewport(document.querySelector('.tcore-today-card')),
        todayPreviewInViewport: isInViewport(document.querySelector('.tcore-today-card__preview')),
        priorityCardInViewport: isInViewport(document.querySelector('[data-teacher-priority-card]')),
        horizontalOverflow: document.documentElement.scrollWidth - window.innerWidth,
      }
    })
    expect(viewportAudit.todayListInViewport).toBe(true)
    expect(viewportAudit.todayCardInViewport).toBe(true)
    expect(viewportAudit.todayPreviewInViewport).toBe(true)
    expect(viewportAudit.priorityCardInViewport).toBe(true)
    expect(viewportAudit.horizontalOverflow).toBeLessThanOrEqual(1)

    const noReloadSentinel = 'teacher-dashboard-dispatch-stays-on-page'
    let mainFrameNavigationCount = 0
    page.on('framenavigated', (frame) => {
      if (frame === page.mainFrame()) mainFrameNavigationCount += 1
    })
    await page.evaluate((sentinel) => {
      window.__tcoreNoReload = sentinel
      document.documentElement.dataset.tcoreNoReload = sentinel
    }, noReloadSentinel)

    await approveCase(page, 'zhang-day4')

    expect(await page.evaluate(() => ({
      windowSentinel: window.__tcoreNoReload,
      documentSentinel: document.documentElement.dataset.tcoreNoReload,
    }))).toEqual({
      windowSentinel: noReloadSentinel,
      documentSentinel: noReloadSentinel,
    })
    expect(mainFrameNavigationCount).toBe(0)
    await expect(page.locator('[data-teacher-pending-count]')).toHaveText('2')
    await expect(priorityCard).not.toContainText('张志强')
    await expect(priorityCard).toContainText('赵丽颖')
    await expect(primaryButtons).toHaveAttribute('href', 'review.html?item=zhao-day1#queue')

    expectNoRuntimeErrors(runtimeErrors)
  } finally {
    await page.evaluate(() => window.OREPDemoState.reset())
  }
})

for (const missingApi of ['getState', 'selectTeacherSummary', 'subscribe', 'STATUS']) {
  test(`教师首页初始态在缺少 ${missingApi} API 时显示安全提示`, async ({ page }) => {
    const runtimeErrors = captureRuntimeErrors(page)
    await page.route('**/shared/demo-state.js', async (route) => {
      await route.fulfill({
        contentType: 'application/javascript',
        body: `
          (function () {
            var api = {
              getState: function () { return {}; },
              selectTeacherSummary: function () { return {}; },
              subscribe: function () { return function () {}; },
              STATUS: { RESUBMITTED: 'RESUBMITTED' },
              consumeRecoveryNotice: function () {
                window.__teacherRecoveryConsumeCount += 1;
                return true;
              }
            };
            window.__teacherRecoveryConsumeCount = 0;
            delete api[${JSON.stringify(missingApi)}];
            window.OREPDemoState = api;
          }());
        `,
      })
    })

    await page.goto('/teacher/index.html')

    await expect(page.locator('.tcore-runtime-alert[role="alert"]')).toHaveCount(1)
    await expect(page.locator('.tcore-runtime-alert[role="alert"]'))
      .toHaveText('演示状态暂不可用，请刷新页面。')
    expect(await page.evaluate(() => window.__teacherRecoveryConsumeCount)).toBe(0)
    await expect(page.locator('.toast')).toHaveText('')
    expectNoRuntimeErrors(runtimeErrors)
  })
}

test('教师目标页初始化失败时不提前消费恢复通知', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)
  await page.route('**/shared/demo-state.js', async (route) => {
    await route.fulfill({
      contentType: 'application/javascript',
      body: `
        window.__teacherRecoveryConsumeCount = 0;
        window.OREPDemoState = {
          getState: function () { return {}; },
          consumeRecoveryNotice: function () {
            window.__teacherRecoveryConsumeCount += 1;
            return true;
          }
        };
      `,
    })
  })

  await page.goto('/teacher/review.html?item=zhang-day4#queue')
  await expect(page.locator('.tcore-runtime-alert[role="alert"]'))
    .toHaveText('演示状态暂不可用，请刷新页面。')
  expect(await page.evaluate(() => Boolean(window.__OREPTeacherReviewLifecycle))).toBe(false)
  expect(await page.evaluate(() => window.__teacherRecoveryConsumeCount)).toBe(0)
  await expect(page.locator('.toast')).toHaveText('')
  expectNoRuntimeErrors(runtimeErrors)
})

test('教师首页初始态空队列隐藏主行动且 reset 后恢复', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)
  await resetDashboard(page)

  try {
    await approveCase(page, 'zhang-day4')
    await approveCase(page, 'li-day4')
    await approveCase(page, 'zhao-day1')

    const primaryAction = page.locator('[data-teacher-primary-action]')
    await expect(page.locator('[data-teacher-priority-card]')).toContainText('待评已清空')
    await expect(primaryAction).toBeHidden()
    await expect(page.locator('.tcore-dashboard .tcore-button--primary:visible')).toHaveCount(0)
    await expect(
      page.locator('.tcore-welcome').getByRole('link', { name: '打开营看板' }),
    ).toHaveCount(1)

    await page.evaluate(() => window.OREPDemoState.reset())

    await expect(primaryAction).toBeVisible()
    await expect(primaryAction).toHaveText('处理待评')
    await expect(primaryAction).toHaveClass(/tcore-button--primary/)
    await expect(primaryAction).toHaveAttribute('href', 'review.html?item=zhang-day4#queue')
    expectNoRuntimeErrors(runtimeErrors)
  } finally {
    await page.evaluate(() => window.OREPDemoState.reset())
  }
})

test('教师首页初始态重复脚本与 BFCache 生命周期保持单一订阅', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)
  await resetDashboard(page)

  try {
    await page.evaluate(() => {
      window.__tcoreSubscribeCalls = 0
      const originalSubscribe = window.OREPDemoState.subscribe
      window.OREPDemoState.subscribe = function countedSubscribe(listener) {
        window.__tcoreSubscribeCalls += 1
        return originalSubscribe.call(this, listener)
      }
    })

    await page.addScriptTag({ url: '/teacher/js/teacher-core.js' })
    expect(await page.evaluate(() => window.__tcoreSubscribeCalls)).toBe(0)

    await page.evaluate(() => {
      window.dispatchEvent(new PageTransitionEvent('pagehide', { persisted: true }))
    })
    await approveCase(page, 'zhang-day4')
    await expect(page.locator('[data-teacher-pending-count]')).toHaveText('3')

    await page.evaluate(() => {
      window.dispatchEvent(new PageTransitionEvent('pageshow', { persisted: true }))
    })
    await expect(page.locator('[data-teacher-pending-count]')).toHaveText('2')
    expect(await page.evaluate(() => window.__tcoreSubscribeCalls)).toBe(1)

    await approveCase(page, 'zhao-day1')
    await expect(page.locator('[data-teacher-pending-count]')).toHaveText('1')
    expectNoRuntimeErrors(runtimeErrors)
  } finally {
    await page.evaluate(() => window.OREPDemoState.reset())
  }
})

test('教师首页初始态在 375 宽度保持决策台首屏可见', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 744 })
  const runtimeErrors = captureRuntimeErrors(page)
  await resetDashboard(page)

  try {
    const dashboard = page.locator('.tcore-dashboard')
    const workspaceMain = page.locator('.workspace-main')
    const welcomeTitle = page.getByRole('heading', { name: /刘老师，先处理/ })
    const mobileGeometry = await page.evaluate(() => {
      const dashboardRect = document.querySelector('.tcore-dashboard').getBoundingClientRect()
      const railRect = document.querySelector('.arch-rail').getBoundingClientRect()
      const mainRect = document.querySelector('.workspace-main').getBoundingClientRect()
      return {
        dashboardTop: dashboardRect.top,
        railWidth: railRect.width,
        mainWidth: mainRect.width,
        horizontalOverflow: document.documentElement.scrollWidth - window.innerWidth,
        viewportHeight: window.innerHeight,
      }
    })

    await expect(dashboard).toBeVisible()
    await expect(workspaceMain).toBeVisible()
    await expect(welcomeTitle).toBeVisible()
    expect(mobileGeometry.dashboardTop).toBeLessThan(mobileGeometry.viewportHeight)
    expect(mobileGeometry.railWidth).toBeGreaterThanOrEqual(60)
    expect(mobileGeometry.railWidth).toBeLessThanOrEqual(68)
    expect(mobileGeometry.railWidth).toBeLessThan(mobileGeometry.mainWidth)
    expect(mobileGeometry.horizontalOverflow).toBeLessThanOrEqual(1)
    expectNoRuntimeErrors(runtimeErrors)
  } finally {
    await page.evaluate(() => window.OREPDemoState.reset())
  }
})

async function resetReview(page, viewport = { width: 1512, height: 900 }) {
  await page.setViewportSize(viewport)
  await page.goto('/teacher/review.html?item=zhang-day4#queue')
  await page.evaluate(() => window.OREPDemoState.reset())
  await page.reload()
}

async function resetCamp(page, viewport = { width: 1512, height: 900 }) {
  await page.setViewportSize(viewport)
  await page.goto('/teacher/camp.html')
  await page.evaluate(() => window.OREPDemoState.reset())
  await page.reload()
}

test('审核工作台直接通过保留提交并自动选择下一条', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)
  await resetReview(page)

  try {
    const zhangQueueItem = page.locator('[data-review-case-id="zhang-day4"]')
    await expect(zhangQueueItem).toHaveAttribute('aria-current', 'true')
    await expect(page.locator('[data-review-queue-count]')).toHaveText('3')

    const evidence = page.locator('#reviewEvidencePanel')
    await expect(evidence).toContainText('验收标准')
    await expect(evidence).toContainText('学生说明')
    await expect(evidence).toContainText('组件结构说明.pdf')
    await expect(evidence).toContainText('排障清单.md')
    await expect(evidence).toContainText('30 秒口述热身.m4a')
    await expect(evidence).toContainText('第 1 轮')

    const decision = page.locator('#reviewDecisionPanel')
    await expect(decision).toContainText('AI 初评 · 仅供参考')
    await page.locator('[data-apply-ai]').click()

    const expectedScores = {
      structure: '88',
      troubleshooting: '84',
      evidence: '76',
      clarity: '82',
    }
    for (const [dimension, score] of Object.entries(expectedScores)) {
      const input = page.locator(`[data-score-input="${dimension}"]`)
      await expect(input).toHaveValue(score)
      await expect(input).toHaveAttribute('aria-valuetext', `${score} 分`)
      await expect(page.locator(`[data-score-output="${dimension}"]`)).toHaveText(score)
    }
    await expect(page.locator('[data-teacher-comment]')).toHaveValue(/异常分支/)
    await expect(page.locator('[data-teacher-next-move]')).toHaveValue(/可复现记录/)
    expect(await page.evaluate(() => (
      window.OREPDemoState.selectCase(
        window.OREPDemoState.getState(),
        'zhang-day4',
      ).status
    ))).toBe('PENDING_REVIEW')

    await page.locator('[data-prepare-approve]').click()
    const confirmation = page.locator('[data-decision-confirmation]')
    await expect(confirmation).toBeVisible()
    await expect(page.locator('[data-prepare-approve]')).toBeHidden()
    await expect(page.locator('.tcore-review .tcore-button--primary:visible')).toHaveCount(1)
    await expect(confirmation).toContainText('通过并发布')
    await expect(confirmation).toContainText('已通过')
    await page.locator('[data-confirm-decision]').click()

    await expect(page.locator('[data-review-queue-count]')).toHaveText('2')
    await expect(zhangQueueItem).toHaveCount(0)
    await expect(page.locator('[data-review-case-id="zhao-day1"]'))
      .toHaveAttribute('aria-current', 'true')

    const state = await page.evaluate(() => window.OREPDemoState.getState())
    const currentCase = state.reviewCases.find((item) => item.caseId === 'zhang-day4')
    expect(currentCase.status).toBe('PASSED')
    expect(currentCase.decisions).toHaveLength(1)
    expect(currentCase.submissions).toHaveLength(1)
    expectNoRuntimeErrors(runtimeErrors)
  } finally {
    await page.evaluate(() => window.OREPDemoState.reset())
  }
})

test('审核工作台退回校验原子失败并逐项清除错误引用', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)
  await resetReview(page)

  try {
    await page.evaluate(() => {
      window.__reviewDispatchCount = 0
      window.__reviewToastCount = 0
      const dispatch = window.OREPDemoState.dispatch
      window.OREPDemoState.dispatch = function countedDispatch(action) {
        window.__reviewDispatchCount += 1
        return dispatch.call(this, action)
      }
      window.toast = function countedToast() {
        window.__reviewToastCount += 1
      }
    })
    await page.locator('[data-prepare-return]').click()
    await expect(page.locator('[data-decision-confirmation]')).toBeVisible()
    await page.locator('[data-confirm-decision]').click()

    const summary = page.locator('[data-decision-errors][role="alert"]')
    await expect(summary).toBeVisible()
    await expect(summary.locator('li')).toHaveCount(7)
    await expect(summary).toContainText('请填写教师评语')
    await expect(summary).toContainText('请填写下一刀建议')
    expect(await summary.locator('button').evaluateAll((buttons) => (
      buttons.every((button) => button.getBoundingClientRect().height >= 40)
    ))).toBe(true)
    const remediationFields = [
      'issueType',
      'evidenceLocation',
      'expectedResult',
      'dueAt',
      'reason',
    ]
    const requiredControls = [
      page.locator('[data-teacher-comment]'),
      page.locator('[data-teacher-next-move]'),
      ...remediationFields.map((field) => (
        page.locator(`[data-remediation-field="${field}"]`)
      )),
    ]
    const errorIds = []
    for (const input of requiredControls) {
      await expect(input).toHaveAttribute('aria-invalid', 'true')
      const describedBy = await input.getAttribute('aria-describedby')
      expect(describedBy).toBeTruthy()
      errorIds.push(describedBy)
      await expect(page.locator(`#${describedBy}`)).toBeVisible()
    }
    expect(new Set(errorIds).size).toBe(7)
    await expect(page.locator('[data-teacher-comment]')).toBeFocused()
    expect(await page.evaluate(() => ({
      dispatches: window.__reviewDispatchCount,
      toasts: window.__reviewToastCount,
      status: window.OREPDemoState.selectCase(
        window.OREPDemoState.getState(),
        'zhang-day4',
      ).status,
    }))).toEqual({
      dispatches: 0,
      toasts: 0,
      status: 'PENDING_REVIEW',
    })

    const comment = page.locator('[data-teacher-comment]')
    await comment.fill('异常分支证据仍不够具体，请补齐后重提。')
    await expect(comment).not.toHaveAttribute('aria-invalid', 'true')
    await expect(comment).not.toHaveAttribute('aria-describedby', /.+/)
    await expect(summary.locator('li')).toHaveCount(6)
    await expect(summary).not.toContainText('请填写教师评语')

    const nextMove = page.locator('[data-teacher-next-move]')
    await nextMove.fill('逐项关联组件、异常现象和回滚条件。')
    await expect(summary.locator('li')).toHaveCount(5)

    for (const field of remediationFields) {
      const input = page.locator(`[data-remediation-field="${field}"]`)
      await expect(input).toHaveAttribute('aria-invalid', 'true')
      const describedBy = await input.getAttribute('aria-describedby')
      expect(describedBy).toBeTruthy()
      await expect(page.locator(`#${describedBy}`)).toBeVisible()
    }

    const issueType = page.locator('[data-remediation-field="issueType"]')
    await issueType.selectOption('证据不足')
    await expect(issueType).not.toHaveAttribute('aria-invalid', 'true')
    await expect(issueType).not.toHaveAttribute('aria-describedby', /.+/)
    await expect(summary.locator('li')).toHaveCount(4)

    await page.locator('[data-remediation-field="evidenceLocation"]')
      .fill('排障清单第 3、4 条')
    await page.locator('[data-remediation-field="expectedResult"]')
      .fill('每条异常分支对应组件截图和可验证回滚条件')
    await page.locator('[data-remediation-field="dueAt"]').fill('2026-07-19T18:00')
    await page.locator('[data-remediation-field="reason"]')
      .fill('当前清单不能复现异常分支的处置过程')
    await expect(page.locator('[data-decision-errors]')).not.toHaveAttribute('role', 'alert')
    await expect(page.locator('[data-decision-errors]')).toBeEmpty()
    await page.locator('[data-confirm-decision]').click()

    const state = await page.evaluate(() => window.OREPDemoState.getState())
    const currentCase = state.reviewCases.find((item) => item.caseId === 'zhang-day4')
    expect(currentCase.status).toBe('CHANGES_REQUESTED')
    expect(currentCase.decisions).toHaveLength(1)
    expect(currentCase.decisions[0].remediation.issueType).toBe('证据不足')
    expect(currentCase.decisions[0].remediation.dueAt)
      .toBe('2026-07-19T18:00:00+08:00')
    expect(await page.evaluate(() => ({
      dispatches: window.__reviewDispatchCount,
      toasts: window.__reviewToastCount,
    }))).toEqual({ dispatches: 1, toasts: 1 })
    expectNoRuntimeErrors(runtimeErrors)
  } finally {
    await page.evaluate(() => window.OREPDemoState.reset())
  }
})

test('退回错误产生后采用 AI 即时清除评语与下一刀错误', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)
  await resetReview(page)

  try {
    await page.locator('[data-prepare-return]').click()
    await page.locator('[data-confirm-decision]').click()

    const summary = page.locator('[data-decision-errors][role="alert"]')
    const comment = page.locator('[data-teacher-comment]')
    const nextMove = page.locator('[data-teacher-next-move]')
    await expect(summary.locator('li')).toHaveCount(7)
    const commentErrorId = await comment.getAttribute('aria-describedby')
    const nextMoveErrorId = await nextMove.getAttribute('aria-describedby')
    expect(commentErrorId).toBeTruthy()
    expect(nextMoveErrorId).toBeTruthy()

    await page.locator('[data-apply-ai]').click()

    await expect(comment).toHaveValue(/异常分支/)
    await expect(nextMove).toHaveValue(/可复现记录/)
    await expect(comment).not.toHaveAttribute('aria-invalid', 'true')
    await expect(comment).not.toHaveAttribute('aria-describedby', /.+/)
    await expect(nextMove).not.toHaveAttribute('aria-invalid', 'true')
    await expect(nextMove).not.toHaveAttribute('aria-describedby', /.+/)
    await expect(page.locator(`#${commentErrorId}`)).toHaveCount(0)
    await expect(page.locator(`#${nextMoveErrorId}`)).toHaveCount(0)
    await expect(summary.locator('li')).toHaveCount(5)
    await expect(summary).not.toContainText('请填写教师评语')
    await expect(summary).not.toContainText('请填写下一刀建议')

    for (const field of [
      'issueType',
      'evidenceLocation',
      'expectedResult',
      'dueAt',
      'reason',
    ]) {
      const control = page.locator(`[data-remediation-field="${field}"]`)
      await expect(control).toHaveAttribute('aria-invalid', 'true')
      const errorId = await control.getAttribute('aria-describedby')
      await expect(page.locator(`#${errorId}`)).toBeVisible()
    }
    expect(await page.evaluate(() => (
      window.OREPDemoState.selectCase(
        window.OREPDemoState.getState(),
        'zhang-day4',
      ).status
    ))).toBe('PENDING_REVIEW')
    expectNoRuntimeErrors(runtimeErrors)
  } finally {
    await page.evaluate(() => window.OREPDemoState.reset())
  }
})

test('审核响应控件在模块浮层侧栏和移动三段间恢复焦点', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)

  await resetReview(page, { width: 1280, height: 800 })
  const moduleToggle = page.locator('button[data-teacher-module-toggle]')
  const moduleList = page.locator('#teacherModuleList')
  await expect(moduleToggle).toBeVisible()
  await expect(moduleToggle).toHaveAttribute('aria-expanded', 'false')
  await expect(moduleList).toBeHidden()
  await expect(moduleList).toHaveAttribute('inert', '')
  await moduleToggle.click()
  await expect(moduleToggle).toHaveAttribute('aria-expanded', 'true')
  await expect(moduleList).toBeVisible()
  await page.keyboard.press('Escape')
  await expect(moduleList).toBeHidden()
  await expect(moduleToggle).toBeFocused()

  await resetReview(page, { width: 1024, height: 800 })
  const decisionToggle = page.locator('[data-review-decision-toggle]')
  const decisionPanel = page.locator('#reviewDecisionPanel')
  await expect(decisionToggle).toBeVisible()
  await expect(decisionToggle).toHaveAttribute('aria-expanded', 'false')
  await expect(decisionPanel).toBeHidden()
  await expect(decisionPanel).toHaveAttribute('inert', '')
  await decisionToggle.click()
  await expect(decisionToggle).toHaveAttribute('aria-expanded', 'true')
  await expect(decisionToggle).toHaveClass(/tcore-button--secondary/)
  await expect(page.locator('.tcore-review .tcore-button--primary:visible')).toHaveCount(1)
  await expect(decisionPanel).toBeVisible()
  await expect(page.locator('#reviewDecisionTitle')).toBeFocused()
  await page.keyboard.press('Escape')
  await expect(decisionPanel).toBeHidden()
  await expect(decisionToggle).toBeFocused()

  await resetReview(page, { width: 390, height: 844 })
  const tabs = page.locator('[data-review-pane-tabs] [role="tab"]')
  await expect(tabs).toHaveCount(3)
  await expect(tabs.nth(0)).toHaveAttribute('aria-controls', 'reviewQueuePanel')
  await expect(tabs.nth(1)).toHaveAttribute('aria-controls', 'reviewEvidencePanel')
  await expect(tabs.nth(2)).toHaveAttribute('aria-controls', 'reviewDecisionPanel')
  await expect(tabs.nth(0)).toHaveAttribute('aria-selected', 'true')
  await expect(page.locator('#reviewQueuePanel')).toBeVisible()
  await expect(page.locator('#reviewEvidencePanel')).toBeHidden()
  await expect(page.locator('#reviewEvidencePanel')).toHaveAttribute('inert', '')
  await expect(page.locator('#reviewDecisionPanel')).toBeHidden()

  await tabs.nth(0).focus()
  await page.keyboard.press('ArrowLeft')
  await expect(tabs.nth(2)).toHaveAttribute('aria-selected', 'true')
  await expect(page.locator('#reviewDecisionPanel')).toBeVisible()
  await page.keyboard.press('Home')
  await expect(tabs.nth(0)).toHaveAttribute('aria-selected', 'true')
  await page.keyboard.press('End')
  await expect(tabs.nth(2)).toHaveAttribute('aria-selected', 'true')
  await page.keyboard.press('ArrowRight')
  await expect(tabs.nth(0)).toHaveAttribute('aria-selected', 'true')
  await expect(tabs.nth(0)).toBeFocused()
  expectNoRuntimeErrors(runtimeErrors)
})

test('审核队列排序深链筛选等待时间与评分触控契约', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)
  await resetReview(page)

  async function queueOrder() {
    return page.locator('[data-review-case-id]').evaluateAll((items) => (
      items.map((item) => item.getAttribute('data-review-case-id'))
    ))
  }

  try {
    await expect(page.locator('[data-review-filter-value]')).toHaveText([
      '全部',
      '首次审核',
      '复审',
      '逾期',
    ])
    expect(await queueOrder()).toEqual(['zhang-day4', 'zhao-day1', 'li-day4'])
    for (const item of await page.locator('[data-review-case-id]').all()) {
      await expect(item.locator('.tcore-queue-item__meta')).toContainText(
        /已等待 \d+ (分钟|小时|天)/,
      )
      await expect(item.locator('.tcore-queue-item__meta')).not.toContainText('-')
    }

    const filters = [
      ['first', 3, ['zhang-day4', 'zhao-day1', 'li-day4']],
      ['resubmitted', 0, []],
      ['overdue', 1, ['zhao-day1']],
      ['all', 3, ['zhang-day4', 'zhao-day1', 'li-day4']],
    ]
    for (const [value, count, order] of filters) {
      const filter = page.locator(`[data-review-filter-value="${value}"]`)
      await filter.click()
      await expect(filter).toHaveAttribute('aria-pressed', 'true')
      await expect(page.locator('[data-review-case-id]')).toHaveCount(count)
      expect(await queueOrder()).toEqual(order)
      if (value === 'resubmitted') {
        await expect(page.locator('.tcore-decision-actions')).toBeHidden()
      }
    }
    await expect(page.locator('.tcore-decision-actions')).toBeVisible()

    await page.goto('/teacher/review.html?item=li-day4#queue')
    await expect(page.locator('[data-review-case-id="li-day4"]'))
      .toHaveAttribute('aria-current', 'true')
    expect(await queueOrder()).toEqual(['zhang-day4', 'zhao-day1', 'li-day4'])

    await page.goto('/teacher/review.html?filter=overdue#queue')
    await expect(page.locator('[data-review-filter-value="overdue"]'))
      .toHaveAttribute('aria-pressed', 'true')
    await expect(page.locator('[data-review-case-id="zhao-day1"]'))
      .toHaveAttribute('aria-current', 'true')

    await page.goto('/teacher/review.html?item=zhang-day4#queue')
    const filterBoxes = await page.locator('[data-review-filter-value]').evaluateAll((buttons) => (
      buttons.map((button) => button.getBoundingClientRect().height)
    ))
    expect(filterBoxes.every((height) => height >= 40)).toBe(true)

    const score = page.locator('[data-score-input="structure"]')
    const output = page.locator('[data-score-output="structure"]')
    expect((await score.boundingBox()).height).toBeGreaterThanOrEqual(40)
    await score.focus()
    await page.keyboard.press('ArrowRight')
    await expect(score).toHaveValue('1')
    await expect(output).toHaveText('1')
    await expect(score).toHaveAttribute('aria-valuetext', '1 分')

    await page.evaluate(() => {
      window.OREPDemoState.dispatch({
        type: 'REQUEST_CHANGES',
        caseId: 'li-day4',
        payload: {
          scores: { structure: 80, troubleshooting: 80, evidence: 80, clarity: 80 },
          comment: '请补充失败尝试证据。',
          nextMove: '补齐截图后重新提交。',
          remediation: {
            issueType: '证据不足',
            evidenceLocation: '联调记录',
            expectedResult: '补充失败尝试截图',
            dueAt: '2026-07-19T18:00:00+08:00',
            reason: '当前证据链不完整',
          },
        },
      })
      window.OREPDemoState.dispatch({
        type: 'RESUBMIT',
        caseId: 'li-day4',
        payload: {
          note: '已补充截图。',
          changeSummary: '新增失败尝试截图。',
          artifacts: [],
        },
      })
    })
    expect(await queueOrder()).toEqual(['zhang-day4', 'li-day4', 'zhao-day1'])
    await page.locator('[data-review-filter-value="resubmitted"]').click()
    expect(await queueOrder()).toEqual(['li-day4'])
    expectNoRuntimeErrors(runtimeErrors)
  } finally {
    await page.evaluate(() => window.OREPDemoState.reset())
  }
})

test('审核响应断点边界恢复面板与教师营页面保持安全', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)

  await resetReview(page, { width: 1180, height: 800 })
  await expect(page.locator('#reviewDecisionPanel')).toBeVisible()
  await expect(page.locator('[data-review-decision-toggle]')).toBeHidden()

  await page.setViewportSize({ width: 1179, height: 800 })
  await expect(page.locator('#reviewDecisionPanel')).toBeHidden()
  await expect(page.locator('[data-review-decision-toggle]')).toBeVisible()
  expect(await page.locator('.tcore-review-rail').evaluate((rail) => (
    rail.getBoundingClientRect().width
  ))).toBe(72)
  expect(await page.locator('#teacherModuleList').evaluate((panel) => (
    getComputedStyle(panel).left
  ))).toBe('72px')

  await page.setViewportSize({ width: 900, height: 800 })
  expect(await page.locator('.tcore-review-rail').evaluate((rail) => (
    rail.getBoundingClientRect().width
  ))).toBe(72)
  await expect(page.locator('[data-review-pane-tabs]')).toBeHidden()

  await page.setViewportSize({ width: 899, height: 800 })
  expect(await page.locator('.tcore-review-rail').evaluate((rail) => (
    rail.getBoundingClientRect().width
  ))).toBe(64)
  await expect(page.locator('[data-review-pane-tabs]')).toBeVisible()
  await expect(page.locator('#reviewQueuePanel')).toBeVisible()
  await expect(page.locator('#reviewEvidencePanel')).toBeHidden()

  await page.setViewportSize({ width: 1180, height: 800 })
  for (const id of ['reviewQueuePanel', 'reviewEvidencePanel', 'reviewDecisionPanel']) {
    await expect(page.locator(`#${id}`)).toBeVisible()
    await expect(page.locator(`#${id}`)).not.toHaveAttribute('inert', '')
  }
  expect(await page.locator('.tcore-review-layout').evaluate((layout) => (
    Array.from(layout.children).map((child) => child.id)
  ))).toEqual(['reviewQueuePanel', 'reviewEvidencePanel', 'reviewDecisionPanel'])

  await page.goto('/teacher/camp.html')
  await expect(page.locator('body[data-teacher-page="camp"]')).toBeVisible()
  await expect(page.locator('main')).toBeVisible()
  expectNoRuntimeErrors(runtimeErrors)
})

test('审核质量壳层在 900 至 1023 与窄屏顶栏完整可见', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)

  for (const width of [1023, 900]) {
    await resetReview(page, { width, height: 800 })
    const geometry = await page.evaluate(() => {
      const main = document.querySelector('.tcore-review-main').getBoundingClientRect()
      const topbar = document.querySelector('.tcore-review-topbar').getBoundingClientRect()
      const heading = document.querySelector('.tcore-review h1').getBoundingClientRect()
      const rail = document.querySelector('.tcore-review-rail').getBoundingClientRect()
      return {
        main,
        topbar,
        heading,
        railWidth: rail.width,
        overflow: document.documentElement.scrollWidth - window.innerWidth,
      }
    })
    expect(geometry.heading.top).toBeGreaterThanOrEqual(0)
    expect(geometry.heading.bottom).toBeLessThanOrEqual(800)
    expect(geometry.main.top).toBeCloseTo(geometry.topbar.bottom, 0)
    expect(geometry.main.right).toBeLessThanOrEqual(width)
    expect(geometry.railWidth).toBe(72)
    expect(geometry.overflow).toBeLessThanOrEqual(1)
    await expect(page.locator('.tcore-review-main')).toBeVisible()
    await expect(page.locator('.tcore-review-topbar')).toBeVisible()
  }

  for (const width of [899, 390]) {
    await resetReview(page, { width, height: 844 })
    const search = page.getByRole('searchbox', { name: '搜索学生、任务或提交' })
    const portal = page.getByRole('link', { name: '切换门户' })
    const message = page.getByRole('button', { name: '消息' })
    for (const control of [search, portal, message]) {
      await expect(control).toBeVisible()
      const box = await control.boundingBox()
      expect(box.height).toBeGreaterThanOrEqual(40)
      expect(box.x).toBeGreaterThanOrEqual(0)
      expect(box.x + box.width).toBeLessThanOrEqual(width)
    }
    const actionsRight = await page.locator('.tcore-review-topbar .workspace-topbar__actions')
      .evaluate((actions) => actions.getBoundingClientRect().right)
    expect(actionsRight).toBeLessThanOrEqual(width)
  }
  expectNoRuntimeErrors(runtimeErrors)
})

test('审核确定性等待时钟与组合深链回写', async ({ page }) => {
  await page.addInitScript(() => {
    Date.now = () => new Date('2027-02-01T12:00:00+08:00').getTime()
  })
  const runtimeErrors = captureRuntimeErrors(page)
  await resetReview(page)

  try {
    await expect(page.locator('[data-review-case-id="zhang-day4"] .tcore-queue-item__meta'))
      .toContainText('已等待 38 分钟')
    await expect(page.locator('[data-review-case-id="zhao-day1"] .tcore-queue-item__meta'))
      .toContainText('已等待 1 小时')
    await expect(page.locator('[data-review-case-id="li-day4"] .tcore-queue-item__meta'))
      .toContainText('已等待 24 分钟')

    await page.goto('/teacher/review.html?filter=overdue&item=zhang-day4#queue')
    await expect(page.locator('[data-review-case-id="zhao-day1"]'))
      .toHaveAttribute('aria-current', 'true')
    expect(new URL(page.url()).searchParams.get('item')).toBe('zhao-day1')

    await page.goto('/teacher/review.html?filter=resubmitted&item=zhang-day4#queue')
    await expect(page.locator('[data-review-case-id]')).toHaveCount(0)
    expect(new URL(page.url()).searchParams.has('item')).toBe(false)
    expectNoRuntimeErrors(runtimeErrors)
  } finally {
    await page.evaluate(() => window.OREPDemoState.reset())
  }
})

test('审核侧栏鼠标关闭、触控对比与筛选单行契约', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)
  await resetReview(page, { width: 1024, height: 800 })

  const decisionToggle = page.locator('[data-review-decision-toggle]')
  await decisionToggle.click()
  const close = page.locator('[data-review-decision-close]')
  await expect(close).toBeVisible()
  const closeBox = await close.boundingBox()
  expect(closeBox.width).toBeGreaterThanOrEqual(40)
  expect(closeBox.height).toBeGreaterThanOrEqual(40)
  await close.click()
  await expect(page.locator('#reviewDecisionPanel')).toBeHidden()
  await expect(decisionToggle).toBeFocused()

  await page.setViewportSize({ width: 1280, height: 800 })
  await page.locator('[data-teacher-module-toggle]').click()
  expect((await page.locator('.tcore-review-rail .arch-rail__brand').boundingBox()).height)
    .toBeGreaterThanOrEqual(40)
  for (const link of await page.locator('#teacherModuleList .module-list__foot a').all()) {
    expect((await link.boundingBox()).height).toBeGreaterThanOrEqual(40)
  }
  expect(await contrastRatio(
    page.locator('#teacherModuleList .module-list__desc').first(),
    '#teacherModuleList',
  )).toBeGreaterThanOrEqual(4.5)
  expect(await contrastRatio(
    page.locator('[data-review-filter-value="first"]'),
    '.tcore-review-filters',
  )).toBeGreaterThanOrEqual(4.5)

  for (const width of [1512, 1280]) {
    await page.setViewportSize({ width, height: 800 })
    const firstReview = page.locator('[data-review-filter-value="first"]')
    expect(await firstReview.evaluate((button) => ({
      whiteSpace: getComputedStyle(button).whiteSpace,
      fits: button.scrollWidth <= button.clientWidth,
    }))).toEqual({ whiteSpace: 'nowrap', fits: true })
  }
  expectNoRuntimeErrors(runtimeErrors)
})

test('审核生命周期重复脚本与 BFCache 只保留一个订阅', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)
  await resetReview(page)

  try {
    await page.evaluate(() => {
      window.__reviewSubscribeCalls = 0
      const subscribe = window.OREPDemoState.subscribe
      window.OREPDemoState.subscribe = function countedSubscribe(listener) {
        window.__reviewSubscribeCalls += 1
        return subscribe.call(this, listener)
      }
    })
    await page.addScriptTag({ url: '/teacher/js/teacher-core.js' })
    expect(await page.evaluate(() => window.__reviewSubscribeCalls)).toBe(0)

    await page.evaluate(() => {
      window.dispatchEvent(new PageTransitionEvent('pagehide', { persisted: true }))
      window.OREPDemoState.dispatch({
        type: 'APPROVE',
        caseId: 'zhang-day4',
        payload: {
          scores: { structure: 88, troubleshooting: 84, evidence: 76, clarity: 82 },
          comment: '证据完整，可以通过。',
          nextMove: '整理为一分钟排障案例。',
        },
      })
    })
    await expect(page.locator('[data-review-queue-count]')).toHaveText('3')

    await page.evaluate(() => {
      window.dispatchEvent(new PageTransitionEvent('pageshow', { persisted: true }))
    })
    await expect(page.locator('[data-review-queue-count]')).toHaveText('2')
    await expect(page.locator('[data-review-case-id="zhao-day1"]'))
      .toHaveAttribute('aria-current', 'true')
    expect(await page.evaluate(() => window.__reviewSubscribeCalls)).toBe(1)
    expectNoRuntimeErrors(runtimeErrors)
  } finally {
    await page.evaluate(() => window.OREPDemoState.reset())
  }
})

test('审核模块栏底部链接同行且无分隔点', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)
  await resetReview(page, { width: 1512, height: 800 })

  const foot = page.locator('#teacherModuleList .module-list__foot')
  const links = foot.locator('a')
  await expect(links).toHaveCount(2)
  await expect(foot).not.toContainText('·')
  const boxes = await links.evaluateAll((items) => items.map((item) => {
    const rect = item.getBoundingClientRect()
    return { top: rect.top, height: rect.height }
  }))
  expect(Math.abs(boxes[0].top - boxes[1].top)).toBeLessThanOrEqual(1)
  expect(boxes.every((box) => box.height >= 40)).toBe(true)
  expectNoRuntimeErrors(runtimeErrors)
})

test('营看板初始渲染真实 8×21 语义矩阵与单一 roving 焦点', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)
  await resetCamp(page)

  try {
    const matrix = page.locator('table[data-camp-matrix]')
    await expect(matrix).toBeVisible()
    await expect(matrix.locator('caption')).toContainText('21 天金牌集训')
    await expect(matrix.locator('thead th[scope="col"][data-camp-day]')).toHaveCount(21)
    await expect(matrix.locator('tbody tr[data-camp-student-row]')).toHaveCount(8)
    await expect(matrix.locator('tbody th[scope="row"]')).toHaveCount(8)
    await expect(matrix.locator('button[data-camp-cell]')).toHaveCount(168)

    const zhangDay4 = matrix.locator('button[data-case-id="zhang-day4"]')
    await expect(zhangDay4).toHaveText(/\u5f85审核/)
    await expect(zhangDay4).toHaveAttribute('aria-label', /张志强 Day 4 待审核/)
    await expect(zhangDay4).toHaveAttribute('tabindex', '0')
    await expect(matrix.locator('button[data-camp-cell][tabindex="0"]')).toHaveCount(1)
    await expect(matrix.locator('button[data-camp-cell][tabindex="-1"]')).toHaveCount(167)

    const geometry = await page.evaluate(() => {
      const shell = document.querySelector('.tcore-matrix-shell')
      const tableHead = document.querySelector('table[data-camp-matrix] thead')
      const dayHeader = document.querySelector('[data-camp-day="4"]')
      const studentHeader = document.querySelector('tbody th[scope="row"]')
      return {
        shellScrollable: shell.scrollWidth > shell.clientWidth,
        shellOverflowX: getComputedStyle(shell).overflowX,
        tableHeadPosition: getComputedStyle(tableHead).position,
        dayHeaderPosition: getComputedStyle(dayHeader).position,
        studentHeaderPosition: getComputedStyle(studentHeader).position,
        documentOverflow: document.documentElement.scrollWidth - window.innerWidth,
      }
    })
    expect(geometry.shellScrollable).toBe(true)
    expect(geometry.shellOverflowX).toBe('auto')
    expect(geometry.tableHeadPosition).toBe('sticky')
    expect(geometry.dayHeaderPosition).toBe('sticky')
    expect(geometry.studentHeaderPosition).toBe('sticky')
    expect(geometry.documentOverflow).toBeLessThanOrEqual(1)
    expectNoRuntimeErrors(runtimeErrors)
  } finally {
    await page.evaluate(() => window.OREPDemoState.reset())
  }
})

test('营看板 roving 方向键与详情面板完整管理焦点', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)
  await resetCamp(page)

  try {
    const zhangDay4 = page.locator('button[data-case-id="zhang-day4"]')
    await zhangDay4.focus()
    await page.keyboard.press('ArrowRight')
    const zhangDay5 = page.locator('button[data-student-id="student-zhang"][data-day="5"]')
    await expect(zhangDay5).toBeFocused()
    await expect(zhangDay5).toHaveAttribute('tabindex', '0')
    await expect(zhangDay4).toHaveAttribute('tabindex', '-1')
    await page.keyboard.press('ArrowLeft')
    await expect(zhangDay4).toBeFocused()
    await page.keyboard.press('Enter')

    const detail = page.locator('#campDetailPanel[data-camp-detail]')
    const title = page.locator('#campDetailTitle')
    await expect(detail).toBeVisible()
    await expect(title).toBeFocused()
    await expect(detail).toContainText('张志强 · Day 4')
    await expect(detail).toContainText('待审核')
    await expect(detail).toContainText('3 份证据')
    await expect(detail).toContainText('第 1 轮')
    await expect(detail).toContainText(/等待老师反馈|最近反馈/)
    await expect(detail.getByRole('link', { name: '进入审核' }))
      .toBeVisible()
    await expect(detail.getByRole('link', { name: '进入审核' }))
      .toHaveAttribute('href', 'review.html?item=zhang-day4#queue')
    await expect(zhangDay4).toHaveAttribute('aria-controls', 'campDetailPanel')
    await expect(zhangDay4).toHaveAttribute('aria-expanded', 'true')

    const close = page.locator('[data-camp-detail-close]')
    const closeBox = await close.boundingBox()
    expect(closeBox.width).toBeGreaterThanOrEqual(40)
    expect(closeBox.height).toBeGreaterThanOrEqual(40)
    await page.keyboard.press('Escape')
    await expect(detail).toBeHidden()
    await expect(zhangDay4).toBeFocused()
    await expect(zhangDay4).toHaveAttribute('aria-expanded', 'false')

    await page.keyboard.press('Space')
    await expect(detail).toBeVisible()
    await close.click()
    await expect(detail).toBeHidden()
    await expect(zhangDay4).toBeFocused()

    await page.keyboard.press('Space')
    await expect(detail).toBeVisible()
    await page.locator('.tcore-camp-header').click({ position: { x: 8, y: 8 } })
    await expect(detail).toBeHidden()
    await expect(zhangDay4).not.toBeFocused()
    expectNoRuntimeErrors(runtimeErrors)
  } finally {
    await page.evaluate(() => window.OREPDemoState.reset())
  }
})

test('营看板鼠标打开格子时同步唯一 roving 格', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)
  await resetCamp(page)

  try {
    const zhangDay4 = page.locator('button[data-case-id="zhang-day4"]')
    const liDay4 = page.locator('button[data-case-id="li-day4"]')

    await expect(zhangDay4).toHaveAttribute('tabindex', '0')
    await liDay4.click()

    await expect(page.locator('#campDetailPanel')).toBeVisible()
    await expect(page.locator('#campDetailTitle')).toContainText('李晓萌 · Day 4')
    await expect(liDay4).toHaveAttribute('tabindex', '0')
    await expect(zhangDay4).toHaveAttribute('tabindex', '-1')
    await expect(page.locator('button[data-camp-cell][tabindex="0"]')).toHaveCount(1)
    expectNoRuntimeErrors(runtimeErrors)
  } finally {
    await page.evaluate(() => window.OREPDemoState.reset())
  }
})

test('营看板详情外点击保留新控件焦点', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)
  await resetCamp(page)

  try {
    const zhangDay4 = page.locator('button[data-case-id="zhang-day4"]')
    const search = page.locator('[data-camp-student-search]')
    const detail = page.locator('#campDetailPanel')

    await zhangDay4.click()
    await expect(detail).toBeVisible()
    await expect(page.locator('#campDetailTitle')).toBeFocused()

    await search.click()
    await expect(detail).toBeHidden()
    await expect(search).toBeFocused()
    expectNoRuntimeErrors(runtimeErrors)
  } finally {
    await page.evaluate(() => window.OREPDemoState.reset())
  }
})

test('营看板状态订阅重建矩阵后恢复同格焦点', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)
  await resetCamp(page)

  try {
    const zhangDay4 = page.locator('button[data-case-id="zhang-day4"]')
    await zhangDay4.focus()
    await expect(zhangDay4).toBeFocused()

    await approveCase(page, 'zhang-day4')

    await expect(zhangDay4).toContainText('已通过')
    await expect(zhangDay4).toBeFocused()
    await expect(zhangDay4).toHaveAttribute('tabindex', '0')
    await expect(page.locator('button[data-camp-cell][tabindex="0"]')).toHaveCount(1)
    expectNoRuntimeErrors(runtimeErrors)
  } finally {
    await page.evaluate(() => window.OREPDemoState.reset())
  }
})

test('营看板状态订阅筛掉聚焦格后转焦新 roving 格', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)
  await resetCamp(page)

  try {
    await page.locator('[data-camp-status-filter]').selectOption('PENDING_REVIEW')
    const zhangDay4 = page.locator('button[data-case-id="zhang-day4"]')
    await zhangDay4.focus()
    await expect(zhangDay4).toBeFocused()

    await approveCase(page, 'zhang-day4')

    await expect(zhangDay4).toHaveCount(0)
    const nextRoving = page.locator('button[data-camp-cell][tabindex="0"]')
    await expect(nextRoving).toHaveCount(1)
    await expect(nextRoving).toBeFocused()
    expectNoRuntimeErrors(runtimeErrors)
  } finally {
    await page.evaluate(() => window.OREPDemoState.reset())
  }
})

test('营看板小组状态搜索筛选保留 roving 并在空结果播报', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)
  await resetCamp(page)

  try {
    const team = page.locator('[data-camp-team-filter]')
    const status = page.locator('[data-camp-status-filter]')
    const search = page.locator('[data-camp-student-search]')
    const resultCount = page.locator('[data-camp-result-count]')
    await expect(search).toBeVisible()

    await team.selectOption('应用攻坚队')
    await expect(page.locator('tr[data-camp-student-row]')).toHaveCount(3)
    await expect(page.locator('tbody th[scope="row"]')).toHaveText(['张志强应用攻坚队', '李晓萌应用攻坚队', '赵丽颖应用攻坚队'])
    await expect(resultCount).toContainText('3 名学生')
    await expect(page.locator('button[data-case-id="zhang-day4"]')).toHaveAttribute('tabindex', '0')

    await team.selectOption('')
    await status.selectOption('PENDING_REVIEW')
    await expect(page.locator('tr[data-camp-student-row]')).toHaveCount(3)
    await expect(resultCount).toContainText('3 项待审核')

    await status.selectOption('')
    await search.fill('林诗雅')
    await expect(page.locator('tr[data-camp-student-row]')).toHaveCount(1)
    await expect(page.locator('tbody th[scope="row"]')).toContainText('林诗雅')
    await expect(page.locator('button[data-camp-cell][tabindex="0"]')).toHaveCount(1)
    await expect(page.locator('button[data-student-id="student-lin"][data-day="1"]'))
      .toHaveAttribute('tabindex', '0')

    await search.fill('不存在学生')
    await expect(page.locator('[data-camp-empty]')).toBeVisible()
    await expect(page.locator('[data-camp-empty]')).toContainText('没有找到')
    await expect(page.locator('table[data-camp-matrix]')).toBeHidden()
    await expect(search).toBeFocused()
    await expect(page.locator('[data-review-live]')).toContainText('没有匹配的学生')
    expectNoRuntimeErrors(runtimeErrors)
  } finally {
    await page.evaluate(() => window.OREPDemoState.reset())
  }
})

test('营看板订阅审核裁决并保持 AI 初评为无裁决演示辅助', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)
  await resetCamp(page)

  try {
    const zhangDay4 = page.locator('button[data-case-id="zhang-day4"]')
    await zhangDay4.click()
    await expect(page.locator('#campDetailPanel')).toBeVisible()
    await expect(page.locator('[data-camp-pending-count]')).toHaveText('3')
    await expect(page.locator('[data-camp-submission-rate]')).toContainText('63%')

    await page.evaluate(() => {
      window.__campDispatchCount = 0
      const dispatch = window.OREPDemoState.dispatch
      window.OREPDemoState.dispatch = function countedDispatch(action) {
        window.__campDispatchCount += 1
        return dispatch.call(this, action)
      }
    })
    await page.locator('[data-camp-ai-demo]').click()
    expect(await page.evaluate(() => window.__campDispatchCount)).toBe(0)
    await expect(page.locator('[data-review-live]')).toContainText('仅生成演示初评')
    expect(await page.evaluate(() => (
      window.OREPDemoState.selectCase(
        window.OREPDemoState.getState(),
        'zhang-day4',
      ).status
    ))).toBe('PENDING_REVIEW')

    await zhangDay4.click()
    await expect(page.locator('#campDetailPanel')).toBeVisible()
    await approveCase(page, 'zhang-day4')
    await expect(zhangDay4).toContainText('已通过')
    await expect(zhangDay4).toContainText('85')
    await expect(zhangDay4).toHaveAttribute('aria-label', /张志强 Day 4 已通过 85 分/)
    await expect(page.locator('[data-camp-pending-count]')).toHaveText('2')
    await expect(page.locator('[data-camp-summary-copy]')).toContainText('2 项待评')
    await expect(page.locator('#campDetailPanel')).toContainText('已通过')
    await expect(page.locator('#campDetailPanel')).toContainText('85 分')
    expectNoRuntimeErrors(runtimeErrors)
  } finally {
    await page.evaluate(() => window.OREPDemoState.reset())
  }
})

test('营看板窄屏只让矩阵容器横向滚动', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)
  await resetCamp(page, { width: 390, height: 844 })

  try {
    const geometry = await page.evaluate(() => {
      const shell = document.querySelector('.tcore-matrix-shell')
      const rail = document.querySelector('.arch-rail').getBoundingClientRect()
      return {
        railWidth: rail.width,
        shellScrollable: shell.scrollWidth > shell.clientWidth,
        shellRight: shell.getBoundingClientRect().right,
        documentOverflow: document.documentElement.scrollWidth - window.innerWidth,
      }
    })
    expect(geometry.railWidth).toBe(64)
    expect(geometry.shellScrollable).toBe(true)
    expect(geometry.shellRight).toBeLessThanOrEqual(390)
    expect(geometry.documentOverflow).toBeLessThanOrEqual(1)
    expectNoRuntimeErrors(runtimeErrors)
  } finally {
    await page.evaluate(() => window.OREPDemoState.reset())
  }
})

async function resetStudentPage(page, path, viewport = { width: 1512, height: 900 }) {
  await page.setViewportSize(viewport)
  await page.goto(path)
  await page.evaluate(() => window.OREPDemoState.reset())
  await page.reload()
}

test('学生端同步初始待评、教师通过与旧路演反馈互不覆盖', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)
  await resetStudentPage(page, '/user/index.html')

  try {
    await expect(page.locator('[data-student-day4-status]')).toHaveText('已提交，等待老师')
    await expect(page.locator('[data-student-primary-action]')).toContainText('查看今日提交')
    await expect(page.locator('[data-student-primary-action]')).toHaveAttribute('href', 'training-day.html')
    await expect(page.locator('[data-student-today-action]')).toContainText('查看提交')
    await expect(page.locator('[data-student-week-card]')).toContainText('待批改 · 今日 14:22 已提交')
    await expect(page.locator('[data-student-now-action]')).toContainText('今日成果已提交 · 待批改')
    await expect(page.locator('[data-student-day4-feedback]')).toHaveCount(0)

    const roadshowFeedback = page
      .getByRole('heading', { name: '上场反馈' })
      .locator('xpath=ancestor::section[1]')
    await expect(roadshowFeedback).toContainText('64/100')
    await expect(roadshowFeedback).toContainText('主线能跟上。路演时「创新成效」缺证据、结论钉不牢——再练时专门练口播结构。')
    await expect(roadshowFeedback).toContainText('下一刀 · 只盯这个')
    await expect(roadshowFeedback).toContainText('用 1 分钟讲清：问题 → 做法 → 数据/证据从哪来。')
    await expect(roadshowFeedback).toContainText('技能 72 · 素养 68 · 应用 78 · 团队 75 · 创新 55')
    await expect(roadshowFeedback.locator('a[href="review-report.html"]')).toHaveCount(2)

    await page.goto('/user/training-day.html')
    await expect(page.locator('[data-student-day4-status]')).toHaveText('待批改')
    const day4Action = page.locator('[data-student-day4-action]')
    await expect(day4Action).toBeDisabled()
    await expect(day4Action).toHaveText('已提交，等待批改')
    await expect(day4Action).not.toHaveAttribute('data-open-modal', /.+/)

    await approveCase(page, 'zhang-day4')

    await expect(page.locator('[data-student-day4-status]')).toHaveText('已通过')
    await expect(day4Action).toBeEnabled()
    await expect(day4Action).toHaveText('查看老师反馈')
    await expect(page.locator('[data-student-day4-feedback]')).toContainText('85')
    await expect(page.locator('[data-student-day4-feedback]')).toContainText('结构 88')
    await expect(page.locator('[data-student-day4-feedback]')).toContainText('排障 86')
    await expect(page.locator('[data-student-day4-feedback]')).toContainText('证据 82')
    await expect(page.locator('[data-student-day4-feedback]')).toContainText('表达 84')
    await expect(page.locator('[data-student-day4-feedback]')).toContainText('结构与排障路径完整，证据能够支撑结论，可以进入下一阶段训练。')
    await expect(page.locator('[data-student-day4-feedback]')).toContainText('整理本轮排障证据，并转化为路演中的一分钟案例说明。')
    await expect(page.locator('[data-student-day4-feedback]')).toContainText('第 1 轮')
    await expect(page.locator('[data-student-day4-feedback]')).toContainText('提交 Day 4 成果')
    await expect(page.locator('[data-student-day4-feedback]')).toContainText('老师评审通过')

    await day4Action.click()
    await expect(page.locator('#submitCampModal')).not.toHaveClass(/is-open/)
    await expect(page.locator('[data-student-day4-feedback]')).toBeFocused()

    await page.goto('/user/index.html')
    await expect(page.locator('[data-student-day4-status]')).toHaveText('已完成')
    await expect(page.locator('[data-student-primary-action]')).toContainText('去练一场路演')
    await expect(page.locator('[data-student-primary-action]')).toHaveAttribute('href', 'roadshow.html')
    await expect(page.locator('[data-student-today-action]')).toContainText('查看老师反馈')
    await expect(page.locator('[data-student-week-card]')).toContainText('已完成 · 本日已通过')
    await expect(page.locator('[data-student-now-action]')).toContainText('查看 Day 4 老师反馈 · 已完成')
    await expect(roadshowFeedback).toContainText('64/100')
    await expect(roadshowFeedback).toContainText('技能 72 · 素养 68 · 应用 78 · 团队 75 · 创新 55')
    expectNoRuntimeErrors(runtimeErrors)
  } finally {
    await page.evaluate(() => window.OREPDemoState.reset())
  }
})

test('学生重提表单两阶段校验成功后进入第 2 轮复审', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)
  await resetStudentPage(page, '/user/training-day.html')

  try {
    await requestChangesCase(page, 'zhang-day4')
    await expect(page.locator('[data-student-day4-status]')).toHaveText('待修改')
    const action = page.locator('[data-student-day4-action]')
    await expect(action).toHaveText('重新提交')
    await expect(action).toHaveAttribute('data-open-modal', 'submitCampModal')
    await action.click()

    const modal = page.locator('#submitCampModal')
    const note = page.locator('[data-student-resubmit-note]')
    const summary = page.locator('[data-student-resubmit-summary]')
    const confirm = page.locator('[data-student-resubmit]')
    const initialRevision = await page.evaluate(() => window.OREPDemoState.getState().revision)
    await expect(modal).toHaveClass(/is-open/)
    await expect(summary).toBeVisible()

    await confirm.click()
    await expect(modal).toHaveClass(/is-open/)
    await expect(note).toBeFocused()
    await expect(note).toHaveAttribute('aria-invalid', 'true')
    await expect(note).toHaveAttribute('aria-describedby', 'studentResubmitNoteError')
    await expect(page.locator('#studentResubmitNoteError')).toBeVisible()
    await expect(summary).toHaveAttribute('aria-invalid', 'true')
    expect(await page.evaluate(() => {
      const view = window.OREPDemoState.selectStudentDay4(
        window.OREPDemoState.getState(),
        'zhang-day4',
      )
      return {
        status: view.status,
        round: view.round,
        submissions: view.submissions.length,
        revision: window.OREPDemoState.getState().revision,
      }
    })).toEqual({
      status: 'CHANGES_REQUESTED',
      round: 1,
      submissions: 1,
      revision: initialRevision,
    })

    await note.fill('已按老师反馈补齐异常分支证据。')
    await confirm.click()
    await expect(modal).toHaveClass(/is-open/)
    await expect(summary).toBeFocused()
    await expect(note).not.toHaveAttribute('aria-invalid', 'true')
    await expect(summary).toHaveAttribute('aria-invalid', 'true')
    await expect(summary).toHaveAttribute('aria-describedby', 'studentResubmitSummaryError')

    await summary.fill('新增组件对应截图，并补充每条回滚条件。')
    await confirm.click()
    await expect(modal).not.toHaveClass(/is-open/)
    await expect(note).toHaveValue('')
    await expect(summary).toHaveValue('')
    await expect(page.locator('[data-student-day4-status]')).toHaveText('复审中')
    await expect(action).toBeDisabled()
    await expect(action).toHaveText('复审中')
    await expect(action).not.toHaveAttribute('data-open-modal', /.+/)
    expect(await page.evaluate(() => {
      const view = window.OREPDemoState.selectStudentDay4(
        window.OREPDemoState.getState(),
        'zhang-day4',
      )
      return {
        status: view.status,
        round: view.round,
        submissions: view.submissions.length,
        note: view.latestSubmission.note,
        changeSummary: view.latestSubmission.changeSummary,
      }
    })).toEqual({
      status: 'RESUBMITTED',
      round: 2,
      submissions: 2,
      note: '已按老师反馈补齐异常分支证据。',
      changeSummary: '新增组件对应截图，并补充每条回滚条件。',
    })

    const feedback = page.locator('[data-student-day4-feedback]')
    await expect(feedback).toContainText('复审中')
    await expect(feedback).toContainText('第 2 轮已送交复审')
    await expect(feedback.locator('.camp-feedback-version')).toContainText('第 2 轮')
    await expect(feedback.locator('.camp-feedback-version')).toContainText('2 次提交')
    await expect(feedback).toContainText('已按老师反馈补齐异常分支证据。')
    await expect(feedback).toContainText('新增组件对应截图，并补充每条回滚条件。')

    const previousRemediation = feedback.getByRole('region', { name: '上一轮整改要求' })
    await expect(previousRemediation).toBeVisible()
    await expect(previousRemediation.getByRole('heading', { name: '上一轮整改要求' })).toBeVisible()
    await expect(previousRemediation).toContainText('异常分支的证据还不够具体，请补齐组件对应关系后重新提交。')
    await expect(previousRemediation).toContainText('问题类型')
    await expect(previousRemediation).toContainText('证据不足')
    await expect(previousRemediation).toContainText('证据位置')
    await expect(previousRemediation).toContainText('排障清单第 3、4 条')
    await expect(previousRemediation).toContainText('期望结果')
    await expect(previousRemediation).toContainText('每条异常分支对应组件截图和可验证回滚条件')
    await expect(previousRemediation).toContainText('截止时间')
    await expect(previousRemediation).toContainText('今日 18:00')
    await expect(previousRemediation).toContainText('退回原因')
    await expect(previousRemediation).toContainText('当前清单不能复现异常分支的处置过程')
    await expect(previousRemediation).toContainText('下一刀')
    await expect(previousRemediation).toContainText('逐项标注异常现象、所属组件和可验证的回滚条件。')
    await expect(previousRemediation.locator('button, input, textarea, select')).toHaveCount(0)

    const timeline = feedback.locator('.camp-feedback-timeline')
    await expect(timeline).toContainText('提交 Day 4 成果')
    await expect(timeline).toContainText('老师退回修改')
    await expect(timeline).toContainText('重新提交第 2 轮成果')
    expectNoRuntimeErrors(runtimeErrors)
  } finally {
    await page.evaluate(() => window.OREPDemoState.reset())
  }
})

test('学生端同步保留完整 21 天预览并让 Day 4 读取当前状态', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)
  await resetStudentPage(page, '/user/training-day.html')

  try {
    const days = page.locator('.camp-day[data-day]')
    await expect(days).toHaveCount(21)
    for (const day of [1, 2, 3]) {
      await expect(page.locator(`.camp-day[data-day="${day}"] .camp-day__s`)).toHaveText('已完成')
    }
    await expect(page.locator('.camp-day[data-day="4"] .camp-day__s')).toHaveText('待批改')
    for (let day = 5; day <= 21; day += 1) {
      await expect(page.locator(`.camp-day[data-day="${day}"] .camp-day__s`)).toHaveText('未解锁')
    }

    await page.locator('.camp-day[data-day="1"]').click()
    await expect(page.locator('#dayPreviewModal')).toHaveClass(/is-open/)
    await expect(page.locator('#dayPreviewBody')).toContainText('该日已完成')
    await page.locator('#dayPreviewModal').getByRole('button', { name: '关闭' }).click()

    await page.locator('.camp-day[data-day="4"]').click()
    await expect(page.locator('#dayPreviewModal')).toHaveClass(/is-open/)
    await expect(page.locator('#dayPreviewBody')).toContainText('已提交，等待老师')
    await page.locator('#dayPreviewModal').getByRole('button', { name: '关闭' }).click()

    await page.locator('.camp-day[data-day="5"]').click()
    await expect(page.locator('#dayPreviewModal')).toHaveClass(/is-open/)
    await expect(page.locator('#dayPreviewBody')).toContainText('尚未解锁')
    expectNoRuntimeErrors(runtimeErrors)
  } finally {
    await page.evaluate(() => window.OREPDemoState.reset())
  }
})

for (const pageCase of [
  {
    name: '首页',
    path: '/user/index.html',
    lifecycle: '__OREPStudentHomeLifecycle',
    status: '[data-student-day4-status]',
    initial: '已提交，等待老师',
    passed: '已完成',
  },
  {
    name: '今日集训',
    path: '/user/training-day.html',
    lifecycle: '__OREPStudentTrainingDayLifecycle',
    status: '[data-student-day4-status]',
    initial: '待批改',
    passed: '已通过',
  },
]) {
  test(`学生端同步${pageCase.name}重复脚本与 BFCache 只保留一个订阅`, async ({ page }) => {
    const runtimeErrors = captureRuntimeErrors(page)
    await resetStudentPage(page, pageCase.path)

    try {
      await expect(page.locator(pageCase.status)).toHaveText(pageCase.initial)
      await page.evaluate(() => {
        window.__studentSubscribeCalls = 0
        const subscribe = window.OREPDemoState.subscribe
        window.OREPDemoState.subscribe = function countedSubscribe(listener) {
          window.__studentSubscribeCalls += 1
          return subscribe.call(this, listener)
        }
      })

      await page.addScriptTag({ url: '/user/js/student-demo-sync.js' })
      expect(await page.evaluate(() => window.__studentSubscribeCalls)).toBe(0)
      expect(await page.evaluate((lifecycleName) => (
        Boolean(window[lifecycleName] && window[lifecycleName].active)
      ), pageCase.lifecycle)).toBe(true)

      await page.evaluate(() => {
        window.dispatchEvent(new PageTransitionEvent('pagehide', { persisted: true }))
      })
      await approveCase(page, 'zhang-day4')
      await expect(page.locator(pageCase.status)).toHaveText(pageCase.initial)

      await page.evaluate(() => {
        window.dispatchEvent(new PageTransitionEvent('pageshow', { persisted: true }))
      })
      await expect(page.locator(pageCase.status)).toHaveText(pageCase.passed)
      expect(await page.evaluate(() => window.__studentSubscribeCalls)).toBe(1)
      expectNoRuntimeErrors(runtimeErrors)
    } finally {
      await page.evaluate(() => window.OREPDemoState.reset())
    }
  })
}

test('学生提交与日预览弹窗具备语义、焦点圈闭和统一焦点归还', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)
  await resetStudentPage(page, '/user/training-day.html')

  try {
    await requestChangesCase(page, 'zhang-day4')
    const action = page.locator('[data-student-day4-action]')
    const submitModal = page.locator('#submitCampModal')
    const note = page.locator('[data-student-resubmit-note]')
    const summary = page.locator('[data-student-resubmit-summary]')
    const confirm = page.locator('[data-student-resubmit]')
    const live = page.locator('[data-student-resubmit-live]')

    await expect(submitModal).toHaveAttribute('role', 'dialog')
    await expect(submitModal).toHaveAttribute('aria-modal', 'true')
    await expect(submitModal).toHaveAttribute('aria-labelledby', 'studentResubmitTitle')
    await expect(page.locator('#dayPreviewModal')).toHaveAttribute('role', 'dialog')
    await expect(page.locator('#dayPreviewModal')).toHaveAttribute('aria-modal', 'true')
    await expect(page.locator('#dayPreviewModal')).toHaveAttribute('aria-labelledby', 'dayPreviewTitle')

    await action.focus()
    await action.click()
    await expect(note).toBeFocused()
    await submitModal.getByRole('button', { name: '取消' }).click()
    await expect(submitModal).not.toHaveClass(/is-open/)
    await expect(action).toBeFocused()

    await action.click()
    await expect(note).toBeFocused()
    await confirm.focus()
    await page.keyboard.press('Tab')
    await expect(note).toBeFocused()
    await page.keyboard.press('Shift+Tab')
    await expect(confirm).toBeFocused()
    await page.keyboard.press('Escape')
    await expect(submitModal).not.toHaveClass(/is-open/)
    await expect(action).toBeFocused()

    await action.click()
    await expect(note).toBeFocused()
    await submitModal.click({ position: { x: 4, y: 4 } })
    await expect(submitModal).not.toHaveClass(/is-open/)
    await expect(action).toBeFocused()

    const dayOne = page.locator('.camp-day[data-day="1"]')
    await dayOne.click()
    await expect(page.locator('#dayPreviewTitle')).toBeFocused()
    await page.keyboard.press('Escape')
    await expect(page.locator('#dayPreviewModal')).not.toHaveClass(/is-open/)
    await expect(dayOne).toBeFocused()

    await action.click()
    await note.fill('已按老师反馈补齐异常分支证据。')
    await summary.fill('新增组件对应截图，并补充每条回滚条件。')
    await confirm.click()
    await expect(submitModal).not.toHaveClass(/is-open/)
    await expect(live).toBeVisible()
    await expect(live).toHaveText(/已重新提交并进入复审/)
    await expect(page.locator('[data-student-day4-feedback]')).toBeFocused()
    expectNoRuntimeErrors(runtimeErrors)
  } finally {
    await page.evaluate(() => window.OREPDemoState.reset())
  }
})

test('学生主行动颜色、首页四态尾标签与窄屏命中区符合可用性基线', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)
  await resetStudentPage(page, '/user/index.html', { width: 390, height: 844 })

  try {
    expect(await contrastRatio(page.locator('[data-student-primary-action]'))).toBeGreaterThanOrEqual(4.5)
    expect(await contrastRatio(page.locator('[data-student-today-action]'))).toBeGreaterThanOrEqual(4.5)

    const initialFooterTag = page.locator('[data-student-now-action] .hd-action__foot .hd-tag')
    await expect(initialFooterTag).toHaveText('待批改')
    const homeGeometry = await page.evaluate(() => ({
      primaryAction: (() => {
        const rect = document.querySelector('[data-student-primary-action]').getBoundingClientRect()
        return { left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom }
      })(),
      todayAction: (() => {
        const rect = document.querySelector('[data-student-today-action]').getBoundingClientRect()
        return {
          width: rect.width,
          height: rect.height,
          left: rect.left,
          right: rect.right,
          top: rect.top,
          bottom: rect.bottom,
        }
      })(),
      weekDays: Array.from(document.querySelectorAll('.hd-cal-day')).slice(0, 7).map((day) => {
        const rect = day.getBoundingClientRect()
        return { width: rect.width, height: rect.height }
      }),
      overflow: document.documentElement.scrollWidth - window.innerWidth,
    }))
    expect(homeGeometry.todayAction.width).toBeGreaterThanOrEqual(40)
    expect(homeGeometry.todayAction.height).toBeGreaterThanOrEqual(40)
    expect(homeGeometry.todayAction.left).toBeGreaterThanOrEqual(0)
    expect(homeGeometry.todayAction.right).toBeLessThanOrEqual(390)
    expect(homeGeometry.primaryAction.left).toBeGreaterThanOrEqual(0)
    expect(homeGeometry.primaryAction.right).toBeLessThanOrEqual(390)
    expect(homeGeometry.primaryAction.top).toBeGreaterThanOrEqual(0)
    expect(homeGeometry.primaryAction.bottom).toBeLessThanOrEqual(844)
    for (const day of homeGeometry.weekDays) {
      expect(day.width).toBeGreaterThanOrEqual(40)
      expect(day.height).toBeGreaterThanOrEqual(40)
    }
    expect(homeGeometry.overflow).toBeLessThanOrEqual(1)

    await approveCase(page, 'zhang-day4')
    await expect(initialFooterTag).toHaveText('已完成')
    await expect(initialFooterTag).toHaveClass(/is-ok/)

    await page.goto('/user/training-day.html')
    const trainingAction = page.locator('[data-student-day4-action]')
    await expect(trainingAction).toBeEnabled()
    expect(await contrastRatio(trainingAction)).toBeGreaterThanOrEqual(4.5)
    const trainingGeometry = await page.evaluate(() => {
      const actionRect = document.querySelector('[data-student-day4-action]').getBoundingClientRect()
      return {
        actionWidth: actionRect.width,
        actionHeight: actionRect.height,
        actionLeft: actionRect.left,
        actionRight: actionRect.right,
        actionTop: actionRect.top,
        actionBottom: actionRect.bottom,
        overflow: document.documentElement.scrollWidth - window.innerWidth,
      }
    })
    expect(trainingGeometry.actionWidth).toBeGreaterThanOrEqual(40)
    expect(trainingGeometry.actionHeight).toBeGreaterThanOrEqual(40)
    expect(trainingGeometry.actionLeft).toBeGreaterThanOrEqual(0)
    expect(trainingGeometry.actionRight).toBeLessThanOrEqual(390)
    expect(trainingGeometry.actionTop).toBeGreaterThanOrEqual(0)
    expect(trainingGeometry.actionBottom).toBeLessThanOrEqual(844)
    expect(trainingGeometry.overflow).toBeLessThanOrEqual(1)
    expectNoRuntimeErrors(runtimeErrors)
  } finally {
    await page.evaluate(() => window.OREPDemoState.reset())
  }
})

test('学生同步运行时首读、派生或订阅异常均单次告警并可原位恢复', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)
  await page.route('**/shared/demo-state.js', async (route) => {
    await route.fulfill({
      contentType: 'application/javascript',
      body: `
        (function () {
          var STATUS = {
            PENDING_REVIEW: 'PENDING_REVIEW',
            CHANGES_REQUESTED: 'CHANGES_REQUESTED',
            RESUBMITTED: 'RESUBMITTED',
            PASSED: 'PASSED'
          };
          var view = {
            status: STATUS.PENDING_REVIEW,
            round: 1,
            home: { ctaLabel: '查看今日提交', ctaHref: 'training-day.html', statusText: '已提交，等待老师' },
            today: { ctaLabel: '查看提交' },
            week: { statusText: '待批改' },
            now: { statusText: '今日成果已提交 · 待批改' }
          };
          window.__studentRuntimeFault = new URL(location.href).searchParams.get('fault') || '';
          window.__studentRuntimeSubscribeCalls = 0;
          window.OREPDemoState = {
            STATUS: STATUS,
            getState: function () {
              if (window.__studentRuntimeFault === 'getState') throw new Error('getState failed');
              return {};
            },
            selectStudentDay4: function () {
              if (window.__studentRuntimeFault === 'selectStudentDay4') throw new Error('select failed');
              return view;
            },
            subscribe: function () {
              if (window.__studentRuntimeFault === 'subscribe') throw new Error('subscribe failed');
              window.__studentRuntimeSubscribeCalls += 1;
              return function () {};
            }
          };
        }());
      `,
    })
  })

  for (const fault of ['getState', 'selectStudentDay4', 'subscribe']) {
    await page.goto(`/user/index.html?fault=${fault}`)
    await expect(page.locator('.student-demo-runtime-alert[role="alert"]')).toHaveCount(1)
    await expect(page.locator('.student-demo-runtime-alert[role="alert"]')).toContainText('暂不可用')
    expect(await page.evaluate(() => ({
      active: Boolean(window.__OREPStudentHomeLifecycle && window.__OREPStudentHomeLifecycle.active),
      failed: Boolean(window.__OREPStudentHomeLifecycle && window.__OREPStudentHomeLifecycle.failed),
      subscriptions: window.__studentRuntimeSubscribeCalls,
    }))).toEqual({ active: false, failed: true, subscriptions: 0 })

    await page.evaluate(() => {
      window.__studentRuntimeFault = ''
    })
    await page.addScriptTag({ url: '/user/js/student-demo-sync.js' })
    await expect(page.locator('[data-student-day4-status]')).toHaveText('已提交，等待老师')
    expect(await page.evaluate(() => ({
      active: window.__OREPStudentHomeLifecycle.active,
      failed: window.__OREPStudentHomeLifecycle.failed,
      subscriptions: window.__studentRuntimeSubscribeCalls,
      alerts: document.querySelectorAll('.student-demo-runtime-alert[role="alert"]').length,
    }))).toEqual({ active: true, failed: false, subscriptions: 1, alerts: 0 })
  }

  expectNoRuntimeErrors(runtimeErrors)
})

test('完整 UI 闭环：教师退回、学生重提、教师复审通过并三端同步', async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 1512, height: 900 } })
  const teacher = await context.newPage()
  const studentHome = await context.newPage()
  const studentTraining = await context.newPage()
  const runtimeErrors = [
    captureRuntimeErrors(teacher),
    captureRuntimeErrors(studentHome),
    captureRuntimeErrors(studentTraining),
  ]

  try {
    await teacher.goto('/teacher/review.html?item=zhang-day4#queue')
    await teacher.evaluate(() => window.OREPDemoState.reset())
    await teacher.reload()
    await studentHome.goto('/user/index.html')
    await studentTraining.goto('/user/training-day.html')

    await teacher.locator('[data-apply-ai]').click()
    await teacher.locator('[data-prepare-return]').click()
    await teacher.locator('[data-confirm-decision]').click()
    const decisionErrors = teacher.locator('[data-decision-errors][role="alert"]')
    await expect(decisionErrors.locator('li')).toHaveCount(5)
    await expect(teacher.locator('[data-remediation-field="issueType"]')).toBeFocused()
    expect(await teacher.evaluate(() => (
      window.OREPDemoState.selectCase(window.OREPDemoState.getState(), 'zhang-day4').status
    ))).toBe('PENDING_REVIEW')

    await teacher.locator('[data-remediation-field="issueType"]').selectOption('证据不足')
    await teacher.locator('[data-remediation-field="evidenceLocation"]').fill('排障清单第 3、4 条')
    await teacher.locator('[data-remediation-field="expectedResult"]')
      .fill('每条异常分支对应组件截图和可验证回滚条件')
    await teacher.locator('[data-remediation-field="dueAt"]').fill('2026-07-19T18:00')
    await teacher.locator('[data-remediation-field="reason"]')
      .fill('当前清单不能复现异常分支的处置过程')
    await teacher.locator('[data-confirm-decision]').click()

    await expect(teacher.locator('[data-review-queue-count]')).toHaveText('2')
    expect(await teacher.evaluate(() => {
      const state = window.OREPDemoState.getState()
      const summary = window.OREPDemoState.selectTeacherSummary(state)
      const reviewCase = window.OREPDemoState.selectCase(state, 'zhang-day4')
      return {
        status: reviewCase.status,
        pending: summary.pendingCount,
        changes: summary.changesRequestedCount,
      }
    })).toEqual({ status: 'CHANGES_REQUESTED', pending: 2, changes: 1 })

    await expect(studentHome.locator('[data-student-day4-status]')).toHaveText('老师已退回')
    await expect(studentHome.locator('[data-student-primary-action]')).toContainText('查看反馈并修改')
    const feedback = studentTraining.locator('[data-student-day4-feedback]')
    await expect(studentTraining.locator('[data-student-day4-status]')).toHaveText('待修改')
    await expect(feedback).toContainText('证据不足')
    await expect(feedback).toContainText('排障清单第 3、4 条')
    await expect(feedback).toContainText('每条异常分支对应组件截图和可验证回滚条件')
    await expect(feedback).toContainText('今日 18:00')
    await expect(feedback).toContainText('当前清单不能复现异常分支的处置过程')
    await expect(feedback).toContainText('可复现记录')

    await studentTraining.locator('[data-student-day4-action]').click()
    const note = studentTraining.locator('[data-student-resubmit-note]')
    const summary = studentTraining.locator('[data-student-resubmit-summary]')
    await studentTraining.locator('[data-student-resubmit]').click()
    await expect(note).toHaveAttribute('aria-invalid', 'true')
    await expect(summary).toHaveAttribute('aria-invalid', 'true')
    await note.fill('已按老师反馈补齐异常分支证据。')
    await summary.fill('新增组件对应截图，并补充每条回滚条件。')
    await studentTraining.locator('[data-student-resubmit]').click()

    expect(await studentTraining.evaluate(() => {
      const reviewCase = window.OREPDemoState.selectCase(
        window.OREPDemoState.getState(),
        'zhang-day4',
      )
      return {
        status: reviewCase.status,
        round: reviewCase.round,
        submissions: reviewCase.submissions.length,
      }
    })).toEqual({ status: 'RESUBMITTED', round: 2, submissions: 2 })

    await teacher.goto('/teacher/index.html')
    await expect(teacher.locator('[data-teacher-pending-count]')).toHaveText('3')
    await expect(teacher.locator('[data-teacher-review-round]')).toContainText('复审')
    await expect(teacher.locator('[data-teacher-progress-summary]')).toContainText('3 待评')
    await teacher.goto('/teacher/review.html?item=zhang-day4#queue')
    await teacher.locator('[data-review-filter-value="resubmitted"]').click()
    await expect(teacher.locator('[data-review-queue-count]')).toHaveText('1')
    await expect(teacher.locator('[data-review-case-id="zhang-day4"]')).toContainText('复审')
    await teacher.locator('[data-apply-ai]').click()
    await teacher.locator('[data-prepare-approve]').click()
    await teacher.locator('[data-confirm-decision]').click()

    expect(await teacher.evaluate(() => {
      const reviewCase = window.OREPDemoState.selectCase(
        window.OREPDemoState.getState(),
        'zhang-day4',
      )
      return {
        status: reviewCase.status,
        round: reviewCase.round,
        submissions: reviewCase.submissions.length,
        decisions: reviewCase.decisions.length,
      }
    })).toEqual({ status: 'PASSED', round: 2, submissions: 2, decisions: 2 })

    await expect(studentHome.locator('[data-student-day4-status]')).toHaveText('已完成')
    await expect(studentHome.locator('[data-student-primary-action]')).toContainText('去练一场路演')
    await expect(studentTraining.locator('[data-student-day4-status]')).toHaveText('已通过')
    await expect(studentTraining.locator('[data-student-day4-feedback]')).toContainText('第 2 轮')
    await expect(studentTraining.locator('[data-student-day4-feedback]')).toContainText('老师评分')
    runtimeErrors.forEach(expectNoRuntimeErrors)
  } finally {
    await context.close()
  }
})

test('审核脏草稿遇学生跨页重提时仅更新队列，显式加载后才覆盖表单', async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 1512, height: 900 } })
  const teacher = await context.newPage()
  const student = await context.newPage()
  const teacherErrors = captureRuntimeErrors(teacher)
  const studentErrors = captureRuntimeErrors(student)

  try {
    await teacher.goto('/teacher/review.html?item=zhang-day4#queue')
    await teacher.evaluate(() => window.OREPDemoState.reset())
    await teacher.reload()
    await student.goto('/user/training-day.html')

    await teacher.locator('[data-apply-ai]').click()
    await teacher.locator('[data-prepare-return]').click()
    await teacher.locator('[data-remediation-field="issueType"]').selectOption('证据不足')
    await teacher.locator('[data-remediation-field="evidenceLocation"]').fill('排障清单第 3、4 条')
    await teacher.locator('[data-remediation-field="expectedResult"]').fill('补齐异常分支证据')
    await teacher.locator('[data-remediation-field="dueAt"]').fill('2026-07-19T18:00')
    await teacher.locator('[data-remediation-field="reason"]').fill('当前证据不足以复现')
    await teacher.locator('[data-confirm-decision]').click()
    await expect(student.locator('[data-student-day4-status]')).toHaveText('待修改')

    await teacher.locator('[data-review-case-id="li-day4"]').click()
    await teacher.locator('[data-apply-ai]').click()
    await teacher.locator('[data-score-input="structure"]').fill('91')
    await teacher.locator('[data-teacher-comment]').fill('这是一份尚未发布的李思雨草稿。')
    await teacher.locator('[data-teacher-next-move]').fill('保留这一刀，等我确认。')
    await teacher.locator('[data-prepare-return]').click()
    await teacher.locator('[data-remediation-field="issueType"]').selectOption('表达不清')
    await teacher.locator('[data-remediation-field="evidenceLocation"]').fill('结构说明第 2 节')
    await teacher.locator('[data-remediation-field="expectedResult"]').fill('补一张调用关系图')
    await teacher.locator('[data-remediation-field="dueAt"]').fill('2026-07-20T12:00')
    await teacher.locator('[data-remediation-field="reason"]').fill('模块边界尚不清楚')

    await student.locator('[data-student-day4-action]').click()
    await student.locator('[data-student-resubmit-note]').fill('已补齐异常分支证据。')
    await student.locator('[data-student-resubmit-summary]').fill('新增截图与回滚条件。')
    await student.locator('[data-student-resubmit]').click()

    await expect(teacher.locator('[data-review-queue-count]')).toHaveText('3')
    await expect(teacher.locator('[data-review-case-id="li-day4"]')).toHaveAttribute('aria-current', 'true')
    await expect(teacher.locator('[data-score-input="structure"]')).toHaveValue('91')
    await expect(teacher.locator('[data-teacher-comment]')).toHaveValue('这是一份尚未发布的李思雨草稿。')
    await expect(teacher.locator('[data-teacher-next-move]')).toHaveValue('保留这一刀，等我确认。')
    await expect(teacher.locator('[data-remediation-field="reason"]')).toHaveValue('模块边界尚不清楚')

    const banner = teacher.locator('[data-external-update-banner]')
    await expect(banner).toBeVisible()
    await expect(banner).toContainText('另一页面')
    const loadLatest = banner.getByRole('button', { name: '加载最新状态' })
    await expect(loadLatest).toHaveCount(1)
    await expect(loadLatest).toHaveClass(/tcore-button/)
    await expect(loadLatest).toHaveClass(/tcore-button--secondary/)
    expect(await loadLatest.evaluate((button) => {
      const rect = button.getBoundingClientRect()
      return { width: rect.width, height: rect.height }
    })).toMatchObject({
      width: expect.any(Number),
      height: expect.any(Number),
    })
    expect(await loadLatest.evaluate((button) => button.getBoundingClientRect().width)).toBeGreaterThanOrEqual(40)
    expect(await loadLatest.evaluate((button) => button.getBoundingClientRect().height)).toBeGreaterThanOrEqual(40)

    await student.evaluate(() => {
      window.OREPDemoState.dispatch({
        type: 'REQUEST_CHANGES',
        caseId: 'zhao-day1',
        payload: {
          scores: { structure: 70, troubleshooting: 72, evidence: 68, clarity: 74 },
          comment: '请补充题意拆解证据。',
          nextMove: '逐条关联原题与实现。',
          remediation: {
            issueType: '证据不足',
            evidenceLocation: '题意拆解表',
            expectedResult: '每条约束对应实现位置',
            dueAt: '2026-07-20T12:00:00+08:00',
            reason: '当前无法验证边界条件',
          },
        },
      })
    })
    await expect(teacher.locator('[data-review-queue-count]')).toHaveText('2')
    await expect(banner.getByRole('button', { name: '加载最新状态' })).toHaveCount(1)
    await expect(teacher.locator('[data-teacher-comment]')).toHaveValue('这是一份尚未发布的李思雨草稿。')

    await loadLatest.click()
    await expect(banner).toBeHidden()
    await expect(teacher.locator('[data-review-case-id="li-day4"][aria-current="true"]')).toBeFocused()
    await expect(teacher).toHaveURL(/\/teacher\/review\.html\?item=li-day4#queue$/)
    await expect(teacher.locator('[data-score-input="structure"]')).toHaveValue('0')
    await expect(teacher.locator('[data-teacher-comment]')).toHaveValue('')
    await expect(teacher.locator('[data-remediation-field]')).toHaveCount(0)

    await teacher.locator('[data-teacher-comment]').fill('切筛选前的临时内容')
    await teacher.locator('[data-review-filter-value="resubmitted"]').click()
    await expect(banner).toBeHidden()
    await expect(teacher.locator('[data-review-case-id]')).toHaveCount(1)
    await expect(teacher.locator('[data-review-case-id="zhang-day4"]')).toHaveAttribute('aria-current', 'true')
    await expect(teacher.locator('[data-teacher-comment]')).toHaveValue('')

    await teacher.locator('[data-teacher-comment]').fill('队列清空前的临时内容')
    await approveCase(student, 'zhang-day4')
    await expect(teacher.locator('[data-review-case-id]')).toHaveCount(0)
    await expect(banner).toBeVisible()
    await banner.getByRole('button', { name: '加载最新状态' }).click()
    await expect(banner).toBeHidden()
    await expect(teacher.locator('[data-review-filter-value="resubmitted"]')).toBeFocused()
    await expect(teacher).toHaveURL(/\/teacher\/review\.html\?filter=resubmitted#queue$/)
    expect(await teacher.evaluate(() => {
      const active = document.activeElement
      return Boolean(active && !active.hidden && active.getClientRects().length)
    })).toBe(true)
    expectNoRuntimeErrors(teacherErrors)
    expectNoRuntimeErrors(studentErrors)
  } finally {
    await context.close()
  }
})

test('移动审核空队列加载最新状态后切回队列面板并聚焦可见筛选', async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 } })
  const teacher = await context.newPage()
  const external = await context.newPage()
  const teacherErrors = captureRuntimeErrors(teacher)
  const externalErrors = captureRuntimeErrors(external)

  try {
    await teacher.goto('/teacher/review.html?item=zhang-day4#queue')
    await teacher.evaluate(() => window.OREPDemoState.reset())
    await teacher.reload()
    await external.goto('/portals.html')

    const queueTab = teacher.locator('#reviewQueueTab')
    const decisionTab = teacher.locator('#reviewDecisionTab')
    const queuePanel = teacher.locator('#reviewQueuePanel')
    const decisionPanel = teacher.locator('#reviewDecisionPanel')
    await decisionTab.click()
    await expect(decisionTab).toHaveAttribute('aria-selected', 'true')
    await expect(decisionPanel).toBeVisible()
    await expect(queuePanel).toBeHidden()
    await expect(queuePanel).toHaveAttribute('inert', '')
    await teacher.locator('[data-teacher-comment]').fill('移动端空队列前保留的脏草稿')

    for (const caseId of ['zhang-day4', 'li-day4', 'zhao-day1']) {
      await approveCase(external, caseId)
    }

    await expect(teacher.locator('[data-review-case-id]')).toHaveCount(0)
    const banner = teacher.locator('[data-external-update-banner]')
    const loadLatest = banner.getByRole('button', { name: '加载最新状态' })
    await expect(banner).toBeVisible()
    await loadLatest.click()

    await expect(banner).toBeHidden()
    await expect(teacher).toHaveURL(/\/teacher\/review\.html#queue$/)
    await expect(teacher.locator('[data-review-queue-count]')).toHaveText('0')
    await expect(queueTab).toHaveAttribute('aria-selected', 'true')
    await expect(queueTab).toHaveAttribute('tabindex', '0')
    await expect(decisionTab).toHaveAttribute('aria-selected', 'false')
    await expect(decisionTab).toHaveAttribute('tabindex', '-1')
    await expect(queuePanel).toBeVisible()
    await expect(queuePanel).not.toHaveAttribute('inert', '')
    await expect(decisionPanel).toBeHidden()
    await expect(decisionPanel).toHaveAttribute('inert', '')
    const activeFilter = teacher.locator('[data-review-filter-value="all"]')
    await expect(activeFilter).toBeFocused()
    expect(await teacher.evaluate(() => (
      !document.activeElement.hasAttribute('data-load-latest-review')
    ))).toBe(true)
    expect(await activeFilter.evaluate((filter) => (
      filter.getClientRects().length > 0 && !filter.closest('[hidden], [inert]')
    ))).toBe(true)
    expectNoRuntimeErrors(teacherErrors)
    expectNoRuntimeErrors(externalErrors)
  } finally {
    await context.close()
  }
})

test('审核 BFCache 恢复时 revision 已变化则保留脏草稿并提示加载', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)
  await resetReview(page)

  try {
    await page.locator('[data-apply-ai]').click()
    await page.locator('[data-teacher-comment]').fill('BFCache 中也不能被覆盖的草稿')
    await page.evaluate(() => {
      window.dispatchEvent(new PageTransitionEvent('pagehide', { persisted: true }))
      window.OREPDemoState.dispatch({
        type: 'APPROVE',
        caseId: 'zhao-day1',
        payload: {
          scores: { structure: 80, troubleshooting: 82, evidence: 78, clarity: 84 },
          comment: '题意拆解已足够清楚。',
          nextMove: '继续验证边界条件。',
        },
      })
      window.dispatchEvent(new PageTransitionEvent('pageshow', { persisted: true }))
    })

    await expect(page.locator('[data-review-queue-count]')).toHaveText('2')
    await expect(page.locator('[data-teacher-comment]')).toHaveValue('BFCache 中也不能被覆盖的草稿')
    const banner = page.locator('[data-external-update-banner]')
    await expect(banner).toBeVisible()
    await expect(banner.getByRole('button', { name: '加载最新状态' })).toHaveCount(1)
    await banner.getByRole('button', { name: '加载最新状态' }).click()
    await expect(page.locator('[data-teacher-comment]')).toHaveValue('')
    await expect(banner).toBeHidden()
    expectNoRuntimeErrors(runtimeErrors)
  } finally {
    await page.evaluate(() => window.OREPDemoState.reset())
  }
})

for (const recoveryCase of [
  {
    name: '教师审核',
    path: '/teacher/review.html?item=zhang-day4#queue',
    lifecycle: '__OREPTeacherReviewLifecycle',
  },
  {
    name: '学生首页',
    path: '/user/index.html',
    lifecycle: '__OREPStudentHomeLifecycle',
  },
  {
    name: '学生今日集训',
    path: '/user/training-day.html',
    lifecycle: '__OREPStudentTrainingDayLifecycle',
  },
]) {
  test(`${recoveryCase.name}损坏演示数据后只 toast 一次恢复通知`, async ({ browser }) => {
    const context = await browser.newContext()
    const page = await context.newPage()
    const runtimeErrors = captureRuntimeErrors(page)

    try {
      await page.goto('/portals.html')
      await page.evaluate(() => {
        localStorage.setItem('orep-hifi-teacher-review-loop:v1', '{not-json')
      })
      await page.goto(recoveryCase.path)
      expect(await page.evaluate((lifecycleName) => (
        Boolean(window[lifecycleName] && window[lifecycleName].active)
      ), recoveryCase.lifecycle)).toBe(true)
      await expect(page.locator('.toast')).toHaveText('演示数据已恢复')
      await page.reload()
      await expect(page.locator('.toast')).toHaveText('')
      expectNoRuntimeErrors(runtimeErrors)
    } finally {
      await context.close()
    }
  })
}

test('教师持久化失败仍完成内存裁决并显示统一临时状态警告', async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 1512, height: 900 } })
  const page = await context.newPage()
  const runtimeErrors = captureRuntimeErrors(page)

  try {
    await page.goto('/teacher/review.html?item=zhang-day4#queue')
    await page.evaluate(() => window.OREPDemoState.reset())
    await page.reload()
    await page.evaluate(() => {
      const original = Storage.prototype.setItem
      window.__restoreStorageSetItem = () => {
        Storage.prototype.setItem = original
      }
      Storage.prototype.setItem = function failDemoStateWrite(key, value) {
        if (key === 'orep-hifi-teacher-review-loop:v1') throw new Error('quota exceeded')
        return original.call(this, key, value)
      }
    })

    await page.locator('[data-apply-ai]').click()
    await page.locator('[data-prepare-approve]').click()
    await page.locator('[data-confirm-decision]').click()
    await expect(page.locator('.toast')).toHaveText('当前为临时演示状态，刷新后可能丢失')
    expect(await page.evaluate(() => (
      window.OREPDemoState.selectCase(window.OREPDemoState.getState(), 'zhang-day4').status
    ))).toBe('PASSED')

    await page.evaluate(() => window.__restoreStorageSetItem())
    await page.reload()
    expect(await page.evaluate(() => (
      window.OREPDemoState.selectCase(window.OREPDemoState.getState(), 'zhang-day4').status
    ))).toBe('PENDING_REVIEW')
    expectNoRuntimeErrors(runtimeErrors)
  } finally {
    await context.close()
  }
})

test('学生重提持久化失败仍更新内存并显示统一临时状态警告', async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 1512, height: 900 } })
  const page = await context.newPage()
  const runtimeErrors = captureRuntimeErrors(page)

  try {
    await page.goto('/user/training-day.html')
    await page.evaluate(() => window.OREPDemoState.reset())
    await requestChangesCase(page, 'zhang-day4')
    await page.evaluate(() => {
      const original = Storage.prototype.setItem
      window.__restoreStorageSetItem = () => {
        Storage.prototype.setItem = original
      }
      Storage.prototype.setItem = function failDemoStateWrite(key, value) {
        if (key === 'orep-hifi-teacher-review-loop:v1') throw new Error('quota exceeded')
        return original.call(this, key, value)
      }
    })

    await page.locator('[data-student-day4-action]').click()
    await page.locator('[data-student-resubmit-note]').fill('已补齐异常分支证据。')
    await page.locator('[data-student-resubmit-summary]').fill('新增截图与回滚条件。')
    await page.locator('[data-student-resubmit]').click()
    await expect(page.locator('.toast')).toHaveText('当前为临时演示状态，刷新后可能丢失')
    expect(await page.evaluate(() => {
      const view = window.OREPDemoState.selectStudentDay4(
        window.OREPDemoState.getState(),
        'zhang-day4',
      )
      return { status: view.status, round: view.round, submissions: view.submissions.length }
    })).toEqual({ status: 'RESUBMITTED', round: 2, submissions: 2 })

    await page.evaluate(() => window.__restoreStorageSetItem())
    await page.reload()
    expect(await page.evaluate(() => {
      const view = window.OREPDemoState.selectStudentDay4(
        window.OREPDemoState.getState(),
        'zhang-day4',
      )
      return { status: view.status, round: view.round, submissions: view.submissions.length }
    })).toEqual({ status: 'CHANGES_REQUESTED', round: 1, submissions: 1 })
    expectNoRuntimeErrors(runtimeErrors)
  } finally {
    await context.close()
  }
})

test('门户演示重置经二次确认后跨页恢复初态并保留无关本地键', async ({ browser }) => {
  const context = await browser.newContext({ viewport: { width: 1280, height: 800 } })
  const teacher = await context.newPage()
  const student = await context.newPage()
  const portal = await context.newPage()
  const runtimeErrors = [
    captureRuntimeErrors(teacher),
    captureRuntimeErrors(student),
    captureRuntimeErrors(portal),
  ]

  try {
    await teacher.goto('/teacher/review.html?item=zhang-day4#queue')
    await teacher.evaluate(() => window.OREPDemoState.reset())
    await teacher.reload()
    await student.goto('/user/training-day.html')
    await teacher.locator('[data-apply-ai]').click()
    await teacher.locator('[data-prepare-approve]').click()
    await teacher.locator('[data-confirm-decision]').click()
    await expect(teacher.locator('[data-review-queue-count]')).toHaveText('2')
    await expect(student.locator('[data-student-day4-status]')).toHaveText('已通过')

    await portal.goto('/portals.html')
    await portal.evaluate(() => {
      localStorage.setItem('orep-demo-state', 'empty')
      localStorage.setItem('orep-role', 'teacher')
      localStorage.setItem('orep-reset-sentinel', 'keep-me')
      window.__portalResetCount = 0
      const reset = window.OREPDemoState.reset
      window.OREPDemoState.reset = function countedReset() {
        window.__portalResetCount += 1
        return reset.call(this)
      }
    })

    const opener = portal.locator('[data-demo-reset]')
    const modal = portal.locator('#demoResetModal')
    const cancel = portal.locator('[data-demo-reset-cancel]')
    const confirm = portal.locator('[data-demo-reset-confirm]')
    await expect(modal).toBeHidden()
    await expect(modal).toHaveAttribute('inert', '')

    await opener.click()
    await expect(modal).toBeVisible()
    await expect(cancel).toBeFocused()
    await cancel.click()
    await expect(modal).toBeHidden()
    await expect(opener).toBeFocused()
    expect(await portal.evaluate(() => window.__portalResetCount)).toBe(0)

    await opener.click()
    await portal.keyboard.press('Escape')
    await expect(modal).toBeHidden()
    await expect(opener).toBeFocused()
    expect(await portal.evaluate(() => window.__portalResetCount)).toBe(0)

    await opener.click()
    await modal.click({ position: { x: 4, y: 4 } })
    await expect(modal).toBeHidden()
    await expect(opener).toBeFocused()
    expect(await portal.evaluate(() => window.__portalResetCount)).toBe(0)

    await opener.click()
    await cancel.focus()
    await portal.keyboard.press('Shift+Tab')
    await expect(confirm).toBeFocused()
    await portal.keyboard.press('Tab')
    await expect(cancel).toBeFocused()
    const persistentRevisionBeforeReset = await portal.evaluate(() => (
      window.OREPDemoState.getState().revision
    ))
    await confirm.evaluate((button) => {
      button.click()
      button.click()
    })

    await expect(modal).toBeHidden()
    await expect(opener).toBeFocused()
    await expect(portal.locator('.toast')).toHaveText('演示数据已恢复到初始状态')
    expect(await portal.evaluate(() => window.__portalResetCount)).toBe(1)
    expect(await portal.evaluate(() => window.OREPDemoState.getState().revision))
      .toBe(persistentRevisionBeforeReset + 1)
    await expect(teacher.locator('[data-review-queue-count]')).toHaveText('3')
    await expect(student.locator('[data-student-day4-status]')).toHaveText('待批改')
    expect(await portal.evaluate(() => {
      const reviewCase = window.OREPDemoState.selectCase(
        window.OREPDemoState.getState(),
        'zhang-day4',
      )
      return {
        status: reviewCase.status,
        demoState: localStorage.getItem('orep-demo-state'),
        role: localStorage.getItem('orep-role'),
        sentinel: localStorage.getItem('orep-reset-sentinel'),
        stateKeyPresent: localStorage.getItem('orep-hifi-teacher-review-loop:v1') !== null,
      }
    })).toEqual({
      status: 'PENDING_REVIEW',
      demoState: 'empty',
      role: 'teacher',
      sentinel: 'keep-me',
      stateKeyPresent: true,
    })

    await approveCase(teacher, 'zhang-day4')
    await expect(student.locator('[data-student-day4-status]')).toHaveText('已通过')
    await expect.poll(async () => portal.evaluate(() => (
      window.OREPDemoState.selectCase(
        window.OREPDemoState.getState(),
        'zhang-day4',
      ).status
    ))).toBe('PASSED')
    await portal.evaluate(() => {
      const original = Storage.prototype.setItem
      window.__restorePortalStorageSetItem = () => {
        Storage.prototype.setItem = original
      }
      Storage.prototype.setItem = function failDemoStateWrite(key, value) {
        if (key === 'orep-hifi-teacher-review-loop:v1') throw new Error('quota exceeded')
        return original.call(this, key, value)
      }
    })

    const temporaryRevisionBeforeReset = await portal.evaluate(() => (
      window.OREPDemoState.getState().revision
    ))
    await opener.click()
    await expect(confirm).toBeEnabled()
    await confirm.evaluate((button) => {
      button.click()
      button.click()
    })
    await expect(modal).toBeHidden()
    await expect(opener).toBeFocused()
    await expect(portal.locator('.toast'))
      .toHaveText('当前为临时演示状态，刷新后可能丢失')
    expect(await portal.evaluate(() => window.__portalResetCount)).toBe(2)
    expect(await portal.evaluate(() => window.OREPDemoState.getState().revision))
      .toBe(temporaryRevisionBeforeReset + 1)
    expect(await portal.evaluate(() => (
      window.OREPDemoState.selectCase(
        window.OREPDemoState.getState(),
        'zhang-day4',
      ).status
    ))).toBe('PENDING_REVIEW')

    await portal.evaluate(() => window.__restorePortalStorageSetItem())
    await portal.reload()
    expect(await portal.evaluate(() => (
      window.OREPDemoState.selectCase(
        window.OREPDemoState.getState(),
        'zhang-day4',
      ).status
    ))).toBe('PASSED')

    await portal.evaluate(() => {
      window.__portalThrowResetCount = 0
      window.__portalThrowRevision = window.OREPDemoState.getState().revision
      window.OREPDemoState.reset = function throwingReset() {
        window.__portalThrowResetCount += 1
        throw new Error('reset unavailable')
      }
    })
    await opener.click()
    await expect(confirm).toBeEnabled()
    await confirm.evaluate((button) => {
      button.click()
      button.click()
    })
    await expect(modal).toBeHidden()
    await expect(opener).toBeFocused()
    await expect(portal.locator('.toast')).toHaveText('恢复失败，请稍后重试')
    expect(await portal.evaluate(() => ({
      calls: window.__portalThrowResetCount,
      revision: window.OREPDemoState.getState().revision,
      revisionBefore: window.__portalThrowRevision,
    }))).toEqual({
      calls: 1,
      revision: await portal.evaluate(() => window.__portalThrowRevision),
      revisionBefore: await portal.evaluate(() => window.__portalThrowRevision),
    })
    await opener.click()
    await expect(confirm).toBeEnabled()
    await cancel.click()
    await expect(opener).toBeFocused()
    runtimeErrors.forEach(expectNoRuntimeErrors)
  } finally {
    await context.close()
  }
})

test('响应式与键盘：四档标杆页布局安全且主行动可达', async ({ page }) => {
  test.setTimeout(120_000)
  const runtimeErrors = captureRuntimeErrors(page)
  const viewports = [
    { width: 1512, height: 744, suffix: '1512' },
    { width: 1280, height: 800, suffix: '1280' },
    { width: 1024, height: 768, suffix: '1024' },
    { width: 390, height: 844, suffix: 'mobile' },
  ]

  await page.goto('/teacher/index.html')
  await page.evaluate(() => window.OREPDemoState.reset())

  try {
    for (const viewport of viewports) {
      await page.setViewportSize(viewport)

      await page.goto('/teacher/index.html')
      await expect(page.locator('.module-list')).toHaveCount(0)
      const dashboardGeometry = await page.evaluate(() => {
        const controls = Array.from(document.querySelectorAll(
          '.tcore-dashboard-topbar input, .tcore-dashboard-topbar a, .tcore-dashboard-topbar button',
        )).filter((element) => {
          const style = getComputedStyle(element)
          return style.display !== 'none' && style.visibility !== 'hidden'
        }).map((element) => {
          const rect = element.getBoundingClientRect()
          return { left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom }
        })
        return {
          overflow: document.documentElement.scrollWidth - window.innerWidth,
          controls,
        }
      })
      expect(dashboardGeometry.overflow).toBeLessThanOrEqual(1)
      expect(dashboardGeometry.controls.length).toBeGreaterThanOrEqual(2)
      expect(dashboardGeometry.controls.every((rect) => (
        rect.left >= 0
        && rect.right <= viewport.width
        && rect.top >= 0
        && rect.bottom <= viewport.height
      ))).toBe(true)
      await expect(page.locator('[data-teacher-primary-action]')).toBeVisible()
      if (viewport.width === 1512) {
        await page.screenshot({ path: 'test-results/hifi-teacher-dashboard-1512.png', fullPage: true })
      }
      if (viewport.width === 390) {
        await page.screenshot({ path: 'test-results/hifi-teacher-dashboard-mobile.png', fullPage: true })
      }

      await page.goto('/teacher/review.html?item=zhang-day4#queue')
      expect(await page.evaluate(() => (
        document.documentElement.scrollWidth - window.innerWidth
      ))).toBeLessThanOrEqual(1)
      const moduleList = page.locator('#teacherModuleList')
      const queuePanel = page.locator('#reviewQueuePanel')
      const evidencePanel = page.locator('#reviewEvidencePanel')
      const decisionPanel = page.locator('#reviewDecisionPanel')
      if (viewport.width >= 1440) {
        await expect(moduleList).toBeVisible()
        await expect(queuePanel).toBeVisible()
        await expect(evidencePanel).toBeVisible()
        await expect(decisionPanel).toBeVisible()
      } else if (viewport.width >= 1180) {
        await expect(moduleList).toBeHidden()
        await expect(page.locator('[data-teacher-module-toggle]')).toBeVisible()
        await expect(queuePanel).toBeVisible()
        await expect(evidencePanel).toBeVisible()
        await expect(decisionPanel).toBeVisible()
      } else if (viewport.width >= 900) {
        await expect(queuePanel).toBeVisible()
        await expect(evidencePanel).toBeVisible()
        await expect(decisionPanel).toBeHidden()
        await expect(page.locator('[data-review-decision-toggle]')).toBeVisible()
      } else {
        await expect(page.locator('[data-review-pane-tabs]')).toBeVisible()
        await expect(queuePanel).toBeVisible()
        await expect(evidencePanel).toBeHidden()
        await expect(decisionPanel).toBeHidden()
      }
      if (viewport.width === 1512) {
        await page.screenshot({ path: 'test-results/hifi-teacher-review-1512.png', fullPage: true })
      } else if (viewport.width === 1280) {
        await page.screenshot({ path: 'test-results/hifi-teacher-review-1280.png', fullPage: true })
      } else if (viewport.width === 1024) {
        await page.locator('[data-review-decision-toggle]').click()
        await page.screenshot({ path: 'test-results/hifi-teacher-review-1024-decision-open.png', fullPage: true })
        await page.keyboard.press('Escape')
      } else {
        await page.screenshot({ path: 'test-results/hifi-teacher-review-mobile.png', fullPage: true })
      }

      await page.goto('/teacher/camp.html')
      const campGeometry = await page.evaluate(() => {
        const matrix = document.querySelector('.tcore-matrix-shell')
        return {
          overflow: document.documentElement.scrollWidth - window.innerWidth,
          matrixOwnScroll: matrix.scrollWidth > matrix.clientWidth,
          matrixRight: matrix.getBoundingClientRect().right,
        }
      })
      expect(campGeometry.overflow).toBeLessThanOrEqual(1)
      expect(campGeometry.matrixOwnScroll).toBe(true)
      expect(campGeometry.matrixRight).toBeLessThanOrEqual(viewport.width)
      await expect(page.locator('.tcore-camp-header__actions .tcore-button--primary')).toBeVisible()
      if (viewport.width === 1512) {
        await page.screenshot({ path: 'test-results/hifi-teacher-camp-1512.png', fullPage: true })
      } else if (viewport.width === 390) {
        await page.locator('.tcore-matrix-shell').scrollIntoViewIfNeeded()
        await page.screenshot({ path: 'test-results/hifi-teacher-camp-mobile-matrix.png', fullPage: true })
      }

      await requestChangesCase(page, 'zhang-day4')
      await page.goto('/user/training-day.html')
      expect(await page.evaluate(() => (
        document.documentElement.scrollWidth - window.innerWidth
      ))).toBeLessThanOrEqual(1)
      const feedback = page.locator('[data-student-day4-feedback]')
      await expect(feedback).toContainText('待修改')
      await expect(feedback).toContainText('老师退回修改')
      await expect(feedback).toBeAttached()
      if (viewport.width === 1512) {
        await feedback.scrollIntoViewIfNeeded()
        await page.screenshot({ path: 'test-results/hifi-student-returned-1512.png', fullPage: true })
      } else if (viewport.width === 390) {
        await feedback.scrollIntoViewIfNeeded()
        await page.screenshot({ path: 'test-results/hifi-student-returned-mobile-feedback.png', fullPage: true })
      }
      await page.evaluate(() => window.OREPDemoState.reset())
    }
    expectNoRuntimeErrors(runtimeErrors)
  } finally {
    await page.evaluate(() => window.OREPDemoState.reset())
  }
})

test('响应式与键盘：审核页签、评分与退回确认焦点连续', async ({ page }) => {
  const runtimeErrors = captureRuntimeErrors(page)
  await resetReview(page, { width: 390, height: 844 })

  const tabs = page.locator('[data-review-pane-tabs] [role="tab"]')
  await tabs.nth(0).focus()
  await page.keyboard.press('End')
  await expect(tabs.nth(2)).toBeFocused()
  await expect(tabs.nth(2)).toHaveAttribute('aria-selected', 'true')
  await expect(page.locator('#reviewQueuePanel')).toHaveAttribute('inert', '')
  await expect(page.locator('#reviewEvidencePanel')).toHaveAttribute('inert', '')

  const score = page.locator('[data-score-input="structure"]')
  const output = page.locator('[data-score-output="structure"]')
  await score.focus()
  await page.keyboard.press('ArrowRight')
  await expect(score).toHaveValue('1')
  await expect(output).toHaveText('1')
  await expect(score).toHaveAttribute('aria-valuetext', '1 分')

  await page.locator('[data-prepare-return]').click()
  const confirmationTitle = page.locator('[data-decision-confirmation] h3')
  await expect(confirmationTitle).toHaveText('确认退回修改')
  await expect(confirmationTitle).toBeFocused()
  await expect(page.locator('[data-remediation-field="issueType"]')).toBeVisible()
  expectNoRuntimeErrors(runtimeErrors)
})

test('响应式与键盘：字号、命中区、减弱动效与单主行动符合规范', async ({ page }) => {
  test.setTimeout(90_000)
  const runtimeErrors = captureRuntimeErrors(page)

  await resetDashboard(page)
  const dashboardMetrics = await page.evaluate(() => {
    const metrics = (selector) => {
      const element = document.querySelector(selector)
      const rect = element.getBoundingClientRect()
      return { font: parseFloat(getComputedStyle(element).fontSize), width: rect.width, height: rect.height }
    }
    return {
      rail: metrics('.arch-rail__txt'),
      brand: metrics('.arch-rail__brand'),
      search: metrics('.tcore-dashboard-topbar input'),
      notice: metrics('.tcore-dashboard-topbar .workspace-icon-btn b'),
    }
  })
  expect(dashboardMetrics.rail.font).toBeGreaterThanOrEqual(11)
  expect(dashboardMetrics.brand.width).toBeGreaterThanOrEqual(40)
  expect(dashboardMetrics.brand.height).toBeGreaterThanOrEqual(40)
  expect(dashboardMetrics.search.height).toBeGreaterThanOrEqual(40)
  expect(dashboardMetrics.notice.font).toBeGreaterThanOrEqual(11)

  await page.goto('/teacher/review.html?item=zhang-day4#queue')
  const reviewType = await page.evaluate(() => ({
    meta: parseFloat(getComputedStyle(document.querySelector('.tcore-queue-item__meta')).fontSize),
    status: parseFloat(getComputedStyle(document.querySelector('.tcore-queue-item__top .tcore-status')).fontSize),
    gap: parseFloat(getComputedStyle(document.querySelector('.tcore-ai-gaps li')).fontSize),
  }))
  expect(reviewType.meta).toBeGreaterThanOrEqual(13)
  expect(reviewType.status).toBeGreaterThanOrEqual(11)
  expect(reviewType.gap).toBeGreaterThanOrEqual(13)

  await page.goto('/teacher/camp.html')
  const campTypeAndTargets = await page.evaluate(() => {
    const box = (selector) => {
      const rect = document.querySelector(selector).getBoundingClientRect()
      return { width: rect.width, height: rect.height }
    }
    const font = (selector) => parseFloat(getComputedStyle(document.querySelector(selector)).fontSize)
    return {
      cellStrong: font('.tcore-camp-cell strong'),
      cellSmall: font('.tcore-camp-cell small'),
      toolbarMeta: font('.tcore-camp-toolbar__meta > span'),
      aiHelper: font('.tcore-camp-toolbar .tcore-button small'),
      legend: font('.tcore-legend-dot'),
      brand: box('.tcore-camp-rail .arch-rail__brand'),
      portal: box('.tcore-camp-topbar .portal-switch'),
      search: box('.tcore-camp-topbar input'),
      footSeparatorFont: font('.tcore-camp-module-list .module-list__foot'),
      moduleLinks: Array.from(document.querySelectorAll('.tcore-camp-module-list .module-list__foot a'))
        .map((element) => {
          const rect = element.getBoundingClientRect()
          return { width: rect.width, height: rect.height }
        }),
    }
  })
  expect(campTypeAndTargets.cellStrong).toBeGreaterThanOrEqual(13)
  expect(campTypeAndTargets.cellSmall).toBeGreaterThanOrEqual(11)
  expect(campTypeAndTargets.toolbarMeta).toBeGreaterThanOrEqual(13)
  expect(campTypeAndTargets.aiHelper).toBeGreaterThanOrEqual(11)
  expect(campTypeAndTargets.legend).toBeGreaterThanOrEqual(11)
  expect(campTypeAndTargets.footSeparatorFont).toBe(0)
  for (const target of [
    campTypeAndTargets.brand,
    campTypeAndTargets.portal,
    campTypeAndTargets.search,
    ...campTypeAndTargets.moduleLinks,
  ]) {
    expect(target.width).toBeGreaterThanOrEqual(40)
    expect(target.height).toBeGreaterThanOrEqual(40)
  }

  await page.locator('button[data-case-id="zhang-day4"]').click()
  const orangePrimaryCount = await page.locator('.tcore-camp .tcore-button:visible').evaluateAll((buttons) => (
    buttons.filter((button) => getComputedStyle(button).backgroundColor === 'rgb(232, 74, 28)').length
  ))
  expect(orangePrimaryCount).toBe(1)

  await requestChangesCase(page, 'zhang-day4')
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.goto('/user/training-day.html')
  const studentMetrics = await page.evaluate(() => {
    const font = (selector) => parseFloat(getComputedStyle(document.querySelector(selector)).fontSize)
    const rect = (selector) => {
      const box = document.querySelector(selector).getBoundingClientRect()
      return { width: box.width, height: box.height }
    }
    return {
      deliver: font('.camp-deliver li'),
      dayTitle: font('.camp-day__t'),
      dayStatus: font('.camp-day__s'),
      remediationTerm: font('.camp-feedback-remediation dt'),
      remediationCopy: font('.camp-feedback-remediation dd'),
      timelineCopy: font('.camp-feedback-timeline p'),
      aiFab: rect('.workspace-ai-fab'),
      brand: rect('.arch-rail__brand'),
      railFont: font('.arch-rail__txt'),
      noticeFont: font('.workspace-icon-btn b'),
      moduleFootFont: font('.module-list__foot'),
      dayTransition: getComputedStyle(document.querySelector('.camp-day')).transitionDuration,
      statGradient: getComputedStyle(document.querySelector('.camp-stat')).backgroundImage,
      feedbackGradient: getComputedStyle(document.querySelector('.camp-feedback-card.is-changes')).backgroundImage,
    }
  })
  expect(studentMetrics.deliver).toBeGreaterThanOrEqual(13)
  expect(studentMetrics.dayTitle).toBeGreaterThanOrEqual(13)
  expect(studentMetrics.dayStatus).toBeGreaterThanOrEqual(11)
  expect(studentMetrics.remediationTerm).toBeGreaterThanOrEqual(11)
  expect(studentMetrics.remediationCopy).toBeGreaterThanOrEqual(13)
  expect(studentMetrics.timelineCopy).toBeGreaterThanOrEqual(13)
  expect(studentMetrics.aiFab.width).toBeGreaterThanOrEqual(40)
  expect(studentMetrics.aiFab.height).toBeGreaterThanOrEqual(40)
  expect(studentMetrics.brand.width).toBeGreaterThanOrEqual(40)
  expect(studentMetrics.brand.height).toBeGreaterThanOrEqual(40)
  expect(studentMetrics.railFont).toBeGreaterThanOrEqual(11)
  expect(studentMetrics.noticeFont).toBeGreaterThanOrEqual(11)
  expect(studentMetrics.moduleFootFont).toBe(0)
  expect(studentMetrics.dayTransition).toMatch(/^0(?:s|\.0+s)?(?:, 0(?:s|\.0+s)?)*$/)
  expect(studentMetrics.statGradient).toBe('none')
  expect(studentMetrics.feedbackGradient).toBe('none')
  expectNoRuntimeErrors(runtimeErrors)
})
