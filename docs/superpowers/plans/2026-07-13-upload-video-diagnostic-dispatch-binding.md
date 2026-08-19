# Upload Video Diagnostic Dispatch Binding Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow the current upload-video user flow to start a diagnostic Python scoring run with the resolved track rule, while preserving the official-publication gate and reporting dispatch errors accurately.

**Architecture:** Java remains the owner of the resolved track rubric and constructs an internal-only `competitionBinding` for Python. The current phase always dispatches uploaded-video sessions with `diagnostic_override` and `publishOfficialScore=false`; Python keeps enforcing the existing gate. Backend error formatting distinguishes business rejection from transport failure.

**Tech Stack:** Java 17, Spring Boot, RestTemplate, JUnit 5, Spring MockRestServiceServer, FastAPI/Pydantic, pytest.

---

### Task 1: Internal pipeline dispatch payload

**Files:**
- Modify: `backend/src/main/java/com/orep/backend/service/AiScoringPipelineClient.java`
- Modify: `backend/src/test/java/com/orep/backend/service/AiScoringPipelineClientTest.java`

- [ ] **Step 1: Write the failing request-contract test**

Add a MockRestServiceServer expectation that parses the request body and asserts:

```java
assertThat(json.path("trackId").asText()).isEqualTo("track-it");
assertThat(json.path("publishOfficialScore").asBoolean()).isFalse();
assertThat(json.path("competitionBinding.selectionSource").asText()).isEqualTo("diagnostic_override");
assertThat(json.path("competitionBinding.ruleVersion").asText()).isEqualTo("v1.2");
assertThat(json.path("competitionBinding.ruleHash").asText()).isEqualTo("sha256:test");
```

- [ ] **Step 2: Run the focused test and verify RED**

Run:

```bash
cd backend
./mvnw -Dtest=AiScoringPipelineClientTest test
```

Expected: compilation failure or request assertion failure because the client does not accept/send the binding fields.

- [ ] **Step 3: Extend the internal client contract**

Change `startSessionPipeline` to accept `trackId`, `ruleVersion`, and `ruleHash`. Send:

```java
body.put("trackId", trackId);
body.put("publishOfficialScore", false);
body.put("competitionBinding", Map.of(
        "trackId", trackId,
        "trackName", trackName,
        "ruleVersion", ruleVersion,
        "ruleHash", ruleHash,
        "selectionSource", "diagnostic_override"
));
```

Validate the four required diagnostic fields before making the HTTP call; return `accepted=false` with `track_confirmation_required` when an internal binding is incomplete.

- [ ] **Step 4: Run the focused test and verify GREEN**

Run the command from Step 2. Expected: all `AiScoringPipelineClientTest` tests pass.

### Task 2: Dispatch resolved session metadata

**Files:**
- Modify: `backend/src/main/java/com/orep/backend/dto/AiScoringSessionUserResponse.java`
- Modify: `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java`
- Modify: `backend/src/main/java/com/orep/backend/controller/AiScoreUploadController.java`
- Modify: `backend/src/test/java/com/orep/backend/controller/AiScoreUploadControllerTest.java`

- [ ] **Step 1: Write the failing controller test**

Capture the arguments passed to `startSessionPipeline` and assert that the controller uses the resolved session values rather than raw form values:

```java
verify(pipelineClient).startSessionPipeline(
        eq(123L), anyString(), any(), any(),
        eq("track-it"), eq("新一代信息技术赛道"),
        eq("v1.2"), eq("sha256:test"),
        eq("uploaded_video"), anyString(), anyString(), anyList(), anyString()
);
```

- [ ] **Step 2: Run the controller test and verify RED**

Run:

```bash
cd backend
./mvnw -Dtest=AiScoreUploadControllerTest test
```

Expected: compilation or verification failure because the resolved internal values are not currently available/passed.

- [ ] **Step 3: Expose resolved metadata internally only**

Add `trackId`, `rubricHash`, and `internalVersion` to `AiScoringSessionUserResponse` with `@JsonIgnore`. Populate them in `AiScoringSessionService.toUserResponse`.

Update `AiScoreUploadController` to dispatch `queuedSession.getTrackId()`, `queuedSession.getTrackName()`, `queuedSession.getInternalVersion()`, and `queuedSession.getRubricHash()`.

- [ ] **Step 4: Run the controller test and verify GREEN**

Run the command from Step 2. Expected: controller tests pass and response JSON still excludes internal fields.

### Task 3: Accurate dispatch failure messages

**Files:**
- Modify: `backend/src/main/java/com/orep/backend/controller/AiScoreUploadController.java`
- Modify: `backend/src/test/java/com/orep/backend/controller/AiScoreUploadControllerTest.java`

- [ ] **Step 1: Write failing message-classification tests**

Cover:

```java
track_confirmation_required -> "AI分析未启动：评分绑定信息不完整"
AI 服务调用失败 -> "AI分析未启动：AI 服务连接失败"
other rejection -> "AI分析未启动：任务派发失败"
```

- [ ] **Step 2: Run the controller tests and verify RED**

Expected: current generic message fails the new expectations.

- [ ] **Step 3: Implement exact classification**

Make `dispatchFailureMessage` branch on the normalized reason while retaining the original service reason in parentheses for audit.

- [ ] **Step 4: Run the controller tests and verify GREEN**

Expected: all focused controller tests pass.

### Task 4: Cross-service contract and existing-session redispatch

**Files:**
- Test: `ai-scoring/tests/test_track_binding_gate.py`
- Runtime verification only: session 25 and existing uploaded media asset

- [ ] **Step 1: Add/confirm the Python contract test**

Create a `SessionScoringRequest` with the exact Java diagnostic binding and assert `accepted=true`, one background task, normalized diagnostic binding, and `publishOfficialScore=false`.

- [ ] **Step 2: Run the Python test and verify behavior**

Run:

```bash
cd ai-scoring
./.venv/bin/python -m pytest tests/test_track_binding_gate.py -q
```

- [ ] **Step 3: Run backend focused and broad tests**

Run:

```bash
cd backend
./mvnw -Dtest=AiScoringPipelineClientTest,AiScoreUploadControllerTest test
./mvnw test
```

- [ ] **Step 4: Build the user frontend**

Run:

```bash
cd frontend/user
npm run build
```

- [ ] **Step 5: Restart backend if required and redispatch session 25**

Use the already stored video asset for session 25. Verify Python returns `accepted=true`, the Java session leaves `pipeline_dispatch_failed`, and the task reaches `queued` or a later scoring stage without a second browser upload.

## Self-review

- The plan preserves the official track-confirmation gate; it does not synthesize competition or group values.
- Rule version and hash cross only the internal Java-to-Python boundary and remain hidden from user JSON.
- The test sequence proves request shape, controller source-of-truth, error classification, Python acceptance, and end-to-end redispatch.
- No changes to the 42 track rules or scoring formulas are included.
