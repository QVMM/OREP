package com.orep.backend.service;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.stereotype.Component;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.*;

@Component
public class AiResultEvidenceAnchorExtractor {
    private final ObjectMapper objectMapper = new ObjectMapper();

    public List<Map<String, Object>> extract(Path resultPath, Long meetingId, Long aiReportId) {
        if (resultPath == null || !Files.isRegularFile(resultPath)) return List.of();
        try {
            Map<String, Object> result = objectMapper.readValue(Files.readString(resultPath), new TypeReference<>() {});
            List<Map<String, Object>> anchors = new ArrayList<>();
            anchors.addAll(transcriptAnchors(result, meetingId, aiReportId));
            anchors.addAll(keyFrameAnchors(result, meetingId, aiReportId));
            anchors.addAll(screenOcrAnchors(result, meetingId, aiReportId));
            anchors.addAll(fusionTimelineAnchors(result, meetingId, aiReportId));
            return anchors.stream().limit(24).toList();
        } catch (Exception ignored) {
            return List.of();
        }
    }

    public Map<String, Object> extractExcerpt(Path resultPath, String sourceRef) {
        if (resultPath == null || !Files.isRegularFile(resultPath) || sourceRef == null || sourceRef.isBlank()) return Map.of();
        try {
            Map<String, Object> result = objectMapper.readValue(Files.readString(resultPath), new TypeReference<>() {});
            Map<String, Object> frame = keyFrameExcerpt(result, sourceRef);
            if (!frame.isEmpty()) return frame;
            Map<String, Object> screen = screenOcrExcerpt(result, sourceRef);
            if (!screen.isEmpty()) return screen;
            Map<String, Object> timeline = fusionTimelineExcerpt(result, sourceRef);
            if (!timeline.isEmpty()) return timeline;
        } catch (Exception ignored) {
        }
        return Map.of();
    }

    private Map<String, Object> keyFrameExcerpt(Map<String, Object> result, String sourceRef) {
        String frameNeedle = sourceRef.contains("@") ? sourceRef.substring(0, sourceRef.indexOf("@")) : sourceRef;
        if (!frameNeedle.toLowerCase(Locale.ROOT).contains("frame")) return Map.of();
        Map<String, Object> video = map(first(result.get("video_analysis"), result.get("video_screen_analysis"), result.get("video_camera_analysis")));
        for (Object item : list(video.get("per_frame"))) {
            Map<String, Object> frame = map(item);
            String frameId = text(first(frame.get("frame_id"), frame.get("frameId"), frame.get("id")), "");
            if (!frameNeedle.equals(frameId)) continue;
            String summary = text(first(frame.get("summary"), frame.get("description"), frame.get("caption"), frame.get("ocr_text")), "");
            return excerpt("key_frame", summary, sourceRef, frame);
        }
        return Map.of();
    }

    private Map<String, Object> screenOcrExcerpt(Map<String, Object> result, String sourceRef) {
        Object value = null;
        if ("fusion.screen_content_summary".equals(sourceRef)) {
            value = map(result.get("fusion")).get("screen_content_summary");
        } else if ("video_analysis.aggregates.screen_content_summary".equals(sourceRef)) {
            value = map(map(result.get("video_analysis")).get("aggregates")).get("screen_content_summary");
        }
        if (value == null) return Map.of();
        Map<String, Object> raw = value instanceof Map<?, ?> ? map(value) : Map.of("text", value);
        String summary = text(first(raw.get("text"), raw.get("summary"), raw.get("ocr"), raw.get("content")), "");
        return excerpt("screen_ocr", summary, sourceRef, raw);
    }

    private Map<String, Object> fusionTimelineExcerpt(Map<String, Object> result, String sourceRef) {
        Map<String, Object> fusion = map(result.get("fusion"));
        for (Object item : list(fusion.get("timeline"))) {
            Map<String, Object> event = map(item);
            String time = text(first(event.get("time"), event.get("timestamp"), event.get("start")), "");
            if (!sourceRef.equals(time)) continue;
            String summary = text(first(event.get("event"), event.get("summary"), event.get("text"), event.get("description")), "");
            return excerpt("fusion_timeline", summary, sourceRef, event);
        }
        return Map.of();
    }

    private Map<String, Object> excerpt(String type, String summary, String sourceRef, Map<String, Object> raw) {
        Map<String, Object> excerpt = new LinkedHashMap<>();
        excerpt.put("type", type);
        excerpt.put("summary", shortText(summary, 240));
        excerpt.put("sourceRef", sourceRef);
        excerpt.put("raw", raw);
        return excerpt;
    }

    private List<Map<String, Object>> transcriptAnchors(Map<String, Object> result, Long meetingId, Long aiReportId) {
        List<Map<String, Object>> anchors = new ArrayList<>();
        Map<String, Object> asr = map(result.get("asr"));
        int index = 1;
        for (Object item : list(asr.get("segments"))) {
            Map<String, Object> segment = map(item);
            String text = text(first(segment.get("text"), segment.get("sentence"), segment.get("content")), "");
            if (text.isBlank()) continue;
            anchors.add(anchor(
                    "transcript_segment",
                    shortText(text, 160),
                    timeRange(segment.get("start"), segment.get("end"), "asr:" + index),
                    meetingId,
                    aiReportId
            ));
            if (++index > 8) break;
        }
        return anchors;
    }

    private List<Map<String, Object>> keyFrameAnchors(Map<String, Object> result, Long meetingId, Long aiReportId) {
        List<Map<String, Object>> anchors = new ArrayList<>();
        Map<String, Object> video = map(first(result.get("video_analysis"), result.get("video_screen_analysis"), result.get("video_camera_analysis")));
        int index = 1;
        for (Object item : list(video.get("per_frame"))) {
            Map<String, Object> frame = map(item);
            String summary = text(first(frame.get("summary"), frame.get("description"), frame.get("caption"), frame.get("ocr_text")), "");
            if (summary.isBlank()) continue;
            String frameId = text(first(frame.get("frame_id"), frame.get("frameId"), frame.get("id")), "frame-" + index);
            anchors.add(anchor(
                    "key_frame",
                    shortText(summary, 160),
                    frameId + "@" + singleTime(frame.get("timestamp"), frame.get("time"), "frame:" + index),
                    meetingId,
                    aiReportId
            ));
            if (++index > 8) break;
        }
        return anchors;
    }

    private List<Map<String, Object>> screenOcrAnchors(Map<String, Object> result, Long meetingId, Long aiReportId) {
        List<Map<String, Object>> anchors = new ArrayList<>();
        Map<String, Object> video = map(first(result.get("video_analysis"), result.get("video_screen_analysis")));
        Map<String, Object> aggregates = map(video.get("aggregates"));
        addScreenSummary(anchors, aggregates.get("screen_content_summary"), "video_analysis.aggregates.screen_content_summary", meetingId, aiReportId);
        Map<String, Object> fusion = map(result.get("fusion"));
        addScreenSummary(anchors, fusion.get("screen_content_summary"), "fusion.screen_content_summary", meetingId, aiReportId);
        return anchors;
    }

    private void addScreenSummary(List<Map<String, Object>> anchors, Object value, String sourceRef, Long meetingId, Long aiReportId) {
        String summary = "";
        if (value instanceof Map<?, ?>) {
            Map<String, Object> map = map(value);
            summary = text(first(map.get("text"), map.get("summary"), map.get("ocr"), map.get("content")), "");
        } else {
            summary = text(value, "");
        }
        if (!summary.isBlank()) {
            anchors.add(anchor("screen_ocr", shortText(summary, 180), sourceRef, meetingId, aiReportId));
        }
    }

    private List<Map<String, Object>> fusionTimelineAnchors(Map<String, Object> result, Long meetingId, Long aiReportId) {
        List<Map<String, Object>> anchors = new ArrayList<>();
        Map<String, Object> fusion = map(result.get("fusion"));
        int index = 1;
        for (Object item : list(fusion.get("timeline"))) {
            Map<String, Object> event = map(item);
            String summary = text(first(event.get("event"), event.get("summary"), event.get("text"), event.get("description")), "");
            if (summary.isBlank()) continue;
            anchors.add(anchor(
                    "fusion_timeline",
                    shortText(summary, 160),
                    text(first(event.get("time"), event.get("timestamp"), event.get("start")), "timeline:" + index),
                    meetingId,
                    aiReportId
            ));
            if (++index > 8) break;
        }
        return anchors;
    }

    private Map<String, Object> anchor(String type, String summary, String sourceRef, Long meetingId, Long aiReportId) {
        Map<String, Object> anchor = new LinkedHashMap<>();
        anchor.put("type", type);
        anchor.put("summary", summary);
        anchor.put("sourceRef", sourceRef);
        anchor.put("meetingId", meetingId == null ? "" : meetingId);
        anchor.put("aiReportId", aiReportId == null ? "" : aiReportId);
        return anchor;
    }

    private String timeRange(Object start, Object end, String fallback) {
        if (start == null && end == null) return fallback;
        return formatSeconds(start) + "-" + formatSeconds(end);
    }

    private String singleTime(Object primary, Object secondary, String fallback) {
        Object value = first(primary, secondary);
        return value == null ? fallback : formatSeconds(value);
    }

    private String formatSeconds(Object value) {
        try {
            double seconds = Double.parseDouble(String.valueOf(value));
            int minutes = (int) (seconds / 60);
            double rest = seconds - minutes * 60;
            return String.format(Locale.ROOT, "%02d:%04.1f", minutes, rest);
        } catch (Exception ignored) {
            return String.valueOf(value);
        }
    }

    @SuppressWarnings("unchecked")
    private List<Object> list(Object value) {
        if (value instanceof List<?> list) return (List<Object>) list;
        return List.of();
    }

    private Map<String, Object> map(Object value) {
        if (value instanceof Map<?, ?> raw) {
            Map<String, Object> converted = new LinkedHashMap<>();
            raw.forEach((key, item) -> converted.put(String.valueOf(key), item));
            return converted;
        }
        return Map.of();
    }

    private Object first(Object... values) {
        for (Object value : values) if (value != null) return value;
        return null;
    }

    private String text(Object value, String fallback) {
        if (value == null) return fallback;
        String text = String.valueOf(value).trim();
        return text.isEmpty() ? fallback : text;
    }

    private String shortText(String value, int maxLength) {
        if (value == null) return "";
        String text = value.replaceAll("[\\r\\n\\t]+", " ").trim();
        return text.length() <= maxLength ? text : text.substring(0, maxLength - 1) + "…";
    }
}
