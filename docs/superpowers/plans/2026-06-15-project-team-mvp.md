# Project Team MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a role-aware project team dashboard that supports student tasks, captain management, teacher observation, project materials, roadshow review, and evidence-based ability profiles.

**Architecture:** Add a backend project-team module with auto-created MySQL tables and role-filtered dashboard APIs. The frontend `/project-team` page consumes the dashboard response and renders student, captain, or teacher-only sections based on backend permissions and team membership.

**Tech Stack:** Spring Boot 3, JdbcTemplate, MySQL, Vue 3, Element Plus, SVG radar charts.

---

### Task 1: Backend Schema And Dashboard Service

**Files:**
- Create: `backend/src/main/resources/sql/create_project_team_tables.sql`
- Create: `backend/src/main/java/com/orep/backend/service/ProjectTeamService.java`
- Create: `backend/src/main/java/com/orep/backend/controller/ProjectTeamController.java`

- [ ] Create project team tables: `project_team`, `project_team_member`, `project_stage`, `project_task`, `project_task_submission`, `project_material`, `project_roadshow_binding`, `project_review_issue`, `member_ability_snapshot`, and `member_ability_evidence`.
- [ ] Auto-create schema at service startup with `JdbcTemplate`.
- [ ] Seed one default team per tenant when a user first opens the page and no team exists.
- [ ] Return `myRoleInTeam`, `canManage`, and `canTeachObserve` from the dashboard API.
- [ ] Never return teacher-only observation fields to student/captain responses unless the global role is `TEACHER`, `SCHOOL_ADMIN`, or `ADMIN`.

### Task 2: Captain Task And Submission Flow

**Files:**
- Modify: `backend/src/main/java/com/orep/backend/service/ProjectTeamService.java`
- Modify: `backend/src/main/java/com/orep/backend/controller/ProjectTeamController.java`

- [ ] Add task creation for captains and teachers.
- [ ] Add task update for owner, dates, priority, and status.
- [ ] Add student submission endpoint.
- [ ] Add review endpoint for captains and teachers with statuses `APPROVED`, `REJECTED`, and `CHANGES_REQUESTED`.
- [ ] Update task status automatically when submissions are approved or returned.

### Task 3: Materials, Roadshow, Review, Ability Evidence

**Files:**
- Modify: `backend/src/main/java/com/orep/backend/service/ProjectTeamService.java`
- Modify: `backend/src/main/java/com/orep/backend/controller/ProjectTeamController.java`

- [ ] Add material creation and review endpoints.
- [ ] Add roadshow meeting binding endpoint.
- [ ] Read AI score from `ai_score_report` first, then fallback to meeting detail score tables.
- [ ] Convert AI critical issues and improvement priorities into visible review items.
- [ ] Calculate six ability dimensions with evidence: problem solving, coding, communication, teamwork, presentation, creativity.

### Task 4: Role-Aware Frontend

**Files:**
- Modify: `frontend/user/src/views/ProjectTeam.vue`

- [ ] Replace the static dashboard with API-backed data.
- [ ] Render student action queue and own ability evidence.
- [ ] Render captain task creation, task audit, member assignment, and material review controls only when `canManage` is true.
- [ ] Render teacher observation only when `canTeachObserve` is true. Student and captain views must not render teacher labels or hidden teacher DOM.
- [ ] Keep OREP dark mission-control visual language with readable density.

### Task 5: Verification

**Commands:**
- Run `mvn -q -DskipTests compile` in `backend`.
- Run `npm run build` in `frontend/user`.
- Verify `https://localhost:5174/project-team` renders and that non-teacher responses omit teacher-only fields.
