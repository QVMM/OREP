package com.orep.backend.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.core.JdbcTemplate;

import java.time.Clock;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;

class TrainingDayLearningResourceSummaryTest {

    @Test
    void summaryIncludesOrderedResourcePreviewAndTypeCounts() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        TrainingDayLearningResourceService service = new TrainingDayLearningResourceService(
                jdbc,
                new ObjectMapper(),
                "./target/test-learning-uploads",
                new TrainingDayAvailabilityService(Clock.systemUTC())
        );
        when(jdbc.queryForList(anyString(), any(Object[].class))).thenAnswer(invocation -> {
            String sql = invocation.getArgument(0);
            if (sql.contains("COUNT(*) learningResourceCount")) {
                return List.of(new LinkedHashMap<>(Map.of(
                        "dayId", 51L,
                        "learningResourceCount", 2,
                        "requiredLearningCount", 1,
                        "estimatedLearningMinutes", 8,
                        "completedLearningCount", 0
                )));
            }
            if (sql.contains("r.resource_type resourceType")) {
                return List.of(
                        new LinkedHashMap<>(Map.of(
                                "id", 71L,
                                "dayId", 51L,
                                "resourceType", "VIDEO",
                                "title", "病虫害识别操作演示",
                                "durationSeconds", 420,
                                "required", 1,
                                "learningStatus", "NOT_STARTED",
                                "progressPercent", 0
                        )),
                        new LinkedHashMap<>(Map.of(
                                "id", 72L,
                                "dayId", 51L,
                                "resourceType", "DOCUMENT",
                                "title", "配套操作手册",
                                "durationSeconds", 0,
                                "required", 0,
                                "learningStatus", "NOT_STARTED",
                                "progressPercent", 0
                        ))
                );
            }
            return List.of();
        });

        Map<String, Object> summary = service.summaries(List.of(51L), 23L).get(51L);

        assertNotNull(summary);
        assertEquals(1, summary.get("videoResourceCount"));
        assertEquals(1, summary.get("documentResourceCount"));
        Map<?, ?> preview = (Map<?, ?>) summary.get("learningPreview");
        assertEquals("VIDEO", preview.get("resourceType"));
        assertEquals("病虫害识别操作演示", preview.get("title"));
        assertEquals(420, preview.get("durationSeconds"));
    }
}
