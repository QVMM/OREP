package com.orep.backend.service;

import com.orep.backend.entity.AiScoringSession;
import com.orep.backend.mapper.AiScoreReportMapper;
import com.orep.backend.mapper.AiScoringSessionMapper;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class AiScoreFailureStateHardeningTest {

    @Test
    void markFailedStoresExplicitStageAndMessage() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        AiScoringSession session = new AiScoringSession();
        session.setId(77L);
        session.setSessionNo("SC-20260624-000077");
        session.setStatus("scoring");
        session.setTrackName("新一代信息技术赛道");
        session.setSourceType("meeting_recording");
        when(sessionMapper.selectById(77L)).thenReturn(session);
        AiScoringSessionService service = new AiScoringSessionService(
                sessionMapper,
                mock(AiScoreReportMapper.class),
                mock(RubricResolverService.class),
                new ScoringFingerprintService()
        );

        var response = service.markFailed(77L, "抽帧服务不可用", "frame_extract_failed");

        assertThat(response.getStatus()).isEqualTo("failed");
        assertThat(response.getCurrentStage()).isEqualTo("frame_extract_failed");
        assertThat(session.getErrorMessage()).isEqualTo("抽帧服务不可用");
        verify(sessionMapper).updateById(any(AiScoringSession.class));
    }
}
