# OREP Closed-Loop Phase 4 Workbenches and Stage Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为老师、队长和学生提供可操作的闭环工作台，并用项目阶段门禁把考试、资源、路演和任务的结果汇总为可追溯的项目推进决策。

**Architecture:** 工作台读取统一闭环查询模型，不直接拼接各领域状态。队长授权使用独立、可撤销、带有效期的 delegation；老师对正式考试、整套 PPT、完整路演和阶段门禁拥有不可下放的最终裁决权。阶段门禁基于关联检查点的快照生成系统建议，最终决定采用追加写入并支持撤销/重开。

**Tech Stack:** Java 21、Spring Boot 3.2、JdbcTemplate、MySQL 8、H2、JUnit 5、MockMvc、Vue 3、Element Plus、Node test runner、Playwright、Vite。

---

## File map

**Create**

- `backend/src/main/resources/sql/create_closed_loop_workbench_gate_tables.sql`
- `deploy/sql/backend-resources/create_closed_loop_workbench_gate_tables.sql`
- `backend/src/main/java/com/orep/backend/service/closedloop/ClosedLoopDelegationService.java`
- `backend/src/main/java/com/orep/backend/service/closedloop/ClosedLoopWorkbenchService.java`
- `backend/src/main/java/com/orep/backend/service/closedloop/StageGateService.java`
- `backend/src/main/java/com/orep/backend/service/closedloop/ClosedLoopOutboxService.java`
- `backend/src/main/java/com/orep/backend/controller/AdminClosedLoopController.java`
- `backend/src/main/java/com/orep/backend/controller/StageGateController.java`
- `backend/src/main/java/com/orep/backend/dto/closedloop/ClosedLoopWorkbenchViews.java`
- `backend/src/test/java/com/orep/backend/service/closedloop/ClosedLoopDelegationServiceTest.java`
- `backend/src/test/java/com/orep/backend/service/closedloop/ClosedLoopWorkbenchServiceTest.java`
- `backend/src/test/java/com/orep/backend/service/closedloop/StageGateServiceTest.java`
- `backend/src/test/java/com/orep/backend/controller/AdminClosedLoopControllerTest.java`
- `backend/src/test/java/com/orep/backend/controller/StageGateControllerTest.java`
- `frontend/admin/src/views/ClosedLoopReview.vue`
- `frontend/admin/src/api/closedLoopReview.js`
- `frontend/admin/src/utils/closedLoopReview.js`
- `frontend/admin/src/utils/closedLoopReview.test.js`
- `frontend/user/src/utils/closedLoopWorkbench.js`
- `frontend/user/src/utils/closedLoopWorkbench.test.js`
- `frontend/user/src/components/project/ClosedLoopBoard.vue`
- `frontend/user/src/components/project/StageGatePanel.vue`
- `frontend/user/tests/closed-loop.spec.js`

**Modify**

- `frontend/admin/src/router/index.js` — 增加老师闭环审核路由。
- `frontend/admin/src/views/Layout.vue` — 增加老师审核入口和待办数量。
- `frontend/user/src/views/ProjectTeam.vue` — 接入队长/学生闭环看板。
- `backend/src/main/java/com/orep/backend/service/closedloop/ClosedLoopAccessService.java` — 使用 delegation 判断普通任务终审。
- `backend/src/main/java/com/orep/backend/controller/ClosedLoopController.java` — 增加角色工作台查询。
- `backend/src/main/resources/application.yml` — 门禁和 outbox 调度开关。
- `deploy/docker-compose.yml` — 增加对应环境变量。

## Task 1: Persist review delegation, stage gates and outbox

- [ ] **Step 1: Write a failing schema test**

Create `ClosedLoopWorkbenchGateSchemaTest.java`. Run schema initialization twice and assert:

```text
CLOSED_LOOP_REVIEW_DELEGATION
CLOSED_LOOP_STAGE_GATE
CLOSED_LOOP_STAGE_GATE_ITEM
CLOSED_LOOP_OUTBOX
```

- [ ] **Step 2: Run and verify failure**

```bash
cd backend
mvn -Dtest=ClosedLoopWorkbenchGateSchemaTest test
```

Expected: missing-table failure.

- [ ] **Step 3: Add identical SQL files**

Core columns:

```sql
CREATE TABLE IF NOT EXISTS closed_loop_review_delegation (
  id BIGINT NOT NULL AUTO_INCREMENT,
  tenant_id BIGINT NOT NULL,
  team_id BIGINT NOT NULL,
  grantor_teacher_id BIGINT NOT NULL,
  captain_id BIGINT NOT NULL,
  subject_type VARCHAR(48) NOT NULL,
  authority VARCHAR(32) NOT NULL,
  valid_from DATETIME NOT NULL,
  valid_until DATETIME DEFAULT NULL,
  revoked_at DATETIME DEFAULT NULL,
  revoke_reason LONGTEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_closed_loop_delegation_active
    (tenant_id, team_id, captain_id, subject_type, authority, revoked_at)
);

CREATE TABLE IF NOT EXISTS closed_loop_stage_gate (
  id BIGINT NOT NULL AUTO_INCREMENT,
  tenant_id BIGINT NOT NULL,
  project_id BIGINT NOT NULL,
  team_id BIGINT NOT NULL,
  gate_code VARCHAR(80) NOT NULL,
  gate_name VARCHAR(160) NOT NULL,
  gate_order INT NOT NULL,
  status VARCHAR(32) NOT NULL,
  current_revision INT NOT NULL DEFAULT 1,
  lock_version INT NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_stage_gate_project_code (tenant_id, project_id, gate_code)
);

CREATE TABLE IF NOT EXISTS closed_loop_stage_gate_item (
  id BIGINT NOT NULL AUTO_INCREMENT,
  gate_id BIGINT NOT NULL,
  checkpoint_id BIGINT NOT NULL,
  required_result VARCHAR(24) NOT NULL,
  blocking TINYINT(1) NOT NULL DEFAULT 1,
  snapshot_revision INT NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uk_stage_gate_item (gate_id, checkpoint_id, snapshot_revision)
);

CREATE TABLE IF NOT EXISTS closed_loop_outbox (
  id BIGINT NOT NULL AUTO_INCREMENT,
  tenant_id BIGINT NOT NULL,
  aggregate_type VARCHAR(48) NOT NULL,
  aggregate_id VARCHAR(120) NOT NULL,
  event_type VARCHAR(80) NOT NULL,
  payload_json LONGTEXT NOT NULL,
  idempotency_key VARCHAR(160) NOT NULL,
  status VARCHAR(24) NOT NULL,
  attempt_count INT NOT NULL DEFAULT 0,
  next_attempt_at DATETIME DEFAULT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  published_at DATETIME DEFAULT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uk_closed_loop_outbox_key (tenant_id, idempotency_key),
  KEY idx_closed_loop_outbox_dispatch (status, next_attempt_at)
);
```

Stage-gate decisions continue to use the Phase 1 append-only `closed_loop_decision` table.

- [ ] **Step 4: Add initializer and repositories**

Use existing resource-loading/JdbcTemplate style. Add upgrade tests from Phase 1–3 schema and keep outbox payload opaque to SQL.

- [ ] **Step 5: Run and commit**

```bash
cd backend
mvn -Dtest=ClosedLoopWorkbenchGateSchemaTest test
git add backend/src/main/resources/sql/create_closed_loop_workbench_gate_tables.sql deploy/sql/backend-resources/create_closed_loop_workbench_gate_tables.sql backend/src/test/java/com/orep/backend/service/closedloop/ClosedLoopWorkbenchGateSchemaTest.java
git commit -m "feat(closed-loop): add delegation gate and outbox schema"
```

## Task 2: Enforce captain pre-review and narrow final-review delegation

- [ ] **Step 1: Write failing delegation tests**

Create `ClosedLoopDelegationServiceTest.java`:

```java
@ParameterizedTest
@ValueSource(strings = {"TEACHER_EXAM", "WHOLE_PPT", "FULL_ROADSHOW", "STAGE_GATE"})
void forbiddenFinalAuthoritiesCannotBeDelegated(String subjectType) {
    assertThatThrownBy(() -> service.grant(finalReview(subjectType), teacher))
        .isInstanceOf(IllegalArgumentException.class);
}

@Test
void captainCanPreReviewOrdinarySubjectsWithoutFinalDelegation() { /* ... */ }

@Test
void activeExplicitDelegationAllowsFinalReviewOfOrdinaryTaskOnly() { /* ... */ }
```

Also cover expiry, revocation, wrong team and tenant isolation.

- [ ] **Step 2: Run and verify failure**

```bash
cd backend
mvn -Dtest=ClosedLoopDelegationServiceTest test
```

Expected: compilation failure.

- [ ] **Step 3: Implement the authority matrix**

Hard-code the non-delegable set in one policy class:

```text
TEACHER_EXAM
WHOLE_PPT
FULL_ROADSHOW
STAGE_GATE
```

Pre-review allowed:

```text
ORDINARY_TASK
PPT_PAGE
SCRIPT_PARAGRAPH
DAILY_PLAN
```

Final delegation allowed only for:

```text
ORDINARY_TASK
DAILY_PLAN
```

The teacher must explicitly grant `FINAL_REVIEW`, with team, captain, subject type and validity window. Every grant/revocation is auditable.

- [ ] **Step 4: Integrate with access checks**

Modify `ClosedLoopAccessService`:

```java
ReviewAuthority resolveAuthority(
        Actor actor,
        long teamId,
        SubjectType subjectType,
        ReviewAction action,
        Instant now);
```

Teacher authority remains primary. Captain role alone never implies final review. Return 403 with a machine-readable reason code such as `FINAL_REVIEW_NOT_DELEGATED`.

- [ ] **Step 5: Add API tests**

Add:

```text
POST   /api/admin/closed-loop/delegations
GET    /api/admin/closed-loop/delegations
DELETE /api/admin/closed-loop/delegations/{id}
```

Deletion performs revocation and requires a reason; it never deletes the row.

- [ ] **Step 6: Run and commit**

```bash
cd backend
mvn -Dtest=ClosedLoopDelegationServiceTest,AdminClosedLoopControllerTest test
git add backend/src/main/java/com/orep/backend/service/closedloop/ClosedLoopDelegationService.java backend/src/main/java/com/orep/backend/service/closedloop/ClosedLoopAccessService.java backend/src/main/java/com/orep/backend/controller/AdminClosedLoopController.java backend/src/test/java/com/orep/backend/service/closedloop/ClosedLoopDelegationServiceTest.java backend/src/test/java/com/orep/backend/controller/AdminClosedLoopControllerTest.java
git commit -m "feat(closed-loop): enforce captain review delegation"
```

## Task 3: Build role-specific read models

- [ ] **Step 1: Write failing workbench tests**

Create `ClosedLoopWorkbenchServiceTest.java` with one dataset and assert:

- teacher sees final-review queue, drafts needing publication, overdue tasks and reopened items;
- captain sees pre-review queue, team tasks and permitted final reviews;
- student sees own tasks, evidence requests, decisions/reasons and recheck status;
- no role sees data from another tenant/team;
- counts equal the returned filtered items.

- [ ] **Step 2: Run and verify failure**

```bash
cd backend
mvn -Dtest=ClosedLoopWorkbenchServiceTest test
```

Expected: compilation failure.

- [ ] **Step 3: Implement query DTOs and service**

Return a stable envelope:

```java
public record WorkbenchView(
        RoleView role,
        SummaryCounts counts,
        List<ReviewItem> reviewQueue,
        List<DraftItem> draftQueue,
        List<ExecutionItem> executionQueue,
        List<RecheckItem> recheckQueue,
        List<StageGateSummary> stageGates) {}
```

Every item includes:

- domain, subject type/id/version;
- cycle number and status;
- system recommendation plus evidence summary;
- latest human decision and reason;
- task/draft link;
- allowed actions returned by the server.

The frontend must never reconstruct authority from role names.

- [ ] **Step 4: Add endpoints**

```text
GET /api/admin/closed-loop/workbench
GET /api/closed-loop/workbench
GET /api/closed-loop/checkpoints/{id}/timeline
```

Timeline is chronological and includes evaluations, decisions, draft edits, publication, submissions, reviews, rechecks and reopen actions.

- [ ] **Step 5: Add query-index assertions**

Use `EXPLAIN` in a MySQL integration profile or repository-level tests to ensure team/status and checkpoint/time indexes are used. Avoid one query per item.

- [ ] **Step 6: Run and commit**

```bash
cd backend
mvn -Dtest=ClosedLoopWorkbenchServiceTest,AdminClosedLoopControllerTest,ClosedLoopControllerTest test
git add backend/src/main/java/com/orep/backend/service/closedloop/ClosedLoopWorkbenchService.java backend/src/main/java/com/orep/backend/dto/closedloop/ClosedLoopWorkbenchViews.java backend/src/main/java/com/orep/backend/controller/AdminClosedLoopController.java backend/src/main/java/com/orep/backend/controller/ClosedLoopController.java backend/src/test/java/com/orep/backend/service/closedloop/ClosedLoopWorkbenchServiceTest.java
git commit -m "feat(closed-loop): add role-specific workbench read models"
```

## Task 4: Implement project stage gates

- [ ] **Step 1: Write failing gate tests**

Create `StageGateServiceTest.java` and cover:

```java
@Test
void systemSuggestsBlockedWhenRequiredCheckpointIsNotPassed() { /* ... */ }

@Test
void onlyTeacherCanFinallyPassOrRejectGate() { /* ... */ }

@Test
void revocationAppendsDecisionAndReopensGate() { /* ... */ }

@Test
void laterCheckpointRegressionReopensPassedGateForReview() { /* ... */ }

@Test
void concurrentDecisionReturnsConflict() { /* ... */ }
```

- [ ] **Step 2: Run and verify failure**

```bash
cd backend
mvn -Dtest=StageGateServiceTest test
```

Expected: compilation failure.

- [ ] **Step 3: Implement gate aggregation**

Required methods:

```java
StageGate create(CreateGate command, Actor teacher);
GateEvaluation evaluate(long gateId, Actor actor);
StageGate decide(long gateId, GateDecision command, Actor teacher);
StageGate reopen(long gateId, String reason, Actor teacher);
List<StageGateSummary> listForProject(long projectId, Actor actor);
```

Rules:

- gate items reference exact checkpoint revisions;
- system evaluation produces `READY`, `BLOCKED` or `INCOMPLETE` plus evidence;
- final actions are `PASS`, `REJECT`, `REEXECUTE`, `REVOKE`;
- every final action requires teacher identity and reason;
- no captain delegation can grant stage-gate final authority;
- a passed gate can be reopened without destroying the prior pass;
- stage progression must not be inferred from all project tasks being `DONE`.

- [ ] **Step 4: Add controller tests and endpoints**

```text
POST /api/admin/projects/{projectId}/stage-gates
GET  /api/projects/{projectId}/stage-gates
POST /api/admin/stage-gates/{gateId}/evaluate
POST /api/admin/stage-gates/{gateId}/decision
POST /api/admin/stage-gates/{gateId}/reopen
```

Use optimistic `expectedRevision`; mismatches return 409 and include current revision.

- [ ] **Step 5: Publish outbox events**

In the same transaction as decision state changes, enqueue:

```text
STAGE_GATE_READY
STAGE_GATE_PASSED
STAGE_GATE_REJECTED
STAGE_GATE_REOPENED
REMEDIATION_DRAFT_READY
TASK_READY_FOR_RECHECK
```

Do not send external messages directly in the transaction.

- [ ] **Step 6: Run and commit**

```bash
cd backend
mvn -Dtest=StageGateServiceTest,StageGateControllerTest test
git add backend/src/main/java/com/orep/backend/service/closedloop/StageGateService.java backend/src/main/java/com/orep/backend/service/closedloop/ClosedLoopOutboxService.java backend/src/main/java/com/orep/backend/controller/StageGateController.java backend/src/test/java/com/orep/backend/service/closedloop/StageGateServiceTest.java backend/src/test/java/com/orep/backend/controller/StageGateControllerTest.java
git commit -m "feat(closed-loop): add teacher-owned project stage gates"
```

## Task 5: Build the teacher review workbench

- [ ] **Step 1: Write failing pure mapper tests**

Create `frontend/admin/src/utils/closedLoopReview.test.js`:

```js
test('uses server allowedActions instead of deriving authority', () => {
  const item = presentReviewItem({
    subjectType: 'FULL_ROADSHOW',
    allowedActions: ['PREVIEW'],
    latestDecision: null
  })
  assert.equal(item.canFinalReview, false)
})

test('requires reason for every teacher decision', () => {
  assert.equal(validateDecision({ action: 'PASS', reason: '  ' }).valid, false)
})
```

- [ ] **Step 2: Run and verify failure**

```bash
cd frontend/admin
node --test src/utils/closedLoopReview.test.js
```

Expected: module-not-found failure.

- [ ] **Step 3: Implement API and mapper**

`closedLoopReview.js` must map domain/status/authority without treating unknown values as passed. `closedLoopReview.js` request helpers must preserve server error codes, especially 403 and 409.

- [ ] **Step 4: Implement `ClosedLoopReview.vue`**

Use four explicit queues:

1. 待终审；
2. 待确认整改草案；
3. 待复查；
4. 已撤销/已重开。

The detail drawer must display system evidence, captain pre-review, history and editable draft fields. Decision buttons are `通过`, `驳回`, `要求重新执行`; all require a reason. Draft publication requires assignee, due date and rework scope.

- [ ] **Step 5: Add route/navigation**

Modify admin router and layout. Display badge count from the workbench API. Hide the entry from non-teacher roles but still rely on backend authorization.

- [ ] **Step 6: Run tests/build and commit**

```bash
cd frontend/admin
node --test src/utils/closedLoopReview.test.js
npm run build
git add frontend/admin/src/views/ClosedLoopReview.vue frontend/admin/src/api/closedLoopReview.js frontend/admin/src/utils/closedLoopReview.js frontend/admin/src/utils/closedLoopReview.test.js frontend/admin/src/router/index.js frontend/admin/src/views/Layout.vue
git commit -m "feat(closed-loop): add teacher review workbench"
```

## Task 6: Build captain and student project views

- [ ] **Step 1: Write failing mapper tests**

Create `closedLoopWorkbench.test.js`:

```js
test('captain pre-review remains distinct from final decision', () => {
  const item = presentWorkbenchItem({
    allowedActions: ['PRE_REVIEW'],
    captainReview: { result: 'RETURN_SUGGESTED' },
    finalDecision: null
  })
  assert.equal(item.statusLabel, '队长建议退回，等待老师裁决')
})

test('accepted task is ready for recheck, not passed', () => {
  assert.equal(
    presentWorkbenchItem({ checkpointStatus: 'READY_FOR_RECHECK' }).statusLabel,
    '整改已验收，等待复查'
  )
})
```

- [ ] **Step 2: Run and verify failure**

```bash
cd frontend/user
node --test src/utils/closedLoopWorkbench.test.js
```

Expected: module-not-found failure.

- [ ] **Step 3: Implement `ClosedLoopBoard.vue`**

For captains, show:

- ordinary task/PPT page/script paragraph/daily-plan pre-review;
- return suggestion with required reason;
- explicit delegated final-review badge and expiry;
- team issue, draft, task and recheck queues.

For students, show:

- own assignment and due date;
- required evidence;
- submission/review history;
- failure reason and linked rework;
- current cycle and next recheck.

- [ ] **Step 4: Implement `StageGatePanel.vue`**

Show current gate, system readiness, blocking checkpoints, latest teacher decision, reason and reopened state. Do not show decision actions in user frontend unless the server explicitly returns them.

- [ ] **Step 5: Integrate into `ProjectTeam.vue`**

Keep existing role views behind the Phase 1 feature flag. Add tabs for `闭环任务` and `项目阶段`; avoid replacing current task management until rollout is complete.

- [ ] **Step 6: Run and commit**

```bash
cd frontend/user
node --test src/utils/closedLoopWorkbench.test.js
npm run build
git add frontend/user/src/utils/closedLoopWorkbench.js frontend/user/src/utils/closedLoopWorkbench.test.js frontend/user/src/components/project/ClosedLoopBoard.vue frontend/user/src/components/project/StageGatePanel.vue frontend/user/src/views/ProjectTeam.vue
git commit -m "feat(closed-loop): add captain and student workbenches"
```

## Task 7: Dispatch outbox safely and expose operations metrics

- [ ] **Step 1: Write failing outbox tests**

Cover:

- one event is delivered once for a stable idempotency key;
- transient failure schedules exponential retry;
- permanent invalid payload moves to `DEAD_LETTER`;
- disabling dispatcher leaves pending events untouched;
- dispatch never changes the domain transaction result.

- [ ] **Step 2: Run and verify failure**

```bash
cd backend
mvn -Dtest=ClosedLoopOutboxServiceTest test
```

Expected: tests fail until dispatcher exists.

- [ ] **Step 3: Implement dispatcher**

Add a scheduled dispatcher guarded by:

```yaml
orep:
  closed-loop:
    outbox:
      dispatch-enabled: ${OREP_CLOSED_LOOP_OUTBOX_DISPATCH_ENABLED:false}
      batch-size: 50
      max-attempts: 8
```

Initially dispatch to the existing in-app notification mechanism only. Preserve event payloads for future email/IM adapters.

- [ ] **Step 4: Add metrics**

Expose counters/timers:

```text
closed_loop_checkpoint_total{domain,status}
closed_loop_review_queue_size{role}
closed_loop_draft_age_seconds
closed_loop_recheck_age_seconds
closed_loop_outbox_total{status,event}
closed_loop_stage_gate_total{status}
```

No metric label may contain tenant, user, project or task identifiers.

- [ ] **Step 5: Run and commit**

```bash
cd backend
mvn -Dtest=ClosedLoopOutboxServiceTest test
git add backend/src/main/java/com/orep/backend/service/closedloop/ClosedLoopOutboxService.java backend/src/main/resources/application.yml deploy/docker-compose.yml backend/src/test/java/com/orep/backend/service/closedloop/ClosedLoopOutboxServiceTest.java
git commit -m "feat(closed-loop): dispatch notifications through transactional outbox"
```

## Task 8: Add end-to-end role and loop tests

- [ ] **Step 1: Create Playwright fixtures**

Use isolated test users:

```text
teacher_closed_loop
captain_closed_loop
student_closed_loop
```

Seed one project, one roadshow issue, one PPT page issue, one formal exam failure and one daily plan.

- [ ] **Step 2: Write `frontend/user/tests/closed-loop.spec.js`**

Scenarios:

1. system evidence creates an inactive draft;
2. captain pre-reviews and suggests return;
3. teacher final-rejects with reason;
4. teacher edits and publishes a remediation task;
5. student submits evidence;
6. captain pre-reviews the ordinary task;
7. authorized reviewer accepts task;
8. checkpoint becomes `READY_FOR_RECHECK`, not passed;
9. recheck creates a new evaluation;
10. teacher passes and project gate becomes ready;
11. teacher passes gate;
12. teacher revokes gate; history remains.

Also assert captain cannot final-decide a formal exam, whole PPT, full roadshow or stage gate.

- [ ] **Step 3: Run E2E**

```bash
cd frontend/user
npx playwright test tests/closed-loop.spec.js
```

Expected: all scenarios pass.

- [ ] **Step 4: Run full regression**

```bash
cd backend
mvn test

cd ../frontend/user
node --test src/utils/*.test.js
npm run build
npx playwright test tests/closed-loop.spec.js

cd ../admin
node --test src/utils/*.test.js
npm run build
```

Expected: zero test failures and both builds succeed.

- [ ] **Step 5: Commit**

```bash
git add frontend/user/tests/closed-loop.spec.js
git commit -m "test(closed-loop): cover role authority and recheck lifecycle"
```

## Task 9: Roll out progressively

- [ ] **Step 1: Establish baseline metrics**

Before enabling adapters, record:

- existing scoring, exam, material-review and project-task error rates;
- number and age of pending reviews;
- current task completion latency;
- database write volume.

- [ ] **Step 2: Enable by stage**

Rollout order:

1. closed-loop core read/write with all adapters off;
2. resource adapter for one internal team;
3. roadshow adapter;
4. formal exam adapter;
5. daily-plan adapter;
6. workbenches;
7. stage gates;
8. outbox dispatch.

Hold each stage for at least one complete business workflow and review error, duplicate, backlog and latency metrics.

- [ ] **Step 3: Verify rollback**

For each adapter, turn its flag off and confirm:

- old pages and APIs remain usable;
- existing closed-loop rows remain readable;
- no table/data deletion is required;
- pending official `ProjectTask` rows continue through the existing task flow.

- [ ] **Step 4: Publish operational runbook**

Create:

```text
docs/runbooks/closed-loop-operations.md
```

Include flags, health checks, queue queries, retry procedure, 409 conflict handling, dead-letter recovery and rollback.

- [ ] **Step 5: Record Phase 4 evidence and commit**

```bash
git add docs/runbooks/closed-loop-operations.md docs/verification/closed-loop/phase-4
git commit -m "docs(closed-loop): add rollout and operations runbook"
```

## Phase 4 completion checklist

- [ ] Teacher, captain and student workbenches use server-provided allowed actions.
- [ ] Captain pre-review is clearly separate from final decision.
- [ ] Non-delegable final-review types cannot be granted by API or database service.
- [ ] Stage-gate decisions are teacher-only, append-only and revocable.
- [ ] Task acceptance leads to recheck, not automatic pass.
- [ ] Outbox is idempotent and disabled by default.
- [ ] Full backend, frontend and Playwright regression passes.
- [ ] Rollback is demonstrated without deleting closed-loop data.
