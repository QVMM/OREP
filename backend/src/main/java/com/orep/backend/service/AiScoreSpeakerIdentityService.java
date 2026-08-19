package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.orep.backend.dto.PipelineCallbackRequest;
import com.orep.backend.entity.AiScoreSpeakerIdentity;
import com.orep.backend.entity.AiScoreTranscriptSegment;
import com.orep.backend.mapper.AiScoreSpeakerIdentityMapper;
import com.orep.backend.mapper.AiScoreTranscriptSegmentMapper;
import org.springframework.stereotype.Service;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

@Service
public class AiScoreSpeakerIdentityService {
    private final AiScoreSpeakerIdentityMapper identityMapper;
    private final AiScoreTranscriptSegmentMapper segmentMapper;
    private final AiScoreSpeakerAttributionPersistenceService attributionPersistenceService;

    @Autowired
    public AiScoreSpeakerIdentityService(
            AiScoreSpeakerIdentityMapper identityMapper,
            AiScoreTranscriptSegmentMapper segmentMapper,
            AiScoreSpeakerAttributionPersistenceService attributionPersistenceService
    ) {
        this.identityMapper = identityMapper;
        this.segmentMapper = segmentMapper;
        this.attributionPersistenceService = attributionPersistenceService;
    }

    public AiScoreSpeakerIdentityService(
            AiScoreSpeakerIdentityMapper identityMapper,
            AiScoreTranscriptSegmentMapper segmentMapper
    ) {
        this(identityMapper, segmentMapper, null);
    }

    public AiScoreSpeakerAttributionPersistenceService.PersistenceOutcome persistAttribution(
            Long sessionId,
            PipelineCallbackRequest.SpeakerAttributionInput snapshot
    ) {
        if (attributionPersistenceService == null) {
            throw new IllegalStateException("speaker attribution persistence is unavailable");
        }
        return attributionPersistenceService.persist(sessionId, snapshot);
    }

    public List<AiScoreSpeakerIdentity> listForSession(Long sessionId) {
        if (sessionId == null || sessionId <= 0) return List.of();
        return identityMapper.selectList(new LambdaQueryWrapper<AiScoreSpeakerIdentity>()
                .eq(AiScoreSpeakerIdentity::getSessionId, sessionId)
                .orderByAsc(AiScoreSpeakerIdentity::getRawSpeakerLabel));
    }

    /**
     * Persists model speaker clusters as identity evidence. This contract is
     * intentionally score-free and never overwrites a human decision.
     */
    @Transactional
    public List<AiScoreSpeakerIdentity> upsertAutoEvidence(
            Long sessionId,
            List<PipelineCallbackRequest.SpeakerEvidenceInput> evidenceItems
    ) {
        if (sessionId == null || sessionId <= 0 || evidenceItems == null || evidenceItems.isEmpty()) {
            return List.of();
        }
        List<AiScoreSpeakerIdentity> persisted = new ArrayList<>();
        Set<String> seen = new HashSet<>();
        for (PipelineCallbackRequest.SpeakerEvidenceInput evidence : evidenceItems) {
            if (evidence == null) continue;
            String raw = clean(evidence.getRawSpeakerId(), 128);
            if (raw.isBlank() || !seen.add(raw)) continue;

            AiScoreSpeakerIdentity identity = identityMapper.selectOne(
                    new LambdaQueryWrapper<AiScoreSpeakerIdentity>()
                            .eq(AiScoreSpeakerIdentity::getSessionId, sessionId)
                            .eq(AiScoreSpeakerIdentity::getRawSpeakerLabel, raw)
                            .last("LIMIT 1")
            );
            if (identity != null && Set.of("CONFIRMED", "REJECTED").contains(identity.getStatus())) {
                persisted.add(identity);
                continue;
            }

            LocalDateTime now = LocalDateTime.now();
            if (identity == null) {
                identity = new AiScoreSpeakerIdentity();
                identity.setSessionId(sessionId);
                identity.setRawSpeakerLabel(raw);
                identity.setRevision(1);
                identity.setCreatedAt(now);
            }
            String display = clean(evidence.getDisplayName(), 120);
            if (display.isBlank()) display = clean(evidence.getMatchedName(), 120);
            String role = clean(evidence.getRoleName(), 120);
            identity.setDisplayName(display.isBlank() ? null : display);
            identity.setRoleName(role.isBlank() ? null : role);
            identity.setStatus("AUTO");
            identity.setSource("MODEL");
            identity.setConfidence(normalizeConfidence(evidence.getConfidence()));
            identity.setUpdatedAt(now);
            if (identity.getId() == null) identityMapper.insert(identity);
            else identityMapper.updateById(identity);
            persisted.add(identity);
        }
        return persisted;
    }

    @Transactional
    public AiScoreSpeakerIdentity confirm(
            Long sessionId,
            String rawSpeakerLabel,
            String displayName,
            String roleName,
            Long userId
    ) {
        if (sessionId == null || sessionId <= 0) {
            throw new IllegalArgumentException("评分会话无效");
        }
        String raw = clean(rawSpeakerLabel, 128);
        String display = clean(displayName, 120);
        String role = clean(roleName, 120);
        if (raw.isBlank()) throw new IllegalArgumentException("原始发言人标签不能为空");
        if (display.isBlank() && role.isBlank()) {
            throw new IllegalArgumentException("至少填写发言人姓名或角色");
        }

        boolean existsInTranscript = segmentMapper.selectList(
                        new LambdaQueryWrapper<AiScoreTranscriptSegment>()
                                .eq(AiScoreTranscriptSegment::getSessionId, sessionId)
                                .eq(AiScoreTranscriptSegment::getSpeakerLabel, raw)
                                .last("LIMIT 1")
                ).stream()
                .anyMatch(item -> raw.equals(item.getSpeakerLabel()));
        if (!existsInTranscript) {
            throw new IllegalArgumentException("该发言人标签在当前转写中不存在");
        }

        AiScoreSpeakerIdentity identity = identityMapper.selectOne(
                new LambdaQueryWrapper<AiScoreSpeakerIdentity>()
                        .eq(AiScoreSpeakerIdentity::getSessionId, sessionId)
                        .eq(AiScoreSpeakerIdentity::getRawSpeakerLabel, raw)
                        .last("LIMIT 1")
        );
        LocalDateTime now = LocalDateTime.now();
        if (identity == null) {
            identity = new AiScoreSpeakerIdentity();
            identity.setSessionId(sessionId);
            identity.setRawSpeakerLabel(raw);
            identity.setRevision(1);
            identity.setCreatedAt(now);
        } else {
            // rawSpeakerLabel 是证据事实，人工修正不得覆盖。
            identity.setRevision(Math.max(0, identity.getRevision() == null ? 0 : identity.getRevision()) + 1);
        }
        identity.setDisplayName(display.isBlank() ? null : display);
        identity.setRoleName(role.isBlank() ? null : role);
        identity.setStatus("CONFIRMED");
        identity.setSource("USER");
        identity.setConfidence(new BigDecimal("1.0000"));
        identity.setUpdatedBy(userId);
        identity.setUpdatedAt(now);
        if (identity.getId() == null) identityMapper.insert(identity);
        else identityMapper.updateById(identity);
        return identity;
    }

    private String clean(String value, int maxLength) {
        String result = value == null ? "" : value.trim();
        return result.length() > maxLength ? result.substring(0, maxLength) : result;
    }

    private BigDecimal normalizeConfidence(BigDecimal value) {
        if (value == null) return null;
        if (value.compareTo(BigDecimal.ZERO) < 0) return BigDecimal.ZERO;
        if (value.compareTo(BigDecimal.ONE) > 0) return BigDecimal.ONE;
        return value.setScale(4, java.math.RoundingMode.HALF_UP);
    }
}
