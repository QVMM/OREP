package com.orep.backend.service;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.*;

class AiResultEvidenceAnchorExtractorTest {

    @TempDir
    Path tempDir;

    @Test
    void extractsPreciseAnchorsFromAiResultJson() throws Exception {
        Path result = tempDir.resolve("result_42.json");
        Files.writeString(result, """
            {
              "asr": {
                "segments": [
                  {"start": 12.3, "end": 18.8, "text": "我们现场演示核心流程已经跑通"}
                ]
              },
              "video_analysis": {
                "per_frame": [
                  {"frame_id": "frame-001", "timestamp": 31.5, "summary": "屏幕展示登录成功和数据看板"}
                ],
                "aggregates": {
                  "screen_content_summary": {
                    "text": "PPT展示了核心功能，但性能测试数据不足"
                  }
                }
              },
              "fusion": {
                "timeline": [
                  {"time": "00:00:32", "event": "系统完成端到端演示"}
                ],
                "screen_content_summary": {
                  "text": "OCR识别到准确率、响应时间等字段缺失"
                }
              }
            }
            """);

        AiResultEvidenceAnchorExtractor extractor = new AiResultEvidenceAnchorExtractor();
        List<Map<String, Object>> anchors = extractor.extract(result, 42L, 1001L);

        assertTrue(anchors.stream().anyMatch(anchor ->
                "transcript_segment".equals(anchor.get("type")) &&
                        "00:12.3-00:18.8".equals(anchor.get("sourceRef"))));
        assertTrue(anchors.stream().anyMatch(anchor ->
                "key_frame".equals(anchor.get("type")) &&
                        "frame-001@00:31.5".equals(anchor.get("sourceRef"))));
        assertTrue(anchors.stream().anyMatch(anchor ->
                "screen_ocr".equals(anchor.get("type")) &&
                        String.valueOf(anchor.get("summary")).contains("响应时间")));
        assertTrue(anchors.stream().anyMatch(anchor ->
                "fusion_timeline".equals(anchor.get("type")) &&
                        "00:00:32".equals(anchor.get("sourceRef"))));
    }

    @Test
    void extractsRawExcerptForEvidenceSourceRef() throws Exception {
        Path result = tempDir.resolve("result_43.json");
        Files.writeString(result, """
            {
              "video_analysis": {
                "per_frame": [
                  {"frame_id": "frame-001", "timestamp": 31.5, "summary": "屏幕展示登录成功和数据看板"},
                  {"frame_id": "frame-002", "timestamp": 42.0, "summary": "评委看到性能数据缺失"}
                ],
                "aggregates": {
                  "screen_content_summary": {
                    "text": "PPT展示了核心功能，但性能测试数据不足"
                  }
                }
              },
              "fusion": {
                "timeline": [
                  {"time": "00:00:32", "event": "系统完成端到端演示"},
                  {"time": "00:00:45", "event": "评委追问测试数据"}
                ],
                "screen_content_summary": {
                  "text": "OCR识别到准确率、响应时间等字段缺失"
                }
              }
            }
            """);

        AiResultEvidenceAnchorExtractor extractor = new AiResultEvidenceAnchorExtractor();

        Map<String, Object> frame = extractor.extractExcerpt(result, "frame-001@00:31.5");
        Map<String, Object> ocr = extractor.extractExcerpt(result, "fusion.screen_content_summary");
        Map<String, Object> timeline = extractor.extractExcerpt(result, "00:00:32");

        assertEquals("key_frame", frame.get("type"));
        assertTrue(String.valueOf(frame.get("summary")).contains("登录成功"));
        assertEquals("screen_ocr", ocr.get("type"));
        assertTrue(String.valueOf(ocr.get("summary")).contains("响应时间"));
        assertEquals("fusion_timeline", timeline.get("type"));
        assertTrue(String.valueOf(timeline.get("summary")).contains("端到端演示"));
    }
}
