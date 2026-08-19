package com.orep.backend.service;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.orep.backend.dto.AiJuryReviewUserResponse;
import com.orep.backend.dto.AiScoreReportUserResponse;
import com.orep.backend.entity.AiJudgeReport;
import com.orep.backend.entity.AiJuryAggregate;
import com.orep.backend.entity.AiJuryMember;
import com.orep.backend.entity.AiJurySession;
import org.junit.jupiter.api.Test;

import java.math.BigDecimal;
import java.nio.file.Files;
import java.nio.file.Path;
import java.sql.Connection;
import java.sql.DriverManager;
import java.sql.ResultSet;
import java.sql.Statement;
import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyMap;
import static org.mockito.ArgumentMatchers.argThat;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

class AiJuryReviewServiceTest {

    @Test
    void juryEntitiesSupportSessionNativeFields() {
        AiJurySession session = new AiJurySession();
        session.setScoringSessionId(99L);
        session.setMeetingId(null);
        session.setStatus("completed");

        AiJudgeReport report = new AiJudgeReport();
        report.setScoringSessionId(99L);
        report.setMeetingId(null);
        report.setPersonaCode("INTJ");
        report.setOverallScore(new BigDecimal("78.50"));

        AiJuryMember member = new AiJuryMember();
        member.setPersonaCode("INTJ");
        member.setSeatNo(1);

        AiJuryAggregate aggregate = new AiJuryAggregate();
        aggregate.setScoringSessionId(99L);
        aggregate.setMeetingId(null);
        aggregate.setTrimmedAverageScore(new BigDecimal("79.20"));

        assertThat(session.getScoringSessionId()).isEqualTo(99L);
        assertThat(report.getMeetingId()).isNull();
        assertThat(member.getSeatNo()).isEqualTo(1);
        assertThat(aggregate.getTrimmedAverageScore()).isEqualByComparingTo("79.20");
    }

    @Test
    void createJuryTablesSqlExecutesInH2MysqlMode() throws Exception {
        String sql = Files.readString(Path.of("src/main/resources/sql/create_ai_jury_tables.sql"));

        try (Connection connection = DriverManager.getConnection(
                "jdbc:h2:mem:ai_jury_create;MODE=MySQL;DATABASE_TO_UPPER=false;DB_CLOSE_DELAY=-1");
             Statement statement = connection.createStatement()) {
            executeSqlStatements(statement, sql);
        }
    }

    @Test
    void createJuryTablesSqlDoesNotCollideWithExistingProjectIndexes() throws Exception {
        String scoreReportSql = Files.readString(Path.of("src/main/resources/sql/create_ai_score_report_table.sql"));
        String jurySql = Files.readString(Path.of("src/main/resources/sql/create_ai_jury_tables.sql"));

        try (Connection connection = DriverManager.getConnection(
                "jdbc:h2:mem:ai_jury_index_collision;MODE=MySQL;DATABASE_TO_UPPER=false;DB_CLOSE_DELAY=-1");
             Statement statement = connection.createStatement()) {
            executeSqlStatements(statement, scoreReportSql);
            executeSqlStatements(statement, jurySql);
        }
    }

    @Test
    void alterJuryTablesSqlAddsScoringSessionColumnsInH2MysqlMode() throws Exception {
        String sql = Files.readString(Path.of("src/main/resources/sql/alter_ai_jury_tables_p11.sql"));

        try (Connection connection = DriverManager.getConnection(
                "jdbc:h2:mem:ai_jury_alter;MODE=MySQL;DATABASE_TO_UPPER=false;DB_CLOSE_DELAY=-1");
             Statement statement = connection.createStatement()) {
            executeSqlStatements(statement, """
                    CREATE TABLE ai_jury_session (
                      id BIGINT NOT NULL AUTO_INCREMENT,
                      meeting_id BIGINT NOT NULL,
                      status VARCHAR(32) NOT NULL DEFAULT 'processing',
                      PRIMARY KEY (id)
                    );
                    CREATE TABLE ai_judge_report (
                      id BIGINT NOT NULL AUTO_INCREMENT,
                      meeting_id BIGINT NOT NULL,
                      PRIMARY KEY (id)
                    );
                    CREATE TABLE ai_jury_aggregate (
                      id BIGINT NOT NULL AUTO_INCREMENT,
                      meeting_id BIGINT NOT NULL,
                      PRIMARY KEY (id)
                    );
                    """);
            executeSqlStatements(statement, sql);

            assertThat(hasColumn(connection, "ai_jury_session", "scoring_session_id")).isTrue();
            assertThat(hasColumn(connection, "ai_judge_report", "scoring_session_id")).isTrue();
            assertThat(hasColumn(connection, "ai_jury_aggregate", "scoring_session_id")).isTrue();
        }
    }

    private void executeSqlStatements(Statement statement, String sql) throws Exception {
        for (String rawStatement : sql.split(";")) {
            String executableStatement = rawStatement.trim();
            if (!executableStatement.isEmpty()) {
                statement.execute(executableStatement);
            }
        }
    }

    private boolean hasColumn(Connection connection, String tableName, String columnName) throws Exception {
        try (ResultSet resultSet = connection.getMetaData().getColumns(null, null, tableName, columnName)) {
            return resultSet.next();
        }
    }

    @Test
    void startForSessionPersistsJurySessionMembersReportsAndAggregate() {
        com.orep.backend.service.AiScoringSessionService scoring = mock(com.orep.backend.service.AiScoringSessionService.class);
        com.orep.backend.service.AiJudgePersonaService personas = mock(com.orep.backend.service.AiJudgePersonaService.class);
        com.orep.backend.mapper.AiJurySessionMapper sessionMapper = mock(com.orep.backend.mapper.AiJurySessionMapper.class);
        com.orep.backend.mapper.AiJuryMemberMapper memberMapper = mock(com.orep.backend.mapper.AiJuryMemberMapper.class);
        com.orep.backend.mapper.AiJudgeReportMapper reportMapper = mock(com.orep.backend.mapper.AiJudgeReportMapper.class);
        com.orep.backend.mapper.AiJuryAggregateMapper aggregateMapper = mock(com.orep.backend.mapper.AiJuryAggregateMapper.class);
        AiJuryPythonClient pythonClient = mock(AiJuryPythonClient.class);

        AiScoreReportUserResponse base = new AiScoreReportUserResponse();
        base.setSessionId(88L);
        base.setMeetingId(12L);
        base.setReportId(33L);
        base.setOverallScore(new BigDecimal("80.00"));
        base.setTrackName("餐饮赛道");
        when(scoring.reportBySession(88L)).thenReturn(base);
        when(personas.listUserPersonaPayloads()).thenReturn(List.of(Map.of(
                "id", 7L,
                "code", "ISTJ",
                "name", "规范审查评委",
                "short_label", "重规范",
                "focus_dimensions", List.of("职业素养"),
                "persona_view", Map.of("top_concerns", List.of("流程不规范"))
        )));
        when(pythonClient.startJuryReview(eq(12L), anyMap())).thenReturn(Map.of(
                "meeting_id", 12,
                "jury_session_id", "python-session-1",
                "status", "completed",
                "official_score", 80.0,
                "judge_count", 1,
                "jury", Map.of(
                        "trimmed_average_score", 78.5,
                        "score_diff_from_official", -1.5,
                        "successful_count", 1
                ),
                "members", List.of(Map.of(
                        "persona_code", "ISTJ",
                        "role_label", "规范审查评委",
                        "overall_score", 78.5,
                        "critical_issues", List.of("流程证据不足"),
                        "improvement_priorities", List.of("补齐流程佐证")
                )),
                "aggregate", Map.of(
                        "consensus_issues", List.of("流程证据不足"),
                        "dimension_stats", List.of("职业素养"),
                        "next_training_priorities", List.of("补齐流程佐证")
                )
        ));

        AiJuryReviewService service = new AiJuryReviewService(
                scoring, personas, pythonClient, sessionMapper, memberMapper, reportMapper, aggregateMapper, new ObjectMapper()
        );

        AiJuryReviewUserResponse response = service.startForSession(88L);

        assertThat(response.getSessionId()).isEqualTo(88L);
        assertThat(response.getMembers()).hasSize(1);
        verify(pythonClient).startJuryReview(eq(12L), anyMap());
        verify(sessionMapper).insert(argThat(item ->
                Long.valueOf(88L).equals(item.getScoringSessionId())
                        && Long.valueOf(12L).equals(item.getMeetingId())
                        && "python-jury-v1".equals(item.getStandardVersion())
                        && "completed".equals(item.getStatus())
        ));
        verify(memberMapper).insert(argThat(item ->
                Long.valueOf(7L).equals(item.getPersonaId())
                        && "ISTJ".equals(item.getPersonaCode())
                        && Integer.valueOf(1).equals(item.getSeatNo())
        ));
        verify(reportMapper).insert(any(AiJudgeReport.class));
        verify(aggregateMapper).insert(any(AiJuryAggregate.class));
    }

    @Test
    void startForSessionUsesOfficialReportScoreAndRecalculatesStalePythonDifference() {
        AiScoringSessionService scoring = mock(AiScoringSessionService.class);
        AiJuryPythonClient pythonClient = mock(AiJuryPythonClient.class);
        AiScoreReportUserResponse base = new AiScoreReportUserResponse();
        base.setSessionId(34L);
        base.setOverallScore(new BigDecimal("55.20"));
        when(scoring.reportBySession(34L)).thenReturn(base);
        when(pythonClient.startJuryReview(eq(34L), anyMap())).thenReturn(Map.of(
                "status", "completed",
                "official_score", 63.63,
                "jury", Map.of(
                        "trimmed_average_score", 53.06,
                        "score_diff_from_official", -10.57
                ),
                "members", List.of(Map.of(
                        "persona_code", "ESTJ",
                        "overall_score", 53.06,
                        "status", "completed"
                ))
        ));
        AiJuryReviewService service = new AiJuryReviewService(
                scoring, mock(AiJudgePersonaService.class), pythonClient,
                null, null, null, null, new ObjectMapper());

        AiJuryReviewUserResponse response = service.startForSession(34L);

        assertThat(response.getOfficialScore()).isEqualByComparingTo("55.20");
        assertThat(response.getScoreDiffFromOfficial()).isEqualByComparingTo("-2.1");
    }

    @Test
    void uploadedVideoSessionStartsPythonJuryWithSessionIdAndKeepsMeetingNull() {
        com.orep.backend.service.AiScoringSessionService scoring = mock(com.orep.backend.service.AiScoringSessionService.class);
        com.orep.backend.service.AiJudgePersonaService personas = mock(com.orep.backend.service.AiJudgePersonaService.class);
        com.orep.backend.mapper.AiJurySessionMapper sessionMapper = mock(com.orep.backend.mapper.AiJurySessionMapper.class);
        com.orep.backend.mapper.AiJuryMemberMapper memberMapper = mock(com.orep.backend.mapper.AiJuryMemberMapper.class);
        com.orep.backend.mapper.AiJudgeReportMapper reportMapper = mock(com.orep.backend.mapper.AiJudgeReportMapper.class);
        com.orep.backend.mapper.AiJuryAggregateMapper aggregateMapper = mock(com.orep.backend.mapper.AiJuryAggregateMapper.class);
        AiJuryPythonClient pythonClient = mock(AiJuryPythonClient.class);

        AiScoreReportUserResponse base = new AiScoreReportUserResponse();
        base.setSessionId(19L);
        base.setMeetingId(null);
        base.setReportId(30L);
        base.setOverallScore(new BigDecimal("65.50"));
        base.setSourceType("uploaded_video");
        when(scoring.reportBySession(19L)).thenReturn(base);
        when(personas.listUserPersonaPayloads()).thenReturn(List.of(Map.of(
                "id", 9L,
                "code", "ENTJ",
                "name", "商业验证评委"
        )));
        when(pythonClient.startJuryReview(eq(19L), anyMap())).thenReturn(Map.of(
                "meeting_id", 19,
                "jury_session_id", "python-uploaded-session",
                "status", "completed",
                "official_score", 65.5,
                "judge_count", 1,
                "jury", Map.of(
                        "trimmed_average_score", 64.0,
                        "score_diff_from_official", -1.5,
                        "successful_count", 1
                ),
                "members", List.of(Map.of(
                        "persona_code", "ENTJ",
                        "role_label", "商业验证评委",
                        "overall_score", 64.0,
                        "critical_issues", List.of("商业数据证据不足"),
                        "improvement_priorities", List.of("补充ROI与订单证据")
                )),
                "aggregate", Map.of(
                        "consensus_issues", List.of("商业数据证据不足"),
                        "next_training_priorities", List.of("补充ROI与订单证据")
                )
        ));

        AiJuryReviewService service = new AiJuryReviewService(
                scoring, personas, pythonClient, sessionMapper, memberMapper, reportMapper, aggregateMapper, new ObjectMapper()
        );

        AiJuryReviewUserResponse response = service.startForSession(19L);

        assertThat(response.getSessionId()).isEqualTo(19L);
        assertThat(response.getMeetingId()).isNull();
        assertThat(response.getMembers()).hasSize(1);
        verify(pythonClient).startJuryReview(eq(19L), anyMap());
        verify(sessionMapper).insert(argThat(item ->
                Long.valueOf(19L).equals(item.getScoringSessionId())
                        && item.getMeetingId() == null
                        && "python-jury-v1".equals(item.getStandardVersion())
        ));
        verify(reportMapper).insert(argThat(item ->
                Long.valueOf(19L).equals(item.getScoringSessionId())
                        && item.getMeetingId() == null
                        && "ENTJ".equals(item.getPersonaCode())
        ));
        verify(aggregateMapper).insert(argThat(item ->
                Long.valueOf(19L).equals(item.getScoringSessionId())
                        && item.getMeetingId() == null
        ));
    }

    @Test
    void startForSessionDoesNotPersistWhenPythonHasNoRealResult() {
        com.orep.backend.service.AiScoringSessionService scoring = mock(com.orep.backend.service.AiScoringSessionService.class);
        com.orep.backend.mapper.AiJurySessionMapper sessionMapper = mock(com.orep.backend.mapper.AiJurySessionMapper.class);
        com.orep.backend.mapper.AiJuryMemberMapper memberMapper = mock(com.orep.backend.mapper.AiJuryMemberMapper.class);
        com.orep.backend.mapper.AiJudgeReportMapper reportMapper = mock(com.orep.backend.mapper.AiJudgeReportMapper.class);
        com.orep.backend.mapper.AiJuryAggregateMapper aggregateMapper = mock(com.orep.backend.mapper.AiJuryAggregateMapper.class);
        AiJuryPythonClient pythonClient = mock(AiJuryPythonClient.class);

        AiScoreReportUserResponse base = new AiScoreReportUserResponse();
        base.setSessionId(88L);
        base.setMeetingId(12L);
        base.setOverallScore(new BigDecimal("80.00"));
        when(scoring.reportBySession(88L)).thenReturn(base);
        when(pythonClient.startJuryReview(eq(12L), anyMap())).thenReturn(Map.of(
                "status", "empty",
                "message", "该会议暂未生成AI评审团复盘"
        ));

        AiJuryReviewService service = new AiJuryReviewService(
                scoring, null, pythonClient, sessionMapper, memberMapper, reportMapper, aggregateMapper, new ObjectMapper()
        );

        AiJuryReviewUserResponse response = service.startForSession(88L);

        assertThat(response.getStatus()).isEqualTo("empty");
        assertThat(response.getMembers()).isEmpty();
        verify(sessionMapper, never()).insert(any(AiJurySession.class));
        verify(memberMapper, never()).insert(any(AiJuryMember.class));
        verify(reportMapper, never()).insert(any(AiJudgeReport.class));
        verify(aggregateMapper, never()).insert(any(AiJuryAggregate.class));
    }

    @Test
    void startForSessionKeepsProcessingStatusWhilePythonJuryIsRunning() {
        com.orep.backend.service.AiScoringSessionService scoring = mock(com.orep.backend.service.AiScoringSessionService.class);
        com.orep.backend.mapper.AiJurySessionMapper sessionMapper = mock(com.orep.backend.mapper.AiJurySessionMapper.class);
        AiJuryPythonClient pythonClient = mock(AiJuryPythonClient.class);

        AiScoreReportUserResponse base = new AiScoreReportUserResponse();
        base.setSessionId(19L);
        base.setMeetingId(null);
        base.setOverallScore(new BigDecimal("65.50"));
        when(scoring.reportBySession(19L)).thenReturn(base);
        when(pythonClient.startJuryReview(eq(19L), anyMap())).thenReturn(Map.of(
                "status", "processing",
                "meeting_id", 19,
                "judge_count", 9,
                "members", List.of(Map.of(
                        "persona_code", "INTP",
                        "status", "pending"
                ))
        ));

        AiJuryReviewService service = new AiJuryReviewService(
                scoring, null, pythonClient, sessionMapper, null, null, null, new ObjectMapper()
        );

        AiJuryReviewUserResponse response = service.startForSession(19L);

        assertThat(response.getSessionId()).isEqualTo(19L);
        assertThat(response.getMeetingId()).isNull();
        assertThat(response.getStatus()).isEqualTo("processing");
        assertThat(response.getJudgeCount()).isEqualTo(9);
        assertThat(response.getMembers()).isEmpty();
        verify(sessionMapper, never()).insert(any(AiJurySession.class));
    }

    @Test
    void startForSessionSendsRuleEngineDisputeContextToPythonReviewLayer() {
        com.orep.backend.service.AiScoringSessionService scoring = mock(com.orep.backend.service.AiScoringSessionService.class);
        AiJuryPythonClient pythonClient = mock(AiJuryPythonClient.class);

        AiScoreReportUserResponse base = new AiScoreReportUserResponse();
        base.setSessionId(101L);
        base.setMeetingId(null);
        base.setReportId(202L);
        base.setOverallScore(new BigDecimal("72.00"));
        base.setTrackName("AI赛道");

        AiScoreReportUserResponse.RuleEngineShadow shadow = new AiScoreReportUserResponse.RuleEngineShadow();
        shadow.setLlmRawScore(new BigDecimal("89.00"));
        shadow.setRuleEngineScore(new BigDecimal("72.00"));
        shadow.setScoreDiff(new BigDecimal("-17.00"));
        shadow.setDiffReasons(List.of("规则引擎分与旧 LLM 分差异超过10分"));
        base.setRuleEngineShadow(shadow);

        AiScoreReportUserResponse.StructuredObservation observation = new AiScoreReportUserResponse.StructuredObservation();
        observation.setDimensionName("商业验证");
        observation.setEvidenceLevel("E5");
        observation.setRawScore(new BigDecimal("18.00"));
        observation.setScoreCap(new BigDecimal("12.00"));
        observation.setConfidence(new BigDecimal("0.42"));
        observation.setEvidenceAnchorIds(List.of(7L));
        base.setStructuredObservations(List.of(observation));

        AiScoreReportUserResponse.StructuredDeduction deduction = new AiScoreReportUserResponse.StructuredDeduction();
        deduction.setDimensionName("商业验证");
        deduction.setReason("客户访谈证据不足");
        deduction.setDeductedPoints(new BigDecimal("4.00"));
        deduction.setConfidence(new BigDecimal("0.50"));
        deduction.setEvidenceLevel("E2");
        deduction.setEvidenceAnchorIds(List.of(7L));
        deduction.setStatus("active");
        base.setStructuredDeductions(List.of(deduction));

        when(scoring.reportBySession(101L)).thenReturn(base);
        when(pythonClient.startJuryReview(eq(101L), anyMap())).thenReturn(Map.of(
                "status", "processing",
                "judge_count", 9
        ));

        AiJuryReviewService service = new AiJuryReviewService(
                scoring, null, pythonClient, null, null, null, null, new ObjectMapper()
        );

        AiJuryReviewUserResponse response = service.startForSession(101L);

        assertThat(response.getStatus()).isEqualTo("processing");
        assertThat(response.getDisputeReviewContext()).isNotNull();
        assertThat(response.getDisputeReviewContext().getMode()).isEqualTo("dispute_review");
        assertThat(response.getDisputeReviewContext().getRuleEngineScore()).isEqualByComparingTo("72.00");
        assertThat(response.getDisputeReviewContext().getLlmRawScore()).isEqualByComparingTo("89.00");
        assertThat(response.getDisputeReviewContext().getReviewTriggers())
                .contains("规则引擎分与旧 LLM 分差异超过10分")
                .contains("E4/E5 高证据等级存在锚点不足风险")
                .contains("关键证据来自低置信度识别结果")
                .contains("存在当前扣分项需要复核轻重");
        assertThat(response.getDisputeReviewContext().getDisputedObservations()).hasSize(1);
        assertThat(response.getDisputeReviewContext().getDisputedObservations().get(0).getReasons())
                .contains("E5 证据等级的证据锚点少于要求")
                .contains("观测点证据来自低置信度识别结果")
                .contains("高分被规则引擎封顶，需要复核封顶原因");
        assertThat(response.getDisputeReviewContext().getDeductionReviewItems()).hasSize(1);
        verify(pythonClient).startJuryReview(eq(101L), argThat(payload ->
                "dispute_review".equals(payload.get("mode"))
                        && new BigDecimal("72.00").compareTo(new BigDecimal(String.valueOf(payload.get("ruleEngineScore")))) == 0
                        && ((List<?>) payload.get("reviewTriggers")).contains("规则引擎分与旧 LLM 分差异超过10分")
        ));
    }

    @Test
    void resultBySessionReturnsEmptyWhenNoPersistedReviewExists() {
        com.orep.backend.mapper.AiJurySessionMapper sessionMapper = mock(com.orep.backend.mapper.AiJurySessionMapper.class);
        when(sessionMapper.selectOne(any())).thenReturn(null);

        AiJuryReviewService service = new AiJuryReviewService(
                null, null, sessionMapper, null, null, null, new ObjectMapper()
        );

        AiJuryReviewUserResponse response = service.resultBySession(88L);

        assertThat(response.getSessionId()).isEqualTo(88L);
        assertThat(response.getStatus()).isEqualTo("empty");
        assertThat(response.getMembers()).isEmpty();
        assertThat(response.getAggregate().getConsensusIssues()).isEmpty();
    }

    @Test
    void resultBySessionTreatsLegacySafeReviewAsEmptySoTemplateDataIsNotShown() {
        com.orep.backend.mapper.AiJurySessionMapper sessionMapper = mock(com.orep.backend.mapper.AiJurySessionMapper.class);
        AiJurySession legacy = new AiJurySession();
        legacy.setId(501L);
        legacy.setScoringSessionId(88L);
        legacy.setStandardVersion("safe-review");
        legacy.setStatus("completed");
        legacy.setOfficialScore(new BigDecimal("80.00"));
        legacy.setJuryTrimmedAvg(new BigDecimal("80.00"));
        legacy.setScoreDiffFromOfficial(BigDecimal.ZERO);
        legacy.setJudgeCount(16);
        when(sessionMapper.selectOne(any())).thenReturn(legacy);

        AiJuryReviewService service = new AiJuryReviewService(
                null, null, sessionMapper, null, null, null, new ObjectMapper()
        );

        AiJuryReviewUserResponse response = service.resultBySession(88L);

        assertThat(response.getStatus()).isEqualTo("empty");
        assertThat(response.getMembers()).isEmpty();
        assertThat(response.getExplanation()).contains("暂未生成");
    }

    @Test
    void resultBySessionReadsPersistedRowsWithoutInternalFields() throws Exception {
        com.orep.backend.mapper.AiJurySessionMapper sessionMapper = mock(com.orep.backend.mapper.AiJurySessionMapper.class);
        com.orep.backend.mapper.AiJudgeReportMapper reportMapper = mock(com.orep.backend.mapper.AiJudgeReportMapper.class);
        com.orep.backend.mapper.AiJuryAggregateMapper aggregateMapper = mock(com.orep.backend.mapper.AiJuryAggregateMapper.class);
        ObjectMapper objectMapper = new ObjectMapper();

        AiJurySession savedSession = new AiJurySession();
        savedSession.setId(501L);
        savedSession.setScoringSessionId(88L);
        savedSession.setMeetingId(null);
        savedSession.setStandardVersion("python-jury-v1");
        savedSession.setStatus("completed");
        savedSession.setOfficialScore(new BigDecimal("80.00"));
        savedSession.setJuryTrimmedAvg(new BigDecimal("80.00"));
        savedSession.setScoreDiffFromOfficial(BigDecimal.ZERO);
        savedSession.setJudgeCount(2);
        when(sessionMapper.selectOne(any())).thenReturn(savedSession);

        AiJuryReviewUserResponse.MemberReview storedMember = new AiJuryReviewUserResponse.MemberReview();
        storedMember.setPersonaCode("ENTJ");
        storedMember.setDisplayName("商业闭环评委");
        storedMember.setRoleLabel("重商业验证");
        storedMember.setPerspectiveQuestions(List.of("客户证据是否可验真？"));
        storedMember.setExpressionRisks(List.of("不要只讲愿景。"));
        storedMember.setTrainingSuggestions(List.of("补充真实订单与复购证据。"));
        storedMember.setEvidenceConcerns(List.of("需要客户来源记录。"));
        storedMember.setStatus("completed");
        AiJudgeReport report = new AiJudgeReport();
        report.setPersonaCode("ENTJ");
        report.setOverallScore(new BigDecimal("80.00"));
        report.setStatus("completed");
        report.setReportJson(objectMapper.writeValueAsString(storedMember));
        AiJuryReviewUserResponse.MemberReview failedMember = new AiJuryReviewUserResponse.MemberReview();
        failedMember.setPersonaCode("INFJ");
        failedMember.setDisplayName("证据审查评委");
        failedMember.setStatus("failed");
        AiJudgeReport failedReport = new AiJudgeReport();
        failedReport.setPersonaCode("INFJ");
        failedReport.setStatus("failed");
        failedReport.setReportJson(objectMapper.writeValueAsString(failedMember));
        when(reportMapper.selectList(any())).thenReturn(List.of(report, failedReport));

        AiJuryAggregate aggregate = new AiJuryAggregate();
        aggregate.setConsensusIssuesJson(objectMapper.writeValueAsString(List.of("客户验证不足")));
        aggregate.setDimensionDisagreementJson(objectMapper.writeValueAsString(List.of("商业模式证据争议")));
        aggregate.setOptimizationSuggestionsJson(objectMapper.writeValueAsString(List.of("下一轮补充客户访谈与订单截图")));
        when(aggregateMapper.selectOne(any())).thenReturn(aggregate);

        AiJuryReviewService service = new AiJuryReviewService(
                null, null, sessionMapper, null, reportMapper, aggregateMapper, objectMapper
        );

        AiJuryReviewUserResponse response = service.resultBySession(88L);
        String json = objectMapper.writeValueAsString(response);

        assertThat(response.getJurySessionId()).isEqualTo(501L);
        assertThat(response.getSessionId()).isEqualTo(88L);
        assertThat(response.getMembers()).hasSize(2);
        assertThat(response.getSuccessfulCount()).isEqualTo(1);
        assertThat(response.getMembers().get(0).getDisplayName()).isEqualTo("商业闭环评委");
        assertThat(response.getMembers().get(1).getStatus()).isEqualTo("failed");
        assertThat(response.getAggregate().getConsensusIssues()).contains("客户验证不足");
        assertThat(json)
                .doesNotContain("prompt")
                .doesNotContain("rubric_hash")
                .doesNotContain("rubric_path")
                .doesNotContain("internal_version")
                .doesNotContain("weight");
    }
}
