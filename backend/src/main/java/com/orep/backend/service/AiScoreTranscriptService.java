package com.orep.backend.service;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.orep.backend.entity.AiScoreTranscriptSegment;
import com.orep.backend.mapper.AiScoreTranscriptSegmentMapper;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Map;

@Service
public class AiScoreTranscriptService {
    private final AiScoreTranscriptSegmentMapper mapper;

    public AiScoreTranscriptService(AiScoreTranscriptSegmentMapper mapper) {
        this.mapper = mapper;
    }

    public List<AiScoreTranscriptSegment> listForSession(Long sessionId) {
        if (sessionId == null || sessionId <= 0) return List.of();
        return mapper.selectList(new LambdaQueryWrapper<AiScoreTranscriptSegment>()
                .eq(AiScoreTranscriptSegment::getSessionId, sessionId)
                .orderByAsc(AiScoreTranscriptSegment::getSegmentNo));
    }

    @Transactional
    public List<AiScoreTranscriptSegment> replaceFromCallback(
            Long sessionId,
            List<Map<String, Object>> rawSegments
    ) {
        if (sessionId == null || sessionId <= 0) {
            throw new IllegalArgumentException("评分会话无效");
        }

        List<AiScoreTranscriptSegment> prepared = new ArrayList<>();
        int originalIndex = 0;
        for (Map<String, Object> raw : rawSegments == null ? List.<Map<String, Object>>of() : rawSegments) {
            originalIndex++;
            if (raw == null) continue;
            long startMs = timeMs(raw, true);
            long endMs = timeMs(raw, false);
            if (startMs < 0 || endMs < startMs) {
                throw new IllegalArgumentException("转写分段时间范围无效: " + originalIndex);
            }
            String text = text(raw.get("text"));
            if (text.isBlank()) continue;

            AiScoreTranscriptSegment segment = new AiScoreTranscriptSegment();
            segment.setSessionId(sessionId);
            segment.setStartMs(startMs);
            segment.setEndMs(endMs);
            segment.setText(text);
            segment.setSpeakerLabel(speakerLabel(raw));
            segment.setSourceType(sourceType(raw));
            segment.setConfidence(confidence(raw.get("confidence")));
            segment.setCreatedAt(LocalDateTime.now());
            segment.setSegmentNo(originalIndex);
            prepared.add(segment);
        }

        prepared.sort(Comparator
                .comparing(AiScoreTranscriptSegment::getStartMs)
                .thenComparing(AiScoreTranscriptSegment::getEndMs)
                .thenComparing(AiScoreTranscriptSegment::getSegmentNo));
        for (int index = 0; index < prepared.size(); index++) {
            AiScoreTranscriptSegment segment = prepared.get(index);
            segment.setSegmentNo(index + 1);
            segment.setSegmentHash(sha256(
                    sessionId + "|" + segment.getStartMs() + "|" + segment.getEndMs() + "|"
                            + value(segment.getSpeakerLabel()) + "|" + segment.getText()
            ));
        }

        // Validate the complete replacement before deleting the prior valid snapshot.
        mapper.delete(new LambdaQueryWrapper<AiScoreTranscriptSegment>()
                .eq(AiScoreTranscriptSegment::getSessionId, sessionId));
        for (AiScoreTranscriptSegment segment : prepared) {
            mapper.insert(segment);
        }
        return List.copyOf(prepared);
    }

    private long timeMs(Map<String, Object> raw, boolean start) {
        String explicit = start ? "startMs" : "endMs";
        if (raw.containsKey(explicit) && raw.get(explicit) != null) {
            return number(raw.get(explicit), explicit).setScale(0, RoundingMode.HALF_UP).longValue();
        }
        String providerField = start ? "begin_time" : "end_time";
        if (raw.containsKey(providerField) && raw.get(providerField) != null) {
            return number(raw.get(providerField), providerField).setScale(0, RoundingMode.HALF_UP).longValue();
        }
        String secondsField = start ? "start" : "end";
        if (!raw.containsKey(secondsField) || raw.get(secondsField) == null) {
            throw new IllegalArgumentException("转写分段缺少时间字段: " + secondsField);
        }
        return number(raw.get(secondsField), secondsField)
                .multiply(new BigDecimal("1000"))
                .setScale(0, RoundingMode.HALF_UP)
                .longValue();
    }

    private BigDecimal number(Object value, String field) {
        try {
            return new BigDecimal(String.valueOf(value));
        } catch (Exception error) {
            throw new IllegalArgumentException("转写分段数值无效: " + field, error);
        }
    }

    private BigDecimal confidence(Object value) {
        if (value == null) return null;
        BigDecimal parsed = number(value, "confidence");
        if (parsed.compareTo(BigDecimal.ZERO) < 0 || parsed.compareTo(BigDecimal.ONE) > 0) {
            return null;
        }
        return parsed.setScale(4, RoundingMode.HALF_UP);
    }

    private String speakerLabel(Map<String, Object> raw) {
        Object value = first(raw.get("speaker_id"), raw.get("speakerId"), raw.get("speaker"));
        if (value == null) return null;
        if (value instanceof Number number) {
            return "SPEAKER_" + number.longValue();
        }
        String label = text(value);
        if (label.isBlank()) return null;
        if (label.chars().allMatch(Character::isDigit)) return "SPEAKER_" + label;
        return label.length() > 128 ? label.substring(0, 128) : label;
    }

    private String sourceType(Map<String, Object> raw) {
        String source = text(raw.get("source"));
        if (source.isBlank()) return "pipeline_asr";
        return source.length() > 32 ? source.substring(0, 32) : source;
    }

    private Object first(Object... values) {
        for (Object value : values) {
            if (value != null && !String.valueOf(value).isBlank()) return value;
        }
        return null;
    }

    private String text(Object value) {
        return value == null ? "" : String.valueOf(value).trim();
    }

    private String value(String value) {
        return value == null ? "" : value;
    }

    private String sha256(String value) {
        try {
            byte[] digest = MessageDigest.getInstance("SHA-256")
                    .digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder result = new StringBuilder(64);
            for (byte item : digest) result.append(String.format("%02x", item));
            return result.toString();
        } catch (Exception error) {
            throw new IllegalStateException("transcript hash failed", error);
        }
    }
}
