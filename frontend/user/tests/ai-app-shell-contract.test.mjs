import assert from 'node:assert/strict'
import { existsSync, readdirSync, readFileSync } from 'node:fs'
import test from 'node:test'

const read = relativePath => readFileSync(
  new URL(`../${relativePath}`, import.meta.url),
  'utf8'
)

function collectSourceFiles(relativeDirectory) {
  const directoryUrl = new URL(`../${relativeDirectory}/`, import.meta.url)

  return readdirSync(directoryUrl, { withFileTypes: true }).flatMap(entry => {
    const relativePath = `${relativeDirectory}/${entry.name}`
    if (entry.isDirectory()) return collectSourceFiles(relativePath)
    return /\.(?:vue|js|css)$/.test(entry.name) ? [relativePath] : []
  })
}

function findBalancedObjectEnd(source, openIndex, description) {
  assert.equal(source[openIndex], '{', `${description} must start at an opening brace`)

  let depth = 0
  let quote = null
  let escaped = false

  for (let index = openIndex; index < source.length; index += 1) {
    const character = source[index]

    if (quote) {
      if (escaped) {
        escaped = false
      } else if (character === '\\') {
        escaped = true
      } else if (character === quote) {
        quote = null
      }
      continue
    }

    if (character === "'" || character === '"' || character === '`') {
      quote = character
    } else if (character === '{') {
      depth += 1
    } else if (character === '}') {
      depth -= 1
      if (depth === 0) return index
    }
  }

  assert.fail(`${description} has no closing brace`)
}

function extractPropsDeclaration(source, componentName) {
  const declaration = /defineProps\s*\(\s*\{|\bprops\s*:\s*\{/.exec(source)
  assert.ok(declaration, `${componentName} must declare its props as an object`)

  const openIndex = declaration.index + declaration[0].lastIndexOf('{')
  return source.slice(
    openIndex,
    findBalancedObjectEnd(source, openIndex, `${componentName} props declaration`) + 1
  )
}

function extractPropObject(source, propName, componentName) {
  const props = extractPropsDeclaration(source, componentName)
  const match = new RegExp(`\\b${propName}\\s*:\\s*\\{`).exec(props)
  assert.ok(match, `${componentName} must declare a ${propName} prop object`)

  const openIndex = match.index + match[0].lastIndexOf('{')
  return props.slice(
    openIndex,
    findBalancedObjectEnd(props, openIndex, `${componentName} ${propName} prop`) + 1
  )
}

function extractRouteBlock(source, routePath) {
  const escapedPath = routePath.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const pathPattern = new RegExp(`\\bpath\\s*:\\s*(['"])${escapedPath}\\1`)
  const pathMatch = pathPattern.exec(source)
  assert.ok(pathMatch, `route ${routePath} must be declared with its exact path literal`)

  const openBraces = []
  let quote = null
  let escaped = false
  for (let index = 0; index < pathMatch.index; index += 1) {
    const character = source[index]
    if (quote) {
      if (escaped) {
        escaped = false
      } else if (character === '\\') {
        escaped = true
      } else if (character === quote) {
        quote = null
      }
      continue
    }
    if (character === "'" || character === '"' || character === '`') {
      quote = character
    } else if (character === '{') {
      openBraces.push(index)
    } else if (character === '}') {
      openBraces.pop()
    }
  }

  const routeStart = openBraces.at(-1)
  assert.notEqual(routeStart, undefined, `route ${routePath} must be inside a route object`)
  const routeEnd = findBalancedObjectEnd(source, routeStart, `route ${routePath}`)
  return source.slice(routeStart, routeEnd + 1)
}

function assertMigratedToShell(source, viewName, modePattern) {
  assert.match(
    source,
    /import\s+AiAppShell\s+from\s+['"][^'"]*AiAppShell\.vue['"]/
  )
  assert.equal((source.match(/<AiAppShell\b[^>]*>/g) || []).length, 1, `${viewName} has one shell opening tag`)
  assert.equal((source.match(/<\/AiAppShell>/g) || []).length, 1, `${viewName} has one shell closing tag`)
  assert.match(source, modePattern)
}

test('AI app shell exposes only approved modes and widths', () => {
  const shell = read('src/components/ai-apps/AiAppShell.vue')
  const content = read('src/components/ai-apps/AiAppContent.vue')
  const styles = read('src/styles/ai-app-shell.css')
  const mode = extractPropObject(shell, 'mode', 'AiAppShell')
  const width = extractPropObject(content, 'width', 'AiAppContent')

  assert.match(mode, /validator:\s*value\s*=>\s*\[\s*'landing'\s*,\s*'task'\s*,\s*'workspace'\s*\]\.includes\(value\)/)
  assert.match(width, /validator:\s*value\s*=>\s*\[\s*'wide'\s*,\s*'standard'\s*,\s*'reading'\s*,\s*'fluid'\s*\]\.includes\(value\)/)
  assert.match(shell, /<slot name="header"/)
  assert.match(shell, /<AiAppContent/)
  assert.match(shell, /<div\s+class="ai-app-shell"/)
  assert.match(shell, /<div\s+class="ai-app-shell__body">/)
  assert.doesNotMatch(shell, /<main\b/)
  assert.doesNotMatch(shell, /width-\$\{width\}/)
  assert.match(styles, /\.ai-app-content\s*\{[\s\S]*--ai-app-width-wide:\s*1280px[\s\S]*--ai-app-width-standard:\s*1120px[\s\S]*--ai-app-width-reading:\s*880px/)
})

test('AI app header owns explicit parent navigation and an unbreakable h1', () => {
  const header = read('src/components/ai-apps/AiAppHeader.vue')
  const styles = read('src/styles/ai-app-shell.css')
  const backLabel = extractPropObject(header, 'backLabel', 'AiAppHeader')
  const backTo = extractPropObject(header, 'backTo', 'AiAppHeader')

  assert.match(backLabel, /type:\s*String\b/)
  assert.match(backLabel, /required:\s*true\b/)
  assert.match(backTo, /type:\s*\[\s*String\s*,\s*Object\s*\]/)
  assert.match(backTo, /required:\s*true\b/)
  assert.match(header, /:to="backTo"/)
  assert.match(header, /\{\{ backLabel \}\}/)
  assert.equal((header.match(/<h1\b/g) || []).length, 1)
  assert.match(header, /<h1\b[^>]*>[\s\S]*v-if="editableTitle"[\s\S]*\{\{ title \}\}[\s\S]*<\/h1>/)
  assert.doesNotMatch(header, /<slot name="title"/)
  assert.match(header, /:class="\[`is-\$\{mode\}`, `is-\$\{app\}`\]"/)
  assert.match(header, /<slot name="actions"/)
  assert.doesNotMatch(header, /to="\/ai-apps"/)
  assert.match(extractPropObject(header, 'editableTitle', 'AiAppHeader'), /type:\s*Boolean\b/)
  assert.match(extractPropObject(header, 'editableTitle', 'AiAppHeader'), /default:\s*false\b/)
  assert.match(extractPropObject(header, 'titleMaxlength', 'AiAppHeader'), /type:\s*Number\b/)
  assert.match(extractPropObject(header, 'titleMaxlength', 'AiAppHeader'), /default:\s*100\b/)
  assert.match(
    extractPropObject(header, 'titleMaxlength', 'AiAppHeader'),
    /validator:\s*value\s*=>\s*Number\.isInteger\(value\)\s*&&\s*value\s*>\s*0/
  )
  assert.match(header, /defineEmits\s*\(\s*\[\s*'update:title'\s*,\s*'titleBlur'\s*\]\s*\)/)
  assert.match(header, /class="ai-app-header__title-input"/)
  assert.match(header, /:maxlength="titleMaxlength"/)
  assert.match(header, /:aria-label="titleLabel"/)
  assert.match(extractPropObject(header, 'titleLabel', 'AiAppHeader'), /default:\s*'页面标题'/)
  assert.match(styles, /\.ai-app-header\.is-script\s+\.ai-app-header__icon/)
  assert.doesNotMatch(styles, /\.ai-app-header__actions\s*>\s*:not\(:last-child\)\s*\{\s*display:\s*none/)
  assert.match(styles, /@media \(max-width: 1023px\)[\s\S]*\.ai-app-shell:not\(\.is-workspace\)[\s\S]*padding-bottom:\s*calc\(96px \+ env\(safe-area-inset-bottom\)\)/)
  assert.match(styles, /@media \(max-width: 1023px\)[\s\S]*\.ai-app-shell\.is-workspace\s+\.ai-app-shell__body[\s\S]*padding-bottom:\s*calc\(96px \+ env\(safe-area-inset-bottom\)\)/)
  assert.match(styles, /@media \(max-width: 720px\)[\s\S]*height:\s*100dvh/)
})

test('AI app routes explicitly opt into a flush main region', () => {
  const router = read('src/router/index.js')
  const workspaceShell = read('src/components/workspace/WorkspaceShell.vue')
  const targetRoutes = [
    ['/script-editor', 'landing'],
    ['/script-editor/detail/:scriptId', 'workspace'],
    ['/script-editor/template/:templateId', 'workspace'],
    ['/ppt-generator', 'task'],
    ['/ppt-editor', 'landing'],
    ['/ppt-history/:id', 'task']
  ]

  for (const [routePath, aiAppMode] of targetRoutes) {
    const routeBlock = extractRouteBlock(router, routePath)
    assert.match(
      routeBlock,
      /meta:\s*\{[^{}]*flushMain:\s*true[^{}]*\}/s,
      `route ${routePath} must set flushMain: true in its own flat meta object`
    )
    assert.match(
      routeBlock,
      new RegExp(`meta:\\s*\\{[^{}]*aiAppMode:\\s*['\"]${aiAppMode}['\"][^{}]*\\}`, 's'),
      `route ${routePath} must set aiAppMode: ${aiAppMode} in its own flat meta object`
    )
  }

  assert.equal(
    (router.match(/\bflushMain\s*:\s*true\b/g) || []).length,
    targetRoutes.length,
    'only the six AI application detail routes may opt into the flush main region'
  )
  assert.equal(
    (router.match(/\baiAppMode\s*:\s*['"](?:landing|task|workspace)['"]/g) || []).length,
    targetRoutes.length,
    'only the six AI application detail routes may declare an AI application mode'
  )
  assert.match(
    workspaceShell,
    /:class="\{[\s\S]*?'is-flush':\s*isFlushPage[\s\S]*?\}"/
  )
  const flushPageDefinition = workspaceShell.match(
    /const\s+isFlushPage\s*=\s*computed\s*\(\s*\(\s*\)\s*=>\s*Boolean\s*\(\s*route\.meta\?\.flushMain\s*\)\s*\)/
  )
  assert.ok(flushPageDefinition)
  assert.equal(
    flushPageDefinition[0].replace(/\s+/g, ' '),
    'const isFlushPage = computed(() => Boolean(route.meta?.flushMain))'
  )
  assert.doesNotMatch(workspaceShell, /path\.startsWith\('\/script-editor'\)/)
  assert.doesNotMatch(workspaceShell, /path\.startsWith\('\/ppt-editor'\)/)
})

test('PPT and script views consume the new shell', () => {
  const ppt = read('src/views/PptEditor.vue')
  const scriptList = read('src/views/ScriptList.vue')
  const scriptEditor = read('src/views/ScriptEditor.vue')

  assertMigratedToShell(ppt, 'PptEditor', /<AiAppShell\b[^>]*:mode="pptShellMode"/)
  assertMigratedToShell(scriptList, 'ScriptList', /<AiAppShell\b[^>]*mode="landing"/)
  assertMigratedToShell(scriptEditor, 'ScriptEditor', /<AiAppShell\b[^>]*mode="workspace"/)
  assert.doesNotMatch(ppt, /AiAppDetailHeader/)
  assert.doesNotMatch(scriptList, /AiAppDetailHeader/)
  assert.doesNotMatch(scriptEditor, /AiAppDetailHeader/)
})

test('editor async workflows are lifecycle-bound and generation is single-flight', () => {
  const ppt = read('src/views/PptEditor.vue')
  const scriptEditor = read('src/views/ScriptEditor.vue')

  assert.match(scriptEditor, /createRequestLifecycle/)
  assert.match(scriptEditor, /scriptRequestLifecycle\.activate\(\)/)
  assert.match(scriptEditor, /signal:\s*loadRequest\.signal/)
  assert.match(scriptEditor, /if\s*\(!loadRequest\.isCurrent\(\)\)\s*return/)
  assert.match(
    scriptEditor,
    /onBeforeUnmount\(\(\)\s*=>\s*\{\s*scriptRequestLifecycle\.invalidate\(\)/
  )

  assert.match(ppt, /createRequestLifecycle/)
  assert.match(ppt, /pptRequestLifecycle\.activate\(\)/)
  assert.match(ppt, /const generateLocked = ref\(false\)/)
  assert.match(ppt, /generateLocked\.value\s*=\s*true[\s\S]*await[\s\S]*generateLocked\.value\s*=\s*false/)
  assert.match(ppt, /const canGenerate = computed\(\(\) => \{[\s\S]*generateLocked\.value/)
  assert.match(ppt, /signal:\s*operation\.signal/)
  assert.match(ppt, /pptRequestLifecycle\.open\(['"]history-detail['"]\)/)
  assert.match(
    ppt,
    /apiGet\(`\/api\/ppt\/history\/\$\{item\.job_id\}`,\s*\{\s*signal:\s*operation\.signal\s*\}\)/
  )
  assert.match(ppt, /if\s*\(!operation\.isCurrent\(\)[\s\S]*\)\s*return false/)
  assert.match(
    ppt,
    /onBeforeUnmount\(\(\)\s*=>\s*\{\s*pptRequestLifecycle\.invalidate\(\)/
  )
})

test('AI application parents and responsive action hierarchy stay explicit', () => {
  const header = read('src/components/ai-apps/AiAppHeader.vue')
  const ppt = read('src/views/PptEditor.vue')
  const history = read('src/views/PptHistoryDetail.vue')
  const scriptList = read('src/views/ScriptList.vue')

  assert.match(header, /titleLabel/)
  assert.match(header, /:aria-label="titleLabel"/)
  assert.match(ppt, /pptView\.value === 'workspace'[\s\S]*\?\s*'PPT 列表'/)
  assert.match(ppt, /query:\s*\{\s*view:\s*'history'\s*\}/)
  assert.match(ppt, /view === 'history'[\s\S]*historyDrawer\.value = true/)
  assert.match(ppt, /aria-label="更多操作"/)
  assert.match(history, /back-label="最近记录"/)
  assert.match(history, /query:\s*\{\s*view:\s*'history'\s*\}/)
  assert.doesNotMatch(
    scriptList.slice(scriptList.indexOf('<AiAppHeader'), scriptList.indexOf('</AiAppHeader>')),
    /#actions/
  )
})

test('script workspace moves its secondary template action into mobile more actions', () => {
  const scriptEditor = read('src/views/ScriptEditor.vue')
  const editorStyles = read('src/styles/script-editor-v2.css')

  assert.match(scriptEditor, /aria-label="更多操作"/)
  assert.match(scriptEditor, /<el-dropdown-item[^>]*command="save-template"[^>]*>存为模板<\/el-dropdown-item>/)
  assert.match(scriptEditor, /handleHeaderMoreAction/)
  assert.match(
    scriptEditor,
    /command === 'save-template'[\s\S]*showSaveAsTemplate\.value = true/
  )
  assert.match(editorStyles, /\.script-mobile-more\s*\{\s*display:\s*none/)
  assert.match(
    editorStyles,
    /@media \(max-width: 767px\)[\s\S]*\.template-btn\s*\{[\s\S]*display:\s*none[\s\S]*\.script-mobile-more\s*\{[\s\S]*display:\s*inline-flex/
  )
})

test('PPT workspace mobile actions share the 768px header breakpoint', () => {
  const ppt = read('src/views/PptEditor.vue')

  assert.match(
    ppt,
    /@media \(max-width: 767px\)[\s\S]*\.ppt-icon-button\.ppt-workspace-secondary-action\s*\{[\s\S]*display:\s*none[\s\S]*\.ppt-mobile-more\s*\{[\s\S]*display:\s*inline-flex/
  )
  assert.doesNotMatch(ppt, /@media \(max-width: 719px\)/)
})

test('PPT interaction API mocks use explicit method and pathname matching', () => {
  const interactions = read('tests/ppt-generator-interactions.spec.js')

  assert.match(
    interactions,
    /function\s+isApiRequest\(method,\s*path,\s*expectedMethod,\s*expectedPath\)/
  )
  assert.doesNotMatch(interactions, /if\s*\(\s*path\s*===/)
})

test('PPT editor uses one three-state shell and restores same-route parent state', () => {
  const ppt = read('src/views/PptEditor.vue')

  assertMigratedToShell(
    ppt,
    'PptEditor',
    /<AiAppShell\b[^>]*:mode="pptShellMode"[^>]*:width="pptShellWidth"/
  )
  assert.equal((ppt.match(/<AiAppHeader\b/g) || []).length, 1)
  assert.match(ppt, /:back-label="pptBackLabel"/)
  assert.match(ppt, /:back-to="pptBackTo"/)
  assert.match(ppt, /:context="pptHeaderContext"/)
  assert.match(ppt, /:title="pptHeaderTitle"/)
  assert.match(ppt, /:subtitle="pptHeaderSubtitle"/)
  assert.match(ppt, /:status="pptHeaderStatus"/)
  assert.match(ppt, /const\s+pptShellMode\s*=\s*computed/)
  assert.match(ppt, /const\s+pptShellWidth\s*=\s*computed/)
  assert.match(ppt, /const\s+pptBackTo\s*=\s*computed/)
  assert.match(ppt, /useRoute\(\)/)
  assert.match(ppt, /\(\)\s*=>\s*route\.query\.view/)
  assert.match(ppt, /router\.replace\(\s*['"]\/ppt-editor['"]\s*\)/)
  assert.match(ppt, /query:\s*\{[\s\S]*view:\s*['"]setup['"]/)
  assert.doesNotMatch(ppt, /AiAppDetailHeader/)
  assert.doesNotMatch(ppt, /@click="pptView\s*=\s*'landing'"/)
})

test('legacy PPT task and history pages use task shells with stable parents', () => {
  const generator = read('src/views/PptGenerator.vue')
  const history = read('src/views/PptHistoryDetail.vue')

  assertMigratedToShell(
    generator,
    'PptGenerator',
    /<AiAppShell\b[^>]*mode="task"[^>]*width="standard"/
  )
  assert.equal((generator.match(/<AiAppHeader\b/g) || []).length, 1)
  assert.match(generator, /back-label="PPT 制作"/)
  assert.match(generator, /back-to="\/ppt-editor"/)
  assert.doesNotMatch(generator, /返回首页/)
  assert.doesNotMatch(generator, /router\.push\(\s*['"]\/['"]\s*\)/)
  assert.doesNotMatch(generator, /class="ppt-generator"/)

  assertMigratedToShell(
    history,
    'PptHistoryDetail',
    /<AiAppShell\b[^>]*mode="task"[^>]*width="wide"/
  )
  assert.equal((history.match(/<AiAppHeader\b/g) || []).length, 1)
  assert.match(history, /back-label="最近记录"/)
  assert.match(history, /query:\s*\{\s*view:\s*'history'\s*\}/)
  assert.match(history, /const\s+downloadActionText\s*=\s*computed/)
  assert.doesNotMatch(history, /router\.back\(\)/)
  assert.doesNotMatch(history, /class="ppt-history-detail"/)
})

test('legacy PPT task interactions are single-flight, lifecycle-safe, and keyboard native', () => {
  const generator = read('src/views/PptGenerator.vue')
  const history = read('src/views/PptHistoryDetail.vue')

  assert.match(generator, /createPptTaskCoordinator/)
  assert.doesNotMatch(generator, /setInterval\s*\(/)
  assert.match(generator, /const\s+submitBusy\s*=\s*ref\(false\)/)
  assert.match(generator, /const\s+confirmBusy\s*=\s*ref\(false\)/)
  assert.match(generator, /const\s+downloadBusy\s*=\s*ref\(false\)/)
  assert.match(generator, /:loading="submitBusy"/)
  assert.match(generator, /:loading="confirmBusy"/)
  assert.match(generator, /:loading="downloadBusy"/)

  assert.match(generator, /<button[\s\S]*:class="\[[^\n]*'domain-card'[^\n]*\]"[\s\S]*:aria-pressed=/)
  assert.match(generator, /<button[\s\S]*:class="\[[^\n]*'theme-card'[^\n]*\]"[\s\S]*:aria-pressed=/)
  assert.match(generator, /<button[\s\S]*class="history-card"/)
  assert.doesNotMatch(generator, /<BaseCard\b[^>]*class="domain-card"/)
  assert.doesNotMatch(generator, /<BaseCard\b[^>]*class="theme-card"/)
  assert.doesNotMatch(generator, /<BaseCard\b[^>]*class="history-card"/)
  assert.match(generator, /\.domain-card:focus-visible[\s\S]*--ds-focus-outline/)
  assert.match(generator, /\.theme-card:focus-visible[\s\S]*--ds-focus-outline/)
  assert.match(generator, /\.history-card:focus-visible[\s\S]*--ds-focus-outline/)

  assert.match(history, /async function performDownloadPpt\(lifecycleToken\s*=\s*pageLifecycle\.capture\(\)\)/)
  assert.match(history, /return\s+downloadCoordinator\.runOnce\(\s*['"]download['"]/)
  assert.match(history, /onBeforeUnmount\(\(\)\s*=>\s*\{[\s\S]*pageLifecycle\.invalidate\(\)[\s\S]*ElMessageBox\.close\(\)/)
  assert.match(history, /signal:\s*controller\.signal/)
})

test('script and PPT preparation share one route-gated landing shell', () => {
  const scriptList = read('src/views/ScriptList.vue')

  assert.match(scriptList, /import\s+AiAppHeader\s+from\s+['"][^'"]*AiAppHeader\.vue['"]/)
  assert.match(scriptList, /import\s+AiAppShell\s+from\s+['"][^'"]*AiAppShell\.vue['"]/)
  assert.match(
    scriptList,
    /const\s+isAiAppPreparation\s*=\s*computed\s*\(\s*\(\)\s*=>\s*\(\s*route\.path\s*===\s*['"]\/script-editor['"]\s*&&\s*\(\s*activePrepKey\.value\s*===\s*['"]script['"]\s*\|\|\s*activePrepKey\.value\s*===\s*['"]ppt['"]\s*\)\s*\)\s*\)/
  )
  assert.equal((scriptList.match(/<AiAppShell\b/g) || []).length, 1)
  assert.match(
    scriptList,
    /<AiAppShell\b[^>]*v-if="isAiAppPreparation"[^>]*mode="landing"[^>]*width="wide"/
  )
  assert.equal((scriptList.match(/<AiAppHeader\b/g) || []).length, 1)
  assert.match(scriptList, /back-label="AI 应用中心"/)
  assert.match(scriptList, /back-to="\/ai-apps"/)
  assert.match(scriptList, /:title="prepTitle"/)
  assert.match(scriptList, /:subtitle="prepSubtitle"/)
  assert.match(scriptList, /@open-script="openScript"/)
  assert.match(scriptList, /@create-blank="createBlankScript"/)
  assert.match(scriptList, /@create-from-template="openTemplateDialog"/)
  assert.match(scriptList, /@enter-ppt="router\.push\('\/ppt-editor'\)"/)
  assert.match(scriptList, /emits:\s*\['enterPpt'\]/)
  assert.match(scriptList, /emit\('enterPpt'\)[\s\S]*进入 PPT 工作台|进入 PPT 工作台[\s\S]*emit\('enterPpt'\)/)
  assert.doesNotMatch(scriptList, /AiAppDetailHeader/)
})

test('resource center remains outside the AI application shell and keeps its gutter contract', () => {
  const scriptList = read('src/views/ScriptList.vue')
  const shellStart = scriptList.indexOf('<AiAppShell')
  const shellEnd = scriptList.indexOf('</AiAppShell>')

  if (shellStart !== -1) {
    assert.notEqual(shellEnd, -1, 'ScriptList AI application shell must have a closing tag')
    const shellMarkup = scriptList.slice(shellStart, shellEnd + '</AiAppShell>'.length)
    assert.doesNotMatch(shellMarkup, /ResourceCenterWorkspace/)
  }

  assert.match(
    scriptList,
    /<ResourceCenterWorkspace[\s\S]*:team-id="activeTeamId"[\s\S]*:team-name="activeTeamName"/
  )
  assert.match(
    scriptList,
    /\.prep-workbench\.mode-materials\s*\{[^}]*width:\s*100%;[^}]*padding:\s*0;[^}]*display:\s*block;/
  )
  assert.doesNotMatch(
    scriptList,
    /\.prep-workbench\.mode-materials\s*\{[^}]*padding:\s*var\(--ai-app/
  )
})

test('script preparation cancels stale requests, serializes polling, and preserves one main landmark', () => {
  const scriptList = read('src/views/ScriptList.vue')
  const template = scriptList.slice(0, scriptList.indexOf('<script setup>'))
  const shellStart = template.indexOf('<AiAppShell')
  const shellEnd = template.indexOf('</AiAppShell>')
  const shellMarkup = template.slice(shellStart, shellEnd + '</AiAppShell>'.length)

  assert.match(
    scriptList,
    /import\s*\{[^}]*createRequestLifecycle[^}]*createSerialPoller[^}]*\}\s*from\s*['"][^'"]*requestLifecycle\.js['"]/
  )
  assert.match(scriptList, /const\s+prepRequestLifecycle\s*=\s*createRequestLifecycle\(\)/)
  assert.match(scriptList, /const\s+runPoller\s*=\s*createSerialPoller\(/)
  assert.doesNotMatch(scriptList, /runPollTimer/)
  assert.doesNotMatch(
    scriptList,
    /function ensureRunPolling\(\)[\s\S]*?setInterval\s*\(/
  )
  assert.match(
    scriptList,
    /request\.get\(\s*['"]\/api\/project-prep\/bootstrap['"][\s\S]*signal:\s*requestContext\.signal/
  )
  assert.match(
    scriptList,
    /if\s*\(\s*!requestContext\.isCurrent\(\)\s*\)\s*return[\s\S]*applyBootstrap/
  )
  assert.match(
    scriptList,
    /async function refreshSession[\s\S]*requestContext\.isCurrent\(\)[\s\S]*prepSession\.value\s*=\s*res\.data/
  )
  assert.match(
    scriptList,
    /onBeforeUnmount\(\(\)\s*=>\s*\{\s*prepRequestLifecycle\.invalidate\(\)/
  )
  assert.match(
    scriptList,
    /watch\(\s*\(\)\s*=>\s*\[\s*route\.path\s*,\s*route\.query\.tab\s*,\s*route\.meta\.defaultPrepTab\s*\]/
  )
  assert.ok(shellStart >= 0 && shellEnd > shellStart)
  assert.doesNotMatch(shellMarkup, /<main\b/)
  assert.doesNotMatch(template, /<main\b/)
})

test('script rows use separate native buttons and PPT workspace has no dead event', () => {
  const scriptList = read('src/views/ScriptList.vue')

  assert.match(
    scriptList,
    /h\('button',\s*\{\s*type:\s*'button',\s*class:\s*'script-row-open'/
  )
  assert.doesNotMatch(
    scriptList,
    /class:\s*'script-row'[\s\S]{0,180}tabindex:\s*0/
  )
  assert.doesNotMatch(
    scriptList,
    /const PptWorkspace[\s\S]*?emits:\s*\[\s*'openEditor'\s*\]/
  )
  assert.match(scriptList, /\.script-row-open:focus-visible/)
})

test('script editor uses the shared workspace header as its only page title and stable parent', () => {
  const scriptEditor = read('src/views/ScriptEditor.vue')
  const scriptEditorStyles = read('src/styles/script-editor-v2.css')

  assertMigratedToShell(
    scriptEditor,
    'ScriptEditor',
    /<AiAppShell\b[^>]*mode="workspace"[^>]*width="fluid"/
  )
  assert.equal((scriptEditor.match(/<AiAppHeader\b/g) || []).length, 1)
  assert.match(scriptEditor, /back-label="讲稿列表"/)
  assert.match(scriptEditor, /back-to="\/script-editor"/)
  assert.match(scriptEditor, /context="讲稿制作 · 编辑器"/)
  assert.match(scriptEditor, /v-model:title="scriptTitle"/)
  assert.match(scriptEditor, /\beditable-title\b/)
  assert.match(scriptEditor, /:title-maxlength="100"/)
  assert.match(scriptEditor, /@title-blur="autoSave"/)
  assert.match(scriptEditor, /:status="headerStatus"/)
  assert.doesNotMatch(scriptEditor, /<h1\b/)
  assert.doesNotMatch(scriptEditor, /AiAppDetailHeader/)
  assert.doesNotMatch(scriptEditor, /#localNavigation/)
  assert.doesNotMatch(scriptEditor, /\bArrowLeft\b/)
  assert.doesNotMatch(scriptEditor, />\s*返回讲稿列表\s*</)
  assert.doesNotMatch(scriptEditor, /\bgoBack\b/)
  assert.doesNotMatch(scriptEditor, /router\.back\(\)/)
  assert.doesNotMatch(scriptEditor, /<main\b/)
  assert.doesNotMatch(scriptEditor, /@media\s+not\s+all/)
  assert.doesNotMatch(scriptEditor, /\.editor-header\b/)
  assert.doesNotMatch(scriptEditor, /\.back-btn\b/)
  assert.equal((scriptEditor.match(/<style\b/g) || []).length, 1)
  assert.match(scriptEditor, /<style scoped src="\.\.\/styles\/script-editor-v2\.css"><\/style>/)
  assert.match(
    scriptEditorStyles,
    /\.editor-state\s*\{[^}]*min-height:\s*100%;[^}]*margin:\s*0;/s
  )
  assert.doesNotMatch(scriptEditorStyles, /\.editor-state\s*\{[^}]*margin:\s*var\(--ds-space-/s)
  assert.match(scriptEditor, /:editable-title="canUseEditor"/)
  assert.match(scriptEditor, /:status="headerStatus"/)
  assert.match(scriptEditor, /const\s+templateSaving\s*=\s*ref\(false\)/)
  assert.match(scriptEditor, /:loading="templateSaving"/)
  assert.match(scriptEditor, /onBeforeRouteLeave\s*\(\s*async/)
  assert.match(scriptEditor, /await\s+flushSaveQueue\(\)/)
  assert.match(scriptEditor, /return\s+false/)
  assert.match(scriptEditor, /beforeunload/)
  assert.match(scriptEditor, /saveTimer\s*=\s*setTimeout\([\s\S]*?\},\s*3000\s*\)/)
  assert.match(scriptEditor, /runAfterSuccessfulSave/)
  assert.doesNotMatch(scriptEditor, /\bdoSave\b/)
  const templateRedirectPattern = /router\.replace\(\s*\{\s*name:\s*['"]ScriptEditor['"]\s*,\s*params:\s*\{\s*scriptId:\s*String\(scriptId\.value\)\s*\}\s*\}\s*\)/g
  assert.equal((scriptEditor.match(templateRedirectPattern) || []).length, 1)
  assert.doesNotMatch(scriptEditor, /class="chapter-item"[\s\S]{0,180}role="button"/)
  assert.match(scriptEditor, /<button\s+type="button"\s+class="chapter-select"/)
  assert.match(scriptEditor, /<button[\s\S]{0,100}type="button"[\s\S]{0,100}class="chapter-delete"/)
  assert.match(scriptEditor, /:aria-pressed="activeChapterIdx === idx"/)
  assert.match(scriptEditorStyles, /\.chapter-select:focus-visible/)
  assert.match(scriptEditorStyles, /\.chapter-delete\s*\{[^}]*min-height:\s*40px/s)
})

test('AI application detail migration has no legacy header or duplicate page landmarks', () => {
  const legacyHeaderUrl = new URL(
    '../src/components/ai-apps/AiAppDetailHeader.vue',
    import.meta.url
  )
  const targetViews = [
    'src/views/PptEditor.vue',
    'src/views/PptGenerator.vue',
    'src/views/PptHistoryDetail.vue',
    'src/views/ScriptList.vue',
    'src/views/ScriptEditor.vue',
  ]

  assert.equal(
    existsSync(legacyHeaderUrl),
    false,
    'the unconsumed AiAppDetailHeader component must be deleted'
  )

  for (const relativePath of targetViews) {
    const source = read(relativePath)
    assert.doesNotMatch(source, /AiAppDetailHeader/)
    assert.doesNotMatch(source, /router\.(?:back|go)\s*\(/)
    assert.doesNotMatch(source, /\bgoBack\b/)
    assert.doesNotMatch(source, /<h1\b/)
    assert.doesNotMatch(source, /class=["'][^"']*\bsr-only\b/)
    assert.doesNotMatch(source, /<main\b/)
  }
})

test('only the approved five detail views consume the shared shell and header', () => {
  const sourceFiles = collectSourceFiles('src')
  const expectedConsumers = [
    'src/views/PptEditor.vue',
    'src/views/PptGenerator.vue',
    'src/views/PptHistoryDetail.vue',
    'src/views/ScriptEditor.vue',
    'src/views/ScriptList.vue',
  ]

  for (const componentName of ['AiAppShell', 'AiAppHeader']) {
    const consumers = sourceFiles
      .filter(relativePath => read(relativePath).includes(`<${componentName}`))
      .sort()

    assert.deepEqual(consumers, expectedConsumers)
  }
})

test('PPT editor leaves viewport sizing, gutters, and header chrome to the shared shell', () => {
  const ppt = read('src/views/PptEditor.vue')
  const rootRules = ppt.match(/^\.ppt-agent-page\s*\{[^}]*\}/gm) || []

  assert.equal(
    rootRules.length,
    1,
    'PptEditor must keep one consolidated business-root rule'
  )
  assert.doesNotMatch(rootRules[0], /height:\s*calc\(100d?vh/)
  assert.match(rootRules[0], /\bheight:\s*100%/)
  assert.match(rootRules[0], /\bpadding:\s*0;/)
  assert.doesNotMatch(
    ppt,
    /\.(?:agent-hero|hero-title-line|hero-actions|materials-trigger|landing-history-button)\b/
  )
  assert.doesNotMatch(ppt, /\.(?:creation-setup-head|setup-back-button)\b/)
  assert.doesNotMatch(
    ppt,
    /\.creation-landing__content\s*\{[^}]*\bmin-height:\s*0;/s
  )
})
