# Student Motion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan.

**Goal:** Give the ordinary student workspace restrained, smooth page transitions and clear interaction feedback without adding motion to immersive exam, meeting, playback, or heavy editor experiences.

**Architecture:** Define shared motion tokens in the student design-token layer, apply route transitions only inside `WorkspaceShell`, and improve existing base/legacy interaction primitives through opt-in interactive classes. Reduced-motion behavior lives next to each motion rule so accessibility does not depend on page-specific code.

**Tech Stack:** Vue 3, Vue Router 4, scoped CSS, shared CSS design tokens, Playwright, Vite

---

## Task 1: Add a small shared motion token set

**Files:**

- Modify: `frontend/user/src/styles/workspace-tokens.css`

1. Add duration, easing, displacement, and hover-shadow tokens beside the existing transition tokens.
2. Remap the existing `--ds-control-transition` and `--ds-transition` aliases to the new tokens so current components remain compatible.
3. Keep the page-enter distance at `6px`, hover lift at `-2px`, and press feedback at `1px`.

## Task 2: Animate ordinary workspace route changes

**Files:**

- Modify: `frontend/user/src/components/workspace/WorkspaceShell.vue`

1. Add `route` to the `router-view` slot.
2. Wrap the existing `keep-alive` component in an `out-in` Vue transition.
3. Key the routed component by `route.path` so normal page navigation transitions while query-only state changes do not unnecessarily remount the page.
4. Add a 220ms opacity + `translateY(6px)` enter and a shorter, subtle leave.
5. Add `prefers-reduced-motion` rules that keep the view change but remove displacement and meaningful duration.

## Task 3: Refine shared button and card primitives

**Files:**

- Modify: `frontend/user/src/components/base/BaseButton.vue`
- Modify: `frontend/user/src/components/base/BaseCard.vue`

1. Add transform to the existing transition list without changing component geometry.
2. Give enabled buttons a `translateY(1px)` active state.
3. Give only `hoverable` cards a `translateY(-2px)` hover state with a light border and shadow.
4. Preserve disabled/loading behavior and keyboard focus styles.
5. Remove displacement under `prefers-reduced-motion`.

## Task 4: Bring legacy student controls onto the same motion language

**Files:**

- Modify: `frontend/user/src/styles/workspace-components.css`
- Modify: `frontend/user/src/styles/student-flow.css`
- Modify: `frontend/user/src/components/workspace/WorkspaceSidebar.vue`
- Modify: `frontend/user/src/components/workspace/WorkspaceModuleNav.vue`

1. Add the same 1px press feedback to legacy student/workspace button classes.
2. Change existing interactive card hover rules from static to the approved 2px lift.
3. Add restrained icon/content movement to main and secondary navigation hover states without moving the fixed navigation columns themselves.
4. Add a reusable motion-link utility whose trailing icon shifts 2px on hover.
5. Add reduced-motion overrides for every new transform.

## Task 5: Verify behavior and regressions

**Files:**

- Modify: `frontend/user/tests/student-prototype-contract.spec.js`

1. Extend the existing student contract test to assert that primary-button hover does not change its bounding box and active feedback uses a transform rather than layout movement.
2. Add a reduced-motion assertion for the ordinary workspace route transition.
3. Run:

   ```bash
   cd frontend/user
   npm run build
   npm run test:e2e:prototype-contract
   ```

4. Manually inspect the ordinary student workspace at desktop width, including home → training → review/collaboration navigation.
5. Confirm formal exam-taking, meeting, playback, and heavy editor routes do not receive the workspace route transition.

**Repository note:** `/Users/liuyixing/项目/OREP` is not a Git worktree, so this plan intentionally omits commit commands.
