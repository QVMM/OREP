import { expect, test } from '@playwright/test'
import { resolveSeekRequest } from '../src/modules/training/videoPlaybackPolicy'

const planPayload = {
  hasCamp: true,
  camp: {
    campId: 8,
    campName: '21天路演训练营',
    teamName: '向上生长队',
    startDate: '2026-07-22',
    endDate: '2026-08-11',
    currentDay: 1,
    totalDays: 21,
    remainingDays: 20
  },
  totalDays: 21,
  totalTasks: 3,
  completedTasks: 1,
  weeks: [
    {
      weekId: 1,
      weekNo: 1,
      title: '问题定义与用户验证',
      startDate: '2026-07-22',
      endDate: '2026-07-28',
      days: [
        {
          dayId: 22,
          dayNo: 1,
          trainingDate: '2026-07-22',
          title: '确定项目问题与用户需求',
          summary: '用真实访谈和场景证据明确项目边界。',
          progressStatus: 'TODAY',
          learningResourceCount: 2,
          learningCompletedCount: 1,
          learningEstimatedMinutes: 18,
          tasks: [
            {
              taskId: 36,
              title: '第 1 天 完成用户问题验证',
              description: '整理访谈证据并形成问题定义。',
              priority: 'HIGH',
              isPrimary: 1,
              requirementCount: 3,
              dueAt: '2026-07-22T22:00:00'
            },
            {
              taskId: 37,
              title: '补充竞品对比',
              description: '选取三个竞品完成差异分析。',
              priority: 'MEDIUM',
              isPrimary: 0,
              requirementCount: 2,
              dueAt: '2026-07-23T18:00:00'
            }
          ]
        }
      ]
    },
    {
      weekId: 2,
      weekNo: 2,
      title: '方案成型与表达',
      startDate: '2026-07-29',
      endDate: '2026-08-04',
      days: [
        {
          dayId: 29,
          dayNo: 8,
          trainingDate: '2026-07-29',
          title: '解决方案结构化',
          summary: '从用户问题推导产品方案。',
          progressStatus: 'UPCOMING',
          tasks: [
            {
              taskId: 52,
              title: '绘制解决方案蓝图',
              description: '完成角色、流程与价值闭环。',
              priority: 'MEDIUM',
              isPrimary: 1,
              requirementCount: 4,
              dueAt: '2026-07-29T22:00:00'
            }
          ]
        }
      ]
    }
  ]
}

test('反复向前拖动不会抬高可观看边界', () => {
  const boundary = { duration: 2345, serverVerifiedEnd: 30, localWatchedEnd: 32 }
  let current = 32

  for (let index = 0; index < 20; index += 1) {
    const result = resolveSeekRequest({ ...boundary, requested: 600 + index, current })
    expect(result.accepted).toBe(false)
    expect(result.position).toBe(32)
    current = result.position
  }

  const replay = resolveSeekRequest({ ...boundary, requested: 12, current })
  expect(replay).toEqual({ accepted: true, position: 12 })
})

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    const payload = btoa(JSON.stringify({ sub: '9', exp: Math.floor(Date.now() / 1000) + 3600 }))
      .replaceAll('+', '-')
      .replaceAll('/', '_')
      .replaceAll('=', '')
    localStorage.setItem('orep_user_token', `test.${payload}.signature`)
    localStorage.setItem('orep_user', JSON.stringify({ id: 9, username: '李林峰', role: 'STUDENT' }))
  })
  await page.route('**/api/training-camps/current/plan', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 200, data: planPayload })
  }))
  await page.route('**/api/training-days/22/overview', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      code: 200,
      data: {
        hasCamp: true,
        hasTrainingDay: true,
        dayId: 22,
        dayNo: 1,
        title: '确定项目问题与用户需求',
        summary: '用真实访谈和场景证据明确项目边界。',
        dueAt: '2026-07-22T22:00:00',
        camp: planPayload.camp,
        tasks: planPayload.weeks[0].days[0].tasks.map(task => ({ ...task, requirements: [{ id: 1, title: '访谈记录', required: true }] })),
        attachments: [],
        submission: {},
        feedback: { feedbackReady: false },
        learningResources: [
          {
            id: 1,
            title: '用户访谈证据怎么整理',
            resourceType: 'VIDEO',
            resourceUrl: '/uploads/training/lesson.mp4',
            required: true,
            estimatedMinutes: 8,
            durationSeconds: 480,
            learningStatus: 'NOT_STARTED',
            progressPercent: 0,
            actualLearningSeconds: 0,
            lastPositionSeconds: 0,
            maxWatchedPositionSeconds: 0
          },
          {
            id: 2,
            title: '问题定义示范',
            resourceType: 'LINK',
            resourceUrl: 'https://example.com/lesson',
            required: false,
            estimatedMinutes: 10,
            durationSeconds: 600,
            learningStatus: 'COMPLETED',
            progressPercent: 100
          }
        ]
      }
    })
  }))
})

test('训练任务入口展示全周期任务，并先进入具体任务详情', async ({ page }) => {
  await page.goto('/training/today')

  await expect(page.getByRole('heading', { name: '训练任务', exact: true })).toBeVisible()
  await expect(page.getByRole('link', { name: /完成用户问题验证/ })).toBeVisible()
  await expect(page.getByRole('link', { name: /绘制解决方案蓝图/ })).toBeVisible()
  await expect(page.getByRole('navigation', { name: '用户端主导航' }).getByRole('link', { name: '训练营' })).toBeVisible()
  await expect(page.getByText('还需完成 1 项学习，再开始任务')).toBeVisible()
  await expect(page.getByText('1 / 2 · 预计 18 分钟')).toBeVisible()
  await expect(page.getByRole('progressbar', { name: '任务前置学习进度' })).toHaveAttribute('aria-valuenow', '50')
  await expect(page.getByRole('link', { name: /完成用户问题验证/ })).toContainText('开始任务')
  await expect(page.locator('.task-item h4').first()).toHaveText('完成用户问题验证')
  await expect(page.getByRole('link', { name: /绘制解决方案蓝图/ })).toContainText('查看要求')
  await expect(page.locator('.task-item').first()).toHaveCSS('transform', 'none')

  await page.getByRole('link', { name: /完成用户问题验证/ }).click()

  await expect(page).toHaveURL(/\/training\/tasks\/36\?dayId=22$/)
  await expect(page.getByRole('heading', { name: '任务详情' })).toBeVisible()
  await expect(page.getByRole('heading', { name: '完成用户问题验证' })).toBeVisible()
  await expect(page.getByText('访谈记录')).toBeVisible()
  await expect(page.getByRole('heading', { name: '今日学习' })).toBeVisible()
  await expect(page.getByText('用户访谈证据怎么整理')).toBeVisible()
  await expect(page.locator('.training-learning-item video')).toBeVisible()
  await expect(page.locator('.training-video-player')).toBeVisible()
  await expect(page.getByRole('img', { name: '学习进度 0%' })).toBeVisible()
  await expect(page.getByText('已学习 0 秒')).toBeVisible()
  await expect(page.locator('.training-learning-card__progress')).toHaveText('1/2 项完成')
  await expect(page.locator('.training-flow').getByText('1/2 项完成')).toBeVisible()
  await expect(page.locator('.training-video-player__center-play')).toBeVisible()
  await expect(page.getByRole('button', { name: '静音' })).toBeVisible()
  await expect(page.getByRole('slider', { name: '音量' })).toBeVisible()
  await expect(page.getByRole('button', { name: '全屏播放' })).toBeVisible()
  await expect(page.locator('.training-video-player__watermark')).toHaveCount(0)
  await page.locator('.training-learning-item video').evaluate(video => video.dispatchEvent(new Event('play')))
  await expect(page.locator('.training-video-player__watermark')).toContainText('李林峰 · 竞赛大脑学习专用')
  await page.locator('.training-learning-item video').evaluate(video => video.dispatchEvent(new Event('pause')))
  await expect(page.locator('.training-video-player__watermark')).toHaveCount(0)
  await expect(page.locator('.training-learning-item video')).not.toHaveAttribute('controls', '')
  await expect(page.locator('.training-learning-item video')).toHaveAttribute('controlslist', /nodownload/)
  await expect(page.getByRole('button', { name: '开始学习' })).toHaveCount(0)
  const signalBox = await page.locator('.training-learning-item__signal').first().boundingBox()
  const videoBox = await page.locator('.training-learning-item video').boundingBox()
  expect(Math.abs(signalBox.x - videoBox.x)).toBeLessThanOrEqual(1)
  const titleBox = await page.getByText('用户访谈证据怎么整理').boundingBox()
  const metaBox = await page.getByText('视频 · 已学习 0 秒').boundingBox()
  expect(metaBox.y - (titleBox.y + titleBox.height)).toBeLessThanOrEqual(5)
  await expect(page.getByText('还有 1 项必学内容未完成，建议学习后再提交。')).toBeVisible()
})

test('任务详情主区与侧栏在不同桌面分辨率下保持 74 比 26 的动态占比', async ({ page }) => {
  for (const width of [1280, 1920, 2560, 3840]) {
    await page.setViewportSize({ width, height: 1000 })
    await page.goto('/training/tasks/36?dayId=22')

    const shares = await page.locator('.training-dashboard').evaluate(dashboard => {
      const primaryWidth = dashboard.querySelector('.training-primary').getBoundingClientRect().width
      const sideWidth = dashboard.querySelector('.training-side').getBoundingClientRect().width
      const tracksWidth = primaryWidth + sideWidth
      return {
        primary: primaryWidth / tracksWidth,
        side: sideWidth / tracksWidth
      }
    })

    expect(shares.primary).toBeCloseTo(0.74, 2)
    expect(shares.side).toBeCloseTo(0.26, 2)
  }

  await page.setViewportSize({ width: 900, height: 1000 })
  await page.goto('/training/tasks/36?dayId=22')
  await expect.poll(() => page.locator('.training-dashboard').evaluate(dashboard => {
    return getComputedStyle(dashboard).gridTemplateColumns.split(' ').length
  })).toBe(1)
  await expect.poll(() => page.evaluate(() => document.body.scrollWidth <= document.body.clientWidth)).toBe(true)
})

test('任务书在外层路由重置滚动后仍恢复到真实阅读位置', async ({ page }) => {
  const sectionCopy = Array.from(
    { length: 14 },
    (_, index) => `<p>这是用于验证长任务书阅读定位的第 ${index + 1} 段说明，学生应能在离开页面后继续从原处阅读。</p>`
  ).join('')
  const contentHtml = [
    '<h1>长任务书阅读验证</h1>',
    '<h2>一、了解任务目标</h2>',
    sectionCopy,
    '<h2>二、准备基础环境</h2>',
    sectionCopy,
    '<h2>三、准备项目数据库</h2>',
    sectionCopy,
    '<h2>四、完成运行检查</h2>',
    sectionCopy
  ].join('')

  await page.route('**/api/training-days/22/overview', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      code: 200,
      data: {
        hasCamp: true,
        hasTrainingDay: true,
        dayId: 22,
        dayNo: 1,
        title: '确定项目问题与用户需求',
        summary: '用真实访谈和场景证据明确项目边界。',
        dueAt: '2026-07-22T22:00:00',
        contentHtml,
        camp: planPayload.camp,
        tasks: planPayload.weeks[0].days[0].tasks.map(task => ({
          ...task,
          requirements: [{ id: 1, title: '访谈记录', required: true }]
        })),
        attachments: [],
        submission: {},
        feedback: { feedbackReady: false },
        learningResources: []
      }
    })
  }))

  await page.setViewportSize({ width: 1280, height: 900 })
  await page.goto('/training/tasks/36?dayId=22')

  const scrollRoot = page.locator('.workspace-main')
  const targetHeading = page.getByRole('heading', { name: '三、准备项目数据库', exact: true })
  const savedHeadingTop = await targetHeading.evaluate((heading) => {
    const root = document.querySelector('.workspace-main')
    const rootTop = root.getBoundingClientRect().top
    const headingTop = heading.getBoundingClientRect().top - rootTop + root.scrollTop
    root.scrollTo({ top: headingTop + 260, behavior: 'auto' })
    return heading.getBoundingClientRect().top
  })
  await expect.poll(() => scrollRoot.evaluate(element => element.scrollTop)).toBeGreaterThan(600)
  await page.waitForTimeout(500)
  const readingStorageKey = 'orep:training-reading:v1:9:36:22'
  await expect.poll(async () => {
    const stored = await page.evaluate(key => JSON.parse(localStorage.getItem(key) || 'null'), readingStorageKey)
    return stored?.headingText || ''
  }).toBe('三、准备项目数据库')

  await page.getByRole('navigation', { name: '用户端主导航' })
    .getByRole('link', { name: '训练营', exact: true })
    .click()
  await expect.poll(async () => {
    const stored = await page.evaluate(key => JSON.parse(localStorage.getItem(key) || 'null'), readingStorageKey)
    return Number(stored?.scrollTop || 0)
  }).toBeGreaterThan(600)
  await page.getByRole('link', { name: /完成用户问题验证/ }).click()

  await expect(page.locator('.training-reading-resume')).toContainText('已回到上次阅读位置 · 三、准备项目数据库')
  await expect.poll(
    () => targetHeading.evaluate(
      (heading, expectedTop) => Math.abs(heading.getBoundingClientRect().top - expectedTop),
      savedHeadingTop
    ),
    { timeout: 5000 }
  ).toBeLessThan(10)
})

test('任务附件与提交成果可独立折叠，全部折叠后侧栏收成工具轨', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 1000 })
  await page.goto('/training/tasks/36?dayId=22')

  const dashboard = page.locator('.training-dashboard')
  const primary = page.locator('.training-primary')
  const side = page.locator('.training-side')
  const primaryWidthBefore = await primary.evaluate(element => element.getBoundingClientRect().width)

  await expect(page.getByRole('button', { name: '折叠任务附件' })).toBeVisible()
  await expect(page.getByRole('button', { name: '折叠提交成果' })).toBeVisible()
  await page.getByRole('button', { name: '折叠任务附件' }).click()

  await expect(page.getByRole('button', { name: '展开任务附件' })).toBeVisible()
  await expect(page.getByRole('button', { name: '折叠提交成果' })).toBeVisible()
  await expect(dashboard).not.toHaveClass(/is-side-rail/)

  await page.getByRole('button', { name: '折叠提交成果' }).click()

  await expect(page.getByRole('button', { name: '展开提交成果' })).toBeVisible()
  await expect(dashboard).toHaveClass(/is-side-rail/)
  await expect(side).toHaveClass(/is-rail/)
  await expect.poll(async () => {
    const box = await side.boundingBox()
    return Math.round(box?.width || 0)
  }).toBe(64)
  await expect.poll(async () => {
    const box = await primary.boundingBox()
    return (box?.width || 0) > primaryWidthBefore
  }).toBe(true)

  await page.reload()
  await expect(page.getByRole('button', { name: '折叠任务附件' })).toBeVisible()
  await expect(page.getByRole('button', { name: '折叠提交成果' })).toBeVisible()
  await expect(dashboard).not.toHaveClass(/is-side-rail/)
})

test('训练任务使用周日双轨时间线并在窄屏降为单列', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 })
  await page.goto('/training/today')

  const firstWeek = page.locator('.tasks-week').first()
  const tracingBeam = page.locator('[data-training-tracing-beam]')
  await expect(firstWeek.getByText('第 1 周', { exact: true })).toBeVisible()
  await expect(firstWeek.getByText('第 1 天', { exact: true })).toBeVisible()
  await expect(firstWeek.getByText(/^W\d+/)).toHaveCount(0)
  await expect(firstWeek.getByText(/^DAY\s+\d+/)).toHaveCount(0)
  await expect(tracingBeam).toBeVisible()
  await expect(tracingBeam.locator('.training-tracing-beam__path')).toHaveCount(2)
  await expect(tracingBeam.locator('.training-tracing-beam__path--active')).toHaveAttribute('stroke', /^url\(#/)
  await expect(tracingBeam.locator('linearGradient stop')).toHaveCount(4)
  await expect(firstWeek.locator('.tasks-week__head')).toHaveCSS('position', 'relative')
  await expect(firstWeek.locator('.tasks-week__head')).toHaveCSS('border-top-width', '0px')
  await expect(firstWeek.locator('.tasks-week__head')).toHaveCSS('box-shadow', 'none')
  await expect.poll(() => firstWeek.locator('.tasks-week__head').evaluate(el => getComputedStyle(el, '::after').content)).toBe('none')
  await expect.poll(() => firstWeek.locator('.tasks-week__head').evaluate(el => getComputedStyle(el).gridTemplateColumns.split(' ').length)).toBe(2)

  const weekNode = firstWeek.locator('.tasks-week__anchor')
  const firstNode = firstWeek.locator('.tasks-day__date i').first()
  await expect(weekNode).toHaveCSS('width', '9px')
  await expect(weekNode).toHaveCSS('height', '9px')
  await expect(firstNode).toHaveCSS('width', '7px')
  await expect(firstNode).toHaveCSS('height', '7px')
  await expect.poll(() => firstNode.evaluate(node => {
    const style = getComputedStyle(node, '::after')
    return {
      width: style.width,
      height: style.height,
      position: style.position
    }
  })).toEqual({
    width: '14px',
    height: '14px',
    position: 'absolute'
  })

  const pathData = await tracingBeam.locator('.training-tracing-beam__path--base').getAttribute('d')
  expect(pathData).toMatch(/^M 10 [\d.]+/)
  expect(pathData).toMatch(/C 10 [\d.]+ 30 [\d.]+ 30 [\d.]+ V [\d.]+/)
  expect(pathData).toMatch(/V [\d.]+ C 30 [\d.]+ 10 [\d.]+ 10 [\d.]+/)
  const axisAlignment = await firstNode.evaluate(dayNode => {
    const beam = dayNode.closest('[data-training-tracing-beam]')
    const rail = beam.querySelector('.training-tracing-beam__rail').getBoundingClientRect()
    const weekRect = beam.querySelector('.tasks-week__anchor').getBoundingClientRect()
    const dayRect = dayNode.getBoundingClientRect()
    return {
      weekCenter: weekRect.left + weekRect.width / 2,
      weekTrack: rail.left + 10,
      dayCenter: dayRect.left + dayRect.width / 2,
      dayTrack: rail.left + 30
    }
  })
  expect(Math.abs(axisAlignment.weekCenter - axisAlignment.weekTrack)).toBeLessThanOrEqual(1)
  expect(Math.abs(axisAlignment.dayCenter - axisAlignment.dayTrack)).toBeLessThanOrEqual(1)

  await page.setViewportSize({ width: 720, height: 900 })
  await expect.poll(() => firstWeek.locator('.tasks-week__head').evaluate(el => getComputedStyle(el).gridTemplateColumns.split(' ').length)).toBe(1)
  await expect(firstWeek.locator('.tasks-week__head')).toHaveCSS('position', 'relative')
  await expect(tracingBeam).toHaveCSS('--training-beam-left', '0px')
  await expect.poll(() => page.evaluate(() => document.body.scrollWidth <= document.body.clientWidth)).toBe(true)
})

test('跟踪光束会随训练任务内部滚动区平滑推进', async ({ page }) => {
  const trainingDate = dayNo => new Date(2026, 6, 21 + dayNo).toISOString().slice(0, 10)
  const longWeeks = Array.from({ length: 3 }, (_, weekIndex) => ({
    weekId: weekIndex + 10,
    weekNo: weekIndex + 1,
    title: `第 ${weekIndex + 1} 周训练重点`,
    startDate: trainingDate(weekIndex * 7 + 1),
    endDate: trainingDate(weekIndex * 7 + 7),
    days: Array.from({ length: 7 }, (_, dayIndex) => {
      const dayNo = weekIndex * 7 + dayIndex + 1
      return {
        dayId: 100 + dayNo,
        dayNo,
        trainingDate: trainingDate(dayNo),
        progressStatus: dayNo === 1 ? 'TODAY' : 'UPCOMING',
        tasks: [{
          taskId: 1000 + dayNo,
          title: `第 ${dayNo} 天训练任务`,
          description: '完成当天训练内容并提交对应成果。',
          priority: 'MEDIUM',
          isPrimary: 1,
          requirementCount: 1,
          dueAt: `${trainingDate(dayNo)}T22:00:00`
        }]
      }
    })
  }))

  await page.route('**/api/training-camps/current/plan', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      code: 200,
      data: {
        ...planPayload,
        totalDays: 21,
        totalTasks: 21,
        completedTasks: 0,
        weeks: longWeeks
      }
    })
  }))
  await page.setViewportSize({ width: 1280, height: 620 })
  await page.goto('/training/today')

  const beam = page.locator('[data-training-tracing-beam]')
  const gradient = beam.locator('linearGradient')
  await expect(beam).toBeVisible()
  const before = Number(await gradient.getAttribute('y2'))

  await page.waitForTimeout(150)
  await page.locator('.workspace-main').evaluate(element => {
    element.scrollTop = 900
  })
  await expect.poll(() => page.locator('.workspace-main').evaluate(element => element.scrollTop)).toBeGreaterThan(500)
  await page.waitForTimeout(700)
  const after = Number(await gradient.getAttribute('y2'))

  expect(after).toBeGreaterThan(before + 200)
})

test('训练列表统一只展示正式任务，不展示训练方向层级', async ({ page }) => {
  await page.goto('/training/today')

  const firstDay = page.locator('.tasks-day').first()
  await expect(firstDay.locator('.tasks-day__body > header')).toHaveCount(0)
  await expect(firstDay.getByText('确定项目问题与用户需求')).toHaveCount(0)
  await expect(firstDay.getByText('用真实访谈和场景证据明确项目边界。')).toHaveCount(0)
  await expect(firstDay.getByRole('link', { name: /完成用户问题验证/ })).toBeVisible()
})

test('训练营取消选题策划和练习考试入口，旧地址回到训练任务', async ({ page }) => {
  await page.goto('/training/today')

  await expect(page.locator('.workspace-module-nav__label', { hasText: '选题策划' })).toHaveCount(0)
  await expect(page.locator('.workspace-module-nav__label', { hasText: '练习考试' })).toHaveCount(0)
  await expect(page.locator('.workspace-module-nav__label', { hasText: '课程学习' })).toHaveCount(0)

  await page.goto('/script-editor?tab=topic')
  await expect(page).toHaveURL(/\/training\/today$/)

  await page.goto('/track-match')
  await expect(page).toHaveURL(/\/training\/today$/)

  await page.goto('/exam-system')
  await expect(page).toHaveURL(/\/training\/today$/)

  await page.goto('/exam-system/take/7')
  await expect(page).toHaveURL(/\/training\/today$/)

  await page.goto('/course-learning/12/lesson/3')
  await expect(page).toHaveURL(/\/training\/today$/)
})
