import { test, expect } from '@playwright/test'

const basePath = '/prototypes/orep-unified-workspace/'

const routes = [
  'home',
  'teacher/projects',
  'team/tasks',
  'team/review',
  'team/materials',
  'team/members',
  'team/stages',
  'growth',
  'profile',
  'intro',
  'login',
  'prep/topic',
  'prep/files',
  'prep/ppt',
  'prep/ppt/new',
  'prep/ppt/edit',
  'prep/ppt/history',
  'prep/script',
  'prep/script/edit',
  'prep/versions',
  'learning/courses',
  'learning/course-detail',
  'learning/lesson',
  'assessment/center',
  'assessment/wrong-book',
  'assessment/favorites',
  'assessment/practice',
  'assessment/exam',
  'assessment/result',
  'teacher/courses',
  'teacher/assessments',
  'teacher/grading',
  'roadshow/lobby',
  'roadshow/room',
  'roadshow/history',
  'roadshow/recordings',
  'roadshow/upload',
  'score/list',
  'score/result',
  'score/todos',
  'score/why',
  'score/jury',
  'score/compare',
  'score/chat'
]

test.describe('OREP unified high-fidelity prototype', () => {
  test.beforeEach(async ({ page }) => {
    await page.emulateMedia({ reducedMotion: 'reduce' })
    await page.goto(`${basePath}#/home`)
    await page.evaluate(() => localStorage.removeItem('orep-unified-workspace-state-v1'))
    await page.reload()
  })

  test('every registered route renders one page title without runtime errors', async ({ page }) => {
    const runtimeErrors = []
    page.on('pageerror', (error) => runtimeErrors.push(error.message))
    page.on('console', (message) => {
      if (message.type() === 'error') runtimeErrors.push(message.text())
    })

    for (const route of routes) {
      await page.goto(`${basePath}#/${route}`)
      await expect(page.locator('#main-content h1')).toHaveCount(1)
      await expect(page.locator('#main-content')).not.toContainText('页面暂时无法显示')
      await expect(page.locator('#app')).not.toContainText('原型页面正在注册')
      const contract = await page.evaluate(() => {
        const actions = [...document.querySelectorAll('[data-action]')]
          .map((element) => element.getAttribute('data-action'))
          .filter(Boolean)
        const missingActions = [...new Set(actions.filter((name) => typeof window.OREP?.actions?.[name] !== 'function'))]
        const idCounts = [...document.querySelectorAll('[id]')].reduce((result, element) => {
          result[element.id] = (result[element.id] || 0) + 1
          return result
        }, {})
        const duplicateIds = Object.entries(idCounts).filter(([, count]) => count > 1).map(([id]) => id)
        return { missingActions, duplicateIds }
      })
      expect(contract.missingActions, `${route} should only render wired actions`).toEqual([])
      expect(contract.duplicateIds, `${route} should not duplicate element IDs`).toEqual([])
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
      expect(overflow, `${route} should not overflow horizontally`).toBeLessThanOrEqual(1)
    }

    expect(runtimeErrors).toEqual([])
  })

  test('student submission and teacher approval update the same workflow state', async ({ page }) => {
    await page.locator('.topbar [data-action="toggle-account"]').click()
    await page.locator('[data-action="switch-role"][data-payload="captain"]').click()
    await page.goto(`${basePath}#/team/tasks`)

    await page.locator('[data-action="core.task.select"][data-payload="task-evidence-cost"]').click()
    await page.locator('[data-action="core.task.submit"][data-payload="task-evidence-cost"]').click()
    await page.locator('[data-field="localData.drafts.submissionTitle"]').fill('三组试点成本收益证据 · V2')
    await page.locator('[data-field="localData.drafts.submissionComment"]').fill('已补齐统计区间、原始记录与回收周期口径。')
    await page.locator('[data-action="core.task.submit-confirm"]').click()

    await expect(page).toHaveURL(/#\/team\/review$/)
    await expect(page.locator('#main-content')).toContainText('三组试点成本收益证据 · V2')
    await expect(page.locator('#main-content')).toContainText('待审核')

    await page.locator('.topbar [data-action="toggle-account"]').click()
    await page.locator('[data-action="switch-role"][data-payload="teacher"]').click()
    await page.goto(`${basePath}#/team/review`)
    await page.locator('[data-action="core.review.select"]').filter({ hasText: '三组试点成本收益证据 · V2' }).click()
    await page.locator('[data-action="core.review.open-decision"]').filter({ hasText: '通过并同步' }).click()
    await page.locator('[data-action="core.review.confirm"]').click()

    await expect(page.locator('#main-content')).toContainText('已通过')
    await page.goto(`${basePath}#/team/tasks`)
    await page.locator('[data-action="core.task.select"][data-payload="task-evidence-cost"]').click()
    await expect(page.locator('.task-detail')).toContainText('已完成')
  })

  test('deep links, role boundaries, and preparation form state stay coherent', async ({ page }) => {
    await page.goto(`${basePath}#/learning/course-detail?course=course-python-foundation`)
    await expect(page.locator('#main-content h1')).toHaveText('Python编程基础')

    await page.goto(`${basePath}#/learning/lesson?course=course-spring-vue&lesson=lesson-auth-scope`)
    await expect(page.locator('#main-content h1')).toHaveText('登录鉴权与数据权限')
    await expect(page.locator('.immersive-island-bar .action-island')).toBeVisible()
    await expect(page.locator('.immersive-island-bar')).toContainText('完成课时')

    await page.goto(`${basePath}#/roadshow/room?meeting=meeting-weekly-07`)
    await expect(page.locator('#main-content h1')).toHaveText('智农云眼 · 每周项目例会')
    await expect(page.locator('.immersive-island-bar')).toContainText('开始录制')

    await page.goto(`${basePath}#/teacher/courses`)
    await expect(page.locator('#main-content h1')).toHaveText('此页面仅对教师开放')
    await expect(page.locator('[data-action="teacherToggleCourseCreate"]')).toHaveCount(0)

    await page.goto(`${basePath}#/prep/topic`)
    const projectName = page.locator('[data-action="prep.topic.field"][data-field="name"]')
    await projectName.fill('智农云眼 · 国赛优化版')
    await page.goto(`${basePath}#/prep/files`)
    await page.goto(`${basePath}#/prep/topic`)
    await expect(projectName).toHaveValue('智农云眼 · 国赛优化版')
  })

  test('learning completion and favorites are shared across all learning views', async ({ page }) => {
    await page.goto(`${basePath}#/learning/lesson?course=course-ai-advanced&lesson=lesson-rag-evaluation`)
    await expect(page.locator('#main-content h1')).toHaveText('建立可复现的评估集')
    await page.locator('#main-content [data-action="learningCompleteLesson"]').click()
    await expect(page).toHaveURL(/lesson=lesson-rag-security/)

    await page.goto(`${basePath}#/learning/course-detail?course=course-ai-advanced`)
    const progressMetric = page.locator('.metric-card').filter({ hasText: '课程进度' })
    await expect(progressMetric.locator('strong')).toHaveText('81%')
    await expect(page.locator('.metric-card').filter({ has: page.getByText('课时', { exact: true }) }).locator('strong')).toHaveText('3/5')

    await page.goto(`${basePath}#/assessment/wrong-book`)
    const timerQuestion = page.locator('.list-row').filter({ hasText: '考试倒计时应只依赖前端本地时间' })
    await expect(timerQuestion.locator('[data-action="assessmentToggleFavorite"]')).toHaveText('收藏')
    await timerQuestion.locator('[data-action="assessmentToggleFavorite"]').click()

    await page.goto(`${basePath}#/assessment/favorites`)
    await expect(page.locator('#main-content')).toContainText('考试倒计时应只依赖前端本地时间')
    await expect(page.locator('.metric-card').filter({ hasText: '已收藏' }).locator('strong')).toHaveText('3')

    await page.goto(`${basePath}#/assessment/center`)
    await expect(page.locator('.tabs [data-value="all"]')).toHaveClass(/active/)
    await expect(page.locator('#main-content .list article')).toHaveCount(2)
  })

  test('teacher publishing and grading update their operational queues', async ({ page }) => {
    await page.locator('.topbar [data-action="toggle-account"]').click()
    await page.locator('[data-action="switch-role"][data-payload="teacher"]').click()
    await page.goto(`${basePath}#/teacher/courses`)

    const courseRow = page.locator('tr').filter({ hasText: '人工智能进阶课程' })
    await courseRow.locator('[data-action="teacherToggleCoursePublish"]').click()
    await expect(courseRow).toContainText('已归档')
    await expect(courseRow.locator('[data-action="teacherToggleCoursePublish"]')).toHaveText('发布')

    await page.goto(`${basePath}#/teacher/assessments`)
    await page.locator('.page-head__aside [data-action="teacherToggleAssessmentCreate"]').click()
    await page.locator('[data-field="learningWorkspace.teacherAssessments.draft.title"]').fill('路演证据链专项测评')
    await page.locator('[data-action="teacherCreateAssessment"]').click()
    const draftRow = page.locator('tr').filter({ hasText: '路演证据链专项测评' })
    await expect(draftRow).toContainText('草稿')
    await draftRow.locator('[data-action="teacherToggleAssessmentPublish"]').click()
    await page.locator('[data-action="teacherSetAssessmentTab"][data-value="all"]').click()
    await expect(page.locator('tr').filter({ hasText: '路演证据链专项测评' })).toContainText('进行中')

    await page.goto(`${basePath}#/teacher/grading`)
    await expect(page.locator('.metric-card').filter({ hasText: '待阅' }).locator('strong')).toHaveText('3')
    await page.locator('[data-field^="learningWorkspace.grading.grades."]').first().fill('26')
    await page.locator('.grading-workbench [data-action="teacherSaveGradeNext"]').click()
    await expect(page.locator('.metric-card').filter({ hasText: '待阅' }).locator('strong')).toHaveText('2')
    await expect(page.locator('.grading-workbench')).toContainText('陈一川的答卷')
  })

  test('reset cancels asynchronous scoring work before restoring demo data', async ({ page }) => {
    await page.goto(`${basePath}#/roadshow/upload`)
    await page.locator('#roadshow-upload-input').setInputFiles({
      name: '第三轮计时彩排.mp4',
      mimeType: 'video/mp4',
      buffer: Buffer.from('orep-prototype-video')
    })
    await expect(page.locator('#main-content')).toContainText('第三轮计时彩排.mp4')
    await page.locator('#main-content').getByRole('button', { name: '开始评分' }).click()
    await page.waitForTimeout(520)
    const progressBeforeReset = await page.evaluate(() => window.OREP.app.state.roadshowScore?.upload?.progress || 0)
    expect(progressBeforeReset).toBeGreaterThan(0)

    await page.locator('.topbar [data-action="toggle-account"]').click()
    await page.locator('[data-action="reset-demo"]').click()
    await expect(page).toHaveURL(/#\/home$/)
    await page.waitForTimeout(900)
    const asyncStateAfterReset = await page.evaluate(() => window.OREP.app.state.roadshowScore)
    expect(asyncStateAfterReset).toBeUndefined()
  })

  test('desktop and mobile reference captures remain visually stable', async ({ page }) => {
    await page.setViewportSize({ width: 1440, height: 1000 })
    await page.goto(`${basePath}#/home`)
    await page.screenshot({ path: 'test-results/unified-home-student.png', fullPage: true })

    await page.locator('.topbar [data-action="toggle-account"]').click()
    await page.locator('[data-action="switch-role"][data-payload="teacher"]').click()
    await page.screenshot({ path: 'test-results/unified-home-teacher.png', fullPage: true })

    await page.goto(`${basePath}#/team/tasks`)
    await page.screenshot({ path: 'test-results/unified-team-tasks.png', fullPage: true })

    await page.goto(`${basePath}#/learning/lesson?course=course-ai-advanced&lesson=lesson-rag-evaluation`)
    await page.screenshot({ path: 'test-results/unified-learning-lesson.png', fullPage: true })

    await page.goto(`${basePath}#/roadshow/room?meeting=meeting-rehearsal-03`)
    await page.screenshot({ path: 'test-results/unified-roadshow-room.png', fullPage: true })

    await page.setViewportSize({ width: 390, height: 844 })
    await page.goto(`${basePath}#/home`)
    await expect(page.locator('.mobile-nav')).toBeVisible()
    await page.screenshot({ path: 'test-results/unified-home-mobile.png', fullPage: true })
  })
})
