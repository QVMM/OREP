# OREP AI Scoring P9 Continuous Memory Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Upgrade continuous AI scoring memory from loose text similarity to deterministic recovery review based on previous `deductionId`, previous `acceptanceCriteria`, current evidence anchors, and backend-capped recoverable points.

**Architecture:** P8 already stores structured observations and deductions in `ai_score_observation` and `ai_score_deduction`; P9 should reuse those tables instead of introducing another memory table. The model may submit recovery claims for prior deductions, but the backend resolves those claims against the latest completed prior session for the same project/team/track, caps recovered points by the stored previous `maxRecoverablePoints`, rejects hallucinated source deductions, writes recovery rows back into `ai_score_deduction`, and leaves current-round deductions visible as separate rows. User-facing responses and report summaries must not expose rule-engine version, rubric hashes, prompt, weight, or internal rule metadata.

**Tech Stack:** Java 21, Spring Boot, MyBatis Plus, Jackson, JUnit 5, Mockito, Maven, existing OREP backend DTO/entity/mapper/service/controller patterns.

---

## File Map

- Modify: `backend/src/main/java/com/orep/backend/dto/AiScoreStructuredResultRequest.java`
  - Add `recoveryClaims` to the structured result payload.
  - Add nested `RecoveryClaimInput` with only user/model-safe fields.
- Create: `backend/src/main/java/com/orep/backend/service/AiScoreRecoveryMemoryService.java`
  - Resolve prior completed scoring session.
  - Validate source deduction IDs against stored prior deductions.
  - Convert model claims into trusted `AiScoreRecoveryInput` for `AiScoreRuleEngine`.
  - Build persisted recovery deduction rows.
- Modify: `backend/src/main/java/com/orep/backend/service/AiScoreStructuredResultValidator.java`
  - Validate recovery claim shape before evidence anchor whitelist.
- Modify: `backend/src/main/java/com/orep/backend/service/AiScoreStructuredResultService.java`
  - Use recovery memory service when `useHistoryMemory=true`.
  - Pass trusted recoveries to the rule engine.
  - Persist accepted recovery rows.
  - Remove `resultRuleEngineVersion` from `structuredResultJson`.
- Test: `backend/src/test/java/com/orep/backend/service/AiScoreRecoveryMemoryServiceTest.java`
  - Unit tests for previous-session lookup, claim validation, cap enforcement, and no-history behavior.
- Modify: `backend/src/test/java/com/orep/backend/service/AiScoreStructuredResultValidatorTest.java`
  - Add recovery claim validation tests.
- Modify: `backend/src/test/java/com/orep/backend/service/AiScoreStructuredResultServiceTest.java`
  - Add integration-style service tests for persisted recovery rows and no internal version in structured summary.
- Modify: `backend/src/test/java/com/orep/backend/controller/AiScoreStructuredResultControllerTest.java`
  - Add request/response test for `recoveryClaims` and redaction.
- Modify: `docs/superpowers/plans/2026-06-23-ai-scoring-meeting-room-optimization.md`
  - Mark P9 complete after tests pass and record exact verification commands.

---

## Task 1: Add Recovery Claim DTO And Validator Rules

**Files:**
- Modify: `backend/src/main/java/com/orep/backend/dto/AiScoreStructuredResultRequest.java`
- Modify: `backend/src/main/java/com/orep/backend/service/AiScoreStructuredResultValidator.java`
- Modify: `backend/src/test/java/com/orep/backend/service/AiScoreStructuredResultValidatorTest.java`

- [x] **Step 1: Write failing validator tests**

Add these tests to `backend/src/test/java/com/orep/backend/service/AiScoreStructuredResultValidatorTest.java`:

```java
@Test
void acceptsCompleteRecoveryClaim() {
    AiScoreStructuredResultRequest request = validRequest();
    request.setRecoveryClaims(List.of(recoveryClaim("previous-deduction-1", "fixed", "4")));

    assertDoesNotThrow(() -> validator.validate(request));
}

@Test
void rejectsAcceptedRecoveryClaimWithoutSourceDeductionId() {
    AiScoreStructuredResultRequest request = validRequest();
    AiScoreStructuredResultRequest.RecoveryClaimInput claim = recoveryClaim("previous-deduction-1", "fixed", "4");
    claim.setSourceDeductionId(" ");
    request.setRecoveryClaims(List.of(claim));

    IllegalArgumentException exception = assertThrows(
            IllegalArgumentException.class,
            () -> validator.validate(request)
    );

    assertTrue(exception.getMessage().contains("recoveryClaims[0].sourceDeductionId"));
}

@Test
void rejectsAcceptedRecoveryClaimWithoutAcceptanceEvidence() {
    AiScoreStructuredResultRequest request = validRequest();
    AiScoreStructuredResultRequest.RecoveryClaimInput claim = recoveryClaim("previous-deduction-1", "verified", "4");
    claim.setAcceptanceEvidence(" ");
    request.setRecoveryClaims(List.of(claim));

    IllegalArgumentException exception = assertThrows(
            IllegalArgumentException.class,
            () -> validator.validate(request)
    );

    assertTrue(exception.getMessage().contains("recoveryClaims[0].acceptanceEvidence"));
}

@Test
void rejectsRecoveryClaimWithNegativeRequestedPoints() {
    AiScoreStructuredResultRequest request = validRequest();
    AiScoreStructuredResultRequest.RecoveryClaimInput claim = recoveryClaim("previous-deduction-1", "fixed", "-0.1");
    request.setRecoveryClaims(List.of(claim));

    IllegalArgumentException exception = assertThrows(
            IllegalArgumentException.class,
            () -> validator.validate(request)
    );

    assertTrue(exception.getMessage().contains("recoveryClaims[0].requestedRecoverPoints"));
}

@Test
void rejectsRecoveryClaimWithEmptyEvidenceAnchors() {
    AiScoreStructuredResultRequest request = validRequest();
    AiScoreStructuredResultRequest.RecoveryClaimInput claim = recoveryClaim("previous-deduction-1", "fixed", "4");
    claim.setEvidenceAnchorIds(List.of());
    request.setRecoveryClaims(List.of(claim));

    IllegalArgumentException exception = assertThrows(
            IllegalArgumentException.class,
            () -> validator.validate(request)
    );

    assertTrue(exception.getMessage().contains("recoveryClaims[0].evidenceAnchorIds"));
}

private AiScoreStructuredResultRequest.RecoveryClaimInput recoveryClaim(
        String sourceDeductionId,
        String status,
        String requestedPoints
) {
    AiScoreStructuredResultRequest.RecoveryClaimInput claim = new AiScoreStructuredResultRequest.RecoveryClaimInput();
    claim.setSourceDeductionId(sourceDeductionId);
    claim.setRecoveryStatus(status);
    claim.setRequestedRecoverPoints(new BigDecimal(requestedPoints));
    claim.setAcceptanceEvidence("本轮演示提供了可打开的修复证据");
    claim.setEvidenceAnchorIds(List.of(10L));
    return claim;
}
```

- [x] **Step 2: Run tests and verify failure**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreStructuredResultValidatorTest
```

Expected: compilation fails because `RecoveryClaimInput` and `setRecoveryClaims` do not exist.

- [x] **Step 3: Add DTO fields**

Update `backend/src/main/java/com/orep/backend/dto/AiScoreStructuredResultRequest.java`:

```java
private List<RecoveryClaimInput> recoveryClaims;
```

Add this nested class:

```java
@Data
public static class RecoveryClaimInput {
    private String sourceDeductionId;
    private String recoveryStatus;
    private BigDecimal requestedRecoverPoints;
    private String acceptanceEvidence;
    private List<Long> evidenceAnchorIds;
}
```

- [x] **Step 4: Add validator logic**

In `backend/src/main/java/com/orep/backend/service/AiScoreStructuredResultValidator.java`, add accepted statuses:

```java
private static final Set<String> RECOVERY_STATUSES = Set.of(
        "not_fixed", "partially_fixed", "fixed", "invalid_fix", "not_enough_evidence", "verified", "recovered", "pending", "rejected"
);

private static final Set<String> ACCEPTED_RECOVERY_STATUSES = Set.of("fixed", "verified", "recovered");
```

Call `validateRecoveryClaims(request.getRecoveryClaims());` from `validate`.

Add:

```java
private void validateRecoveryClaims(List<AiScoreStructuredResultRequest.RecoveryClaimInput> claims) {
    List<AiScoreStructuredResultRequest.RecoveryClaimInput> safeClaims = emptyIfNull(claims);
    for (int index = 0; index < safeClaims.size(); index++) {
        AiScoreStructuredResultRequest.RecoveryClaimInput claim = safeClaims.get(index);
        String prefix = "recoveryClaims[" + index + "]";
        requireNonNull(claim, prefix);
        requireText(claim.getSourceDeductionId(), prefix + ".sourceDeductionId");
        requireEnum(claim.getRecoveryStatus(), RECOVERY_STATUSES, prefix + ".recoveryStatus");
        requireScore(claim.getRequestedRecoverPoints(), prefix + ".requestedRecoverPoints");
        if (ACCEPTED_RECOVERY_STATUSES.contains(claim.getRecoveryStatus())) {
            requireText(claim.getAcceptanceEvidence(), prefix + ".acceptanceEvidence");
            requireAnchorIds(claim.getEvidenceAnchorIds(), prefix + ".evidenceAnchorIds");
        }
    }
}
```

Use existing helper methods where available. If helper names differ, implement equivalent private helpers with the same validation messages used in tests.

- [x] **Step 5: Run validator tests**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreStructuredResultValidatorTest
```

Expected: all tests pass.

---

## Task 2: Implement Previous Deduction Recovery Memory Service

**Files:**
- Create: `backend/src/main/java/com/orep/backend/service/AiScoreRecoveryMemoryService.java`
- Test: `backend/src/test/java/com/orep/backend/service/AiScoreRecoveryMemoryServiceTest.java`

- [x] **Step 1: Write failing service tests**

Create `backend/src/test/java/com/orep/backend/service/AiScoreRecoveryMemoryServiceTest.java`:

```java
package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.orep.backend.dto.AiScoreRecoveryInput;
import com.orep.backend.dto.AiScoreStructuredResultRequest;
import com.orep.backend.entity.AiScoreDeduction;
import com.orep.backend.entity.AiScoringSession;
import com.orep.backend.mapper.AiScoreDeductionMapper;
import com.orep.backend.mapper.AiScoringSessionMapper;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.util.List;
import java.util.Set;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class AiScoreRecoveryMemoryServiceTest {
    private final AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
    private final AiScoreDeductionMapper deductionMapper = mock(AiScoreDeductionMapper.class);
    private final AiScoreRecoveryMemoryService service = new AiScoreRecoveryMemoryService(sessionMapper, deductionMapper);

    @Test
    void returnsEmptyWhenHistoryMemoryDisabled() {
        AiScoringSession current = currentSession();
        current.setUseHistoryMemory(false);

        List<AiScoreRecoveryInput> recoveries = service.resolveTrustedRecoveries(
                current,
                List.of(claim("deduction-1", "fixed", "10")),
                Set.of(10L)
        );

        assertTrue(recoveries.isEmpty());
    }

    @Test
    void capsRecoveryByPreviousMaxRecoverablePoints() {
        when(sessionMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(previousSession()));
        when(deductionMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(previousDeduction("deduction-1", "6")));

        List<AiScoreRecoveryInput> recoveries = service.resolveTrustedRecoveries(
                currentSession(),
                List.of(claim("deduction-1", "fixed", "10")),
                Set.of(10L)
        );

        assertEquals(1, recoveries.size());
        assertEquals(new BigDecimal("10"), recoveries.getFirst().getRequestedRecoverPoints());
        assertEquals(new BigDecimal("6"), recoveries.getFirst().getMaxRecoverablePoints());
        assertEquals("deduction-1", recoveries.getFirst().getSourceDeductionId());
        assertEquals("fixed", recoveries.getFirst().getRecoveryStatus());
    }

    @Test
    void rejectsClaimForMissingPreviousDeduction() {
        when(sessionMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(previousSession()));
        when(deductionMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(previousDeduction("deduction-1", "6")));

        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> service.resolveTrustedRecoveries(
                        currentSession(),
                        List.of(claim("hallucinated-deduction", "fixed", "3")),
                        Set.of(10L)
                )
        );

        assertTrue(exception.getMessage().contains("hallucinated-deduction"));
    }

    @Test
    void rejectsAcceptedClaimWithAnchorOutsideCurrentSession() {
        when(sessionMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(previousSession()));
        when(deductionMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(previousDeduction("deduction-1", "6")));

        IllegalArgumentException exception = assertThrows(
                IllegalArgumentException.class,
                () -> service.resolveTrustedRecoveries(
                        currentSession(),
                        List.of(claim("deduction-1", "fixed", "3")),
                        Set.of(99L)
                )
        );

        assertTrue(exception.getMessage().contains("evidenceAnchorId 10"));
    }

    private AiScoringSession currentSession() {
        AiScoringSession session = new AiScoringSession();
        session.setId(200L);
        session.setProjectId(1L);
        session.setTeamId(2L);
        session.setTrackId("track-it");
        session.setUseHistoryMemory(true);
        return session;
    }

    private AiScoringSession previousSession() {
        AiScoringSession session = new AiScoringSession();
        session.setId(100L);
        session.setProjectId(1L);
        session.setTeamId(2L);
        session.setTrackId("track-it");
        session.setStatus("completed");
        return session;
    }

    private AiScoreDeduction previousDeduction(String deductionId, String maxRecoverablePoints) {
        AiScoreDeduction deduction = new AiScoreDeduction();
        deduction.setDeductionId(deductionId);
        deduction.setObservationCode("tech_demo");
        deduction.setDimensionCode("technology");
        deduction.setDeductedPoints(new BigDecimal("8"));
        deduction.setMaxRecoverablePoints(new BigDecimal(maxRecoverablePoints));
        deduction.setReason("上一轮现场演示故障");
        deduction.setRequiredFix("修复演示流程并提供可复验证据");
        deduction.setAcceptanceCriteria("演示流程稳定跑通且关键画面可复核");
        deduction.setStatus("new");
        return deduction;
    }

    private AiScoreStructuredResultRequest.RecoveryClaimInput claim(String sourceDeductionId, String status, String points) {
        AiScoreStructuredResultRequest.RecoveryClaimInput claim = new AiScoreStructuredResultRequest.RecoveryClaimInput();
        claim.setSourceDeductionId(sourceDeductionId);
        claim.setRecoveryStatus(status);
        claim.setRequestedRecoverPoints(new BigDecimal(points));
        claim.setAcceptanceEvidence("本轮视频证据显示已完成整改");
        claim.setEvidenceAnchorIds(List.of(10L));
        return claim;
    }
}
```

- [x] **Step 2: Run tests and verify failure**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreRecoveryMemoryServiceTest
```

Expected: compilation fails because `AiScoreRecoveryMemoryService` does not exist.

- [x] **Step 3: Implement service**

Create `backend/src/main/java/com/orep/backend/service/AiScoreRecoveryMemoryService.java`:

```java
package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.orep.backend.dto.AiScoreRecoveryInput;
import com.orep.backend.dto.AiScoreStructuredResultRequest;
import com.orep.backend.entity.AiScoreDeduction;
import com.orep.backend.entity.AiScoringSession;
import com.orep.backend.mapper.AiScoreDeductionMapper;
import com.orep.backend.mapper.AiScoringSessionMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class AiScoreRecoveryMemoryService {
    private static final Set<String> ACCEPTED_STATUSES = Set.of("fixed", "verified", "recovered");

    private final AiScoringSessionMapper sessionMapper;
    private final AiScoreDeductionMapper deductionMapper;

    public List<AiScoreRecoveryInput> resolveTrustedRecoveries(
            AiScoringSession currentSession,
            List<AiScoreStructuredResultRequest.RecoveryClaimInput> claims,
            Set<Long> validAnchorIds
    ) {
        if (currentSession == null || !Boolean.TRUE.equals(currentSession.getUseHistoryMemory()) || claims == null || claims.isEmpty()) {
            return List.of();
        }

        AiScoringSession previousSession = latestPreviousCompletedSession(currentSession);
        if (previousSession == null) {
            return List.of();
        }

        Map<String, AiScoreDeduction> previousDeductions = previousDeductionsById(previousSession.getId());
        return claims.stream()
                .filter(claim -> ACCEPTED_STATUSES.contains(claim.getRecoveryStatus()))
                .map(claim -> trustedRecovery(claim, previousDeductions, validAnchorIds))
                .toList();
    }

    public List<AiScoreDeduction> buildRecoveryRows(
            Long sessionId,
            Long reportId,
            List<AiScoreRecoveryInput> acceptedRecoveries,
            List<AiScoreStructuredResultRequest.RecoveryClaimInput> claims,
            java.time.LocalDateTime now
    ) {
        if (acceptedRecoveries == null || acceptedRecoveries.isEmpty()) {
            return List.of();
        }
        Map<String, AiScoreStructuredResultRequest.RecoveryClaimInput> claimsBySource = claims.stream()
                .collect(Collectors.toMap(
                        AiScoreStructuredResultRequest.RecoveryClaimInput::getSourceDeductionId,
                        claim -> claim,
                        (left, right) -> left,
                        LinkedHashMap::new
                ));
        return acceptedRecoveries.stream()
                .map(recovery -> recoveryRow(sessionId, reportId, recovery, claimsBySource.get(recovery.getSourceDeductionId()), now))
                .toList();
    }

    private AiScoringSession latestPreviousCompletedSession(AiScoringSession currentSession) {
        List<AiScoringSession> sessions = sessionMapper.selectList(new LambdaQueryWrapper<AiScoringSession>()
                .eq(AiScoringSession::getProjectId, currentSession.getProjectId())
                .eq(AiScoringSession::getTeamId, currentSession.getTeamId())
                .eq(AiScoringSession::getTrackId, currentSession.getTrackId())
                .eq(AiScoringSession::getStatus, "completed")
                .lt(AiScoringSession::getId, currentSession.getId())
                .orderByDesc(AiScoringSession::getId)
                .last("LIMIT 1"));
        return sessions.isEmpty() ? null : sessions.getFirst();
    }

    private Map<String, AiScoreDeduction> previousDeductionsById(Long previousSessionId) {
        return deductionMapper.selectList(new LambdaQueryWrapper<AiScoreDeduction>()
                        .eq(AiScoreDeduction::getSessionId, previousSessionId))
                .stream()
                .filter(deduction -> deduction.getDeductionId() != null)
                .collect(Collectors.toMap(
                        AiScoreDeduction::getDeductionId,
                        deduction -> deduction,
                        (left, right) -> left,
                        LinkedHashMap::new
                ));
    }

    private AiScoreRecoveryInput trustedRecovery(
            AiScoreStructuredResultRequest.RecoveryClaimInput claim,
            Map<String, AiScoreDeduction> previousDeductions,
            Set<Long> validAnchorIds
    ) {
        for (Long anchorId : claim.getEvidenceAnchorIds()) {
            if (!validAnchorIds.contains(anchorId)) {
                throw new IllegalArgumentException("evidenceAnchorId " + anchorId + " does not belong to current recovery session");
            }
        }
        AiScoreDeduction previousDeduction = previousDeductions.get(claim.getSourceDeductionId());
        if (previousDeduction == null) {
            throw new IllegalArgumentException("recovery source deduction not found: " + claim.getSourceDeductionId());
        }
        AiScoreRecoveryInput recovery = new AiScoreRecoveryInput();
        recovery.setSourceDeductionId(claim.getSourceDeductionId());
        recovery.setRecoveryStatus(claim.getRecoveryStatus());
        recovery.setRequestedRecoverPoints(claim.getRequestedRecoverPoints());
        recovery.setMaxRecoverablePoints(previousDeduction.getMaxRecoverablePoints() == null ? BigDecimal.ZERO : previousDeduction.getMaxRecoverablePoints());
        recovery.setAcceptanceEvidence(claim.getAcceptanceEvidence());
        return recovery;
    }

    private AiScoreDeduction recoveryRow(
            Long sessionId,
            Long reportId,
            AiScoreRecoveryInput recovery,
            AiScoreStructuredResultRequest.RecoveryClaimInput claim,
            java.time.LocalDateTime now
    ) {
        AiScoreDeduction row = new AiScoreDeduction();
        row.setSessionId(sessionId);
        row.setReportId(reportId);
        row.setDeductionId("recovery-" + recovery.getSourceDeductionId());
        row.setDeductedPoints(BigDecimal.ZERO);
        row.setRecoveredPoints(recovery.getMaxRecoverablePoints().min(recovery.getRequestedRecoverPoints()));
        row.setReason("上轮扣分项已通过本轮证据复核");
        row.setRequiredFix("保持已修复项稳定，不用本项抵消本轮新增扣分");
        row.setAcceptanceCriteria(recovery.getAcceptanceEvidence());
        row.setMaxRecoverablePoints(recovery.getMaxRecoverablePoints());
        row.setEvidenceLevel("medium");
        row.setConfidence(new BigDecimal("0.80"));
        row.setEvidenceAnchorIdsJson("[]");
        row.setRecoverySourceDeductionId(recovery.getSourceDeductionId());
        row.setStatus(recovery.getRecoveryStatus());
        row.setCreatedAt(now);
        return row;
    }
}
```

- [x] **Step 4: Run service tests**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreRecoveryMemoryServiceTest
```

Expected: all tests pass.

---

## Task 3: Integrate Recovery Memory Into Structured Result Application

**Files:**
- Modify: `backend/src/main/java/com/orep/backend/service/AiScoreStructuredResultService.java`
- Modify: `backend/src/test/java/com/orep/backend/service/AiScoreStructuredResultServiceTest.java`

- [x] **Step 1: Write failing service tests**

Add these tests to `backend/src/test/java/com/orep/backend/service/AiScoreStructuredResultServiceTest.java`:

```java
@Test
void appliesTrustedRecoveryFromPreviousDeductionAndPersistsRecoveryRow() {
    AiScoreRecoveryMemoryService recoveryMemoryService = mock(AiScoreRecoveryMemoryService.class);
    AiScoreStructuredResultService serviceWithRecovery = new AiScoreStructuredResultService(
            sessionMapper,
            evidenceAnchorMapper,
            reportMapper,
            observationMapper,
            deductionMapper,
            validator,
            ruleEngine,
            recoveryMemoryService,
            new ObjectMapper()
    );
    AiScoringSession session = session(123L, 456L, null);
    session.setProjectId(1L);
    session.setTeamId(2L);
    session.setTrackId("track-it");
    session.setUseHistoryMemory(true);
    AiScoreReport existingReport = new AiScoreReport();
    existingReport.setId(888L);
    existingReport.setMeetingId(456L);
    when(sessionMapper.selectById(123L)).thenReturn(session);
    when(evidenceAnchorMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(anchor(10L), anchor(11L)));
    when(reportMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(existingReport);
    AiScoreStructuredResultRequest request = validRequest(123L);
    request.setRecoveryClaims(List.of(recoveryClaim("deduction-old", "fixed", "10")));
    AiScoreRecoveryInput trustedRecovery = new AiScoreRecoveryInput();
    trustedRecovery.setSourceDeductionId("deduction-old");
    trustedRecovery.setRecoveryStatus("fixed");
    trustedRecovery.setRequestedRecoverPoints(new BigDecimal("10"));
    trustedRecovery.setMaxRecoverablePoints(new BigDecimal("6"));
    trustedRecovery.setAcceptanceEvidence("本轮证据已验收");
    when(recoveryMemoryService.resolveTrustedRecoveries(any(AiScoringSession.class), any(), any())).thenReturn(List.of(trustedRecovery));
    AiScoreDeduction recoveryRow = new AiScoreDeduction();
    recoveryRow.setSessionId(123L);
    recoveryRow.setReportId(888L);
    recoveryRow.setDeductionId("recovery-deduction-old");
    recoveryRow.setDeductedPoints(BigDecimal.ZERO);
    recoveryRow.setRecoveredPoints(new BigDecimal("6"));
    recoveryRow.setRecoverySourceDeductionId("deduction-old");
    recoveryRow.setStatus("fixed");
    when(recoveryMemoryService.buildRecoveryRows(any(), any(), any(), any(), any())).thenReturn(List.of(recoveryRow));

    AiScoreRuleEngineResult result = serviceWithRecovery.applyStructuredResult(123L, request, List.of());

    assertScore("100.00", result.getFinalScore());
    assertScore("6", result.getRecoveredScore());
    ArgumentCaptor<AiScoreDeduction> deductionCaptor = ArgumentCaptor.forClass(AiScoreDeduction.class);
    verify(deductionMapper, org.mockito.Mockito.times(2)).insert(deductionCaptor.capture());
    assertTrue(deductionCaptor.getAllValues().stream()
            .anyMatch(deduction -> "recovery-deduction-old".equals(deduction.getDeductionId())
                    && new BigDecimal("6").compareTo(deduction.getRecoveredPoints()) == 0));
}

@Test
void structuredResultSummaryDoesNotExposeRuleEngineVersion() {
    when(sessionMapper.selectById(123L)).thenReturn(session(123L, 456L, null));
    when(evidenceAnchorMapper.selectList(any(LambdaQueryWrapper.class))).thenReturn(List.of(anchor(10L), anchor(11L)));
    AiScoreReport existingReport = new AiScoreReport();
    existingReport.setId(888L);
    existingReport.setMeetingId(456L);
    when(reportMapper.selectOne(any(LambdaQueryWrapper.class))).thenReturn(existingReport);

    service.applyStructuredResult(123L, validRequest(123L), List.of());

    ArgumentCaptor<AiScoreReport> reportCaptor = ArgumentCaptor.forClass(AiScoreReport.class);
    verify(reportMapper).updateById(reportCaptor.capture());
    assertTrue(!reportCaptor.getValue().getStructuredResultJson().contains("ruleEngineVersion"));
}

private AiScoreStructuredResultRequest.RecoveryClaimInput recoveryClaim(String sourceDeductionId, String status, String points) {
    AiScoreStructuredResultRequest.RecoveryClaimInput claim = new AiScoreStructuredResultRequest.RecoveryClaimInput();
    claim.setSourceDeductionId(sourceDeductionId);
    claim.setRecoveryStatus(status);
    claim.setRequestedRecoverPoints(new BigDecimal(points));
    claim.setAcceptanceEvidence("本轮证据已验收");
    claim.setEvidenceAnchorIds(List.of(10L));
    return claim;
}
```

- [x] **Step 2: Run tests and verify failure**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreStructuredResultServiceTest
```

Expected: compilation fails because the service constructor and integration logic do not yet include `AiScoreRecoveryMemoryService`.

- [x] **Step 3: Inject recovery memory service**

Update constructor fields in `AiScoreStructuredResultService`:

```java
private final AiScoreRecoveryMemoryService recoveryMemoryService;
```

Update tests constructing the service to pass either a real service or a Mockito mock. The main field initialization should become:

```java
private final AiScoreRecoveryMemoryService recoveryMemoryService = mock(AiScoreRecoveryMemoryService.class);
private final AiScoreStructuredResultService service = new AiScoreStructuredResultService(
        sessionMapper,
        evidenceAnchorMapper,
        reportMapper,
        observationMapper,
        deductionMapper,
        validator,
        ruleEngine,
        recoveryMemoryService,
        new ObjectMapper()
);
```

- [x] **Step 4: Resolve trusted recoveries inside `applyStructuredResult`**

Replace:

```java
AiScoreRuleEngineResult result = ruleEngine.score(request, recoveries);
```

with:

```java
List<AiScoreRecoveryInput> trustedRecoveries = recoveryMemoryService.resolveTrustedRecoveries(
        session,
        request.getRecoveryClaims(),
        validAnchorIds
);
if ((trustedRecoveries == null || trustedRecoveries.isEmpty()) && recoveries != null && !recoveries.isEmpty()) {
    trustedRecoveries = recoveries;
}
AiScoreRuleEngineResult result = ruleEngine.score(request, trustedRecoveries);
```

The fallback preserves existing P8 tests that call the service directly with explicit recoveries.

- [x] **Step 5: Persist recovery rows after current deductions**

After `insertDeductions(sessionId, reportId, request.getDeductions(), now);`, add:

```java
insertRecoveryRows(
        recoveryMemoryService.buildRecoveryRows(sessionId, reportId, result.getRecoveries(), request.getRecoveryClaims(), now)
);
```

Add helper:

```java
private void insertRecoveryRows(List<AiScoreDeduction> recoveryRows) {
    for (AiScoreDeduction recoveryRow : emptyIfNull(recoveryRows)) {
        deductionMapper.insert(recoveryRow);
    }
}
```

- [x] **Step 6: Remove internal version from structured report summary**

In `structuredResultSummary`, remove:

```java
summary.put("resultRuleEngineVersion", result.getRuleEngineVersion());
```

- [x] **Step 7: Run service tests**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreStructuredResultServiceTest
```

Expected: all tests pass.

---

## Task 4: Controller Integration And Redaction Regression

**Files:**
- Modify: `backend/src/test/java/com/orep/backend/controller/AiScoreStructuredResultControllerTest.java`
- Modify if needed: `backend/src/main/java/com/orep/backend/controller/AiScoreController.java`

- [x] **Step 1: Add controller test with recovery claims**

Add a WebMvc test that posts `recoveryClaims` to:

```text
POST /api/ai-score/sessions/{sessionId}/structured-result
```

The JSON body must include:

```json
{
  "sessionId": 123,
  "ruleEngineVersion": "p9-test",
  "scoreSummary": {
    "rawTotalScore": 95,
    "finalScore": 95,
    "scoreCap": 100
  },
  "observations": [
    {
      "observationCode": "tech_demo",
      "dimensionCode": "technology",
      "dimensionName": "技术能力",
      "rawScore": 100,
      "scoreCap": 100,
      "evidenceLevel": "strong",
      "confidence": 0.91,
      "validityStatus": "valid",
      "modelReason": "现场演示证据充分",
      "evidenceAnchorIds": [10]
    }
  ],
  "deductions": [],
  "recoveryClaims": [
    {
      "sourceDeductionId": "previous-demo-failure",
      "recoveryStatus": "fixed",
      "requestedRecoverPoints": 6,
      "acceptanceEvidence": "本轮视频显示核心演示流程稳定跑通",
      "evidenceAnchorIds": [10]
    }
  ]
}
```

Expected response:

```java
andExpect(status().isOk())
andExpect(jsonPath("$.data.finalScore").exists())
andExpect(jsonPath("$.data.ruleEngineVersion").doesNotExist())
```

Also assert raw response does not contain:

```text
rubric_hash
rubric_path
internal_version
prompt
weight
ruleEngineVersion
```

- [x] **Step 2: Run controller test**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreStructuredResultControllerTest,AiScoreResponseRedactionTest
```

Expected: all tests pass. If the test fails because the controller does not accept the new JSON field, ensure `AiScoreStructuredResultRequest` has `recoveryClaims` with standard Lombok getter/setter.

---

## Task 5: Full Verification And Main Plan Update

**Files:**
- Modify: `docs/superpowers/plans/2026-06-23-ai-scoring-meeting-room-optimization.md`

- [x] **Step 1: Run targeted P9 verification**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreStructuredResultValidatorTest,AiScoreRecoveryMemoryServiceTest,AiScoreStructuredResultServiceTest,AiScoreStructuredResultControllerTest,AiScoreRuleEngineTest,AiScoreResponseRedactionTest
```

Expected: all listed tests pass.

- [x] **Step 2: Run full backend regression**

Run:

```bash
cd backend && mvn test
```

Expected: all backend tests pass.

- [x] **Step 3: Update execution dashboard**

In `docs/superpowers/plans/2026-06-23-ai-scoring-meeting-room-optimization.md`, change the P9 row:

```markdown
| P9 | 已完成 | 连续评分记忆升级 | 已完成 | `cd backend && mvn test -Dtest=AiScoreStructuredResultValidatorTest,AiScoreRecoveryMemoryServiceTest,AiScoreStructuredResultServiceTest,AiScoreStructuredResultControllerTest,AiScoreRuleEngineTest,AiScoreResponseRedactionTest` 通过；`cd backend && mvn test` 通过；新增 recoveryClaims、上一轮扣分项解析、追回分上限裁定、恢复行落库、结构化报告脱敏回归 |
```

Append a completion record under the existing P8 completion record:

```markdown
### 本轮完成记录：P9 连续评分记忆升级

- 计划文件：
  - `docs/superpowers/plans/2026-06-24-ai-scoring-p9-continuous-memory.md`
- 修改文件：
  - `backend/src/main/java/com/orep/backend/dto/AiScoreStructuredResultRequest.java`
  - `backend/src/main/java/com/orep/backend/service/AiScoreStructuredResultValidator.java`
  - `backend/src/main/java/com/orep/backend/service/AiScoreRecoveryMemoryService.java`
  - `backend/src/main/java/com/orep/backend/service/AiScoreStructuredResultService.java`
  - `backend/src/test/java/com/orep/backend/service/AiScoreStructuredResultValidatorTest.java`
  - `backend/src/test/java/com/orep/backend/service/AiScoreRecoveryMemoryServiceTest.java`
  - `backend/src/test/java/com/orep/backend/service/AiScoreStructuredResultServiceTest.java`
  - `backend/src/test/java/com/orep/backend/controller/AiScoreStructuredResultControllerTest.java`
- 后端能力：
  - `recoveryClaims` 只表达模型/流水线对旧扣分项的修复主张，不能自带规则版本、权重或 prompt。
  - 后端按同项目、同团队、同赛道、当前 session 之前最近 completed session 查找上一轮扣分项。
  - 追回分只能来自真实存在的上一轮 `deductionId`，并受上一轮 `maxRecoverablePoints` 约束。
  - 本轮新增扣分项仍单独落库展示，追回行通过 `recovery_source_deduction_id` 关联旧扣分项，不把新增问题吞掉。
  - `structuredResultJson` 不再包含 `ruleEngineVersion`，减少后续报告页泄露内部评分管线信息的风险。
- 验证：
  - `cd backend && mvn test -Dtest=AiScoreStructuredResultValidatorTest,AiScoreRecoveryMemoryServiceTest,AiScoreStructuredResultServiceTest,AiScoreStructuredResultControllerTest,AiScoreRuleEngineTest,AiScoreResponseRedactionTest` 通过。
  - `cd backend && mvn test` 通过。
- 已知边界：
  - P9 解决“上一轮扣分项如何被本轮证据验证并追回分”的后端确定性地基；真实 ASR/OCR/frame 证据质量和报告 UI 展示仍在 P10-P12。
```

- [x] **Step 4: Verify no red-flag text in the P9 plan**

Run:

```bash
python - <<'PY'
from pathlib import Path

path = Path("docs/superpowers/plans/2026-06-24-ai-scoring-p9-continuous-memory.md")
terms = [
    "TB" + "D",
    "TO" + "DO",
    "implement " + "later",
    "fill " + "in",
    "place" + "holder",
    "Similar " + "to",
    "Write tests for " + "the above",
    "Add " + "appropriate",
]
text = path.read_text()
for line_no, line in enumerate(text.splitlines(), start=1):
    if any(term in line for term in terms):
        print(f"{line_no}:{line}")
PY
```

Expected: no output.

---

## Self-Review

**Spec coverage:** P9 requirement “deductionId + acceptanceCriteria + evidence review” is covered by `recoveryClaims`, previous deduction lookup, anchor validation, and persisted recovery rows. The requirement “first round deducts 6, second round can recover at most 6” is covered by `AiScoreRecoveryMemoryServiceTest.capsRecoveryByPreviousMaxRecoverablePoints`. The requirement “new deductions cannot disappear” is covered by keeping current deduction inserts and adding recovery rows separately. The requirement “cannot exceed score cap” remains covered by P8 `AiScoreRuleEngineTest.recoveryCannotExceedCurrentScoreCap`.

**Red-flag scan:** The plan avoids open-ended filler steps and includes exact file paths, code snippets, commands, and expected results.

**Type consistency:** `RecoveryClaimInput` is defined on `AiScoreStructuredResultRequest` and referenced consistently by validator, memory service, structured result service, and tests. `AiScoreRecoveryInput` remains the trusted internal rule-engine input.
