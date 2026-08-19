package com.orep.backend.service;

import com.orep.backend.dto.ScoringFingerprintInput;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.stream.Collectors;

@Service
public class ScoringFingerprintService {

    public String fingerprint(ScoringFingerprintInput input) {
        if (input == null) {
            throw new IllegalArgumentException("fingerprint input cannot be null");
        }
        Map<String, Object> values = new LinkedHashMap<>();
        values.put("trackId", norm(input.getTrackId()));
        values.put("rubricId", norm(input.getRubricId()));
        values.put("rubricHash", norm(input.getRubricHash()));
        values.put("evidenceSchemaId", input.getEvidenceSchemaId());
        values.put("evidenceSchemaVersion", norm(input.getEvidenceSchemaVersion()));
        values.put("evidenceSchemaHash", norm(input.getEvidenceSchemaHash()));
        values.put("sourceType", norm(input.getSourceType()));
        values.put("sourceId", input.getSourceId());
        values.put("meetingId", input.getMeetingId());
        values.put("recordingId", input.getRecordingId());
        values.put("projectId", input.getProjectId());
        values.put("teamId", input.getTeamId());
        values.put("useHistoryMemory", Boolean.TRUE.equals(input.getUseHistoryMemory()));
        values.put("historyMemorySnapshotId", input.getHistoryMemorySnapshotId());
        values.put("modelVersion", norm(defaulted(input.getModelVersion(), "default-model")));
        values.put("promptVersion", norm(defaulted(input.getPromptVersion(), "default-prompt")));
        values.put("scoringConfigHash", norm(defaulted(input.getScoringConfigHash(), "default-config")));
        return sha256(values.entrySet().stream()
                .map(entry -> entry.getKey() + "=" + String.valueOf(entry.getValue()))
                .collect(Collectors.joining("|")));
    }

    private String norm(String value) {
        return value == null ? "" : value.trim();
    }

    private String defaulted(String value, String fallback) {
        return value == null || value.isBlank() ? fallback : value;
    }

    private String sha256(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder builder = new StringBuilder(hash.length * 2);
            for (byte b : hash) {
                builder.append(String.format("%02x", b));
            }
            return builder.toString();
        } catch (Exception e) {
            throw new IllegalStateException("failed to create scoring fingerprint", e);
        }
    }
}
