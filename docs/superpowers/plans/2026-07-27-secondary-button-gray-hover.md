# Secondary Button Gray Hover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make student-side secondary interactive buttons reveal a neutral gray background on hover and keyboard focus.

**Architecture:** Keep the behavior inside the shared `InteractiveHoverButton` component. Add a focused Playwright assertion before changing the component variables, then build and deploy only the student frontend.

**Tech Stack:** Vue 3, scoped CSS, Vite, Playwright, Docker Compose

---

### Task 1: Lock the secondary hover contract

**Files:**
- Modify: `frontend/user/tests/student-prototype-contract.spec.js`

- [ ] Add assertions that a secondary button's reveal fill is neutral gray and its revealed text is dark gray.
- [ ] Run the focused test and confirm it fails because the current fill is orange.

### Task 2: Update the shared component

**Files:**
- Modify: `frontend/user/src/components/base/InteractiveHoverButton.vue`

- [ ] Change only the secondary button's `--interactive-fill` and `--interactive-reveal-fg` values.
- [ ] Run the focused test and confirm it passes.
- [ ] Run the student-side smoke tests and production build.

### Task 3: Deploy the student frontend

**Files:**
- Update generated files under: `deploy/frontend/user/dist`

- [ ] Back up the current cloud student frontend.
- [ ] Upload the new distribution and recreate only `frontend-user`.
- [ ] Verify the homepage, project-team route, new assets, and service health.
