# P12 AI Scoring Hardening and E2E Gate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把 P0-P11 已完成的会议评分、上传视频评分、连续评分记忆、报告页和评审团复核升级为上线前可自动验收的硬门槛，覆盖黑盒泄露、一致性、权限隔离、失败可解释和前端全链路冒烟。

**Architecture:** 本阶段不重做评分业务逻辑，主要新增测试、少量访问控制服务、前端自动化脚本和验收文档。后端以 `AiScoreAccessControlService` 统一保护 session/report/media/evidence/jury 读取与操作，现有 controller 在进入 service 前校验 userId/team/project 访问权；前端用 Playwright 做关键页面冒烟和 Network 脱敏检查。所有用户端 API 继续返回 DTO，不暴露规则版本、hash、prompt、权重、完整规则阈值或内部 schema。

**Tech Stack:** Spring Boot 3 + MyBatis Plus + JdbcTemplate + MockMvc + JUnit 5 + Mockito + H2/MySQL mode；Vue 3 + Vite + Element Plus；Playwright for frontend smoke tests；existing `scoring_session` / `ai_score_media_asset` / structured report / jury tables.

---

## Scope

P12 是上线前硬化和验收层，不新增真实 ASR/OCR/LLM 能力，不改变评分算法，不改变 42 赛道规则文件结构。它要把以下风险变成测试：

- 普通用户接口泄露规则内部字段。
- 同一输入重复评分得到不同 fingerprint 或绕过缓存。
- 上传视频无 `meetingId` 时报告页或评审团失败。
- 上一轮扣分追回可以突破上轮扣分或本轮 evidence cap。
- 证据锚点全部落到默认片段，导致报告不可复核。
- 评分/证据/评审团失败后 session 状态不可解释。
- A 团队用户读取 B 团队 session/report/media/evidence/jury。
- 前端报告页仍展示规则版本/hash/prompt/权重。

## File Structure

**Backend create:**

- `backend/src/main/java/com/orep/backend/service/AiScoreAccessControlService.java`  
  One responsibility: decide whether current user can access a scoring session and related assets.
- `backend/src/test/java/com/orep/backend/service/AiScoreAccessControlServiceTest.java`  
  Unit tests for owner/team/admin access and cross-team denial.
- `backend/src/test/java/com/orep/backend/controller/AiScoreUserApiHardeningTest.java`  
  MockMvc response redaction sweep for session/report/evidence/jury/upload endpoints.
- `backend/src/test/java/com/orep/backend/service/AiScoreFingerprintCacheHardeningTest.java`  
  Fingerprint and cache invariants not already covered by P3.
- `backend/src/test/java/com/orep/backend/service/AiScoreReportSessionNativeHardeningTest.java`  
  Uploaded-video/no-meeting report and evidence anchor correlation tests.
- `backend/src/test/java/com/orep/backend/service/AiScoreFailureStateHardeningTest.java`  
  Failure-state tests for upload, evidence preparation, structured result, and jury failure tolerance.

**Backend modify:**

- `backend/src/main/java/com/orep/backend/controller/AiScoreController.java`  
  Add access checks to session status/start/cancel/restart/latest/report/evidence/structured endpoints.
- `backend/src/main/java/com/orep/backend/controller/AiScoreUploadController.java`  
  Add access checks before upload-session accepts project/team target.
- `backend/src/main/java/com/orep/backend/controller/AiJuryReviewController.java`  
  Add access checks before session-native jury start/result/report.
- `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java`  
  Expose safe `findSessionForAccess(sessionId)` or `requireSessionForAccess(sessionId)` without leaking internals.
- `backend/src/test/java/com/orep/backend/controller/AiScoreSessionControllerTest.java`  
  Update controller constructor and add forbidden-access assertions.
- `backend/src/test/java/com/orep/backend/controller/AiJuryReviewControllerTest.java`  
  Add forbidden-access assertions.
- `backend/src/test/java/com/orep/backend/controller/AiScoreUploadControllerTest.java`  
  Add upload access assertion.
- `backend/src/test/java/com/orep/backend/controller/AiScoreResponseRedactionTest.java`  
  Reuse hardening redaction helper or keep as focused regression.

**Frontend create:**

- `frontend/user/tests/ai-score-hardening.spec.js`  
  Playwright smoke tests for report page, upload page, jury panel, and forbidden-field Network scan.
- `frontend/user/playwright.config.js`  
  Minimal config if the project does not already have one.

**Frontend modify:**

- `frontend/user/package.json`  
  Add `test:e2e:ai-score` script.
- `frontend/user/src/views/AiScoreResult.vue`  
  Only if Playwright reveals a visible internal-field leak or missing no-meeting fallback.
- `frontend/user/src/components/ai-score/JuryPerspectivePanel.vue`  
  Only if Playwright reveals empty/loading/error state cannot be asserted.

**Docs modify:**

- `docs/superpowers/plans/2026-06-23-ai-scoring-meeting-room-optimization.md`  
  Update P12 execution board and append completion record.
- `docs/superpowers/checklists/p12-ai-scoring-e2e-checklist.md`  
  Manual QA checklist with exact page paths, expected UI, and Network assertions.

---

## Task 1: Backend Access Control Service ✅

**Files:**

- Create: `backend/src/main/java/com/orep/backend/service/AiScoreAccessControlService.java`
- Test: `backend/src/test/java/com/orep/backend/service/AiScoreAccessControlServiceTest.java`

- [x] **Step 1: Write failing access-control tests**

Create `backend/src/test/java/com/orep/backend/service/AiScoreAccessControlServiceTest.java`:

```java
package com.orep.backend.service;

import com.orep.backend.entity.AiScoringSession;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.server.ResponseStatusException;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class AiScoreAccessControlServiceTest {

    @Test
    void creatorCanAccessOwnSessionEvenWhenTeamIsMissing() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        AiScoreAccessControlService service = new AiScoreAccessControlService(jdbc);
        AiScoringSession session = new AiScoringSession();
        session.setId(11L);
        session.setCreatedBy(7L);
        session.setTeamId(null);

        assertThatCode(() -> service.assertSessionAccess(session, 1L, 7L, "STUDENT"))
                .doesNotThrowAnyException();
    }

    @Test
    void teacherCanAccessSessionInSameTenant() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        when(jdbc.queryForObject(any(String.class), eq(Integer.class), eq(3L), eq(9L))).thenReturn(1);
        AiScoreAccessControlService service = new AiScoreAccessControlService(jdbc);
        AiScoringSession session = new AiScoringSession();
        session.setId(11L);
        session.setTeamId(9L);

        assertThatCode(() -> service.assertSessionAccess(session, 3L, 77L, "TEACHER"))
                .doesNotThrowAnyException();
    }

    @Test
    void teamMemberCanAccessOwnTeamSession() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        when(jdbc.queryForObject(any(String.class), eq(Integer.class), eq(3L), eq(9L), eq(7L))).thenReturn(1);
        AiScoreAccessControlService service = new AiScoreAccessControlService(jdbc);
        AiScoringSession session = new AiScoringSession();
        session.setId(11L);
        session.setTeamId(9L);

        assertThatCode(() -> service.assertSessionAccess(session, 3L, 7L, "STUDENT"))
                .doesNotThrowAnyException();
    }

    @Test
    void crossTeamStudentIsRejected() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        when(jdbc.queryForObject(any(String.class), eq(Integer.class), eq(3L), eq(9L), eq(8L))).thenReturn(0);
        AiScoreAccessControlService service = new AiScoreAccessControlService(jdbc);
        AiScoringSession session = new AiScoringSession();
        session.setId(11L);
        session.setTeamId(9L);
        session.setCreatedBy(7L);

        assertThatThrownBy(() -> service.assertSessionAccess(session, 3L, 8L, "STUDENT"))
                .isInstanceOf(ResponseStatusException.class)
                .hasMessageContaining("无权访问该评分会话");
    }
}
```

- [x] **Step 2: Run test to verify it fails**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreAccessControlServiceTest
```

Expected: FAIL with `cannot find symbol class AiScoreAccessControlService`.

- [x] **Step 3: Implement access control service**

Create `backend/src/main/java/com/orep/backend/service/AiScoreAccessControlService.java`:

```java
package com.orep.backend.service;

import com.orep.backend.entity.AiScoringSession;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

import java.util.Locale;
import java.util.Objects;
import java.util.Set;

@Service
public class AiScoreAccessControlService {
    private static final Set<String> TEACHER_SCOPE_ROLES = Set.of("TEACHER", "ADMIN", "SUPER_ADMIN");

    private final JdbcTemplate jdbc;

    public AiScoreAccessControlService(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public void assertSessionAccess(AiScoringSession session, Long tenantId, Long userId, String role) {
        if (session == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "评分会话不存在");
        }
        if (userId == null) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "请先登录");
        }
        if (Objects.equals(session.getCreatedBy(), userId)) {
            return;
        }
        Long teamId = session.getTeamId();
        if (teamId == null) {
            throw new ResponseStatusException(HttpStatus.FORBIDDEN, "无权访问该评分会话");
        }
        if (hasTeacherScope(role) && teamBelongsToTenant(tenantId, teamId)) {
            return;
        }
        if (teamMemberInTenant(tenantId, teamId, userId)) {
            return;
        }
        throw new ResponseStatusException(HttpStatus.FORBIDDEN, "无权访问该评分会话");
    }

    public boolean hasTeacherScope(String role) {
        if (role == null) return false;
        return TEACHER_SCOPE_ROLES.contains(role.trim().toUpperCase(Locale.ROOT));
    }

    private boolean teamBelongsToTenant(Long tenantId, Long teamId) {
        if (tenantId == null || teamId == null) return false;
        Integer count = jdbc.queryForObject(
                "SELECT COUNT(*) FROM project_team WHERE tenant_id = ? AND id = ?",
                Integer.class,
                tenantId,
                teamId
        );
        return count != null && count > 0;
    }

    private boolean teamMemberInTenant(Long tenantId, Long teamId, Long userId) {
        if (tenantId == null || teamId == null || userId == null) return false;
        Integer count = jdbc.queryForObject("""
                SELECT COUNT(*)
                FROM project_team t
                JOIN project_team_member m ON m.team_id = t.id
                WHERE t.tenant_id = ? AND t.id = ? AND m.user_id = ?
                """, Integer.class, tenantId, teamId, userId);
        return count != null && count > 0;
    }
}
```

- [x] **Step 4: Run access-control tests**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreAccessControlServiceTest
```

Expected: PASS, 4 tests, 0 failures.

---

## Task 2: Wire Access Control into Session, Report, Evidence, Upload, and Jury APIs ✅

**Files:**

- Modify: `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java`
- Modify: `backend/src/main/java/com/orep/backend/controller/AiScoreController.java`
- Modify: `backend/src/main/java/com/orep/backend/controller/AiScoreUploadController.java`
- Modify: `backend/src/main/java/com/orep/backend/controller/AiJuryReviewController.java`
- Test: `backend/src/test/java/com/orep/backend/controller/AiScoreSessionControllerTest.java`
- Test: `backend/src/test/java/com/orep/backend/controller/AiScoreUploadControllerTest.java`
- Test: `backend/src/test/java/com/orep/backend/controller/AiJuryReviewControllerTest.java`

- [x] **Step 1: Add failing controller tests for forbidden session access**

Append to `backend/src/test/java/com/orep/backend/controller/AiScoreSessionControllerTest.java`:

```java
@Test
void statusRejectsCrossTeamUserBeforeReturningSession() throws Exception {
    AiScoringSessionService sessionService = mock(AiScoringSessionService.class);
    AiScoreAccessControlService access = mock(AiScoreAccessControlService.class);
    AiScoringSession session = new AiScoringSession();
    session.setId(101L);
    session.setTeamId(9L);
    when(sessionService.requireSessionForAccess(101L)).thenReturn(session);
    doThrow(new org.springframework.web.server.ResponseStatusException(
            org.springframework.http.HttpStatus.FORBIDDEN, "无权访问该评分会话"))
            .when(access).assertSessionAccess(eq(session), eq(3L), eq(8L), eq("STUDENT"));

    MockMvc mvc = standaloneSetup(new AiScoreController(
            mock(AiScoreReportMapper.class),
            mock(ProjectTeamService.class),
            sessionService,
            mock(AiScoreEvidenceBundleService.class),
            mock(AiScoreStructuredResultService.class),
            access)).build();

    mvc.perform(get("/api/ai-score/sessions/101/status")
                    .requestAttr("tenantId", 3L)
                    .requestAttr("userId", 8L)
                    .requestAttr("role", "STUDENT"))
            .andExpect(status().isForbidden());
}
```

If this test file does not currently import these classes, add:

```java
import com.orep.backend.entity.AiScoringSession;
import com.orep.backend.mapper.AiScoreReportMapper;
import com.orep.backend.service.AiScoreAccessControlService;
import com.orep.backend.service.AiScoreEvidenceBundleService;
import com.orep.backend.service.AiScoreStructuredResultService;
import com.orep.backend.service.ProjectTeamService;

import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
```

- [x] **Step 2: Run the controller test and verify it fails**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreSessionControllerTest#statusRejectsCrossTeamUserBeforeReturningSession
```

Expected: FAIL because `AiScoreController` has no constructor parameter for `AiScoreAccessControlService` and `AiScoringSessionService` has no `requireSessionForAccess`.

- [x] **Step 3: Expose session lookup for access control**

In `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java`, add this public method near `getStatus`:

```java
public AiScoringSession requireSessionForAccess(Long sessionId) {
    return requireSession(sessionId);
}
```

Do not expose this object from controller responses. It is only for access control.

- [x] **Step 4: Add access-control constructor dependency to `AiScoreController`**

Modify `backend/src/main/java/com/orep/backend/controller/AiScoreController.java`:

```java
private final AiScoreAccessControlService accessControlService;

public AiScoreController(AiScoreReportMapper reportMapper,
                         ProjectTeamService projectTeamService,
                         AiScoringSessionService scoringSessionService,
                         AiScoreEvidenceBundleService evidenceBundleService,
                         AiScoreStructuredResultService structuredResultService,
                         AiScoreAccessControlService accessControlService) {
    this.reportMapper = reportMapper;
    this.projectTeamService = projectTeamService;
    this.scoringSessionService = scoringSessionService;
    this.evidenceBundleService = evidenceBundleService;
    this.structuredResultService = structuredResultService;
    this.accessControlService = accessControlService;
}
```

Add helper methods near `markFailedQuietly`:

```java
private void assertSessionAccess(Long sessionId, HttpServletRequest request) {
    accessControlService.assertSessionAccess(
            scoringSessionService.requireSessionForAccess(sessionId),
            attrLong(request, "tenantId"),
            attrLong(request, "userId"),
            attrString(request, "role")
    );
}

private Long attrLong(HttpServletRequest request, String key) {
    Object value = request.getAttribute(key);
    return value instanceof Number number ? number.longValue() : null;
}

private String attrString(HttpServletRequest request, String key) {
    Object value = request.getAttribute(key);
    return value == null ? null : String.valueOf(value);
}
```

Change session-specific endpoints to accept `HttpServletRequest` and call `assertSessionAccess(sessionId, request)` before returning data or mutating state:

```java
@GetMapping("/sessions/{sessionId}/status")
public Result<AiScoringSessionUserResponse> sessionStatus(@PathVariable("sessionId") Long sessionId,
                                                          HttpServletRequest request) {
    try {
        assertSessionAccess(sessionId, request);
        return Result.success(scoringSessionService.getStatus(sessionId));
    } catch (IllegalStateException e) {
        return Result.error(404, e.getMessage());
    }
}
```

Apply the same pattern to:

- `startSession`
- `cancelSession`
- `restartSession`
- `prepareEvidence`
- `evidenceBundle`
- `applyStructuredResult`
- `reportBySession`

Do not add this check to legacy `/status/{meetingId}` in this task; legacy direct entity response is handled in Task 3 hardening/redaction or deprecated in Task 8.

- [x] **Step 5: Add access-control dependency to upload and jury controllers**

In `backend/src/main/java/com/orep/backend/controller/AiScoreUploadController.java`, add:

```java
private final AiScoreAccessControlService accessControlService;
```

Constructor should become:

```java
public AiScoreUploadController(AiScoringSessionService sessionService,
                               AiScoreMediaAssetService mediaAssetService,
                               AiScoreAccessControlService accessControlService) {
    this.sessionService = sessionService;
    this.mediaAssetService = mediaAssetService;
    this.accessControlService = accessControlService;
}
```

After the upload controller calls `sessionService.createSession(request, userId)` and receives a session response, call access control on the newly created session before saving files:

```java
accessControlService.assertSessionAccess(
        sessionService.requireSessionForAccess(session.getSessionId()),
        attrLong(request, "tenantId"),
        attrLong(request, "userId"),
        attrString(request, "role")
);
```

If `AiScoreUploadController` does not currently accept `HttpServletRequest`, add it to the endpoint method arguments.

In `backend/src/main/java/com/orep/backend/controller/AiJuryReviewController.java`, add constructor dependency `AiScoringSessionService` and `AiScoreAccessControlService`, then guard session-native jury endpoints:

```java
private void assertSessionAccess(Long sessionId, HttpServletRequest request) {
    accessControlService.assertSessionAccess(
            scoringSessionService.requireSessionForAccess(sessionId),
            attrLong(request, "tenantId"),
            attrLong(request, "userId"),
            attrString(request, "role")
    );
}
```

Call it in:

- `startBySession`
- `resultBySession`
- `reportBySession`

Leave legacy meeting endpoints unchanged for compatibility in this task; Task 8 documents deprecation and P12 manual risk.

- [x] **Step 6: Run affected controller tests**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreSessionControllerTest,AiScoreUploadControllerTest,AiJuryReviewControllerTest,AiScoreResponseRedactionTest
```

Expected: PASS. If constructor updates break existing tests, inject `mock(AiScoreAccessControlService.class)` and stub no behavior.

---

## Task 3: User API Redaction Sweep ✅

**Files:**

- Create: `backend/src/test/java/com/orep/backend/controller/AiScoreUserApiHardeningTest.java`
- Modify: `backend/src/main/java/com/orep/backend/controller/AiScoreController.java` only if test finds direct entity leak in a user endpoint.

- [x] **Step 1: Write failing redaction sweep test**

Create `backend/src/test/java/com/orep/backend/controller/AiScoreUserApiHardeningTest.java`:

```java
package com.orep.backend.controller;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;

import java.util.Iterator;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

class AiScoreUserApiHardeningTest {
    private static final ObjectMapper OBJECT_MAPPER = new ObjectMapper();
    private static final String[] FORBIDDEN_NORMALIZED_FIELD_NAMES = {
            "rubrichash",
            "rubricpath",
            "internalversion",
            "rubricinternalversion",
            "prompt",
            "promptversion",
            "weight",
            "ruleformula",
            "scorethreshold",
            "rulesourcetext",
            "ruleengineversion",
            "evidenceschemahash",
            "evidenceschemaversion",
            "promptmodifier",
            "scoringbias",
            "rubricfocus",
            "standardversion",
            "personapoolversion",
            "tokensjson"
    };

    @Test
    void recursiveFieldScannerCatchesForbiddenNamesEvenWhenCasingChanges() throws Exception {
        String json = """
                {
                  "data": {
                    "sessionId": 1,
                    "safe": {"trackName": "餐饮赛道"},
                    "nested": [{"rubric_hash": "secret"}]
                  }
                }
                """;

        assertThat(hasForbiddenField(OBJECT_MAPPER.readTree(json))).isTrue();
    }

    @Test
    void recursiveFieldScannerAllowsPromptAndWeightAsOrdinaryUserTextValues() throws Exception {
        String json = """
                {
                  "data": {
                    "sessionId": 1,
                    "summary": "报告文本里可以讨论 prompt 或 weight 这两个普通词，但不能作为字段名"
                  }
                }
                """;

        assertThat(hasForbiddenField(OBJECT_MAPPER.readTree(json))).isFalse();
    }

    static void assertNoForbiddenFields(String json) throws Exception {
        JsonNode node = OBJECT_MAPPER.readTree(json);
        assertThat(hasForbiddenField(node))
                .describedAs("user API response must not contain forbidden internal field names: %s", json)
                .isFalse();
    }

    private static boolean hasForbiddenField(JsonNode node) {
        if (node == null) return false;
        if (node.isObject()) {
            Iterator<Map.Entry<String, JsonNode>> fields = node.fields();
            while (fields.hasNext()) {
                Map.Entry<String, JsonNode> field = fields.next();
                String normalized = field.getKey().replace("_", "").replace("-", "").toLowerCase();
                for (String forbidden : FORBIDDEN_NORMALIZED_FIELD_NAMES) {
                    if (forbidden.equals(normalized)) {
                        return true;
                    }
                }
                if (hasForbiddenField(field.getValue())) {
                    return true;
                }
            }
        }
        if (node.isArray()) {
            for (JsonNode child : node) {
                if (hasForbiddenField(child)) {
                    return true;
                }
            }
        }
        return false;
    }
}
```

- [x] **Step 2: Run scanner tests**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreUserApiHardeningTest
```

Expected: PASS, 2 tests, 0 failures. This validates the scanner before using it in endpoint tests.

- [x] **Step 3: Add endpoint JSON sweep to existing controller redaction tests**

In `backend/src/test/java/com/orep/backend/controller/AiScoreResponseRedactionTest.java`, import and call:

```java
AiScoreUserApiHardeningTest.assertNoForbiddenFields(createJson);
AiScoreUserApiHardeningTest.assertNoForbiddenFields(statusJson);
AiScoreUserApiHardeningTest.assertNoForbiddenFields(responseJson);
```

Keep the existing secret-value assertions. The scanner catches field names; the old assertions catch known secret values.

- [x] **Step 4: Run redaction tests**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreUserApiHardeningTest,AiScoreResponseRedactionTest,AiScoringSessionRedactionMappingTest,AiJuryReviewControllerTest
```

Expected: PASS. If any legacy user endpoint serializes `AiScoreReport` entity directly, either route it through `AiScoreReportUserResponse` or mark it as legacy-only and add a follow-up deprecation note in Task 8.

---

## Task 4: Fingerprint and Cache Consistency Hardening ✅

**Files:**

- Create: `backend/src/test/java/com/orep/backend/service/AiScoreFingerprintCacheHardeningTest.java`
- Modify: `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java` only if cache lookup or fingerprint input misses required fields.

- [x] **Step 1: Write failing fingerprint/cache hardening tests**

Create `backend/src/test/java/com/orep/backend/service/AiScoreFingerprintCacheHardeningTest.java`:

```java
package com.orep.backend.service;

import com.orep.backend.dto.AiScoringSessionCreateRequest;
import com.orep.backend.dto.ResolvedRubric;
import com.orep.backend.entity.AiScoringSession;
import com.orep.backend.mapper.AiScoreReportMapper;
import com.orep.backend.mapper.AiScoringSessionMapper;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class AiScoreFingerprintCacheHardeningTest {

    @Test
    void sameMeetingInputHitsCompletedCacheAndDoesNotCreateNewSession() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        RubricResolverService resolver = mock(RubricResolverService.class);
        when(resolver.resolve("track-food", "餐饮赛道")).thenReturn(rubric());
        AiScoringSession cached = completedSession(222L);
        when(sessionMapper.selectOne(any())).thenReturn(cached);
        AiScoringSessionService service = new AiScoringSessionService(
                sessionMapper,
                mock(AiScoreReportMapper.class),
                resolver,
                new ScoringFingerprintService()
        );

        var response = service.createSession(request("meeting_recording"), 7L);

        assertThat(response.getSessionId()).isEqualTo(222L);
        assertThat(response.getCached()).isTrue();
        assertThat(response.getMessage()).contains("历史评分输入完全一致");
        verify(sessionMapper, never()).insert(any(AiScoringSession.class));
    }

    @Test
    void uploadedVideoAlwaysCreatesNewSessionUntilMediaHashesJoinFingerprint() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        RubricResolverService resolver = mock(RubricResolverService.class);
        when(resolver.resolve("track-food", "餐饮赛道")).thenReturn(rubric());
        doAnswer(invocation -> {
            AiScoringSession session = invocation.getArgument(0);
            session.setId(333L);
            return 1;
        }).when(sessionMapper).insert(any(AiScoringSession.class));
        AiScoringSessionService service = new AiScoringSessionService(
                sessionMapper,
                mock(AiScoreReportMapper.class),
                resolver,
                new ScoringFingerprintService()
        );

        var response = service.createSession(request("uploaded_video"), 7L);

        assertThat(response.getSessionId()).isEqualTo(333L);
        assertThat(response.getCached()).isFalse();
        verify(sessionMapper, never()).selectOne(any());
        verify(sessionMapper).insert(any(AiScoringSession.class));
    }

    private AiScoringSessionCreateRequest request(String sourceType) {
        AiScoringSessionCreateRequest request = new AiScoringSessionCreateRequest();
        request.setSourceType(sourceType);
        request.setMeetingId(12L);
        request.setProjectId(3L);
        request.setTeamId(9L);
        request.setTrackId("track-food");
        request.setTrackName("餐饮赛道");
        request.setUseHistoryMemory(true);
        return request;
    }

    private AiScoringSession completedSession(Long id) {
        AiScoringSession session = new AiScoringSession();
        session.setId(id);
        session.setSessionNo("SC-20260624-000222");
        session.setStatus("completed");
        session.setCurrentStage("completed");
        session.setTrackName("餐饮赛道");
        session.setSourceType("meeting_recording");
        session.setUseHistoryMemory(true);
        session.setJuryEnabled(false);
        return session;
    }

    private ResolvedRubric rubric() {
        ResolvedRubric rubric = new ResolvedRubric();
        rubric.setTrackId("track-food");
        rubric.setTrackName("餐饮赛道");
        rubric.setRubricId("rubric-food-v12");
        rubric.setRubricInternalVersion("internal-v12");
        rubric.setRubricHash("secret-food-hash");
        rubric.setEvidenceSchemaId(44L);
        rubric.setEvidenceSchemaVersion("schema-food-v12");
        rubric.setEvidenceSchemaHash("schema-food-hash");
        return rubric;
    }
}
```

- [x] **Step 2: Run hardening tests**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreFingerprintCacheHardeningTest,ScoringFingerprintServiceTest,AiScoringSessionServiceTest
```

Expected: PASS. If uploaded-video cache currently hits completed sessions, keep the current P5 decision: uploaded videos create a new session until media hash is part of fingerprint.

---

## Task 5: Session-Native Uploaded Video Report and Evidence Anchor Correlation ✅

**Files:**

- Create: `backend/src/test/java/com/orep/backend/service/AiScoreReportSessionNativeHardeningTest.java`
- Modify: `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java` only if uploaded video reports still require `meetingId`.

- [x] **Step 1: Write failing session-native report test**

Create `backend/src/test/java/com/orep/backend/service/AiScoreReportSessionNativeHardeningTest.java`:

```java
package com.orep.backend.service;

import com.orep.backend.entity.AiScoreDeduction;
import com.orep.backend.entity.AiScoreEvidenceAnchor;
import com.orep.backend.entity.AiScoreReport;
import com.orep.backend.entity.AiScoringSession;
import com.orep.backend.mapper.AiScoreDeductionMapper;
import com.orep.backend.mapper.AiScoreEvidenceAnchorMapper;
import com.orep.backend.mapper.AiScoreObservationMapper;
import com.orep.backend.mapper.AiScoreReportMapper;
import com.orep.backend.mapper.AiScoringSessionMapper;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class AiScoreReportSessionNativeHardeningTest {

    @Test
    void uploadedVideoReportBySessionDoesNotRequireMeetingId() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
        AiScoreObservationMapper observationMapper = mock(AiScoreObservationMapper.class);
        AiScoreDeductionMapper deductionMapper = mock(AiScoreDeductionMapper.class);
        AiScoreEvidenceAnchorMapper anchorMapper = mock(AiScoreEvidenceAnchorMapper.class);

        AiScoringSession session = new AiScoringSession();
        session.setId(88L);
        session.setReportId(55L);
        session.setMeetingId(null);
        session.setSessionNo("SC-20260624-000088");
        session.setTrackName("医学技术赛道");
        session.setSourceType("uploaded_video");
        when(sessionMapper.selectById(88L)).thenReturn(session);

        AiScoreReport report = new AiScoreReport();
        report.setId(55L);
        report.setMeetingId(-88L);
        report.setOverallScore(new BigDecimal("78.50"));
        report.setStatus("completed");
        when(reportMapper.selectById(55L)).thenReturn(report);
        when(observationMapper.selectList(any())).thenReturn(List.of());
        when(deductionMapper.selectList(any())).thenReturn(List.of());
        when(anchorMapper.selectList(any())).thenReturn(List.of());

        AiScoringSessionService service = new AiScoringSessionService(
                sessionMapper,
                reportMapper,
                observationMapper,
                deductionMapper,
                anchorMapper,
                mock(RubricResolverService.class),
                new ScoringFingerprintService()
        );

        var response = service.reportBySession(88L);

        assertThat(response.getSessionId()).isEqualTo(88L);
        assertThat(response.getMeetingId()).isEqualTo(-88L);
        assertThat(response.getSourceType()).isEqualTo("uploaded_video");
        assertThat(response.getScoringConsistencyNo()).isEqualTo("SC-20260624-000088");
    }

    @Test
    void structuredDeductionsKeepDistinctEvidenceAnchors() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoreReportMapper reportMapper = mock(AiScoreReportMapper.class);
        AiScoreObservationMapper observationMapper = mock(AiScoreObservationMapper.class);
        AiScoreDeductionMapper deductionMapper = mock(AiScoreDeductionMapper.class);
        AiScoreEvidenceAnchorMapper anchorMapper = mock(AiScoreEvidenceAnchorMapper.class);

        AiScoringSession session = new AiScoringSession();
        session.setId(88L);
        session.setReportId(55L);
        session.setSessionNo("SC-20260624-000088");
        when(sessionMapper.selectById(88L)).thenReturn(session);

        AiScoreReport report = new AiScoreReport();
        report.setId(55L);
        report.setMeetingId(-88L);
        report.setOverallScore(new BigDecimal("78.50"));
        report.setStatus("completed");
        when(reportMapper.selectById(55L)).thenReturn(report);
        when(observationMapper.selectList(any())).thenReturn(List.of());

        AiScoreDeduction first = deduction("D1", "技术演示中断", "A1");
        AiScoreDeduction second = deduction("D2", "商业证据不足", "A2");
        when(deductionMapper.selectList(any())).thenReturn(List.of(first, second));
        when(anchorMapper.selectList(any())).thenReturn(List.of(
                anchor("A1", "00:02.0-00:05.0", "演示页面报错后切换到截图"),
                anchor("A2", "00:20.0-00:26.0", "只口头说明客户，没有订单或访谈截图")
        ));

        AiScoringSessionService service = new AiScoringSessionService(
                sessionMapper,
                reportMapper,
                observationMapper,
                deductionMapper,
                anchorMapper,
                mock(RubricResolverService.class),
                new ScoringFingerprintService()
        );

        var response = service.reportBySession(88L);

        assertThat(response.getEvidenceAnchors()).hasSize(2);
        assertThat(response.getEvidenceAnchors()).extracting("sourceRef")
                .containsExactly("A1", "A2");
        assertThat(response.getEvidenceAnchors()).extracting("text")
                .doesNotContain("大家好。");
    }

    private AiScoreDeduction deduction(String id, String reason, String evidenceRef) {
        AiScoreDeduction deduction = new AiScoreDeduction();
        deduction.setDeductionId(id);
        deduction.setDimensionName("综合");
        deduction.setReason(reason);
        deduction.setEvidenceAnchorId(evidenceRef);
        deduction.setDeductedPoints(new BigDecimal("3.00"));
        deduction.setMaxRecoverablePoints(new BigDecimal("3.00"));
        return deduction;
    }

    private AiScoreEvidenceAnchor anchor(String sourceRef, String timeRange, String text) {
        AiScoreEvidenceAnchor anchor = new AiScoreEvidenceAnchor();
        anchor.setSourceRef(sourceRef);
        anchor.setSourceType("transcript");
        anchor.setTimeRange(timeRange);
        anchor.setText(text);
        anchor.setConfidence(new BigDecimal("0.80"));
        return anchor;
    }
}
```

- [x] **Step 2: Run session-native report hardening tests**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreReportSessionNativeHardeningTest,AiScoringSessionReportDetailTest
```

Expected: PASS. If it fails because `toReportResponse` still assumes meeting report only, fix `reportBySession` so `session.reportId` is authoritative.

---

## Task 6: Recovery Cap and New-Issue Isolation ✅

**Files:**

- Modify: `backend/src/test/java/com/orep/backend/service/AiScoreRecoveryMemoryServiceTest.java`
- Modify: `backend/src/test/java/com/orep/backend/service/AiScoreStructuredResultServiceTest.java`
- Modify: `backend/src/main/java/com/orep/backend/service/AiScoreRecoveryMemoryService.java` only if caps fail.

- [x] **Step 1: Add recovery cap regression test**

Append to `backend/src/test/java/com/orep/backend/service/AiScoreRecoveryMemoryServiceTest.java`:

```java
@Test
void buildRecoveryRowsCannotRecoverMoreThanPreviousMaxRecoverablePoints() {
    LocalDateTime now = LocalDateTime.of(2026, 6, 24, 10, 0);
    AiScoreRecoveryInput recovery = recovery("deduction-1", "fixed", "10", "4");

    List<AiScoreDeduction> rows = service.buildRecoveryRows(
            12L,
            88L,
            List.of(recovery),
            List.of(claim("deduction-1", "fixed", "10", 10L)),
            now
    );

    assertEquals(1, rows.size());
    AiScoreDeduction row = rows.getFirst();
    assertScore("4", row.getRecoveredPoints());
    assertScore("0", row.getDeductedPoints());
    assertEquals("deduction-1", row.getRecoverySourceDeductionId());
    assertEquals("[10]", row.getEvidenceAnchorIdsJson());
}
```

- [x] **Step 2: Add new issue isolation regression**

Append to `backend/src/test/java/com/orep/backend/service/AiScoreStructuredResultServiceTest.java`:

```java
@Test
void recoveryRowsDoNotRemoveCurrentNewDeductions() {
    AiScoreRecoveryMemoryService realRecoveryMemoryService = new AiScoreRecoveryMemoryService(
            sessionMapper,
            deductionMapper
    );
    AiScoreStructuredResultService serviceWithRealRecovery = new AiScoreStructuredResultService(
            sessionMapper,
            evidenceAnchorMapper,
            reportMapper,
            observationMapper,
            deductionMapper,
            validator,
            ruleEngine,
            realRecoveryMemoryService,
            new ObjectMapper()
    );
    AiScoringSession session = session(123L, 456L, null);
    session.setProjectId(1L);
    session.setTeamId(2L);
    session.setTrackId("track-a");
    session.setUseHistoryMemory(true);
    AiScoringSession previousSession = session(122L, 455L, 887L);
    previousSession.setProjectId(1L);
    previousSession.setTeamId(2L);
    previousSession.setTrackId("track-a");
    previousSession.setStatus("completed");
    AiScoreReport existingReport = new AiScoreReport();
    existingReport.setId(888L);
    existingReport.setMeetingId(456L);
    when(sessionMapper.selectById(123L)).thenReturn(session);
    when(sessionMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(previousSession));
    when(evidenceAnchorMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(anchor(10L), anchor(11L)));
    when(reportMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(existingReport);
    when(deductionMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(previousDeduction(
            "deduction-old",
            "6"
    )));

    AiScoreStructuredResultRequest request = validRequest(123L);
    request.getDeductions().getFirst().setDeductionId("deduction-new");
    request.setRecoveryClaims(List.of(recoveryClaim("deduction-old", "fixed", "6", 11L)));

    serviceWithRealRecovery.applyStructuredResult(123L, request, List.of());

    ArgumentCaptor<AiScoreDeduction> deductionCaptor = ArgumentCaptor.forClass(AiScoreDeduction.class);
    verify(deductionMapper, times(2)).insert(deductionCaptor.capture());
    List<AiScoreDeduction> insertedDeductions = deductionCaptor.getAllValues();
    assertEquals("deduction-new", insertedDeductions.get(0).getDeductionId());
    assertEquals(null, insertedDeductions.get(0).getRecoverySourceDeductionId());
    assertEquals("recovery-deduction-old", insertedDeductions.get(1).getDeductionId());
    assertEquals("deduction-old", insertedDeductions.get(1).getRecoverySourceDeductionId());
    assertScore("6", insertedDeductions.get(1).getRecoveredPoints());
}
```

- [x] **Step 3: Run recovery tests**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreRecoveryMemoryServiceTest,AiScoreStructuredResultServiceTest,AiScoreRuleEngineTest
```

Expected: PASS. If the package-private method is added only for testability, keep it deterministic and free of DB dependencies.

---

## Task 7: Failure State Hardening ✅

**Files:**

- Create: `backend/src/test/java/com/orep/backend/service/AiScoreFailureStateHardeningTest.java`
- Modify: `backend/src/main/java/com/orep/backend/controller/AiScoreController.java` only if evidence failure does not mark session failed.
- Modify: `backend/src/main/java/com/orep/backend/controller/AiScoreUploadController.java` only if upload failure does not mark session failed.

- [x] **Step 1: Write failure state tests**

Create `backend/src/test/java/com/orep/backend/service/AiScoreFailureStateHardeningTest.java`:

```java
package com.orep.backend.service;

import com.orep.backend.entity.AiScoringSession;
import com.orep.backend.mapper.AiScoreReportMapper;
import com.orep.backend.mapper.AiScoringSessionMapper;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class AiScoreFailureStateHardeningTest {

    @Test
    void markFailedStoresExplicitStageAndMessage() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoringSession session = new AiScoringSession();
        session.setId(77L);
        session.setSessionNo("SC-20260624-000077");
        session.setStatus("scoring");
        session.setTrackName("新一代信息技术赛道");
        session.setSourceType("meeting_recording");
        when(sessionMapper.selectById(77L)).thenReturn(session);
        AiScoringSessionService service = new AiScoringSessionService(
                sessionMapper,
                mock(AiScoreReportMapper.class),
                mock(RubricResolverService.class),
                new ScoringFingerprintService()
        );

        var response = service.markFailed(77L, "抽帧服务不可用", "frame_extract_failed");

        assertThat(response.getStatus()).isEqualTo("failed");
        assertThat(response.getCurrentStage()).isEqualTo("frame_extract_failed");
        assertThat(session.getErrorMessage()).isEqualTo("抽帧服务不可用");
        verify(sessionMapper).updateById(any(AiScoringSession.class));
    }
}
```

- [x] **Step 2: Run failure hardening tests**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreFailureStateHardeningTest,AiScoreSessionControllerTest,AiScoreUploadControllerTest,AiScoreEvidenceBundleControllerTest
```

Expected: PASS. If controller tests show unhandled exceptions, convert them to `Result.error` with explicit stage updates.

---

## Task 8: Frontend E2E Smoke and Network Redaction ✅ (spec committed, E2E not run: no dev server)

**Files:**

- Create: `frontend/user/playwright.config.js`
- Create: `frontend/user/tests/ai-score-hardening.spec.js`
- Modify: `frontend/user/package.json`

- [x] **Step 1: Add Playwright config**

Create `frontend/user/playwright.config.js`:

```js
import { defineConfig } from '@playwright/test'

export default defineConfig({
  testDir: './tests',
  timeout: 30_000,
  use: {
    baseURL: process.env.OREP_E2E_BASE_URL || 'http://localhost:5174',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure'
  }
})
```

- [x] **Step 2: Add E2E hardening spec**

Create `frontend/user/tests/ai-score-hardening.spec.js`:

```js
import { test, expect } from '@playwright/test'

const forbidden = [
  'rubric_hash',
  'rubricPath',
  'rubric_path',
  'internal_version',
  'internalVersion',
  'prompt',
  'weight',
  'rule_formula',
  'score_threshold',
  'ruleEngineVersion'
]

function containsForbiddenField(value) {
  if (!value || typeof value !== 'object') return false
  if (Array.isArray(value)) return value.some(containsForbiddenField)
  return Object.entries(value).some(([key, child]) => {
    const normalized = key.replace(/[-_\\s]/g, '').toLowerCase()
    if (forbidden.some(item => normalized === item.replace(/[-_\\s]/g, '').toLowerCase())) return true
    return containsForbiddenField(child)
  })
}

test('AI score report page hides internal rule fields and keeps jury as review layer', async ({ page }) => {
  const apiPayloads = []
  page.on('response', async response => {
    const url = response.url()
    if (!url.includes('/api/ai-score') && !url.includes('/api/ai-jury')) return
    const contentType = response.headers()['content-type'] || ''
    if (!contentType.includes('application/json')) return
    try {
      apiPayloads.push(await response.json())
    } catch {
      // Ignore non-json bodies even if the content type is incorrect.
    }
  })

  await page.goto('/ai-score/report/1')
  await expect(page.getByText(/AI 路演评分分析台|正在载入评分分析台|未找到评分结果/)).toBeVisible()

  const bodyText = await page.locator('body').innerText()
  expect(bodyText).not.toContain('rubric_hash')
  expect(bodyText).not.toContain('internal_version')
  expect(bodyText).not.toContain('规则 hash')
  expect(bodyText).not.toContain('prompt')

  for (const payload of apiPayloads) {
    expect(containsForbiddenField(payload)).toBe(false)
  }
})

test('upload video score page does not expose scoring rule version selector', async ({ page }) => {
  await page.goto('/ai-score-upload')
  const bodyText = await page.locator('body').innerText()

  expect(bodyText).toContain('上传')
  expect(bodyText).not.toContain('评分规则版本')
  expect(bodyText).not.toContain('rubric')
  expect(bodyText).not.toContain('hash')
})
```

- [x] **Step 3: Add npm script**

Modify `frontend/user/package.json`, add under `scripts`:

```json
"test:e2e:ai-score": "playwright test tests/ai-score-hardening.spec.js"
```

If Playwright is not in `devDependencies`, add:

```json
"@playwright/test": "^1.56.0"
```

Do not run `npm install` in the plan step unless package lock update is intended. During execution, if dependency is missing, run:

```bash
cd frontend/user && npm install
```

- [x] **Step 4: Run frontend build and optional E2E** — build PASS, E2E not run (no dev server available)

Run:

```bash
cd frontend/user && npm run build
```

Expected: PASS.

If a local dev server is available, also run:

```bash
cd frontend/user && npm run test:e2e:ai-score
```

Expected: PASS. If backend/dev server is not running, record E2E as "not run: server unavailable" in the P12 completion record and keep the spec committed.

---

## Task 9: Manual QA Checklist Document ✅

**Files:**

- Create: `docs/superpowers/checklists/p12-ai-scoring-e2e-checklist.md`

- [x] **Step 1: Create checklist directory**

Run:

```bash
mkdir -p docs/superpowers/checklists
```

- [x] **Step 2: Create manual checklist**

Create `docs/superpowers/checklists/p12-ai-scoring-e2e-checklist.md`:

```markdown
# P12 AI评分上线前手工验收清单

## 环境

- 日期：
- 验收人：
- 前端地址：
- 后端地址：
- 测试账号 A：
- 测试账号 B：
- 测试项目/团队/赛道：

## 会议评分链路

- [ ] 进入会议室页面，绑定项目、团队、赛道。
- [ ] 点击 AI评分，开始弹窗不出现评分规则版本、规则 hash、prompt、权重。
- [ ] 评分中再次点击 AI评分，出现运行中弹窗，包含查看进度、结束并生成已有证据报告、终止当前评分、重新开始评分、取消。
- [ ] 结束会议后可进入 `/ai-score/report/:sessionId`。
- [ ] 报告页显示评分一致性编号。
- [ ] 报告页显示为什么不是 100、观察点评分、当前扣分项、上轮问题复核、证据锚点。

## 上传视频链路

- [ ] 进入 `/ai-score-upload`。
- [ ] 页面不出现评分规则版本选择。
- [ ] 上传合法视频后创建 session。
- [ ] 无 `meetingId` 仍能进入 `/ai-score/report/:sessionId`。
- [ ] 上传失败时显示明确错误，session 状态为 failed 或可解释失败。

## 多轮复评

- [ ] 第一轮扣分项出现在连续评分记忆。
- [ ] 第二轮修复项只追回对应扣分，不直接冲到 100。
- [ ] 第二轮新增扣分项单独展示。
- [ ] 本轮上限说明能解释“为什么不是 100”。

## 评审团复核

- [ ] 生成 AI评审团复核后，报告页显示“只做复核，不修改基础分”。
- [ ] 评审团意见包含质疑点、表达风险、训练建议、共识问题。
- [ ] 评审团生成失败不影响基础评分报告。
- [ ] 评审团均分或参考分不覆盖基础 `overallScore`。

## 黑盒与权限

- [ ] Chrome Network 搜索 `rubric_hash` 无结果。
- [ ] Chrome Network 搜索 `rubric_path` 无结果。
- [ ] Chrome Network 搜索 `internal_version` 无结果。
- [ ] Chrome Network 搜索 `prompt` 无内部字段结果。
- [ ] Chrome Network 搜索 `weight` 无内部字段结果。
- [ ] A 团队用户不能访问 B 团队 `/api/ai-score/sessions/{sessionId}/status`。
- [ ] A 团队用户不能访问 B 团队 `/api/ai-score/reports/by-session/{sessionId}`。
- [ ] A 团队用户不能访问 B 团队 `/api/ai-score/sessions/{sessionId}/jury/result`。

## 结论

- [ ] 通过，可以进入下一阶段。
- [ ] 不通过，阻断原因：
```

- [x] **Step 3: Verify checklist exists**

Run:

```bash
test -f docs/superpowers/checklists/p12-ai-scoring-e2e-checklist.md && echo "checklist exists"
```

Expected:

```text
checklist exists
```

---

## Task 10: Full Verification and Master Plan Update ✅

**Files:**

- Modify: `docs/superpowers/plans/2026-06-23-ai-scoring-meeting-room-optimization.md`

- [x] **Step 1: Run targeted P12 backend tests**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreAccessControlServiceTest,AiScoreUserApiHardeningTest,AiScoreFingerprintCacheHardeningTest,AiScoreReportSessionNativeHardeningTest,AiScoreFailureStateHardeningTest,AiScoreSessionControllerTest,AiScoreUploadControllerTest,AiJuryReviewControllerTest,AiScoreResponseRedactionTest,AiScoringSessionRedactionMappingTest,AiScoreRecoveryMemoryServiceTest,AiScoreStructuredResultServiceTest
```

Expected: PASS, 0 failures.

- [x] **Step 2: Run full backend tests**

Run:

```bash
cd backend && mvn test
```

Expected: PASS, 0 failures.

- [x] **Step 3: Run frontend build**

Run:

```bash
cd frontend/user && npm run build
```

Expected: PASS.

- [x] **Step 4: Run optional frontend E2E if local servers are available** — not run, no dev server

Run:

```bash
cd frontend/user && npm run test:e2e:ai-score
```

Expected: PASS if frontend/backend test servers are running. If not run, record the exact blocker in the master plan.

- [x] **Step 5: Update master plan P12 row**

In `docs/superpowers/plans/2026-06-23-ai-scoring-meeting-room-optimization.md`, replace the P12 row:

```markdown
| P12 | 已完成 | 黑盒泄露、一致性、权限和全链路专项验收 | 已完成 | `cd backend && mvn test -Dtest=AiScoreAccessControlServiceTest,AiScoreUserApiHardeningTest,AiScoreFingerprintCacheHardeningTest,AiScoreReportSessionNativeHardeningTest,AiScoreFailureStateHardeningTest,AiScoreSessionControllerTest,AiScoreUploadControllerTest,AiJuryReviewControllerTest,AiScoreResponseRedactionTest,AiScoringSessionRedactionMappingTest,AiScoreRecoveryMemoryServiceTest,AiScoreStructuredResultServiceTest` 通过；`cd backend && mvn test` 通过；`cd frontend/user && npm run build` 通过；已新增 P12 手工验收清单和前端 E2E 冒烟脚本 |
```

Append a completion record only after Step 1-4 have been run. Use this exact structure, and copy the actual command strings and test counts from the terminal output:

```markdown
### 本轮完成记录：P12 黑盒泄露、一致性、权限和全链路专项验收

- 修改文件：
  - `backend/src/main/java/com/orep/backend/service/AiScoreAccessControlService.java`
  - `backend/src/main/java/com/orep/backend/controller/AiScoreController.java`
  - `backend/src/main/java/com/orep/backend/controller/AiScoreUploadController.java`
  - `backend/src/main/java/com/orep/backend/controller/AiJuryReviewController.java`
  - `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java`
  - `backend/src/test/java/com/orep/backend/service/AiScoreAccessControlServiceTest.java`
  - `backend/src/test/java/com/orep/backend/controller/AiScoreUserApiHardeningTest.java`
  - `backend/src/test/java/com/orep/backend/service/AiScoreFingerprintCacheHardeningTest.java`
  - `backend/src/test/java/com/orep/backend/service/AiScoreReportSessionNativeHardeningTest.java`
  - `backend/src/test/java/com/orep/backend/service/AiScoreFailureStateHardeningTest.java`
  - `frontend/user/playwright.config.js`
  - `frontend/user/tests/ai-score-hardening.spec.js`
  - `frontend/user/package.json`
  - `docs/superpowers/checklists/p12-ai-scoring-e2e-checklist.md`
- 后端验证：
  - 复制 Step 1 的完整 targeted backend test command；记录 Surefire 的 `Tests run`、`Failures`、`Errors`、`Skipped`。
  - 复制 Step 2 的 `cd backend && mvn test` 命令；记录 Surefire 的 `Tests run`、`Failures`、`Errors`、`Skipped`。
- 前端验证：
  - `cd frontend/user && npm run build` 通过。
  - `cd frontend/user && npm run test:e2e:ai-score` 通过，或记录未运行原因。
- 手工验证：
  - 使用 `docs/superpowers/checklists/p12-ai-scoring-e2e-checklist.md` 执行，填写通过/阻断项。
- 已知边界：
  - P12 不新增真实 ASR/OCR/LLM 能力；真实媒体质量与模型质量仍需生产环境观测。
```

Before finalizing, the completion record must contain real terminal evidence rather than example values.

---

## Self-Review

**Spec coverage:**

- 会议评分链路：Task 8/9 covers frontend smoke and manual checklist.
- 上传视频无 `meetingId`：Task 5 covers session-native report; Task 9 manual checklist covers UI.
- 多轮复评追回：Task 6 covers cap and new issue isolation.
- 黑盒泄露：Task 3 backend scanner and Task 8 Network scan cover field names.
- 指纹一致性和缓存：Task 4 covers completed cache and uploaded-video exception.
- 证据锚点相关性：Task 5 covers non-default distinct anchors.
- 失败恢复：Task 7 covers failed status/stage/message.
- 权限隔离：Task 1/2 implement and wire access control.
- 评审团不改基础分：P11 tests already cover it; Task 9 manual checklist keeps it as release gate.

**Placeholder scan:**

- This plan contains no unresolved placeholder markers.
- No task asks the worker to infer test contents without concrete code.

**Type consistency:**

- `sessionId` is the public route identifier; DB field is `AiScoringSession.id`.
- Access control uses `tenantId`, `userId`, and `role` request attributes already used by `ProjectTeamController`.
- User-facing report remains `AiScoreReportUserResponse`; internal `AiScoringSession` is only used for access checks.
