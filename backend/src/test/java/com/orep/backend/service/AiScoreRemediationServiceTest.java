package com.orep.backend.service;

import com.orep.backend.entity.AiScoreRemediationTask;
import com.orep.backend.entity.AiScoreTaskLossLink;
import com.orep.backend.entity.AiScoreTaskVerification;
import com.orep.backend.mapper.AiScoreRemediationTaskMapper;
import com.orep.backend.mapper.AiScoreTaskLossLinkMapper;
import com.orep.backend.mapper.AiScoreTaskVerificationMapper;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.Arguments;
import org.junit.jupiter.params.provider.MethodSource;
import org.mockito.ArgumentCaptor;

import java.math.BigDecimal;
import java.util.List;
import java.util.Map;
import java.util.stream.Stream;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doAnswer;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class AiScoreRemediationServiceTest {

    @ParameterizedTest
    @MethodSource("verificationCases")
    void comparesStableLossBudgets(BigDecimal oldPoints, BigDecimal newPoints, String expected) {
        AiScoreRemediationService service = new AiScoreRemediationService(
                mock(AiScoreRemediationTaskMapper.class),
                mock(AiScoreTaskLossLinkMapper.class),
                mock(AiScoreTaskVerificationMapper.class)
        );

        assertEquals(expected, service.verificationStatus(oldPoints, newPoints));
    }

    static Stream<Arguments> verificationCases() {
        return Stream.of(
                Arguments.of(new BigDecimal("4.0"), BigDecimal.ZERO, "verified"),
                Arguments.of(new BigDecimal("4.0"), new BigDecimal("1.5"), "partial"),
                Arguments.of(new BigDecimal("4.0"), new BigDecimal("4.0"), "failed"),
                Arguments.of(BigDecimal.ZERO, new BigDecimal("2.0"), "regressed")
        );
    }

    @Test
    void persistsOneTaskWithEveryCoveredLossLink() {
        AiScoreRemediationTaskMapper taskMapper = mock(AiScoreRemediationTaskMapper.class);
        AiScoreTaskLossLinkMapper linkMapper = mock(AiScoreTaskLossLinkMapper.class);
        when(taskMapper.selectOne(any())).thenReturn(null);
        doAnswer(invocation -> {
            AiScoreRemediationTask task = invocation.getArgument(0);
            task.setId(91L);
            return 1;
        }).when(taskMapper).insert(any(AiScoreRemediationTask.class));
        AiScoreRemediationService service = new AiScoreRemediationService(
                taskMapper,
                linkMapper,
                mock(AiScoreTaskVerificationMapper.class)
        );

        service.persistSnapshot(
                "project:7",
                26L,
                "[{\"taskId\":\"task-demo\",\"rootCauseKey\":\"DEMO\",\"title\":\"加固演示\",\"status\":\"not_started\",\"coveredLossIds\":[\"l1\",\"l2\"]}]",
                "["
                        + "{\"lossId\":\"l1\",\"lossKey\":\"rule:O1:performance\",\"observationCode\":\"O1\",\"scoreBudgetKey\":\"O1:performance\",\"points\":3.0},"
                        + "{\"lossId\":\"l2\",\"lossKey\":\"rule:O2:evidence\",\"observationCode\":\"O2\",\"scoreBudgetKey\":\"O2:evidence\",\"points\":2.5}"
                        + "]"
        );

        ArgumentCaptor<AiScoreRemediationTask> taskCaptor = ArgumentCaptor.forClass(AiScoreRemediationTask.class);
        ArgumentCaptor<AiScoreTaskLossLink> linkCaptor = ArgumentCaptor.forClass(AiScoreTaskLossLink.class);
        verify(taskMapper).insert(taskCaptor.capture());
        verify(linkMapper).delete(any());
        verify(linkMapper, org.mockito.Mockito.times(2)).insert(linkCaptor.capture());
        assertEquals("task-demo", taskCaptor.getValue().getTaskKey());
        assertEquals("not_started", taskCaptor.getValue().getStatus());
        assertEquals(2, linkCaptor.getAllValues().size());
        assertEquals(
                new BigDecimal("5.5"),
                linkCaptor.getAllValues().stream()
                        .map(AiScoreTaskLossLink::getGapPoints)
                        .reduce(BigDecimal.ZERO, BigDecimal::add)
        );
    }

    @Test
    void replayUpdatesSnapshotWithoutResettingLiveTaskStatus() {
        AiScoreRemediationTaskMapper taskMapper = mock(AiScoreRemediationTaskMapper.class);
        AiScoreTaskLossLinkMapper linkMapper = mock(AiScoreTaskLossLinkMapper.class);
        AiScoreRemediationTask existing = new AiScoreRemediationTask();
        existing.setId(91L);
        existing.setProjectScopeKey("project:7");
        existing.setTaskKey("task-demo");
        existing.setStatus("in_progress");
        when(taskMapper.selectOne(any())).thenReturn(existing);
        AiScoreRemediationService service = new AiScoreRemediationService(
                taskMapper,
                linkMapper,
                mock(AiScoreTaskVerificationMapper.class)
        );

        service.persistSnapshot(
                "project:7",
                26L,
                "[{\"taskId\":\"task-demo\",\"rootCauseKey\":\"DEMO\",\"title\":\"加固演示\",\"status\":\"not_started\",\"coveredLossIds\":[\"l1\"]}]",
                "[{\"lossId\":\"l1\",\"lossKey\":\"rule:O1:performance\",\"observationCode\":\"O1\",\"scoreBudgetKey\":\"O1:performance\",\"points\":3.0}]"
        );

        assertEquals("in_progress", existing.getStatus());
        assertEquals(26L, existing.getLatestReportId());
        verify(taskMapper, never()).insert(any());
        verify(taskMapper).updateById(existing);
        verify(linkMapper).delete(any());
        verify(linkMapper).insert(any(AiScoreTaskLossLink.class));
    }

    @Test
    void liveTasksOverlayDatabaseStatusWithoutMutatingReportSnapshot() {
        AiScoreRemediationTaskMapper taskMapper = mock(AiScoreRemediationTaskMapper.class);
        AiScoreRemediationTask existing = new AiScoreRemediationTask();
        existing.setId(91L);
        existing.setTaskKey("task-demo");
        existing.setTaskJson("{\"taskId\":\"task-demo\",\"title\":\"加固演示\",\"status\":\"not_started\"}");
        existing.setStatus("in_progress");
        when(taskMapper.selectList(any())).thenReturn(List.of(existing));
        AiScoreRemediationService service = new AiScoreRemediationService(
                taskMapper,
                mock(AiScoreTaskLossLinkMapper.class),
                mock(AiScoreTaskVerificationMapper.class)
        );

        List<Map<String, Object>> live = service.liveTasksForReport(
                26L,
                "[{\"taskId\":\"task-demo\",\"title\":\"加固演示\",\"status\":\"not_started\"}]"
        );

        assertEquals(1, live.size());
        assertEquals("in_progress", live.getFirst().get("status"));
        assertEquals(91L, live.getFirst().get("taskRecordId"));
    }

    @Test
    void userStatusUpdateAllowsOnlyExecutionTransitions() {
        AiScoreRemediationTaskMapper taskMapper = mock(AiScoreRemediationTaskMapper.class);
        AiScoreRemediationTask existing = new AiScoreRemediationTask();
        existing.setId(91L);
        existing.setSourceReportId(26L);
        existing.setLatestReportId(26L);
        existing.setStatus("not_started");
        when(taskMapper.selectById(91L)).thenReturn(existing);
        AiScoreRemediationService service = new AiScoreRemediationService(
                taskMapper,
                mock(AiScoreTaskLossLinkMapper.class),
                mock(AiScoreTaskVerificationMapper.class)
        );

        Map<String, Object> updated = service.updateUserTaskStatus(26L, 91L, "in_progress");

        assertEquals("in_progress", existing.getStatus());
        assertEquals("in_progress", updated.get("status"));
        verify(taskMapper).updateById(existing);

        IllegalArgumentException error = assertThrows(
                IllegalArgumentException.class,
                () -> service.updateUserTaskStatus(26L, 91L, "verified")
        );
        assertEquals("task status transition in_progress -> verified is not allowed", error.getMessage());
    }

    @Test
    void nextComparableReportVerifiesAwaitingTaskWhenItsLossDisappears() {
        AiScoreRemediationTaskMapper taskMapper = mock(AiScoreRemediationTaskMapper.class);
        AiScoreTaskLossLinkMapper linkMapper = mock(AiScoreTaskLossLinkMapper.class);
        AiScoreTaskVerificationMapper verificationMapper = mock(AiScoreTaskVerificationMapper.class);
        AiScoreRemediationTask awaiting = new AiScoreRemediationTask();
        awaiting.setId(91L);
        awaiting.setProjectScopeKey("project:7");
        awaiting.setTaskKey("task-demo");
        awaiting.setStatus("awaiting_rerun");
        awaiting.setLatestReportId(26L);
        awaiting.setTaskJson("{\"taskId\":\"task-demo\",\"scoreImpact\":{\"ruleHash\":\"rule-1\"}}");
        AiScoreTaskLossLink previousLoss = new AiScoreTaskLossLink();
        previousLoss.setTaskId(91L);
        previousLoss.setReportId(26L);
        previousLoss.setLossKey("rule-1:O01:performance");
        previousLoss.setGapPoints(new BigDecimal("4.0"));
        when(taskMapper.selectList(any())).thenReturn(List.of(awaiting));
        when(linkMapper.selectList(any())).thenReturn(List.of(previousLoss));
        when(verificationMapper.selectOne(any())).thenReturn(null);
        AiScoreRemediationService service = new AiScoreRemediationService(taskMapper, linkMapper, verificationMapper);

        service.persistSnapshot(
                "project:7",
                30L,
                90L,
                "[]",
                "[]",
                "{\"ruleHash\":\"rule-1\",\"status\":\"complete\"}"
        );

        ArgumentCaptor<AiScoreTaskVerification> verification = ArgumentCaptor.forClass(AiScoreTaskVerification.class);
        verify(verificationMapper).insert(verification.capture());
        assertEquals("verified", verification.getValue().getStatus());
        assertEquals(Boolean.TRUE, verification.getValue().getRuleComparable());
        assertEquals(Boolean.TRUE, verification.getValue().getFullScorePassed());
        assertEquals("verified", awaiting.getStatus());
        assertEquals(30L, awaiting.getLatestReportId());
        verify(taskMapper).updateById(awaiting);
    }
}
