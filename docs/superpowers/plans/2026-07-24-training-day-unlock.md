# Training Day Unlock Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Show every training day to students while enforcing publish and Beijing-time release rules on both UI and server.

**Architecture:** A focused `TrainingDayAvailabilityService` owns all release calculations and access checks. Student plan and project-team APIs expose the same availability metadata; teacher APIs only mutate `early_unlocked_at`. Vue views render metadata and never duplicate release-time rules.

**Tech Stack:** Java 21, Spring Boot 3.2, JdbcTemplate, Flyway/MySQL, Vue 3, Vite, Playwright.

---

### Task 1: Availability Domain

**Files:**
- Create: `backend/src/main/resources/db/migration/V105__training_day_early_unlock.sql`
- Create: `backend/src/main/java/com/orep/backend/service/TrainingDayAvailabilityService.java`
- Test: `backend/src/test/java/com/orep/backend/service/TrainingDayAvailabilityServiceTest.java`

- [ ] **Step 1: Write failing boundary tests**

Test a published future day as locked, the same day at Beijing 00:00 as open, an early-unlocked future day as open, and a draft day as unpublished/locked.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `cd backend && mvn -Dtest=TrainingDayAvailabilityServiceTest test`

Expected: compilation failure because `TrainingDayAvailabilityService` does not exist.

- [ ] **Step 3: Add the nullable migration**

```sql
ALTER TABLE training_day
    ADD COLUMN early_unlocked_at DATETIME NULL AFTER due_at,
    ADD KEY idx_training_day_release (camp_id, status, training_date, early_unlocked_at);
```

- [ ] **Step 4: Implement one availability calculation**

Return `published`, `locked`, `lockReason`, `scheduledUnlockAt`,
`earlyUnlockedAt`, and `effectiveUnlockAt`. Use `ZoneId.of("Asia/Shanghai")`
and `trainingDate.atStartOfDay()`.

- [ ] **Step 5: Run the focused test and verify GREEN**

Run: `cd backend && mvn -Dtest=TrainingDayAvailabilityServiceTest test`

Expected: all availability tests pass.

### Task 2: Student Plan and Access Guards

**Files:**
- Modify: `backend/src/main/java/com/orep/backend/service/StudentTrainingService.java`
- Modify: `backend/src/main/java/com/orep/backend/controller/StudentTrainingController.java`
- Test: `backend/src/test/java/com/orep/backend/controller/StudentTrainingControllerTest.java`

- [ ] **Step 1: Add failing API contract tests**

Assert that the plan includes draft and future days with availability metadata,
while a locked day detail request produces HTTP 423.

- [ ] **Step 2: Run tests and verify RED**

Run: `cd backend && mvn -Dtest=StudentTrainingControllerTest test`

Expected: missing availability fields and no locked-day rejection.

- [ ] **Step 3: Return all training days**

Remove `d.status <> 'DRAFT'` from the plan-day query, attach availability
metadata, and leave unpublished days with an empty `tasks` array.

- [ ] **Step 4: Guard detail endpoints**

Call `availabilityService.assertStudentCanAccess(day)` before building day
content. Throw `ResponseStatusException(HttpStatus.LOCKED, reason)` for locked
or unpublished days.

- [ ] **Step 5: Run tests and verify GREEN**

Run: `cd backend && mvn -Dtest=StudentTrainingControllerTest test`

Expected: all controller tests pass.

### Task 3: Project Queue and Submission Guards

**Files:**
- Modify: `backend/src/main/java/com/orep/backend/service/ProjectTeamService.java`
- Test: `backend/src/test/java/com/orep/backend/service/ProjectTeamServiceMembershipTest.java`

- [ ] **Step 1: Add failing tests**

Assert that a student dashboard receives `trainingSchedule` with every camp
day, and that task detail/submission is rejected while its training day is
locked.

- [ ] **Step 2: Run tests and verify RED**

Run: `cd backend && mvn -Dtest=ProjectTeamServiceMembershipTest test`

Expected: no `trainingSchedule` and locked task access remains allowed.

- [ ] **Step 3: Add schedule payload**

Query all training days for the selected team/camp, link existing primary task
IDs where present, and attach availability metadata without creating placeholder
database tasks.

- [ ] **Step 4: Reuse one access guard**

Before returning task details or accepting a submission, resolve any linked
training day and enforce `assertStudentCanAccess`; teacher/admin access remains
unchanged.

- [ ] **Step 5: Run tests and verify GREEN**

Run: `cd backend && mvn -Dtest=ProjectTeamServiceMembershipTest test`

Expected: all focused tests pass.

### Task 4: Teacher Unlock API

**Files:**
- Modify: `backend/src/main/java/com/orep/backend/controller/TeacherPortalController.java`
- Modify: `backend/src/main/java/com/orep/backend/service/TeacherPortalService.java`
- Test: `backend/src/test/java/com/orep/backend/service/TeacherPortalServiceScopeTest.java`

- [ ] **Step 1: Add failing permission and transition tests**

Cover early unlock of a published future day, rejection for a draft day, reset
to scheduled release, and rejection outside the teacher's accessible teams.

- [ ] **Step 2: Run tests and verify RED**

Run: `cd backend && mvn -Dtest=TeacherPortalServiceScopeTest test`

Expected: unlock methods and endpoints are absent.

- [ ] **Step 3: Add endpoints**

```text
POST   /api/teacher/portal/camp/days/{dayId}/early-unlock
DELETE /api/teacher/portal/camp/days/{dayId}/early-unlock
```

Set `early_unlocked_at` to current Beijing time or `NULL`, then return the
updated day with availability metadata.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `cd backend && mvn -Dtest=TeacherPortalServiceScopeTest test`

Expected: all teacher scope tests pass.

### Task 5: Student UI and 40px Layout

**Files:**
- Modify: `frontend/user/src/views/ProjectTeam.vue`
- Modify: `frontend/user/src/modules/training/TrainingPlan.vue`
- Test: `frontend/user/tests/training-task-locking.spec.js`

- [ ] **Step 1: Add failing Playwright component-contract tests**

Assert all schedule days render, locked rows have `aria-disabled="true"`, locked
clicks do not navigate, release copy is present, and `.task-management-shell`
has 40px top padding.

- [ ] **Step 2: Run tests and verify RED**

Run: `cd frontend/user && npx playwright test tests/training-task-locking.spec.js --reporter=line`

Expected: missing locked schedule rows and incorrect top spacing.

- [ ] **Step 3: Merge schedule rows**

Map `dashboard.trainingSchedule` to locked work items when no real task exists;
for real tasks, copy availability metadata onto the existing work item.

- [ ] **Step 4: Render locked states**

Use a lock icon, “待教师发布” or “X月X日 00:00开放”, prevent navigation, and
disable detail/submission actions. Apply `padding-top: 40px` to the task page's
main content boundary.

- [ ] **Step 5: Keep training plan consistent**

Render days with no published task as locked day shells and replace future
`RouterLink` elements with non-interactive rows until unlocked.

- [ ] **Step 6: Run tests and build**

Run: `cd frontend/user && npx playwright test tests/training-task-locking.spec.js --reporter=line && npm run build`

Expected: tests pass and Vite exits 0.

### Task 6: Teacher UI

**Files:**
- Modify: `frontend/teacher/src/api/index.js`
- Modify: `frontend/teacher/src/views/camp/CampPlanView.vue`

- [ ] **Step 1: Add API helpers**

Add `earlyUnlockTeacherTrainingDay(dayId)` and
`restoreTeacherTrainingDaySchedule(dayId)`.

- [ ] **Step 2: Show release state and controls**

Published future days show “提前解锁”; early-unlocked days show “恢复按日期开放”;
draft days explain that they must be published first.

- [ ] **Step 3: Build teacher frontend**

Run: `cd frontend/teacher && npm run build`

Expected: Vite exits 0.

### Task 7: Integrated Verification

**Files:**
- Verify only; no new files.

- [ ] **Step 1: Run backend tests**

Run: `cd backend && mvn -Dtest=TrainingDayAvailabilityServiceTest,StudentTrainingControllerTest,ProjectTeamServiceMembershipTest,TeacherPortalServiceScopeTest test`

Expected: zero failures.

- [ ] **Step 2: Package backend**

Run: `cd backend && mvn -DskipTests package`

Expected: `target/orep-backend-1.0.0.jar` is produced.

- [ ] **Step 3: Sync release artifacts and deploy only affected services**

Build and recreate `backend`, `frontend-user`, and `frontend-teacher` with the
existing production Compose file. Do not recreate MySQL, MinIO, LiveKit, or AI.

- [ ] **Step 4: Verify production**

Check container health/restart counts, HTTP 200 for all three frontends, locked
student navigation, teacher early unlock/reset, and the 40px computed layout.

