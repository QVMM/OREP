# OREP AI Scoring P6 Evidence Bundle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将上传视频、会议录制、正式转写、关键帧、OCR 和材料识别结果固化为可复现的 `evidence_bundle`，让后续评分不再引用易漂移的实时转写或默认片段。

**Architecture:** P6 只建设证据地基，不启动真实 ASR/OCR/抽帧大模型。后端新增 transcript/frame/ocr/evidence bundle 的结构化表、实体、Mapper 与服务，先用确定性模拟抽取器从媒体资产生成稳定快照和 hash；前端报告页增加“证据准备状态”面板，展示 session 当前证据状态和 anchor 数量，不展示内部规则或 prompt。

**Tech Stack:** Spring Boot 3 + MyBatis Plus + MySQL/H2 tests；Vue 3 + Vite；现有 `ai_scoring_session`、`ai_score_media_asset`、`ai_score_evidence_snapshot`、`ScoreEvidenceAnchorStore`、`RecordingEvidenceAnchorBuilder`。

---

## 0. Scope

本计划只做 P6：

- 建立正式评分证据模型。
- 从 `ai_score_media_asset` 生成稳定的 mock ASR/OCR/frame 快照。
- 更新 `ai_score_evidence_snapshot` hash。
- 为报告页提供 evidence bundle 状态接口。
- 修复“所有扣分都指向同一个转写片段”的底层锚点能力。

本计划不做：

- 不接真实 Whisper/ASR 服务。
- 不接真实 OCR 模型。
- 不接 ffmpeg/ffprobe。
- 不接 P7 赛道 schema。
- 不接 P8 规则引擎算分。

---

## 1. File Structure

### Backend Files

- Create: `backend/src/main/java/com/orep/backend/entity/AiScoreTranscriptSegment.java`
  - Stores fixed ASR transcript segments for a scoring session.
- Create: `backend/src/main/java/com/orep/backend/entity/AiScoreFrame.java`
  - Stores deterministic key-frame records and optional OCR text.
- Create: `backend/src/main/java/com/orep/backend/entity/AiScoreEvidenceAnchor.java`
  - Stores normalized anchors linked to transcript segments, frames, OCR, recording playback, or material assets.
- Create: `backend/src/main/java/com/orep/backend/mapper/AiScoreTranscriptSegmentMapper.java`
- Create: `backend/src/main/java/com/orep/backend/mapper/AiScoreFrameMapper.java`
- Create: `backend/src/main/java/com/orep/backend/mapper/AiScoreEvidenceAnchorMapper.java`
- Create: `backend/src/main/java/com/orep/backend/dto/AiScoreEvidenceBundleResponse.java`
  - User-safe response for evidence status.
- Create: `backend/src/main/java/com/orep/backend/service/AiScoreEvidenceBundleService.java`
  - Creates deterministic evidence bundle from media assets.
- Modify: `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java`
  - Add status transition helpers for evidence stages.
- Modify: `backend/src/main/java/com/orep/backend/controller/AiScoreController.java`
  - Add `POST /api/ai-score/sessions/{sessionId}/prepare-evidence` and `GET /api/ai-score/sessions/{sessionId}/evidence-bundle`.
- Modify: `backend/src/main/resources/sql/create_ai_scoring_session_tables.sql`
  - Add evidence tables.
- Modify: `dockerrun/sql/backend-resources/create_ai_scoring_session_tables.sql`
  - Mirror SQL.
- Test: `backend/src/test/java/com/orep/backend/service/AiScoreEvidenceBundleServiceTest.java`
- Test: `backend/src/test/java/com/orep/backend/controller/AiScoreEvidenceBundleControllerTest.java`

### Frontend Files

- Create: `frontend/user/src/utils/aiScoreEvidence.js`
  - Calls evidence prepare/status APIs.
- Create: `frontend/user/src/components/ai-score/EvidenceBundlePanel.vue`
  - Shows evidence state in report page.
- Modify: `frontend/user/src/views/AiScoreResult.vue`
  - Load and display evidence bundle status by sessionId.

---

## 2. Data Model

### Tables

Append the following SQL to both:

- `backend/src/main/resources/sql/create_ai_scoring_session_tables.sql`
- `dockerrun/sql/backend-resources/create_ai_scoring_session_tables.sql`

```sql
CREATE TABLE IF NOT EXISTS ai_score_transcript_segment (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id BIGINT NOT NULL,
  media_asset_id BIGINT NULL,
  segment_no INT NOT NULL,
  speaker_label VARCHAR(128) NULL,
  start_ms BIGINT NOT NULL,
  end_ms BIGINT NOT NULL,
  text TEXT NOT NULL,
  source_type VARCHAR(32) NOT NULL,
  confidence DECIMAL(5,4) NULL,
  segment_hash VARCHAR(128) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_transcript_segment_session_no (session_id, segment_no),
  INDEX idx_transcript_segment_session (session_id),
  INDEX idx_transcript_segment_hash (segment_hash)
);

CREATE TABLE IF NOT EXISTS ai_score_frame (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id BIGINT NOT NULL,
  media_asset_id BIGINT NULL,
  frame_no INT NOT NULL,
  timestamp_ms BIGINT NOT NULL,
  frame_path VARCHAR(1024) NULL,
  frame_hash VARCHAR(128) NOT NULL,
  perceptual_hash VARCHAR(128) NULL,
  ocr_text TEXT NULL,
  frame_reason VARCHAR(64) NOT NULL,
  confidence DECIMAL(5,4) NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uk_ai_score_frame_session_no (session_id, frame_no),
  INDEX idx_ai_score_frame_session (session_id),
  INDEX idx_ai_score_frame_hash (frame_hash)
);

CREATE TABLE IF NOT EXISTS ai_score_evidence_anchor (
  id BIGINT PRIMARY KEY AUTO_INCREMENT,
  session_id BIGINT NOT NULL,
  anchor_type VARCHAR(64) NOT NULL,
  anchor_title VARCHAR(255) NOT NULL,
  evidence_text TEXT NOT NULL,
  source_ref VARCHAR(512) NULL,
  transcript_segment_id BIGINT NULL,
  frame_id BIGINT NULL,
  media_asset_id BIGINT NULL,
  start_ms BIGINT NULL,
  end_ms BIGINT NULL,
  confidence DECIMAL(5,4) NULL,
  validity_status VARCHAR(32) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_ai_score_evidence_anchor_session (session_id),
  INDEX idx_ai_score_evidence_anchor_type (anchor_type),
  INDEX idx_ai_score_evidence_anchor_segment (transcript_segment_id),
  INDEX idx_ai_score_evidence_anchor_frame (frame_id)
);
```

### Entity Field Names

Use Java camelCase matching MyBatis Plus defaults:

- `sessionId`
- `mediaAssetId`
- `segmentNo`
- `speakerLabel`
- `startMs`
- `endMs`
- `sourceType`
- `segmentHash`
- `frameNo`
- `timestampMs`
- `framePath`
- `frameHash`
- `perceptualHash`
- `ocrText`
- `frameReason`
- `anchorType`
- `anchorTitle`
- `evidenceText`
- `sourceRef`
- `transcriptSegmentId`
- `frameId`
- `validityStatus`

---

## 3. Task P6-A: Add Evidence Bundle Tables And Entities

**Files:**

- Modify: `backend/src/main/resources/sql/create_ai_scoring_session_tables.sql`
- Modify: `dockerrun/sql/backend-resources/create_ai_scoring_session_tables.sql`
- Create: `backend/src/main/java/com/orep/backend/entity/AiScoreTranscriptSegment.java`
- Create: `backend/src/main/java/com/orep/backend/entity/AiScoreFrame.java`
- Create: `backend/src/main/java/com/orep/backend/entity/AiScoreEvidenceAnchor.java`
- Create: `backend/src/main/java/com/orep/backend/mapper/AiScoreTranscriptSegmentMapper.java`
- Create: `backend/src/main/java/com/orep/backend/mapper/AiScoreFrameMapper.java`
- Create: `backend/src/main/java/com/orep/backend/mapper/AiScoreEvidenceAnchorMapper.java`

- [ ] **Step 1: Add entity `AiScoreTranscriptSegment`**

Create `backend/src/main/java/com/orep/backend/entity/AiScoreTranscriptSegment.java`:

```java
package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("ai_score_transcript_segment")
public class AiScoreTranscriptSegment {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long sessionId;
    private Long mediaAssetId;
    private Integer segmentNo;
    private String speakerLabel;
    private Long startMs;
    private Long endMs;
    private String text;
    private String sourceType;
    private BigDecimal confidence;
    private String segmentHash;
    private LocalDateTime createdAt;
}
```

- [ ] **Step 2: Add entity `AiScoreFrame`**

Create `backend/src/main/java/com/orep/backend/entity/AiScoreFrame.java`:

```java
package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("ai_score_frame")
public class AiScoreFrame {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long sessionId;
    private Long mediaAssetId;
    private Integer frameNo;
    private Long timestampMs;
    private String framePath;
    private String frameHash;
    private String perceptualHash;
    private String ocrText;
    private String frameReason;
    private BigDecimal confidence;
    private LocalDateTime createdAt;
}
```

- [ ] **Step 3: Add entity `AiScoreEvidenceAnchor`**

Create `backend/src/main/java/com/orep/backend/entity/AiScoreEvidenceAnchor.java`:

```java
package com.orep.backend.entity;

import com.baomidou.mybatisplus.annotation.IdType;
import com.baomidou.mybatisplus.annotation.TableId;
import com.baomidou.mybatisplus.annotation.TableName;
import lombok.Data;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Data
@TableName("ai_score_evidence_anchor")
public class AiScoreEvidenceAnchor {
    @TableId(type = IdType.AUTO)
    private Long id;
    private Long sessionId;
    private String anchorType;
    private String anchorTitle;
    private String evidenceText;
    private String sourceRef;
    private Long transcriptSegmentId;
    private Long frameId;
    private Long mediaAssetId;
    private Long startMs;
    private Long endMs;
    private BigDecimal confidence;
    private String validityStatus;
    private LocalDateTime createdAt;
}
```

- [ ] **Step 4: Add mappers**

Create `backend/src/main/java/com/orep/backend/mapper/AiScoreTranscriptSegmentMapper.java`:

```java
package com.orep.backend.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.orep.backend.entity.AiScoreTranscriptSegment;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface AiScoreTranscriptSegmentMapper extends BaseMapper<AiScoreTranscriptSegment> {
}
```

Create `backend/src/main/java/com/orep/backend/mapper/AiScoreFrameMapper.java`:

```java
package com.orep.backend.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.orep.backend.entity.AiScoreFrame;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface AiScoreFrameMapper extends BaseMapper<AiScoreFrame> {
}
```

Create `backend/src/main/java/com/orep/backend/mapper/AiScoreEvidenceAnchorMapper.java`:

```java
package com.orep.backend.mapper;

import com.baomidou.mybatisplus.core.mapper.BaseMapper;
import com.orep.backend.entity.AiScoreEvidenceAnchor;
import org.apache.ibatis.annotations.Mapper;

@Mapper
public interface AiScoreEvidenceAnchorMapper extends BaseMapper<AiScoreEvidenceAnchor> {
}
```

- [ ] **Step 5: Run compile**

Run:

```bash
cd backend && mvn test -DskipTests
```

Expected: build success.

---

## 4. Task P6-B: Add Evidence Bundle Service Tests

**Files:**

- Create: `backend/src/test/java/com/orep/backend/service/AiScoreEvidenceBundleServiceTest.java`

- [ ] **Step 1: Write failing tests**

Create `backend/src/test/java/com/orep/backend/service/AiScoreEvidenceBundleServiceTest.java`:

```java
package com.orep.backend.service;

import com.orep.backend.dto.AiScoreEvidenceBundleResponse;
import com.orep.backend.entity.AiScoreEvidenceAnchor;
import com.orep.backend.entity.AiScoreEvidenceSnapshot;
import com.orep.backend.entity.AiScoreFrame;
import com.orep.backend.entity.AiScoreMediaAsset;
import com.orep.backend.entity.AiScoreTranscriptSegment;
import com.orep.backend.mapper.AiScoreEvidenceAnchorMapper;
import com.orep.backend.mapper.AiScoreEvidenceSnapshotMapper;
import com.orep.backend.mapper.AiScoreFrameMapper;
import com.orep.backend.mapper.AiScoreMediaAssetMapper;
import com.orep.backend.mapper.AiScoreTranscriptSegmentMapper;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.util.List;

import static org.junit.jupiter.api.Assertions.*;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.*;

class AiScoreEvidenceBundleServiceTest {

    @Test
    void prepareEvidenceCreatesStableTranscriptFramesAnchorsAndSnapshotHashes() {
        AiScoreMediaAssetMapper mediaMapper = mock(AiScoreMediaAssetMapper.class);
        AiScoreTranscriptSegmentMapper segmentMapper = mock(AiScoreTranscriptSegmentMapper.class);
        AiScoreFrameMapper frameMapper = mock(AiScoreFrameMapper.class);
        AiScoreEvidenceAnchorMapper anchorMapper = mock(AiScoreEvidenceAnchorMapper.class);
        AiScoreEvidenceSnapshotMapper snapshotMapper = mock(AiScoreEvidenceSnapshotMapper.class);

        AiScoreMediaAsset video = new AiScoreMediaAsset();
        video.setId(11L);
        video.setSessionId(101L);
        video.setAssetType("video");
        video.setSourceType("uploaded_video");
        video.setOriginalName("roadshow.mp4");
        video.setFilePath("uploads/ai-score/101/roadshow.mp4");
        video.setFileHash("hash-video");
        video.setHasAudio(true);
        video.setHasVideo(true);
        video.setStatus("uploaded");

        when(mediaMapper.selectList(any())).thenReturn(List.of(video));
        when(segmentMapper.insert(any())).thenAnswer(invocation -> {
            AiScoreTranscriptSegment value = invocation.getArgument(0);
            value.setId((long) value.getSegmentNo());
            return 1;
        });
        when(frameMapper.insert(any())).thenAnswer(invocation -> {
            AiScoreFrame value = invocation.getArgument(0);
            value.setId((long) value.getFrameNo());
            return 1;
        });
        when(anchorMapper.insert(any())).thenReturn(1);
        when(snapshotMapper.insert(any())).thenAnswer(invocation -> {
            AiScoreEvidenceSnapshot value = invocation.getArgument(0);
            value.setId(901L);
            return 1;
        });

        AiScoreEvidenceBundleService service = new AiScoreEvidenceBundleService(
                mediaMapper, segmentMapper, frameMapper, anchorMapper, snapshotMapper
        );

        AiScoreEvidenceBundleResponse response = service.prepareEvidence(101L);

        assertEquals(101L, response.getSessionId());
        assertEquals("ready", response.getSnapshotStatus());
        assertEquals(3, response.getTranscriptSegmentCount());
        assertEquals(3, response.getFrameCount());
        assertTrue(response.getEvidenceAnchorCount() >= 6);
        assertNotNull(response.getAsrSnapshotHash());
        assertNotNull(response.getFrameSnapshotHash());
        assertNotNull(response.getOcrSnapshotHash());
        assertNotNull(response.getMediaAssetHash());

        ArgumentCaptor<AiScoreEvidenceAnchor> anchorCaptor = ArgumentCaptor.forClass(AiScoreEvidenceAnchor.class);
        verify(anchorMapper, atLeast(6)).insert(anchorCaptor.capture());
        assertTrue(anchorCaptor.getAllValues().stream().anyMatch(anchor -> "transcript_segment".equals(anchor.getAnchorType())));
        assertTrue(anchorCaptor.getAllValues().stream().anyMatch(anchor -> "key_frame".equals(anchor.getAnchorType())));
        assertTrue(anchorCaptor.getAllValues().stream().anyMatch(anchor -> anchor.getTranscriptSegmentId() != null));
        assertTrue(anchorCaptor.getAllValues().stream().anyMatch(anchor -> anchor.getFrameId() != null));

        ArgumentCaptor<AiScoreEvidenceSnapshot> snapshotCaptor = ArgumentCaptor.forClass(AiScoreEvidenceSnapshot.class);
        verify(snapshotMapper).insert(snapshotCaptor.capture());
        assertEquals("ready", snapshotCaptor.getValue().getSnapshotStatus());
        assertEquals(response.getAsrSnapshotHash(), snapshotCaptor.getValue().getAsrSnapshotHash());
    }

    @Test
    void prepareEvidenceRejectsSessionWithoutUploadedMediaAssets() {
        AiScoreMediaAssetMapper mediaMapper = mock(AiScoreMediaAssetMapper.class);
        when(mediaMapper.selectList(any())).thenReturn(List.of());

        AiScoreEvidenceBundleService service = new AiScoreEvidenceBundleService(
                mediaMapper,
                mock(AiScoreTranscriptSegmentMapper.class),
                mock(AiScoreFrameMapper.class),
                mock(AiScoreEvidenceAnchorMapper.class),
                mock(AiScoreEvidenceSnapshotMapper.class)
        );

        IllegalStateException error = assertThrows(IllegalStateException.class, () -> service.prepareEvidence(101L));
        assertTrue(error.getMessage().contains("未找到可用媒体资产"));
    }
}
```

- [ ] **Step 2: Run tests to verify failure**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreEvidenceBundleServiceTest
```

Expected: FAIL because `AiScoreEvidenceBundleService` and `AiScoreEvidenceBundleResponse` do not exist yet.

---

## 5. Task P6-C: Implement Evidence Bundle DTO And Service

**Files:**

- Create: `backend/src/main/java/com/orep/backend/dto/AiScoreEvidenceBundleResponse.java`
- Create: `backend/src/main/java/com/orep/backend/service/AiScoreEvidenceBundleService.java`

- [ ] **Step 1: Add response DTO**

Create `backend/src/main/java/com/orep/backend/dto/AiScoreEvidenceBundleResponse.java`:

```java
package com.orep.backend.dto;

import lombok.Data;

@Data
public class AiScoreEvidenceBundleResponse {
    private Long sessionId;
    private Long snapshotId;
    private String snapshotStatus;
    private Integer mediaAssetCount;
    private Integer transcriptSegmentCount;
    private Integer frameCount;
    private Integer evidenceAnchorCount;
    private String mediaAssetHash;
    private String asrSnapshotHash;
    private String frameSnapshotHash;
    private String ocrSnapshotHash;
    private String materialSnapshotHash;
}
```

- [ ] **Step 2: Add service implementation**

Create `backend/src/main/java/com/orep/backend/service/AiScoreEvidenceBundleService.java`:

```java
package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.orep.backend.dto.AiScoreEvidenceBundleResponse;
import com.orep.backend.entity.AiScoreEvidenceAnchor;
import com.orep.backend.entity.AiScoreEvidenceSnapshot;
import com.orep.backend.entity.AiScoreFrame;
import com.orep.backend.entity.AiScoreMediaAsset;
import com.orep.backend.entity.AiScoreTranscriptSegment;
import com.orep.backend.mapper.AiScoreEvidenceAnchorMapper;
import com.orep.backend.mapper.AiScoreEvidenceSnapshotMapper;
import com.orep.backend.mapper.AiScoreFrameMapper;
import com.orep.backend.mapper.AiScoreMediaAssetMapper;
import com.orep.backend.mapper.AiScoreTranscriptSegmentMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class AiScoreEvidenceBundleService {
    private final AiScoreMediaAssetMapper mediaAssetMapper;
    private final AiScoreTranscriptSegmentMapper transcriptSegmentMapper;
    private final AiScoreFrameMapper frameMapper;
    private final AiScoreEvidenceAnchorMapper evidenceAnchorMapper;
    private final AiScoreEvidenceSnapshotMapper evidenceSnapshotMapper;

    public AiScoreEvidenceBundleService(AiScoreMediaAssetMapper mediaAssetMapper,
                                        AiScoreTranscriptSegmentMapper transcriptSegmentMapper,
                                        AiScoreFrameMapper frameMapper,
                                        AiScoreEvidenceAnchorMapper evidenceAnchorMapper,
                                        AiScoreEvidenceSnapshotMapper evidenceSnapshotMapper) {
        this.mediaAssetMapper = mediaAssetMapper;
        this.transcriptSegmentMapper = transcriptSegmentMapper;
        this.frameMapper = frameMapper;
        this.evidenceAnchorMapper = evidenceAnchorMapper;
        this.evidenceSnapshotMapper = evidenceSnapshotMapper;
    }

    @Transactional
    public AiScoreEvidenceBundleResponse prepareEvidence(Long sessionId) {
        if (sessionId == null || sessionId <= 0) {
            throw new IllegalArgumentException("评分会话无效");
        }
        List<AiScoreMediaAsset> assets = mediaAssetMapper.selectList(new LambdaQueryWrapper<AiScoreMediaAsset>()
                .eq(AiScoreMediaAsset::getSessionId, sessionId)
                .eq(AiScoreMediaAsset::getStatus, "uploaded")
                .orderByAsc(AiScoreMediaAsset::getId));
        if (assets.isEmpty()) {
            throw new IllegalStateException("未找到可用媒体资产");
        }

        List<AiScoreMediaAsset> sortedAssets = assets.stream()
                .sorted(Comparator.comparing(AiScoreMediaAsset::getId, Comparator.nullsLast(Long::compareTo)))
                .toList();
        AiScoreMediaAsset primary = sortedAssets.stream()
                .filter(asset -> Boolean.TRUE.equals(asset.getHasVideo()) || Boolean.TRUE.equals(asset.getHasAudio()))
                .findFirst()
                .orElse(sortedAssets.get(0));

        List<AiScoreTranscriptSegment> segments = buildTranscriptSegments(sessionId, primary);
        List<AiScoreFrame> frames = buildFrames(sessionId, primary);
        List<AiScoreEvidenceAnchor> anchors = buildAnchors(sessionId, primary, segments, frames);

        for (AiScoreTranscriptSegment segment : segments) {
            transcriptSegmentMapper.insert(segment);
        }
        for (AiScoreFrame frame : frames) {
            frameMapper.insert(frame);
        }
        for (AiScoreEvidenceAnchor anchor : anchors) {
            evidenceAnchorMapper.insert(anchor);
        }

        AiScoreEvidenceSnapshot snapshot = new AiScoreEvidenceSnapshot();
        snapshot.setSessionId(sessionId);
        snapshot.setMediaAssetHash(hashValues(sortedAssets.stream().map(AiScoreMediaAsset::getFileHash).toList()));
        snapshot.setAsrSnapshotHash(hashValues(segments.stream().map(AiScoreTranscriptSegment::getSegmentHash).toList()));
        snapshot.setFrameSnapshotHash(hashValues(frames.stream().map(AiScoreFrame::getFrameHash).toList()));
        snapshot.setOcrSnapshotHash(hashValues(frames.stream().map(AiScoreFrame::getOcrText).toList()));
        snapshot.setMaterialSnapshotHash(hashValues(sortedAssets.stream()
                .filter(asset -> "material".equals(asset.getAssetType()))
                .map(AiScoreMediaAsset::getFileHash)
                .toList()));
        snapshot.setSnapshotStatus("ready");
        snapshot.setCreatedAt(LocalDateTime.now());
        evidenceSnapshotMapper.insert(snapshot);

        AiScoreEvidenceBundleResponse response = new AiScoreEvidenceBundleResponse();
        response.setSessionId(sessionId);
        response.setSnapshotId(snapshot.getId());
        response.setSnapshotStatus(snapshot.getSnapshotStatus());
        response.setMediaAssetCount(sortedAssets.size());
        response.setTranscriptSegmentCount(segments.size());
        response.setFrameCount(frames.size());
        response.setEvidenceAnchorCount(anchors.size());
        response.setMediaAssetHash(snapshot.getMediaAssetHash());
        response.setAsrSnapshotHash(snapshot.getAsrSnapshotHash());
        response.setFrameSnapshotHash(snapshot.getFrameSnapshotHash());
        response.setOcrSnapshotHash(snapshot.getOcrSnapshotHash());
        response.setMaterialSnapshotHash(snapshot.getMaterialSnapshotHash());
        return response;
    }

    public AiScoreEvidenceBundleResponse latestBundle(Long sessionId) {
        AiScoreEvidenceSnapshot snapshot = evidenceSnapshotMapper.selectOne(new LambdaQueryWrapper<AiScoreEvidenceSnapshot>()
                .eq(AiScoreEvidenceSnapshot::getSessionId, sessionId)
                .orderByDesc(AiScoreEvidenceSnapshot::getId)
                .last("LIMIT 1"));
        AiScoreEvidenceBundleResponse response = new AiScoreEvidenceBundleResponse();
        response.setSessionId(sessionId);
        if (snapshot == null) {
            response.setSnapshotStatus("missing");
            response.setMediaAssetCount(0);
            response.setTranscriptSegmentCount(0);
            response.setFrameCount(0);
            response.setEvidenceAnchorCount(0);
            return response;
        }
        response.setSnapshotId(snapshot.getId());
        response.setSnapshotStatus(snapshot.getSnapshotStatus());
        response.setMediaAssetHash(snapshot.getMediaAssetHash());
        response.setAsrSnapshotHash(snapshot.getAsrSnapshotHash());
        response.setFrameSnapshotHash(snapshot.getFrameSnapshotHash());
        response.setOcrSnapshotHash(snapshot.getOcrSnapshotHash());
        response.setMaterialSnapshotHash(snapshot.getMaterialSnapshotHash());
        response.setMediaAssetCount(countAssets(sessionId));
        response.setTranscriptSegmentCount(countSegments(sessionId));
        response.setFrameCount(countFrames(sessionId));
        response.setEvidenceAnchorCount(countAnchors(sessionId));
        return response;
    }

    private List<AiScoreTranscriptSegment> buildTranscriptSegments(Long sessionId, AiScoreMediaAsset asset) {
        List<String> texts = List.of(
                "本轮路演已接入正式评分证据快照，后续评分引用该固定转写片段。",
                "团队围绕项目背景、核心方案、现场演示和商业价值进行了说明。",
                "系统已记录该视频的关键时间段，后续 ASR 服务接入后会替换为真实转写。"
        );
        List<AiScoreTranscriptSegment> segments = new ArrayList<>();
        for (int i = 0; i < texts.size(); i++) {
            AiScoreTranscriptSegment segment = new AiScoreTranscriptSegment();
            segment.setSessionId(sessionId);
            segment.setMediaAssetId(asset.getId());
            segment.setSegmentNo(i + 1);
            segment.setSpeakerLabel("speaker_" + (i + 1));
            segment.setStartMs(i * 20_000L);
            segment.setEndMs((i + 1) * 20_000L - 1_000L);
            segment.setText(texts.get(i));
            segment.setSourceType("mock_asr_snapshot");
            segment.setConfidence(new BigDecimal("0.8000"));
            segment.setSegmentHash(sha256(sessionId + "|segment|" + (i + 1) + "|" + texts.get(i)));
            segment.setCreatedAt(LocalDateTime.now());
            segments.add(segment);
        }
        return segments;
    }

    private List<AiScoreFrame> buildFrames(Long sessionId, AiScoreMediaAsset asset) {
        List<Map<String, String>> frameSpecs = List.of(
                Map.of("reason", "fixed_interval", "ocr", "标题页或项目概览画面"),
                Map.of("reason", "demo_candidate", "ocr", "现场演示或系统界面候选画面"),
                Map.of("reason", "risk_review", "ocr", "评分风险复核候选画面")
        );
        List<AiScoreFrame> frames = new ArrayList<>();
        for (int i = 0; i < frameSpecs.size(); i++) {
            Map<String, String> spec = frameSpecs.get(i);
            AiScoreFrame frame = new AiScoreFrame();
            frame.setSessionId(sessionId);
            frame.setMediaAssetId(asset.getId());
            frame.setFrameNo(i + 1);
            frame.setTimestampMs((i + 1) * 15_000L);
            frame.setFramePath(asset.getFilePath() + "#frame-" + (i + 1));
            frame.setFrameHash(sha256(sessionId + "|frame|" + (i + 1) + "|" + asset.getFileHash()));
            frame.setPerceptualHash(sha256("phash|" + sessionId + "|" + (i + 1)).substring(0, 16));
            frame.setOcrText(spec.get("ocr"));
            frame.setFrameReason(spec.get("reason"));
            frame.setConfidence(new BigDecimal("0.7600"));
            frame.setCreatedAt(LocalDateTime.now());
            frames.add(frame);
        }
        return frames;
    }

    private List<AiScoreEvidenceAnchor> buildAnchors(Long sessionId,
                                                     AiScoreMediaAsset asset,
                                                     List<AiScoreTranscriptSegment> segments,
                                                     List<AiScoreFrame> frames) {
        List<AiScoreEvidenceAnchor> anchors = new ArrayList<>();
        for (AiScoreTranscriptSegment segment : segments) {
            AiScoreEvidenceAnchor anchor = baseAnchor(sessionId, "transcript_segment", "正式转写片段", segment.getText());
            anchor.setTranscriptSegmentId(segment.getId());
            anchor.setMediaAssetId(asset.getId());
            anchor.setStartMs(segment.getStartMs());
            anchor.setEndMs(segment.getEndMs());
            anchor.setSourceRef("segment:" + segment.getSegmentNo());
            anchors.add(anchor);
        }
        for (AiScoreFrame frame : frames) {
            AiScoreEvidenceAnchor anchor = baseAnchor(sessionId, "key_frame", "关键帧", frame.getOcrText());
            anchor.setFrameId(frame.getId());
            anchor.setMediaAssetId(asset.getId());
            anchor.setStartMs(frame.getTimestampMs());
            anchor.setEndMs(frame.getTimestampMs());
            anchor.setSourceRef("frame:" + frame.getFrameNo() + "@" + frame.getTimestampMs());
            anchors.add(anchor);
        }
        return anchors;
    }

    private AiScoreEvidenceAnchor baseAnchor(Long sessionId, String type, String title, String text) {
        AiScoreEvidenceAnchor anchor = new AiScoreEvidenceAnchor();
        anchor.setSessionId(sessionId);
        anchor.setAnchorType(type);
        anchor.setAnchorTitle(title);
        anchor.setEvidenceText(text);
        anchor.setConfidence(new BigDecimal("0.8000"));
        anchor.setValidityStatus("valid");
        anchor.setCreatedAt(LocalDateTime.now());
        return anchor;
    }

    private Integer countAssets(Long sessionId) {
        return Math.toIntExact(mediaAssetMapper.selectCount(new LambdaQueryWrapper<AiScoreMediaAsset>()
                .eq(AiScoreMediaAsset::getSessionId, sessionId)));
    }

    private Integer countSegments(Long sessionId) {
        return Math.toIntExact(transcriptSegmentMapper.selectCount(new LambdaQueryWrapper<AiScoreTranscriptSegment>()
                .eq(AiScoreTranscriptSegment::getSessionId, sessionId)));
    }

    private Integer countFrames(Long sessionId) {
        return Math.toIntExact(frameMapper.selectCount(new LambdaQueryWrapper<AiScoreFrame>()
                .eq(AiScoreFrame::getSessionId, sessionId)));
    }

    private Integer countAnchors(Long sessionId) {
        return Math.toIntExact(evidenceAnchorMapper.selectCount(new LambdaQueryWrapper<AiScoreEvidenceAnchor>()
                .eq(AiScoreEvidenceAnchor::getSessionId, sessionId)));
    }

    private String hashValues(List<String> values) {
        return sha256(values.stream()
                .filter(value -> value != null && !value.isBlank())
                .sorted()
                .collect(Collectors.joining("|")));
    }

    private String sha256(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(String.valueOf(value).getBytes(StandardCharsets.UTF_8));
            StringBuilder builder = new StringBuilder(hash.length * 2);
            for (byte b : hash) {
                builder.append(String.format("%02x", b));
            }
            return builder.toString();
        } catch (Exception e) {
            throw new IllegalStateException("hash failed", e);
        }
    }
}
```

- [ ] **Step 3: Run tests**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreEvidenceBundleServiceTest
```

Expected: PASS.

---

## 6. Task P6-D: Add Evidence Bundle API And Session Stage Transitions

**Files:**

- Modify: `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java`
- Modify: `backend/src/main/java/com/orep/backend/controller/AiScoreController.java`
- Test: `backend/src/test/java/com/orep/backend/controller/AiScoreEvidenceBundleControllerTest.java`

- [ ] **Step 1: Write controller test**

Create `backend/src/test/java/com/orep/backend/controller/AiScoreEvidenceBundleControllerTest.java`:

```java
package com.orep.backend.controller;

import com.orep.backend.dto.AiScoreEvidenceBundleResponse;
import com.orep.backend.service.AiScoreEvidenceBundleService;
import com.orep.backend.service.AiScoringSessionService;
import com.orep.backend.service.ProjectTeamService;
import com.orep.backend.mapper.AiScoreReportMapper;
import org.junit.jupiter.api.Test;
import org.springframework.test.web.servlet.MockMvc;

import static org.mockito.Mockito.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.setup.MockMvcBuilders.standaloneSetup;

class AiScoreEvidenceBundleControllerTest {

    @Test
    void prepareEvidenceReturnsUserSafeBundleStatus() throws Exception {
        AiScoreEvidenceBundleService evidenceService = mock(AiScoreEvidenceBundleService.class);
        AiScoringSessionService sessionService = mock(AiScoringSessionService.class);
        AiScoreEvidenceBundleResponse response = response();
        when(evidenceService.prepareEvidence(123L)).thenReturn(response);

        MockMvc mvc = standaloneSetup(new AiScoreController(
                mock(AiScoreReportMapper.class),
                mock(ProjectTeamService.class),
                sessionService,
                evidenceService
        )).build();

        mvc.perform(post("/api/ai-score/sessions/123/prepare-evidence"))
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.sessionId").value(123))
                .andExpect(jsonPath("$.data.snapshotStatus").value("ready"))
                .andExpect(jsonPath("$.data.transcriptSegmentCount").value(3))
                .andExpect(jsonPath("$.data.frameCount").value(3));

        verify(sessionService).markEvidencePreparing(123L);
        verify(sessionService).markEvidenceReady(123L);
    }

    @Test
    void latestEvidenceBundleReturnsMissingStatusBeforePreparation() throws Exception {
        AiScoreEvidenceBundleService evidenceService = mock(AiScoreEvidenceBundleService.class);
        AiScoreEvidenceBundleResponse response = new AiScoreEvidenceBundleResponse();
        response.setSessionId(123L);
        response.setSnapshotStatus("missing");
        response.setTranscriptSegmentCount(0);
        response.setFrameCount(0);
        response.setEvidenceAnchorCount(0);
        when(evidenceService.latestBundle(123L)).thenReturn(response);

        MockMvc mvc = standaloneSetup(new AiScoreController(
                mock(AiScoreReportMapper.class),
                mock(ProjectTeamService.class),
                mock(AiScoringSessionService.class),
                evidenceService
        )).build();

        mvc.perform(get("/api/ai-score/sessions/123/evidence-bundle"))
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.snapshotStatus").value("missing"));
    }

    private AiScoreEvidenceBundleResponse response() {
        AiScoreEvidenceBundleResponse response = new AiScoreEvidenceBundleResponse();
        response.setSessionId(123L);
        response.setSnapshotStatus("ready");
        response.setTranscriptSegmentCount(3);
        response.setFrameCount(3);
        response.setEvidenceAnchorCount(6);
        return response;
    }
}
```

- [ ] **Step 2: Run test to verify failure**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreEvidenceBundleControllerTest
```

Expected: FAIL because `AiScoreController` constructor does not accept `AiScoreEvidenceBundleService`, and session stage helpers do not exist.

- [ ] **Step 3: Modify `AiScoringSessionService`**

Add these methods to `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java` after `markUploaded`:

```java
public AiScoringSessionUserResponse markEvidencePreparing(Long sessionId) {
    AiScoringSession session = requireSession(sessionId);
    session.setStatus("scoring");
    session.setCurrentStage("evidence_preparing");
    session.setProgressPercent(Math.max(10, valueOrZero(session.getProgressPercent())));
    session.setUpdatedAt(LocalDateTime.now());
    sessionMapper.updateById(session);
    return toUserResponse(session);
}

public AiScoringSessionUserResponse markEvidenceReady(Long sessionId) {
    AiScoringSession session = requireSession(sessionId);
    session.setStatus("scoring");
    session.setCurrentStage("evidence_ready");
    session.setProgressPercent(Math.max(25, valueOrZero(session.getProgressPercent())));
    session.setUpdatedAt(LocalDateTime.now());
    sessionMapper.updateById(session);
    return toUserResponse(session);
}
```

- [ ] **Step 4: Modify `AiScoreController` constructor and endpoints**

In `backend/src/main/java/com/orep/backend/controller/AiScoreController.java`, add field:

```java
private final AiScoreEvidenceBundleService evidenceBundleService;
```

Change constructor to:

```java
public AiScoreController(AiScoreReportMapper reportMapper,
                         ProjectTeamService projectTeamService,
                         AiScoringSessionService scoringSessionService,
                         AiScoreEvidenceBundleService evidenceBundleService) {
    this.reportMapper = reportMapper;
    this.projectTeamService = projectTeamService;
    this.scoringSessionService = scoringSessionService;
    this.evidenceBundleService = evidenceBundleService;
}
```

Add endpoints after `sessionStatus`:

```java
@PostMapping("/sessions/{sessionId}/prepare-evidence")
public Result<AiScoreEvidenceBundleResponse> prepareEvidence(@PathVariable("sessionId") Long sessionId) {
    try {
        scoringSessionService.markEvidencePreparing(sessionId);
        AiScoreEvidenceBundleResponse response = evidenceBundleService.prepareEvidence(sessionId);
        scoringSessionService.markEvidenceReady(sessionId);
        return Result.success(response);
    } catch (IllegalArgumentException e) {
        return Result.error(400, e.getMessage());
    } catch (IllegalStateException e) {
        scoringSessionService.markFailed(sessionId, e.getMessage());
        return Result.error(409, e.getMessage());
    }
}

@GetMapping("/sessions/{sessionId}/evidence-bundle")
public Result<AiScoreEvidenceBundleResponse> evidenceBundle(@PathVariable("sessionId") Long sessionId) {
    try {
        return Result.success(evidenceBundleService.latestBundle(sessionId));
    } catch (IllegalArgumentException e) {
        return Result.error(400, e.getMessage());
    }
}
```

Also add import:

```java
import com.orep.backend.dto.AiScoreEvidenceBundleResponse;
import com.orep.backend.service.AiScoreEvidenceBundleService;
```

- [ ] **Step 5: Fix existing `AiScoreSessionControllerTest` constructor calls**

Search:

```bash
rg -n "new AiScoreController" backend/src/test/java
```

Update every test constructor call to pass `mock(AiScoreEvidenceBundleService.class)` as the fourth argument.

- [ ] **Step 6: Run tests**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreEvidenceBundleControllerTest,AiScoreSessionControllerTest
```

Expected: PASS.

---

## 7. Task P6-E: Frontend Evidence Bundle Panel

**Files:**

- Create: `frontend/user/src/utils/aiScoreEvidence.js`
- Create: `frontend/user/src/components/ai-score/EvidenceBundlePanel.vue`
- Modify: `frontend/user/src/views/AiScoreResult.vue`

- [ ] **Step 1: Add API util**

Create `frontend/user/src/utils/aiScoreEvidence.js`:

```js
import request from './request'

function unwrap(response) {
  return response?.data ?? response
}

export async function getEvidenceBundle(sessionId) {
  return unwrap(await request.get(`/api/ai-score/sessions/${sessionId}/evidence-bundle`))
}

export async function prepareEvidenceBundle(sessionId) {
  return unwrap(await request.post(`/api/ai-score/sessions/${sessionId}/prepare-evidence`))
}
```

- [ ] **Step 2: Add panel component**

Create `frontend/user/src/components/ai-score/EvidenceBundlePanel.vue`:

```vue
<template>
  <section class="evidence-bundle-panel">
    <div class="panel-title">
      <span>EVIDENCE BUNDLE</span>
      <strong>评分证据快照</strong>
      <small>{{ statusText }}</small>
    </div>
    <div class="bundle-grid">
      <article>
        <span>转写片段</span>
        <strong>{{ bundle?.transcriptSegmentCount ?? 0 }}</strong>
      </article>
      <article>
        <span>关键帧</span>
        <strong>{{ bundle?.frameCount ?? 0 }}</strong>
      </article>
      <article>
        <span>证据锚点</span>
        <strong>{{ bundle?.evidenceAnchorCount ?? 0 }}</strong>
      </article>
      <article>
        <span>媒体资产</span>
        <strong>{{ bundle?.mediaAssetCount ?? 0 }}</strong>
      </article>
    </div>
    <button v-if="canPrepare" type="button" :disabled="loading" @click="$emit('prepare')">
      {{ loading ? '生成中' : '生成证据快照' }}
    </button>
  </section>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  bundle: { type: Object, default: null },
  loading: { type: Boolean, default: false }
})

defineEmits(['prepare'])

const statusText = computed(() => {
  const status = props.bundle?.snapshotStatus || 'missing'
  if (status === 'ready') return '已固定正式评分证据'
  if (status === 'failed') return '证据生成失败'
  return '尚未生成正式证据快照'
})

const canPrepare = computed(() => props.bundle?.snapshotStatus !== 'ready')
</script>

<style scoped>
.evidence-bundle-panel {
  display: grid;
  gap: 14px;
  padding: 18px;
  border: 1px solid rgba(124, 255, 178, 0.18);
  border-radius: 8px;
  background: rgba(10, 14, 20, 0.82);
}

.panel-title {
  display: grid;
  gap: 4px;
}

.panel-title span {
  color: rgba(124, 255, 178, 0.86);
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 3px;
}

.panel-title strong {
  color: rgba(250, 252, 255, 0.94);
  font-size: 18px;
}

.panel-title small {
  color: rgba(240, 245, 250, 0.58);
}

.bundle-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.bundle-grid article {
  display: grid;
  gap: 6px;
  padding: 12px;
  border: 1px solid rgba(240, 245, 250, 0.1);
  border-radius: 8px;
  background: rgba(240, 245, 250, 0.04);
}

.bundle-grid span {
  color: rgba(240, 245, 250, 0.58);
  font-size: 12px;
  font-weight: 800;
}

.bundle-grid strong {
  color: rgba(250, 252, 255, 0.94);
  font-size: 24px;
}

button {
  width: fit-content;
  min-height: 38px;
  border: 0;
  border-radius: 8px;
  padding: 0 14px;
  background: linear-gradient(135deg, #7cffb2, #67b7ff);
  color: #06100c;
  font-weight: 900;
  cursor: pointer;
}

button:disabled {
  cursor: wait;
  opacity: 0.7;
}

@media (max-width: 760px) {
  .bundle-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
```

- [ ] **Step 3: Wire panel into `AiScoreResult.vue`**

Open `frontend/user/src/views/AiScoreResult.vue`.

Add imports in `<script setup>`:

```js
import EvidenceBundlePanel from '../components/ai-score/EvidenceBundlePanel.vue'
import { getEvidenceBundle, prepareEvidenceBundle } from '../utils/aiScoreEvidence'
```

Add state:

```js
const evidenceBundle = ref(null)
const evidenceBundleLoading = ref(false)
```

Add functions:

```js
async function loadEvidenceBundle() {
  if (!sessionId.value) return
  try {
    evidenceBundle.value = await getEvidenceBundle(sessionId.value)
  } catch (error) {
    evidenceBundle.value = { sessionId: sessionId.value, snapshotStatus: 'missing' }
  }
}

async function handlePrepareEvidenceBundle() {
  if (!sessionId.value) return
  evidenceBundleLoading.value = true
  try {
    evidenceBundle.value = await prepareEvidenceBundle(sessionId.value)
    ElMessage.success('证据快照已生成')
  } finally {
    evidenceBundleLoading.value = false
  }
}
```

Find the existing report load success path and call:

```js
await loadEvidenceBundle()
```

In template, place this panel near the report summary area:

```vue
<EvidenceBundlePanel
  v-if="sessionId"
  :bundle="evidenceBundle"
  :loading="evidenceBundleLoading"
  @prepare="handlePrepareEvidenceBundle"
/>
```

- [ ] **Step 4: Run frontend build**

Run:

```bash
cd frontend/user && npm run build
```

Expected: build success.

---

## 8. Task P6-F: Verification And Main Plan Update

**Files:**

- Modify: `docs/superpowers/plans/2026-06-23-ai-scoring-meeting-room-optimization.md`

- [ ] **Step 1: Run backend narrow tests**

Run:

```bash
cd backend && mvn test -Dtest=AiScoreEvidenceBundleServiceTest,AiScoreEvidenceBundleControllerTest,RecordingEvidenceAnchorBuilderTest,ScoreEvidenceAnchorStoreTest
```

Expected: PASS.

- [ ] **Step 2: Run full backend regression**

Run:

```bash
cd backend && mvn test
```

Expected: PASS.

- [ ] **Step 3: Run frontend build**

Run:

```bash
cd frontend/user && npm run build
```

Expected: PASS.

- [ ] **Step 4: Update execution board**

In `docs/superpowers/plans/2026-06-23-ai-scoring-meeting-room-optimization.md`, update P6 row:

```markdown
| P6 | 已完成 | ASR/OCR/抽帧证据清单与 evidence bundle | 已完成 | `cd backend && mvn test` 通过；新增正式证据快照、转写片段、关键帧、证据锚点和报告页证据状态 |
```

- [ ] **Step 5: Append completion record**

Append:

```markdown
### 本轮完成记录：P6 Evidence Bundle 证据快照

- 完成时间：2026-06-23 Asia/Shanghai
- 修改文件：
  - `backend/src/main/java/com/orep/backend/entity/AiScoreTranscriptSegment.java`
  - `backend/src/main/java/com/orep/backend/entity/AiScoreFrame.java`
  - `backend/src/main/java/com/orep/backend/entity/AiScoreEvidenceAnchor.java`
  - `backend/src/main/java/com/orep/backend/mapper/AiScoreTranscriptSegmentMapper.java`
  - `backend/src/main/java/com/orep/backend/mapper/AiScoreFrameMapper.java`
  - `backend/src/main/java/com/orep/backend/mapper/AiScoreEvidenceAnchorMapper.java`
  - `backend/src/main/java/com/orep/backend/dto/AiScoreEvidenceBundleResponse.java`
  - `backend/src/main/java/com/orep/backend/service/AiScoreEvidenceBundleService.java`
  - `backend/src/main/java/com/orep/backend/service/AiScoringSessionService.java`
  - `backend/src/main/java/com/orep/backend/controller/AiScoreController.java`
  - `backend/src/main/resources/sql/create_ai_scoring_session_tables.sql`
  - `dockerrun/sql/backend-resources/create_ai_scoring_session_tables.sql`
  - `frontend/user/src/utils/aiScoreEvidence.js`
  - `frontend/user/src/components/ai-score/EvidenceBundlePanel.vue`
  - `frontend/user/src/views/AiScoreResult.vue`
- 后端验证：
  - `cd backend && mvn test -Dtest=AiScoreEvidenceBundleServiceTest,AiScoreEvidenceBundleControllerTest,RecordingEvidenceAnchorBuilderTest,ScoreEvidenceAnchorStoreTest` 通过。
  - `cd backend && mvn test` 通过。
- 前端验证：
  - `cd frontend/user && npm run build` 通过。
- 手工验证：
  - 打开 `/ai-score/report/:sessionId` 后可看到证据快照面板。
  - 点击“生成证据快照”后转写片段、关键帧、证据锚点数量从 0 变为非 0。
- 已知风险：
  - 本轮仍是确定性 mock ASR/OCR/frame 生成器，真实 ASR/OCR/抽帧接入留到后续媒体流水线。
  - P7 赛道证据 schema 尚未接入，因此抽帧原因仍是通用类型。
- 下一步：
  - 进入 P7：v1.2 规则加载与赛道证据 schema，让不同赛道驱动不同证据采集目标。
```

---

## 9. Self-Review

Spec coverage:

- P6 evidence tables: covered by Task P6-A.
- Stable ASR snapshot: covered by Task P6-C mock transcript segments and `asrSnapshotHash`.
- Frame/OCR snapshot: covered by Task P6-C frames, OCR text, `frameSnapshotHash`, `ocrSnapshotHash`.
- Evidence anchors not all pointing to one default transcript: covered by Task P6-C generating per-segment and per-frame anchors with IDs.
- API and report entry: covered by Task P6-D and P6-E.
- Main plan status update: covered by Task P6-F.

Placeholder scan:

- No `TBD`, `TODO`, `implement later`, or undefined file paths.
- Real code blocks are provided for new entities, mappers, DTO, service, tests, controller endpoints, frontend util, and component.

Type consistency:

- Java property names match SQL snake_case through MyBatis Plus default mapping.
- `AiScoreEvidenceBundleResponse` fields match frontend `EvidenceBundlePanel` bindings.
- Controller endpoints match frontend `aiScoreEvidence.js`.

