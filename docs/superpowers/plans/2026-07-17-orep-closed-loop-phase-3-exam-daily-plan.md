# OREP Closed-Loop Phase 3 Exam and Daily Plan Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 明确区分自主测试与老师发布考试，并为考试未通过、每日计划未通过建立“系统建议—老师裁决—整改草案—发布任务—重练复查”的完整闭环。

**Architecture:** 新增考试发布与目标对象，保留现有试卷和答题记录；老师发布考试进入统一检查点，自主测试只提供个人建议。人工题评分完成后重新计算系统建议，但正式考试最终结果由老师裁决。每日计划作为独立领域对象支持系统生成和老师添加，审核模式固定保存到每个计划实例。

**Tech Stack:** Java 21、Spring Boot 3.2、MyBatis-Plus/JdbcTemplate、MySQL 8、H2、JUnit 5、MockMvc、Vue 3、Element Plus、Node test runner、Vite。

---

## File map

**Create**

- `backend/src/main/resources/sql/create_exam_assignment_daily_plan_tables.sql`
- `deploy/sql/backend-resources/create_exam_assignment_daily_plan_tables.sql`
- `backend/src/main/java/com/orep/backend/entity/ExamAssignment.java`
- `backend/src/main/java/com/orep/backend/entity/ExamAssignmentTarget.java`
- `backend/src/main/java/com/orep/backend/entity/DailyPlan.java`
- `backend/src/main/java/com/orep/backend/entity/DailyPlanSubmission.java`
- `backend/src/main/java/com/orep/backend/mapper/ExamAssignmentMapper.java`
- `backend/src/main/java/com/orep/backend/mapper/ExamAssignmentTargetMapper.java`
- `backend/src/main/java/com/orep/backend/mapper/DailyPlanMapper.java`
- `backend/src/main/java/com/orep/backend/mapper/DailyPlanSubmissionMapper.java`
- `backend/src/main/java/com/orep/backend/service/ExamAssignmentService.java`
- `backend/src/main/java/com/orep/backend/service/DailyPlanService.java`
- `backend/src/main/java/com/orep/backend/service/closedloop/adapter/ExamClosedLoopAdapter.java`
- `backend/src/main/java/com/orep/backend/service/closedloop/adapter/DailyPlanClosedLoopAdapter.java`
- `backend/src/main/java/com/orep/backend/controller/AdminExamAssignmentController.java`
- `backend/src/main/java/com/orep/backend/controller/DailyPlanController.java`
- `backend/src/main/java/com/orep/backend/controller/AdminDailyPlanController.java`
- `backend/src/test/java/com/orep/backend/service/ExamAssignmentServiceTest.java`
- `backend/src/test/java/com/orep/backend/service/closedloop/adapter/ExamClosedLoopAdapterTest.java`
- `backend/src/test/java/com/orep/backend/service/DailyPlanServiceTest.java`
- `backend/src/test/java/com/orep/backend/controller/AdminExamAssignmentControllerTest.java`
- `backend/src/test/java/com/orep/backend/controller/DailyPlanControllerTest.java`
- `frontend/user/src/utils/examClosedLoop.js`
- `frontend/user/src/utils/examClosedLoop.test.js`
- `frontend/user/src/utils/dailyPlanClosedLoop.js`
- `frontend/user/src/utils/dailyPlanClosedLoop.test.js`
- `frontend/user/src/views/DailyPlan.vue`
- `frontend/admin/src/api/closedLoopExam.js`
- `frontend/admin/src/api/dailyPlan.js`

**Modify**

- `backend/src/main/java/com/orep/backend/entity/ExamAttempt.java` — 增加发布、上轮和检查点引用。
- `backend/src/main/java/com/orep/backend/service/ExamService.java:266` — 区分自主测试和正式考试并提交系统评估。
- `backend/src/main/java/com/orep/backend/service/ExamService.java:381` — 人工阅卷后重新计算正式结果建议。
- `backend/src/main/java/com/orep/backend/controller/ExamController.java` — 增加正式考试开始/重考入口。
- `backend/src/test/java/com/orep/backend/service/ExamServiceTest.java`
- `frontend/admin/src/views/ExamManagement.vue` — 发布、终审、重练草案。
- `frontend/user/src/views/ExamSystem.vue` — 展示自主测试与老师考试。
- `frontend/user/src/views/ExamTaking.vue` — 绑定 assignment 和 reattempt。
- `frontend/user/src/router/index.js` — 增加每日计划路由。
- `frontend/user/src/views/ProjectTeam.vue` — 团队上下文中显示每日计划入口。

## Task 1: Add assignment and daily-plan persistence

- [ ] **Step 1: Write the failing schema test**

Add `ExamAssignmentDailyPlanSchemaTest.java` using H2 MySQL mode. Run the initializer twice and assert these tables exist:

```text
EXAM_ASSIGNMENT
EXAM_ASSIGNMENT_TARGET
DAILY_PLAN
DAILY_PLAN_SUBMISSION
```

Also assert `EXAM_ATTEMPT` contains:

```text
ASSIGNMENT_ID
PREVIOUS_ATTEMPT_ID
CLOSED_LOOP_CHECKPOINT_ID
ATTEMPT_SOURCE
```

- [ ] **Step 2: Run and verify failure**

```bash
cd backend
mvn -Dtest=ExamAssignmentDailyPlanSchemaTest test
```

Expected: missing-table/column failure.

- [ ] **Step 3: Create identical resource and deployment SQL**

Create both SQL files with:

```sql
CREATE TABLE IF NOT EXISTS exam_assignment (
  id BIGINT NOT NULL AUTO_INCREMENT,
  tenant_id BIGINT NOT NULL,
  team_id BIGINT DEFAULT NULL,
  project_id BIGINT DEFAULT NULL,
  paper_id BIGINT NOT NULL,
  title VARCHAR(180) NOT NULL,
  pass_score DECIMAL(10,2) NOT NULL,
  review_mode VARCHAR(40) NOT NULL,
  remediation_policy VARCHAR(40) NOT NULL,
  starts_at DATETIME DEFAULT NULL,
  due_at DATETIME DEFAULT NULL,
  status VARCHAR(32) NOT NULL,
  published_by BIGINT NOT NULL,
  published_at DATETIME DEFAULT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_exam_assignment_scope (tenant_id, team_id, status)
);

CREATE TABLE IF NOT EXISTS exam_assignment_target (
  id BIGINT NOT NULL AUTO_INCREMENT,
  assignment_id BIGINT NOT NULL,
  user_id BIGINT NOT NULL,
  status VARCHAR(32) NOT NULL,
  latest_attempt_id BIGINT DEFAULT NULL,
  final_decision_id BIGINT DEFAULT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_exam_assignment_target (assignment_id, user_id)
);

CREATE TABLE IF NOT EXISTS daily_plan (
  id BIGINT NOT NULL AUTO_INCREMENT,
  tenant_id BIGINT NOT NULL,
  team_id BIGINT DEFAULT NULL,
  project_id BIGINT DEFAULT NULL,
  student_id BIGINT NOT NULL,
  source_type VARCHAR(24) NOT NULL,
  source_ref VARCHAR(160) DEFAULT NULL,
  title VARCHAR(180) NOT NULL,
  description LONGTEXT,
  plan_date DATE NOT NULL,
  review_mode VARCHAR(40) NOT NULL,
  completion_rule LONGTEXT,
  status VARCHAR(32) NOT NULL,
  created_by BIGINT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_daily_plan_student (tenant_id, student_id, plan_date, status)
);

CREATE TABLE IF NOT EXISTS daily_plan_submission (
  id BIGINT NOT NULL AUTO_INCREMENT,
  plan_id BIGINT NOT NULL,
  student_id BIGINT NOT NULL,
  evidence_json LONGTEXT,
  submitted_at DATETIME NOT NULL,
  system_result VARCHAR(24) DEFAULT NULL,
  system_reason LONGTEXT,
  reviewer_id BIGINT DEFAULT NULL,
  reviewer_result VARCHAR(24) DEFAULT NULL,
  reviewer_reason LONGTEXT,
  decided_at DATETIME DEFAULT NULL,
  checkpoint_id BIGINT DEFAULT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_daily_plan_submission_plan (plan_id, submitted_at)
);
```

Add safe, idempotent upgrade statements for the four `exam_attempt` columns. Because MySQL and H2 differ for conditional column changes, put dialect handling in the existing schema initializer and test both fresh and upgraded schemas.

- [ ] **Step 4: Add entities, mappers and initializer**

Map enum-like values as strings. Do not use Java ordinal persistence. Add composite-index query methods for assignment targets and daily-plan dates.

- [ ] **Step 5: Run schema tests**

```bash
cd backend
mvn -Dtest=ExamAssignmentDailyPlanSchemaTest test
```

Expected: fresh and upgrade cases pass.

- [ ] **Step 6: Commit**

```bash
git add backend/src/main/resources/sql/create_exam_assignment_daily_plan_tables.sql deploy/sql/backend-resources/create_exam_assignment_daily_plan_tables.sql backend/src/main/java/com/orep/backend/entity/ExamAssignment.java backend/src/main/java/com/orep/backend/entity/ExamAssignmentTarget.java backend/src/main/java/com/orep/backend/entity/DailyPlan.java backend/src/main/java/com/orep/backend/entity/DailyPlanSubmission.java backend/src/main/java/com/orep/backend/mapper/ExamAssignmentMapper.java backend/src/main/java/com/orep/backend/mapper/ExamAssignmentTargetMapper.java backend/src/main/java/com/orep/backend/mapper/DailyPlanMapper.java backend/src/main/java/com/orep/backend/mapper/DailyPlanSubmissionMapper.java backend/src/test/java/com/orep/backend/service/ExamAssignmentDailyPlanSchemaTest.java
git commit -m "feat(closed-loop): add exam assignment and daily plan schema"
```

## Task 2: Publish teacher exams to explicit targets

- [ ] **Step 1: Write failing service tests**

Create `ExamAssignmentServiceTest.java` and cover:

- teacher publishes to one student, several students or a team;
- publishing freezes `passScore`, `reviewMode` and remediation policy;
- duplicate target identifiers are deduplicated;
- student/captain cannot publish;
- target outside tenant/team is rejected;
- published assignment cannot silently change pass score.

- [ ] **Step 2: Run and verify failure**

```bash
cd backend
mvn -Dtest=ExamAssignmentServiceTest test
```

Expected: compilation failure.

- [ ] **Step 3: Implement assignment service**

Required methods:

```java
ExamAssignment publish(PublishExamAssignment command, Actor actor);
List<AssignedExamView> listForStudent(long studentId, Actor actor);
AttemptStartResult startAssignedAttempt(long assignmentId, Actor actor);
AttemptStartResult startReattempt(long assignmentId, long previousAttemptId, Actor actor);
```

Rules:

- `publish` requires teacher authority.
- Assignment pass score defaults from `ExamPaper.passScore` only when teacher omits it; the resolved value is stored.
- Every target gets one row and one target state.
- Start verifies time window and target membership.
- Reattempt requires a previous non-passed formal attempt for the same assignment.
- `attemptSource=TEACHER_ASSIGNMENT`; existing unbound attempts remain `SELF_TEST`.

- [ ] **Step 4: Add admin controller tests and endpoint**

Create:

```text
POST /api/admin/exam-assignments
GET  /api/admin/exam-assignments
GET  /api/exams/assignments/mine
POST /api/exams/assignments/{assignmentId}/attempts
POST /api/exams/assignments/{assignmentId}/reattempts
```

Controller must take actor identity from authentication and return 409 for an invalid reattempt transition.

- [ ] **Step 5: Run tests**

```bash
cd backend
mvn -Dtest=ExamAssignmentServiceTest,AdminExamAssignmentControllerTest test
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add backend/src/main/java/com/orep/backend/service/ExamAssignmentService.java backend/src/main/java/com/orep/backend/controller/AdminExamAssignmentController.java backend/src/main/java/com/orep/backend/controller/ExamController.java backend/src/test/java/com/orep/backend/service/ExamAssignmentServiceTest.java backend/src/test/java/com/orep/backend/controller/AdminExamAssignmentControllerTest.java
git commit -m "feat(exam): publish teacher assignments and explicit reattempts"
```

## Task 3: Separate self-test feedback from formal exam decisions

- [ ] **Step 1: Add failing `ExamServiceTest` cases**

Cover:

1. self-test submission preserves current immediate score/result and creates no formal closed-loop decision;
2. teacher exam with objective questions submits a system suggestion and waits for configured final review;
3. teacher exam with manual questions remains `PENDING_MANUAL_GRADING`;
4. manual grading recalculates the total against the assignment pass score;
5. client-supplied pass score cannot override the assignment snapshot.

- [ ] **Step 2: Run and verify failure**

```bash
cd backend
mvn -Dtest=ExamServiceTest test
```

Expected: formal and self-test paths are not yet distinct.

- [ ] **Step 3: Implement `ExamClosedLoopAdapter`**

The adapter input must include:

```java
public record FormalExamSnapshot(
        long assignmentId,
        long targetId,
        long attemptId,
        long studentId,
        BigDecimal score,
        BigDecimal passScore,
        boolean manualGradingComplete,
        String answerEvidenceJson,
        String gradingEvidenceJson) {}
```

Behavior by review mode:

- `MANUAL_FINAL_REQUIRED`: save system recommendation, status `PENDING_FINAL_REVIEW`.
- `AUTO_PASS_AUDITABLE`: pass recommendation may complete the checkpoint; create an append-only system decision that a teacher can later revoke.
- `ADVISORY_ONLY`: save recommendation and never create pass/fail decision.

A fail recommendation can create a remediation draft batch, but never publish it.

- [ ] **Step 4: Modify submit and manual-grade paths**

At `ExamService.submitAttempt(...)`:

- branch by `attemptSource`;
- keep the current self-test behavior;
- invoke the adapter only after objective/manual scores are persisted.

At `ExamService.gradeManualAnswers(...)`:

- recompute objective + manual total;
- compare with assignment pass score;
- submit a new immutable evaluation;
- never overwrite an existing teacher decision.

- [ ] **Step 5: Run tests**

```bash
cd backend
mvn -Dtest=ExamServiceTest,ExamClosedLoopAdapterTest test
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add backend/src/main/java/com/orep/backend/service/ExamService.java backend/src/main/java/com/orep/backend/service/closedloop/adapter/ExamClosedLoopAdapter.java backend/src/test/java/com/orep/backend/service/ExamServiceTest.java backend/src/test/java/com/orep/backend/service/closedloop/adapter/ExamClosedLoopAdapterTest.java
git commit -m "feat(exam): evaluate formal attempts through closed loop"
```

## Task 4: Add teacher final decision and failed-exam training drafts

- [ ] **Step 1: Write failing controller tests**

Add:

```text
POST /api/admin/exam-assignments/{assignmentId}/targets/{targetId}/decision
POST /api/admin/exam-assignments/{assignmentId}/targets/{targetId}/remediation-draft/publish
```

Decision payload supports `PASS`, `REJECT`, `REEXECUTE`; every action requires a reason. Assert captains receive 403.

- [ ] **Step 2: Run and verify failure**

```bash
cd backend
mvn -Dtest=AdminExamAssignmentControllerTest test
```

Expected: endpoint missing.

- [ ] **Step 3: Implement final decision orchestration**

On `PASS`:

- append a teacher decision;
- mark target passed;
- close open exam issues;
- do not delete old drafts/tasks.

On `REJECT` or `REEXECUTE`:

- append the decision and reason;
- generate/update a draft with weak knowledge points and answer evidence;
- leave the draft inactive;
- return fields teacher must confirm: assignee, due date, training scope, estimated workload.

- [ ] **Step 4: Publish remediation through Phase 1**

The publish endpoint must validate:

- assignee is the failed student unless teacher explicitly chooses a permitted coach/team member;
- due date is present and after publish time;
- scope is nonblank;
- target has a current non-passed decision;
- idempotency key uses assignment, target and decision revision.

After publication, store task link and show `TRAINING_ASSIGNED`; passing the task changes the checkpoint only to `READY_FOR_RECHECK`.

- [ ] **Step 5: Add reattempt lineage test**

Start a reattempt and assert:

- `previousAttemptId` points to the failed attempt;
- the new checkpoint links to the previous checkpoint and remediation batch;
- prior evidence and decisions remain queryable.

- [ ] **Step 6: Run tests and commit**

```bash
cd backend
mvn -Dtest=AdminExamAssignmentControllerTest,ExamAssignmentServiceTest,ExamClosedLoopAdapterTest test
git add backend/src/main/java/com/orep/backend/controller/AdminExamAssignmentController.java backend/src/main/java/com/orep/backend/service/ExamAssignmentService.java backend/src/main/java/com/orep/backend/service/closedloop/adapter/ExamClosedLoopAdapter.java backend/src/test/java/com/orep/backend/controller/AdminExamAssignmentControllerTest.java backend/src/test/java/com/orep/backend/service/ExamAssignmentServiceTest.java
git commit -m "feat(exam): add teacher decisions and retraining drafts"
```

## Task 5: Implement daily plans with two sources and three review modes

- [ ] **Step 1: Write failing service tests**

Create `DailyPlanServiceTest.java`:

```java
@Test
void teacherPlanFreezesManualReviewMode() { /* source=TEACHER */ }

@Test
void systemPlanCanUseAutoPassAuditableMode() { /* source=SYSTEM */ }

@Test
void advisoryPlanNeverCreatesPassDecision() { /* reviewMode=ADVISORY_ONLY */ }

@Test
void failedCompletionCreatesDraftButNoProjectTask() { /* verify never publish */ }
```

Also cover authorization, plan-date queries and duplicate system generation.

- [ ] **Step 2: Run and verify failure**

```bash
cd backend
mvn -Dtest=DailyPlanServiceTest test
```

Expected: compilation failure.

- [ ] **Step 3: Implement plan creation and submission**

Required methods:

```java
DailyPlan createByTeacher(CreateDailyPlan command, Actor teacher);
DailyPlan generateBySystem(GenerateDailyPlan command);
DailyPlanSubmission submit(long planId, CompletionEvidence evidence, Actor student);
ReviewResult review(long submissionId, ReviewCommand command, Actor reviewer);
List<DailyPlanView> listMine(LocalDate from, LocalDate to, Actor student);
```

Evidence must be a frozen JSON snapshot containing task completion data, links, timestamps and optional attachments. Never treat opening the page as completion.

- [ ] **Step 4: Implement `DailyPlanClosedLoopAdapter`**

For each submission:

- create a `DAILY_PLAN` checkpoint;
- run configured rule evaluation when evidence is machine-readable;
- store system result and evidence;
- apply the plan's stored review mode;
- on non-pass create a draft containing missed items and required rework;
- do not publish the draft.

Teachers may always revoke an auto pass through an append-only decision. Captains may pre-review a team plan but may only finally review ordinary plans when an active delegation exists.

- [ ] **Step 5: Add controllers**

Create:

```text
GET  /api/daily-plans/mine
POST /api/daily-plans/{planId}/submissions
POST /api/daily-plans/submissions/{submissionId}/pre-review
POST /api/admin/daily-plans
POST /api/admin/daily-plans/submissions/{submissionId}/decision
```

All rejection/reexecution decisions require a reason.

- [ ] **Step 6: Run tests and commit**

```bash
cd backend
mvn -Dtest=DailyPlanServiceTest,DailyPlanControllerTest test
git add backend/src/main/java/com/orep/backend/service/DailyPlanService.java backend/src/main/java/com/orep/backend/service/closedloop/adapter/DailyPlanClosedLoopAdapter.java backend/src/main/java/com/orep/backend/controller/DailyPlanController.java backend/src/main/java/com/orep/backend/controller/AdminDailyPlanController.java backend/src/test/java/com/orep/backend/service/DailyPlanServiceTest.java backend/src/test/java/com/orep/backend/controller/DailyPlanControllerTest.java
git commit -m "feat(daily-plan): add evidence-based completion loop"
```

## Task 6: Update teacher and student exam experiences

- [ ] **Step 1: Write failing frontend mappers**

Create `examClosedLoop.test.js`:

```js
test('separates self test from teacher assignment', () => {
  assert.equal(presentExam({ attemptSource: 'SELF_TEST' }).kindLabel, '自主测试')
  assert.equal(presentExam({ attemptSource: 'TEACHER_ASSIGNMENT' }).kindLabel, '老师考试')
})

test('formal fail waits for teacher draft publication', () => {
  assert.equal(
    presentExam({ attemptSource: 'TEACHER_ASSIGNMENT', state: 'DRAFT_REVIEW' }).nextAction,
    '等待老师确认重练任务'
  )
})
```

- [ ] **Step 2: Run and verify failure**

```bash
cd frontend/user
node --test src/utils/examClosedLoop.test.js
```

Expected: module-not-found failure.

- [ ] **Step 3: Implement student UI**

Update `ExamSystem.vue` with separate sections:

- 老师发布：deadline, pass score, status, review mode, teacher decision;
- 自主测试：existing papers and personal feedback.

Update `ExamTaking.vue` to keep `assignmentId` and `previousAttemptId` through refresh and submission. Do not infer an assignment from paper id.

- [ ] **Step 4: Implement teacher UI**

Update `ExamManagement.vue` to support:

- publish assignment and targets;
- inspect system score/evidence;
- pass, reject or require reexecution with mandatory reason;
- edit draft assignee, due date and training scope;
- publish draft;
- see reattempt lineage.

- [ ] **Step 5: Run test and both builds**

```bash
cd frontend/user
node --test src/utils/examClosedLoop.test.js
npm run build

cd ../admin
npm run build
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add frontend/user/src/utils/examClosedLoop.js frontend/user/src/utils/examClosedLoop.test.js frontend/user/src/views/ExamSystem.vue frontend/user/src/views/ExamTaking.vue frontend/admin/src/api/closedLoopExam.js frontend/admin/src/views/ExamManagement.vue
git commit -m "feat(exam): expose formal exam decision lifecycle"
```

## Task 7: Add the daily-plan experience

- [ ] **Step 1: Write the failing presentation tests**

Create `dailyPlanClosedLoop.test.js` covering:

- `SYSTEM` and `TEACHER` source labels;
- all three review modes;
- `PENDING_REVIEW`, `DRAFT_REMEDIATION`, `PUBLISHED_REMEDIATION`, `READY_FOR_RECHECK`;
- unknown status is never shown as completed.

- [ ] **Step 2: Run and verify failure**

```bash
cd frontend/user
node --test src/utils/dailyPlanClosedLoop.test.js
```

Expected: module-not-found failure.

- [ ] **Step 3: Implement `DailyPlan.vue`**

The page must show:

- plan date and source;
- completion rule;
- required evidence;
- system assessment and evidence;
- captain pre-review when present;
- teacher decision and reason;
- linked rework task and next recheck.

Submission button becomes disabled only after a successful API response; a rejected submission remains visible as history.

- [ ] **Step 4: Add route and team entry**

Add `/daily-plan` to `frontend/user/src/router/index.js` and a role-aware entry from `ProjectTeam.vue`. Add admin API support for teacher-created plans and review.

- [ ] **Step 5: Run tests and build**

```bash
cd frontend/user
node --test src/utils/dailyPlanClosedLoop.test.js
npm run build
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add frontend/user/src/utils/dailyPlanClosedLoop.js frontend/user/src/utils/dailyPlanClosedLoop.test.js frontend/user/src/views/DailyPlan.vue frontend/user/src/router/index.js frontend/user/src/views/ProjectTeam.vue frontend/admin/src/api/dailyPlan.js
git commit -m "feat(daily-plan): add student completion and review timeline"
```

## Task 8: Verify Phase 3 acceptance

- [ ] **Step 1: Run focused backend tests**

```bash
cd backend
mvn -Dtest=ExamAssignmentDailyPlanSchemaTest,ExamAssignmentServiceTest,ExamServiceTest,ExamClosedLoopAdapterTest,AdminExamAssignmentControllerTest,DailyPlanServiceTest,DailyPlanControllerTest test
```

Expected: zero failures.

- [ ] **Step 2: Run backend regression**

```bash
cd backend
mvn test
```

Expected: zero failures.

- [ ] **Step 3: Run frontend verification**

```bash
cd frontend/user
node --test src/utils/examClosedLoop.test.js src/utils/dailyPlanClosedLoop.test.js
npm run build

cd ../admin
npm run build
```

Expected: tests and builds pass.

- [ ] **Step 4: Execute acceptance scenarios**

With exam and daily-plan adapters enabled:

1. Complete a self-test; confirm no formal teacher-review item is created.
2. Publish an objective-only teacher exam; verify the stored pass score and final-review mode.
3. Fail it; verify a draft exists but no project task exists.
4. Teacher edits and publishes the draft; complete training; verify `READY_FOR_RECHECK`.
5. Start reattempt; verify full lineage.
6. Publish an exam with manual questions; grade it; verify the score recommendation is recomputed.
7. Create one system daily plan and one teacher daily plan.
8. Exercise manual-final, auto-pass-auditable and advisory-only modes.
9. Revoke an auto pass and verify the old decision remains visible.

- [ ] **Step 5: Record and commit evidence**

```bash
git add docs/verification/closed-loop/phase-3
git commit -m "test(closed-loop): record phase three acceptance evidence"
```
