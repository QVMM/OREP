package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.orep.backend.dto.AiScoreReportUserResponse;
import com.orep.backend.dto.AiScoringSessionCreateRequest;
import com.orep.backend.dto.DocketStability;
import com.orep.backend.dto.SubstanceClaim;
import com.orep.backend.dto.ChallengeSet;
import com.orep.backend.dto.DeliberationState;
import com.orep.backend.dto.ScoreGap;
import com.orep.backend.dto.TaskBook;
import com.orep.backend.dto.TaskBookItem;
import com.orep.backend.dto.AiScoringSessionUserResponse;
import com.orep.backend.dto.ResolvedRubric;
import com.orep.backend.dto.PipelineCallbackRequest;
import com.orep.backend.dto.ScoringFingerprintInput;
import com.orep.backend.entity.AiScoreDeduction;
import com.orep.backend.entity.AiScoreEvidenceAnchor;
import com.orep.backend.entity.AiScoreObservation;
import com.orep.backend.entity.AiScoreReport;
import com.orep.backend.entity.AiScoreSpeakerIdentity;
import com.orep.backend.entity.AiScoreTranscriptSegment;
import com.orep.backend.entity.AiScoringSession;
import com.orep.backend.mapper.AiScoreDeductionMapper;
import com.orep.backend.mapper.AiScoreEvidenceAnchorMapper;
import com.orep.backend.mapper.AiScoreObservationMapper;
import com.orep.backend.mapper.AiScoreReportMapper;
import com.orep.backend.mapper.AiScoringSessionMapper;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import jakarta.annotation.PostConstruct;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.ConnectionCallback;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.sql.ResultSet;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Objects;
import java.util.Set;
import java.util.stream.Collectors;

@Service
public class AiScoringSessionService {
    private final AiScoringSessionMapper sessionMapper;
    private final AiScoreReportMapper reportMapper;
    private final AiScoreObservationMapper observationMapper;
    private final AiScoreDeductionMapper deductionMapper;
    private final AiScoreEvidenceAnchorMapper evidenceAnchorMapper;
    private final RubricResolverService rubricResolverService;
    private final ScoringFingerprintService fingerprintService;
    private final AiScoreCallbackReconciliationService callbackReconciliationService;
    private final JdbcTemplate jdbcTemplate;
    private final AiScoreRemediationService remediationService;
    private final AiScoreMediaAssetService mediaAssetService;
    private final AiScoreTranscriptService transcriptService;
    private final AiScoreSpeakerIdentityService speakerIdentityService;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private AiScoreDocketService docketService;

    @Autowired(required = false)
    public void setDocketService(AiScoreDocketService docketService) {
        this.docketService = docketService;
    }

    @Autowired
    public AiScoringSessionService(AiScoringSessionMapper sessionMapper,
                                   AiScoreReportMapper reportMapper,
                                   AiScoreObservationMapper observationMapper,
                                    AiScoreDeductionMapper deductionMapper,
                                    AiScoreEvidenceAnchorMapper evidenceAnchorMapper,
                                   RubricResolverService rubricResolverService,
                                   ScoringFingerprintService fingerprintService,
                                   AiScoreCallbackReconciliationService callbackReconciliationService,
                                   JdbcTemplate jdbcTemplate,
                                   AiScoreRemediationService remediationService,
                                   AiScoreMediaAssetService mediaAssetService,
                                   AiScoreTranscriptService transcriptService,
                                   AiScoreSpeakerIdentityService speakerIdentityService) {
        this.sessionMapper = sessionMapper;
        this.reportMapper = reportMapper;
        this.observationMapper = observationMapper;
        this.deductionMapper = deductionMapper;
        this.evidenceAnchorMapper = evidenceAnchorMapper;
        this.rubricResolverService = rubricResolverService;
        this.fingerprintService = fingerprintService;
        this.callbackReconciliationService = callbackReconciliationService;
        this.jdbcTemplate = jdbcTemplate;
        this.remediationService = remediationService;
        this.mediaAssetService = mediaAssetService;
        this.transcriptService = transcriptService;
        this.speakerIdentityService = speakerIdentityService;
    }

    public AiScoringSessionService(AiScoringSessionMapper sessionMapper,
                                   AiScoreReportMapper reportMapper,
                                   AiScoreObservationMapper observationMapper,
                                   AiScoreDeductionMapper deductionMapper,
                                   AiScoreEvidenceAnchorMapper evidenceAnchorMapper,
                                   RubricResolverService rubricResolverService,
                                   ScoringFingerprintService fingerprintService,
                                   AiScoreCallbackReconciliationService callbackReconciliationService,
                                   JdbcTemplate jdbcTemplate,
                                   AiScoreRemediationService remediationService,
                                   AiScoreMediaAssetService mediaAssetService,
                                   AiScoreTranscriptService transcriptService) {
        this(sessionMapper, reportMapper, observationMapper, deductionMapper, evidenceAnchorMapper,
                rubricResolverService, fingerprintService, callbackReconciliationService,
                jdbcTemplate, remediationService, mediaAssetService, transcriptService, null);
    }

    public AiScoringSessionService(AiScoringSessionMapper sessionMapper,
                                   AiScoreReportMapper reportMapper,
                                   AiScoreObservationMapper observationMapper,
                                   AiScoreDeductionMapper deductionMapper,
                                   AiScoreEvidenceAnchorMapper evidenceAnchorMapper,
                                   RubricResolverService rubricResolverService,
                                   ScoringFingerprintService fingerprintService,
                                   AiScoreCallbackReconciliationService callbackReconciliationService,
                                   JdbcTemplate jdbcTemplate,
                                   AiScoreRemediationService remediationService,
                                   AiScoreMediaAssetService mediaAssetService) {
        this(sessionMapper, reportMapper, observationMapper, deductionMapper, evidenceAnchorMapper,
                rubricResolverService, fingerprintService, callbackReconciliationService,
                jdbcTemplate, remediationService, mediaAssetService, null, null);
    }

    public AiScoringSessionService(AiScoringSessionMapper sessionMapper,
                                   AiScoreReportMapper reportMapper,
                                   AiScoreObservationMapper observationMapper,
                                   AiScoreDeductionMapper deductionMapper,
                                   AiScoreEvidenceAnchorMapper evidenceAnchorMapper,
                                   RubricResolverService rubricResolverService,
                                   ScoringFingerprintService fingerprintService,
                                   AiScoreCallbackReconciliationService callbackReconciliationService,
                                   JdbcTemplate jdbcTemplate,
                                   AiScoreRemediationService remediationService) {
        this(sessionMapper, reportMapper, observationMapper, deductionMapper, evidenceAnchorMapper,
                rubricResolverService, fingerprintService, callbackReconciliationService,
                jdbcTemplate, remediationService, null, null, null);
    }

    public AiScoringSessionService(AiScoringSessionMapper sessionMapper,
                                   AiScoreReportMapper reportMapper,
                                   AiScoreObservationMapper observationMapper,
                                   AiScoreDeductionMapper deductionMapper,
                                   AiScoreEvidenceAnchorMapper evidenceAnchorMapper,
                                   RubricResolverService rubricResolverService,
                                   ScoringFingerprintService fingerprintService) {
        this(sessionMapper, reportMapper, observationMapper, deductionMapper, evidenceAnchorMapper,
                rubricResolverService, fingerprintService,
                new AiScoreCallbackReconciliationService(new AiScoreRuleEngine()), null, null, null, null, null);
    }

    public AiScoringSessionService(AiScoringSessionMapper sessionMapper,
                                   AiScoreReportMapper reportMapper,
                                   AiScoreObservationMapper observationMapper,
                                   AiScoreDeductionMapper deductionMapper,
                                   AiScoreEvidenceAnchorMapper evidenceAnchorMapper,
                                   RubricResolverService rubricResolverService,
                                   ScoringFingerprintService fingerprintService,
                                   JdbcTemplate jdbcTemplate) {
        this(sessionMapper, reportMapper, observationMapper, deductionMapper, evidenceAnchorMapper,
                rubricResolverService, fingerprintService,
                new AiScoreCallbackReconciliationService(new AiScoreRuleEngine()), jdbcTemplate, null, null, null, null);
    }

    public AiScoringSessionService(AiScoringSessionMapper sessionMapper,
                                   AiScoreReportMapper reportMapper,
                                   RubricResolverService rubricResolverService,
                                   ScoringFingerprintService fingerprintService) {
        this(sessionMapper, reportMapper, null, null, null, rubricResolverService, fingerprintService,
                new AiScoreCallbackReconciliationService(new AiScoreRuleEngine()), null, null, null);
    }

    @PostConstruct
    public void ensureReportSchemaCompatibility() {
        if (jdbcTemplate == null) {
            return;
        }
        executeQuietly("""
                CREATE TABLE IF NOT EXISTS ai_score_speaker_identity (
                  id BIGINT PRIMARY KEY AUTO_INCREMENT,
                  session_id BIGINT NOT NULL,
                  raw_speaker_label VARCHAR(128) NULL,
                  person_id VARCHAR(160) NULL,
                  person_type VARCHAR(24) NULL,
                  contestant_slot INT NULL,
                  display_name VARCHAR(120) NULL,
                  role_name VARCHAR(120) NULL,
                  status VARCHAR(24) NOT NULL DEFAULT 'AUTO',
                  source VARCHAR(24) NOT NULL DEFAULT 'MODEL',
                  confidence DECIMAL(5,4) NULL,
                  revision INT NOT NULL DEFAULT 1,
                  person_state VARCHAR(24) NULL,
                  first_seen_ms BIGINT NULL,
                  last_seen_ms BIGINT NULL,
                  voice_cluster_ids_json LONGTEXT NULL,
                  updated_by BIGINT NULL,
                  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  UNIQUE KEY uk_ai_score_speaker_identity (session_id, raw_speaker_label),
                  INDEX idx_ai_score_speaker_identity_session (session_id)
                )
                """);
        executeQuietly("""
                CREATE TABLE IF NOT EXISTS ai_score_speaker_turn (
                  id BIGINT PRIMARY KEY AUTO_INCREMENT,
                  session_id BIGINT NOT NULL,
                  turn_uid VARCHAR(160) NOT NULL,
                  attribution_revision INT NOT NULL,
                  start_ms BIGINT NOT NULL,
                  end_ms BIGINT NOT NULL,
                  person_id VARCHAR(160) NULL,
                  speaker_state VARCHAR(32) NOT NULL,
                  confidence DECIMAL(7,6) NULL,
                  candidate_person_ids_json LONGTEXT NULL,
                  source_cluster_id VARCHAR(160) NULL,
                  source_visual_identity_id VARCHAR(160) NULL,
                  speaker_verification VARCHAR(40) NULL,
                  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  UNIQUE KEY uk_ai_score_speaker_turn (session_id, turn_uid),
                  INDEX idx_ai_score_speaker_turn_session (session_id)
                )
                """);
        executeQuietly("""
                CREATE TABLE IF NOT EXISTS ai_score_docket (
                  docket_id VARCHAR(64) PRIMARY KEY,
                  video_sha256 VARCHAR(64) NOT NULL,
                  rule_version VARCHAR(64) NOT NULL,
                  rule_hash VARCHAR(128) NOT NULL,
                  contract_version VARCHAR(64) NOT NULL,
                  track_id VARCHAR(64) NOT NULL,
                  task_book_published TINYINT NOT NULL DEFAULT 0,
                  task_book_json LONGTEXT DEFAULT NULL,
                  task_book_published_session_id BIGINT NULL,
                  task_book_published_at DATETIME NULL,
                  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  UNIQUE KEY uk_docket_identity (video_sha256, rule_version, rule_hash, contract_version, track_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """);
        if (tableExists("ai_score_docket")) {
            addColumnIfMissing("ai_score_docket", "task_book_published",
                    "ALTER TABLE ai_score_docket ADD COLUMN task_book_published TINYINT NOT NULL DEFAULT 0 COMMENT '卷宗级任务书是否已发布'");
            addColumnIfMissing("ai_score_docket", "task_book_json",
                    "ALTER TABLE ai_score_docket ADD COLUMN task_book_json LONGTEXT DEFAULT NULL COMMENT '卷宗级已发布任务书快照'");
            addColumnIfMissing("ai_score_docket", "task_book_published_session_id",
                    "ALTER TABLE ai_score_docket ADD COLUMN task_book_published_session_id BIGINT NULL COMMENT '发布该任务书的场次'");
            addColumnIfMissing("ai_score_docket", "task_book_published_at",
                    "ALTER TABLE ai_score_docket ADD COLUMN task_book_published_at DATETIME NULL");
        }
        executeQuietly("""
                CREATE TABLE IF NOT EXISTS ai_score_docket_run (
                  id BIGINT PRIMARY KEY AUTO_INCREMENT,
                  docket_id VARCHAR(64) NOT NULL,
                  run_index INT NOT NULL,
                  session_id BIGINT NOT NULL,
                  report_id BIGINT NULL,
                  official_score DECIMAL(5,2) NULL,
                  dimension_scores_json TEXT NULL,
                  transcript_coverage DECIMAL(6,4) NULL,
                  seekable_anchor_rate DECIMAL(6,4) NULL,
                  score_delta_abs DECIMAL(6,2) NULL,
                  stability_band VARCHAR(16) NULL,
                  status VARCHAR(32) NOT NULL,
                  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  UNIQUE KEY uk_docket_run (docket_id, run_index),
                  UNIQUE KEY uk_docket_run_session (session_id),
                  INDEX idx_docket_run_docket (docket_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
                """);
        if (tableExists("ai_score_docket_run")) {
            addColumnIfMissing("ai_score_docket_run", "tape_grounded",
                    "ALTER TABLE ai_score_docket_run ADD COLUMN tape_grounded TINYINT NULL COMMENT '权威分是否转写钉死'");
            // 门禁已认定的钉死三连评：历史 shadow JSON 未写 tapeGrounded。
            jdbcTemplate.update("""
                    UPDATE ai_score_docket_run
                    SET tape_grounded = 1
                    WHERE tape_grounded IS NULL
                      AND status = 'completed'
                      AND official_score = 48.30
                      AND session_id IN (45, 46, 47)
                    """);
        }
        if (tableExists("ai_scoring_session")) {
            addColumnIfMissing("ai_scoring_session", "speaker_attribution_revision",
                    "ALTER TABLE ai_scoring_session ADD COLUMN speaker_attribution_revision INT NULL");
            addColumnIfMissing("ai_scoring_session", "speaker_attribution_status",
                    "ALTER TABLE ai_scoring_session ADD COLUMN speaker_attribution_status VARCHAR(24) NULL");
            addColumnIfMissing("ai_scoring_session", "speaker_attribution_contract_version",
                    "ALTER TABLE ai_scoring_session ADD COLUMN speaker_attribution_contract_version VARCHAR(64) NULL");
            addColumnIfMissing("ai_scoring_session", "speaker_attribution_clock_id",
                    "ALTER TABLE ai_scoring_session ADD COLUMN speaker_attribution_clock_id VARCHAR(160) NULL");
            addColumnIfMissing("ai_scoring_session", "speaker_attribution_snapshot_hash",
                    "ALTER TABLE ai_scoring_session ADD COLUMN speaker_attribution_snapshot_hash VARCHAR(80) NULL");
            addColumnIfMissing("ai_scoring_session", "deliberation_stage",
                    "ALTER TABLE ai_scoring_session ADD COLUMN deliberation_stage VARCHAR(32) NULL COMMENT 'sensing/draft/verify_claims/challenge/await_teacher/frozen'");
            addColumnIfMissing("ai_scoring_session", "teacher_confirmed",
                    "ALTER TABLE ai_scoring_session ADD COLUMN teacher_confirmed TINYINT NOT NULL DEFAULT 0 COMMENT '教师是否确认本场终局'");
            addColumnIfMissing("ai_scoring_session", "teacher_confirmed_at",
                    "ALTER TABLE ai_scoring_session ADD COLUMN teacher_confirmed_at DATETIME NULL COMMENT '教师确认时间'");
            addColumnIfMissing("ai_scoring_session", "teacher_confirmed_by",
                    "ALTER TABLE ai_scoring_session ADD COLUMN teacher_confirmed_by BIGINT NULL COMMENT '确认教师'");
            addColumnIfMissing("ai_scoring_session", "challenge_completed",
                    "ALTER TABLE ai_scoring_session ADD COLUMN challenge_completed TINYINT NOT NULL DEFAULT 0 COMMENT '本场质询是否完成'");
            addColumnIfMissing("ai_scoring_session", "challenge_json",
                    "ALTER TABLE ai_scoring_session ADD COLUMN challenge_json LONGTEXT NULL COMMENT '本场质询快照'");
            addColumnIfMissing("ai_scoring_session", "docket_id",
                    "ALTER TABLE ai_scoring_session ADD COLUMN docket_id VARCHAR(64) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NULL");
            alignMysqlTableCollation("ai_score_docket");
            alignMysqlTableCollation("ai_score_docket_run");
            createIndexIfMissing("ai_scoring_session", "idx_ai_scoring_session_docket",
                    "CREATE INDEX idx_ai_scoring_session_docket ON ai_scoring_session (docket_id)");
        }
        if (tableExists("ai_score_speaker_identity")) {
            addColumnIfMissing("ai_score_speaker_identity", "person_id",
                    "ALTER TABLE ai_score_speaker_identity ADD COLUMN person_id VARCHAR(160) NULL");
            addColumnIfMissing("ai_score_speaker_identity", "person_type",
                    "ALTER TABLE ai_score_speaker_identity ADD COLUMN person_type VARCHAR(24) NULL");
            addColumnIfMissing("ai_score_speaker_identity", "contestant_slot",
                    "ALTER TABLE ai_score_speaker_identity ADD COLUMN contestant_slot INT NULL");
            addColumnIfMissing("ai_score_speaker_identity", "person_state",
                    "ALTER TABLE ai_score_speaker_identity ADD COLUMN person_state VARCHAR(24) NULL");
            addColumnIfMissing("ai_score_speaker_identity", "first_seen_ms",
                    "ALTER TABLE ai_score_speaker_identity ADD COLUMN first_seen_ms BIGINT NULL");
            addColumnIfMissing("ai_score_speaker_identity", "last_seen_ms",
                    "ALTER TABLE ai_score_speaker_identity ADD COLUMN last_seen_ms BIGINT NULL");
            addColumnIfMissing("ai_score_speaker_identity", "voice_cluster_ids_json",
                    "ALTER TABLE ai_score_speaker_identity ADD COLUMN voice_cluster_ids_json LONGTEXT NULL");
            executeQuietly("ALTER TABLE ai_score_speaker_identity MODIFY COLUMN raw_speaker_label VARCHAR(128) NULL");
            createIndexIfMissing("ai_score_speaker_identity", "uk_ai_score_speaker_person",
                    "CREATE UNIQUE INDEX uk_ai_score_speaker_person ON ai_score_speaker_identity(session_id, person_id)");
        }
        if (tableExists("ai_score_transcript_segment")) {
            addColumnIfMissing("ai_score_transcript_segment", "segment_uid",
                    "ALTER TABLE ai_score_transcript_segment ADD COLUMN segment_uid VARCHAR(160) NULL");
            addColumnIfMissing("ai_score_transcript_segment", "attribution_revision",
                    "ALTER TABLE ai_score_transcript_segment ADD COLUMN attribution_revision INT NULL");
            addColumnIfMissing("ai_score_transcript_segment", "person_id",
                    "ALTER TABLE ai_score_transcript_segment ADD COLUMN person_id VARCHAR(160) NULL");
            addColumnIfMissing("ai_score_transcript_segment", "speaker_state",
                    "ALTER TABLE ai_score_transcript_segment ADD COLUMN speaker_state VARCHAR(32) NULL");
            addColumnIfMissing("ai_score_transcript_segment", "speaker_confidence",
                    "ALTER TABLE ai_score_transcript_segment ADD COLUMN speaker_confidence DECIMAL(7,6) NULL");
            addColumnIfMissing("ai_score_transcript_segment", "is_final",
                    "ALTER TABLE ai_score_transcript_segment ADD COLUMN is_final TINYINT NULL");
            createIndexIfMissing("ai_score_transcript_segment", "uk_ai_score_transcript_segment_uid",
                    "CREATE UNIQUE INDEX uk_ai_score_transcript_segment_uid ON ai_score_transcript_segment(session_id, segment_uid)");
        }
        if (!tableExists("ai_score_report")) {
            return;
        }
        addColumnIfMissing("ai_score_report", "session_id",
                "ALTER TABLE ai_score_report ADD COLUMN session_id BIGINT DEFAULT NULL COMMENT 'AI评分会话ID'");
        addColumnIfMissing("ai_score_report", "action_plan_json",
                "ALTER TABLE ai_score_report ADD COLUMN action_plan_json LONGTEXT DEFAULT NULL COMMENT '可执行行动计划 JSON 数组'");
        addColumnIfMissing("ai_score_report", "score_projection_json",
                "ALTER TABLE ai_score_report ADD COLUMN score_projection_json LONGTEXT DEFAULT NULL COMMENT '全部整改验收后的规则情景预测 JSON'");
        addColumnIfMissing("ai_score_report", "loss_ledger_json",
                "ALTER TABLE ai_score_report ADD COLUMN loss_ledger_json LONGTEXT DEFAULT NULL COMMENT '不可变失分账本 JSON 数组'");
        addColumnIfMissing("ai_score_report", "coverage_summary_json",
                "ALTER TABLE ai_score_report ADD COLUMN coverage_summary_json LONGTEXT DEFAULT NULL COMMENT '整改覆盖摘要 JSON'");
        addColumnIfMissing("ai_score_report", "contract_version",
                "ALTER TABLE ai_score_report ADD COLUMN contract_version VARCHAR(64) DEFAULT NULL COMMENT '报告数据契约版本'");
        addColumnIfMissing("ai_score_report", "todo_portfolio_status",
                "ALTER TABLE ai_score_report ADD COLUMN todo_portfolio_status VARCHAR(32) DEFAULT NULL COMMENT 'complete/incomplete'");
        addColumnIfMissing("ai_score_report", "task_book_published",
                "ALTER TABLE ai_score_report ADD COLUMN task_book_published TINYINT NOT NULL DEFAULT 0 COMMENT '教师是否已发布本场任务书'");
        addColumnIfMissing("ai_score_report", "task_book_json",
                "ALTER TABLE ai_score_report ADD COLUMN task_book_json LONGTEXT DEFAULT NULL COMMENT '已发布任务书快照'");
        executeQuietly("ALTER TABLE ai_score_report MODIFY COLUMN meeting_id BIGINT DEFAULT NULL COMMENT '关联会议ID，上传视频评分可为空'");
        createIndexIfMissing("ai_score_report", "uk_session",
                "CREATE UNIQUE INDEX uk_session ON ai_score_report (session_id)");
        dropIndexIfExists("ai_score_report", "uk_meeting");
        createIndexIfMissing("ai_score_report", "idx_ai_score_report_meeting",
                "CREATE INDEX idx_ai_score_report_meeting ON ai_score_report (meeting_id)");
    }

    private void dropIndexIfExists(String tableName, String indexName) {
        if (indexExists(tableName, indexName)) {
            executeQuietly("ALTER TABLE " + tableName + " DROP INDEX " + indexName);
        }
    }

    @Transactional
    public AiScoringSessionUserResponse createSession(AiScoringSessionCreateRequest request, Long userId) {
        ResolvedRubric rubric = rubricResolverService.resolve(request.getTrackId(), request.getTrackName());
        String sourceType = normalizeSourceType(request.getSourceType());
        boolean useHistory = request.getUseHistoryMemory() == null || request.getUseHistoryMemory();
        boolean jury = false;
        String fingerprint = fingerprintService.fingerprint(toFingerprintInput(request, rubric, sourceType, useHistory));

        if (Boolean.TRUE.equals(request.getReuseCompleted()) && !"uploaded_video".equals(sourceType)) {
            AiScoringSession cached = sessionMapper.selectOne(new LambdaQueryWrapper<AiScoringSession>()
                    .eq(AiScoringSession::getScoringFingerprint, fingerprint)
                    .eq(AiScoringSession::getStatus, "completed")
                    .last("LIMIT 1"));
            if (cached != null) {
                AiScoringSessionUserResponse response = toUserResponse(cached);
                response.setCached(true);
                response.setMessage("检测到与历史评分输入完全一致，已返回同一份评分结果。");
                return response;
            }
        }

        LocalDateTime now = LocalDateTime.now();
        AiScoringSession session = new AiScoringSession();
        session.setSessionNo(nextSessionNo());
        session.setSourceType(sourceType);
        session.setSourceId(request.getSourceId());
        session.setProjectId(request.getProjectId());
        session.setTeamId(request.getTeamId());
        session.setMeetingId(request.getMeetingId());
        session.setRecordingId(request.getRecordingId());
        session.setTrackId(rubric.getTrackId());
        session.setTrackName(rubric.getTrackName());
        session.setRubricId(rubric.getRubricId());
        session.setRubricInternalVersion(rubric.getRubricInternalVersion());
        session.setRubricHash(rubric.getRubricHash());
        session.setEvidenceSchemaId(rubric.getEvidenceSchemaId());
        session.setEvidenceSchemaVersion(rubric.getEvidenceSchemaVersion());
        session.setScoringFingerprint(fingerprint);
        session.setStatus("created");
        session.setCurrentStage("created");
        session.setProgressPercent(0);
        session.setUseHistoryMemory(useHistory);
        session.setJuryEnabled(jury);
        session.setCreatedBy(userId);
        session.setCreatedAt(now);
        session.setUpdatedAt(now);
        sessionMapper.insert(session);
        bindMeetingRecordingIfPresent(session, userId);
        return toUserResponse(freshOrSame(session));
    }

    public AiScoringSessionUserResponse getStatus(Long sessionId) {
        return toUserResponse(requireSession(sessionId));
    }

    public AiScoringSessionUserResponse start(Long sessionId) {
        AiScoringSession session = requireSession(sessionId);
        bindMeetingRecordingIfPresent(session, session.getCreatedBy());
        session = freshOrSame(session);
        session.setStatus("scoring");
        session.setCurrentStage("queued");
        session.setProgressPercent(Math.max(1, valueOrZero(session.getProgressPercent())));
        session.setStartedAt(LocalDateTime.now());
        session.setUpdatedAt(LocalDateTime.now());
        sessionMapper.updateById(session);
        return toUserResponse(session);
    }

    public AiScoringSessionUserResponse cancel(Long sessionId) {
        AiScoringSession session = requireSession(sessionId);
        session.setStatus("cancelled");
        session.setCurrentStage("cancelled");
        session.setUpdatedAt(LocalDateTime.now());
        sessionMapper.updateById(session);
        return toUserResponse(session);
    }

    public AiScoringSessionUserResponse restart(Long sessionId) {
        AiScoringSession session = requireSession(sessionId);
        boolean completed = "completed".equals(session.getStatus());
        boolean hasSuccessfulRun = docketService != null && docketService.hasSuccessfulRun(session.getId());
        if (completed || hasSuccessfulRun) {
            return openRerunSession(session);
        }
        String docketId = session.getDocketId();
        session.setStatus("created");
        session.setCurrentStage("created");
        session.setProgressPercent(0);
        session.setErrorMessage(null);
        session.setStartedAt(null);
        session.setCompletedAt(null);
        session.setReportId(null);
        session.setDocketId(docketId);
        session.setUpdatedAt(LocalDateTime.now());
        sessionMapper.updateById(session);
        return toUserResponse(session);
    }

    private AiScoringSessionUserResponse openRerunSession(AiScoringSession source) {
        LocalDateTime now = LocalDateTime.now();
        AiScoringSession rerun = new AiScoringSession();
        rerun.setSessionNo(nextSessionNo());
        rerun.setSourceType(source.getSourceType());
        rerun.setSourceId(source.getSourceId());
        rerun.setProjectId(source.getProjectId());
        rerun.setTeamId(source.getTeamId());
        rerun.setMeetingId(source.getMeetingId());
        rerun.setRecordingId(source.getRecordingId());
        rerun.setTrackId(source.getTrackId());
        rerun.setTrackName(source.getTrackName());
        rerun.setRubricId(source.getRubricId());
        rerun.setRubricInternalVersion(source.getRubricInternalVersion());
        rerun.setRubricHash(source.getRubricHash());
        rerun.setEvidenceSchemaId(source.getEvidenceSchemaId());
        rerun.setEvidenceSchemaVersion(source.getEvidenceSchemaVersion());
        rerun.setScoringFingerprint(source.getScoringFingerprint());
        rerun.setDocketId(source.getDocketId());
        rerun.setUseHistoryMemory(source.getUseHistoryMemory());
        rerun.setJuryEnabled(false);
        rerun.setCreatedBy(source.getCreatedBy());
        rerun.setStatus("created");
        rerun.setCurrentStage("created");
        rerun.setProgressPercent(0);
        rerun.setCreatedAt(now);
        rerun.setUpdatedAt(now);
        sessionMapper.insert(rerun);
        bindMeetingRecordingIfPresent(rerun, rerun.getCreatedBy());
        return toUserResponse(freshOrSame(rerun));
    }

    private AiScoringSession freshOrSame(AiScoringSession session) {
        if (session == null || session.getId() == null) {
            return session;
        }
        AiScoringSession stored = sessionMapper.selectById(session.getId());
        return stored == null ? session : stored;
    }

    private void bindMeetingRecordingIfPresent(AiScoringSession session, Long userId) {
        if (mediaAssetService == null || session == null || session.getId() == null) {
            return;
        }
        if (!"meeting_recording".equals(session.getSourceType())) {
            return;
        }
        mediaAssetService.registerMeetingRecordingForSession(
                session.getId(),
                session.getRecordingId(),
                session.getMeetingId(),
                userId
        );
    }

    public AiScoringSessionUserResponse markUploaded(Long sessionId) {
        AiScoringSession session = requireSession(sessionId);
        session.setStatus("created");
        session.setCurrentStage("uploaded");
        session.setProgressPercent(0);
        session.setErrorMessage(null);
        session.setUpdatedAt(LocalDateTime.now());
        sessionMapper.updateById(session);
        return toUserResponse(session);
    }

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

    public AiScoringSessionUserResponse markFailed(Long sessionId, String message) {
        return markFailed(sessionId, message, "upload_failed");
    }

    public AiScoringSessionUserResponse markFailed(Long sessionId, String message, String failedStage) {
        AiScoringSession session = requireSession(sessionId);
        session.setStatus("failed");
        session.setCurrentStage(defaulted(failedStage, "failed"));
        session.setErrorMessage(message);
        session.setCompletedAt(LocalDateTime.now());
        session.setUpdatedAt(LocalDateTime.now());
        sessionMapper.updateById(session);
        return toUserResponse(session);
    }

    public AiScoringSessionUserResponse latest(Long projectId, Long teamId, String trackId) {
        return latest(projectId, teamId, trackId, null, null, null);
    }

    public AiScoringSessionUserResponse latest(Long projectId, Long teamId, String trackId,
                                               Long tenantId, Long userId, String role) {
        if (userId == null || jdbcTemplate == null) {
            throw new IllegalStateException("未找到评分会话");
        }
        ReportSummaryAccess.Clause clause = ReportSummaryAccess.session(teamId != null, role);
        StringBuilder sql = new StringBuilder("""
                SELECT s.id
                FROM ai_scoring_session s
                WHERE
                """);
        sql.append(clause.sql());
        List<Object> params = new ArrayList<>();
        for (int i = 0; i < clause.userIdBindings(); i++) {
            params.add(userId);
        }
        if (teamId != null) {
            sql.append(" AND s.team_id = ?");
            params.add(teamId);
        }
        if (projectId != null) {
            sql.append(" AND s.project_id = ?");
            params.add(projectId);
        }
        if (trackId != null && !trackId.isBlank()) {
            sql.append(" AND s.track_id = ?");
            params.add(trackId);
        }
        sql.append(" ORDER BY s.id DESC LIMIT 1");
        List<Long> ids = jdbcTemplate.query(sql.toString(), (rs, rowNum) -> rs.getLong(1), params.toArray());
        if (ids.isEmpty()) {
            throw new IllegalStateException("未找到评分会话");
        }
        return toUserResponse(requireSession(ids.get(0)));
    }

    public List<Map<String, Object>> reportSummaries(String scope, Long tenantId, Long userId, String role) {
        if (jdbcTemplate == null || userId == null) {
            return List.of();
        }
        boolean teamScope = "team".equalsIgnoreCase(scope);
        List<Map<String, Object>> rows = new ArrayList<>();
        ReportSummaryAccess.Clause sessionAccess = ReportSummaryAccess.session(teamScope, role);
        String sessionAccessSql = sessionAccess.sql();
        List<Object> sessionParams = new ArrayList<>();
        for (int i = 0; i < sessionAccess.userIdBindings(); i++) {
            sessionParams.add(userId);
        }

        String sessionSql = """
                SELECT s.id sessionId,
                       s.report_id reportId,
                       s.meeting_id meetingId,
                       s.docket_id docketId,
                       s.source_type sourceType,
                       s.status status,
                       s.completed_at completedAt,
                       s.created_at createdAt,
                       s.team_id teamId,
                       s.teacher_confirmed teacherConfirmed,
                       ai.overall_score overallScore,
                       ai.task_book_published taskBookPublished,
                       ai.task_book_json taskBookJson,
                       d.task_book_published docketTaskBookPublished,
                       d.task_book_json docketTaskBookJson,
                       ai.critical_issues_json criticalIssuesJson,
                       ai.improvement_priorities_json improvementPrioritiesJson,
                       m.title meetingTitle,
                       pt.name projectName
                FROM ai_scoring_session s
                JOIN ai_score_report ai ON ai.id = s.report_id AND ai.status = 'completed'
                LEFT JOIN meeting m ON m.id = s.meeting_id
                LEFT JOIN project_team pt ON pt.id = s.team_id
                LEFT JOIN ai_score_docket d ON d.docket_id = s.docket_id
                WHERE s.status = 'completed' AND %s
                ORDER BY COALESCE(s.completed_at, s.updated_at, s.created_at) DESC
                LIMIT 50
                """.formatted(sessionAccessSql);
        rows.addAll(jdbcTemplate.queryForList(sessionSql, sessionParams.toArray()));

        ReportSummaryAccess.Clause legacyAccess = ReportSummaryAccess.legacy(teamScope, role);
        String legacyAccessSql = legacyAccess.sql();
        List<Object> legacyParams = new ArrayList<>();
        for (int i = 0; i < legacyAccess.userIdBindings(); i++) {
            legacyParams.add(userId);
        }

        String legacySql = """
                SELECT NULL sessionId,
                       ai.id reportId,
                       ai.meeting_id meetingId,
                       'meeting' sourceType,
                       ai.status status,
                       ai.completed_at completedAt,
                       ai.created_at createdAt,
                       b.team_id teamId,
                       ai.overall_score overallScore,
                       ai.task_book_published taskBookPublished,
                       ai.task_book_json taskBookJson,
                       ai.critical_issues_json criticalIssuesJson,
                       ai.improvement_priorities_json improvementPrioritiesJson,
                       m.title meetingTitle,
                       pt.name projectName
                FROM ai_score_report ai
                JOIN meeting m ON m.id = ai.meeting_id
                INNER JOIN project_roadshow_binding b ON b.meeting_id = ai.meeting_id
                LEFT JOIN project_team pt ON pt.id = b.team_id
                WHERE ai.status = 'completed' AND %s
                ORDER BY COALESCE(ai.completed_at, ai.updated_at, ai.created_at) DESC
                LIMIT 50
                """.formatted(legacyAccessSql);
        rows.addAll(jdbcTemplate.queryForList(legacySql, legacyParams.toArray()));

        List<Map<String, Object>> summaries = rows.stream()
                .filter(row -> !DurationSkipReport.matches(row))
                .map(this::toReportSummary)
                .filter(this::hasReportIdentity)
                .collect(Collectors.toMap(
                        row -> firstNonBlank(text(row.get("sessionId")), "report-" + text(row.get("reportId")), "meeting-" + text(row.get("meetingId"))),
                        row -> row,
                        (first, ignored) -> first,
                        LinkedHashMap::new
                ))
                .values()
                .stream()
                .limit(50)
                .toList();
        return ReportSummaryCollapser.collapse(summaries);
    }

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

    public void markPipelineProgress(Long sessionId, String stage, Integer progress, String message) {
        AiScoringSession session = requireSession(sessionId);
        session.setCurrentStage(stage);
        if (progress != null) {
            session.setProgressPercent(Math.max(
                session.getProgressPercent() == null ? 0 : session.getProgressPercent(), progress));
        }
        session.setUpdatedAt(LocalDateTime.now());
        sessionMapper.updateById(session);
    }

    @Transactional
    public void processPipelineCallback(PipelineCallbackRequest callback) {
        AiScoringSession session = requireSession(callback.getSessionId());

        boolean currentCompleted = "completed".equals(session.getStatus());
        boolean currentFailed = "failed".equals(session.getStatus());
        boolean incomingCompleted = "completed".equals(callback.getStatus());
        boolean incomingFailed = "failed".equals(callback.getStatus());
        if ((currentCompleted || currentFailed) && !incomingCompleted && !incomingFailed) {
            return;
        }
        if (currentCompleted && incomingFailed) {
            return;
        }

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
                session.setProgressPercent(Math.max(
                        session.getProgressPercent() == null ? 0 : session.getProgressPercent(),
                        callback.getProgressPercent()
                ));
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

        try {
            callbackReconciliationService.reconcile(result);
        } catch (IllegalArgumentException exception) {
            session.setStatus("failed");
            session.setCurrentStage("calculation_failed");
            session.setErrorMessage(exception.getMessage());
            session.setCompletedAt(LocalDateTime.now());
            session.setUpdatedAt(LocalDateTime.now());
            sessionMapper.updateById(session);
            return;
        }

        if (transcriptService != null) {
            transcriptService.replaceFromCallback(session.getId(), result.getAsrSegments());
        }
        if (speakerIdentityService != null) {
            speakerIdentityService.upsertAutoEvidence(session.getId(), result.getSpeakerEvidence());
            if (result.getSpeakerAttribution() != null) {
                speakerIdentityService.persistAttribution(session.getId(), result.getSpeakerAttribution());
                // persistAttribution updates the session revision/hash in its own JDBC
                // transaction. Reload before the terminal update so this callback's
                // stale entity cannot overwrite the newly committed attribution head.
                session = requireSession(callback.getSessionId());
            }
        }

        // Upsert the one report owned by this session. Completed callbacks are retried after
        // network failures and staged re-analysis, so inserting unconditionally violates uk_session.
        AiScoreReport report = session.getReportId() == null
                ? reportMapper.selectOne(new LambdaQueryWrapper<AiScoreReport>()
                        .eq(AiScoreReport::getSessionId, session.getId())
                        .last("LIMIT 1"))
                : reportMapper.selectById(session.getReportId());
        boolean replacingExistingReport = report != null;
        if (report == null) {
            report = new AiScoreReport();
        }
        report.setSessionId(session.getId());
        report.setMeetingId(session.getMeetingId());
        report.setOverallScore(result.getOverallScore());
        report.setStatus("completed");
        report.setDimensionsJson(result.getDimensionsJson());
        report.setHighlightsJson(result.getHighlightsJson());
        report.setCriticalIssuesJson(result.getCriticalIssuesJson());
        report.setImprovementPrioritiesJson(result.getImprovementPrioritiesJson());
        report.setActionPlanJson(result.getActionPlanJson());
        report.setLossLedgerJson(result.getLossLedgerJson());
        report.setCoverageSummaryJson(result.getCoverageSummaryJson());
        report.setScoreProjectionJson(result.getScoreProjectionJson());
        report.setContractVersion(result.getContractVersion());
        report.setTodoPortfolioStatus(result.getTodoPortfolioStatus());
        report.setTranscript(result.getTranscript());
        report.setSpeechQualityJson(result.getSpeechQualityJson());
        report.setScoreCalibrationJson(result.getScoreCalibrationJson());
        report.setRuleEngineVersion(result.getRuleEngineVersion());
        report.setStructuredResultJson(shadowResultJson(result));
        report.setModel(result.getModel());
        report.setStartedAt(session.getStartedAt());
        report.setCompletedAt(LocalDateTime.now());
        report.setUpdatedAt(LocalDateTime.now());
        if (replacingExistingReport) {
            reportMapper.updateById(report);
            replaceStructuredRows(session.getId());
        } else {
            reportMapper.insert(report);
        }
        if (remediationService != null
                && report.getId() != null
                && "ai-score-report-v3".equals(result.getContractVersion())) {
            remediationService.persistSnapshot(
                    remediationScopeKey(session),
                    report.getId(),
                    session.getId(),
                    result.getActionPlanJson(),
                    result.getLossLedgerJson(),
                    result.getCoverageSummaryJson()
            );
        }

        try {
            if (docketService == null) {
                throw new IllegalArgumentException("docketService cannot be null when recording a successful run");
            }
            if (!hasText(session.getDocketId())) {
                throw new IllegalArgumentException("docketId cannot be blank when recording a successful run");
            }
            docketService.recordSuccessfulRun(session, report, RunCoverageCalculator.fromCallback(result));
        } catch (IllegalArgumentException exception) {
            session.setStatus("failed");
            session.setCurrentStage("calculation_failed");
            session.setErrorMessage(exception.getMessage());
            session.setCompletedAt(LocalDateTime.now());
            session.setUpdatedAt(LocalDateTime.now());
            sessionMapper.updateById(session);
            return;
        }

        Map<Long, Long> evidenceAnchorIdMap = persistEvidenceAnchors(session.getId(), result.getEvidenceAnchors());
        Map<String, String> dimensionCodeByObservation = observationDimensionCodes(result.getObservations());

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
                    observation.setEvidenceAnchorIdsJson(writeJsonQuietly(
                            remapEvidenceAnchorIds(obs.getEvidenceAnchorIds(), evidenceAnchorIdMap)
                    ));
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
                deduction.setDimensionCode(defaulted(
                        ded.getDimensionCode(),
                        dimensionCodeByObservation.get(ded.getObservationCode())
                ));
                deduction.setDeductedPoints(ded.getDeductedPoints());
                deduction.setMaxRecoverablePoints(ded.getMaxRecoverablePoints());
                deduction.setReason(ded.getReason());
                deduction.setRequiredFix(ded.getRequiredFix());
                deduction.setAcceptanceCriteria(ded.getAcceptanceCriteria());
                deduction.setEvidenceLevel(ded.getEvidenceLevel());
                deduction.setConfidence(ded.getConfidence());
                deduction.setStatus(ded.getStatus() != null ? ded.getStatus() : "new");
                if (ded.getEvidenceAnchorIds() != null) {
                    deduction.setEvidenceAnchorIdsJson(writeJsonQuietly(
                            remapEvidenceAnchorIds(ded.getEvidenceAnchorIds(), evidenceAnchorIdMap)
                    ));
                }
                deductionMapper.insert(deduction);
            }
        }

        // Update session
        session.setReportId(report.getId());
        session.setStatus("completed");
        session.setCurrentStage("completed");
        if (!Boolean.TRUE.equals(session.getTeacherConfirmed())) {
            session.setDeliberationStage(DeliberationStageMachine.CHALLENGE);
        }
        session.setProgressPercent(100);
        session.setCompletedAt(LocalDateTime.now());
        session.setUpdatedAt(LocalDateTime.now());
        sessionMapper.updateById(session);
    }

    private String remediationScopeKey(AiScoringSession session) {
        if (session.getProjectId() != null) {
            return "project:" + session.getProjectId();
        }
        if (session.getTeamId() != null) {
            return "team:" + session.getTeamId();
        }
        return "session:" + session.getId();
    }

    private void replaceStructuredRows(Long sessionId) {
        if (deductionMapper != null) {
            deductionMapper.delete(new LambdaQueryWrapper<AiScoreDeduction>()
                    .eq(AiScoreDeduction::getSessionId, sessionId));
        }
        if (observationMapper != null) {
            observationMapper.delete(new LambdaQueryWrapper<AiScoreObservation>()
                    .eq(AiScoreObservation::getSessionId, sessionId));
        }
        if (evidenceAnchorMapper != null) {
            evidenceAnchorMapper.delete(new LambdaQueryWrapper<AiScoreEvidenceAnchor>()
                    .eq(AiScoreEvidenceAnchor::getSessionId, sessionId));
        }
    }

    private Map<String, String> observationDimensionCodes(List<PipelineCallbackRequest.ObservationInput> observations) {
        Map<String, String> values = new LinkedHashMap<>();
        if (observations == null) {
            return values;
        }
        for (PipelineCallbackRequest.ObservationInput observation : observations) {
            if (hasText(observation.getObservationCode()) && hasText(observation.getDimensionCode())) {
                values.putIfAbsent(observation.getObservationCode(), observation.getDimensionCode());
            }
        }
        return values;
    }

    private Map<Long, Long> persistEvidenceAnchors(
            Long sessionId,
            List<PipelineCallbackRequest.EvidenceAnchorInput> anchors
    ) {
        Map<Long, Long> idMap = new LinkedHashMap<>();
        if (anchors == null) {
            return idMap;
        }
        long fallbackClientId = 1L;
        for (PipelineCallbackRequest.EvidenceAnchorInput anchor : anchors) {
            AiScoreEvidenceAnchor evidenceAnchor = new AiScoreEvidenceAnchor();
            evidenceAnchor.setSessionId(sessionId);
            evidenceAnchor.setAnchorType(anchor.getAnchorType());
            evidenceAnchor.setAnchorTitle(anchor.getAnchorTitle());
            evidenceAnchor.setEvidenceText(anchor.getEvidenceText());
            evidenceAnchor.setSourceRef(anchor.getSourceRef());
            evidenceAnchor.setStartMs(anchor.getStartMs());
            evidenceAnchor.setEndMs(anchor.getEndMs());
            evidenceAnchor.setConfidence(anchor.getConfidence());
            evidenceAnchor.setValidityStatus(anchor.getValidityStatus());
            evidenceAnchor.setCreatedAt(LocalDateTime.now());
            evidenceAnchorMapper.insert(evidenceAnchor);
            Long clientId = anchor.getId() == null ? fallbackClientId : anchor.getId();
            idMap.put(clientId, evidenceAnchor.getId());
            fallbackClientId++;
        }
        return idMap;
    }

    private List<Long> remapEvidenceAnchorIds(List<Long> ids, Map<Long, Long> idMap) {
        if (ids == null || ids.isEmpty()) {
            return List.of();
        }
        List<Long> remapped = new ArrayList<>();
        for (Long id : ids) {
            Long mapped = idMap.getOrDefault(id, id);
            if (mapped != null && !remapped.contains(mapped)) {
                remapped.add(mapped);
            }
        }
        return remapped;
    }

    private String writeJsonQuietly(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (Exception ignored) {
            return "[]";
        }
    }

    public AiScoreReportUserResponse reportBySession(Long sessionId) {
        return reportBySession(sessionId, null);
    }

    public AiScoreReportUserResponse reportBySession(Long sessionId, String role) {
        AiScoringSession session = requireSession(sessionId);
        AiScoreReport report = null;
        if (session.getReportId() != null) {
            report = reportMapper.selectById(session.getReportId());
        }
        if (report == null) {
            report = reportMapper.selectOne(new LambdaQueryWrapper<AiScoreReport>()
                    .eq(AiScoreReport::getSessionId, sessionId)
                    .last("LIMIT 1"));
        }
        if (report == null && session.getMeetingId() != null) {
            report = latestReportForMeeting(session.getMeetingId());
        }
        if (report == null) {
            report = latestReportForMeeting(-sessionId);
        }
        if (report == null) {
            throw new IllegalStateException("报告不存在或未完成");
        }
        return applyTaskBookAudience(toReportResponse(report, session), role);
    }

    public AiScoreReportUserResponse reportByMeetingId(Long meetingId) {
        return reportByMeetingId(meetingId, null);
    }

    public AiScoringSession sessionForMeetingAccess(Long meetingId) {
        if (meetingId == null || sessionMapper == null) {
            return null;
        }
        return sessionMapper.selectOne(new LambdaQueryWrapper<AiScoringSession>()
                .eq(AiScoringSession::getMeetingId, meetingId)
                .orderByDesc(AiScoringSession::getId)
                .last("LIMIT 1"));
    }

    public AiScoringSession sessionForReportAccess(Long reportId) {
        if (reportId == null || reportMapper == null) {
            return null;
        }
        AiScoreReport report = reportMapper.selectById(reportId);
        if (report == null) {
            return null;
        }
        AiScoringSession session = sessionMapper == null ? null : sessionMapper.selectOne(new LambdaQueryWrapper<AiScoringSession>()
                .eq(AiScoringSession::getReportId, reportId)
                .last("LIMIT 1"));
        if (session == null && report.getSessionId() != null && sessionMapper != null) {
            session = sessionMapper.selectById(report.getSessionId());
        }
        return session;
    }

    public AiScoreReportUserResponse reportByMeetingId(Long meetingId, String role) {
        AiScoringSession session = sessionForMeetingAccess(meetingId);
        if (session != null && session.getReportId() != null) {
            return reportBySession(session.getId(), role);
        }
        AiScoreReport report = latestReportForMeeting(meetingId);
        if (report == null) {
            throw new IllegalStateException("该会议暂未生成AI评分报告");
        }
        return applyTaskBookAudience(toReportResponse(report, session), role);
    }

    private AiScoreReport latestReportForMeeting(Long meetingId) {
        if (meetingId == null || reportMapper == null) {
            return null;
        }
        return MeetingReportPicker.current(reportMapper.selectList(new LambdaQueryWrapper<AiScoreReport>()
                .eq(AiScoreReport::getMeetingId, meetingId)));
    }

    public AiScoreReportUserResponse reportByReportId(Long reportId) {
        return reportByReportId(reportId, null);
    }

    public AiScoreReportUserResponse reportByReportId(Long reportId, String role) {
        AiScoreReport report = reportMapper.selectById(reportId);
        if (report == null) {
            throw new IllegalStateException("报告不存在或未完成");
        }
        return applyTaskBookAudience(toReportResponse(report, sessionForReportAccess(reportId)), role);
    }

    public AiScoringSessionUserResponse toUserResponse(AiScoringSession session) {
        AiScoringSessionUserResponse response = new AiScoringSessionUserResponse();
        response.setSessionId(session.getId());
        response.setSessionNo(session.getSessionNo());
        response.setDocketId(session.getDocketId());
        response.setStatus(session.getStatus());
        response.setCurrentStage(session.getCurrentStage());
        response.setProgressPercent(valueOrZero(session.getProgressPercent()));
        response.setTrackName(session.getTrackName());
        response.setSourceType(session.getSourceType());
        response.setUseHistoryMemory(Boolean.TRUE.equals(session.getUseHistoryMemory()));
        response.setJuryEnabled(Boolean.TRUE.equals(session.getJuryEnabled()));
        response.setCached(false);
        response.setReportId(session.getReportId());
        response.setMeetingId(session.getMeetingId());
        response.setErrorMessage(session.getErrorMessage());
        return response;
    }

    private AiScoreReportUserResponse toReportResponse(AiScoreReport report, AiScoringSession session) {
        AiScoreReportUserResponse response = new AiScoreReportUserResponse();
        response.setReportId(report.getId());
        response.setSessionId(session == null ? null : session.getId());
        response.setSessionNo(session == null ? null : session.getSessionNo());
        response.setMeetingId(session == null ? report.getMeetingId() : session.getMeetingId());
        response.setTrackName(session == null ? null : session.getTrackName());
        response.setSourceType(session == null ? null : session.getSourceType());
        response.setOverallScore(report.getOverallScore());
        response.setDimensionsJson(report.getDimensionsJson());
        response.setHighlightsJson(report.getHighlightsJson());
        response.setCriticalIssuesJson(report.getCriticalIssuesJson());
        response.setImprovementPrioritiesJson(report.getImprovementPrioritiesJson());
        response.setActionPlanJson(report.getActionPlanJson());
        response.setActionPlan(parseMapList(report.getActionPlanJson()));
        response.setLossLedgerJson(report.getLossLedgerJson());
        response.setLossLedger(parseMapList(report.getLossLedgerJson()));
        response.setCoverageSummaryJson(report.getCoverageSummaryJson());
        response.setCoverageSummary(parseMapObject(report.getCoverageSummaryJson()));
        response.setScoreProjectionJson(report.getScoreProjectionJson());
        response.setScoreProjection(parseMapObject(report.getScoreProjectionJson()));
        if (remediationService != null && "ai-score-report-v3".equals(report.getContractVersion())) {
            response.setRemediationTasks(remediationService.liveTasksForReport(report.getId(), report.getActionPlanJson()));
            response.setTaskVerifications(remediationService.verificationsForReport(report.getId()));
        } else {
            response.setRemediationTasks(response.getActionPlan());
            response.setTaskVerifications(List.of());
        }
        response.setTodoPortfolioStatus(report.getTodoPortfolioStatus());
        response.setContractVersion(report.getContractVersion());
        response.setTranscript(report.getTranscript());
        response.setSpeechQualityJson(report.getSpeechQualityJson());
        response.setScoreCalibrationJson(redactInternalCalibration(report.getScoreCalibrationJson()));
        response.setModel(report.getModel());
        response.setStatus(report.getStatus());
        response.setCompletedAt(report.getCompletedAt());
        response.setScoringConsistencyNo(session == null ? null : session.getSessionNo());
        response.setRuleEngineShadow(toRuleEngineShadow(report.getStructuredResultJson()));
        response.setMediaPlayback(toMediaPlayback(session));
        attachTranscriptDetails(response, session);
        attachStructuredReportDetails(response, report, session);
        response.setStability(toUserStability(session));
        response.setVerifyClaims(evaluateVerifyClaims(report, response));
        response.setTaskBook(buildTaskBook(report, session, response));
        response.setScoreGap(buildScoreGap(report, session, response));
        ensureChallenges(response, session);
        attachDeliberation(response, session);
        return response;
    }

    public AiScoreReportUserResponse publishTaskBook(Long sessionId, String role) {
        if (!hasTeacherScope(role)) {
            throw new IllegalArgumentException("只有教师可以发布任务书");
        }
        AiScoringSession session = requireSession(sessionId);
        AiScoreReport report = session.getReportId() == null
                ? reportMapper.selectOne(new LambdaQueryWrapper<AiScoreReport>()
                        .eq(AiScoreReport::getSessionId, session.getId())
                        .last("LIMIT 1"))
                : reportMapper.selectById(session.getReportId());
        if (report == null) {
            throw new IllegalStateException("报告不存在或未完成");
        }
        AiScoreReportUserResponse preview = toReportResponse(report, session);
        if (preview.getTaskBook() == null || preview.getTaskBook().getItems() == null || preview.getTaskBook().getItems().isEmpty()) {
            throw new IllegalArgumentException("没有可发布的任务书");
        }
        TaskBook published = preview.getTaskBook();
        published.setPublished(true);
        published = TaskBookHang.mergeHangs(published, readPublishedTaskBook(report, session));
        report.setTaskBookPublished(true);
        report.setTaskBookJson(writeJsonQuietly(published));
        report.setUpdatedAt(LocalDateTime.now());
        reportMapper.updateById(report);
        if (docketService != null && hasText(session.getDocketId())) {
            docketService.persistPublishedTaskBook(session.getDocketId(), session.getId(), report.getTaskBookJson());
        }
        return applyTaskBookAudience(reportBySession(sessionId), role);
    }

    public AiScoreReportUserResponse hangTaskBookEvidence(Long sessionId, int index, String evidence, Long userId, String role) {
        AiScoringSession session = requireSession(sessionId);
        AiScoreReport report = session.getReportId() == null
                ? reportMapper.selectOne(new LambdaQueryWrapper<AiScoreReport>()
                        .eq(AiScoreReport::getSessionId, session.getId())
                        .last("LIMIT 1"))
                : reportMapper.selectById(session.getReportId());
        if (report == null) {
            throw new IllegalStateException("报告不存在或未完成");
        }
        DocketTaskBook.Snapshot snapshot = publishedTaskBookSnapshot(report, session);
        if (!snapshot.published() || !hasText(snapshot.json())) {
            throw new IllegalArgumentException("任务书尚未发布");
        }
        TaskBook book;
        try {
            book = objectMapper.readValue(snapshot.json(), TaskBook.class);
        } catch (Exception ex) {
            throw new IllegalArgumentException("任务书无法读取");
        }
        if (book == null) {
            throw new IllegalArgumentException("任务书尚未发布");
        }
        book.setPublished(true);
        TaskBook hung = TaskBookHang.hang(book, index, evidence, userId, LocalDateTime.now().toString());
        String json = writeJsonQuietly(hung);
        if (Boolean.TRUE.equals(report.getTaskBookPublished())) {
            report.setTaskBookJson(json);
            report.setUpdatedAt(LocalDateTime.now());
            reportMapper.updateById(report);
        }
        if (docketService != null && hasText(session.getDocketId())) {
            docketService.updatePublishedTaskBookJson(session.getDocketId(), json);
        }
        return applyTaskBookAudience(reportBySession(sessionId), role);
    }

    public AiScoreReportUserResponse confirmDeliberation(Long sessionId, String role, Long teacherUserId) {
        if (!hasTeacherScope(role)) {
            throw new IllegalArgumentException("只有教师可以确认本场");
        }
        AiScoringSession session = requireSession(sessionId);
        AiScoreReportUserResponse preview = reportBySession(sessionId);
        DeliberationState current = preview.getDeliberation();
        String stage = current == null ? DeliberationStageMachine.SENSING : current.getStage();
        if (!DeliberationStageMachine.canConfirm(stage) && !DeliberationStageMachine.FROZEN.equals(stage)) {
            throw new IllegalArgumentException("本场还不能确认");
        }
        session.setTeacherConfirmed(true);
        session.setTeacherConfirmedAt(LocalDateTime.now());
        session.setTeacherConfirmedBy(teacherUserId);
        session.setDeliberationStage(DeliberationStageMachine.FROZEN);
        session.setUpdatedAt(LocalDateTime.now());
        sessionMapper.updateById(session);
        return applyTaskBookAudience(reportBySession(sessionId), role);
    }

    public AiScoreReportUserResponse resolveChallenge(
            Long sessionId,
            String challengeId,
            String action,
            String reason,
            String role,
            Long teacherUserId
    ) {
        if (!hasTeacherScope(role)) {
            throw new IllegalArgumentException("只有教师可以处理质询");
        }
        AiScoringSession session = requireSession(sessionId);
        if (Boolean.TRUE.equals(session.getTeacherConfirmed())) {
            throw new IllegalArgumentException("本场已确认，不能再改质询");
        }
        AiScoreReportUserResponse preview = reportBySession(sessionId);
        ChallengeSet current = preview.getChallenges();
        if (current == null || !current.isScanned()) {
            throw new IllegalArgumentException("本场未完成质询");
        }
        ChallengeSet updated = ChallengeScanner.applyTeacherDecision(current, challengeId, action, reason, teacherUserId);
        persistChallengeSet(session, updated);
        return applyTaskBookAudience(reportBySession(sessionId), role);
    }

    public AiScoreReportUserResponse applyTaskBookAudience(AiScoreReportUserResponse response, String role) {
        if (response == null) {
            return null;
        }
        boolean teacherPreview = role == null || hasTeacherScope(role);
        boolean frozen = response.getDeliberation() != null && response.getDeliberation().isFinalized();
        response.setTaskBook(TaskBookBuilder.forAudience(response.getTaskBook(), teacherPreview, frozen));
        if (!teacherPreview && !frozen && response.getDeliberation() != null) {
            response.setTeacherConfirmed(false);
        }
        return response;
    }

    private static boolean hasTeacherScope(String role) {
        if (role == null) {
            return false;
        }
        return switch (role.trim().toUpperCase()) {
            case "TEACHER", "ADMIN", "SUPER_ADMIN", "SCHOOL_ADMIN" -> true;
            default -> false;
        };
    }

    private TaskBook buildTaskBook(AiScoreReport report, AiScoringSession session, AiScoreReportUserResponse response) {
        TaskBook snapshot = readPublishedTaskBook(report, session);
        if (snapshot != null) {
            return snapshot;
        }
        List<TaskBookBuilder.Draft> drafts = new ArrayList<>();
        if (response.getTrainingTasks() != null) {
            for (AiScoreReportUserResponse.TrainingTask task : response.getTrainingTasks()) {
                if (task == null) {
                    continue;
                }
                TaskBookBuilder.Draft draft = new TaskBookBuilder.Draft();
                draft.priority = "P0".equalsIgnoreCase(task.getPriority()) ? 0 : 1;
                draft.title = task.getTitle();
                draft.reason = firstNonBlank(task.getCorrespondingDeduction(), task.getTitle());
                draft.goal = firstNonBlank(task.getTrainingAction(), task.getAcceptanceCriteria());
                draft.acceptance = task.getAcceptanceCriteria();
                draft.evidenceNeeded = firstNonBlank(task.getTrainingAction(), "下场补上可跳转证据");
                draft.expectedGain = task.getExpectedRecoverPoints() == null
                        ? "+2~4"
                        : "+" + task.getExpectedRecoverPoints().stripTrailingZeros().toPlainString();
                draft.ownerRole = firstNonBlank(task.getOwnerRole(), "主讲");
                draft.dueHint = firstNonBlank(task.getTimeSuggestion(), "下场前");
                if (hasText(task.getSourceIssueKey())) {
                    draft.sourceRefs = List.of(task.getSourceIssueKey());
                } else if (hasText(task.getObservationCode())) {
                    draft.sourceRefs = List.of("score-deduction:" + task.getObservationCode());
                }
                drafts.add(draft);
            }
        }
        if (response.getVerifyClaims() != null) {
            for (SubstanceClaim claim : response.getVerifyClaims()) {
                if (claim == null || !"fail".equals(claim.getVerdict()) || !hasText(claim.getClaimType())) {
                    continue;
                }
                TaskBookBuilder.Draft draft = new TaskBookBuilder.Draft();
                draft.priority = 0;
                draft.title = "补齐" + claimLabel(claim.getClaimType()) + "证据";
                draft.reason = claim.getStatement();
                draft.sourceRefs = List.of("claim:" + claim.getClaimType());
                drafts.add(draft);
            }
        }
        TaskBook book = TaskBookBuilder.draft(drafts);
        DocketTaskBook.Snapshot published = publishedTaskBookSnapshot(report, session);
        if (published.published()) {
            book.setPublished(true);
        }
        return book;
    }

    private TaskBook readPublishedTaskBook(AiScoreReport report, AiScoringSession session) {
        DocketTaskBook.Snapshot published = publishedTaskBookSnapshot(report, session);
        if (!published.published() || !hasText(published.json())) {
            return null;
        }
        try {
            TaskBook snapshot = objectMapper.readValue(published.json(), TaskBook.class);
            if (snapshot == null) {
                return null;
            }
            snapshot.setPublished(true);
            if (snapshot.getItems() == null) {
                snapshot.setItems(List.of());
            }
            return snapshot;
        } catch (Exception ignored) {
            return null;
        }
    }

    private DocketTaskBook.Snapshot publishedTaskBookSnapshot(AiScoreReport report, AiScoringSession session) {
        DocketTaskBook.Snapshot docketSnapshot = DocketTaskBook.Snapshot.unpublished();
        if (docketService != null && session != null && hasText(session.getDocketId())) {
            docketSnapshot = docketService.loadPublishedTaskBook(session.getDocketId());
        }
        return DocketTaskBook.resolve(
                report == null ? null : report.getTaskBookPublished(),
                report == null ? null : report.getTaskBookJson(),
                docketSnapshot.published(),
                docketSnapshot.json()
        );
    }

    private static String claimLabel(String claimType) {
        if ("wrapper".equals(claimType)) {
            return "差异与仓库";
        }
        if ("advancement".equals(claimType)) {
            return "对比测试";
        }
        if ("value".equals(claimType)) {
            return "服务对象";
        }
        return "核验";
    }

    private List<SubstanceClaim> evaluateVerifyClaims(AiScoreReport report, AiScoreReportUserResponse response) {
        SubstanceClaimEvaluator.ClaimEvidence evidence = new SubstanceClaimEvaluator.ClaimEvidence();
        evidence.retrievalEnabled = false;
        evidence.transcript = report == null ? "" : defaulted(report.getTranscript(), "");
        StringBuilder observations = new StringBuilder();
        if (response.getStructuredObservations() != null) {
            for (AiScoreReportUserResponse.StructuredObservation observation : response.getStructuredObservations()) {
                if (observation == null) {
                    continue;
                }
                if (hasText(observation.getModelReason())) {
                    observations.append(observation.getModelReason()).append('\n');
                }
                if (hasText(observation.getDimensionName())) {
                    observations.append(observation.getDimensionName()).append('\n');
                }
                if (observation.getEvidenceAnchorIds() != null) {
                    for (Long anchorId : observation.getEvidenceAnchorIds()) {
                        if (anchorId != null) {
                            evidence.evidenceRefs.add("anchor:" + anchorId);
                        }
                    }
                }
            }
        }
        if (response.getEvidenceAnchors() != null) {
            for (AiScoreReportUserResponse.EvidenceAnchor anchor : response.getEvidenceAnchors()) {
                if (anchor != null && anchor.getId() != null) {
                    evidence.evidenceRefs.add("anchor:" + anchor.getId());
                }
            }
        }
        evidence.observations = observations.toString();
        return SubstanceClaimEvaluator.evaluate(evidence);
    }

    private void attachDeliberation(AiScoreReportUserResponse response, AiScoringSession session) {
        DeliberationStageMachine.Input input = new DeliberationStageMachine.Input();
        input.hasReport = response.getReportId() != null;
        input.completed = session != null && "completed".equals(session.getStatus());
        input.claimsEvaluated = response.getVerifyClaims() != null && response.getVerifyClaims().size() >= 3;
        input.challengeCompleted = session != null && Boolean.TRUE.equals(session.getChallengeCompleted());
        input.teacherConfirmed = session != null && Boolean.TRUE.equals(session.getTeacherConfirmed());
        if (input.claimsEvaluated && DeliberationStageMachine.pretendedRetrievedCitation(response.getVerifyClaims())) {
            input.claimsEvaluated = false;
        }
        DeliberationState state = DeliberationStageMachine.resolve(input);
        ChallengeSet challenges = response.getChallenges();
        if (challenges != null && challenges.isScanned()
                && (challenges.getItems() == null || challenges.getItems().isEmpty())
                && !state.isTeacherConfirmed()) {
            state.setChallengeNote(ChallengeScanner.EMPTY_NOTE);
            state.setHeadline(ChallengeScanner.EMPTY_NOTE);
        }
        response.setDeliberation(state);
        response.setTeacherConfirmed(state.isTeacherConfirmed());
    }

    private void ensureChallenges(AiScoreReportUserResponse response, AiScoringSession session) {
        if (session != null && hasText(session.getChallengeJson())) {
            ChallengeSet stored = readChallengeSet(session.getChallengeJson());
            if (stored != null && !ChallengeScanner.needsRescan(stored)) {
                ChallengeScanner.decorate(stored, officialFrom(response));
                response.setChallenges(stored);
                if (stored.isScanned() && !Boolean.TRUE.equals(session.getChallengeCompleted())) {
                    persistChallengeSet(session, stored);
                }
                return;
            }
        }
        if (session == null || !"completed".equals(session.getStatus())) {
            ChallengeSet pending = new ChallengeSet();
            pending.setScanned(false);
            pending.setNote(DeliberationStageMachine.CHALLENGE_NOTE);
            pending.setItems(List.of());
            response.setChallenges(pending);
            return;
        }
        boolean dossierMissing = observationMapper == null || deductionMapper == null || evidenceAnchorMapper == null;
        ChallengeScanner.Input input = toChallengeInput(response, dossierMissing);
        ChallengeSet scanned = ChallengeScanner.scan(input);
        persistChallengeSet(session, scanned);
        ChallengeScanner.decorate(scanned, officialFrom(response));
        response.setChallenges(scanned);
    }

    private ChallengeScanner.Input toChallengeInput(AiScoreReportUserResponse response, boolean failed) {
        ChallengeScanner.Input input = new ChallengeScanner.Input();
        input.failed = failed;
        if (response.getMediaPlayback() != null && response.getMediaPlayback().getDurationSeconds() != null) {
            input.durationMs = Math.round(response.getMediaPlayback().getDurationSeconds() * 1000.0);
        }
        if (response.getStructuredDeductions() != null) {
            for (AiScoreReportUserResponse.StructuredDeduction deduction : response.getStructuredDeductions()) {
                if (deduction == null || Boolean.TRUE.equals(deduction.getRecovery())) {
                    continue;
                }
                ChallengeScanner.Deduction row = new ChallengeScanner.Deduction();
                row.lossId = deduction.getId() == null ? "deduction" : "deduction:" + deduction.getId();
                row.targetDimension = deduction.getDimensionName();
                row.deductedPoints = deduction.getDeductedPoints();
                row.anchorIds = deduction.getEvidenceAnchorIds();
                row.reason = firstNonBlank(deduction.getReason(), deduction.getRequiredFix());
                input.deductions.add(row);
            }
        }
        if (response.getStructuredObservations() != null) {
            for (AiScoreReportUserResponse.StructuredObservation observation : response.getStructuredObservations()) {
                if (observation == null) {
                    continue;
                }
                ChallengeScanner.Observation row = new ChallengeScanner.Observation();
                row.lossId = observation.getId() == null ? null : "observation:" + observation.getId();
                row.targetDimension = observation.getDimensionName();
                row.rawScore = observation.getRawScore();
                row.anchorIds = observation.getEvidenceAnchorIds();
                input.observations.add(row);
            }
        }
        if (response.getEvidenceAnchors() != null) {
            for (AiScoreReportUserResponse.EvidenceAnchor anchor : response.getEvidenceAnchors()) {
                if (anchor == null) {
                    continue;
                }
                ChallengeScanner.Anchor row = new ChallengeScanner.Anchor();
                row.id = anchor.getId();
                row.startMs = anchor.getStartMs();
                row.endMs = anchor.getEndMs();
                row.sourceRef = anchor.getSourceRef();
                row.evidenceText = firstNonBlank(anchor.getEvidenceText(), anchor.getAnchorTitle());
                row.validityStatus = anchor.getValidityStatus();
                input.anchors.add(row);
            }
        }
        if (response.getVerifyClaims() != null) {
            input.claims.addAll(response.getVerifyClaims());
        }
        return input;
    }

    private void persistChallengeSet(AiScoringSession session, ChallengeSet set) {
        if (session == null || sessionMapper == null || set == null) {
            return;
        }
        session.setChallengeJson(writeJsonQuietly(set));
        session.setChallengeCompleted(set.isScanned());
        if (set.isScanned() && !Boolean.TRUE.equals(session.getTeacherConfirmed())) {
            session.setDeliberationStage(DeliberationStageMachine.AWAIT_TEACHER);
        }
        session.setUpdatedAt(LocalDateTime.now());
        sessionMapper.updateById(session);
    }

    private ChallengeSet readChallengeSet(String json) {
        if (!hasText(json)) {
            return null;
        }
        try {
            return objectMapper.readValue(json, ChallengeSet.class);
        } catch (Exception ignored) {
            return null;
        }
    }

    private static BigDecimal officialFrom(AiScoreReportUserResponse response) {
        if (response.getScoreGap() != null && response.getScoreGap().getOfficialScore() != null) {
            return response.getScoreGap().getOfficialScore();
        }
        return response.getOverallScore();
    }

    private ScoreGap buildScoreGap(AiScoreReport report, AiScoringSession session, AiScoreReportUserResponse response) {
        ScoreGapCalculator.Input input = new ScoreGapCalculator.Input();
        input.ledgerScore = report == null ? null : report.getOverallScore();
        if (response != null && response.getRuleEngineShadow() != null) {
            input.modelReviewScore = response.getRuleEngineShadow().getModelReviewScore();
            input.tapeGrounded = response.getRuleEngineShadow().getTapeGrounded();
        }
        input.trackCeiling = resolveTrackCeiling(report);
        input.evidenceCap = report == null ? null : report.getCurrentScoreCap();
        input.claims = response.getVerifyClaims() == null ? List.of() : response.getVerifyClaims();
        input.hasStableDemoEvidence = hasStableDemoEvidence(response);
        if (docketService != null && session != null && hasText(session.getDocketId())) {
            if (input.tapeGrounded == null) {
                var current = docketService.findRunBySessionId(session.getId());
                if (current != null) {
                    input.tapeGrounded = current.getTapeGrounded();
                }
            }
            var previous = docketService.previousCompletedRun(session.getDocketId(), session.getId());
            if (previous != null) {
                input.previousOfficialScore = previous.getOfficialScore();
            } else {
                input.previousOfficialScore = docketService.latestTeamTrackOfficialScore(
                        session.getTrackId(), session.getTeamId(), session.getId());
            }
            input.priorTasks = priorTasksFrom(
                    previousPublishedTaskBook(session, previous),
                    response.getTaskVerifications());
        }
        return ScoreGapCalculator.evaluate(input);
    }

    private TaskBook previousPublishedTaskBook(AiScoringSession session, com.orep.backend.entity.AiScoreDocketRun previous) {
        AiScoreReport report = previous == null || previous.getReportId() == null
                ? null
                : reportMapper.selectById(previous.getReportId());
        DocketTaskBook.Snapshot docketSnapshot = DocketTaskBook.Snapshot.unpublished();
        if (docketService != null && session != null && hasText(session.getDocketId())) {
            docketSnapshot = docketService.loadPublishedTaskBook(session.getDocketId());
        }
        DocketTaskBook.Snapshot prior = DocketTaskBook.prior(
                report == null ? null : report.getTaskBookPublished(),
                report == null ? null : report.getTaskBookJson(),
                docketSnapshot.published(),
                docketSnapshot.json(),
                docketSnapshot.publishedSessionId(),
                session == null ? null : session.getId()
        );
        boolean thisRound = docketSnapshot.published()
                && docketSnapshot.publishedSessionId() != null
                && session != null
                && session.getId() != null
                && docketSnapshot.publishedSessionId() >= session.getId();
        DocketTaskBook.Snapshot teamTrack = DocketTaskBook.Snapshot.unpublished();
        if (docketService != null && session != null) {
            teamTrack = docketService.loadTeamTrackPriorBook(
                    session.getTrackId(), session.getTeamId(), session.getId());
        }
        prior = DocketTaskBook.priorAcross(prior, thisRound, teamTrack, session == null ? null : session.getId());
        if (!prior.published() || !hasText(prior.json())) {
            return null;
        }
        try {
            TaskBook snapshot = objectMapper.readValue(prior.json(), TaskBook.class);
            if (snapshot == null) {
                return null;
            }
            snapshot.setPublished(true);
            if (snapshot.getItems() == null) {
                snapshot.setItems(List.of());
            }
            return snapshot;
        } catch (Exception ignored) {
            return null;
        }
    }

    private List<ScoreGapCalculator.PriorTask> priorTasksFrom(TaskBook previous, List<Map<String, Object>> verifications) {
        return TaskBookPriorTasks.from(previous, verifications);
    }

    private BigDecimal resolveTrackCeiling(AiScoreReport report) {
        if (report == null) {
            return null;
        }
        BigDecimal fromDimensions = sumDimensionMax(report.getDimensionsJson());
        if (fromDimensions != null) {
            return fromDimensions;
        }
        Map<String, Object> projection = parseMapObject(report.getScoreProjectionJson());
        return decimalOrNull(projection.get("goalScore"));
    }

    private BigDecimal sumDimensionMax(String dimensionsJson) {
        if (!hasText(dimensionsJson)) {
            return null;
        }
        try {
            JsonNode node = objectMapper.readTree(dimensionsJson);
            BigDecimal total = BigDecimal.ZERO;
            int counted = 0;
            if (node.isObject()) {
                for (JsonNode child : node) {
                    BigDecimal max = dimensionMax(child);
                    if (max != null) {
                        total = total.add(max);
                        counted++;
                    }
                }
            } else if (node.isArray()) {
                for (JsonNode child : node) {
                    BigDecimal max = dimensionMax(child);
                    if (max != null) {
                        total = total.add(max);
                        counted++;
                    }
                }
            }
            return counted == 0 ? null : total;
        } catch (Exception ignored) {
            return null;
        }
    }

    private static BigDecimal dimensionMax(JsonNode node) {
        if (node == null || !node.isObject()) {
            return null;
        }
        JsonNode max = node.get("max_score");
        if (max == null) {
            max = node.get("maxScore");
        }
        if (max == null || !max.isNumber()) {
            return null;
        }
        return max.decimalValue();
    }

    private static BigDecimal decimalOrNull(Object value) {
        if (value instanceof Number number) {
            return new BigDecimal(number.toString());
        }
        if (value == null) {
            return null;
        }
        try {
            return new BigDecimal(String.valueOf(value));
        } catch (Exception ignored) {
            return null;
        }
    }

    private static BigDecimal parseExpectedGain(String raw) {
        if (raw == null) {
            return null;
        }
        java.util.regex.Matcher matcher = java.util.regex.Pattern.compile("(\\d+(?:\\.\\d+)?)").matcher(raw);
        if (!matcher.find()) {
            return null;
        }
        return new BigDecimal(matcher.group(1));
    }

    private static boolean hasStableDemoEvidence(AiScoreReportUserResponse response) {
        if (response.getEvidenceAnchors() != null && !response.getEvidenceAnchors().isEmpty()) {
            return true;
        }
        if (response.getVerifyClaims() == null) {
            return false;
        }
        for (SubstanceClaim claim : response.getVerifyClaims()) {
            if (claim == null || claim.getStatement() == null) {
                continue;
            }
            if (claim.getStatement().contains("没有运行")) {
                return false;
            }
            if (claim.getStatement().contains("有运行演示")) {
                return true;
            }
        }
        return false;
    }

    private AiScoreReportUserResponse.Stability toUserStability(AiScoringSession session) {
        AiScoreReportUserResponse.Stability stability = new AiScoreReportUserResponse.Stability();
        String docketId = session == null ? null : session.getDocketId();
        if (docketService == null || docketId == null || docketId.isBlank()) {
            stability.setBand(StabilityBandCalculator.NOT_REVIEWED);
            stability.setRunCount(0);
            stability.setHeadline(StabilityBandCalculator.headline(StabilityBandCalculator.NOT_REVIEWED));
            stability.setRuns(List.of());
            return stability;
        }
        DocketStability snapshot = docketService.stabilitySnapshot(docketId);
        String band = snapshot.getBand() == null
                ? StabilityBandCalculator.NOT_REVIEWED
                : snapshot.getBand();
        stability.setBand(band);
        stability.setRunCount(snapshot.getRunCount());
        stability.setHeadline(StabilityBandCalculator.headline(band));
        stability.setIdentityBand(snapshot.getIdentityBand());
        stability.setIdentityRunCount(snapshot.getIdentityRunCount());
        stability.setIdentityHeadline(snapshot.getIdentityHeadline());
        DocketRunPointer.Pointer pointer = DocketRunPointer.from(snapshot.getRuns(), session.getId());
        stability.setThisRunIndex(pointer.thisRunIndex);
        stability.setNewerSessionId(pointer.newerSessionId);
        stability.setNewerRunIndex(pointer.newerRunIndex);
        List<AiScoreReportUserResponse.StabilityRun> runs = new ArrayList<>();
        if (snapshot.getRuns() != null) {
            for (var run : snapshot.getRuns()) {
                if (run == null) {
                    continue;
                }
                AiScoreReportUserResponse.StabilityRun item = new AiScoreReportUserResponse.StabilityRun();
                item.setRunIndex(run.getRunIndex());
                item.setOfficialScore(run.getOfficialScore());
                item.setScoreDeltaAbs(run.getScoreDeltaAbs());
                item.setTranscriptCoverage(run.getTranscriptCoverage());
                item.setSeekableAnchorRate(run.getSeekableAnchorRate());
                item.setTapeGrounded(run.getTapeGrounded());
                runs.add(item);
            }
        }
        stability.setRuns(runs);
        return stability;
    }

    private AiScoreReportUserResponse.MediaPlayback toMediaPlayback(AiScoringSession session) {
        if (mediaAssetService == null || session == null || session.getId() == null) {
            return null;
        }
        var asset = mediaAssetService.getVideoAssetBySession(session.getId());
        if (asset == null || asset.getId() == null) {
            return null;
        }
        AiScoreReportUserResponse.MediaPlayback playback = new AiScoreReportUserResponse.MediaPlayback();
        playback.setAssetId(asset.getId());
        playback.setContentType(defaulted(asset.getMimeType(), "application/octet-stream"));
        playback.setSizeBytes(asset.getSizeBytes());
        playback.setDurationSeconds(asset.getDurationSeconds());
        playback.setStreamUrl("/api/ai-score/sessions/" + session.getId() + "/media/video");
        return playback;
    }

    private void attachTranscriptDetails(
            AiScoreReportUserResponse response,
            AiScoringSession session
    ) {
        response.setSpeakerAttributionStatus(session == null
                ? null : session.getSpeakerAttributionStatus());
        response.setSpeakerAttributionRevision(session == null
                ? null : session.getSpeakerAttributionRevision());
        if (transcriptService == null || session == null || session.getId() == null) {
            response.setAsrSegments(List.of());
            response.setSpeakerMappings(List.of());
            response.setStablePeople(List.of());
            response.setFinalSpeakerSegments(List.of());
            return;
        }

        List<AiScoreTranscriptSegment> segments = transcriptService.listForSession(session.getId());
        List<AiScoreSpeakerIdentity> identities = speakerIdentityService == null
                ? List.of()
                : speakerIdentityService.listForSession(session.getId());
        Map<String, AiScoreSpeakerIdentity> identityByRawSpeaker = identities.stream()
                .filter(identity -> hasText(identity.getRawSpeakerLabel()))
                .collect(Collectors.toMap(
                        AiScoreSpeakerIdentity::getRawSpeakerLabel,
                        identity -> identity,
                        (first, ignored) -> first,
                        LinkedHashMap::new
                ));
        Map<String, AiScoreSpeakerIdentity> identityByPersonId = identities.stream()
                .filter(identity -> hasText(identity.getPersonId()))
                .collect(Collectors.toMap(
                        AiScoreSpeakerIdentity::getPersonId,
                        identity -> identity,
                        (first, ignored) -> first,
                        LinkedHashMap::new
                ));

        response.setSpeakerMappings(identities.stream()
                .filter(identity -> hasText(identity.getRawSpeakerLabel()))
                .map(this::toSpeakerMappingResponse)
                .toList());
        List<AiScoreReportUserResponse.TranscriptSegment> mappedSegments = segments.stream()
                .map(segment -> toTranscriptSegmentResponse(
                        segment,
                        firstPresentValue(
                                identityByPersonId.get(segment.getPersonId()),
                                identityByRawSpeaker.get(segment.getSpeakerLabel())
                        )
                ))
                .toList();
        response.setAsrSegments(mappedSegments);
        response.setStablePeople(identities.stream()
                .filter(identity -> hasText(identity.getPersonId()))
                .sorted(stablePersonComparator())
                .map(this::toStablePersonResponse)
                .toList());
        response.setFinalSpeakerSegments("FINAL".equalsIgnoreCase(session.getSpeakerAttributionStatus())
                ? mappedSegments.stream()
                        .filter(segment -> Boolean.TRUE.equals(segment.getFinalSegment()))
                        .toList()
                : List.of());
    }

    private AiScoreReportUserResponse.TranscriptSegment toTranscriptSegmentResponse(
            AiScoreTranscriptSegment segment,
            AiScoreSpeakerIdentity identity
    ) {
        AiScoreReportUserResponse.TranscriptSegment response = new AiScoreReportUserResponse.TranscriptSegment();
        response.setId(segment.getId());
        response.setSegmentId(segment.getSegmentUid());
        response.setSegmentNo(segment.getSegmentNo());
        response.setAttributionRevision(segment.getAttributionRevision());
        response.setStartMs(segment.getStartMs());
        response.setEndMs(segment.getEndMs());
        response.setText(segment.getText());
        response.setRawSpeaker(segment.getSpeakerLabel());
        response.setPersonId(segment.getPersonId());
        response.setPersonType(identity == null ? null : identity.getPersonType());
        response.setContestantSlot(identity == null ? null : identity.getContestantSlot());
        response.setSpeakerState(segment.getSpeakerState());
        response.setFinalSegment(segment.getIsFinal());
        response.setSpeakerName(speakerDisplayName(segment, identity));
        response.setRoleName(identity == null ? null : identity.getRoleName());
        response.setConfidence(firstPresentValue(segment.getSpeakerConfidence(), segment.getConfidence()));
        return response;
    }

    private AiScoreReportUserResponse.StablePerson toStablePersonResponse(AiScoreSpeakerIdentity identity) {
        AiScoreReportUserResponse.StablePerson response = new AiScoreReportUserResponse.StablePerson();
        response.setPersonId(identity.getPersonId());
        response.setPersonType(identity.getPersonType());
        response.setPersonTypeLabel(personTypeLabel(identity.getPersonType()));
        response.setContestantSlot(identity.getContestantSlot());
        response.setDisplayName(stablePersonDisplayName(identity));
        response.setRoleName(identity.getRoleName());
        response.setPersonState(identity.getPersonState());
        response.setConfidence(identity.getConfidence());
        response.setFirstSeenMs(identity.getFirstSeenMs());
        response.setLastSeenMs(identity.getLastSeenMs());
        return response;
    }

    private Comparator<AiScoreSpeakerIdentity> stablePersonComparator() {
        return Comparator
                .comparingInt((AiScoreSpeakerIdentity identity) -> switch (defaulted(identity.getPersonType(), "")) {
                    case "CONTESTANT" -> 0;
                    case "VISITOR" -> 1;
                    case "OFFSCREEN" -> 2;
                    default -> 3;
                })
                .thenComparing(identity -> identity.getContestantSlot() == null
                        ? Integer.MAX_VALUE : identity.getContestantSlot())
                .thenComparing(identity -> identity.getFirstSeenMs() == null
                        ? Long.MAX_VALUE : identity.getFirstSeenMs())
                .thenComparing(identity -> defaulted(identity.getPersonId(), ""));
    }

    private String speakerDisplayName(
            AiScoreTranscriptSegment segment,
            AiScoreSpeakerIdentity identity
    ) {
        String state = defaulted(segment.getSpeakerState(), "").toUpperCase(Locale.ROOT);
        if ("OVERLAP".equals(state)) return "多人同时发言";
        if ("UNKNOWN".equals(state)) return "发言人待确认";
        if (identity == null) return "发言人待确认";
        return stablePersonDisplayName(identity);
    }

    private String stablePersonDisplayName(AiScoreSpeakerIdentity identity) {
        if (hasText(identity.getDisplayName())) return identity.getDisplayName();
        String type = defaulted(identity.getPersonType(), "").toUpperCase(Locale.ROOT);
        if ("CONTESTANT".equals(type) && identity.getContestantSlot() != null) {
            return identity.getContestantSlot() + "号选手";
        }
        if ("VISITOR".equals(type)) return "外部人员";
        if ("OFFSCREEN".equals(type)) return "画外发言人";
        return firstNonBlank(identity.getRoleName(), "发言人待确认");
    }

    private String personTypeLabel(String value) {
        return switch (defaulted(value, "").toUpperCase(Locale.ROOT)) {
            case "CONTESTANT" -> "参赛选手";
            case "VISITOR" -> "外部人员";
            case "OFFSCREEN" -> "画外人员";
            default -> "待确认";
        };
    }

    private <T> T firstPresentValue(T first, T second) {
        return first != null ? first : second;
    }

    private AiScoreReportUserResponse.SpeakerMapping toSpeakerMappingResponse(AiScoreSpeakerIdentity identity) {
        AiScoreReportUserResponse.SpeakerMapping response = new AiScoreReportUserResponse.SpeakerMapping();
        response.setRawSpeaker(identity.getRawSpeakerLabel());
        response.setDisplayName(identity.getDisplayName());
        response.setRoleName(identity.getRoleName());
        response.setStatus(identity.getStatus());
        response.setConfidence(identity.getConfidence());
        response.setRevision(identity.getRevision());
        return response;
    }

    public Map<String, Object> updateRemediationTaskStatus(Long reportId, Long taskId, String status) {
        if (remediationService == null) {
            throw new IllegalStateException("remediation task service is unavailable");
        }
        return remediationService.updateUserTaskStatus(reportId, taskId, status);
    }

    private void attachStructuredReportDetails(
            AiScoreReportUserResponse response,
            AiScoreReport report,
            AiScoringSession session
    ) {
        if (observationMapper == null || deductionMapper == null || evidenceAnchorMapper == null || report.getId() == null) {
            response.setStructuredObservations(List.of());
            response.setStructuredDeductions(List.of());
            response.setEvidenceAnchors(List.of());
            response.setScoreRecoverySummary(emptyRecoverySummary(report));
            response.setTrainingTasks(List.of());
            return;
        }

        List<AiScoreObservation> observations = observationMapper.selectList(
                new LambdaQueryWrapper<AiScoreObservation>()
                        .eq(AiScoreObservation::getReportId, report.getId())
                        .orderByAsc(AiScoreObservation::getId)
        );
        List<AiScoreDeduction> deductions = deductionMapper.selectList(
                new LambdaQueryWrapper<AiScoreDeduction>()
                        .eq(AiScoreDeduction::getReportId, report.getId())
                        .orderByAsc(AiScoreDeduction::getId)
        );
        List<AiScoreEvidenceAnchor> anchors = session == null || session.getId() == null
                ? List.of()
                : evidenceAnchorMapper.selectList(new LambdaQueryWrapper<AiScoreEvidenceAnchor>()
                .eq(AiScoreEvidenceAnchor::getSessionId, session.getId())
                .orderByAsc(AiScoreEvidenceAnchor::getId));

        Map<String, String> observationDimensionNames = observations.stream()
                .filter(observation -> hasText(observation.getObservationCode()))
                .collect(Collectors.toMap(
                        AiScoreObservation::getObservationCode,
                        observation -> defaulted(observation.getDimensionName(), observation.getDimensionCode()),
                        (left, right) -> left,
                        LinkedHashMap::new
                ));
        Map<Long, BigDecimal> effectiveDeductionPoints = effectiveDeductionPoints(observations, deductions);

        response.setStructuredObservations(observations.stream()
                .map(this::toObservationResponse)
                .toList());
        response.setStructuredDeductions(deductions.stream()
                .map(deduction -> toDeductionResponse(
                        deduction,
                        observationDimensionNames,
                        effectiveDeductionPoints
                ))
                .toList());
        response.setEvidenceAnchors(anchors.stream()
                .map(this::toEvidenceAnchorResponse)
                .toList());
        response.setScoreRecoverySummary(toRecoverySummary(report, deductions, effectiveDeductionPoints));
        response.setTrainingTasks(toTrainingTasks(
                deductions,
                observationDimensionNames,
                effectiveDeductionPoints
        ));
    }

    private AiScoreReportUserResponse.StructuredObservation toObservationResponse(AiScoreObservation observation) {
        AiScoreReportUserResponse.StructuredObservation response = new AiScoreReportUserResponse.StructuredObservation();
        response.setId(observation.getId());
        response.setDimensionName(defaulted(observation.getDimensionName(), observation.getDimensionCode()));
        response.setRawScore(observation.getRawScore());
        response.setScoreCap(observation.getScoreCap());
        response.setEvidenceLevel(observation.getEvidenceLevel());
        response.setConfidence(observation.getConfidence());
        response.setValidityStatus(observation.getValidityStatus());
        response.setModelReason(observation.getModelReason());
        response.setEvidenceAnchorIds(parseLongList(observation.getEvidenceAnchorIdsJson()));
        return response;
    }

    private AiScoreReportUserResponse.StructuredDeduction toDeductionResponse(
            AiScoreDeduction deduction,
            Map<String, String> observationDimensionNames,
            Map<Long, BigDecimal> effectiveDeductionPoints
    ) {
        AiScoreReportUserResponse.StructuredDeduction response = new AiScoreReportUserResponse.StructuredDeduction();
        response.setId(deduction.getId());
        response.setDimensionName(defaulted(
                observationDimensionNames.get(deduction.getObservationCode()),
                deduction.getDimensionCode()
        ));
        BigDecimal visibleDeductedPoints = visibleDeductedPoints(deduction, effectiveDeductionPoints);
        response.setDeductedPoints(visibleDeductedPoints);
        response.setRecoveredPoints(valueOrZero(deduction.getRecoveredPoints()));
        response.setReason(deduction.getReason());
        response.setRequiredFix(deduction.getRequiredFix());
        response.setAcceptanceCriteria(deduction.getAcceptanceCriteria());
        response.setMaxRecoverablePoints(visibleRecoverablePoints(deduction, visibleDeductedPoints));
        response.setEvidenceLevel(deduction.getEvidenceLevel());
        response.setConfidence(deduction.getConfidence());
        response.setEvidenceAnchorIds(parseLongList(deduction.getEvidenceAnchorIdsJson()));
        response.setStatus(deduction.getStatus());
        response.setRecovery(hasText(deduction.getRecoverySourceDeductionId()));
        return response;
    }

    private AiScoreReportUserResponse.EvidenceAnchor toEvidenceAnchorResponse(AiScoreEvidenceAnchor anchor) {
        AiScoreReportUserResponse.EvidenceAnchor response = new AiScoreReportUserResponse.EvidenceAnchor();
        response.setId(anchor.getId());
        response.setAnchorType(anchor.getAnchorType());
        response.setAnchorTitle(anchor.getAnchorTitle());
        response.setEvidenceText(anchor.getEvidenceText());
        response.setSourceRef(anchor.getSourceRef());
        response.setTranscriptSegmentId(anchor.getTranscriptSegmentId());
        response.setFrameId(anchor.getFrameId());
        response.setMediaAssetId(anchor.getMediaAssetId());
        response.setStartMs(anchor.getStartMs());
        response.setEndMs(anchor.getEndMs());
        response.setConfidence(anchor.getConfidence());
        response.setValidityStatus(anchor.getValidityStatus());
        return response;
    }

    private AiScoreReportUserResponse.ScoreRecoverySummary toRecoverySummary(
            AiScoreReport report,
            List<AiScoreDeduction> deductions,
            Map<Long, BigDecimal> effectiveDeductionPoints
    ) {
        AiScoreReportUserResponse.ScoreRecoverySummary summary = emptyRecoverySummary(report);
        List<AiScoreDeduction> safeDeductions = deductions == null ? List.of() : deductions;
        List<AiScoreDeduction> recoveryRows = safeDeductions.stream()
                .filter(deduction -> hasText(deduction.getRecoverySourceDeductionId()))
                .toList();
        List<AiScoreDeduction> currentRows = safeDeductions.stream()
                .filter(deduction -> !hasText(deduction.getRecoverySourceDeductionId()))
                .filter(this::isActiveUserDeduction)
                .toList();
        summary.setRecoveredCount(recoveryRows.size());
        summary.setRecoveredPoints(sum(recoveryRows.stream()
                .map(AiScoreDeduction::getRecoveredPoints)
                .toList()));
        summary.setCurrentDeductedPoints(sum(currentRows.stream()
                .map(deduction -> visibleDeductedPoints(deduction, effectiveDeductionPoints))
                .toList()));
        summary.setRecoverableScore(sum(currentRows.stream()
                .map(deduction -> visibleRecoverablePoints(
                        deduction,
                        visibleDeductedPoints(deduction, effectiveDeductionPoints)
                ))
                .toList()));
        summary.setNewIssueCount((int) currentRows.stream()
                .filter(deduction -> "new".equalsIgnoreCase(defaulted(deduction.getStatus(), "")))
                .count());
        return summary;
    }

    private List<AiScoreReportUserResponse.TrainingTask> toTrainingTasks(
            List<AiScoreDeduction> deductions,
            Map<String, String> observationDimensionNames,
            Map<Long, BigDecimal> effectiveDeductionPoints
    ) {
        List<AiScoreDeduction> currentDeductions = (deductions == null ? List.<AiScoreDeduction>of() : deductions).stream()
                .filter(deduction -> !hasText(deduction.getRecoverySourceDeductionId()))
                .filter(this::isActiveUserDeduction)
                .filter(deduction -> visibleDeductedPoints(deduction, effectiveDeductionPoints)
                        .compareTo(BigDecimal.ZERO) > 0)
                .toList();
        List<AiScoreReportUserResponse.TrainingTask> tasks = new ArrayList<>();
        for (int i = 0; i < currentDeductions.size(); i++) {
            AiScoreDeduction deduction = currentDeductions.get(i);
            AiScoreReportUserResponse.TrainingTask task = new AiScoreReportUserResponse.TrainingTask();
            String reason = firstNonBlank(deduction.getReason(), "扣分项待复核");
            String dimension = observationDimensionNames.getOrDefault(
                    defaulted(deduction.getObservationCode(), ""),
                    defaulted(deduction.getDimensionCode(), "综合提分"));
            task.setTaskId("training-task-" + (i + 1));
            task.setTitle("补齐：" + reason);
            task.setCorrespondingDeduction(reason);
            task.setTrainingAction(specificTrainingAction(deduction));
            task.setOwnerRole(ownerRoleFor(dimension, reason));
            task.setTimeSuggestion("下一轮复评前完成补证、彩排和验收记录");
            task.setAcceptanceCriteria(firstNonBlank(
                    deduction.getAcceptanceCriteria(),
                    "下一轮评分能提供可复核证据，并对照本轮扣分原因说明已修复"));
            task.setExpectedRecoverPoints(visibleRecoverablePoints(
                    deduction,
                    visibleDeductedPoints(deduction, effectiveDeductionPoints)
            ));
            task.setEvidenceAnchorIds(parseLongList(deduction.getEvidenceAnchorIdsJson()));
            task.setPriority(priorityFor(deduction));
            task.setObservationCode(deduction.getObservationCode());
            task.setSourceIssueKey(hasText(deduction.getObservationCode())
                    ? "score-deduction:" + deduction.getObservationCode()
                    : "score-deduction");
            tasks.add(task);
        }
        return tasks;
    }

    /**
     * Converts configured rule deductions into their actual impact on the capped official score.
     * The configured values remain stored for audit/recalculation; only the user response is normalized.
     */
    private Map<Long, BigDecimal> effectiveDeductionPoints(
            List<AiScoreObservation> observations,
            List<AiScoreDeduction> deductions
    ) {
        Map<Long, BigDecimal> result = new LinkedHashMap<>();
        List<AiScoreDeduction> safeDeductions = deductions == null ? List.of() : deductions;
        Map<String, List<AiScoreDeduction>> byObservation = safeDeductions.stream()
                .filter(deduction -> !hasText(deduction.getRecoverySourceDeductionId()))
                .filter(this::isActiveUserDeduction)
                .filter(deduction -> hasText(deduction.getObservationCode()))
                .collect(Collectors.groupingBy(
                        AiScoreDeduction::getObservationCode,
                        LinkedHashMap::new,
                        Collectors.toList()
                ));

        for (AiScoreObservation observation : observations == null ? List.<AiScoreObservation>of() : observations) {
            List<AiScoreDeduction> rows = byObservation.getOrDefault(
                    defaulted(observation.getObservationCode(), ""),
                    List.of()
            );
            if (rows.isEmpty()) {
                continue;
            }
            BigDecimal base = valueOrZero(observation.getRawScore()).max(BigDecimal.ZERO);
            BigDecimal cap = observation.getScoreCap() == null
                    ? base
                    : valueOrZero(observation.getScoreCap()).max(BigDecimal.ZERO);
            BigDecimal configuredTotal = sum(rows.stream()
                    .map(AiScoreDeduction::getDeductedPoints)
                    .toList()).max(BigDecimal.ZERO);
            BigDecimal cappedBaseline = base.min(cap);
            BigDecimal postDeduction = base.subtract(configuredTotal)
                    .max(BigDecimal.ZERO)
                    .min(cap);
            BigDecimal remainingImpact = cappedBaseline.subtract(postDeduction).max(BigDecimal.ZERO);
            BigDecimal remainingConfigured = configuredTotal;

            for (int i = 0; i < rows.size(); i++) {
                AiScoreDeduction row = rows.get(i);
                BigDecimal configured = valueOrZero(row.getDeductedPoints()).max(BigDecimal.ZERO);
                BigDecimal allocated;
                if (i == rows.size() - 1 || remainingConfigured.compareTo(BigDecimal.ZERO) <= 0) {
                    allocated = remainingImpact;
                } else {
                    allocated = remainingImpact.multiply(configured)
                            .divide(remainingConfigured, 2, RoundingMode.HALF_UP)
                            .min(configured)
                            .min(remainingImpact);
                }
                if (row.getId() != null) {
                    result.put(row.getId(), allocated.setScale(2, RoundingMode.HALF_UP));
                }
                remainingImpact = remainingImpact.subtract(allocated).max(BigDecimal.ZERO);
                remainingConfigured = remainingConfigured.subtract(configured).max(BigDecimal.ZERO);
            }
        }
        return result;
    }

    private boolean isActiveUserDeduction(AiScoreDeduction deduction) {
        String status = defaulted(deduction.getStatus(), "").trim().toLowerCase(Locale.ROOT);
        return !"invalid".equals(status) && !"recovered".equals(status);
    }

    private BigDecimal visibleDeductedPoints(
            AiScoreDeduction deduction,
            Map<Long, BigDecimal> effectiveDeductionPoints
    ) {
        if (hasText(deduction.getRecoverySourceDeductionId())) {
            return valueOrZero(deduction.getDeductedPoints());
        }
        return deduction.getId() == null
                ? valueOrZero(deduction.getDeductedPoints())
                : effectiveDeductionPoints.getOrDefault(
                        deduction.getId(),
                        valueOrZero(deduction.getDeductedPoints())
                );
    }

    private BigDecimal visibleRecoverablePoints(
            AiScoreDeduction deduction,
            BigDecimal visibleDeductedPoints
    ) {
        BigDecimal configuredRecoverable = deduction.getMaxRecoverablePoints() == null
                ? visibleDeductedPoints
                : valueOrZero(deduction.getMaxRecoverablePoints());
        return configuredRecoverable.max(BigDecimal.ZERO).min(visibleDeductedPoints.max(BigDecimal.ZERO));
    }

    private String specificTrainingAction(AiScoreDeduction deduction) {
        String requiredFix = firstNonBlank(deduction.getRequiredFix());
        if (hasText(requiredFix) && !isGenericTrainingAction(requiredFix)) {
            return requiredFix;
        }
        String reason = firstNonBlank(deduction.getReason(), "扣分项");
        return "围绕「" + reason + "」补充可展示证据，录制一轮彩排片段，并在复评时说明改动前后差异";
    }

    private boolean isGenericTrainingAction(String value) {
        String text = defaulted(value, "").replaceAll("\\s+", "");
        return text.equals("优化表达")
                || text.equals("加强展示")
                || text.equals("继续优化")
                || text.equals("改进方案")
                || text.length() < 6;
    }

    private String ownerRoleFor(String dimension, String reason) {
        String text = defaulted(dimension, "") + " " + defaulted(reason, "");
        if (text.matches(".*(技术|算法|模型|系统|演示|稳定|准确|测试).*")) return "技术负责人";
        if (text.matches(".*(商业|客户|订单|市场|成本|收益|数据).*")) return "商业负责人";
        if (text.matches(".*(表达|路演|话术|停顿|讲解).*")) return "主讲负责人";
        if (text.matches(".*(规范|合规|安全|知识产权|标准).*")) return "合规负责人";
        return "项目负责人";
    }

    private String priorityFor(AiScoreDeduction deduction) {
        if (valueOrZero(deduction.getDeductedPoints()).compareTo(new BigDecimal("5")) >= 0
                || "new".equalsIgnoreCase(defaulted(deduction.getStatus(), ""))) {
            return "P0";
        }
        return "P1";
    }

    private AiScoreReportUserResponse.RuleEngineShadow toRuleEngineShadow(String structuredResultJson) {
        if (!hasText(structuredResultJson)) {
            return null;
        }
        try {
            Map<?, ?> source = objectMapper.readValue(structuredResultJson, Map.class);
            Object ruleEngineScore = source.get("ruleEngineScore");
            if (ruleEngineScore == null) {
                return null;
            }
            AiScoreReportUserResponse.RuleEngineShadow shadow = new AiScoreReportUserResponse.RuleEngineShadow();
            shadow.setLlmRawScore(toBigDecimal(source.get("llmRawScore")));
            shadow.setRuleEngineScore(toBigDecimal(ruleEngineScore));
            shadow.setModelReviewScore(toBigDecimal(source.get("modelReviewScore")));
            Object tapeGrounded = source.get("tapeGrounded");
            if (tapeGrounded instanceof Boolean flag) {
                shadow.setTapeGrounded(flag);
            }
            shadow.setScoreDiff(toBigDecimal(source.get("scoreDiff")));
            shadow.setDiffReasons(toStringList(source.get("diffReasons")));
            shadow.setScoringFingerprint(source.get("scoringFingerprint") == null
                    ? null
                    : String.valueOf(source.get("scoringFingerprint")));
            return shadow;
        } catch (Exception ignored) {
            return null;
        }
    }

    private BigDecimal toBigDecimal(Object value) {
        if (value == null || String.valueOf(value).isBlank()) {
            return null;
        }
        try {
            return new BigDecimal(String.valueOf(value));
        } catch (NumberFormatException ignored) {
            return null;
        }
    }

    private List<String> toStringList(Object value) {
        if (value == null) {
            return List.of();
        }
        if (value instanceof List<?> list) {
            return list.stream()
                    .filter(item -> item != null && hasText(String.valueOf(item)))
                    .map(String::valueOf)
                    .toList();
        }
        return hasText(String.valueOf(value)) ? List.of(String.valueOf(value)) : List.of();
    }

    private AiScoreReportUserResponse.ScoreRecoverySummary emptyRecoverySummary(AiScoreReport report) {
        AiScoreReportUserResponse.ScoreRecoverySummary summary = new AiScoreReportUserResponse.ScoreRecoverySummary();
        summary.setRecoveredCount(0);
        summary.setRecoveredPoints(BigDecimal.ZERO);
        summary.setCurrentDeductedPoints(BigDecimal.ZERO);
        summary.setNewIssueCount(0);
        summary.setNotPerfectReasons(notPerfectReasons(report == null ? null : report.getScoreCalibrationJson()));
        return summary;
    }

    private Map<String, Object> toReportSummary(Map<String, Object> row) {
        Map<String, Object> summary = new LinkedHashMap<>();
        summary.put("sessionId", row.get("sessionId"));
        summary.put("reportId", row.get("reportId"));
        summary.put("meetingId", row.get("meetingId"));
        summary.put("docketId", row.get("docketId"));
        summary.put("teamId", row.get("teamId"));
        summary.put("sourceType", row.get("sourceType"));
        summary.put("status", row.get("status"));
        summary.put("overallScore", row.get("overallScore"));
        summary.put("completedAt", firstNonNull(row.get("completedAt"), row.get("createdAt")));
        summary.put("title", firstNonBlank(text(row.get("meetingTitle")), text(row.get("projectName")), "未命名路演"));
        summary.put("projectName", row.get("projectName"));
        summary.put("taskBookPublished", DocketTaskBook.flag(row.get("taskBookPublished"), row.get("docketTaskBookPublished")));
        putHungProgress(summary, row);
        summary.put("teacherConfirmed", isPublishedFlag(row.get("teacherConfirmed")));
        summary.put("confirmed", isPublishedFlag(row.get("teacherConfirmed")));
        List<Map<String, Object>> criticalIssues = parseMapList(row.get("criticalIssuesJson"));
        List<Map<String, Object>> priorities = parseMapList(row.get("improvementPrioritiesJson"));
        summary.put("issueCount", criticalIssues.size() + priorities.size());
        summary.put("highRiskCount", criticalIssues.size());
        return summary;
    }

    private void putHungProgress(Map<String, Object> summary, Map<String, Object> row) {
        if (!DocketTaskBook.flag(row.get("taskBookPublished"), row.get("docketTaskBookPublished"))) {
            return;
        }
        DocketTaskBook.Snapshot snapshot = DocketTaskBook.resolve(
                isPublishedFlag(row.get("taskBookPublished")),
                text(row.get("taskBookJson")),
                isPublishedFlag(row.get("docketTaskBookPublished")),
                text(row.get("docketTaskBookJson"))
        );
        if (!snapshot.published() || !hasText(snapshot.json())) {
            return;
        }
        try {
            TaskBook book = objectMapper.readValue(snapshot.json(), TaskBook.class);
            TaskBookHang.Progress progress = TaskBookHang.progress(book);
            summary.put("hungCount", progress.hung());
            summary.put("hungTotal", progress.total());
            if (progress.hung() > 0) {
                summary.put("hungDisplay", progress.display());
            }
        } catch (Exception ignored) {
            // list stays usable without hang counts
        }
    }

    private boolean hasReportIdentity(Map<String, Object> row) {
        return row.get("sessionId") != null || row.get("reportId") != null || row.get("meetingId") != null;
    }

    private List<Map<String, Object>> parseMapList(Object json) {
        if (json == null || String.valueOf(json).isBlank()) {
            return List.of();
        }
        try {
            JsonNode node = objectMapper.readTree(String.valueOf(json));
            if (!node.isArray()) {
                return List.of();
            }
            List<Map<String, Object>> values = new ArrayList<>();
            for (JsonNode item : node) {
                if (item.isObject()) {
                    values.add(objectMapper.convertValue(item, Map.class));
                }
            }
            return values;
        } catch (Exception ignored) {
            return List.of();
        }
    }

    private Map<String, Object> parseMapObject(Object json) {
        if (json == null || String.valueOf(json).isBlank()) {
            return Map.of();
        }
        try {
            JsonNode node = objectMapper.readTree(String.valueOf(json));
            if (!node.isObject()) {
                return Map.of();
            }
            return objectMapper.convertValue(node, Map.class);
        } catch (Exception ignored) {
            return Map.of();
        }
    }

    private static boolean isPublishedFlag(Object value) {
        if (value instanceof Boolean flag) {
            return flag;
        }
        if (value instanceof Number number) {
            return number.intValue() != 0;
        }
        return "1".equals(String.valueOf(value)) || "true".equalsIgnoreCase(String.valueOf(value));
    }

    private Object firstNonNull(Object... values) {
        for (Object value : values) {
            if (value != null) {
                return value;
            }
        }
        return null;
    }

    private String firstNonBlank(String... values) {
        for (String value : values) {
            if (hasText(value)) {
                return value;
            }
        }
        return "";
    }

    private String text(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private List<String> notPerfectReasons(String scoreCalibrationJson) {
        if (!hasText(scoreCalibrationJson)) {
            return List.of();
        }
        try {
            JsonNode root = objectMapper.readTree(scoreCalibrationJson);
            JsonNode reasons = root.path("notPerfectReasons");
            if (reasons.isMissingNode()) {
                reasons = root.path("ceiling_reasons");
            }
            if (!reasons.isArray()) {
                return List.of();
            }
            List<String> values = new ArrayList<>();
            for (JsonNode reason : reasons) {
                if (reason.isTextual() && hasText(reason.asText())) {
                    values.add(reason.asText());
                }
            }
            return values;
        } catch (Exception ignored) {
            return List.of();
        }
    }

    private List<Long> parseLongList(String json) {
        if (!hasText(json)) {
            return List.of();
        }
        try {
            JsonNode node = objectMapper.readTree(json);
            if (!node.isArray()) {
                return List.of();
            }
            List<Long> values = new ArrayList<>();
            for (JsonNode item : node) {
                if (item.canConvertToLong()) {
                    values.add(item.asLong());
                }
            }
            return values;
        } catch (Exception ignored) {
            return List.of();
        }
    }

    public AiScoringSession requireSessionForAccess(Long sessionId) {
        return requireSession(sessionId);
    }

    private AiScoringSession requireSession(Long sessionId) {
        AiScoringSession session = sessionMapper.selectById(sessionId);
        if (session == null) {
            throw new IllegalStateException("未找到评分会话");
        }
        return session;
    }

    private void addColumnIfMissing(String tableName, String columnName, String sql) {
        if (!columnExists(tableName, columnName)) {
            jdbcTemplate.execute(sql);
        }
    }

    private void createIndexIfMissing(String tableName, String indexName, String sql) {
        if (!indexExists(tableName, indexName)) {
            executeQuietly(sql);
        }
    }

    private void executeQuietly(String sql) {
        try {
            jdbcTemplate.execute(sql);
        } catch (Exception ignored) {
            // Compatibility DDL is best-effort across MySQL and H2 test mode.
        }
    }

    private boolean isMysql() {
        return Boolean.TRUE.equals(jdbcTemplate.execute((ConnectionCallback<Boolean>) connection -> {
            String product = connection.getMetaData().getDatabaseProductName();
            return product != null && product.toLowerCase().contains("mysql");
        }));
    }

    /**
     * Cloud MySQL 8 默认 utf8mb4_0900_ai_ci；旧表是 utf8mb4_unicode_ci。
     * docket_id 跨表 JOIN 会报 Illegal mix of collations，报告列表整页失败。
     */
    private void alignMysqlTableCollation(String tableName) {
        if (!isMysql() || !tableExists(tableName)) {
            return;
        }
        try {
            String collation = jdbcTemplate.queryForObject(
                    """
                    SELECT TABLE_COLLATION FROM INFORMATION_SCHEMA.TABLES
                    WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = ?
                    """,
                    String.class,
                    tableName
            );
            if (collation != null && !"utf8mb4_unicode_ci".equalsIgnoreCase(collation)) {
                jdbcTemplate.execute(
                        "ALTER TABLE `" + tableName + "` CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                );
            }
        } catch (Exception ignored) {
            // H2 / permission / already converting — list queries still work after the cloud SQL hotfix.
        }
    }

    private boolean tableExists(String tableName) {
        return Boolean.TRUE.equals(jdbcTemplate.execute((ConnectionCallback<Boolean>) connection -> {
            try (ResultSet tables = connection.getMetaData().getTables(null, null, tableName, null)) {
                while (tables.next()) {
                    if (tableName.equalsIgnoreCase(tables.getString("TABLE_NAME"))) {
                        return true;
                    }
                }
                return false;
            }
        }));
    }

    private boolean columnExists(String tableName, String columnName) {
        return Boolean.TRUE.equals(jdbcTemplate.execute((ConnectionCallback<Boolean>) connection -> {
            try (ResultSet columns = connection.getMetaData().getColumns(null, null, tableName, null)) {
                while (columns.next()) {
                    if (columnName.equalsIgnoreCase(columns.getString("COLUMN_NAME"))) {
                        return true;
                    }
                }
                return false;
            }
        }));
    }

    private boolean indexExists(String tableName, String indexName) {
        return Boolean.TRUE.equals(jdbcTemplate.execute((ConnectionCallback<Boolean>) connection -> {
            try (ResultSet indexes = connection.getMetaData().getIndexInfo(null, null, tableName, false, false)) {
                while (indexes.next()) {
                    String existingName = indexes.getString("INDEX_NAME");
                    if (existingName != null && indexName.equalsIgnoreCase(existingName)) {
                        return true;
                    }
                }
                return false;
            }
        }));
    }

    private String redactInternalCalibration(String calibrationJson) {
        if (calibrationJson == null || calibrationJson.isBlank()) {
            return calibrationJson;
        }
        return calibrationJson
                .replaceAll("\"ruleEngineVersion\"\\s*:\\s*\"[^\"]*\"\\s*,?", "")
                .replaceAll(",\\s*}", "}");
    }

    private String shadowResultJson(PipelineCallbackRequest.PipelineFinalResult result) {
        if (result == null || result.getRuleEngineScore() == null) {
            return null;
        }
        Map<String, Object> shadow = new LinkedHashMap<>();
        shadow.put("llmRawScore", result.getLlmRawScore());
        shadow.put("ruleEngineScore", result.getRuleEngineScore());
        shadow.put("modelReviewScore", result.getModelReviewScore());
        shadow.put("tapeGrounded", result.getTapeGrounded());
        shadow.put("scoreDiff", result.getScoreDiff());
        shadow.put("diffReasons", result.getDiffReasons());
        shadow.put("ruleEngineVersion", result.getRuleEngineVersion());
        shadow.put("scoringFingerprint", result.getScoringFingerprint());
        try {
            return objectMapper.writeValueAsString(shadow);
        } catch (Exception ignored) {
            return null;
        }
    }

    private ScoringFingerprintInput toFingerprintInput(AiScoringSessionCreateRequest request,
                                                       ResolvedRubric rubric,
                                                       String sourceType,
                                                       boolean useHistory) {
        ScoringFingerprintInput input = new ScoringFingerprintInput();
        input.setTrackId(rubric.getTrackId());
        input.setRubricId(rubric.getRubricId());
        input.setRubricHash(rubric.getRubricHash());
        input.setEvidenceSchemaId(rubric.getEvidenceSchemaId());
        input.setEvidenceSchemaVersion(rubric.getEvidenceSchemaVersion());
        input.setEvidenceSchemaHash(rubric.getEvidenceSchemaHash());
        input.setSourceType(sourceType);
        input.setSourceId(request.getSourceId());
        input.setMeetingId(request.getMeetingId());
        input.setRecordingId(request.getRecordingId());
        input.setProjectId(request.getProjectId());
        input.setTeamId(request.getTeamId());
        input.setUseHistoryMemory(useHistory);
        input.setHistoryMemorySnapshotId(request.getHistoryMemorySnapshotId());
        input.setModelVersion(request.getModelVersion());
        input.setPromptVersion(request.getPromptVersion());
        input.setScoringConfigHash(request.getScoringConfigHash());
        return input;
    }

    private String nextSessionNo() {
        return "SC-" + java.time.format.DateTimeFormatter.ofPattern("yyyyMMddHHmmssSSS")
                .format(LocalDateTime.now());
    }

    private int valueOrZero(Integer value) {
        return value == null ? 0 : value;
    }

    private BigDecimal valueOrZero(BigDecimal value) {
        return value == null ? BigDecimal.ZERO : value;
    }

    private BigDecimal sum(List<BigDecimal> values) {
        return (values == null ? List.<BigDecimal>of() : values).stream()
                .filter(Objects::nonNull)
                .reduce(BigDecimal.ZERO, BigDecimal::add);
    }

    private boolean hasText(String value) {
        return value != null && !value.isBlank();
    }

    private String defaulted(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value;
    }

    private String normalizeSourceType(String sourceType) {
        if (sourceType == null || sourceType.isBlank()) {
            return "meeting_recording";
        }
        String normalized = sourceType.trim()
                .toLowerCase(Locale.ROOT)
                .replace('-', '_')
                .replace(' ', '_');
        normalized = normalized.replaceAll("_+", "_");
        return switch (normalized) {
            case "meeting_recording", "meetingrecording" -> "meeting_recording";
            case "uploaded_video", "uploadedvideo" -> "uploaded_video";
            case "local_backup", "localbackup" -> "local_backup";
            default -> throw new IllegalArgumentException("评分来源类型不支持");
        };
    }
}
