# Teacher Real Review Queue Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将教师工作台接入本人指导团队的真实最新待审提交，并禁止审核旧版本或重复审核。

**Architecture:** 新增独立 `TeacherReviewController` 提供教师队列和详情读取接口，查询与审核约束继续集中在现有 `ProjectTeamService`，复用附件和链接组装逻辑。教师端在有 token 时把真实审核数据映射进现有混合队列，其他待办仍保留演示数据；审核成功后本地移除当前项并自动进入下一项。

**Tech Stack:** Java 21、Spring Boot 3.2、JdbcTemplate、JUnit 5、Mockito、Vue 3、Axios、Vite、gstack browse

---

## File Structure

- Create: `backend/src/main/java/com/orep/backend/controller/TeacherReviewController.java`：教师审核读取接口。
- Create: `backend/src/test/java/com/orep/backend/controller/TeacherReviewControllerTest.java`：身份属性委托和返回结构测试。
- Create: `backend/src/test/java/com/orep/backend/service/ProjectTeamServiceReviewTest.java`：队列范围、详情历史和审核约束测试。
- Modify: `backend/src/main/java/com/orep/backend/service/ProjectTeamService.java`：队列、详情、归属判断和审核状态保护。
- Modify: `frontend/teacher/src/api/index.js`：教师队列、详情和现有审核请求。
- Modify: `frontend/teacher/src/views/WorkbenchView.vue`：真实数据加载、详情状态、历史版本、提交审核和错误恢复。

### Task 1: Teacher Review Read API

**Files:**
- Create: `backend/src/test/java/com/orep/backend/controller/TeacherReviewControllerTest.java`
- Create: `backend/src/main/java/com/orep/backend/controller/TeacherReviewController.java`
- Test: `backend/src/test/java/com/orep/backend/controller/TeacherReviewControllerTest.java`

- [ ] **Step 1: Write failing controller tests**

覆盖 `GET /api/teacher/review-queue` 和 `GET /api/teacher/submissions/{id}`，断言 request 中的 `tenantId`、`userId`、`role` 原样传入 `ProjectTeamService`，并断言 `Result.success` 返回 `code=200`。

- [ ] **Step 2: Verify tests fail because the controller does not exist**

Run: `./mvnw -Dtest=TeacherReviewControllerTest test` in `backend`

Expected: compilation failure naming missing `TeacherReviewController` or missing service methods.

- [ ] **Step 3: Add the minimal controller**

实现：

```java
@RestController
@RequestMapping("/api/teacher")
public class TeacherReviewController {
    @GetMapping("/review-queue")
    public Result<List<Map<String, Object>>> reviewQueue(HttpServletRequest request) { ... }

    @GetMapping("/submissions/{submissionId}")
    public Result<Map<String, Object>> submission(
            @PathVariable Long submissionId,
            HttpServletRequest request
    ) { ... }
}
```

- [ ] **Step 4: Run the controller tests**

Run: `./mvnw -Dtest=TeacherReviewControllerTest test`

Expected: PASS.

### Task 2: Scoped Latest-Submission Queries

**Files:**
- Create: `backend/src/test/java/com/orep/backend/service/ProjectTeamServiceReviewTest.java`
- Modify: `backend/src/main/java/com/orep/backend/service/ProjectTeamService.java`

- [ ] **Step 1: Write failing queue-scope tests**

使用 Mockito 捕获 SQL 和参数，断言：

- `TEACHER` 查询包含 `pt.mentor_id = ?` 和 `MENTOR` 成员关系，参数含当前 `userId`。
- `ADMIN`/`SCHOOL_ADMIN` 查询不要求导师归属，但仍包含 `pt.tenant_id = ?`。
- SQL 通过 `NOT EXISTS` 排除同任务更新版本，并只取 `PENDING_REVIEW`、`REVIEWING`。
- 非教师角色抛出 403。

- [ ] **Step 2: Run the service tests and verify RED**

Run: `./mvnw -Dtest=ProjectTeamServiceReviewTest test`

Expected: compilation failure for missing `teacherReviewQueue` and `teacherSubmissionDetail`.

- [ ] **Step 3: Implement `teacherReviewQueue`**

新增 public 方法：

```java
public List<Map<String, Object>> teacherReviewQueue(
        Long tenantId, Long userId, String role)
```

查询从 `project_task_submission` 出发，关联任务、团队和提交人；训练日和集训营使用相关子查询获取单个展示上下文，避免一个任务映射多个训练日时重复提交。调用 `attachSubmissionPayloads(rows)` 后返回。

- [ ] **Step 4: Write failing submission-detail tests**

断言详情查询同时校验租户和教师指导范围，返回 `requirements`、`history`，并仅在当前记录是最新待审版本时返回 `canReview=true`。

- [ ] **Step 5: Implement `teacherSubmissionDetail`**

新增 public 方法：

```java
public Map<String, Object> teacherSubmissionDetail(
        Long submissionId, Long tenantId, Long userId, String role)
```

跨租户和越权统一返回 404；详情复用 `attachSubmissionPayloads`，要求按 `sort_order,id` 排序，历史按 `version_no,id` 倒序。

- [ ] **Step 6: Run the focused backend tests**

Run: `./mvnw -Dtest=TeacherReviewControllerTest,ProjectTeamServiceReviewTest test`

Expected: PASS.

### Task 3: Protect Submission Review State

**Files:**
- Modify: `backend/src/test/java/com/orep/backend/service/ProjectTeamServiceReviewTest.java`
- Modify: `backend/src/main/java/com/orep/backend/service/ProjectTeamService.java`

- [ ] **Step 1: Write failing review-protection tests**

覆盖：

- 教师只能审核本人指导团队；管理员可审核租户内团队。
- 队长仍可按 `REVIEW_SUBMISSION` 权限审核。
- 当前提交不是任务最新版本时返回 409。
- 当前状态不是 `PENDING_REVIEW`/`REVIEWING` 时返回 409。
- 条件更新影响行数为 0 时返回 409，防止并发重复审核。

- [ ] **Step 2: Run the test and verify expected failures**

Run: `./mvnw -Dtest=ProjectTeamServiceReviewTest test`

Expected: FAIL because current `reviewSubmission` accepts old and completed submissions.

- [ ] **Step 3: Implement minimal review guards**

在更新前校验最新提交 ID 和当前状态。教师使用导师归属判断，管理员使用租户范围，队长沿用既有权限。更新 SQL 收紧为：

```sql
UPDATE project_task_submission
SET status = ?, reviewer_id = ?, review_comment = ?, reviewed_at = NOW()
WHERE id = ? AND status IN ('PENDING_REVIEW', 'REVIEWING')
```

受影响行数不是 1 时返回 409；只有成功后才更新任务、能力画像和项目阶段。

- [ ] **Step 4: Run all ProjectTeam focused tests**

Run: `./mvnw -Dtest=ProjectTeamServiceReviewTest,ProjectTeamServiceMembershipTest,ProjectTeamControllerTest,TeacherReviewControllerTest test`

Expected: PASS.

### Task 4: Connect the Teacher Workbench

**Files:**
- Modify: `frontend/teacher/src/api/index.js`
- Modify: `frontend/teacher/src/views/WorkbenchView.vue`

- [ ] **Step 1: Add API functions**

新增：

```js
export async function fetchTeacherReviewQueue() {
  return unwrap(await request.get('/api/teacher/review-queue')) || []
}

export async function fetchTeacherSubmission(submissionId) {
  return unwrap(await request.get(`/api/teacher/submissions/${submissionId}`))
}
```

- [ ] **Step 2: Map real submissions into existing queue items**

真实审核项使用稳定 ID `review-${submissionId}`，保留 `submissionId`、任务、团队、提交人、版本和附件计数。登录后只替换 `type === 'review'` 的演示项，路演、AI 待办和未交演示项保持不变。

- [ ] **Step 3: Load detail on active review change**

增加 `reviewDetail`、`reviewLoading`、`reviewSubmitting`、`reviewError`。选择真实审核项时请求详情；快速切换时以当前 submission ID 校验响应，避免旧请求覆盖新项。

- [ ] **Step 4: Render full review context**

处理台展示正文、附件链接、外部链接、交付要求和历史版本摘要。加载失败保留队列项并提供“重新加载”，演示项继续显示原摘要。

- [ ] **Step 5: Submit real review before removing the item**

“要求重交”映射 `CHANGES_REQUESTED`，“通过并下一条”映射 `APPROVED`。请求成功后调用现有移除和下一条逻辑；请求失败时保留当前项、详情和教师意见，并显示错误。

- [ ] **Step 6: Build the teacher frontend**

Run: `npm run build` in `frontend/teacher`

Expected: Vite build exits 0 with generated assets.

### Task 5: End-to-End Verification

**Files:**
- Update if needed: `frontend/teacher/.gstack/qa-reports/qa-report-teacher-localhost-2026-07-21.md`

- [ ] **Step 1: Run backend regression tests**

Run: `./mvnw test` in `backend`

Expected: PASS. If unrelated existing failures occur, record exact test names and still run the focused suite to prove this change.

- [ ] **Step 2: Run frontend production build again**

Run: `npm run build` in `frontend/teacher`

Expected: PASS.

- [ ] **Step 3: Browser-verify demo mode**

Without token, open `/`, confirm the mock review flow still removes the current item and advances to the next item with zero console errors.

- [ ] **Step 4: Browser-verify authenticated behavior where credentials/data are available**

Confirm loading, empty, detail, approve/change-request, error preservation, desktop and 375px layout. If no real teacher credentials or pending submission data are available, document that limitation rather than fabricating success.

- [ ] **Step 5: Self-review changed files**

Check diff-equivalent file reads for missed imports, inconsistent response field names, SQL tenant scope, old-version protection, stale asynchronous detail responses, and accidental changes to unrelated worktree files.

## Plan Self-Review

- Spec coverage: queue scope, admin scope, tenant isolation, latest-version-only queue, read-only history, review guards, mock fallback, error preservation and verification all map to explicit tasks.
- Placeholder scan: no deferred implementation items; browser authenticated verification explicitly handles unavailable credentials as an environmental limitation.
- Type consistency: controller and frontend use `submissionId`; service list rows retain existing `id` for payload attachment and expose `submissionId` for teacher API consumers.
