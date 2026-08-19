package com.orep.backend.service;

import com.orep.backend.entity.AiScoreTranscriptSegment;
import com.orep.backend.mapper.AiScoreTranscriptSegmentMapper;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;

import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.times;
import static org.mockito.Mockito.verify;

class AiScoreTranscriptServiceTest {

    @Test
    void replacesCallbackSegmentsInTimelineOrderWithRealSpeakerLabels() {
        AiScoreTranscriptSegmentMapper mapper = mock(AiScoreTranscriptSegmentMapper.class);
        AiScoreTranscriptService service = new AiScoreTranscriptService(mapper);

        List<AiScoreTranscriptSegment> result = service.replaceFromCallback(26L, List.of(
                mapOf("start", 3.5, "end", 5.0, "text", "第二段", "speaker_id", 2, "confidence", 0.87),
                mapOf("start", 1.0, "end", 3.0, "text", "第一段", "speaker", "SPEAKER_1")
        ));

        assertThat(result).hasSize(2);
        assertThat(result.get(0).getSegmentNo()).isEqualTo(1);
        assertThat(result.get(0).getStartMs()).isEqualTo(1000L);
        assertThat(result.get(0).getEndMs()).isEqualTo(3000L);
        assertThat(result.get(0).getSpeakerLabel()).isEqualTo("SPEAKER_1");
        assertThat(result.get(1).getStartMs()).isEqualTo(3500L);
        assertThat(result.get(1).getSpeakerLabel()).isEqualTo("SPEAKER_2");
        assertThat(result.get(1).getConfidence()).isEqualByComparingTo("0.8700");
        assertThat(result).allSatisfy(item -> {
            assertThat(item.getSessionId()).isEqualTo(26L);
            assertThat(item.getSourceType()).isEqualTo("pipeline_asr");
            assertThat(item.getSegmentHash()).hasSize(64);
        });
        verify(mapper).delete(any());
        verify(mapper, times(2)).insert(any(AiScoreTranscriptSegment.class));
    }

    @Test
    void missingSpeakerRemainsNullInsteadOfInventingSpeakerZero() {
        AiScoreTranscriptSegmentMapper mapper = mock(AiScoreTranscriptSegmentMapper.class);
        AiScoreTranscriptService service = new AiScoreTranscriptService(mapper);

        List<AiScoreTranscriptSegment> result = service.replaceFromCallback(26L, List.of(
                mapOf("start", 0.0, "end", 1.0, "text", "没有说话人字段")
        ));

        assertThat(result.getFirst().getSpeakerLabel()).isNull();
    }

    @Test
    void explicitMillisecondFieldsAreNotMultipliedAgain() {
        AiScoreTranscriptService service = new AiScoreTranscriptService(mock(AiScoreTranscriptSegmentMapper.class));

        List<AiScoreTranscriptSegment> result = service.replaceFromCallback(26L, List.of(
                mapOf("startMs", 1250L, "endMs", 2750L, "text", "毫秒时间")
        ));

        assertThat(result.getFirst().getStartMs()).isEqualTo(1250L);
        assertThat(result.getFirst().getEndMs()).isEqualTo(2750L);
    }

    @Test
    void invalidSegmentRejectsWholeReplacementBeforeDeletingPriorSnapshot() {
        AiScoreTranscriptSegmentMapper mapper = mock(AiScoreTranscriptSegmentMapper.class);
        AiScoreTranscriptService service = new AiScoreTranscriptService(mapper);

        assertThatThrownBy(() -> service.replaceFromCallback(26L, List.of(
                mapOf("start", 2.0, "end", 1.0, "text", "时间倒退")
        )))
                .isInstanceOf(IllegalArgumentException.class)
                .hasMessageContaining("时间范围");

        verify(mapper, never()).delete(any());
        verify(mapper, never()).insert(any());
    }

    @Test
    void completedCallbackReplayReplacesRowsInsteadOfAppendingDuplicates() {
        AiScoreTranscriptSegmentMapper mapper = mock(AiScoreTranscriptSegmentMapper.class);
        AiScoreTranscriptService service = new AiScoreTranscriptService(mapper);
        List<Map<String, Object>> segments = List.of(
                mapOf("start", 0.0, "end", 1.0, "text", "同一份结果")
        );

        List<AiScoreTranscriptSegment> first = service.replaceFromCallback(26L, segments);
        List<AiScoreTranscriptSegment> second = service.replaceFromCallback(26L, segments);

        assertThat(first.getFirst().getSegmentHash()).isEqualTo(second.getFirst().getSegmentHash());
        verify(mapper, times(2)).delete(any());
        verify(mapper, times(2)).insert(any(AiScoreTranscriptSegment.class));
    }

    private static Map<String, Object> mapOf(Object... values) {
        Map<String, Object> result = new LinkedHashMap<>();
        for (int index = 0; index < values.length; index += 2) {
            result.put(String.valueOf(values[index]), values[index + 1]);
        }
        return result;
    }
}
