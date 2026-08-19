package com.orep.backend.service;

import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class RecordingEvidenceAnchorBuilderTest {

    @Test
    void buildsPlaybackAnchorsForReadySplitRecordingFiles() {
        RecordingEvidenceAnchorBuilder builder = new RecordingEvidenceAnchorBuilder();

        List<Map<String, Object>> anchors = builder.build(List.of(Map.of(
                "id", 77L,
                "meetingId", 42L,
                "status", "READY",
                "filePath", "recordings/meeting_42/main.webm",
                "cameraFile", "recordings/meeting_42/camera.webm",
                "screenFile", "recordings/meeting_42/screen.webm",
                "audioFile", "recordings/meeting_42/audio.webm",
                "durationSeconds", 126
        )));

        assertTrue(anchors.stream().anyMatch(anchor ->
                "recording_video".equals(anchor.get("type")) &&
                        "/api/recording/77/stream?file=video".equals(anchor.get("sourceRef"))));
        assertTrue(anchors.stream().anyMatch(anchor ->
                "recording_screen".equals(anchor.get("type")) &&
                        "/api/recording/77/stream?file=screen".equals(anchor.get("sourceRef"))));
        assertTrue(anchors.stream().anyMatch(anchor ->
                "recording_audio".equals(anchor.get("type")) &&
                        String.valueOf(anchor.get("summary")).contains("126秒")));
        assertEquals(4, anchors.size());
    }
}
