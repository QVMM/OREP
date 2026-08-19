package com.orep.backend.service;

import com.orep.backend.dto.ProjectPreparationAiResponse;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestTemplate;

import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withServerError;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

class ProjectPreparationAiClientTest {

    @Test
    void analyzeCallsPrepTopicPlanningEndpointAndParsesDirections() {
        RestTemplate restTemplate = new RestTemplate();
        MockRestServiceServer server = MockRestServiceServer.bindTo(restTemplate).build();
        server.expect(requestTo("http://127.0.0.1:8090/api/prep/topic-planning/analyze"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withSuccess("""
                        {
                          "accepted": true,
                          "message": "ok",
                          "assistantMessage": "基于真实材料生成了2个方向。",
                          "model": "mimo-web",
                          "agentSteps": [
                            {
                              "agentKey": "topic_planner",
                              "agentName": "赵选题",
                              "agentRole": "选题总策划",
                              "status": "COMPLETED",
                              "inputSummary": "用户补充温室场景。",
                              "outputSummary": "建议收窄到温室诊断。",
                              "findings": ["边界清晰"],
                              "questions": ["是否有数据？"],
                              "sources": [{"title": "用户补充", "sourceType": "USER_INPUT"}]
                            }
                          ],
                          "directions": [
                            {
                              "title": "温室能耗诊断",
                              "summary": "利用已有传感器数据做能耗异常识别。",
                              "tags": ["农业", "节能"],
                              "equipmentMatch": "HIGH",
                              "competitionMatch": "MEDIUM",
                              "recommendationLevel": "RECOMMENDED",
                              "expertRationale": "专家团建议优先推进。",
                              "scores": {"competitionFit": 8, "resourceFit": 7, "innovation": 6, "demoReadiness": 8, "riskControl": 6},
                              "evidenceGaps": ["补充历史能耗数据"],
                              "risks": ["样本周期不足"],
                              "nextTasks": [{"title": "整理传感器字段"}],
                              "researchRefs": [{"title": "公开趋势", "url": "https://example.com"}]
                            }
                          ]
                        }
                        """, MediaType.APPLICATION_JSON));

        ProjectPreparationAiClient client = new ProjectPreparationAiClient(restTemplate);
        ProjectPreparationAiResponse response = client.analyze(Map.of("teamId", 9L));

        assertThat(response.isAccepted()).isTrue();
        assertThat(response.getAssistantMessage()).contains("真实材料");
        assertThat(response.getAgentSteps()).hasSize(1);
        assertThat(response.getAgentSteps().get(0).getAgentName()).isEqualTo("赵选题");
        assertThat(response.getDirections()).hasSize(1);
        assertThat(response.getDirections().get(0).getRecommendationLevel()).isEqualTo("RECOMMENDED");
        assertThat(response.getDirections().get(0).getScores().getCompetitionFit()).isEqualTo(8);
        assertThat(response.getDirections().get(0).getNextTasks()).hasSize(1);
        server.verify();
    }

    @Test
    void analyzeConvertsExplicitNullListsToEmptyLists() {
        RestTemplate restTemplate = new RestTemplate();
        MockRestServiceServer server = MockRestServiceServer.bindTo(restTemplate).build();
        server.expect(requestTo("http://127.0.0.1:8090/api/prep/topic-planning/analyze"))
                .andExpect(method(HttpMethod.POST))
                .andRespond(withSuccess("""
                        {
                          "accepted": true,
                          "agentSteps": [
                            {
                              "agentName": "赵选题",
                              "findings": null,
                              "questions": null,
                              "sources": null
                            }
                          ],
                          "questions": null,
                          "directions": [
                            {
                              "title": "温室能耗诊断",
                              "tags": null,
                              "evidenceGaps": null,
                              "risks": null,
                              "nextTasks": null,
                              "researchRefs": null
                            }
                          ],
                          "sources": null,
                          "nextActions": null
                        }
                        """, MediaType.APPLICATION_JSON));

        ProjectPreparationAiClient client = new ProjectPreparationAiClient(restTemplate);
        ProjectPreparationAiResponse response = client.analyze(Map.of("teamId", 9L));

        assertThat(response.getAgentSteps()).hasSize(1);
        assertThat(response.getQuestions()).isEmpty();
        assertThat(response.getDirections()).hasSize(1);
        assertThat(response.getSources()).isEmpty();
        assertThat(response.getNextActions()).isEmpty();

        ProjectPreparationAiResponse.AgentStep agentStep = response.getAgentSteps().get(0);
        assertThat(agentStep.getFindings()).isEmpty();
        assertThat(agentStep.getQuestions()).isEmpty();
        assertThat(agentStep.getSources()).isEmpty();

        ProjectPreparationAiResponse.Direction direction = response.getDirections().get(0);
        assertThat(direction.getTags()).isEmpty();
        assertThat(direction.getEvidenceGaps()).isEmpty();
        assertThat(direction.getRisks()).isEmpty();
        assertThat(direction.getNextTasks()).isEmpty();
        assertThat(direction.getResearchRefs()).isEmpty();
        server.verify();
    }

    @Test
    void analyzeHandlesServerErrorGracefully() {
        RestTemplate restTemplate = new RestTemplate();
        MockRestServiceServer server = MockRestServiceServer.bindTo(restTemplate).build();
        server.expect(requestTo("http://127.0.0.1:8090/api/prep/topic-planning/analyze"))
                .andRespond(withServerError());

        ProjectPreparationAiClient client = new ProjectPreparationAiClient(restTemplate);
        ProjectPreparationAiResponse response = client.analyze(Map.of("teamId", 9L));

        assertThat(response.isAccepted()).isFalse();
        assertThat(response.getMessage()).contains("AI 服务调用失败");
        server.verify();
    }

    @Test
    void analyzeHandlesUnexpectedParseFailureGracefully() {
        RestTemplate restTemplate = mock(RestTemplate.class);
        when(restTemplate.postForObject(anyString(), any(), eq(ProjectPreparationAiResponse.class)))
                .thenThrow(new IllegalStateException("bad response contract"));

        ProjectPreparationAiClient client = new ProjectPreparationAiClient(restTemplate);
        ProjectPreparationAiResponse response = client.analyze(Map.of("teamId", 9L));

        assertThat(response.isAccepted()).isFalse();
        assertThat(response.getMessage()).startsWith("AI 服务响应解析失败:");
    }
}
