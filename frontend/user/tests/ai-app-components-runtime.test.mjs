import assert from 'node:assert/strict'
import test from 'node:test'
import { createServer } from 'vite'
import { createSSRApp, h } from 'vue'
import { createMemoryHistory, createRouter } from 'vue-router'
import { renderToString } from '@vue/server-renderer'

let viteServer

test.before(async () => {
  viteServer = await createServer({
    server: { middlewareMode: true },
    appType: 'custom',
  })
})

test.after(async () => {
  await viteServer.close()
})

async function renderWithRouter(component, template) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: '/', component: { template: '<div />' } },
      { path: '/return', component: { template: '<div />' } },
    ],
  })
  await router.push('/')
  await router.isReady()

  const app = createSSRApp({ components: { Component: component }, template })
  app.use(router)
  return renderToString(app)
}

test('shell renders a div body rather than a nested main landmark', async () => {
  const { default: AiAppShell } = await viteServer.ssrLoadModule('/src/components/ai-apps/AiAppShell.vue')
  const html = await renderWithRouter(
    AiAppShell,
    '<Component mode="landing"><template #header><header>Header</header></template><p>Body</p></Component>'
  )

  assert.match(html, /class="ai-app-shell is-landing"/)
  assert.match(html, /class="ai-app-shell__body"/)
  assert.doesNotMatch(html, /<main\b/)
})

test('header preserves one h1, ignores title slots, supports editing, and resolves object navigation', async () => {
  const { default: AiAppHeader } = await viteServer.ssrLoadModule('/src/components/ai-apps/AiAppHeader.vue')
  const defaultHtml = await renderWithRouter(
    AiAppHeader,
    '<Component app="script" back-label="返回列表" :back-to="{ path: \'/return\' }" title="默认标题"><template #title><span>不应渲染</span></template></Component>'
  )
  const editableHtml = await renderWithRouter(
    AiAppHeader,
    '<Component app="script" back-label="返回列表" back-to="/return" title="可编辑标题" editable-title />'
  )

  assert.match(defaultHtml, /class="ai-app-header is-landing is-script"/)
  assert.equal((defaultHtml.match(/<h1\b/g) || []).length, 1)
  assert.match(defaultHtml, /<h1[^>]*>[\s\S]*默认标题[\s\S]*<\/h1>/)
  assert.doesNotMatch(defaultHtml, /不应渲染/)
  assert.match(defaultHtml, /href="\/return"/)
  assert.equal((editableHtml.match(/<h1\b/g) || []).length, 1)
  assert.match(editableHtml, /<h1[^>]*>[\s\S]*<input class="ai-app-header__title-input"[^>]*value="可编辑标题"[^>]*maxlength="100"[^>]*aria-label="页面标题"/)
})

test('editable header forwards title input and blur events through the component runtime', async () => {
  const { default: AiAppHeader } = await viteServer.ssrLoadModule('/src/components/ai-apps/AiAppHeader.vue')
  const originalSetup = AiAppHeader.setup
  let headerBindings
  const titleUpdates = []
  const blurEvents = []

  AiAppHeader.setup = (props, context) => {
    headerBindings = originalSetup(props, context)
    return headerBindings
  }

  try {
    const router = createRouter({
      history: createMemoryHistory(),
      routes: [
        { path: '/', component: { template: '<div />' } },
        { path: '/return', component: { template: '<div />' } },
      ],
    })
    await router.push('/')
    await router.isReady()

    const app = createSSRApp({
      render: () => h(AiAppHeader, {
        app: 'script',
        backLabel: '讲稿列表',
        backTo: '/return',
        title: '旧标题',
        editableTitle: true,
        'onUpdate:title': value => titleUpdates.push(value),
        onTitleBlur: event => blurEvents.push(event),
      }),
    })
    app.use(router)
    await renderToString(app)

    const blurEvent = { type: 'blur' }
    headerBindings.emit('update:title', '新标题')
    headerBindings.emit('titleBlur', blurEvent)

    assert.deepEqual(titleUpdates, ['新标题'])
    assert.deepEqual(blurEvents, [blurEvent])
  } finally {
    AiAppHeader.setup = originalSetup
  }
})

test('content widths and section roots render independently and semantically', async () => {
  const { default: AiAppContent } = await viteServer.ssrLoadModule('/src/components/ai-apps/AiAppContent.vue')
  const { default: AiAppSection } = await viteServer.ssrLoadModule('/src/components/ai-apps/AiAppSection.vue')
  const contentHtml = await renderWithRouter(AiAppContent, '<Component width="reading">Content</Component>')
  const namedSectionHtml = await renderWithRouter(AiAppSection, '<Component title="章节标题">Body</Component>')
  const unnamedSectionHtml = await renderWithRouter(AiAppSection, '<Component description="无标题说明">Body</Component>')

  assert.match(contentHtml, /class="ai-app-content is-reading"/)
  assert.match(namedSectionHtml, /<section class="ai-app-section is-default" aria-label="章节标题">/)
  assert.match(unnamedSectionHtml, /<div class="ai-app-section is-default">/)
  assert.doesNotMatch(unnamedSectionHtml, /<section\b/)
})
