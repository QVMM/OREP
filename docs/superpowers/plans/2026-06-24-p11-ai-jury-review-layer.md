# P11 AI Jury Review Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 16 人格/AI 评审团从 meetingId 绑定的展示能力升级为 session/report 维度的脱敏复核层，只输出质疑点、表达盲区、训练建议和分歧说明，不改基础 AI 分数。

**Architecture:** 后端新增 session-native jury review API，基于 P10 的 `AiScoreReportUserResponse` 安全字段构造评审团输入，写入现有 `ai_jury_*` 表并输出脱敏 DTO。前端报告页从 `/api/ai/jury/{meetingId}` 迁移到 `/api/ai-score/sessions/{sessionId}/jury/*`，保留 meetingId legacy fallback。16 人格画像分为用户 DTO 和管理员 DTO，用户端永不暴露 `prompt_modifier`、`scoring_bias`、内部规则聚焦配置或任何 prompt/weight/version/hash 字段。

**Tech Stack:** Spring Boot 3 + MyBatis Plus + Jackson + H2/MySQL SQL migrations；Vue 3 + Vite + Element Plus；existing `AiScoringSessionService` report DTO；existing `ai_judge_personas_seed.json` seed.

---

## Scope

P11 只做评审团复核层，不重新设计评分规则，不修改 P8/P9/P10 基础评分分数，不把评审团意见写回 `ai_score_report.overall_score`。

This plan intentionally implements a deterministic local jury review first. Future LLM calls can replace the deterministic report builder behind the same service contract, but user-facing DTO and black-box redaction rules must not change.

## File Structure

**Backend create:**

- `backend/src/main/java/com/orep/backend/entity/AiJurySession.java`  
  Maps `ai_jury_session`, adding `scoringSessionId` support.
- `backend/src/main/java/com/orep/backend/entity/AiJuryMember.java`  
  Maps `ai_jury_member`.
- `backend/src/main/java/com/orep/backend/entity/AiJudgeReport.java`  
  Maps per-persona review rows.
- `backend/src/main/java/com/orep/backend/entity/AiJuryAggregate.java`  
  Maps aggregate disagreement/consensus rows.
- `backend/src/main/java/com/orep/backend/mapper/AiJurySessionMapper.java`
- `backend/src/main/java/com/orep/backend/mapper/AiJuryMemberMapper.java`
- `backend/src/main/java/com/orep/backend/mapper/AiJudgeReportMapper.java`
- `backend/src/main/java/com/orep/backend/mapper/AiJuryAggregateMapper.java`
- `backend/src/main/java/com/orep/backend/dto/AiJuryReviewUserResponse.java`  
  User-safe jury response.
- `backend/src/main/java/com/orep/backend/dto/AiJudgePersonaUserResponse.java`  
  User-safe persona card.
- `backend/src/main/java/com/orep/backend/service/AiJuryReviewService.java`  
  Builds, stores, reads, and redacts jury review results.
- `backend/src/main/java/com/orep/backend/controller/AiJuryReviewController.java`  
  Session-native jury endpoints plus legacy meeting compatibility.
- `backend/src/main/resources/sql/alter_ai_jury_tables_p11.sql`
- `dockerrun/sql/backend-resources/alter_ai_jury_tables_p11.sql`
- `backend/src/test/java/com/orep/backend/service/AiJuryReviewServiceTest.java`
- `backend/src/test/java/com/orep/backend/controller/AiJuryReviewControllerTest.java`

**Backend modify:**

- `backend/src/main/java/com/orep/backend/service/AiJudgePersonaService.java`  
  Split user-safe and admin payloads.
- `backend/src/main/java/com/orep/backend/controller/AiJuryPersonaController.java`  
  User persona endpoint returns safe DTO; admin endpoint keeps editable internals.
- `backend/src/main/resources/sql/create_ai_jury_tables.sql`
- `dockerrun/sql/backend-resources/create_ai_jury_tables.sql`
- `backend/src/test/java/com/orep/backend/service/AiJudgePersonaServiceTest.java`

**Frontend create:**

- `frontend/user/src/utils/aiJuryReview.js`
- `frontend/user/src/components/ai-score/JuryPerspectivePanel.vue`

**Frontend modify:**

- `frontend/user/src/views/AiScoreResult.vue`  
  Replace embedded jury workspace with `JuryPerspectivePanel`, use session-first API, keep legacy fallback.

**Plan/status modify at completion:**

- `docs/superpowers/plans/2026-06-23-ai-scoring-meeting-room-optimization.md`

---

## Task 1: Persona User DTO Redaction

**Files:**

- Modify: `backend/src/main/java/com/orep/backend/service/AiJudgePersonaService.java`
- Modify: `backend/src/main/java/com/orep/backend/controller/AiJuryPersonaController.java`
- Test: `backend/src/test/java/com/orep/backend/service/AiJudgePersonaServiceTest.java`

- [x] **Step 1: Add failing service test for user-safe persona payload**

Append this test to `backend/src/test/java/com/orep/backend/service/AiJudgePersonaServiceTest.java`:

```java
@Test
void userPersonaPayloadDoesNotExposePromptBiasOrInternalRubricFocus() {
    AiJudgePersona persona = new AiJudgePersona();
    persona.setId(1L);
    persona.setCode("ENTP");
    persona.setName("创新挑战评委");
    persona.setShortLabel("爱追问创新闭环");
    persona.setFocusDimensionsJson("[\"innovation\",\"application_value\"]");
    persona.setJudgeProfileJson("{\"core_traits\":[\"质疑假设\"],\"scoring_style\":\"关注创新证据\",\"top_concerns\":[\"包装风险\"]}");
    persona.setRubricFocusJson("{\"primary_dimensions\":[\"innovation\"],\"primary_items\":[\"内部观察点A\"]}");
    persona.setScoringBiasJson("{\"risk_weight\":0.3}");
    persona.setPromptModifier("内部prompt片段");
    persona.setDescription("从创新性和真实性角度复核");
    persona.setEnabled(true);

    AiJudgePersonaService service = new AiJudgePersonaService(mock(AiJudgePersonaMapper.class), null);

    Map<String, Object> payload = service.toUserPayload(persona);
    String json = String.valueOf(payload);

    assertThat(payload).containsKeys("code", "name", "short_label", "focus_dimensions", "description", "enabled", "persona_view");
    assertThat(json)
            .doesNotContain("prompt")
            .doesNotContain("Prompt")
            .doesNotContain("prompt_modifier")
            .doesNotContain("scoring_bias")
            .doesNotContain("rubric_focus")
            .doesNotContain("内部观察点A")
            .doesNotContain("risk_weight")
            .doesNotContain("内部prompt片段");
}
```

- [x] **Step 2: Run test and verify it fails**

Run:

```bash
cd backend && mvn test -Dtest=AiJudgePersonaServiceTest#userPersonaPayloadDoesNotExposePromptBiasOrInternalRubricFocus
```

Expected: FAIL with `cannot find symbol method toUserPayload(...)`.

- [x] **Step 3: Implement user/admin payload split**

In `backend/src/main/java/com/orep/backend/service/AiJudgePersonaService.java`, add:

```java
public List<Map<String, Object>> listUserPersonaPayloads() {
    return listEnabledPersonas().stream().map(this::toUserPayload).toList();
}

public List<Map<String, Object>> listAdminPersonaPayloads() {
    List<AiJudgePersona> personas = listEnabledPersonas();
    return personas.stream().map(this::toPayload).toList();
}

private List<AiJudgePersona> listEnabledPersonas() {
    List<AiJudgePersona> personas = personaMapper.selectList(
            new LambdaQueryWrapper<AiJudgePersona>().orderByAsc(AiJudgePersona::getCode)
    );
    if (personas.isEmpty()) {
        seedMissingDefaults();
        personas = personaMapper.selectList(
                new LambdaQueryWrapper<AiJudgePersona>().orderByAsc(AiJudgePersona::getCode)
        );
    }
    return personas.stream()
            .filter(item -> item.getEnabled() == null || item.getEnabled())
            .toList();
}

public Map<String, Object> toUserPayload(AiJudgePersona persona) {
    Map<String, Object> profile = readJson(persona.getJudgeProfileJson(), Map.class, Map.of());
    Map<String, Object> personaView = new LinkedHashMap<>();
    personaView.put("core_traits", profile.getOrDefault("core_traits", List.of()));
    personaView.put("scoring_style", profile.getOrDefault("scoring_style", ""));
    personaView.put("evidence_preference", profile.getOrDefault("evidence_preference", ""));
    personaView.put("top_concerns", profile.getOrDefault("top_concerns", profile.getOrDefault("sensitive_risks", List.of())));
    personaView.put("feedback_style", profile.getOrDefault("feedback_style", ""));

    Map<String, Object> payload = new LinkedHashMap<>();
    payload.put("code", persona.getCode());
    payload.put("name", persona.getName());
    payload.put("short_label", persona.getShortLabel());
    payload.put("focus_dimensions", readJson(persona.getFocusDimensionsJson(), List.class, List.of()));
    payload.put("description", persona.getDescription());
    payload.put("enabled", persona.getEnabled() == null || persona.getEnabled());
    payload.put("persona_view", personaView);
    return payload;
}
```

Change existing `listPersonaPayloads()` to delegate to `listAdminPersonaPayloads()` to preserve admin behavior:

```java
public List<Map<String, Object>> listPersonaPayloads() {
    return listAdminPersonaPayloads();
}
```

- [x] **Step 4: Change controller user endpoint to safe payload**

In `backend/src/main/java/com/orep/backend/controller/AiJuryPersonaController.java`, replace the combined mapping:

```java
@GetMapping("/api/ai-jury/personas")
public Result<Map<String, Object>> listUserPersonas() {
    return Result.success(Map.of("personas", personaService.listUserPersonaPayloads()));
}

@GetMapping("/api/admin/ai-jury/personas")
public Result<Map<String, Object>> listAdminPersonas() {
    return Result.success(Map.of("personas", personaService.listAdminPersonaPayloads()));
}
```

- [x] **Step 5: Run persona tests**

Run:

```bash
cd backend && mvn test -Dtest=AiJudgePersonaServiceTest
```

Expected: PASS, 3 tests, 0 failures.

---

## Task 2: Session-Native Jury Tables and Entities

**Files:**

- Create: `backend/src/main/resources/sql/alter_ai_jury_tables_p11.sql`
- Create: `dockerrun/sql/backend-resources/alter_ai_jury_tables_p11.sql`
- Modify: `backend/src/main/resources/sql/create_ai_jury_tables.sql`
- Modify: `dockerrun/sql/backend-resources/create_ai_jury_tables.sql`
- Create: `backend/src/main/java/com/orep/backend/entity/AiJurySession.java`
- Create: `backend/src/main/java/com/orep/backend/entity/AiJuryMember.java`
- Create: `backend/src/main/java/com/orep/backend/entity/AiJudgeReport.java`
- Create: `backend/src/main/java/com/orep/backend/entity/AiJuryAggregate.java`
- Create: `backend/src/main/java/com/orep/backend/mapper/AiJurySessionMapper.java`
- Create: `backend/src/main/java/com/orep/backend/mapper/AiJuryMemberMapper.java`
- Create: `backend/src/main/java/com/orep/backend/mapper/AiJudgeReportMapper.java`
- Create: `backend/src/main/java/com/orep/backend/mapper/AiJuryAggregateMapper.java`
- Test: `backend/src/test/java/com/orep/backend/service/AiJuryReviewServiceTest.java`

- [x] **Step 1: Add SQL migration**

Create `backend/src/main/resources/sql/alter_ai_jury_tables_p11.sql` and copy the same file to `dockerrun/sql/backend-resources/alter_ai_jury_tables_p11.sql`:

```sql
ALTER TABLE ai_jury_session
  ADD COLUMN IF NOT EXISTS scoring_session_id BIGINT NULL COMMENT 'AI评分会话ID';

ALTER TABLE ai_jury_session
  MODIFY COLUMN meeting_id BIGINT NULL COMMENT '会议ID，上传视频评分可为空';

ALTER TABLE ai_jury_session
  ADD INDEX IF NOT EXISTS idx_scoring_session_status (scoring_session_id, status);

ALTER TABLE ai_judge_report
  ADD COLUMN IF NOT EXISTS scoring_session_id BIGINT NULL COMMENT 'AI评分会话ID';

ALTER TABLE ai_judge_report
  MODIFY COLUMN meeting_id BIGINT NULL COMMENT '会议ID，上传视频评分可为空';

ALTER TABLE ai_judge_report
  ADD INDEX IF NOT EXISTS idx_scoring_session (scoring_session_id);

ALTER TABLE ai_jury_aggregate
  ADD COLUMN IF NOT EXISTS scoring_session_id BIGINT NULL COMMENT 'AI评分会话ID';

ALTER TABLE ai_jury_aggregate
  MODIFY COLUMN meeting_id BIGINT NULL COMMENT '会议ID，上传视频评分可为空';

ALTER TABLE ai_jury_aggregate
  ADD INDEX IF NOT EXISTS idx_scoring_session (scoring_session_id);
```

- [x] **Step 2: Update create SQL for fresh installs**

In both `create_ai_jury_tables.sql` files:

- Change `ai_jury_session.meeting_id BIGINT NOT NULL` to `meeting_id BIGINT DEFAULT NULL`.
- Add `scoring_session_id BIGINT DEFAULT NULL` after `meeting_id`.
- Add key `KEY idx_scoring_session_status (scoring_session_id, status)`.
- Change `ai_judge_report.meeting_id BIGINT NOT NULL` to `meeting_id BIGINT DEFAULT NULL`.
- Add `scoring_session_id BIGINT DEFAULT NULL` after `meeting_id`.
- Add key `KEY idx_scoring_session (scoring_session_id)`.
- Change `ai_jury_aggregate.meeting_id BIGINT NOT NULL` to `meeting_id BIGINT DEFAULT NULL`.
- Add `scoring_session_id BIGINT DEFAULT NULL` after `meeting_id`.
- Add key `KEY idx_scoring_session (scoring_session_id)`.

- [x] **Step 3: Add entity and mapper compile test**

Create `backend/src/test/java/com/orep/backend/service/AiJuryReviewServiceTest.java` with initial compile assertion:

```java
package com.orep.backend.service;

import com.orep.backend.entity.AiJudgeReport;
import com.orep.backend.entity.AiJuryAggregate;
import com.orep.backend.entity.AiJuryMember;
import com.orep.backend.entity.AiJurySession;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;

import static org.assertj.core.api.Assertions.assertThat;

class AiJuryReviewServiceTest {

    @Test
    void juryEntitiesSupportSessionNativeFields() {
        AiJurySession session = new AiJurySession();
        session.setScoringSessionId(99L);
        session.setMeetingId(null);
        session.setStatus("completed");

        AiJudgeReport report = new AiJudgeReport();
        report.setScoringSessionId(99L);
        report.setMeetingId(null);
        report.setPersonaCode("INTJ");
        report.setOverallScore(new BigDecimal("78.50"));

        AiJuryMember member = new AiJuryMember();
        member.setPersonaCode("INTJ");
        member.setSeatNo(1);

        AiJuryAggregate aggregate = new AiJuryAggregate();
        aggregate.setScoringSessionId(99L);
        aggregate.setMeetingId(null);
        aggregate.setTrimmedAverageScore(new BigDecimal("79.20"));

        assertThat(session.getScoringSessionId()).isEqualTo(99L);
        assertThat(report.getMeetingId()).isNull();
        assertThat(member.getSeatNo()).isEqualTo(1);
        assertThat(aggregate.getTrimmedAverageScore()).isEqualByComparingTo("79.20");
    }
}
```

- [x] **Step 4: Run test and verify it fails**

Run:

```bash
cd backend && mvn test -Dtest=AiJuryReviewServiceTest#juryEntitiesSupportSessionNativeFields
```

Expected: FAIL with missing entity classes.

- [x] **Step 5: Implement entities and mappers**

Create each entity with Lombok `@Data`, MyBatis `@TableName`, and `@TableId(type = IdType.AUTO)`. Use Java fields matching snake_case columns:

```java
@Data
@TableName("ai_jury_session")
public class AiJurySession {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long meetingId;
    private Long scoringSessionId;
    private Long baseReportId;
    private String seed;
    private String standardVersion;
    private String personaPoolVersion;
    private Integer judgeCount;
    private String status;
    private BigDecimal officialScore;
    private BigDecimal juryTrimmedAvg;
    private BigDecimal juryRawAvg;
    private BigDecimal highestScore;
    private BigDecimal lowestScore;
    private BigDecimal scoreDiffFromOfficial;
    private String evidenceSnapshotPath;
    private String resultPath;
    private String errorMessage;
    private LocalDateTime startedAt;
    private LocalDateTime completedAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
}
```

For `AiJuryMember`, include `id`, `jurySessionId`, `personaId`, `personaCode`, `seatNo`, `displayName`, `roleLabel`, `createdAt`.  
For `AiJudgeReport`, include all columns from `ai_judge_report`, including `scoringSessionId`.  
For `AiJuryAggregate`, include all columns from `ai_jury_aggregate`, including `scoringSessionId`.

Create mappers:

```java
@Mapper
public interface AiJurySessionMapper extends BaseMapper<AiJurySession> {
}
```

Repeat the same pattern for `AiJuryMemberMapper`, `AiJudgeReportMapper`, and `AiJuryAggregateMapper`.

- [x] **Step 6: Run compile test**

Run:

```bash
cd backend && mvn test -Dtest=AiJuryReviewServiceTest#juryEntitiesSupportSessionNativeFields
```

Expected: PASS, 1 test, 0 failures.

---

## Task 3: User-Safe Jury Review DTO and Service

**Files:**

- Create: `backend/src/main/java/com/orep/backend/dto/AiJuryReviewUserResponse.java`
- Create: `backend/src/main/java/com/orep/backend/service/AiJuryReviewService.java`
- Modify: `backend/src/test/java/com/orep/backend/service/AiJuryReviewServiceTest.java`

- [x] **Step 1: Add failing test for deterministic safe review**

Append to `AiJuryReviewServiceTest`:

```java
@Test
void buildPreviewReviewDoesNotChangeOfficialScoreAndDoesNotExposeInternalFields() {
    AiScoreReportUserResponse base = new AiScoreReportUserResponse();
    base.setSessionId(77L);
    base.setMeetingId(null);
    base.setOverallScore(new BigDecimal("82.00"));
    base.setTrackName("新一代信息技术赛道");

    AiScoreReportUserResponse.StructuredDeduction deduction = new AiScoreReportUserResponse.StructuredDeduction();
    deduction.setDimensionName("技术能力");
    deduction.setDeductedPoints(new BigDecimal("4.00"));
    deduction.setReason("核心演示证据不足");
    deduction.setRequiredFix("补充真实运行演示和关键日志");
    deduction.setAcceptanceCriteria("下一轮能看到完整运行链路");
    deduction.setRecovery(false);
    base.setStructuredDeductions(List.of(deduction));

    Map<String, Object> persona = new LinkedHashMap<>();
    persona.put("code", "INTJ");
    persona.put("name", "系统架构评委");
    persona.put("short_label", "重系统性");
    persona.put("focus_dimensions", List.of("技术能力"));
    persona.put("persona_view", Map.of(
            "scoring_style", "严谨审查",
            "top_concerns", List.of("演示证据不足"),
            "feedback_style", "直接给出结构化建议"
    ));

    AiJuryReviewService service = new AiJuryReviewService(null, null, null, null, null, null, null);

    AiJuryReviewUserResponse response = service.buildPreviewResponse(base, List.of(persona));
    String json = new ObjectMapper().writeValueAsString(response);

    assertThat(response.getOfficialScore()).isEqualByComparingTo("82.00");
    assertThat(response.getMembers()).hasSize(1);
    assertThat(response.getMembers().get(0).getRoleLabel()).contains("重系统性");
    assertThat(response.getMembers().get(0).getPerspectiveQuestions()).isNotEmpty();
    assertThat(response.getMembers().get(0).getTrainingSuggestions()).isNotEmpty();
    assertThat(json)
            .doesNotContain("prompt")
            .doesNotContain("rubric")
            .doesNotContain("weight")
            .doesNotContain("internal")
            .doesNotContain("version");
}
```

- [x] **Step 2: Run test and verify it fails**

Run:

```bash
cd backend && mvn test -Dtest=AiJuryReviewServiceTest#buildPreviewReviewDoesNotChangeOfficialScoreAndDoesNotExposeInternalFields
```

Expected: FAIL with missing `AiJuryReviewService` or `AiJuryReviewUserResponse`.

- [x] **Step 3: Create DTO**

Create `backend/src/main/java/com/orep/backend/dto/AiJuryReviewUserResponse.java`:

```java
package com.orep.backend.dto;

import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Data
public class AiJuryReviewUserResponse {
    private Long jurySessionId;
    private Long sessionId;
    private Long meetingId;
    private String status;
    private String reviewMode;
    private String trackName;
    private BigDecimal officialScore;
    private BigDecimal juryAverageScore;
    private BigDecimal scoreDiffFromOfficial;
    private Integer judgeCount;
    private Integer successfulCount;
    private String explanation;
    private List<MemberReview> members = new ArrayList<>();
    private AggregateReview aggregate = new AggregateReview();
    private LocalDateTime completedAt;

    @Data
    public static class MemberReview {
        private String personaCode;
        private String displayName;
        private String roleLabel;
        private BigDecimal referenceScore;
        private String scoreRelationToOfficial;
        private List<String> perspectiveQuestions = new ArrayList<>();
        private List<String> expressionRisks = new ArrayList<>();
        private List<String> trainingSuggestions = new ArrayList<>();
        private List<String> evidenceConcerns = new ArrayList<>();
    }

    @Data
    public static class AggregateReview {
        private List<String> consensusIssues = new ArrayList<>();
        private List<String> disagreementFocus = new ArrayList<>();
        private List<String> nextTrainingPriorities = new ArrayList<>();
    }
}
```

- [x] **Step 4: Create deterministic service preview builder**

Create `backend/src/main/java/com/orep/backend/service/AiJuryReviewService.java` with constructor dependencies:

```java
public AiJuryReviewService(
        AiScoringSessionService scoringSessionService,
        AiJudgePersonaService personaService,
        AiJurySessionMapper jurySessionMapper,
        AiJuryMemberMapper juryMemberMapper,
        AiJudgeReportMapper judgeReportMapper,
        AiJuryAggregateMapper aggregateMapper,
        ObjectMapper objectMapper
) {
    this.scoringSessionService = scoringSessionService;
    this.personaService = personaService;
    this.jurySessionMapper = jurySessionMapper;
    this.juryMemberMapper = juryMemberMapper;
    this.judgeReportMapper = judgeReportMapper;
    this.aggregateMapper = aggregateMapper;
    this.objectMapper = objectMapper == null ? new ObjectMapper() : objectMapper;
}
```

Add public preview method:

```java
public AiJuryReviewUserResponse buildPreviewResponse(
        AiScoreReportUserResponse base,
        List<Map<String, Object>> personas
) {
    AiJuryReviewUserResponse response = new AiJuryReviewUserResponse();
    response.setSessionId(base.getSessionId());
    response.setMeetingId(base.getMeetingId());
    response.setStatus("completed");
    response.setReviewMode("复核层");
    response.setTrackName(base.getTrackName());
    response.setOfficialScore(valueOrZero(base.getOverallScore()));
    response.setJudgeCount(personas.size());
    response.setSuccessfulCount(personas.size());
    response.setExplanation("AI评审团只提供复核视角、表达盲区和训练建议，不修改基础AI评分。");

    List<AiScoreReportUserResponse.StructuredDeduction> deductions =
            base.getStructuredDeductions() == null ? List.of() : base.getStructuredDeductions();

    for (Map<String, Object> persona : personas) {
        response.getMembers().add(toMemberReview(response.getOfficialScore(), persona, deductions));
    }
    response.setJuryAverageScore(response.getOfficialScore());
    response.setScoreDiffFromOfficial(BigDecimal.ZERO);
    response.setAggregate(toAggregateReview(deductions));
    return response;
}
```

Add helper behavior:

```java
private AiJuryReviewUserResponse.MemberReview toMemberReview(
        BigDecimal officialScore,
        Map<String, Object> persona,
        List<AiScoreReportUserResponse.StructuredDeduction> deductions
) {
    String code = String.valueOf(persona.getOrDefault("code", ""));
    String shortLabel = String.valueOf(persona.getOrDefault("short_label", "独立复核"));
    AiJuryReviewUserResponse.MemberReview member = new AiJuryReviewUserResponse.MemberReview();
    member.setPersonaCode(code);
    member.setDisplayName(String.valueOf(persona.getOrDefault("name", code)));
    member.setRoleLabel(shortLabel);
    member.setReferenceScore(officialScore);
    member.setScoreRelationToOfficial("不参与基础分计算");
    member.setPerspectiveQuestions(buildQuestions(shortLabel, deductions));
    member.setExpressionRisks(buildExpressionRisks(deductions));
    member.setTrainingSuggestions(buildTrainingSuggestions(deductions));
    member.setEvidenceConcerns(buildEvidenceConcerns(deductions));
    return member;
}

private List<String> buildQuestions(String label, List<AiScoreReportUserResponse.StructuredDeduction> deductions) {
    if (deductions.isEmpty()) return List.of(label + "会追问：当前亮点是否有现场证据支撑？");
    return deductions.stream()
            .limit(3)
            .map(item -> label + "会追问：" + safe(item.getReason(), "该问题") + " 是否已经被真实证据闭环？")
            .toList();
}

private List<String> buildTrainingSuggestions(List<AiScoreReportUserResponse.StructuredDeduction> deductions) {
    if (deductions.isEmpty()) return List.of("保留当前优势，并补充可验真的演示证据。");
    return deductions.stream()
            .limit(3)
            .map(item -> safe(item.getRequiredFix(), "围绕扣分项补充证据、演示和验收标准。"))
            .toList();
}
```

The service must not include any field named `prompt`, `rubric`, `weight`, `internal`, or `version` in `AiJuryReviewUserResponse`.

- [x] **Step 5: Run service test**

Run:

```bash
cd backend && mvn test -Dtest=AiJuryReviewServiceTest
```

Expected: PASS, 2 tests, 0 failures.

---

## Task 4: Session-Native Jury Review API

**Files:**

- Create: `backend/src/main/java/com/orep/backend/controller/AiJuryReviewController.java`
- Modify: `backend/src/main/java/com/orep/backend/service/AiJuryReviewService.java`
- Test: `backend/src/test/java/com/orep/backend/controller/AiJuryReviewControllerTest.java`

- [x] **Step 1: Add failing controller tests**

Create `backend/src/test/java/com/orep/backend/controller/AiJuryReviewControllerTest.java`:

```java
package com.orep.backend.controller;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.orep.backend.dto.AiJuryReviewUserResponse;
import com.orep.backend.service.AiJuryReviewService;
import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MockMvc;

import java.math.BigDecimal;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;
import static org.springframework.test.web.servlet.setup.MockMvcBuilders.standaloneSetup;

class AiJuryReviewControllerTest {

    @Test
    void startAndResultUseSessionIdAndDoNotExposeInternalFields() throws Exception {
        AiJuryReviewService service = mock(AiJuryReviewService.class);
        AiJuryReviewUserResponse response = new AiJuryReviewUserResponse();
        response.setSessionId(88L);
        response.setStatus("completed");
        response.setReviewMode("复核层");
        response.setOfficialScore(new BigDecimal("81.00"));
        response.setExplanation("评审团不修改基础AI评分。");
        when(service.startForSession(88L)).thenReturn(response);
        when(service.resultBySession(88L)).thenReturn(response);

        MockMvc mvc = standaloneSetup(new AiJuryReviewController(service)).build();

        String startJson = mvc.perform(post("/api/ai-score/sessions/88/jury/start"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.sessionId").value(88))
                .andExpect(jsonPath("$.data.reviewMode").value("复核层"))
                .andReturn().getResponse().getContentAsString();

        String resultJson = mvc.perform(get("/api/ai-score/sessions/88/jury/result"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.data.sessionId").value(88))
                .andExpect(jsonPath("$.data.officialScore").value(81.00))
                .andReturn().getResponse().getContentAsString();

        assertThat(startJson + resultJson)
                .doesNotContain("prompt")
                .doesNotContain("rubric_hash")
                .doesNotContain("rubric_path")
                .doesNotContain("internal_version")
                .doesNotContain("weight");
    }
}
```

- [x] **Step 2: Run controller test and verify it fails**

Run:

```bash
cd backend && mvn test -Dtest=AiJuryReviewControllerTest
```

Expected: FAIL with missing controller.

- [x] **Step 3: Implement controller**

Create `backend/src/main/java/com/orep/backend/controller/AiJuryReviewController.java`:

```java
package com.orep.backend.controller;

import com.orep.backend.common.Result;
import com.orep.backend.dto.AiJuryReviewUserResponse;
import com.orep.backend.service.AiJuryReviewService;
import org.springframework.web.bind.annotation.*;

@RestController
public class AiJuryReviewController {
    private final AiJuryReviewService juryReviewService;

    public AiJuryReviewController(AiJuryReviewService juryReviewService) {
        this.juryReviewService = juryReviewService;
    }

    @PostMapping("/api/ai-score/sessions/{sessionId}/jury/start")
    public Result<AiJuryReviewUserResponse> startBySession(@PathVariable Long sessionId) {
        return Result.success(juryReviewService.startForSession(sessionId));
    }

    @GetMapping("/api/ai-score/sessions/{sessionId}/jury/result")
    public Result<AiJuryReviewUserResponse> resultBySession(@PathVariable Long sessionId) {
        return Result.success(juryReviewService.resultBySession(sessionId));
    }

    @GetMapping("/api/ai-score/sessions/{sessionId}/jury/report")
    public Result<AiJuryReviewUserResponse> reportBySession(@PathVariable Long sessionId) {
        return Result.success(juryReviewService.resultBySession(sessionId));
    }

    @PostMapping("/api/ai/jury/{meetingId}/start")
    public AiJuryReviewUserResponse startByMeetingLegacy(@PathVariable Long meetingId) {
        return juryReviewService.startForLatestMeeting(meetingId);
    }

    @GetMapping("/api/ai/jury/{meetingId}/result")
    public AiJuryReviewUserResponse resultByMeetingLegacy(@PathVariable Long meetingId) {
        return juryReviewService.resultByLatestMeeting(meetingId);
    }
}
```

- [x] **Step 4: Implement service API methods**

In `AiJuryReviewService`, add:

```java
public AiJuryReviewUserResponse startForSession(Long sessionId) {
    AiScoreReportUserResponse base = scoringSessionService.reportBySession(sessionId);
    List<Map<String, Object>> personas = personaService.listUserPersonaPayloads();
    return buildPreviewResponse(base, personas);
}

public AiJuryReviewUserResponse resultBySession(Long sessionId) {
    return startForSession(sessionId);
}

public AiJuryReviewUserResponse startForLatestMeeting(Long meetingId) {
    AiScoreReportUserResponse base = scoringSessionService.reportByMeetingId(meetingId);
    List<Map<String, Object>> personas = personaService.listUserPersonaPayloads();
    return buildPreviewResponse(base, personas);
}

public AiJuryReviewUserResponse resultByLatestMeeting(Long meetingId) {
    return startForLatestMeeting(meetingId);
}
```

If `AiScoringSessionService.reportByMeetingId(Long)` does not exist, add it there as a legacy compatibility helper that loads latest session by meetingId and falls back to legacy report, using existing `statusByMeetingId`/report code paths. The returned DTO must pass existing redaction rules.

- [x] **Step 5: Run controller test**

Run:

```bash
cd backend && mvn test -Dtest=AiJuryReviewControllerTest,AiJudgePersonaServiceTest,AiJuryReviewServiceTest
```

Expected: PASS, all selected tests 0 failures.

---

## Task 5: Persist Jury Preview Results

**Files:**

- Modify: `backend/src/main/java/com/orep/backend/service/AiJuryReviewService.java`
- Modify: `backend/src/test/java/com/orep/backend/service/AiJuryReviewServiceTest.java`

- [x] **Step 1: Add failing persistence interaction test**

Append to `AiJuryReviewServiceTest`:

```java
@Test
void startForSessionPersistsJurySessionMembersReportsAndAggregate() {
    AiScoringSessionService scoring = mock(AiScoringSessionService.class);
    AiJudgePersonaService personas = mock(AiJudgePersonaService.class);
    AiJurySessionMapper sessionMapper = mock(AiJurySessionMapper.class);
    AiJuryMemberMapper memberMapper = mock(AiJuryMemberMapper.class);
    AiJudgeReportMapper reportMapper = mock(AiJudgeReportMapper.class);
    AiJuryAggregateMapper aggregateMapper = mock(AiJuryAggregateMapper.class);

    AiScoreReportUserResponse base = new AiScoreReportUserResponse();
    base.setSessionId(88L);
    base.setMeetingId(12L);
    base.setReportId(33L);
    base.setOverallScore(new BigDecimal("80.00"));
    base.setTrackName("餐饮赛道");
    when(scoring.reportBySession(88L)).thenReturn(base);
    when(personas.listUserPersonaPayloads()).thenReturn(List.of(Map.of(
            "code", "ISTJ",
            "name", "规范审查评委",
            "short_label", "重规范",
            "focus_dimensions", List.of("职业素养"),
            "persona_view", Map.of("top_concerns", List.of("流程不规范"))
    )));

    AiJuryReviewService service = new AiJuryReviewService(
            scoring, personas, sessionMapper, memberMapper, reportMapper, aggregateMapper, new ObjectMapper()
    );

    AiJuryReviewUserResponse response = service.startForSession(88L);

    assertThat(response.getSessionId()).isEqualTo(88L);
    verify(sessionMapper).insert(argThat(item ->
            Long.valueOf(88L).equals(item.getScoringSessionId())
                    && Long.valueOf(12L).equals(item.getMeetingId())
                    && "completed".equals(item.getStatus())
    ));
    verify(memberMapper).insert(any(AiJuryMember.class));
    verify(reportMapper).insert(any(AiJudgeReport.class));
    verify(aggregateMapper).insert(any(AiJuryAggregate.class));
}
```

- [x] **Step 2: Run test and verify it fails**

Run:

```bash
cd backend && mvn test -Dtest=AiJuryReviewServiceTest#startForSessionPersistsJurySessionMembersReportsAndAggregate
```

Expected: FAIL because service currently returns preview without persistence.

- [x] **Step 3: Implement persistence in startForSession**

In `AiJuryReviewService.startForSession(Long sessionId)`:

1. Load base report via `scoringSessionService.reportBySession(sessionId)`.
2. Build response with user-safe personas.
3. Insert `AiJurySession` with:
   - `scoringSessionId = base.getSessionId()`
   - `meetingId = base.getMeetingId()`
   - `baseReportId = base.getReportId()`
   - `seed = "session-" + sessionId`
   - `standardVersion = "safe-review"`
   - `personaPoolVersion = "user-safe"`
   - `judgeCount = response.getJudgeCount()`
   - `status = "completed"`
   - `officialScore = response.getOfficialScore()`
   - `juryTrimmedAvg = response.getJuryAverageScore()`
   - `juryRawAvg = response.getJuryAverageScore()`
   - `scoreDiffFromOfficial = response.getScoreDiffFromOfficial()`
   - timestamps.
4. Insert one `AiJuryMember` and one `AiJudgeReport` per member.
5. Insert one `AiJuryAggregate`.

Use `objectMapper.writeValueAsString(...)` only for user-safe member/aggregate maps, never for persona admin payloads.

- [x] **Step 4: Add resultBySession to read latest persisted result**

Implement:

```java
public AiJuryReviewUserResponse resultBySession(Long sessionId) {
    AiJurySession latest = jurySessionMapper.selectOne(
            new LambdaQueryWrapper<AiJurySession>()
                    .eq(AiJurySession::getScoringSessionId, sessionId)
                    .orderByDesc(AiJurySession::getCreatedAt)
                    .last("LIMIT 1")
    );
    if (latest == null) {
        AiJuryReviewUserResponse empty = new AiJuryReviewUserResponse();
        empty.setSessionId(sessionId);
        empty.setStatus("empty");
        empty.setReviewMode("复核层");
        empty.setExplanation("当前评分会话暂未生成AI评审团复核。");
        return empty;
    }
    return toUserResponse(latest);
}
```

`toUserResponse(latest)` must read reports and aggregate rows and return only `AiJuryReviewUserResponse` fields.

- [x] **Step 5: Run persistence tests**

Run:

```bash
cd backend && mvn test -Dtest=AiJuryReviewServiceTest,AiJuryReviewControllerTest
```

Expected: PASS, all selected tests 0 failures.

---

## Task 6: Frontend Jury API Utility and Panel Component

**Files:**

- Create: `frontend/user/src/utils/aiJuryReview.js`
- Create: `frontend/user/src/components/ai-score/JuryPerspectivePanel.vue`

- [x] **Step 1: Create API utility**

Create `frontend/user/src/utils/aiJuryReview.js`:

```js
import request from './request'

export async function getJuryReviewBySession(sessionId) {
  if (!sessionId) return { status: 'empty' }
  const res = await request.get(`/api/ai-score/sessions/${sessionId}/jury/result`)
  return res.data || res
}

export async function startJuryReviewBySession(sessionId) {
  const res = await request.post(`/api/ai-score/sessions/${sessionId}/jury/start`)
  return res.data || res
}

export async function getLegacyJuryReviewByMeeting(meetingId) {
  if (!meetingId) return { status: 'empty' }
  const res = await fetch(`/api/ai/jury/${meetingId}/result`)
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}

export async function startLegacyJuryReviewByMeeting(meetingId) {
  const res = await fetch(`/api/ai/jury/${meetingId}/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({})
  })
  if (!res.ok) throw new Error(`HTTP ${res.status}`)
  return res.json()
}
```

- [x] **Step 2: Create reusable panel component**

Create `frontend/user/src/components/ai-score/JuryPerspectivePanel.vue` with props:

```js
const props = defineProps({
  review: { type: Object, default: () => ({ status: 'empty' }) },
  loading: { type: Boolean, default: false },
  starting: { type: Boolean, default: false },
  error: { type: String, default: '' },
  canStart: { type: Boolean, default: true }
})

const emit = defineEmits(['start', 'select-member'])
```

Template requirements:

- Empty state: “当前评分会话暂未生成 AI 评审团复核” and button “生成评审团复核”.
- Header: “评审团只做复核，不修改基础分”.
- Metrics: officialScore, juryAverageScore, scoreDiffFromOfficial, judgeCount/successfulCount.
- Member list: personaCode, roleLabel, referenceScore, scoreRelationToOfficial.
- Aggregate cards: consensusIssues, disagreementFocus, nextTrainingPriorities.
- No visible text for `prompt`, `rubric`, `weight`, `version`, `hash`.

Use existing report page dark visual language: 8px radius, restrained borders, no nested cards inside cards.

- [x] **Step 3: Run frontend build to verify component compiles**

Run:

```bash
cd frontend/user && npm run build
```

Expected: PASS.

---

## Task 7: Wire Jury Panel Into AiScoreResult.vue

**Files:**

- Modify: `frontend/user/src/views/AiScoreResult.vue`

- [x] **Step 1: Import utility and component**

Add:

```js
import JuryPerspectivePanel from '../components/ai-score/JuryPerspectivePanel.vue'
import {
  getJuryReviewBySession,
  startJuryReviewBySession,
  getLegacyJuryReviewByMeeting,
  startLegacyJuryReviewByMeeting
} from '../utils/aiJuryReview'
```

- [x] **Step 2: Replace jury API functions with session-first logic**

Replace `loadJuryReview()`:

```js
async function loadJuryReview() {
  juryLoading.value = true
  juryError.value = ''
  try {
    if (sessionId.value) {
      juryResult.value = sanitizeInternalAiScoreFields(await getJuryReviewBySession(sessionId.value))
    } else if (effectiveMeetingId.value) {
      juryResult.value = sanitizeInternalAiScoreFields(await getLegacyJuryReviewByMeeting(effectiveMeetingId.value))
    } else {
      juryResult.value = { status: 'empty' }
    }
  } catch {
    juryResult.value = { status: 'empty' }
    juryError.value = 'AI评审团复核暂未生成。'
  } finally {
    juryLoading.value = false
  }
}
```

Replace `startJuryReview()`:

```js
async function startJuryReview() {
  juryStarting.value = true
  juryError.value = ''
  try {
    if (sessionId.value) {
      juryResult.value = sanitizeInternalAiScoreFields(await startJuryReviewBySession(sessionId.value))
    } else if (effectiveMeetingId.value) {
      juryResult.value = sanitizeInternalAiScoreFields(await startLegacyJuryReviewByMeeting(effectiveMeetingId.value))
    }
  } catch {
    juryError.value = 'AI评审团复核启动失败，请稍后重试。'
  } finally {
    juryStarting.value = false
  }
}
```

- [x] **Step 3: Replace large jury overview template with panel**

Inside `<section v-show="activeSection === 'jury'" class="section-stack jury-workspace">`, render:

```vue
<JuryPerspectivePanel
  :review="juryResult || { status: 'empty' }"
  :loading="juryLoading"
  :starting="juryStarting"
  :error="juryError"
  :can-start="Boolean(sessionId || effectiveMeetingId)"
  @start="startJuryReview"
  @select-member="selectedJuryMember = $event"
/>
```

Keep the existing member detail view if `selectedJuryMember` is used; otherwise remove dead detail code only after `npm run build` proves no references break.

- [x] **Step 4: Extend client-side internal-field scrubber**

In `sanitizeInternalAiScoreFields`, ensure the forbidden normalized keys include:

```js
'promptmodifier',
'scoringbias',
'rubricfocus',
'personapoolversion',
'standardversion',
'tokensjson',
'model',
'provider'
```

Keep `officialScore` and member `referenceScore`; those are user-safe because they are display-only and do not change base score.

- [x] **Step 5: Run frontend build**

Run:

```bash
cd frontend/user && npm run build
```

Expected: PASS.

---

## Task 8: Redaction and Regression Verification

**Files:**

- Modify: `backend/src/test/java/com/orep/backend/service/AiScoringSessionRedactionMappingTest.java`
- Modify: `docs/superpowers/plans/2026-06-23-ai-scoring-meeting-room-optimization.md`

- [x] **Step 1: Add P11 forbidden-field regression**

In backend redaction tests, recursively assert user-facing jury responses do not contain:

```text
rubric_hash
rubric_path
internal_version
prompt
prompt_modifier
weight
scoring_bias
rubric_focus
standard_version
persona_pool_version
tokens_json
provider
model
```

Use `ObjectMapper.writeValueAsString(response)` and AssertJ `doesNotContain(...)`.

- [x] **Step 2: Run backend targeted tests**

Run:

```bash
cd backend && mvn test -Dtest=AiJudgePersonaServiceTest,AiJuryReviewServiceTest,AiJuryReviewControllerTest,AiScoringSessionRedactionMappingTest
```

Expected: PASS, all selected tests 0 failures.

- [x] **Step 3: Run full backend test suite**

Run:

```bash
cd backend && mvn test
```

Expected: PASS, 0 failures.

- [x] **Step 4: Run frontend build**

Run:

```bash
cd frontend/user && npm run build
```

Expected: PASS.

- [x] **Step 5: Update master plan execution board**

In `docs/superpowers/plans/2026-06-23-ai-scoring-meeting-room-optimization.md`, update P11 row:

```markdown
| P11 | 已完成 | 16人格/评审团作为复核层 | 已完成 | `cd backend && mvn test -Dtest=AiJudgePersonaServiceTest,AiJuryReviewServiceTest,AiJuryReviewControllerTest,AiScoringSessionRedactionMappingTest` 通过；`cd backend && mvn test` 通过；`cd frontend/user && npm run build` 通过；评审团已迁移到 session/report 维度复核层，用户端不暴露 prompt、规则、权重或内部版本 |
```

Append completion record with:

```markdown
### 本轮完成记录：P11 16人格/评审团复核层

- 修改文件：
  - `backend/src/main/java/com/orep/backend/service/AiJudgePersonaService.java`
  - `backend/src/main/java/com/orep/backend/controller/AiJuryPersonaController.java`
  - `backend/src/main/java/com/orep/backend/service/AiJuryReviewService.java`
  - `backend/src/main/java/com/orep/backend/controller/AiJuryReviewController.java`
  - `frontend/user/src/views/AiScoreResult.vue`
  - `frontend/user/src/components/ai-score/JuryPerspectivePanel.vue`
  - `frontend/user/src/utils/aiJuryReview.js`
- 后端验证：
  - `cd backend && mvn test -Dtest=AiJudgePersonaServiceTest,AiJuryReviewServiceTest,AiJuryReviewControllerTest,AiScoringSessionRedactionMappingTest` 通过，0 failures。
  - `cd backend && mvn test` 通过，0 failures。
- 前端验证：
  - `cd frontend/user && npm run build` 通过。
- 手工验证：
  - 打开 `/ai-score/report/:sessionId`，AI评审团页显示“只做复核，不修改基础分”。
  - Network 响应不含 `prompt`、`rubric_hash`、`rubric_path`、`internal_version`、`weight`。
- 已知边界：
  - 本轮使用确定性本地复核生成器；真实多模型独立调用可在后续替换 service 内部实现，但 DTO 和脱敏边界不变。
```

Before finalizing, replace the two bracketed verification lines with actual test outputs. Do not leave bracket text in the final committed plan.

---

## Self-Review

**Spec coverage:**

- P11 “只做复核视角，不篡改基础分”: Task 3 response explicitly keeps `officialScore` and uses `referenceScore`/`scoreRelationToOfficial`; Task 8 verifies no report score mutation.
- “输入是基础报告、证据锚点、观察点扣分项、赛道、脱敏风险标签”: Task 3 builds from `AiScoreReportUserResponse`, which already contains P10-safe structured observations/deductions/evidence anchors.
- “不传内部规则全文/prompt/精确权重”: Task 1 redacts persona user payload; Task 4/8 recursively test user API output.
- “输出不同评审视角、表达风险、训练建议、分歧说明”: Task 3 DTO and builder fields cover questions, expression risks, suggestions, aggregate focus.
- “前端报告页接入”: Task 6/7 adds panel and session-first API wiring.

**Placeholder scan:**

- No task contains `TBD`, `TODO`, or “implement later”.
- Verification-record examples contain exact commands and expected pass/failure wording.

**Type consistency:**

- `sessionId` maps to backend `scoringSessionId` in DB entities and to frontend route `/api/ai-score/sessions/{sessionId}/jury/*`.
- `officialScore` is display-only; `juryAverageScore` and member `referenceScore` do not write back to `AiScoreReportUserResponse.overallScore`.
- User-safe persona payload uses `persona_view`; frontend panel reads jury review response only, not admin persona payload.
