# OREP Closed-Loop Phase 2 Roadshow and Resources Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把完整路演、PPT 页/整套 PPT、讲稿段落和团队材料接入阶段 1 的统一闭环，并保留现有 AI 评分和材料审核能力。

**Architecture:** 路演适配器在既有评分报告落库后提交成果级检查点、评估证据和整改草案；下一轮评分只做问题对账，不自动代替老师裁决。PPT 质量检查暂由用户端桥接到 Spring 闭环接口，并固定为“必须人工终审”；讲稿和材料退回通过领域事件进入同一草案发布链路。

**Tech Stack:** Java 21、Spring Boot 3.2、JdbcTemplate、JUnit 5、Mockito、Vue 3、Element Plus、Node test runner、Vite。

---

## File map

**Create**

- `backend/src/main/java/com/orep/backend/service/closedloop/adapter/RoadshowClosedLoopAdapter.java`
- `backend/src/main/java/com/orep/backend/service/closedloop/adapter/RoadshowCycleReconciler.java`
- `backend/src/main/java/com/orep/backend/service/closedloop/adapter/ResourceClosedLoopAdapter.java`
- `backend/src/main/java/com/orep/backend/service/closedloop/event/ResourceReviewRejectedEvent.java`
- `backend/src/main/java/com/orep/backend/service/closedloop/event/ResourceReviewRejectedListener.java`
- `backend/src/main/java/com/orep/backend/controller/ClosedLoopAdapterController.java`
- `backend/src/main/java/com/orep/backend/dto/closedloop/ClosedLoopAdapterRequests.java`
- `backend/src/test/java/com/orep/backend/service/closedloop/adapter/RoadshowClosedLoopAdapterTest.java`
- `backend/src/test/java/com/orep/backend/service/closedloop/adapter/RoadshowCycleReconcilerTest.java`
- `backend/src/test/java/com/orep/backend/service/closedloop/adapter/ResourceClosedLoopAdapterTest.java`
- `backend/src/test/java/com/orep/backend/controller/ClosedLoopAdapterControllerTest.java`
- `frontend/user/src/utils/closedLoopResourceBridge.js`
- `frontend/user/src/utils/closedLoopResourceBridge.test.js`
- `frontend/user/src/utils/closedLoopRoadshow.js`
- `frontend/user/src/utils/closedLoopRoadshow.test.js`

**Modify**

- `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java` — 评分报告持久化后调用路演适配器。
- `backend/src/test/java/com/orep/backend/service/AiScoringSessionServiceTest.java` — 验证开关、幂等和异常隔离。
- `backend/src/main/java/com/orep/backend/service/ProjectTeamService.java:1063` — 材料退回发布领域事件。
- `backend/src/test/java/com/orep/backend/controller/ProjectTeamControllerTest.java` — 验证退回原因和事件触发。
- `frontend/user/src/views/ai-score-report/AiScoreReportTodos.vue` — 展示系统整改草案、发布状态和下一轮对账结果。
- `frontend/user/src/views/PptHistoryDetail.vue:3571` — 质量检查成功后向闭环接口提交不可变快照。

## Task 1: Define roadshow mapping and idempotency

- [ ] **Step 1: Write the failing adapter test**

Create `backend/src/test/java/com/orep/backend/service/closedloop/adapter/RoadshowClosedLoopAdapterTest.java`:

```java
@ExtendWith(MockitoExtension.class)
class RoadshowClosedLoopAdapterTest {
    @Mock ClosedLoopService closedLoopService;
    @Mock ClosedLoopRemediationService remediationService;

    @Test
    void mapsOneReportToOneCheckpointAndDraftsWithoutPublishingTasks() {
        RoadshowClosedLoopAdapter adapter =
                new RoadshowClosedLoopAdapter(closedLoopService, remediationService);
        RoadshowClosedLoopAdapter.ReportSnapshot snapshot =
                Fixtures.failedReport(9L, 21L, "report-88", "v3");

        adapter.accept(snapshot);

        verify(closedLoopService).upsertCheckpoint(argThat(command ->
                command.idempotencyKey().equals("roadshow:team:21:report:report-88")
                && command.reviewMode() == MANUAL_FINAL_REQUIRED));
        verify(remediationService).createDraftBatch(argThat(command ->
                command.issues().stream().allMatch(issue ->
                        issue.sourceRef().startsWith("ai-score-report:report-88/loss:"))));
        verify(remediationService, never()).publishDraft(any(), any());
    }
}
```

- [ ] **Step 2: Run the test and verify it fails**

```bash
cd backend
mvn -Dtest=RoadshowClosedLoopAdapterTest test
```

Expected: compilation failure because the adapter does not exist.

- [ ] **Step 3: Implement immutable report input and mapping**

Create `RoadshowClosedLoopAdapter.java` with records:

```java
public record ReportSnapshot(
        long tenantId,
        long teamId,
        Long projectId,
        String reportId,
        String reportVersion,
        BigDecimal totalScore,
        List<LossSnapshot> losses,
        long actorId,
        Instant completedAt) {}

public record LossSnapshot(
        String lossKey,
        String title,
        String description,
        String evidenceJson,
        String ownerHint,
        String remediationHint) {}
```

The `accept` method must:

1. Return without side effects when either the global or roadshow adapter flag is off.
2. Create `subjectType=ROADSHOW`, `subjectId=reportId`, `checkpointLevel=ARTIFACT`.
3. Force `reviewMode=MANUAL_FINAL_REQUIRED`; a complete roadshow can only be finally decided by a teacher.
4. Persist the score, report version, loss evidence and rule version as an evaluation snapshot.
5. Create or update draft issues using `lossKey`; never call `publishDraft`.
6. Use the exact checkpoint key `roadshow:team:{teamId}:report:{reportId}`.

- [ ] **Step 4: Add negative and duplicate tests**

Add these named cases to `RoadshowClosedLoopAdapterTest.java`:

- disabled flag produces no calls;
- accepting the same report twice leaves one checkpoint and one issue per `lossKey`;
- a report without losses creates an evaluation but no remediation batch;
- malformed evidence is stored as text and cannot break SQL serialization.

- [ ] **Step 5: Run the focused tests**

```bash
cd backend
mvn -Dtest=RoadshowClosedLoopAdapterTest test
```

Expected: all adapter tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/src/main/java/com/orep/backend/service/closedloop/adapter/RoadshowClosedLoopAdapter.java backend/src/test/java/com/orep/backend/service/closedloop/adapter/RoadshowClosedLoopAdapterTest.java
git commit -m "feat(closed-loop): map roadshow reports to draft remediation"
```

## Task 2: Connect the adapter after authoritative report persistence

- [ ] **Step 1: Add a failing service test**

In `AiScoringSessionServiceTest.java`, add a test that completes a scoring session and verifies:

```java
verify(roadshowClosedLoopAdapter).accept(argThat(snapshot ->
        snapshot.reportId().equals(savedReportId)
        && snapshot.losses().size() == persistedRemediationItems.size()));
```

Also assert that the call occurs after `AiScoreRemediationService.persistSnapshot(...)`.

- [ ] **Step 2: Run the test**

```bash
cd backend
mvn -Dtest=AiScoringSessionServiceTest test
```

Expected: failure because no adapter call exists.

- [ ] **Step 3: Inject and invoke the adapter**

Modify `AiScoringSessionService.java` at the report-finalization path near the existing remediation snapshot persistence:

```java
remediationService.persistSnapshot(reportId, authoritativeReport);
try {
    roadshowClosedLoopAdapter.accept(
            roadshowSnapshotFactory.from(reportId, authoritativeReport, currentActor));
} catch (RuntimeException ex) {
    log.error("closed-loop roadshow adapter failed for reportId={}", reportId, ex);
}
```

Constraints:

- Build the snapshot only from the persisted authoritative report.
- Do not call the adapter for previews or incomplete sessions.
- A closed-loop failure must not roll back the original scoring report.
- Record the failure in structured logs with `tenantId`, `teamId` and `reportId`.

- [ ] **Step 4: Add regression tests**

Cover:

- adapter exception does not change the scoring response;
- reprocessing the same callback does not duplicate a checkpoint;
- incomplete/failed scoring sessions do not invoke the adapter.

- [ ] **Step 5: Run scoring and adapter tests**

```bash
cd backend
mvn -Dtest=AiScoringSessionServiceTest,RoadshowClosedLoopAdapterTest test
```

Expected: tests pass and existing scoring assertions are unchanged.

- [ ] **Step 6: Commit**

```bash
git add backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java backend/src/test/java/com/orep/backend/service/AiScoringSessionServiceTest.java
git commit -m "feat(closed-loop): ingest authoritative roadshow reports"
```

## Task 3: Reconcile issues across roadshow rounds

- [ ] **Step 1: Write the failing reconciliation tests**

Create `RoadshowCycleReconcilerTest.java` with three previous issues and a next report:

```java
@Test
void classifiesResolvedPersistentRegressedAndNewIssues() {
    Reconciliation result = reconciler.reconcile(previousCycle, nextReport);

    assertThat(result.resolvedKeys()).containsExactly("pace");
    assertThat(result.persistentKeys()).containsExactly("market-proof");
    assertThat(result.regressedKeys()).containsExactly("speaker-handoff");
    assertThat(result.newKeys()).containsExactly("financial-source");
}
```

- [ ] **Step 2: Run and verify failure**

```bash
cd backend
mvn -Dtest=RoadshowCycleReconcilerTest test
```

Expected: compilation failure.

- [ ] **Step 3: Implement reconciliation**

Create `RoadshowCycleReconciler.java` and reuse the existing `AiScoreTaskVerification` evidence when available. Matching order:

1. stable `lossKey`;
2. existing remediation task identifier;
3. normalized rule identifier and evidence location;
4. unmatched items become `NEW`, never guessed by title similarity.

Persist:

- a `closed_loop_cycle_link` from previous to current checkpoint;
- issue relation/status evidence (`RESOLVED_SUGGESTED`, `PERSISTENT`, `REGRESSED`, `NEW`);
- the new evaluation snapshot.

Do not create a final `PASSED` decision. Resolved is a system recommendation until the authorized reviewer decides.

- [ ] **Step 4: Add edge-case tests**

Cover missing previous cycle, identical callbacks, missing stable keys, and one old issue splitting into multiple new evidence items.

- [ ] **Step 5: Run tests**

```bash
cd backend
mvn -Dtest=RoadshowCycleReconcilerTest,RoadshowClosedLoopAdapterTest test
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add backend/src/main/java/com/orep/backend/service/closedloop/adapter/RoadshowCycleReconciler.java backend/src/test/java/com/orep/backend/service/closedloop/adapter/RoadshowCycleReconcilerTest.java
git commit -m "feat(closed-loop): reconcile roadshow issues across rounds"
```

## Task 4: Present roadshow remediation as drafts, not completed tasks

- [ ] **Step 1: Write the failing presentation tests**

Create `frontend/user/src/utils/closedLoopRoadshow.test.js`:

```js
import test from 'node:test'
import assert from 'node:assert/strict'
import { presentRoadshowItem } from './closedLoopRoadshow.js'

test('draft remediation is visibly pending teacher publication', () => {
  assert.deepEqual(
    presentRoadshowItem({ state: 'DRAFT', reconciliation: 'PERSISTENT' }),
    { badge: '系统草案', action: '等待老师确认负责人、截止时间和重练范围', tone: 'warning' }
  )
})
```

- [ ] **Step 2: Run and verify failure**

```bash
cd frontend/user
node --test src/utils/closedLoopRoadshow.test.js
```

Expected: module-not-found failure.

- [ ] **Step 3: Implement the pure presentation mapper**

Create `closedLoopRoadshow.js` with explicit mappings for:

- `DRAFT`;
- `PUBLISHED`;
- `READY_FOR_RECHECK`;
- `RESOLVED_SUGGESTED`;
- `PERSISTENT`;
- `REGRESSED`;
- `NEW`.

Unknown states must map to `需人工确认`, not to a success style.

- [ ] **Step 4: Update the report remediation view**

Modify `frontend/user/src/views/ai-score-report/AiScoreReportTodos.vue` so each row displays:

- problem/evidence source;
- current round and previous round;
- draft vs published task state;
- assignee and due date only after publication;
- reconciliation result;
- a link to the project task when `taskLinkId` exists.

Remove any wording implying AI remediation items are already official team assignments before publication.

- [ ] **Step 5: Run tests and build**

```bash
cd frontend/user
node --test src/utils/closedLoopRoadshow.test.js
npm run build
```

Expected: test and Vite build succeed.

- [ ] **Step 6: Commit**

```bash
git add frontend/user/src/utils/closedLoopRoadshow.js frontend/user/src/utils/closedLoopRoadshow.test.js frontend/user/src/views/ai-score-report/AiScoreReportTodos.vue
git commit -m "feat(closed-loop): show roadshow remediation lifecycle"
```

## Task 5: Add the PPT quality-check bridge

- [ ] **Step 1: Write failing backend controller tests**

Create `ClosedLoopAdapterControllerTest.java` cases for:

```text
POST /api/closed-loop/adapters/resource/ppt-quality
```

Assert:

- a valid team member can submit page-level quality evidence;
- a user outside the team receives 403;
- missing `deckId`, `deckVersion`, `teamId` or check evidence receives 400;
- duplicate `sourceEventId` returns the existing snapshot;
- client-supplied `AUTO_PASS_AUDITABLE` is ignored and stored as `MANUAL_FINAL_REQUIRED`.

- [ ] **Step 2: Run and verify failure**

```bash
cd backend
mvn -Dtest=ClosedLoopAdapterControllerTest test
```

Expected: 404 or compilation failure.

- [ ] **Step 3: Implement DTO, access checks and adapter**

Create `ClosedLoopAdapterRequests.PptQualitySnapshot`:

```java
public record PptQualitySnapshot(
        Long teamId,
        Long projectId,
        String deckId,
        String deckVersion,
        String sourceEventId,
        List<PageCheck> pageChecks,
        String wholeDeckSummary) {}
```

The controller must get tenant/user identity from authenticated server context, not from the body. `ResourceClosedLoopAdapter` must:

- create one whole-deck checkpoint and child page checkpoints;
- store `evaluatorType=CLIENT_BRIDGE`;
- force `reviewMode=MANUAL_FINAL_REQUIRED`;
- include deck version and page number in each issue `sourceRef`;
- generate drafts only for failed/uncertain checks;
- use `ppt-quality:{teamId}:{deckId}:{deckVersion}:{sourceEventId}` for idempotency.

- [ ] **Step 4: Run backend tests**

```bash
cd backend
mvn -Dtest=ClosedLoopAdapterControllerTest,ResourceClosedLoopAdapterTest test
```

Expected: all tests pass.

- [ ] **Step 5: Write the failing frontend bridge test**

Create `closedLoopResourceBridge.test.js`:

```js
test('normalizes quality output without inventing projectId', () => {
  const payload = toPptQualitySnapshot({
    teamId: 21,
    projectId: null,
    deckId: 'deck-7',
    version: 4,
    sourceEventId: 'quality-93',
    checks: [{ page: 3, status: 'failed', evidence: ['字号过小'] }]
  })
  assert.equal(payload.projectId, null)
  assert.equal(payload.pageChecks[0].pageNumber, 3)
})
```

- [ ] **Step 6: Implement the bridge and call it from the PPT page**

Create `closedLoopResourceBridge.js` as a pure normalizer plus one request function. In `PptHistoryDetail.vue`, call the bridge only after `/quality-check` returns a successful, versioned result:

```js
await submitPptQualitySnapshot({
  teamId: activeTeamId.value,
  projectId: activeProjectId.value ?? null,
  deckId: String(taskId.value),
  version: qualityResult.version,
  sourceEventId: qualityResult.runId,
  checks: qualityResult.pageChecks
})
```

If the bridge fails, show “质量检查已完成，闭环草案同步失败，可重试”; do not report the quality check itself as failed.

- [ ] **Step 7: Run frontend tests and build**

```bash
cd frontend/user
node --test src/utils/closedLoopResourceBridge.test.js
npm run build
```

Expected: pass.

- [ ] **Step 8: Commit**

```bash
git add backend/src/main/java/com/orep/backend/controller/ClosedLoopAdapterController.java backend/src/main/java/com/orep/backend/dto/closedloop/ClosedLoopAdapterRequests.java backend/src/main/java/com/orep/backend/service/closedloop/adapter/ResourceClosedLoopAdapter.java backend/src/test/java/com/orep/backend/controller/ClosedLoopAdapterControllerTest.java backend/src/test/java/com/orep/backend/service/closedloop/adapter/ResourceClosedLoopAdapterTest.java frontend/user/src/utils/closedLoopResourceBridge.js frontend/user/src/utils/closedLoopResourceBridge.test.js frontend/user/src/views/PptHistoryDetail.vue
git commit -m "feat(closed-loop): bridge PPT quality evidence into remediation drafts"
```

## Task 6: Turn material and script rejection into remediation drafts

- [ ] **Step 1: Add failing project-team tests**

In `ProjectTeamControllerTest.java`, add:

- rejection without a reason returns 400;
- `CHANGES_REQUESTED` publishes `ResourceReviewRejectedEvent`;
- approval does not publish rejection;
- the existing material status remains compatible.

- [ ] **Step 2: Run and verify failure**

```bash
cd backend
mvn -Dtest=ProjectTeamControllerTest test
```

Expected: event assertion fails and blank reasons are currently accepted.

- [ ] **Step 3: Publish the domain event**

Modify `ProjectTeamService.reviewMaterial(...)` to publish:

```java
new ResourceReviewRejectedEvent(
        tenantId,
        teamId,
        projectId,
        materialId,
        materialType,
        materialVersion,
        reviewerId,
        normalizedReason,
        reviewId)
```

Rules:

- Require a nonblank reason for `CHANGES_REQUESTED` or `REJECTED`.
- Preserve the existing review row and status transition.
- Publish only after the transaction commits.
- Do not create a formal task inside `ProjectTeamService`.

- [ ] **Step 4: Implement the listener**

`ResourceReviewRejectedListener` maps:

- PPT page -> page checkpoint;
- whole PPT -> artifact checkpoint;
- script paragraph -> paragraph checkpoint;
- whole script/material -> artifact checkpoint.

If the rejected material already has an open linked task, reopen that task through the existing service; otherwise create a draft. The listener must not publish a draft.

- [ ] **Step 5: Add listener tests**

Verify page/paragraph source references, duplicate review idempotency, reopen behavior, and a teacher-authored evaluation snapshot.

- [ ] **Step 6: Run backend regression**

```bash
cd backend
mvn -Dtest=ProjectTeamControllerTest,ResourceClosedLoopAdapterTest test
```

Expected: pass.

- [ ] **Step 7: Commit**

```bash
git add backend/src/main/java/com/orep/backend/service/ProjectTeamService.java backend/src/main/java/com/orep/backend/service/closedloop/event/ResourceReviewRejectedEvent.java backend/src/main/java/com/orep/backend/service/closedloop/event/ResourceReviewRejectedListener.java backend/src/test/java/com/orep/backend/controller/ProjectTeamControllerTest.java backend/src/test/java/com/orep/backend/service/closedloop/adapter/ResourceClosedLoopAdapterTest.java
git commit -m "feat(closed-loop): draft remediation from resource rejection"
```

## Task 7: Verify Phase 2 acceptance

- [ ] **Step 1: Run focused backend tests**

```bash
cd backend
mvn -Dtest=RoadshowClosedLoopAdapterTest,RoadshowCycleReconcilerTest,ResourceClosedLoopAdapterTest,ClosedLoopAdapterControllerTest,AiScoringSessionServiceTest,ProjectTeamControllerTest test
```

Expected: zero failures.

- [ ] **Step 2: Run all backend tests**

```bash
cd backend
mvn test
```

Expected: zero failures.

- [ ] **Step 3: Run user frontend tests and build**

```bash
cd frontend/user
node --test src/utils/closedLoopRoadshow.test.js src/utils/closedLoopResourceBridge.test.js
npm run build
```

Expected: tests and build pass.

- [ ] **Step 4: Manually verify with flags**

Enable only:

```text
OREP_CLOSED_LOOP_ENABLED=true
OREP_CLOSED_LOOP_ADAPTERS_ROADSHOW=true
OREP_CLOSED_LOOP_ADAPTERS_RESOURCE=true
```

Verify:

1. Complete a roadshow scoring session.
2. Confirm one checkpoint and draft batch exist, with no new official task.
3. Teacher publishes one draft after selecting assignee, due date and scope.
4. Accept the task and confirm checkpoint becomes `READY_FOR_RECHECK`.
5. Run the next roadshow and confirm resolved/persistent/regressed/new classification.
6. Run PPT quality check and confirm page/version references.
7. Reject a script paragraph with a reason and confirm a draft or reopened task is produced.

- [ ] **Step 5: Record evidence**

Save API samples and screenshots under:

```text
docs/verification/closed-loop/phase-2/
```

Do not place tokens, cookies or personal information in evidence files.

- [ ] **Step 6: Commit verification evidence**

```bash
git add docs/verification/closed-loop/phase-2
git commit -m "test(closed-loop): record phase two acceptance evidence"
```
