# Workspace Sidebar Button Navigation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert the desktop workspace sidebar into the confirmed icon-only, rounded “button” navigation while preserving route behavior and accessibility.

**Architecture:** Keep `OREP_NAV_ITEMS` and `isOrepRouteActive` as the single navigation source. Limit production changes to the existing sidebar and shared module-icon component; add one focused Playwright contract test that verifies semantics, geometry, tooltip behavior, active state, and the existing mobile breakpoint.

**Tech Stack:** Vue 3 single-file components, Vue Router, scoped CSS, inline SVG, Playwright, Vite.

---

## File Map

- Create `frontend/user/tests/workspace-sidebar-navigation.spec.js`: desktop sidebar visual and accessibility contract.
- Modify `frontend/user/src/components/workspace/WorkspaceSidebar.vue`: icon-only item markup, tooltip, interaction states, and sizing.
- Modify `frontend/user/src/components/workspace/WorkspaceModuleIcon.vue`: unified rounded outline icon paths and 1.9px stroke.
- No change to `frontend/user/src/composables/apple/useOrepNavigation.js`: labels, order, routes, and active-route rules remain authoritative.
- No change to `frontend/user/src/components/workspace/WorkspaceMobileNav.vue`: mobile navigation remains out of scope.

The workspace is not a Git repository, so the commit steps normally required between tasks cannot be executed. Preserve that limitation in the handoff rather than creating repository metadata.

### Task 1: Lock the sidebar contract with a failing Playwright test

**Files:**
- Create: `frontend/user/tests/workspace-sidebar-navigation.spec.js`

- [ ] **Step 1: Write the navigation test**

```js
import { expect, test } from '@playwright/test'

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => {
    localStorage.setItem('orep_user_token', 'workspace-sidebar-test-token')
  })

  await page.route('**/api/**', route => route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify({ code: 200, data: {} }),
  }))
})

test('桌面侧栏使用统一的大号图标扣子并保留可访问名称', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 })
  await page.goto('/training/today')

  const nav = page.getByRole('navigation', { name: '用户端主导航' })
  const links = nav.getByRole('link')
  await expect(links).toHaveCount(7)

  const training = nav.getByRole('link', { name: '训练营', exact: true })
  await expect(training).toHaveClass(/is-active/)
  await expect(training).toHaveCSS('width', '52px')
  await expect(training).toHaveCSS('height', '52px')
  await expect(training).toHaveCSS('border-radius', '16px')
  await expect(training.locator('svg')).toHaveCSS('width', '24px')
  await expect(training.locator('svg')).toHaveCSS('height', '24px')

  const tooltip = training.locator('.workspace-nav__tooltip')
  await expect(tooltip).toHaveText('训练营')
  await expect(tooltip).toHaveCSS('visibility', 'hidden')

  await training.hover()
  await expect(tooltip).toHaveCSS('visibility', 'visible')
  await expect(tooltip).toHaveCSS('opacity', '1')

  await training.focus()
  await expect(tooltip).toHaveCSS('visibility', 'visible')
  await expect(training).toHaveCSS('outline-style', 'solid')
})

test('窄屏继续使用现有移动端导航并隐藏桌面侧栏', async ({ page }) => {
  await page.setViewportSize({ width: 900, height: 900 })
  await page.goto('/training/today')

  await expect(page.locator('.workspace-sidebar')).toHaveCSS('display', 'none')
})
```

- [ ] **Step 2: Run the new test and verify it fails for the current 70px labeled items**

Run:

```bash
cd /Users/liuyixing/项目/OREP/frontend/user
npx playwright test tests/workspace-sidebar-navigation.spec.js
```

Expected: the desktop test fails because the current navigation items are not 52×52px, the SVG is 19px, and `.workspace-nav__tooltip` does not exist.

### Task 2: Implement the icon-only button navigation

**Files:**
- Modify: `frontend/user/src/components/workspace/WorkspaceSidebar.vue:18-30`
- Modify: `frontend/user/src/components/workspace/WorkspaceSidebar.vue:108-199`
- Modify: `frontend/user/src/components/workspace/WorkspaceSidebar.vue:464-478`

- [ ] **Step 1: Replace visible labels with an accessible custom tooltip and switch to outline icons**

Replace the router-link markup with:

```vue
<router-link
  v-for="item in navItems"
  :key="item.path"
  :to="item.path"
  class="workspace-nav__item"
  :class="{ 'is-active': isOrepRouteActive(route, item.path) }"
  :aria-label="item.label"
>
  <span class="workspace-nav__icon" aria-hidden="true">
    <WorkspaceModuleIcon :name="item.group" variant="outline" />
  </span>
  <span class="workspace-nav__tooltip" aria-hidden="true">{{ item.label }}</span>
  <span v-if="item.badge" class="workspace-nav__badge">{{ item.badge }}</span>
</router-link>
```

- [ ] **Step 2: Apply the confirmed button geometry and states**

Replace the existing `.workspace-nav` through `.workspace-nav__badge` rules with:

```css
.workspace-nav {
  flex: 1;
  min-height: 0;
  padding: 18px 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: clamp(6px, 0.9vh, 10px);
}

.workspace-nav__label {
  display: none;
}

.workspace-nav__item {
  position: relative;
  flex: 0 0 52px;
  width: 52px;
  height: 52px;
  border-radius: 16px;
  display: grid;
  place-items: center;
  color: oklch(59% 0.008 260);
  text-decoration: none;
  transition:
    background-color 180ms var(--ds-motion-ease-out),
    color 180ms var(--ds-motion-ease-out),
    box-shadow 180ms var(--ds-motion-ease-out);
}

.workspace-nav__item:hover {
  color: oklch(36% 0.008 260);
  background: oklch(95.2% 0.004 50);
}

.workspace-nav__item.is-active {
  color: oklch(25% 0.008 260);
  background: oklch(92.5% 0.006 50);
  box-shadow: inset 0 0 0 1px oklch(30% 0.008 50 / 0.035);
}

.workspace-nav__item:focus-visible {
  outline: 2px solid var(--ds-orange);
  outline-offset: 3px;
}

.workspace-nav__icon {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  color: currentColor;
}

.workspace-nav__icon svg {
  width: 24px;
  height: 24px;
  display: block;
}

.workspace-nav__tooltip {
  position: absolute;
  left: calc(100% + 12px);
  top: 50%;
  z-index: 20;
  min-height: 34px;
  padding: 0 12px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  color: oklch(98% 0.004 50);
  background: oklch(22% 0.008 260);
  box-shadow: 0 10px 24px oklch(20% 0.01 260 / 0.18);
  font-size: 13px;
  font-weight: 650;
  line-height: 1;
  white-space: nowrap;
  opacity: 0;
  visibility: hidden;
  pointer-events: none;
  transform: translate(4px, -50%);
  transition:
    opacity 160ms var(--ds-motion-ease-out),
    transform 160ms var(--ds-motion-ease-out),
    visibility 160ms;
}

.workspace-nav__tooltip::before {
  content: "";
  position: absolute;
  right: 100%;
  top: 50%;
  width: 8px;
  height: 8px;
  background: inherit;
  transform: translate(4px, -50%) rotate(45deg);
}

.workspace-nav__item:hover .workspace-nav__tooltip,
.workspace-nav__item:focus-visible .workspace-nav__tooltip {
  opacity: 1;
  visibility: visible;
  transform: translate(0, -50%);
}

.workspace-nav__badge {
  position: absolute;
  top: -3px;
  right: -5px;
  min-width: 20px;
  height: 18px;
  border-radius: 999px;
  display: grid;
  place-items: center;
  padding: 0 6px;
  color: oklch(98% 0.004 50);
  background: var(--workspace-red-600);
  font-size: 11px;
}

@media (prefers-reduced-motion: reduce) {
  .workspace-nav__item,
  .workspace-nav__tooltip {
    transition-duration: 0.01ms;
  }
}
```

- [ ] **Step 3: Remove the short-height rule that shrinks navigation items**

Inside `@media (max-height: 760px) and (min-width: 1024px)`, remove:

```css
.workspace-nav__item {
  flex-basis: 42px;
  font-size: 13px;
}
```

Keep the compact navigation gap and padding rules. Seven 52px buttons still fit within the supported 760px desktop height.

- [ ] **Step 4: Run the focused test**

Run:

```bash
cd /Users/liuyixing/项目/OREP/frontend/user
npx playwright test tests/workspace-sidebar-navigation.spec.js
```

Expected: the geometry, active state, tooltip, focus, and narrow-screen tests pass.

### Task 3: Unify the seven module icons

**Files:**
- Modify: `frontend/user/src/components/workspace/WorkspaceModuleIcon.vue:39-50`
- Modify: `frontend/user/src/components/workspace/WorkspaceModuleIcon.vue:68-73`

- [ ] **Step 1: Replace the seven navigation outline definitions**

Use these balanced 24px paths:

```js
const outlineIcons = {
  home: [
    'M4.5 10.5 12 4l7.5 6.5v8.2a1.3 1.3 0 0 1-1.3 1.3H15v-6H9v6H5.8a1.3 1.3 0 0 1-1.3-1.3v-8.2Z',
  ],
  progress: ['M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z', 'M12 7v5l3.2 2'],
  learning: ['M4 5.5A2.5 2.5 0 0 1 6.5 3H11v16H6.5A2.5 2.5 0 0 0 4 21V5.5Z', 'M20 5.5A2.5 2.5 0 0 0 17.5 3H13v16h4.5A2.5 2.5 0 0 1 20 21V5.5Z'],
  training: [
    'M3.5 7 12 3l8.5 4-8.5 4-8.5-4Z',
    'M6 10v5.6c0 2.4 2.7 4.4 6 4.4s6-2 6-4.4V10',
  ],
  roadshow: [
    'M5.5 6h10A2.5 2.5 0 0 1 18 8.5v7a2.5 2.5 0 0 1-2.5 2.5h-10A2.5 2.5 0 0 1 3 15.5v-7A2.5 2.5 0 0 1 5.5 6Z',
    'm18 10 3-2v8l-3-2',
  ],
  review: [
    'M4 20h16',
    'M6.5 15v2',
    'M11 11v6',
    'M15.5 13v4',
    'm5 11 4-4 3 2.5L19 4',
  ],
  rhythm: ['M5 4h14a2 2 0 0 1 2 2v14H3V6a2 2 0 0 1 2-2Z', 'M8 2v4', 'M16 2v4', 'M3 9h18', 'M7 13h3', 'M14 13h3', 'M7 17h3'],
  actions: ['M10 6h10', 'M10 12h10', 'M10 18h10', 'm4 6 1.4 1.4L8 4.8', 'm4 12 1.4 1.4L8 10.8', 'm4 18 1.4 1.4L8 16.8'],
  collaboration: [
    'M8.2 11.2a3.4 3.4 0 1 0 0-6.8 3.4 3.4 0 0 0 0 6.8Z',
    'M3 20a5.2 5.2 0 0 1 10.4 0',
    'M16.7 10.2a2.8 2.8 0 1 0 0-5.6',
    'M14.4 15.3A4.8 4.8 0 0 1 21 19.8',
  ],
  aiApps: [
    'M5.5 3.5h3A1.5 1.5 0 0 1 10 5v3a1.5 1.5 0 0 1-1.5 1.5h-3A1.5 1.5 0 0 1 4 8V5a1.5 1.5 0 0 1 1.5-1.5Z',
    'M5.5 14.5h3A1.5 1.5 0 0 1 10 16v3a1.5 1.5 0 0 1-1.5 1.5h-3A1.5 1.5 0 0 1 4 19v-3a1.5 1.5 0 0 1 1.5-1.5Z',
    'M16 13.5h3a1.5 1.5 0 0 1 1.5 1.5v4a1.5 1.5 0 0 1-1.5 1.5h-3a1.5 1.5 0 0 1-1.5-1.5v-4a1.5 1.5 0 0 1 1.5-1.5Z',
    'm16.8 2 .6 1.8 1.8.6-1.8.6-.6 1.8-.6-1.8-1.8-.6 1.8-.6.6-1.8Z',
  ],
  profile: [
    'M12 11.8a4.2 4.2 0 1 0 0-8.4 4.2 4.2 0 0 0 0 8.4Z',
    'M5 20.5a7 7 0 0 1 14 0',
  ],
}
```

- [ ] **Step 2: Set the shared outline stroke to the confirmed value**

```css
.workspace-module-icon.is-outline {
  fill: none;
  stroke: currentColor;
  stroke-width: 1.9;
  stroke-linecap: round;
  stroke-linejoin: round;
}
```

- [ ] **Step 3: Re-run the focused test**

Run:

```bash
cd /Users/liuyixing/项目/OREP/frontend/user
npx playwright test tests/workspace-sidebar-navigation.spec.js
```

Expected: both tests pass after the icon changes.

### Task 4: Run regression and visual verification

**Files:**
- Verify: `frontend/user/src/components/workspace/WorkspaceSidebar.vue`
- Verify: `frontend/user/src/components/workspace/WorkspaceModuleIcon.vue`
- Verify: `frontend/user/tests/workspace-sidebar-navigation.spec.js`

- [ ] **Step 1: Build the user frontend**

Run:

```bash
cd /Users/liuyixing/项目/OREP/frontend/user
npm run build
```

Expected: Vite completes successfully with exit code 0 and writes the production bundle.

- [ ] **Step 2: Run the existing navigation regression tests**

Run:

```bash
cd /Users/liuyixing/项目/OREP/frontend/user
npx playwright test \
  tests/workspace-sidebar-navigation.spec.js \
  tests/workspace-route-shell-stability.spec.js \
  tests/training-task-list.spec.js
```

Expected: all selected tests pass. Existing API fixtures may log handled application messages but must not produce test failures.

- [ ] **Step 3: Inspect `/training/today` at 1545×1071**

Use the existing local page at `http://localhost:5174/training/today` and verify:

- the rail remains 86px wide;
- all seven buttons are 52×52px with 24px outline icons;
- icon optical weight and centering are consistent;
- the active training button is neutral gray, not orange-filled;
- hover and keyboard focus tooltips remain inside the viewport and do not shift layout;
- the content area begins at the same horizontal position as before.

- [ ] **Step 4: Inspect the 900px mobile breakpoint**

Set a 900px-wide viewport and verify the desktop sidebar is hidden and the existing mobile navigation remains present and usable.

- [ ] **Step 5: Record verification evidence**

In the final handoff, report:

- focused Playwright result;
- regression Playwright result;
- Vite build result;
- visual inspection result at desktop and narrow widths;
- the inability to create a Git commit because no repository metadata exists.

### Task 5: Enlarge icons and add an arrowed tooltip

**Files:**
- Modify: `frontend/user/tests/workspace-sidebar-navigation.spec.js:144-191`
- Modify: `frontend/user/src/components/workspace/WorkspaceSidebar.vue:157-196`

- [ ] **Step 1: Update the visual contract test before production CSS**

In the desktop tooltip test, replace the 24px icon expectations and add tooltip typography and pseudo-element assertions:

```js
await expect(icon).toHaveCSS('width', '28px')
await expect(icon).toHaveCSS('height', '28px')
await expect(tooltip).toHaveCSS('font-size', '14px')
await expect(tooltip).toHaveCSS('min-height', '36px')

const tooltipDecoration = await tooltip.evaluate((element) => {
  const tooltipStyle = getComputedStyle(element)
  const arrowStyle = getComputedStyle(element, '::before')

  return {
    tooltipBackground: tooltipStyle.backgroundColor,
    arrowBackground: arrowStyle.backgroundColor,
    arrowContent: arrowStyle.content,
    arrowWidth: arrowStyle.width,
    arrowHeight: arrowStyle.height,
    arrowTransform: arrowStyle.transform,
  }
})

expect(tooltipDecoration.arrowContent).not.toBe('none')
expect(tooltipDecoration.arrowContent).not.toBe('normal')
expect(tooltipDecoration.arrowWidth).toBe('8px')
expect(tooltipDecoration.arrowHeight).toBe('8px')
expect(tooltipDecoration.arrowBackground).toBe(tooltipDecoration.tooltipBackground)
expect(tooltipDecoration.arrowTransform).not.toBe('none')
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
cd /Users/liuyixing/项目/OREP/frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test tests/workspace-sidebar-navigation.spec.js
```

Expected: the desktop tooltip test fails because the current icon is 24px, the tooltip text is 12px, its minimum height is 30px, and no `::before` arrow exists.

- [ ] **Step 3: Apply the approved 28px icon and 14px arrowed tooltip**

Update the existing scoped rules:

```css
.workspace-nav__icon {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  background: transparent;
  color: currentColor;
}

.workspace-nav__icon svg {
  width: 28px;
  height: 28px;
  display: block;
}

.workspace-nav__tooltip {
  min-height: 36px;
  padding: 0 13px;
  border-radius: 10px;
  font-size: 14px;
}

.workspace-nav__tooltip::before {
  content: "";
  position: absolute;
  top: 50%;
  right: 100%;
  width: 8px;
  height: 8px;
  background: inherit;
  transform: translate(4px, -50%) rotate(45deg);
}
```

Keep the existing 52px button, tooltip background, hover/focus visibility, route behavior, short-height scrolling, and 1023px mobile breakpoint unchanged.

- [ ] **Step 4: Run focused and shell regression tests**

Run:

```bash
cd /Users/liuyixing/项目/OREP/frontend/user
OREP_E2E_BASE_URL=http://localhost:5174 npx playwright test \
  tests/workspace-sidebar-navigation.spec.js \
  tests/workspace-route-shell-stability.spec.js
```

Expected: all sidebar and shell tests pass.

- [ ] **Step 5: Build and visually inspect the hovered state**

Run:

```bash
cd /Users/liuyixing/项目/OREP/frontend/user
npm run build
```

Expected: Vite exits with code 0. At `http://localhost:5174/training/today`, inspect the 1545×1071 desktop view and confirm the 28px icons remain optically centered, the 14px tooltip is legible, the arrow points to the hovered button, and the tooltip does not clip or widen the document.
