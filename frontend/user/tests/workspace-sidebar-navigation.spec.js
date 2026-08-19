import { expect, test } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('orep_user_token', 'workspace-sidebar-navigation-token')
  })

  await page.route('**/api/**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 200, data: {} })
  }))
})

test('桌面主导航保留六个准确命名的可访问链接及训练营当前态', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 })
  await page.goto('/training/today')

  const navigation = page.getByRole('navigation', { name: '用户端主导航' })
  const links = navigation.getByRole('link')
  const expectedNames = ['首页', '训练营', '路演训练', '资源中心', 'AI应用中心', '我的']

  await expect(links).toHaveCount(6)
  for (const [index, name] of expectedNames.entries()) {
    await expect(links.nth(index)).toHaveAccessibleName(name)
  }

  const iconGeometry = await page.evaluate(() => (
    Array.from(document.querySelectorAll('.workspace-nav .workspace-module-icon')).map((svg) => {
      const paths = Array.from(svg.querySelectorAll('path'))
      const boxes = paths.map(path => path.getBBox())
      const x = Math.min(...boxes.map(box => box.x))
      const y = Math.min(...boxes.map(box => box.y))
      const right = Math.max(...boxes.map(box => box.x + box.width))
      const bottom = Math.max(...boxes.map(box => box.y + box.height))
      const viewBox = svg.viewBox.baseVal
      const halfStroke = Number.parseFloat(getComputedStyle(svg).strokeWidth) / 2
      const tolerance = 0.01

      return {
        pathCount: paths.length,
        width: right - x,
        height: bottom - y,
        staysInsideViewBox: (
          x - halfStroke >= viewBox.x - tolerance
          && y - halfStroke >= viewBox.y - tolerance
          && right + halfStroke <= viewBox.x + viewBox.width + tolerance
          && bottom + halfStroke <= viewBox.y + viewBox.height + tolerance
        ),
      }
    })
  ))

  expect(iconGeometry).toHaveLength(6)
  for (const geometry of iconGeometry) {
    expect(geometry.pathCount).toBeGreaterThan(0)
    expect(geometry.width).toBeGreaterThan(0)
    expect(geometry.height).toBeGreaterThan(0)
    expect(geometry.staysInsideViewBox).toBe(true)
  }

  const trainingLink = navigation.getByRole('link', { name: '训练营', exact: true })
  await expect(trainingLink).toHaveClass(/\bis-active\b/)

  const trainingIcon = trainingLink.locator('.workspace-module-icon')

  await expect(trainingIcon).toHaveClass(/\bis-filled\b/)
  expect(await trainingIcon.evaluate(element => getComputedStyle(element).fill)).not.toBe('none')
  await expect(trainingIcon).toHaveCSS('stroke', 'none')

  for (const link of await links.all()) {
    if (await link.getAttribute('aria-current') === 'page') continue
    await expect(link.locator('.workspace-module-icon')).toHaveClass(/\bis-outline\b/)
  }
})

test('侧栏品牌按钮提供返回首页的可访问名称', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 })
  await page.goto('/training/today')

  const brandButton = page.getByRole('button', { name: '返回首页', exact: true })
  const brandOrange = await page.evaluate(() => {
    const probe = document.createElement('span')
    probe.style.color = 'var(--ds-orange)'
    document.body.append(probe)
    const computedColor = getComputedStyle(probe).color
    probe.remove()
    return computedColor
  })

  await expect(brandButton).toBeVisible()
  await brandButton.focus()
  await expect(brandButton).toHaveCSS('outline-style', 'solid')
  await expect(brandButton).toHaveCSS('outline-width', '2px')
  await expect(brandButton).toHaveCSS('outline-color', brandOrange)
  await expect(brandButton).toHaveCSS('outline-offset', '3px')
})

test('侧栏品牌按钮点击后返回首页', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 })
  await page.goto('/training/today')

  await page.getByRole('button', { name: '返回首页', exact: true }).click()
  await expect(page).toHaveURL('/')
})

test('路演训练子路由同步当前项样式与 aria-current', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 })
  await page.goto('/meeting-history/1')

  const roadshowLink = page
    .getByRole('navigation', { name: '用户端主导航' })
    .getByRole('link', { name: '路演训练', exact: true })

  await expect(roadshowLink).toHaveClass(/\bis-active\b/)
  await expect(roadshowLink).toHaveAttribute('aria-current', 'page')

  const roadshowIcon = roadshowLink.locator('.workspace-module-icon')
  const trainingIcon = page
    .getByRole('navigation', { name: '用户端主导航' })
    .getByRole('link', { name: '训练营', exact: true })
    .locator('.workspace-module-icon')

  await expect(roadshowIcon).toHaveClass(/\bis-filled\b/)
  await expect(trainingIcon).toHaveClass(/\bis-outline\b/)
})

test('主导航路由族按路径分段匹配且不会误认相似前缀', async ({ page }) => {
  await page.goto('/training/today')

  const results = await page.evaluate(async () => {
    const { isOrepRouteActive } = await import('/src/composables/apple/useOrepNavigation.js')
    const roadshowPaths = [
      '/online-meeting',
      '/meeting/12',
      '/meeting-history/1',
      '/my-recordings',
      '/statistics',
      '/score-result/12',
      '/ai-score-upload',
      '/ai-score/12/result',
      '/ai-score/report/26/result',
      '/ai-score/report-id/9/result',
      '/roadshow-chat/1',
    ]
    const roadshowNearMisses = [
      '/online-meeting-old',
      '/meeting-old/1',
      '/meeting-history-old',
      '/my-recordings-old',
      '/statistics-old',
      '/score-result-old',
      '/ai-scoreboard',
      '/roadshow-chat-old',
    ]

    return {
      roadshow: roadshowPaths.map(path => ({
        path,
        active: isOrepRouteActive(path, '/online-meeting'),
      })),
      nearMisses: roadshowNearMisses.map(path => ({
        path,
        active: isOrepRouteActive(path, '/online-meeting'),
      })),
      otherNearMisses: [
        { path: '/training-old', itemPath: '/training/today' },
        { path: '/profile-old', itemPath: '/profile' },
        { path: '/project-team-old', itemPath: '/project-team' },
      ].map(({ path, itemPath }) => ({
        path,
        active: isOrepRouteActive(path, itemPath),
      })),
    }
  })

  expect(results.roadshow).toEqual(results.roadshow.map(({ path }) => ({ path, active: true })))
  expect(results.nearMisses).toEqual(results.nearMisses.map(({ path }) => ({ path, active: false })))
  expect(results.otherNearMisses).toEqual(results.otherNearMisses.map(({ path }) => ({ path, active: false })))
})

test('评分深层页面归入路演训练且不再显示复盘入口', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 })
  await page.goto('/ai-score-upload')

  const navigation = page.getByRole('navigation', { name: '用户端主导航' })
  const roadshowLink = navigation.getByRole('link', { name: '路演训练', exact: true })

  await expect(navigation.getByRole('link', { name: '复盘', exact: true })).toHaveCount(0)
  await expect(roadshowLink).toHaveAttribute('aria-current', 'page')
  await expect(roadshowLink).toHaveClass(/\bis-active\b/)
  await expect(roadshowLink.locator('.workspace-module-icon')).toHaveClass(/\bis-filled\b/)
  await expect(page.locator('.workspace-module-nav')).toHaveCount(0)
})

test('九百像素宽度下移动端使用五个普通入口加中央协作入口', async ({ page }) => {
  await page.setViewportSize({ width: 900, height: 900 })
  await page.goto('/ai-score-upload')

  const navigation = page.getByRole('navigation', { name: '移动端主导航' })
  const links = navigation.getByRole('link')
  const expectedNames = ['首页', '训练营', '路演训练', '资源中心', '我的']

  await expect(navigation).toBeVisible()
  await expect(links).toHaveCount(5)
  for (const [index, name] of expectedNames.entries()) {
    await expect(links.nth(index)).toHaveAccessibleName(name)
  }
  await expect(navigation.getByRole('button', { name: '协作', exact: true })).toBeVisible()
  await expect(navigation.getByRole('link', { name: 'AI应用中心', exact: true })).toHaveCount(0)

  const roadshowLink = navigation.getByRole('link', { name: '路演训练', exact: true })
  await expect.soft(roadshowLink).toHaveClass(/\bis-active\b/)
  await expect.soft(roadshowLink).toHaveAttribute('aria-current', 'page')
  expect.soft(await navigation.evaluate(element => (
    getComputedStyle(element).gridTemplateColumns.split(' ').length
  ))).toBe(6)
  await expect(navigation.getByRole('link', { name: '复盘', exact: true })).toHaveCount(0)
})

test('未知图标样式回退为具有描边样式的 outline', async ({ page }) => {
  await page.goto('/training/today')

  const rendered = await page.evaluate(async () => {
    const [{ createApp, h, nextTick }, { default: WorkspaceModuleIcon }] = await Promise.all([
      import('/node_modules/.vite/deps/vue.js'),
      import('/src/components/workspace/WorkspaceModuleIcon.vue'),
    ])
    const host = document.createElement('div')
    document.body.append(host)
    const app = createApp({
      render: () => h(WorkspaceModuleIcon, { name: 'home', variant: 'unexpected' }),
    })

    try {
      app.mount(host)
      await nextTick()
      const svg = host.querySelector('svg')
      const style = getComputedStyle(svg)

      return {
        className: svg.getAttribute('class'),
        fill: style.fill,
        stroke: style.stroke,
      }
    } finally {
      app.unmount()
      host.remove()
    }
  })

  expect(rendered.className).toContain('is-outline')
  expect(rendered.fill).toBe('none')
  expect(rendered.stroke).not.toBe('none')
})

test('桌面图标扣子尺寸固定并在悬停与键盘聚焦时显示中文提示', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 700 })
  await page.goto('/training/today')

  const navigation = page.getByRole('navigation', { name: '用户端主导航' })
  const trainingLink = navigation
    .getByRole('link', { name: '训练营', exact: true })
  const tooltip = trainingLink.locator('.workspace-nav__tooltip')
  const iconFrame = trainingLink.locator('.workspace-nav__icon')
  const icon = trainingLink.locator('svg')
  const outlineIcon = navigation
    .getByRole('link', { name: '首页', exact: true })
    .locator('svg')
  const sidebar = page.locator('.workspace-sidebar')

  await expect(trainingLink).toHaveCSS('width', '52px')
  await expect(trainingLink).toHaveCSS('height', '52px')
  await expect(trainingLink).toHaveCSS('border-radius', '16px')
  await expect(iconFrame).toHaveCSS('width', '28px')
  await expect(iconFrame).toHaveCSS('height', '28px')
  await expect(icon).toHaveCSS('width', '28px')
  await expect(icon).toHaveCSS('height', '28px')
  await expect(outlineIcon).toHaveCSS('stroke-width', '1.9px')
  await expect(outlineIcon).toHaveCSS('stroke-linecap', 'round')
  await expect(outlineIcon).toHaveCSS('stroke-linejoin', 'round')
  await expect(sidebar).toHaveCSS('overflow-x', 'visible')
  await expect(sidebar).toHaveCSS('overflow-y', 'visible')
  await expect(navigation).toHaveCSS('overflow-x', 'visible')
  await expect(navigation).toHaveCSS('overflow-y', 'visible')

  await expect(tooltip).toHaveCSS('font-size', '14px')
  await expect(tooltip).toHaveCSS('min-height', '36px')
  const tooltipDecoration = await tooltip.evaluate((element) => {
    const tooltipStyle = getComputedStyle(element)
    const arrowStyle = getComputedStyle(element, '::before')

    return {
      arrowContent: arrowStyle.content,
      arrowWidth: arrowStyle.width,
      arrowHeight: arrowStyle.height,
      arrowBackgroundColor: arrowStyle.backgroundColor,
      tooltipBackgroundColor: tooltipStyle.backgroundColor,
      arrowTransform: arrowStyle.transform,
    }
  })
  expect(tooltipDecoration.arrowContent).toBe('""')
  expect(tooltipDecoration.arrowWidth).toBe('8px')
  expect(tooltipDecoration.arrowHeight).toBe('8px')
  expect(tooltipDecoration.arrowBackgroundColor).toBe(tooltipDecoration.tooltipBackgroundColor)
  expect(tooltipDecoration.arrowTransform).toBe(
    'matrix(0.707107, 0.707107, -0.707107, 0.707107, 4, -4)',
  )

  await expect(tooltip).toHaveCSS('visibility', 'hidden')
  await expect(tooltip).toHaveCSS('opacity', '0')

  await trainingLink.hover()
  await expect(tooltip).toHaveCSS('visibility', 'visible')
  await expect(tooltip).toHaveCSS('opacity', '1')
  await expect(tooltip).toBeInViewport({ ratio: 1 })
  expect(await tooltip.evaluate((element) => {
    const { left, top, width, height } = element.getBoundingClientRect()
    element.style.pointerEvents = 'auto'
    const isTopLayer = document.elementFromPoint(left + width / 2, top + height / 2) === element
    element.style.removeProperty('pointer-events')
    return isTopLayer
  })).toBe(true)
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(1280)

  await page.mouse.move(320, 320)
  await trainingLink.focus()
  await expect(trainingLink).toHaveCSS('outline-style', 'solid')
  await expect(tooltip).toHaveCSS('visibility', 'visible')
  await expect(tooltip).toHaveCSS('opacity', '1')
  await expect(tooltip).toBeInViewport({ ratio: 1 })
})

test('极矮桌面仍可滚动访问最后一个完整尺寸导航项', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 320 })
  await page.goto('/training/today')

  const workspace = page.locator('.workspace-app')
  const profileLink = page
    .getByRole('navigation', { name: '用户端主导航' })
    .getByRole('link', { name: '我的', exact: true })

  await expect(profileLink).toHaveCSS('width', '52px')
  await expect(profileLink).toHaveCSS('height', '52px')
  await expect(workspace).toHaveCSS('overflow-y', 'auto')
  expect(await workspace.evaluate(element => element.scrollHeight > element.clientHeight)).toBe(true)

  await profileLink.scrollIntoViewIfNeeded()
  const profileBox = await profileLink.boundingBox()
  expect(profileBox.y).toBeGreaterThanOrEqual(0)
  expect(profileBox.y + profileBox.height).toBeLessThanOrEqual(320)
})

test('九百像素宽度下隐藏桌面侧栏', async ({ page }) => {
  await page.setViewportSize({ width: 900, height: 900 })
  await page.goto('/training/today')

  await expect(page.locator('.workspace-sidebar')).toHaveCSS('display', 'none')
})
