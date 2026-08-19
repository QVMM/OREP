package com.orep.backend.service;

import org.junit.jupiter.api.Test;

import java.nio.file.Files;
import java.nio.file.Path;

import static org.assertj.core.api.Assertions.assertThat;

class SpeakerScoringIsolationContractTest {

    @Test
    void personalAbilityNeverConsumesLegacyHiddenSpeakerDimensionScores() throws Exception {
        String source = Files.readString(Path.of(
                "src/main/java/com/orep/backend/service/ProjectTeamService.java"
        ));

        assertThat(source).doesNotContain("speakerDimensionScore(");
        assertThat(source).doesNotContain("readJsonMap(speaker.get(\"dimensionsJson\"))");
    }

    @Test
    void legacySpeakerIngestionPersistsEvidenceButNotASecondScoreSet() throws Exception {
        String source = Files.readString(Path.of(
                "src/main/java/com/orep/backend/service/ProjectTeamService.java"
        ));
        int methodStart = source.indexOf("public void ingestRoadshowSpeakers");
        int methodEnd = source.indexOf("private Long teamTenantId", methodStart);
        String method = source.substring(methodStart, methodEnd);

        assertThat(method).doesNotContain("dimensions_json");
        assertThat(method).doesNotContain("speaker.get(\"dimensions\")");
        assertThat(method).contains("evidence_quotes_json", "segments_json");
    }
}
