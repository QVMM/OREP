package com.orep.backend.service;

import org.springframework.stereotype.Component;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

@Component
public class RecordingEvidenceAnchorBuilder {

    public List<Map<String, Object>> build(List<Map<String, Object>> recordings) {
        List<Map<String, Object>> anchors = new ArrayList<>();
        for (Map<String, Object> recording : recordings == null ? List.<Map<String, Object>>of() : recordings) {
            if (!"READY".equalsIgnoreCase(String.valueOf(recording.getOrDefault("status", "")))) continue;
            Long id = longValue(recording.get("id"));
            if (id == null) continue;
            Long meetingId = longValue(recording.get("meetingId"));
            String duration = durationText(recording.get("durationSeconds"));
            addAnchor(anchors, recording, "filePath", "video", "recording_video", "完整录制视频" + duration, id, meetingId);
            addAnchor(anchors, recording, "cameraFile", "camera", "recording_camera", "摄像头录制" + duration, id, meetingId);
            addAnchor(anchors, recording, "screenFile", "screen", "recording_screen", "屏幕录制" + duration, id, meetingId);
            addAnchor(anchors, recording, "audioFile", "audio", "recording_audio", "音频录制" + duration, id, meetingId);
        }
        return anchors.stream().limit(16).toList();
    }

    private void addAnchor(
            List<Map<String, Object>> anchors,
            Map<String, Object> recording,
            String pathKey,
            String fileType,
            String anchorType,
            String summary,
            Long id,
            Long meetingId
    ) {
        String path = text(recording.get(pathKey));
        if (path == null) return;
        Map<String, Object> anchor = new LinkedHashMap<>();
        anchor.put("type", anchorType);
        anchor.put("summary", summary);
        anchor.put("sourceRef", "/api/recording/" + id + "/stream?file=" + fileType);
        anchor.put("meetingId", meetingId == null ? "" : meetingId);
        anchor.put("recordingId", id);
        anchor.put("objectPath", path);
        anchors.add(anchor);
    }

    private String durationText(Object value) {
        Long seconds = longValue(value);
        return seconds == null || seconds <= 0 ? "" : "（" + seconds + "秒）";
    }

    private Long longValue(Object value) {
        if (value instanceof Number number) return number.longValue();
        try {
            String text = text(value);
            return text == null ? null : Long.parseLong(text);
        } catch (Exception ignored) {
            return null;
        }
    }

    private String text(Object value) {
        if (value == null) return null;
        String text = String.valueOf(value).trim();
        return text.isEmpty() ? null : text;
    }
}
