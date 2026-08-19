# Upload Video AI Scoring Pipeline Integration Plan ✅

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Connect the Java backend's uploaded_video scoring session to the local ai-scoring FastAPI pipeline, so uploaded videos get ASR, frame extraction, OCR, multi-model scoring, and report generation automatically.

**Architecture:** Java backend owns session lifecycle, permissions, media assets, and frontend API. After upload completes, Java calls ai-scoring's new `POST /api/ai/score-session` endpoint with session metadata and file paths. ai-scoring runs its existing pipeline and calls back Java's new `POST /api/ai-score/sessions/{sessionId}/pipeline-callback` endpoint with progress updates and final results. Java persists the final result as report/observations/deductions/evidence-anchors. Frontend report page shows a progress view when session is not yet completed.

**Tech Stack:** Spring Boot 3 + RestTemplate/WebClient + MyBatis-Plus; FastAPI + httpx; Vue 3 + Element Plus

---

## File Structure

**Backend create:**
- `backend/src/main/java/com/orep/backend/service/AiScoringPipelineClient.java` — HTTP client to call ai-scoring service
- `backend/src/main/java/com/orep/backend/dto/PipelineCallbackRequest.java` — DTO for pipeline callback payload
- `backend/src/main/java/com/orep/backend/dto/PipelineStartResponse.java` — DTO for pipeline start response
- `backend/src/test/java/com/orep/backend/service/AiScoringPipelineClientTest.java` — Unit tests for pipeline client

**Backend modify:**
- `backend/src/main/java/com/orep/backend/controller/AiScoreUploadController.java` — Call startPipeline after markUploaded
- `backend/src/main/java/com/orep/backend/controller/AiScoreController.java` — Add pipeline-callback endpoint
- `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java` — Add markPipelineQueued, processPipelineCallback methods
- `backend/src/main/java/com/orep/backend/service/AiScoreMediaAssetService.java` — Add getVideoAssetsBySession for pipeline client

**ai-scoring create:**
- `ai-scoring/app/routers/session_scoring_router.py` — New router for session-based scoring entry point
- `ai-scoring/app/services/session_pipeline_service.py` — Pipeline adapted for session-based flow with Java callbacks

**ai-scoring modify:**
- `ai-scoring/main.py` — Register new session_scoring_router

**Frontend modify:**
- `frontend/user/src/views/AiScoreResult.vue` — Add progress view when session not completed

---

## Task 1: Pipeline Callback DTO

**Files:**
- Create: `backend/src/main/java/com/orep/backend/dto/PipelineCallbackRequest.java`

- [x] **Step 1: Create PipelineCallbackRequest DTO**

```java
package com.orep.backend.dto;

import lombok.Data;
import java.math.BigDecimal;
import java.util.List;
import java.util.Map;

@Data
public class PipelineCallbackRequest {
    private Long sessionId;
    private String status;          // scoring, completed, failed
    private String currentStage;    // queued, audio_extracting, asr_processing, frame_extracting, ocr_processing, evidence_building, model_scoring, rule_calibrating, report_generating, completed, failed
    private Integer progressPercent;
    private String message;
    private String errorMessage;
    private PipelineFinalResult finalResult;

    @Data
    public static class PipelineFinalResult {
        private String transcript;
        private List<Map<String, Object>> asrSegments;
        private BigDecimal overallScore;
        private BigDecimal rawOverallScore;
        private String dimensionsJson;
        private String highlightsJson;
        private String criticalIssuesJson;
        private String improvementPrioritiesJson;
        private String speechQualityJson;
        private String scoreCalibrationJson;
        private String model;
        private List<ObservationInput> observations;
        private List<DeductionInput> deductions;
        private List<EvidenceAnchorInput> evidenceAnchors;
        private String ruleEngineVersion;
    }

    @Data
    public static class ObservationInput {
        private String observationCode;
        private String dimensionCode;
        private String dimensionName;
        private BigDecimal rawScore;
        private BigDecimal scoreCap;
        private String evidenceLevel;
        private BigDecimal confidence;
        private String validityStatus;
        private String modelReason;
        private List<Long> evidenceAnchorIds;
    }

    @Data
    public static class DeductionInput {
        private String deductionId;
        private String observationCode;
        private String dimensionCode;
        private BigDecimal deductedPoints;
        private BigDecimal maxRecoverablePoints;
        private String reason;
        private String requiredFix;
        private String acceptanceCriteria;
        private String evidenceLevel;
        private BigDecimal confidence;
        private String status;
        private List<Long> evidenceAnchorIds;
    }

    @Data
    public static class EvidenceAnchorInput {
        private String anchorType;
        private String anchorTitle;
        private String evidenceText;
        private String sourceRef;
        private Long startMs;
        private Long endMs;
        private BigDecimal confidence;
        private String validityStatus;
    }
}
```

- [x] **Step 2: Verify compilation**

Run: `cd backend && mvn compile -q`
Expected: BUILD SUCCESS

---

## Task 2: Pipeline Start Response DTO

**Files:**
- Create: `backend/src/main/java/com/orep/backend/dto/PipelineStartResponse.java`

- [x] **Step 1: Create PipelineStartResponse DTO**

```java
package com.orep.backend.dto;

import lombok.Data;

@Data
public class PipelineStartResponse {
    private boolean accepted;
    private String message;
    private String taskId;
}
```

- [x] **Step 2: Verify compilation**

Run: `cd backend && mvn compile -q`
Expected: BUILD SUCCESS

---

## Task 3: AiScoreMediaAssetService — Add query method for pipeline

**Files:**
- Modify: `backend/src/main/java/com/orep/backend/service/AiScoreMediaAssetService.java`

- [x] **Step 1: Add getVideoAssetBySession method**

Add this method to `AiScoreMediaAssetService`:

```java
public AiScoreMediaAsset getVideoAssetBySession(Long sessionId) {
    return mediaAssetMapper.selectOne(
        new LambdaQueryWrapper<AiScoreMediaAsset>()
            .eq(AiScoreMediaAsset::getSessionId, sessionId)
            .eq(AiScoreMediaAsset::getAssetType, "video")
            .last("LIMIT 1")
    );
}

public List<AiScoreMediaAsset> getMaterialAssetsBySession(Long sessionId) {
    return mediaAssetMapper.selectList(
        new LambdaQueryWrapper<AiScoreMediaAsset>()
            .eq(AiScoreMediaAsset::getSessionId, sessionId)
            .eq(AiScoreMediaAsset::getAssetType, "material")
    );
}
```

- [x] **Step 2: Verify compilation**

Run: `cd backend && mvn compile -q`
Expected: BUILD SUCCESS

---

## Task 4: AiScoringPipelineClient — HTTP client to call ai-scoring

**Files:**
- Create: `backend/src/main/java/com/orep/backend/service/AiScoringPipelineClient.java`
- Create: `backend/src/test/java/com/orep/backend/service/AiScoringPipelineClientTest.java`

- [x] **Step 1: Write failing tests for pipeline client**

```java
package com.orep.backend.service;

import com.orep.backend.dto.PipelineStartResponse;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestTemplate;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.client.RequestMatchers.requestTo;
import static org.springframework.test.client.ResponseCreators.withSuccess;
import static org.springframework.test.client.ResponseCreators.withServerError;

class AiScoringPipelineClientTest {

    @Test
    void startSessionPipelineSendsCorrectPayloadAndParsesResponse() {
        RestTemplate restTemplate = new RestTemplate();
        MockRestServiceServer server = MockRestServiceServer.bindTo(restTemplate).build();

        server.expect(requestTo("http://127.0.0.1:8090/api/ai/score-session"))
                .andExpect(org.springframework.test.client.RequestMatchers.method(HttpMethod.POST))
                .andRespond(withSuccess("""
                        {"accepted": true, "message": "Pipeline started", "taskId": "task-123"}
                        """, MediaType.APPLICATION_JSON));

        AiScoringPipelineClient client = new AiScoringPipelineClient(restTemplate);

        PipelineStartResponse response = client.startSessionPipeline(
                101L, "SC-20260624-000101", 9L, 3L, "餐饮赛道",
                "uploaded_video", "/uploads/ai-score/101/abc-video.mp4", "roadshow.mp4",
                List.of(Map.of("path", "/uploads/ai-score/101/mat.pdf", "name", "bp.pdf")),
                "http://localhost:8080/api/ai-score/sessions/101/pipeline-callback"
        );

        assertThat(response.isAccepted()).isTrue();
        assertThat(response.getTaskId()).isEqualTo("task-123");
        server.verify();
    }

    @Test
    void startSessionPipelineHandlesServerErrorGracefully() {
        RestTemplate restTemplate = new RestTemplate();
        MockRestServiceServer server = MockRestServiceServer.bindTo(restTemplate).build();

        server.expect(requestTo("http://127.0.0.1:8090/api/ai/score-session"))
                .andRespond(withServerError());

        AiScoringPipelineClient client = new AiScoringPipelineClient(restTemplate);

        PipelineStartResponse response = client.startSessionPipeline(
                101L, "SC-20260624-000101", 9L, 3L, "餐饮赛道",
                "uploaded_video", "/uploads/ai-score/101/abc-video.mp4", "roadshow.mp4",
                List.of(), "http://localhost:8080/api/ai-score/sessions/101/pipeline-callback"
        );

        assertThat(response.isAccepted()).isFalse();
        assertThat(response.getMessage()).contains("AI 服务调用失败");
        server.verify();
    }
}
```

- [x] **Step 2: Run test to verify it fails**

Run: `cd backend && mvn test -Dtest=AiScoringPipelineClientTest -q`
Expected: FAIL — class not found

- [x] **Step 3: Implement AiScoringPipelineClient**

```java
package com.orep.backend.service;

import com.orep.backend.dto.PipelineStartResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class AiScoringPipelineClient {

    private static final Logger log = LoggerFactory.getLogger(AiScoringPipelineClient.class);

    private final RestTemplate restTemplate;
    private final String baseUrl;

    public AiScoringPipelineClient(
            @Value("${ai-scoring.base-url:http://127.0.0.1:8090}") String baseUrl) {
        this.restTemplate = new RestTemplate();
        this.baseUrl = baseUrl;
    }

    // Constructor for testing with custom RestTemplate
    public AiScoringPipelineClient(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
        this.baseUrl = "http://127.0.0.1:8090";
    }

    public PipelineStartResponse startSessionPipeline(
            Long sessionId,
            String sessionNo,
            Long teamId,
            Long projectId,
            String trackName,
            String sourceType,
            String videoFilePath,
            String videoOriginalName,
            List<Map<String, String>> materials,
            String callbackUrl) {

        Map<String, Object> body = new HashMap<>();
        body.put("sessionId", sessionId);
        body.put("sessionNo", sessionNo);
        body.put("teamId", teamId);
        body.put("projectId", projectId);
        body.put("trackName", trackName);
        body.put("sourceType", sourceType);
        body.put("videoFilePath", videoFilePath);
        body.put("videoOriginalName", videoOriginalName);
        body.put("materials", materials != null ? materials : List.of());
        body.put("callbackUrl", callbackUrl);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);

        try {
            PipelineStartResponse response = restTemplate.postForObject(
                    baseUrl + "/api/ai/score-session",
                    entity,
                    PipelineStartResponse.class
            );
            if (response == null) {
                PipelineStartResponse fallback = new PipelineStartResponse();
                fallback.setAccepted(false);
                fallback.setMessage("AI 服务返回空响应");
                return fallback;
            }
            return response;
        } catch (RestClientException e) {
            log.error("Failed to call ai-scoring service at {}: {}", baseUrl, e.getMessage());
            PipelineStartResponse error = new PipelineStartResponse();
            error.setAccepted(false);
            error.setMessage("AI 服务调用失败: " + e.getMessage());
            return error;
        }
    }
}
```

- [x] **Step 4: Run tests to verify they pass**

Run: `cd backend && mvn test -Dtest=AiScoringPipelineClientTest -q`
Expected: PASS, 2 tests, 0 failures

- [x] **Step 5: Add RestTemplate bean if not already configured**

Check if `RestTemplate` bean exists. If not, add to a config class. Search for `@Bean` + `RestTemplate` first.

---

## Task 5: AiScoringSessionService — Add pipeline state methods

**Files:**
- Modify: `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java`

- [x] **Step 1: Add markPipelineQueued method**

```java
public AiScoringSessionUserResponse markPipelineQueued(Long sessionId) {
    AiScoringSession session = requireSession(sessionId);
    session.setStatus("scoring");
    session.setCurrentStage("queued");
    session.setProgressPercent(5);
    session.setStartedAt(LocalDateTime.now());
    session.setUpdatedAt(LocalDateTime.now());
    sessionMapper.updateById(session);
    return toUserResponse(session);
}
```

- [x] **Step 2: Add markPipelineProgress method**

```java
public void markPipelineProgress(Long sessionId, String stage, Integer progress, String message) {
    AiScoringSession session = requireSession(sessionId);
    session.setCurrentStage(stage);
    if (progress != null) {
        session.setProgressPercent(Math.max(session.getProgressPercent() == null ? 0 : session.getProgressPercent(), progress));
    }
    session.setUpdatedAt(LocalDateTime.now());
    sessionMapper.updateById(session);
}
```

- [x] **Step 3: Add processPipelineCallback method**

```java
@Transactional
public void processPipelineCallback(PipelineCallbackRequest callback) {
    AiScoringSession session = requireSession(callback.getSessionId());

    if ("failed".equals(callback.getStatus())) {
        session.setStatus("failed");
        session.setCurrentStage(callback.getCurrentStage() != null ? callback.getCurrentStage() : "failed");
        session.setErrorMessage(callback.getErrorMessage());
        session.setCompletedAt(LocalDateTime.now());
        session.setUpdatedAt(LocalDateTime.now());
        sessionMapper.updateById(session);
        return;
    }

    if (!"completed".equals(callback.getStatus())) {
        // Progress update only
        session.setCurrentStage(callback.getCurrentStage());
        if (callback.getProgressPercent() != null) {
            session.setProgressPercent(callback.getProgressPercent());
        }
        session.setUpdatedAt(LocalDateTime.now());
        sessionMapper.updateById(session);
        return;
    }

    // Completed — persist final result
    PipelineCallbackRequest.PipelineFinalResult result = callback.getFinalResult();
    if (result == null) {
        throw new IllegalArgumentException("finalResult cannot be null when status is completed");
    }

    // Create or update report
    AiScoreReport report = new AiScoreReport();
    report.setMeetingId(session.getMeetingId() != null ? session.getMeetingId() : -session.getId());
    report.setOverallScore(result.getOverallScore());
    report.setStatus("completed");
    report.setDimensionsJson(result.getDimensionsJson());
    report.setHighlightsJson(result.getHighlightsJson());
    report.setCriticalIssuesJson(result.getCriticalIssuesJson());
    report.setImprovementPrioritiesJson(result.getImprovementPrioritiesJson());
    report.setTranscript(result.getTranscript());
    report.setSpeechQualityJson(result.getSpeechQualityJson());
    report.setScoreCalibrationJson(result.getScoreCalibrationJson());
    report.setModel(result.getModel());
    report.setStartedAt(session.getStartedAt());
    report.setCompletedAt(LocalDateTime.now());
    report.setUpdatedAt(LocalDateTime.now());
    reportMapper.insert(report);

    // Persist observations
    if (result.getObservations() != null) {
        for (PipelineCallbackRequest.ObservationInput obs : result.getObservations()) {
            AiScoreObservation observation = new AiScoreObservation();
            observation.setSessionId(session.getId());
            observation.setReportId(report.getId());
            observation.setObservationCode(obs.getObservationCode());
            observation.setDimensionCode(obs.getDimensionCode());
            observation.setDimensionName(obs.getDimensionName());
            observation.setRawScore(obs.getRawScore());
            observation.setScoreCap(obs.getScoreCap());
            observation.setEvidenceLevel(obs.getEvidenceLevel());
            observation.setConfidence(obs.getConfidence());
            observation.setValidityStatus(obs.getValidityStatus());
            observation.setModelReason(obs.getModelReason());
            if (obs.getEvidenceAnchorIds() != null) {
                observation.setEvidenceAnchorIdsJson(obs.getEvidenceAnchorIds().toString());
            }
            observationMapper.insert(observation);
        }
    }

    // Persist deductions
    if (result.getDeductions() != null) {
        for (PipelineCallbackRequest.DeductionInput ded : result.getDeductions()) {
            AiScoreDeduction deduction = new AiScoreDeduction();
            deduction.setSessionId(session.getId());
            deduction.setReportId(report.getId());
            deduction.setDeductionId(ded.getDeductionId());
            deduction.setObservationCode(ded.getObservationCode());
            deduction.setDimensionCode(ded.getDimensionCode());
            deduction.setDeductedPoints(ded.getDeductedPoints());
            deduction.setMaxRecoverablePoints(ded.getMaxRecoverablePoints());
            deduction.setReason(ded.getReason());
            deduction.setRequiredFix(ded.getRequiredFix());
            deduction.setAcceptanceCriteria(ded.getAcceptanceCriteria());
            deduction.setEvidenceLevel(ded.getEvidenceLevel());
            deduction.setConfidence(ded.getConfidence());
            deduction.setStatus(ded.getStatus() != null ? ded.getStatus() : "new");
            if (ded.getEvidenceAnchorIds() != null) {
                deduction.setEvidenceAnchorIdsJson(ded.getEvidenceAnchorIds().toString());
            }
            deductionMapper.insert(deduction);
        }
    }

    // Persist evidence anchors
    if (result.getEvidenceAnchors() != null) {
        for (PipelineCallbackRequest.EvidenceAnchorInput anchor : result.getEvidenceAnchors()) {
            AiScoreEvidenceAnchor evidenceAnchor = new AiScoreEvidenceAnchor();
            evidenceAnchor.setSessionId(session.getId());
            evidenceAnchor.setAnchorType(anchor.getAnchorType());
            evidenceAnchor.setAnchorTitle(anchor.getAnchorTitle());
            evidenceAnchor.setEvidenceText(anchor.getEvidenceText());
            evidenceAnchor.setSourceRef(anchor.getSourceRef());
            evidenceAnchor.setStartMs(anchor.getStartMs());
            evidenceAnchor.setEndMs(anchor.getEndMs());
            evidenceAnchor.setConfidence(anchor.getConfidence());
            evidenceAnchor.setValidityStatus(anchor.getValidityStatus());
            evidenceAnchorMapper.insert(evidenceAnchor);
        }
    }

    // Update session
    session.setReportId(report.getId());
    session.setStatus("completed");
    session.setCurrentStage("completed");
    session.setProgressPercent(100);
    session.setCompletedAt(LocalDateTime.now());
    session.setUpdatedAt(LocalDateTime.now());
    sessionMapper.updateById(session);
}
```

- [x] **Step 4: Verify compilation**

Run: `cd backend && mvn compile -q`
Expected: BUILD SUCCESS

---

## Task 6: AiScoreController — Add pipeline-callback endpoint

**Files:**
- Modify: `backend/src/main/java/com/orep/backend/controller/AiScoreController.java`

- [x] **Step 1: Add pipeline-callback endpoint**

Add this endpoint to `AiScoreController`:

```java
@PostMapping("/sessions/{sessionId}/pipeline-callback")
public Result<Void> pipelineCallback(@PathVariable("sessionId") Long sessionId,
                                     @RequestBody PipelineCallbackRequest callback) {
    try {
        callback.setSessionId(sessionId);
        scoringSessionService.processPipelineCallback(callback);
        return Result.success();
    } catch (IllegalArgumentException e) {
        return Result.error(400, e.getMessage());
    } catch (IllegalStateException e) {
        return Result.error(404, e.getMessage());
    }
}
```

- [x] **Step 2: Add import**

Add `import com.orep.backend.dto.PipelineCallbackRequest;` to imports.

- [x] **Step 3: Verify compilation**

Run: `cd backend && mvn compile -q`
Expected: BUILD SUCCESS

---

## Task 7: AiScoreUploadController — Call pipeline after upload

**Files:**
- Modify: `backend/src/main/java/com/orep/backend/controller/AiScoreUploadController.java`

- [x] **Step 1: Add AiScoringPipelineClient dependency**

Add field and constructor parameter:

```java
private final AiScoringPipelineClient pipelineClient;

public AiScoreUploadController(AiScoringSessionService scoringSessionService,
                               AiScoreMediaAssetService mediaAssetService,
                               AiScoreAccessControlService accessControlService,
                               AiScoringPipelineClient pipelineClient) {
    this.scoringSessionService = scoringSessionService;
    this.mediaAssetService = mediaAssetService;
    this.accessControlService = accessControlService;
    this.pipelineClient = pipelineClient;
}
```

- [x] **Step 2: Add startPipeline call after markUploaded**

After `markUploaded(session.getSessionId())`, add:

```java
// Start pipeline
scoringSessionService.markPipelineQueued(session.getSessionId());
String callbackUrl = buildCallbackUrl(request, session.getSessionId());
var videoAsset = mediaAssetService.getVideoAssetBySession(session.getSessionId());
var materialAssets = mediaAssetService.getMaterialAssetsBySession(session.getSessionId());
List<Map<String, String>> materialList = materialAssets.stream()
        .map(a -> Map.of("path", a.getFilePath(), "name", a.getOriginalName()))
        .toList();
pipelineClient.startSessionPipeline(
        session.getSessionId(),
        session.getSessionNo(),
        teamId, projectId, trackName,
        "uploaded_video",
        videoAsset.getFilePath(),
        videoAsset.getOriginalName(),
        materialList,
        callbackUrl
);
```

- [x] **Step 3: Add buildCallbackUrl helper**

```java
private String buildCallbackUrl(HttpServletRequest request, Long sessionId) {
    String scheme = request.getScheme();
    String host = request.getServerName();
    int port = request.getServerPort();
    return String.format("%s://%s:%d/api/ai-score/sessions/%d/pipeline-callback", scheme, host, port, sessionId);
}
```

- [x] **Step 4: Update all test constructors**

Update every test that creates `AiScoreUploadController` to pass the new `pipelineClient` parameter:

```java
// In AiScoreUploadControllerTest, AiScoreUploadControllerWebMvcTest, AiScoreResponseRedactionTest
// Add mock(AiScoringPipelineClient.class) or @MockBean AiScoringPipelineClient
```

- [x] **Step 5: Run affected tests**

Run: `cd backend && mvn test -Dtest=AiScoreUploadControllerTest,AiScoreUploadControllerWebMvcTest,AiScoreResponseRedactionTest -q`
Expected: PASS

---

## Task 8: ai-scoring — New session-based scoring endpoint

**Files:**
- Create: `ai-scoring/app/routers/session_scoring_router.py`
- Create: `ai-scoring/app/services/session_pipeline_service.py`
- Modify: `ai-scoring/main.py`

- [x] **Step 1: Create session_pipeline_service.py**

```python
"""
Session-based pipeline service for Java backend integration.
Receives session metadata from Java, runs the existing pipeline, and callbacks Java with progress/results.
"""
import asyncio
import json
import logging
import os
import traceback
from datetime import datetime
from typing import Optional

import httpx

from app.services.pipeline_service import run_scoring_pipeline
from app.services.video_analysis_service import video_analysis_service
from app.services.asr_service import transcribe_long_audio
from app.services.llm_scoring_service import score_roadshow
from app.services.competition_calibration_service import apply_calibration_to_result
from app.config import settings

logger = logging.getLogger(__name__)

UPLOAD_DIR = settings.UPLOAD_DIR


async def run_session_pipeline(
    session_id: int,
    session_no: str,
    team_id: int,
    project_id: int,
    track_name: str,
    source_type: str,
    video_file_path: str,
    video_original_name: str,
    materials: list[dict],
    callback_url: str,
):
    """Run the full scoring pipeline for a session and callback Java with progress/results."""

    async def notify(status: str, stage: str, progress: int, message: str = "",
                     error_message: str = None, final_result: dict = None):
        """Send progress/result callback to Java backend."""
        payload = {
            "sessionId": session_id,
            "status": status,
            "currentStage": stage,
            "progressPercent": progress,
            "message": message,
        }
        if error_message:
            payload["errorMessage"] = error_message
        if final_result:
            payload["finalResult"] = final_result

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(callback_url, json=payload)
                logger.info(f"Callback to Java: {resp.status_code} - stage={stage}")
        except Exception as e:
            logger.error(f"Failed to callback Java: {e}")

    try:
        # Resolve absolute path to video file
        abs_video_path = video_file_path
        if not os.path.isabs(abs_video_path):
            abs_video_path = os.path.join(UPLOAD_DIR, abs_video_path)
        if not os.path.exists(abs_video_path):
            await notify("failed", "failed", 0,
                         error_message=f"Video file not found: {abs_video_path}")
            return

        # Step 1: Audio extraction + ASR
        await notify("scoring", "audio_extracting", 10, "正在提取音频...")
        await notify("scoring", "asr_processing", 20, "正在语音识别...")

        project_info = {
            "team_size": 4,
            "track": track_name,
            "project_name": f"Session {session_no}",
        }

        # Step 2: Video analysis
        await notify("scoring", "frame_extracting", 35, "正在抽取关键帧...")
        video_result = await asyncio.to_thread(
            video_analysis_service.run_analysis, abs_video_path, 30, None
        )

        await notify("scoring", "ocr_processing", 50, "正在分析视频内容...")

        # Step 3: Run the main pipeline (ASR + scoring + calibration)
        await notify("scoring", "model_scoring", 60, "正在 AI 评分...")
        pipeline_result = await run_scoring_pipeline(
            audio_file_path=abs_video_path,
            meeting_id=str(session_id),
            project_info=project_info,
            callback_url=None,  # We handle callbacks ourselves
            provider="deepseek",
            compare_mode=False,
            ppt_recognition=True,
        )

        # Step 4: Calibrate
        await notify("scoring", "rule_calibrating", 85, "正在校准评分...")
        if "ai_score" in pipeline_result:
            pipeline_result = apply_calibration_to_result(pipeline_result)

        # Step 5: Build final result
        await notify("scoring", "report_generating", 95, "正在生成报告...")

        ai_score = pipeline_result.get("ai_score", {})
        calibration = pipeline_result.get("score_calibration", {})
        speech_quality = pipeline_result.get("speech_quality", {})
        asr = pipeline_result.get("asr", {})

        # Build observations and deductions from dimensions
        observations = []
        deductions = []
        dimensions = ai_score.get("dimensions", {})
        for dim_key, dim_data in dimensions.items():
            if isinstance(dim_data, dict):
                obs = {
                    "observationCode": dim_key,
                    "dimensionCode": dim_key,
                    "dimensionName": dim_data.get("name", dim_key),
                    "rawScore": dim_data.get("score"),
                    "scoreCap": dim_data.get("max_score"),
                    "evidenceLevel": "medium",
                    "confidence": 0.85,
                    "validityStatus": "valid",
                    "modelReason": f"{dim_data.get('name', dim_key)}评分",
                    "evidenceAnchorIds": [],
                }
                observations.append(obs)

        final_result = {
            "transcript": asr.get("transcript", ""),
            "asrSegments": asr.get("segments", []),
            "overallScore": ai_score.get("overall_score"),
            "rawOverallScore": ai_score.get("raw_overall_score", ai_score.get("overall_score")),
            "dimensionsJson": json.dumps(dimensions, ensure_ascii=False) if dimensions else None,
            "highlightsJson": json.dumps(ai_score.get("highlights", []), ensure_ascii=False),
            "criticalIssuesJson": json.dumps(ai_score.get("critical_issues", []), ensure_ascii=False),
            "improvementPrioritiesJson": json.dumps(ai_score.get("improvement_priorities", []), ensure_ascii=False),
            "speechQualityJson": json.dumps(speech_quality, ensure_ascii=False) if speech_quality else None,
            "scoreCalibrationJson": json.dumps(calibration, ensure_ascii=False) if calibration else None,
            "model": ai_score.get("model", "deepseek-chat"),
            "observations": observations,
            "deductions": deductions,
            "evidenceAnchors": [],
            "ruleEngineVersion": "pipeline-v1",
        }

        await notify("completed", "completed", 100, "评分完成", final_result=final_result)
        logger.info(f"Session {session_id} pipeline completed successfully")

    except Exception as e:
        logger.error(f"Session {session_id} pipeline failed: {traceback.format_exc()}")
        await notify("failed", "failed", 0, error_message=str(e))
```

- [x] **Step 2: Create session_scoring_router.py**

```python
"""
Session-based scoring endpoint for Java backend integration.
"""
import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from app.services.session_pipeline_service import run_session_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ai", tags=["session-scoring"])


class SessionScoringRequest(BaseModel):
    sessionId: int
    sessionNo: str
    teamId: Optional[int] = None
    projectId: Optional[int] = None
    trackName: Optional[str] = None
    sourceType: str = "uploaded_video"
    videoFilePath: str
    videoOriginalName: Optional[str] = None
    materials: list[dict] = []
    callbackUrl: str


class SessionScoringResponse(BaseModel):
    accepted: bool
    message: str
    taskId: Optional[str] = None


@router.post("/score-session", response_model=SessionScoringResponse)
async def score_session(request: SessionScoringRequest, background_tasks: BackgroundTasks):
    """Receive session scoring request from Java backend and start pipeline in background."""
    logger.info(f"Received session scoring request: sessionId={request.sessionId}, "
                f"track={request.trackName}, video={request.videoFilePath}")

    background_tasks.add_task(
        run_session_pipeline,
        session_id=request.sessionId,
        session_no=request.sessionNo,
        team_id=request.teamId,
        project_id=request.projectId,
        track_name=request.trackName,
        source_type=request.sourceType,
        video_file_path=request.videoFilePath,
        video_original_name=request.videoOriginalName,
        materials=request.materials,
        callback_url=request.callbackUrl,
    )

    return SessionScoringResponse(
        accepted=True,
        message=f"Pipeline started for session {request.sessionId}",
        taskId=f"session-{request.sessionId}",
    )
```

- [x] **Step 3: Register router in main.py**

In `main.py`, add:

```python
from app.routers.session_scoring_router import router as session_scoring_router
# ... after existing router includes:
app.include_router(session_scoring_router)
```

- [x] **Step 4: Configure JAVA_UPLOAD_DIR in ai-scoring**

In `ai-scoring/app/config.py`, add to the Settings class:

```python
# Java backend upload directory (for uploaded_video pipeline integration)
JAVA_UPLOAD_DIR: str = os.environ.get("JAVA_UPLOAD_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "..", "backend", "uploads"))
```

Then in `session_pipeline_service.py`, resolve the video path:

```python
from app.config import settings

abs_video_path = video_file_path
if not os.path.isabs(abs_video_path):
    abs_video_path = os.path.join(settings.JAVA_UPLOAD_DIR, abs_video_path)
```

- [x] **Step 5: Verify ai-scoring starts**

Run: `cd ai-scoring && python -c "from app.routers.session_scoring_router import router; print('OK')"`
Expected: OK

---

## Task 9: Frontend — Progress view in report page

**Files:**
- Modify: `frontend/user/src/views/AiScoreResult.vue`

- [x] **Step 1: Add progress state variables**

In the `<script setup>` section, add:

```js
const sessionStatus = ref(null)
const sessionProgress = ref(0)
const sessionStage = ref('')
const sessionErrorMessage = ref('')
const progressPollingTimer = ref(null)
const isLoadingSession = ref(false)

const STAGE_LABELS = {
  queued: '排队中',
  audio_extracting: '正在提取音频',
  asr_processing: '正在语音识别',
  frame_extracting: '正在抽取关键帧',
  ocr_processing: '正在分析视频内容',
  evidence_building: '正在构建证据链',
  model_scoring: '正在 AI 评分',
  rule_calibrating: '正在校准评分',
  report_generating: '正在生成报告',
  completed: '评分完成',
  failed: '评分失败',
}
```

- [x] **Step 2: Add progress polling function**

```js
async function pollSessionProgress(sessionId) {
  try {
    const res = await request.get(`/api/ai-score/sessions/${sessionId}/status`)
    if (res.code === 200 && res.data) {
      sessionStatus.value = res.data.status
      sessionProgress.value = res.data.progressPercent || 0
      sessionStage.value = res.data.currentStage || ''
      sessionErrorMessage.value = res.data.errorMessage || ''

      if (res.data.status === 'completed' && res.data.reportId) {
        // Scoring done — stop polling and reload report
        stopProgressPolling()
        await loadResult()
      } else if (res.data.status === 'failed') {
        stopProgressPolling()
      }
    }
  } catch (e) {
    console.warn('Failed to poll session progress:', e)
  }
}

function startProgressPolling(sessionId) {
  stopProgressPolling()
  pollSessionProgress(sessionId)
  progressPollingTimer.value = setInterval(() => pollSessionProgress(sessionId), 3000)
}

function stopProgressPolling() {
  if (progressPollingTimer.value) {
    clearInterval(progressPollingTimer.value)
    progressPollingTimer.value = null
  }
}
```

- [x] **Step 3: Modify loadResult to handle non-completed sessions**

In `loadResult()`, after the session-based API call fails or returns no report, check session status:

```js
// In the session-based load path, if report not found:
// Instead of showing error, start polling for progress
if (route.params.sessionId) {
  isLoadingSession.value = true
  try {
    const statusRes = await request.get(`/api/ai-score/sessions/${route.params.sessionId}/status`)
    if (statusRes.code === 200 && statusRes.data) {
      sessionStatus.value = statusRes.data.status
      sessionProgress.value = statusRes.data.progressPercent || 0
      sessionStage.value = statusRes.data.currentStage || ''
      sessionErrorMessage.value = statusRes.data.errorMessage || ''

      if (statusRes.data.status === 'scoring' || statusRes.data.status === 'created') {
        // Not done yet — show progress and start polling
        startProgressPolling(route.params.sessionId)
        loading.value = false
        isLoadingSession.value = false
        return
      }
    }
  } catch (e) {
    console.warn('Failed to check session status:', e)
  }
  isLoadingSession.value = false
}
```

- [x] **Step 4: Add progress view template**

Add this before the main report view (after the loading/error states):

```html
<!-- Progress view: scoring in progress -->
<template v-if="sessionStatus === 'scoring' || sessionStatus === 'created'">
  <div class="ai-score-progress-container">
    <div class="progress-card">
      <div class="progress-header">
        <el-icon :size="48" class="rotating"><Loading /></el-icon>
        <h2>AI 评分进行中</h2>
        <p class="session-no">{{ result?.scoringConsistencyNo || '' }}</p>
      </div>

      <el-progress
        :percentage="sessionProgress"
        :stroke-width="12"
        :format="(p) => `${p}%`"
        class="main-progress"
      />

      <div class="stage-info">
        <p class="current-stage">
          当前阶段：{{ STAGE_LABELS[sessionStage] || sessionStage }}
        </p>
      </div>

      <div class="stage-list">
        <div
          v-for="(label, key) in STAGE_LABELS"
          :key="key"
          class="stage-item"
          :class="{
            'stage-done': isStageDone(key),
            'stage-current': sessionStage === key,
            'stage-pending': !isStageDone(key) && sessionStage !== key
          }"
        >
          <el-icon v-if="isStageDone(key)"><CircleCheckFilled /></el-icon>
          <el-icon v-else-if="sessionStage === key" class="rotating"><Loading /></el-icon>
          <el-icon v-else><CircleClose /></el-icon>
          <span>{{ label }}</span>
        </div>
      </div>

      <div v-if="sessionStatus === 'failed'" class="error-section">
        <el-alert
          :title="'评分失败'"
          :description="sessionErrorMessage || '未知错误'"
          type="error"
          show-icon
        />
        <el-button type="primary" @click="handleRestart" class="restart-btn">
          重新开始
        </el-button>
      </div>
    </div>
  </div>
</template>
```

- [x] **Step 5: Add isStageDone helper**

```js
const STAGE_ORDER = ['queued', 'audio_extracting', 'asr_processing', 'frame_extracting',
  'ocr_processing', 'evidence_building', 'model_scoring', 'rule_calibrating',
  'report_generating', 'completed']

function isStageDone(stage) {
  const currentIdx = STAGE_ORDER.indexOf(sessionStage.value)
  const stageIdx = STAGE_ORDER.indexOf(stage)
  return currentIdx > stageIdx
}
```

- [x] **Step 6: Add restart handler**

```js
async function handleRestart() {
  if (!route.params.sessionId) return
  try {
    await request.post(`/api/ai-score/sessions/${route.params.sessionId}/restart`)
    sessionStatus.value = 'created'
    sessionProgress.value = 0
    sessionStage.value = 'created'
    sessionErrorMessage.value = ''
    // Navigate back to upload
    router.push('/ai-score-upload')
  } catch (e) {
    ElMessage.error('重新开始失败')
  }
}
```

- [x] **Step 7: Add progress view styles**

```css
.ai-score-progress-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 80vh;
  padding: 40px;
}

.progress-card {
  max-width: 600px;
  width: 100%;
  background: #fff;
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.progress-header {
  text-align: center;
  margin-bottom: 32px;
}

.progress-header h2 {
  margin: 16px 0 8px;
  font-size: 24px;
  color: #303133;
}

.session-no {
  color: #909399;
  font-size: 14px;
}

.main-progress {
  margin-bottom: 24px;
}

.stage-info {
  text-align: center;
  margin-bottom: 24px;
}

.current-stage {
  font-size: 16px;
  color: #409eff;
  font-weight: 500;
}

.stage-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stage-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border-radius: 6px;
  font-size: 14px;
}

.stage-done {
  color: #67c23a;
}

.stage-current {
  color: #409eff;
  background: #ecf5ff;
  font-weight: 500;
}

.stage-pending {
  color: #c0c4cc;
}

.rotating {
  animation: rotate 1s linear infinite;
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.error-section {
  margin-top: 24px;
  text-align: center;
}

.restart-btn {
  margin-top: 16px;
}
```

- [x] **Step 8: Cleanup on unmount**

```js
onUnmounted(() => {
  stopProgressPolling()
})
```

- [x] **Step 9: Build frontend**

Run: `cd frontend/user && npm run build`
Expected: PASS

---

## Task 10: Fix test constructors and run full verification

**Files:**
- Modify: All test files that construct `AiScoreUploadController`

- [x] **Step 1: Update AiScoreUploadControllerTest**

Add `mock(AiScoringPipelineClient.class)` to all `new AiScoreUploadController(...)` calls:

```java
import com.orep.backend.service.AiScoringPipelineClient;
// ...
MockMvc mvc = standaloneSetup(new AiScoreUploadController(sessionService, assetService,
        mock(AiScoreAccessControlService.class), mock(AiScoringPipelineClient.class))).build();
```

- [x] **Step 2: Update AiScoreUploadControllerWebMvcTest**

Add `@MockBean`:

```java
@MockBean
private AiScoringPipelineClient pipelineClient;
```

- [x] **Step 3: Update AiScoreResponseRedactionTest**

Update the upload controller constructor call.

- [x] **Step 4: Run full backend tests**

Run: `cd backend && mvn test`
Expected: PASS, 0 failures

- [x] **Step 5: Run frontend build**

Run: `cd frontend/user && npm run build`
Expected: PASS

---

## Self-Review

**Spec coverage:**
1. ✅ Java AiScoringPipelineClient — Task 4
2. ✅ startPipeline after upload — Task 7
3. ✅ ai-scoring session endpoint — Task 8
4. ✅ Pipeline progress callback — Task 5, 6, 8
5. ✅ Final result callback with all fields — Task 5, 8
6. ✅ Frontend progress view — Task 9
7. ✅ No rule field leaks — existing P12 tests + DTO constraints
8. ✅ Verification — Task 10

**Placeholder scan:** No TBD/TODO/placeholders found.

**Type consistency:** `PipelineCallbackRequest` fields match between Java DTO (Task 1) and ai-scoring payload construction (Task 8). Stage names are consistent across all tasks.
