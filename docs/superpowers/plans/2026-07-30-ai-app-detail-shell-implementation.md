# AI Application Detail Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one reusable AI application detail shell and migrate PPT creation, PPT history, script creation, and both editors to the approved landing/task/workspace hierarchy.

**Architecture:** Introduce four focused Vue components (`AiAppShell`, `AiAppHeader`, `AiAppContent`, `AiAppSection`) plus one shared stylesheet that consumes existing `--ds-*` tokens. Route metadata will explicitly declare flush AI application pages, while each page chooses its runtime mode and width; this removes path-prefix layout inference and page-owned outer gutters.

**Tech Stack:** Vue 3 Composition API, Vue Router, Element Plus icons and controls, CSS custom properties, Node built-in test runner, Playwright, Vite.

---

## Scope and file map

### Create

- `frontend/user/src/components/ai-apps/AiAppShell.vue` — owns AI application page mode and the only outer gutter.
- `frontend/user/src/components/ai-apps/AiAppHeader.vue` — owns parent navigation, application identity, H1, status, and header actions.
- `frontend/user/src/components/ai-apps/AiAppContent.vue` — owns `wide`, `standard`, `reading`, and `fluid` widths.
- `frontend/user/src/components/ai-apps/AiAppSection.vue` — owns L1 business-section structure and density.
- `frontend/user/src/styles/ai-app-shell.css` — responsive spacing and shared visual contract.
- `frontend/user/tests/ai-app-shell-contract.test.mjs` — source-level component, route, and migration contract.
- `frontend/user/tests/ai-app-detail-shell.spec.js` — browser-level semantics, layout, and responsive assertions.

### Modify

- `frontend/user/src/main.js` — import the shared AI application stylesheet.
- `frontend/user/src/router/index.js` — mark AI application routes with explicit shell metadata.
- `frontend/user/src/components/workspace/WorkspaceShell.vue` — remove route-prefix flush inference.
- `frontend/user/src/views/PptEditor.vue` — migrate landing, setup, and workspace states.
- `frontend/user/src/views/PptGenerator.vue` — migrate the legacy generator task page.
- `frontend/user/src/views/PptHistoryDetail.vue` — use stable parent navigation and the task shell.
- `frontend/user/src/views/ScriptList.vue` — migrate script and PPT preparation landing states without changing the resource-center route.
- `frontend/user/src/views/ScriptEditor.vue` — migrate to the workspace shell and single visible H1.
- `frontend/user/src/styles/script-editor-v2.css` — remove outer-shell responsibilities after the editor migration.

### Delete after all consumers migrate

- `frontend/user/src/components/ai-apps/AiAppDetailHeader.vue` — replaced by `AiAppHeader.vue`.

### Version-control note

The current `/Users/liuyixing/项目/OREP` workspace has no root `.git` directory. Do not initialize Git as part of this work. If execution later occurs inside a tracked clone, use the commit message listed at the end of each task.

---

### Task 1: Lock the shared-shell contract with a failing source test

**Files:**

- Create: `frontend/user/tests/ai-app-shell-contract.test.mjs`

- [ ] **Step 1: Add the initial contract test**

```js
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import test from 'node:test'

const read = relativePath => readFileSync(
  new URL(`../${relativePath}`, import.meta.url),
  'utf8'
)

test('AI app shell exposes only approved modes and widths', () => {
  const shell = read('src/components/ai-apps/AiAppShell.vue')
  const content = read('src/components/ai-apps/AiAppContent.vue')

  assert.match(shell, /\\['landing', 'task', 'workspace'\\]/)
  assert.match(content, /\\['wide', 'standard', 'reading', 'fluid'\\]/)
  assert.match(shell, /<slot name="header"/)
  assert.match(shell, /<AiAppContent/)
})

test('AI app header owns explicit parent navigation and one default h1', () => {
  const header = read('src/components/ai-apps/AiAppHeader.vue')

  assert.match(header, /:to="backTo"/)
  assert.match(header, /\\{\\{ backLabel \\}\\}/)
  assert.match(header, /<h1[^>]*>\\{\\{ title \\}\\}<\\/h1>/)
  assert.match(header, /<slot name="actions"/)
  assert.doesNotMatch(header, /to="\\/ai-apps"/)
})

test('AI app routes explicitly opt into a flush main region', () => {
  const router = read('src/router/index.js')
  const workspaceShell = read('src/components/workspace/WorkspaceShell.vue')

  for (const routePath of [
    '/script-editor',
    '/script-editor/detail/:scriptId',
    '/script-editor/template/:templateId',
    '/ppt-generator',
    '/ppt-editor',
    '/ppt-history/:id'
  ]) {
    const escaped = routePath.replace(/[/:]/g, match => `\\\\${match}`)
    assert.match(router, new RegExp(`path: '${escaped}'[\\\\s\\\\S]*?flushMain: true`))
  }

  assert.match(workspaceShell, /Boolean\\(route\\.meta\\?\\.flushMain\\)/)
  assert.doesNotMatch(workspaceShell, /path\\.startsWith\\('\\/script-editor'\\)/)
  assert.doesNotMatch(workspaceShell, /path\\.startsWith\\('\\/ppt-editor'\\)/)
})

test('PPT and script views consume the new shell', () => {
  const ppt = read('src/views/PptEditor.vue')
  const scriptList = read('src/views/ScriptList.vue')
  const scriptEditor = read('src/views/ScriptEditor.vue')

  assert.match(ppt, /<AiAppShell/)
  assert.match(ppt, /:mode="pptShellMode"/)
  assert.match(scriptList, /<AiAppShell/)
  assert.match(scriptEditor, /<AiAppShell[^>]*mode="workspace"/)
  assert.doesNotMatch(ppt, /AiAppDetailHeader/)
  assert.doesNotMatch(scriptEditor, /AiAppDetailHeader/)
})
```

- [ ] **Step 2: Run the test and verify the intended failure**

Run:

```bash
cd frontend/user
node --test tests/ai-app-shell-contract.test.mjs
```

Expected: FAIL with `ENOENT` for `AiAppShell.vue`.

- [ ] **Step 3: Record the checkpoint**

If running in a tracked clone:

```bash
git add frontend/user/tests/ai-app-shell-contract.test.mjs
git commit -m "test: define AI app shell contract"
```

---

### Task 2: Implement the four shared components and shared styles

**Files:**

- Create: `frontend/user/src/components/ai-apps/AiAppShell.vue`
- Create: `frontend/user/src/components/ai-apps/AiAppHeader.vue`
- Create: `frontend/user/src/components/ai-apps/AiAppContent.vue`
- Create: `frontend/user/src/components/ai-apps/AiAppSection.vue`
- Create: `frontend/user/src/styles/ai-app-shell.css`
- Modify: `frontend/user/src/main.js`
- Test: `frontend/user/tests/ai-app-shell-contract.test.mjs`

- [ ] **Step 1: Implement `AiAppContent.vue`**

```vue
<template>
  <div class="ai-app-content" :class="`is-${width}`">
    <slot />
  </div>
</template>

<script setup>
defineProps({
  width: {
    type: String,
    default: 'wide',
    validator: value => ['wide', 'standard', 'reading', 'fluid'].includes(value),
  },
})
</script>
```

- [ ] **Step 2: Implement `AiAppShell.vue`**

```vue
<template>
  <section class="ai-app-shell" :class="[`is-${mode}`, `width-${width}`]">
    <AiAppContent :width="width" class="ai-app-shell__header-wrap">
      <slot name="header" />
    </AiAppContent>
    <AiAppContent :width="width" class="ai-app-shell__body">
      <slot />
    </AiAppContent>
  </section>
</template>

<script setup>
import AiAppContent from './AiAppContent.vue'

defineProps({
  mode: {
    type: String,
    required: true,
    validator: value => ['landing', 'task', 'workspace'].includes(value),
  },
  width: {
    type: String,
    default: 'wide',
    validator: value => ['wide', 'standard', 'reading', 'fluid'].includes(value),
  },
})
</script>
```

- [ ] **Step 3: Implement `AiAppHeader.vue`**

```vue
<template>
  <header class="ai-app-header" :class="`is-${mode}`">
    <div class="ai-app-header__main">
      <RouterLink
        :to="backTo"
        class="ai-app-header__back"
        :aria-label="`返回${backLabel}`"
      >
        <ArrowLeft aria-hidden="true" />
        <span>{{ backLabel }}</span>
      </RouterLink>

      <span class="ai-app-header__divider" aria-hidden="true"></span>

      <span class="ai-app-header__icon" :class="`is-${app}`" aria-hidden="true">
        <component :is="applicationIcon" />
      </span>

      <div class="ai-app-header__copy">
        <span v-if="context" class="ai-app-header__context">{{ context }}</span>
        <slot name="title">
          <h1>{{ title }}</h1>
        </slot>
        <p v-if="subtitle">{{ subtitle }}</p>
      </div>

      <div v-if="$slots.localNavigation" class="ai-app-header__local-nav">
        <slot name="localNavigation" />
      </div>
    </div>

    <div v-if="status || $slots.actions" class="ai-app-header__right">
      <span v-if="status" class="ai-app-header__status" role="status" aria-live="polite">
        {{ status }}
      </span>
      <div v-if="$slots.actions" class="ai-app-header__actions">
        <slot name="actions" />
      </div>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { ArrowLeft, Document, Picture } from '@element-plus/icons-vue'
import { RouterLink } from 'vue-router'

const props = defineProps({
  mode: {
    type: String,
    default: 'landing',
    validator: value => ['landing', 'task', 'workspace'].includes(value),
  },
  app: {
    type: String,
    required: true,
    validator: value => ['ppt', 'script'].includes(value),
  },
  backLabel: {
    type: String,
    required: true,
  },
  backTo: {
    type: [String, Object],
    required: true,
  },
  context: {
    type: String,
    default: '',
  },
  title: {
    type: String,
    required: true,
  },
  subtitle: {
    type: String,
    default: '',
  },
  status: {
    type: String,
    default: '',
  },
})

const applicationIcon = computed(() => (
  props.app === 'ppt' ? Picture : Document
))
</script>
```

- [ ] **Step 4: Implement `AiAppSection.vue`**

```vue
<template>
  <section class="ai-app-section" :class="`is-${density}`">
    <header v-if="title || description || $slots.actions" class="ai-app-section__head">
      <div>
        <h2 v-if="title">{{ title }}</h2>
        <p v-if="description">{{ description }}</p>
      </div>
      <div v-if="$slots.actions" class="ai-app-section__actions">
        <slot name="actions" />
      </div>
    </header>
    <div class="ai-app-section__body">
      <slot />
    </div>
  </section>
</template>

<script setup>
defineProps({
  title: {
    type: String,
    default: '',
  },
  description: {
    type: String,
    default: '',
  },
  density: {
    type: String,
    default: 'default',
    validator: value => ['default', 'compact'].includes(value),
  },
})
</script>
```

- [ ] **Step 5: Add `ai-app-shell.css`**

```css
:root {
  --ai-app-page-inset: var(--ds-space-10);
  --ai-app-workspace-inset: var(--ds-space-6);
  --ai-app-header-height: 72px;
  --ai-app-workspace-header-height: 64px;
  --ai-app-content-wide: 1280px;
  --ai-app-content-standard: 1120px;
  --ai-app-content-reading: 880px;
}

.ai-app-shell {
  box-sizing: border-box;
  width: 100%;
  min-height: calc(100vh - var(--workspace-header-height));
  padding: var(--ai-app-page-inset);
  color: var(--ds-ink-2);
  background: transparent;
}

.ai-app-shell.is-workspace {
  height: calc(100vh - var(--workspace-header-height));
  min-height: 0;
  display: grid;
  grid-template-rows: var(--ai-app-workspace-header-height) minmax(0, 1fr);
  padding: 0;
  overflow: hidden;
}

.ai-app-content {
  box-sizing: border-box;
  width: 100%;
  margin-inline: auto;
}

.ai-app-content.is-wide { max-width: var(--ai-app-content-wide); }
.ai-app-content.is-standard { max-width: var(--ai-app-content-standard); }
.ai-app-content.is-reading { max-width: var(--ai-app-content-reading); }
.ai-app-content.is-fluid { max-width: none; }

.ai-app-shell__header-wrap {
  border-bottom: 1px solid var(--ds-line);
}

.ai-app-shell:not(.is-workspace) .ai-app-shell__body {
  margin-top: var(--ds-space-6);
}

.ai-app-shell.is-workspace .ai-app-shell__header-wrap,
.ai-app-shell.is-workspace .ai-app-shell__body {
  min-height: 0;
}

.ai-app-shell.is-workspace .ai-app-shell__header-wrap {
  max-width: none;
  padding-inline: var(--ai-app-workspace-inset);
  background: var(--ds-surface-solid);
}

.ai-app-shell.is-workspace .ai-app-shell__body {
  overflow: hidden;
  padding: var(--ds-space-5) var(--ai-app-workspace-inset) var(--ai-app-workspace-inset);
}

.ai-app-header {
  box-sizing: border-box;
  min-height: var(--ai-app-header-height);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--ds-space-5);
}

.ai-app-header.is-workspace {
  min-height: var(--ai-app-workspace-header-height);
}

.ai-app-header__main,
.ai-app-header__right,
.ai-app-header__actions,
.ai-app-header__local-nav {
  min-width: 0;
  display: flex;
  align-items: center;
}

.ai-app-header__main {
  flex: 1;
  gap: var(--ds-space-3);
}

.ai-app-header__back {
  min-height: var(--ds-btn-height-sm);
  display: inline-flex;
  align-items: center;
  gap: var(--ds-space-2);
  padding: 0 var(--ds-btn-padding-x-sm);
  border-radius: var(--ds-radius-pill);
  color: var(--ds-muted);
  font-size: var(--ds-btn-font-sm);
  font-weight: var(--ds-weight-bold);
  text-decoration: none;
}

.ai-app-header__back:hover {
  color: var(--ds-ink);
  background: var(--ds-btn-ghost-bg-hover);
}

.ai-app-header__back:focus-visible {
  outline: var(--ds-focus-outline);
  outline-offset: var(--ds-focus-offset);
}

.ai-app-header__back svg {
  width: var(--ds-icon-size-sm);
  height: var(--ds-icon-size-sm);
}

.ai-app-header__divider {
  width: 1px;
  height: 28px;
  background: var(--ds-line);
}

.ai-app-header__icon {
  width: 40px;
  height: 40px;
  flex: 0 0 40px;
  display: grid;
  place-items: center;
  border: 1px solid var(--ds-orange-100);
  border-radius: var(--ds-radius-md);
  background: var(--ds-orange-50);
  color: var(--ds-orange-700);
}

.ai-app-header.is-workspace .ai-app-header__icon {
  width: 36px;
  height: 36px;
  flex-basis: 36px;
}

.ai-app-header__icon svg {
  width: var(--ds-icon-size-md);
  height: var(--ds-icon-size-md);
}

.ai-app-header__copy {
  min-width: 0;
}

.ai-app-header__copy h1,
.ai-app-header__copy p {
  margin: 0;
}

.ai-app-header__copy h1 {
  overflow: hidden;
  color: var(--ds-ink);
  font-size: var(--ds-text-h1);
  line-height: 1.3;
  font-weight: var(--ds-weight-bold);
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ai-app-header.is-workspace .ai-app-header__copy h1 {
  font-size: 20px;
  line-height: 1.25;
}

.ai-app-header__copy p,
.ai-app-header__status {
  color: var(--ds-muted);
  font-size: var(--ds-text-caption);
  line-height: 1.45;
}

.ai-app-header__copy p {
  margin-top: var(--ds-space-1);
}

.ai-app-header__context {
  display: block;
  margin-bottom: var(--ds-space-1);
  color: var(--ds-muted);
  font-size: var(--ds-text-label);
  font-weight: var(--ds-weight-bold);
}

.ai-app-header__right {
  flex: 0 0 auto;
  justify-content: flex-end;
  gap: var(--ds-space-3);
}

.ai-app-header__actions,
.ai-app-header__local-nav {
  gap: var(--ds-space-2);
}

.ai-app-section {
  border: 1px solid var(--ds-card-border);
  border-radius: var(--ds-radius-lg);
  background: var(--ds-card-bg);
  box-shadow: var(--ds-card-shadow);
}

.ai-app-section__head,
.ai-app-section__body {
  padding: var(--ds-space-6);
}

.ai-app-section.is-compact .ai-app-section__head,
.ai-app-section.is-compact .ai-app-section__body {
  padding: var(--ds-space-4);
}

.ai-app-section__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--ds-space-6);
  border-bottom: 1px solid var(--ds-line);
}

.ai-app-section__head h2,
.ai-app-section__head p {
  margin: 0;
}

.ai-app-section__head h2 {
  color: var(--ds-ink);
  font-size: var(--ds-text-h3);
  line-height: 1.3;
}

.ai-app-section__head p {
  margin-top: var(--ds-space-1);
  color: var(--ds-muted);
  font-size: var(--ds-text-caption);
  line-height: 1.5;
}

@media (max-width: 1439px) {
  :root { --ai-app-page-inset: var(--ds-space-8); }
}

@media (max-width: 1199px) {
  :root { --ai-app-page-inset: var(--ds-space-6); }
}

@media (max-width: 767px) {
  :root {
    --ai-app-page-inset: var(--ds-space-4);
    --ai-app-workspace-inset: var(--ds-space-4);
  }

  .ai-app-shell:not(.is-workspace) {
    padding-bottom: 96px;
  }

  .ai-app-header {
    min-height: 64px;
    gap: var(--ds-space-2);
  }

  .ai-app-header__back {
    width: 40px;
    min-width: 40px;
    height: 40px;
    justify-content: center;
    padding: 0;
  }

  .ai-app-header__back span,
  .ai-app-header__divider,
  .ai-app-header__copy p {
    display: none;
  }

  .ai-app-header__icon {
    width: 36px;
    height: 36px;
    flex-basis: 36px;
  }

  .ai-app-header__copy h1 {
    font-size: 20px;
  }

  .ai-app-header__right {
    max-width: 44%;
  }

  .ai-app-header__actions > :not(:last-child) {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .ai-app-header__back {
    transition-duration: 0.01ms;
  }
}
```

- [ ] **Step 6: Import the stylesheet after workspace primitives**

Add to `frontend/user/src/main.js` immediately after `workspace-components.css`:

```js
import './styles/ai-app-shell.css'
```

- [ ] **Step 7: Run the contract test**

Run:

```bash
cd frontend/user
node --test tests/ai-app-shell-contract.test.mjs
```

Expected: the component-interface tests PASS; route and view migration tests still FAIL.

- [ ] **Step 8: Record the checkpoint**

If running in a tracked clone:

```bash
git add frontend/user/src/components/ai-apps frontend/user/src/styles/ai-app-shell.css frontend/user/src/main.js
git commit -m "feat: add unified AI app shell components"
```

---

### Task 3: Make route shell ownership explicit

**Files:**

- Modify: `frontend/user/src/router/index.js`
- Modify: `frontend/user/src/components/workspace/WorkspaceShell.vue`
- Test: `frontend/user/tests/ai-app-shell-contract.test.mjs`
- Test: `frontend/user/tests/workspace-route-shell-stability.spec.js`

- [ ] **Step 1: Add explicit route metadata**

Apply these metadata values without changing authentication or module grouping:

```js
{
  path: '/script-editor',
  name: 'ScriptList',
  component: () => import('../views/ScriptList.vue'),
  beforeEnter: (to) => {
    if (to.query.tab === 'topic') return '/training/today'
    if (to.query.tab === 'materials') {
      const query = { ...to.query }
      delete query.tab
      return { path: '/resource-center', query }
    }
    return true
  },
  meta: {
    requiresAuth: true,
    moduleGroup: 'aiApps',
    flushMain: true,
    aiAppMode: 'landing'
  }
},
{
  path: '/script-editor/detail/:scriptId',
  name: 'ScriptEditor',
  component: () => import('../views/ScriptEditor.vue'),
  meta: {
    requiresAuth: true,
    moduleGroup: 'aiApps',
    flushMain: true,
    aiAppMode: 'workspace'
  }
},
{
  path: '/script-editor/template/:templateId',
  name: 'ScriptEditorTemplate',
  component: () => import('../views/ScriptEditor.vue'),
  meta: {
    requiresAuth: true,
    moduleGroup: 'aiApps',
    flushMain: true,
    aiAppMode: 'workspace'
  }
},
{
  path: '/ppt-generator',
  name: 'PptGenerator',
  component: () => import('../views/PptGenerator.vue'),
  meta: {
    requiresAuth: true,
    moduleGroup: 'aiApps',
    flushMain: true,
    aiAppMode: 'task'
  }
},
{
  path: '/ppt-editor',
  name: 'PptEditor',
  component: () => import('../views/PptEditor.vue'),
  meta: {
    requiresAuth: true,
    moduleGroup: 'aiApps',
    flushMain: true,
    aiAppMode: 'landing'
  }
},
{
  path: '/ppt-history/:id',
  name: 'PptHistoryDetail',
  component: () => import('../views/PptHistoryDetail.vue'),
  meta: {
    requiresAuth: true,
    moduleGroup: 'aiApps',
    flushMain: true,
    aiAppMode: 'task'
  }
}
```

Keep the existing inline `beforeEnter` body for `/script-editor`; only the metadata changes.

- [ ] **Step 2: Remove prefix inference from `WorkspaceShell.vue`**

Replace `isFlushPage` with:

```js
const isFlushPage = computed(() => Boolean(route.meta?.flushMain))
```

Do not change `shouldAnimateWorkspaceRoute` in this step; its existing route-transition exclusions are behaviorally separate.

- [ ] **Step 3: Run the source contract**

Run:

```bash
cd frontend/user
node --test tests/ai-app-shell-contract.test.mjs
```

Expected: route-shell test PASS; view migration test still FAIL.

- [ ] **Step 4: Run the existing shell-stability browser test**

Terminal A:

```bash
cd frontend/user
npm run dev -- --host 127.0.0.1
```

Terminal B:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://127.0.0.1:5174 npx playwright test tests/workspace-route-shell-stability.spec.js
```

Expected: 1 passed.

- [ ] **Step 5: Record the checkpoint**

If running in a tracked clone:

```bash
git add frontend/user/src/router/index.js frontend/user/src/components/workspace/WorkspaceShell.vue
git commit -m "refactor: make AI app shell routing explicit"
```

---

### Task 4: Migrate `PptEditor.vue` landing, setup, and workspace states

**Files:**

- Modify: `frontend/user/src/views/PptEditor.vue`
- Test: `frontend/user/tests/ai-app-shell-contract.test.mjs`

- [ ] **Step 1: Replace the outer root with `AiAppShell`**

Replace the outermost opening element:

```vue
<div :class="['ppt-agent-page', `is-${pptView}-view`]">
```

with:

```vue
<AiAppShell :mode="pptShellMode" :width="pptShellWidth">
```

Replace the matching outermost closing `</div>` immediately before `</template>` with `</AiAppShell>`. Leave all existing drawers, dialogs, landing body, setup body, and workspace body in their current order.

- [ ] **Step 2: Insert one shared header slot and delete the three old headers**

Insert immediately after the new `<AiAppShell>` opening tag:

```vue
<template #header>
  <AiAppHeader
    app="ppt"
    :mode="pptShellMode"
    :back-label="pptBackLabel"
    :back-to="pptBackTo"
    :context="pptHeaderContext"
    :title="pptHeaderTitle"
    :subtitle="pptHeaderSubtitle"
    :status="pptHeaderStatus"
  >
    <template #actions>
      <button
        type="button"
        class="ppt-icon-button"
        aria-label="最近记录"
        title="最近记录"
        @click="openHistoryDrawer"
      >
        <el-icon><FolderOpened /></el-icon>
      </button>
      <button
        v-if="pptView === 'workspace'"
        type="button"
        class="ppt-icon-button"
        aria-label="调整生成设置"
        title="调整生成设置"
        @click="openSetup"
      >
        <el-icon><Setting /></el-icon>
      </button>
      <button
        v-if="pptView === 'workspace'"
        type="button"
        class="ppt-icon-button"
        aria-label="新建 PPT"
        title="新建 PPT"
        @click="createNewPpt"
      >
        <el-icon><Plus /></el-icon>
      </button>
    </template>
  </AiAppHeader>
</template>
```

Delete the complete `AiAppDetailHeader` blocks currently guarded by:

```vue
v-if="pptView === 'workspace'"
```

and nested inside `.creation-landing` and `.creation-setup-shell`.

- [ ] **Step 3: Add the shell computed values**

Add beside the existing `pptView` state:

```js
const pptShellMode = computed(() => {
  if (pptView.value === 'workspace') return 'workspace'
  if (pptView.value === 'setup') return 'task'
  return 'landing'
})

const pptShellWidth = computed(() => (
  pptView.value === 'workspace' ? 'fluid' : pptView.value === 'setup' ? 'standard' : 'wide'
))

const pptBackLabel = computed(() => (
  pptView.value === 'landing' ? 'AI 应用中心' : 'PPT 制作'
))

const pptBackTo = computed(() => (
  pptView.value === 'landing'
    ? '/ai-apps'
    : { path: '/ppt-editor', query: { view: 'landing' } }
))

const pptHeaderContext = computed(() => (
  pptView.value === 'workspace' ? 'PPT 制作 · 编辑器' : ''
))

const pptHeaderTitle = computed(() => {
  if (pptView.value === 'workspace') {
    return String(materialForm.value.project_name || '').trim() || '未命名 PPT'
  }
  return pptView.value === 'setup' ? '创建 PPT' : 'PPT 制作'
})

const pptHeaderSubtitle = computed(() => {
  if (pptView.value === 'landing') return '把项目资料整理成可编辑的路演 PPT'
  if (pptView.value === 'setup') return '上传材料并确认生成设置'
  return ''
})

const pptHeaderStatus = computed(() => {
  if (pptView.value !== 'workspace') return ''
  if (isRunning.value) return jobSubtitle.value
  return jobId.value ? '已保存到最近记录' : ''
})
```

- [ ] **Step 4: Make the task back link change local state instead of leaving the route**

Because `AiAppHeader` uses `RouterLink`, synchronize the route query with `pptView`:

```js
const route = useRoute()
const router = useRouter()

watch(
  () => route.query.view,
  view => {
    if (view === 'landing') {
      pptView.value = 'landing'
      router.replace('/ppt-editor')
      return
    }
    if (view === 'setup' && pptView.value !== 'workspace') {
      pptView.value = 'setup'
      return
    }
    if (!view && pptView.value === 'setup') pptView.value = 'landing'
  },
  { immediate: true }
)

function openSetup() {
  advancedSettingsOpen.value = false
  pptView.value = 'setup'
  router.replace({ path: '/ppt-editor', query: { ...route.query, view: 'setup' } })
}
```

Both setup and workspace link to the explicit `view=landing` parent state. The watcher restores `pptView = 'landing'` and canonicalizes the URL back to `/ppt-editor`, so same-route navigation works even when the editor is already mounted.

- [ ] **Step 5: Remove page-owned outer gutters and full-height landing card styles**

Delete or neutralize these legacy responsibilities:

```css
.ppt-agent-page.is-landing-view,
.ppt-agent-page.is-setup-view {
  padding: 0;
}

.creation-landing {
  width: 100%;
  min-height: 0;
  margin: 0;
  overflow: visible;
}

.creation-landing__content {
  min-height: 0;
}
```

Delete selectors that style `.creation-landing__head`, `.creation-setup__head`, `.ppt-page-head`, or `.creation-view-head`; the shared `AiAppHeader` now owns those areas.

- [ ] **Step 6: Update imports**

Use:

```js
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AiAppHeader from '@/components/ai-apps/AiAppHeader.vue'
import AiAppShell from '@/components/ai-apps/AiAppShell.vue'
```

Preserve every other existing import and remove only `AiAppDetailHeader`.

- [ ] **Step 7: Run the contract test and build**

Run:

```bash
cd frontend/user
node --test tests/ai-app-shell-contract.test.mjs
npm run build
```

Expected: the PPT migration assertions PASS; the script migration assertions still FAIL; Vite build exits 0.

- [ ] **Step 8: Record the checkpoint**

If running in a tracked clone:

```bash
git add frontend/user/src/views/PptEditor.vue
git commit -m "refactor: migrate PPT editor to AI app shell"
```

---

### Task 5: Migrate legacy PPT generator and PPT history

**Files:**

- Modify: `frontend/user/src/views/PptGenerator.vue`
- Modify: `frontend/user/src/views/PptHistoryDetail.vue`
- Test: `frontend/user/tests/ai-app-shell-contract.test.mjs`

- [ ] **Step 1: Wrap `PptGenerator.vue` as a task**

Replace the root `<div class="ppt-generator">` with `<AiAppShell mode="task" width="standard">` and replace its matching outer closing tag with `</AiAppShell>`.

Delete the existing `.ppt-generator__header` block. Insert this header and progress section before the existing `.step-content`:

```vue
<template #header>
  <AiAppHeader
    app="ppt"
    mode="task"
    back-label="PPT 制作"
    back-to="/ppt-editor"
    title="创建 PPT"
    subtitle="填写项目信息并确认生成步骤"
  />
</template>

<AiAppSection title="创建进度" :description="currentStepLabel">
  <el-steps :active="currentStep" finish-status="success" align-center>
    <el-step title="选择领域" description="选择技术方向" />
    <el-step title="填写问卷" description="填写项目信息" />
    <el-step title="确认大纲" description="预览并确认" />
    <el-step title="生成 PPT" description="等待生成完成" />
  </el-steps>
</AiAppSection>
```

Wrap the existing `.step-content` and `.history-section` siblings in `<div class="ppt-generator__task-content">...</div>` without changing their internal templates. Remove the current “返回首页” button, `.hero-panel`, `.hero-status-card`, and the old `.steps-container`.

- [ ] **Step 2: Use shell spacing in `PptGenerator.vue`**

Replace root-level layout styles with:

```css
.ppt-generator__task-content {
  display: grid;
  gap: var(--ds-space-6);
  margin-top: var(--ds-space-6);
}

.steps-container,
.step-content,
.history-section {
  width: 100%;
  margin-inline: 0;
}
```

Remove the local page background, `min-height: 100vh`, outer padding, and legacy hero styles.

- [ ] **Step 3: Wrap `PptHistoryDetail.vue` as a task**

Replace the root `<div class="ppt-history-detail">` with `<AiAppShell mode="task" width="wide">` and replace its matching outer closing tag with `</AiAppShell>`. Delete the existing `.page-header` block and insert:

```vue
<template #header>
  <AiAppHeader
    app="ppt"
    mode="task"
    back-label="PPT 制作"
    back-to="/ppt-editor"
    :title="task?.project_name || 'PPT 历史详情'"
    :subtitle="`${taskStatusText} · ${htmlPages.length} 页 · ${formatDate(task?.created_at)}`"
  >
    <template #actions>
      <el-button
        v-if="task?.status === 'completed'"
        :type="deliverabilityVerdict.status === 'blocked' ? 'warning' : 'primary'"
        :loading="downloadingPpt"
        @click="downloadPpt"
      >
        <el-icon><Download /></el-icon>
        {{ downloadActionText }}
      </el-button>
    </template>
  </AiAppHeader>
</template>
```

Rename the existing `v-loading="loading"` content wrapper class from `content-card` to `ppt-history-detail__content`; do not change its child template.

Extract the existing nested download-label expression into:

```js
const downloadActionText = computed(() => {
  if (pendingDownloadAfterFix.value) {
    if (deliverabilityVerdict.value.status === 'blocked') return '查看并继续下载'
    if (deliverabilityVerdict.value.status === 'warning') return '继续下载当前版本'
    return '继续下载'
  }
  if (deliverabilityVerdict.value.status === 'blocked') return '查看下载条件'
  if (deliverabilityVerdict.value.status === 'warning') return '下载当前版本'
  return '下载 PPT'
})
```

Remove the local `router.back()` page-header button.

- [ ] **Step 4: Add imports and remove obsolete imports**

Both files use:

```js
import AiAppHeader from '@/components/ai-apps/AiAppHeader.vue'
import AiAppSection from '@/components/ai-apps/AiAppSection.vue'
import AiAppShell from '@/components/ai-apps/AiAppShell.vue'
```

`PptHistoryDetail.vue` only needs `AiAppSection` if an existing top-level information group is converted in this task; otherwise omit that import.

- [ ] **Step 5: Extend the source contract**

Add:

```js
test('legacy PPT task and history pages use task shells with stable parents', () => {
  const generator = read('src/views/PptGenerator.vue')
  const history = read('src/views/PptHistoryDetail.vue')

  assert.match(generator, /<AiAppShell[^>]*mode="task"[^>]*width="standard"/)
  assert.match(generator, /back-label="PPT 制作"/)
  assert.doesNotMatch(generator, /返回首页/)
  assert.match(history, /<AiAppShell[^>]*mode="task"[^>]*width="wide"/)
  assert.match(history, /back-to="\\/ppt-editor"/)
  assert.doesNotMatch(history, /router\\.back\\(\\)/)
})
```

- [ ] **Step 6: Run tests and build**

Run:

```bash
cd frontend/user
node --test tests/ai-app-shell-contract.test.mjs
npm run build
```

Expected: PPT task/history contract PASS; build exits 0.

- [ ] **Step 7: Record the checkpoint**

If running in a tracked clone:

```bash
git add frontend/user/src/views/PptGenerator.vue frontend/user/src/views/PptHistoryDetail.vue frontend/user/tests/ai-app-shell-contract.test.mjs
git commit -m "refactor: align PPT task and history pages"
```

---

### Task 6: Migrate the script landing without affecting resource center

**Files:**

- Modify: `frontend/user/src/views/ScriptList.vue`
- Test: `frontend/user/tests/ai-app-shell-contract.test.mjs`

- [ ] **Step 1: Add route-aware shell activation**

Add:

```js
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AiAppHeader from '../components/ai-apps/AiAppHeader.vue'
import AiAppShell from '../components/ai-apps/AiAppShell.vue'

const route = useRoute()
const router = useRouter()

const isAiAppPreparation = computed(() => (
  route.path === '/script-editor'
  && (activePrepKey.value === 'script' || activePrepKey.value === 'ppt')
))

const prepApp = computed(() => activePrepKey.value === 'ppt' ? 'ppt' : 'script')
const prepTitle = computed(() => activePrepKey.value === 'ppt' ? 'PPT 制作' : '讲稿制作')
const prepSubtitle = computed(() => (
  activePrepKey.value === 'ppt'
    ? '准备路演 PPT'
    : '创建、继续编辑和管理讲稿'
))
```

If `useRouter` or `computed` is already imported, merge imports rather than duplicate them.

- [ ] **Step 2: Wrap only AI application preparation content**

Inside `.prep-workbench`, render:

```vue
<AiAppShell
  v-if="isAiAppPreparation"
  mode="landing"
  width="wide"
  class="prep-ai-app-shell"
>
  <template #header>
    <AiAppHeader
      :app="prepApp"
      mode="landing"
      back-label="AI 应用中心"
      back-to="/ai-apps"
      :title="prepTitle"
      :subtitle="prepSubtitle"
    >
      <template #actions>
        <button
          v-if="activePrepKey === 'script'"
          type="button"
          class="header-button"
          @click="openTemplateDialog"
        >
          <el-icon aria-hidden="true"><DocumentAdd /></el-icon>
          <span>新建讲稿</span>
        </button>
        <button
          v-else
          type="button"
          class="header-button"
          @click="router.push('/ppt-editor')"
        >
          <el-icon aria-hidden="true"><Collection /></el-icon>
          <span>进入 PPT 工作台</span>
        </button>
      </template>
    </AiAppHeader>
  </template>

  <section class="planning-board">
    <PptWorkspace
      v-if="activePrepKey === 'ppt'"
      :resources="resources"
      :stages="dashboard.stages || []"
      @open-editor="router.push('/ppt-editor')"
    />
    <ScriptWorkspace
      v-else
      :scripts="scripts"
      :templates="templates"
      @create="openTemplateDialog"
      @open="openScript"
    />
  </section>
</AiAppShell>
```

Reuse the actual existing `PptWorkspace` and `ScriptWorkspace` prop/event bindings from the current template. Do not duplicate or rename business events.

Keep the existing non-AI branches for `resource-center`, topic preparation, and other preparation modes outside this shell.

- [ ] **Step 3: Remove the old `AiAppDetailHeader` block**

Delete:

```vue
<AiAppDetailHeader
  v-if="activePrepKey === 'script' || activePrepKey === 'ppt'"
  ...
/>
```

Remove its import.

- [ ] **Step 4: Remove duplicate page gutters only for AI preparation**

Use:

```css
.prep-workbench.mode-script,
.prep-workbench.mode-ppt {
  min-height: calc(100vh - var(--workspace-header-height));
  padding: 0;
  background: transparent;
}

.prep-ai-app-shell {
  min-height: calc(100vh - var(--workspace-header-height));
}

.prep-ai-app-shell .planning-board {
  min-height: 0;
  overflow: visible;
  border: 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
}
```

Do not change `.prep-workbench.mode-materials`; `/resource-center` remains governed by the existing workspace shell contract.

- [ ] **Step 5: Run contract and resource-center regression tests**

Run:

```bash
cd frontend/user
node --test tests/ai-app-shell-contract.test.mjs
node --test tests/resource-center-navigation-contract.test.mjs
node --test tests/resource-center-finder-contract.test.mjs
npm run build
```

Expected: all Node tests PASS and build exits 0.

- [ ] **Step 6: Record the checkpoint**

If running in a tracked clone:

```bash
git add frontend/user/src/views/ScriptList.vue
git commit -m "refactor: migrate script landing to AI app shell"
```

---

### Task 7: Migrate `ScriptEditor.vue` to the workspace shell

**Files:**

- Modify: `frontend/user/src/views/ScriptEditor.vue`
- Modify: `frontend/user/src/styles/script-editor-v2.css`
- Test: `frontend/user/tests/ai-app-shell-contract.test.mjs`

- [ ] **Step 1: Replace the root and duplicated header**

Replace the root `<div class="script-editor">` with `<AiAppShell mode="workspace" width="fluid">` and its matching outer closing tag with `</AiAppShell>`. Delete the current root `h1.sr-only` and the complete `AiAppDetailHeader` block. Insert immediately after the new shell opening:

```vue
<template #header>
  <AiAppHeader
    app="script"
    mode="workspace"
    back-label="讲稿列表"
    back-to="/script-editor"
    context="讲稿制作 · 编辑器"
    title="讲稿编辑器"
    :status="saveText || (loadingScript ? '正在加载' : '自动保存')"
  >
    <template #title>
      <h1 class="script-title-heading">
        <el-input
          v-model="scriptTitle"
          placeholder="讲稿标题"
          class="title-input"
          maxlength="100"
          aria-label="讲稿标题"
          @blur="autoSave"
        />
      </h1>
    </template>
    <template #actions>
      <el-button class="template-btn" @click="showSaveAsTemplate = true">
        <el-icon><FolderAdd /></el-icon>
        <span>存为模板</span>
      </el-button>
      <el-button type="primary" class="export-btn" @click="exportPdf" :loading="exporting">
        <el-icon><Download /></el-icon>
        <span>导出 PDF</span>
      </el-button>
    </template>
  </AiAppHeader>
</template>
```

Delete the root `<h1 class="sr-only">` and the local “返回列表” button. The editable title now sits inside the single visible H1.

- [ ] **Step 2: Update imports**

Use:

```js
import AiAppHeader from '../components/ai-apps/AiAppHeader.vue'
import AiAppShell from '../components/ai-apps/AiAppShell.vue'
```

Remove `AiAppDetailHeader` and remove `ArrowLeft` only if no remaining error-state or body control uses it.

- [ ] **Step 3: Move shell layout responsibilities out of `script-editor-v2.css`**

Replace the final root/header/body overrides with:

```css
.script-editor {
  min-height: 0;
}

.script-title-heading {
  width: min(46vw, 520px);
  margin: 0;
}

.editor-body {
  min-height: 0;
  height: 100%;
  display: flex;
  gap: var(--ds-space-4);
  padding: 0;
  overflow: hidden;
}

.editor-state {
  min-height: 100%;
  margin: 0;
}
```

Remove local `.editor-header` height, padding, border, and background rules. Preserve editor-panel, chapter, field, dialog, and narrow-screen business styles.

- [ ] **Step 4: Extend the contract with H1 and stable-parent assertions**

Add:

```js
test('script workspace has one visible editable h1 and a stable list parent', () => {
  const scriptEditor = read('src/views/ScriptEditor.vue')

  assert.match(scriptEditor, /<AiAppShell[^>]*mode="workspace"[^>]*width="fluid"/)
  assert.match(scriptEditor, /back-label="讲稿列表"/)
  assert.match(scriptEditor, /back-to="\\/script-editor"/)
  assert.match(scriptEditor, /<h1 class="script-title-heading">/)
  assert.doesNotMatch(scriptEditor, /<h1 class="sr-only"/)
  assert.doesNotMatch(scriptEditor, /返回列表/)
})
```

- [ ] **Step 5: Run the contract test and build**

Run:

```bash
cd frontend/user
node --test tests/ai-app-shell-contract.test.mjs
npm run build
```

Expected: all source-contract tests PASS and build exits 0.

- [ ] **Step 6: Record the checkpoint**

If running in a tracked clone:

```bash
git add frontend/user/src/views/ScriptEditor.vue frontend/user/src/styles/script-editor-v2.css frontend/user/tests/ai-app-shell-contract.test.mjs
git commit -m "refactor: migrate script editor to AI app workspace"
```

---

### Task 8: Add browser-level layout, semantics, and responsive verification

**Files:**

- Create: `frontend/user/tests/ai-app-detail-shell.spec.js`

- [ ] **Step 1: Add stable API mocks and shell assertions**

```js
import { expect, test } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('orep_user_token', 'ai-app-shell-contract-token')
  })

  await page.route('**/api/ppt/health', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ status: 'ok', image2_configured: true })
  }))
  await page.route('**/api/ppt/providers', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ providers: [] })
  }))
  await page.route('**/api/ppt/templates', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify([])
  }))
  await page.route('**/api/ppt/history', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ jobs: [] })
  }))
  await page.route('**/api/project-prep/bootstrap**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({
      code: 200,
      data: {
        teams: [],
        activeTeamId: null,
        dashboard: {},
        prepSession: null,
        scripts: [],
        scriptTemplates: [],
        resources: []
      }
    })
  }))
})

test('PPT landing has one h1, one explicit parent, and one primary creation action', async ({ page }) => {
  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/ppt-editor')

  await expect(page.locator('.ai-app-shell')).toHaveClass(/is-landing/)
  await expect(page.getByRole('heading', { level: 1, name: 'PPT 制作' })).toBeVisible()
  await expect(page.getByRole('heading', { level: 1 })).toHaveCount(1)
  await expect(page.getByRole('link', { name: '返回AI 应用中心' })).toBeVisible()
  await expect(page.getByRole('button', { name: '开始创建' })).toHaveCount(1)

  const shellBox = await page.locator('.ai-app-shell').boundingBox()
  const headerBox = await page.locator('.ai-app-header').boundingBox()
  expect(shellBox).not.toBeNull()
  expect(headerBox).not.toBeNull()
  expect(headerBox.x - shellBox.x).toBeGreaterThanOrEqual(39)
  expect(headerBox.x - shellBox.x).toBeLessThanOrEqual(41)
})

test('PPT setup uses task semantics and returns to the app landing', async ({ page }) => {
  await page.goto('/ppt-editor')
  await page.getByRole('button', { name: '开始创建' }).click()

  await expect(page).toHaveURL(/\\/ppt-editor\\?view=setup/)
  await expect(page.locator('.ai-app-shell')).toHaveClass(/is-task/)
  await expect(page.getByRole('heading', { level: 1, name: '创建 PPT' })).toBeVisible()
  await expect(page.getByRole('heading', { level: 1 })).toHaveCount(1)
  await expect(page.getByRole('link', { name: '返回PPT 制作' })).toBeVisible()

  await page.getByRole('link', { name: '返回PPT 制作' }).click()
  await expect(page).toHaveURL('/ppt-editor')
  await expect(page.locator('.ai-app-shell')).toHaveClass(/is-landing/)
})

test('script landing shares the shell and resource center keeps its own layout', async ({ page }) => {
  await page.goto('/script-editor')

  await expect(page.locator('.ai-app-shell')).toHaveClass(/is-landing/)
  await expect(page.getByRole('heading', { level: 1, name: '讲稿制作' })).toBeVisible()
  await expect(page.getByRole('link', { name: '返回AI 应用中心' })).toBeVisible()

  await page.goto('/resource-center')
  await expect(page.locator('.ai-app-shell')).toHaveCount(0)
  await expect(page.getByRole('heading', { level: 1, name: '资源中心' })).toBeVisible()
})

test('mobile landing has no horizontal overflow and keeps an accessible return target', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/ppt-editor')

  await expect(page.getByRole('link', { name: '返回AI 应用中心' })).toBeVisible()
  await expect(page.getByRole('heading', { level: 1, name: 'PPT 制作' })).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBe(390)
})
```

- [ ] **Step 2: Run the browser contract**

Terminal A:

```bash
cd frontend/user
npm run dev -- --host 127.0.0.1
```

Terminal B:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://127.0.0.1:5174 npx playwright test tests/ai-app-detail-shell.spec.js
```

Expected: 4 passed.

- [ ] **Step 3: Run related regression tests**

With the same dev server:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://127.0.0.1:5174 npx playwright test \
  tests/ai-app-detail-shell.spec.js \
  tests/workspace-route-shell-stability.spec.js
```

Then run the Node contract separately:

```bash
node --test tests/resource-center-finder-contract.test.mjs
```

Expected: all selected Playwright tests pass and the Node contract passes.

- [ ] **Step 4: Record the checkpoint**

If running in a tracked clone:

```bash
git add frontend/user/tests/ai-app-detail-shell.spec.js
git commit -m "test: verify unified AI app detail shell"
```

---

### Task 9: Remove the legacy header and complete the migration audit

**Files:**

- Delete: `frontend/user/src/components/ai-apps/AiAppDetailHeader.vue`
- Modify: `frontend/user/tests/ai-app-shell-contract.test.mjs`

- [ ] **Step 1: Verify there are no remaining consumers**

Run:

```bash
cd frontend/user
rg -n "AiAppDetailHeader" src
```

Expected: only `src/components/ai-apps/AiAppDetailHeader.vue` matches.

- [ ] **Step 2: Delete the legacy component**

Remove:

```text
frontend/user/src/components/ai-apps/AiAppDetailHeader.vue
```

- [ ] **Step 3: Add the deletion contract**

Append:

```js
test('legacy AI app detail header has no consumers', () => {
  const sources = [
    read('src/views/PptEditor.vue'),
    read('src/views/PptGenerator.vue'),
    read('src/views/PptHistoryDetail.vue'),
    read('src/views/ScriptList.vue'),
    read('src/views/ScriptEditor.vue')
  ].join('\\n')

  assert.doesNotMatch(sources, /AiAppDetailHeader/)
})
```

- [ ] **Step 4: Run all targeted checks**

Run:

```bash
cd frontend/user
node --test tests/ai-app-shell-contract.test.mjs
node --test tests/resource-center-navigation-contract.test.mjs
node --test tests/resource-center-finder-contract.test.mjs
npm run build
```

Expected: all Node tests PASS and Vite build exits 0.

- [ ] **Step 5: Run the final browser suite**

With the development server running:

```bash
cd frontend/user
OREP_E2E_BASE_URL=http://127.0.0.1:5174 npx playwright test \
  tests/ai-app-detail-shell.spec.js \
  tests/workspace-route-shell-stability.spec.js
```

Expected: 5 total tests passed.

- [ ] **Step 6: Manually inspect the approved routes**

At 1440×900 and 390×844, inspect:

```text
/ppt-editor
/ppt-editor?view=setup
/ppt-generator
/script-editor
/script-editor/detail/42
```

For `/script-editor/detail/42`, mock `/api/script/42` with:

```json
{
  "code": 200,
  "data": {
    "id": 42,
    "title": "乡村振兴路演讲稿",
    "sourceType": "manual",
    "content": "[]",
    "roles": "[]"
  }
}
```

Confirm:

- one visible H1 per route;
- return control is always at the far left;
- no duplicated return control in the right action group;
- 40/32/24/16px shell gutters follow the approved breakpoints;
- no full-height empty white landing card;
- one visual primary action per page phase;
- no horizontal overflow at390px;
- workspace title, save status, and actions remain usable.

- [ ] **Step 7: Record the final checkpoint**

If running in a tracked clone:

```bash
git add frontend/user
git commit -m "refactor: standardize AI application detail pages"
```

---

## Self-review

### Spec coverage

- Three shell modes: Tasks 2, 4, 6, and 7.
- One H1 and title semantics: Tasks 2, 4, 5, 7, and 8.
- Stable parent navigation: Tasks 2, 4, 5, 6, 7, and 8.
- One outer gutter owner and four widths: Tasks 2, 3, 4, 6, and 7.
- Open layout and removal of the full-height PPT card: Task 4.
- Header action limit and no duplicate return: Tasks 2, 4, 7, and 8.
- State ownership: existing business states are preserved; Task 7 moves save status into the shared header.
- Responsive layout and mobile overflow: Tasks 2 and 8.
- Accessibility: Tasks 2, 7, and 8.
- Existing route migration: Tasks 3–7.
- Legacy cleanup: Task 9.

### Placeholder scan

The plan contains no `TBD`, `TODO`, unspecified error handling, unnamed tests, or code-block placeholders.

### Type and naming consistency

- Modes are consistently `landing | task | workspace`.
- Widths are consistently `wide | standard | reading | fluid`.
- Header props are consistently `backLabel`, `backTo`, `context`, `title`, `subtitle`, and `status`.
- Runtime Vue attributes use kebab-case and script props use camelCase.
- The legacy `AiAppDetailHeader` name is removed only after every consumer migrates.
