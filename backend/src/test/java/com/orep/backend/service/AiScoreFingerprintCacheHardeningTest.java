package com.orep.backend.service;

import com.orep.backend.dto.AiScoringSessionCreateRequest;
import com.orep.backend.dto.ResolvedRubric;
import com.orep.backend.entity.AiScoringSession;
import com.orep.backend.mapper.AiScoreReportMapper;
import com.orep.backend.mapper.AiScoringSessionMapper;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class AiScoreFingerprintCacheHardeningTest {

    @Test
    void sameMeetingInputCreatesNewSessionUnlessReuseCompleted() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        RubricResolverService resolver = mock(RubricResolverService.class);
        when(resolver.resolve("track-food", "餐饮赛道")).thenReturn(rubric());
        doAnswer(invocation -> {
            AiScoringSession session = invocation.getArgument(0);
            session.setId(223L);
            return 1;
        }).when(sessionMapper).insert(any(AiScoringSession.class));
        AiScoringSessionService service = new AiScoringSessionService(
                sessionMapper,
                mock(AiScoreReportMapper.class),
                resolver,
                new ScoringFingerprintService()
        );

        var response = service.createSession(request("meeting_recording"), 7L);

        assertThat(response.getSessionId()).isEqualTo(223L);
        assertThat(response.getCached()).isFalse();
        verify(sessionMapper).insert(any(AiScoringSession.class));
        verify(sessionMapper, never()).selectOne(any());
    }

    @Test
    void reuseCompletedHitsCompletedCacheAndDoesNotCreateNewSession() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        RubricResolverService resolver = mock(RubricResolverService.class);
        when(resolver.resolve("track-food", "餐饮赛道")).thenReturn(rubric());
        AiScoringSession cached = completedSession(222L);
        when(sessionMapper.selectOne(any())).thenReturn(cached);
        AiScoringSessionService service = new AiScoringSessionService(
                sessionMapper,
                mock(AiScoreReportMapper.class),
                resolver,
                new ScoringFingerprintService()
        );

        var request = request("meeting_recording");
        request.setReuseCompleted(true);
        var response = service.createSession(request, 7L);

        assertThat(response.getSessionId()).isEqualTo(222L);
        assertThat(response.getCached()).isTrue();
        assertThat(response.getMessage()).contains("历史评分输入完全一致");
        verify(sessionMapper, never()).insert(any(AiScoringSession.class));
    }

    @Test
    void uploadedVideoAlwaysCreatesNewSessionUntilMediaHashesJoinFingerprint() {
        AiScoringSessionMapper sessionMapper = mock(AiScoringSessionMapper.class);
        RubricResolverService resolver = mock(RubricResolverService.class);
        when(resolver.resolve("track-food", "餐饮赛道")).thenReturn(rubric());
        doAnswer(invocation -> {
            AiScoringSession session = invocation.getArgument(0);
            session.setId(333L);
            return 1;
        }).when(sessionMapper).insert(any(AiScoringSession.class));
        AiScoringSessionService service = new AiScoringSessionService(
                sessionMapper,
                mock(AiScoreReportMapper.class),
                resolver,
                new ScoringFingerprintService()
        );

        var response = service.createSession(request("uploaded_video"), 7L);

        assertThat(response.getSessionId()).isEqualTo(333L);
        assertThat(response.getCached()).isFalse();
        verify(sessionMapper, never()).selectOne(any());
        verify(sessionMapper).insert(any(AiScoringSession.class));
    }

    private AiScoringSessionCreateRequest request(String sourceType) {
        AiScoringSessionCreateRequest request = new AiScoringSessionCreateRequest();
        request.setSourceType(sourceType);
        request.setMeetingId(12L);
        request.setProjectId(3L);
        request.setTeamId(9L);
        request.setTrackId("track-food");
        request.setTrackName("餐饮赛道");
        request.setUseHistoryMemory(true);
        return request;
    }

    private AiScoringSession completedSession(Long id) {
        AiScoringSession session = new AiScoringSession();
        session.setId(id);
        session.setSessionNo("SC-20260624-000222");
        session.setStatus("completed");
        session.setCurrentStage("completed");
        session.setTrackName("餐饮赛道");
        session.setSourceType("meeting_recording");
        session.setUseHistoryMemory(true);
        session.setJuryEnabled(false);
        return session;
    }

    private ResolvedRubric rubric() {
        ResolvedRubric rubric = new ResolvedRubric();
        rubric.setTrackId("track-food");
        rubric.setTrackName("餐饮赛道");
        rubric.setRubricId("rubric-food-v12");
        rubric.setRubricInternalVersion("internal-v12");
        rubric.setRubricHash("secret-food-hash");
        rubric.setEvidenceSchemaId(44L);
        rubric.setEvidenceSchemaVersion("schema-food-v12");
        rubric.setEvidenceSchemaHash("schema-food-hash");
        return rubric;
    }
}
