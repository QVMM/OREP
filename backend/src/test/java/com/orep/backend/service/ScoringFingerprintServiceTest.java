package com.orep.backend.service;

import com.orep.backend.dto.ScoringFingerprintInput;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class ScoringFingerprintServiceTest {

    @Test
    void sameInputCreatesSameFingerprint() {
        ScoringFingerprintService service = new ScoringFingerprintService();
        ScoringFingerprintInput input = baseInput();

        String first = service.fingerprint(input);
        String second = service.fingerprint(input);

        assertEquals(first, second);
        assertEquals(64, first.length());
    }

    @Test
    void rubricHashChangeCreatesDifferentFingerprint() {
        ScoringFingerprintService service = new ScoringFingerprintService();
        ScoringFingerprintInput first = baseInput();
        ScoringFingerprintInput second = baseInput();
        second.setRubricHash("rubric-hash-v2");

        assertNotEquals(service.fingerprint(first), service.fingerprint(second));
    }

    @Test
    void evidenceSchemaFieldsChangeCreatesDifferentFingerprint() {
        ScoringFingerprintService service = new ScoringFingerprintService();
        ScoringFingerprintInput base = baseInput();

        ScoringFingerprintInput differentId = baseInput();
        differentId.setEvidenceSchemaId(99L);
        assertNotEquals(service.fingerprint(base), service.fingerprint(differentId));

        ScoringFingerprintInput differentVersion = baseInput();
        differentVersion.setEvidenceSchemaVersion("schema-v2");
        assertNotEquals(service.fingerprint(base), service.fingerprint(differentVersion));

        ScoringFingerprintInput differentHash = baseInput();
        differentHash.setEvidenceSchemaHash("schema-hash-v2");
        assertNotEquals(service.fingerprint(base), service.fingerprint(differentHash));
    }

    private ScoringFingerprintInput baseInput() {
        ScoringFingerprintInput input = new ScoringFingerprintInput();
        input.setTrackId("track-it");
        input.setRubricId("rubric-it");
        input.setRubricHash("rubric-hash-v1");
        input.setEvidenceSchemaId(33L);
        input.setEvidenceSchemaVersion("schema-v1");
        input.setEvidenceSchemaHash("schema-hash-v1");
        input.setSourceType("meeting_recording");
        input.setMeetingId(12L);
        input.setProjectId(3L);
        input.setTeamId(9L);
        input.setUseHistoryMemory(true);
        input.setHistoryMemorySnapshotId(88L);
        input.setModelVersion("default-model");
        input.setPromptVersion("default-prompt");
        input.setScoringConfigHash("default-config");
        return input;
    }
}
