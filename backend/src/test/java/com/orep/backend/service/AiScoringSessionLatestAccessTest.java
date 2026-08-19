package com.orep.backend.service;

import com.orep.backend.entity.AiScoringSession;
import com.orep.backend.mapper.AiScoreDeductionMapper;
import com.orep.backend.mapper.AiScoreEvidenceAnchorMapper;
import com.orep.backend.mapper.AiScoreObservationMapper;
import com.orep.backend.mapper.AiScoreReportMapper;
import com.orep.backend.mapper.AiScoringSessionMapper;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class AiScoringSessionLatestAccessTest {

    @Test
    void studentLatestSqlStaysOnOwnOrTeamSessions() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        AiScoringSessionMapper sessions = mock(AiScoringSessionMapper.class);
        when(jdbc.query(anyString(), any(RowMapper.class), any(Object[].class))).thenReturn(List.of(47L));
        AiScoringSession session = new AiScoringSession();
        session.setId(47L);
        session.setTeamId(3L);
        session.setStatus("completed");
        when(sessions.selectById(47L)).thenReturn(session);

        AiScoringSessionService service = new AiScoringSessionService(
                sessions,
                mock(AiScoreReportMapper.class),
                mock(AiScoreObservationMapper.class),
                mock(AiScoreDeductionMapper.class),
                mock(AiScoreEvidenceAnchorMapper.class),
                mock(RubricResolverService.class),
                mock(ScoringFingerprintService.class),
                jdbc
        );

        assertEquals(47L, service.latest(null, null, null, 3L, 10L, "STUDENT").getSessionId());

        ArgumentCaptor<String> sql = ArgumentCaptor.forClass(String.class);
        ArgumentCaptor<Object[]> params = ArgumentCaptor.forClass(Object[].class);
        verify(jdbc).query(sql.capture(), any(RowMapper.class), params.capture());
        assertTrue(sql.getValue().contains("created_by"));
        assertTrue(sql.getValue().contains("project_team_member"));
        assertFalse(sql.getValue().contains("tenant"));
        assertEquals(10L, params.getValue()[0]);
        assertEquals(10L, params.getValue()[1]);
    }

    @Test
    void otherTeamLatestIsHidden() {
        JdbcTemplate jdbc = mock(JdbcTemplate.class);
        when(jdbc.query(anyString(), any(RowMapper.class), any(Object[].class))).thenReturn(List.of());
        AiScoringSessionService service = new AiScoringSessionService(
                mock(AiScoringSessionMapper.class),
                mock(AiScoreReportMapper.class),
                mock(AiScoreObservationMapper.class),
                mock(AiScoreDeductionMapper.class),
                mock(AiScoreEvidenceAnchorMapper.class),
                mock(RubricResolverService.class),
                mock(ScoringFingerprintService.class),
                jdbc
        );

        assertThrows(IllegalStateException.class,
                () -> service.latest(null, 1L, null, 3L, 10L, "STUDENT"));

        ArgumentCaptor<String> sql = ArgumentCaptor.forClass(String.class);
        verify(jdbc).query(sql.capture(), any(RowMapper.class), any(Object[].class));
        assertTrue(sql.getValue().contains("s.team_id = ?"));
        assertTrue(sql.getValue().contains("project_team_member"));
    }
}
