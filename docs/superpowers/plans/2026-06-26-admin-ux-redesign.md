# OREP Admin UX Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the `https://localhost:5173/` admin frontend so it matches the user-side orange visual system and improves high-frequency admin operations.

**Architecture:** Keep the existing Vue 3 + Element Plus app and backend APIs. Add a small admin UI CSS layer for consistent page headers, metric cards, filter panels, tables, empty states, and action bars. Refactor only the highest-impact pages first: layout, dashboard, meetings, resources, analytics.

**Tech Stack:** Vue 3, Vite, Element Plus, ECharts, existing `request` API helper.

---

## Files

- Modify: `frontend/admin/src/theme.css`, unify admin tokens with the user orange theme.
- Create: `frontend/admin/src/admin-ui.css`, shared admin layout and operation patterns.
- Modify: `frontend/admin/src/main.js`, import shared admin UI CSS.
- Modify: `frontend/admin/src/views/Layout.vue`, modern shell, grouped navigation, clearer identity/actions.
- Modify: `frontend/admin/src/views/Dashboard.vue`, convert from raw stats to admin workbench.
- Modify: `frontend/admin/src/views/Meetings.vue`, improve create flow, search/filter, summaries, copy actions, contextual operations.
- Modify: `frontend/admin/src/views/Resources.vue`, improve upload guidance, file filters, summaries, empty states.
- Modify: `frontend/admin/src/views/Analytics.vue`, add overview context, filters, chart cards, empty guidance.

## Task 1: Shared Admin UI Layer

- [x] **Step 1: Update admin design tokens**

Use the user-side orange palette: `#F36B17` for emphasis, black for primary actions, warm paper background, neutral borders, green/red for status.

- [x] **Step 2: Add shared classes**

Create reusable classes for `.admin-page`, `.admin-page-hero`, `.admin-metrics`, `.admin-panel`, `.admin-filter-bar`, `.admin-table-card`, `.admin-empty`, `.admin-action-strip`.

- [x] **Step 3: Import CSS globally**

Import `admin-ui.css` after `theme.css` and before page-specific CSS in `frontend/admin/src/main.js`.

## Task 2: Shell And Navigation

- [x] **Step 1: Refactor shell copy and layout**

Make the sidebar brand match the user app: `竞赛备赛大脑`, `管理控制台`. Remove hardcoded Element Plus menu colors and bind them to CSS variables.

- [x] **Step 2: Improve top bar**

Show current page title, role, username, read-only state, and logout with less visual noise.

## Task 3: Admin Workbench

- [x] **Step 1: Replace dashboard top with a workbench hero**

Show operational focus: meetings, average score, unresolved issues, resolved issues.

- [x] **Step 2: Add actionable task cards**

Add quick entries for meeting management, issue follow-up, score review, resource maintenance.

- [x] **Step 3: Restyle trend and recent meeting panels**

Use orange chart accent and status cards instead of generic Element Plus defaults.

## Task 4: Meeting Management UX

- [x] **Step 1: Turn inline create form into a guided panel**

Group title, password, duration, and primary action with clear helper text.

- [x] **Step 2: Add search and status summaries**

Support keyword search by title/code and show counts for all, created, active, finished.

- [x] **Step 3: Improve row actions**

Add copy meeting code/password, clear status labels, safer destructive action placement.

## Task 5: Resource Management UX

- [x] **Step 1: Add resource operation header**

Show accepted formats, max size, total resources, total size, and selected count.

- [x] **Step 2: Add search/type filters**

Filter by filename/uploader and file extension.

- [x] **Step 3: Improve empty and file list states**

Make upload CTA and table feedback clearer.

## Task 6: Analytics UX

- [x] **Step 1: Add analytics context header**

Explain what admins should use charts for.

- [x] **Step 2: Add metric strip**

Show meetings, average score, issues, resolution rate before charts.

- [x] **Step 3: Restyle ECharts**

Use orange/green/red palette and consistent card headers.

## Task 7: Verification

- [ ] **Step 1: Build admin frontend**

Run: `npm run build` in `frontend/admin`.

Expected: Vite build completes successfully.

- [ ] **Step 2: Self-review changed files**

Check for broken imports, missing refs, invalid CSS, and accidental user-side edits.
