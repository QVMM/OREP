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

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.LocalDateTime;
import java.util.Comparator;
import java.util.List;
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
        validateSessionId(sessionId);
        List<AiScoreMediaAsset> assets = mediaAssetMapper.selectList(new LambdaQueryWrapper<AiScoreMediaAsset>()
                .eq(AiScoreMediaAsset::getSessionId, sessionId)
                .eq(AiScoreMediaAsset::getStatus, "uploaded")
                .orderByAsc(AiScoreMediaAsset::getId));
        if (assets.isEmpty()) {
            throw new IllegalStateException("未找到可用媒体资产");
        }
        clearExistingEvidenceBundle(sessionId);

        List<AiScoreMediaAsset> sortedAssets = assets.stream()
                .sorted(Comparator.comparing(AiScoreMediaAsset::getId, Comparator.nullsLast(Long::compareTo)))
                .toList();

        // ASR 和关键帧尚未执行时只冻结真实媒体资产。
        // 不得用占位转写、虚拟 OCR 或伪帧填充证据包。
        List<AiScoreTranscriptSegment> segments = List.of();
        List<AiScoreFrame> frames = List.of();
        List<AiScoreEvidenceAnchor> anchors = List.of();

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
        validateSessionId(sessionId);
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

    private void validateSessionId(Long sessionId) {
        if (sessionId == null || sessionId <= 0) {
            throw new IllegalArgumentException("评分会话无效");
        }
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

    private void clearExistingEvidenceBundle(Long sessionId) {
        evidenceAnchorMapper.delete(new LambdaQueryWrapper<AiScoreEvidenceAnchor>()
                .eq(AiScoreEvidenceAnchor::getSessionId, sessionId));
        transcriptSegmentMapper.delete(new LambdaQueryWrapper<AiScoreTranscriptSegment>()
                .eq(AiScoreTranscriptSegment::getSessionId, sessionId));
        frameMapper.delete(new LambdaQueryWrapper<AiScoreFrame>()
                .eq(AiScoreFrame::getSessionId, sessionId));
        evidenceSnapshotMapper.delete(new LambdaQueryWrapper<AiScoreEvidenceSnapshot>()
                .eq(AiScoreEvidenceSnapshot::getSessionId, sessionId));
    }
}
