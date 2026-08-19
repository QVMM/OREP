# Teacher Member Global Role Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make teacher team membership follow the user's global role, support controlled manual role changes, and deploy the verified change to production.

**Architecture:** `users.role` remains the authoritative identity. `ProjectTeamService` validates requested `STUDENT`/`TEACHER` changes, persists the global role, and derives `MEMBER`/`MENTOR`; the teacher frontend only presents role choices and sends the requested global role.

**Tech Stack:** Spring Boot, JdbcTemplate, JUnit 5/Mockito, Vue 3, Vite, Docker Compose, Nginx.

---

### Task 1: Backend role synchronization

**Files:**
- Modify: `backend/src/test/java/com/orep/backend/service/ProjectTeamServiceMembershipTest.java`
- Modify: `backend/src/main/java/com/orep/backend/service/ProjectTeamService.java`

- [ ] Add failing tests proving teachers become mentors automatically, students remain members, manual role changes update both tables, captains cannot become teachers, and unsupported roles are rejected.
- [ ] Run the focused JUnit test class and confirm failures are caused by the missing synchronization behavior.
- [ ] Add role lookup, validation, team-role derivation, mentor assignment, and safe mentor replacement logic.
- [ ] Run the focused JUnit test class and confirm it passes.

### Task 2: Teacher member management UI

**Files:**
- Modify: `frontend/teacher/src/views/team/TeamWorkspaceView.vue`

- [ ] Preserve candidate global roles in the view model.
- [ ] Show automatic role detection and per-candidate manual overrides in the add-member drawer.
- [ ] Add an editable system-role column for existing non-captain members.
- [ ] Send `systemRole` with add/update requests and show the re-login notice.
- [ ] Run the teacher frontend production build.

### Task 3: Regression verification

**Files:**
- Verify: `backend/src/test/java`
- Verify: `frontend/teacher`

- [ ] Run the complete backend test suite.
- [ ] Run the teacher frontend production build again from a clean output directory.
- [ ] Review the changed files for unrelated edits and secret exposure.

### Task 4: Production deployment

**Files:**
- Deploy: `backend/target/*.jar`
- Deploy: `frontend/teacher/dist`

- [ ] Back up the current backend artifact, teacher frontend, and the affected `users`, `project_team`, and `project_team_member` tables.
- [ ] Upload the verified artifacts without replacing resource directories or importing a database.
- [ ] Rebuild and restart only `backend` and `frontend-teacher`.
- [ ] Check container health, backend logs, HTTPS responses, and the teacher member-management route.

