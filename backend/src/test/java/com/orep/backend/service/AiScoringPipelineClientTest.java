package com.orep.backend.service;

import com.orep.backend.dto.PipelineStartResponse;
import org.junit.jupiter.api.Test;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestTemplate;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.content;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withServerError;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

class AiScoringPipelineClientTest {

    @Test
    void startSessionPipelineSendsCorrectPayloadAndParsesResponse() {
        RestTemplate restTemplate = new RestTemplate();
        MockRestServiceServer server = MockRestServiceServer.bindTo(restTemplate).build();

        server.expect(requestTo("http://127.0.0.1:8090/api/ai/score-session"))
                .andExpect(method(HttpMethod.POST))
                .andExpect(content().json("""
                        {
                          "trackId": "track-it",
                           "trackName": "新一代信息技术赛道",
                           "publishOfficialScore": false,
                           "juryEnabled": true,
                          "competitionBinding": {
                            "trackId": "track-it",
                            "trackName": "新一代信息技术赛道",
                            "ruleVersion": "v1.2",
                            "ruleHash": "sha256:test",
                            "selectionSource": "diagnostic_override"
                          },
                          "forceRetranscribe": false
                        }
                        """, false))
                .andRespond(withSuccess("""
                        {"accepted": true, "message": "Pipeline started", "taskId": "task-123"}
                        """, MediaType.APPLICATION_JSON));

        AiScoringPipelineClient client = new AiScoringPipelineClient(restTemplate);

        PipelineStartResponse response = client.startSessionPipeline(
                101L, "SC-20260624-000101", 9L, 3L,
                 "track-it", "新一代信息技术赛道", "v1.2", "sha256:test",
                 "uploaded_video", "/uploads/ai-score/101/abc-video.mp4", "roadshow.mp4",
                 List.of(Map.of("path", "/uploads/ai-score/101/mat.pdf", "name", "bp.pdf")),
                 true,
                 "http://localhost:8080/api/ai-score/sessions/101/pipeline-callback"
         );

        assertThat(response.isAccepted()).isTrue();
        assertThat(response.getTaskId()).isEqualTo("task-123");
        server.verify();
    }

    @Test
    void startSessionPipelineSendsVideoHashAndForceRetranscribe() {
        RestTemplate restTemplate = new RestTemplate();
        MockRestServiceServer server = MockRestServiceServer.bindTo(restTemplate).build();

        server.expect(requestTo("http://127.0.0.1:8090/api/ai/score-session"))
                .andExpect(method(HttpMethod.POST))
                .andExpect(content().json("""
                        {
                          "videoSha256": "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                          "forceRetranscribe": true
                        }
                        """, false))
                .andRespond(withSuccess("""
                        {"accepted": true, "message": "Pipeline started", "taskId": "task-hash"}
                        """, MediaType.APPLICATION_JSON));

        AiScoringPipelineClient client = new AiScoringPipelineClient(restTemplate);
        PipelineStartResponse response = client.startSessionPipeline(
                101L, "SC-20260624-000101", 9L, 3L,
                "track-it", "新一代信息技术赛道", "v1.2", "sha256:test",
                "uploaded_video", "/uploads/ai-score/101/abc-video.mp4", "roadshow.mp4",
                List.of(), true,
                "BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB",
                true,
                "http://localhost:8080/api/ai-score/sessions/101/pipeline-callback"
        );

        assertThat(response.isAccepted()).isTrue();
        server.verify();
    }

    @Test
    void startSessionPipelineHandlesServerErrorGracefully() {
        RestTemplate restTemplate = new RestTemplate();
        MockRestServiceServer server = MockRestServiceServer.bindTo(restTemplate).build();

        server.expect(requestTo("http://127.0.0.1:8090/api/ai/score-session"))
                .andRespond(withServerError());

        AiScoringPipelineClient client = new AiScoringPipelineClient(restTemplate);

        PipelineStartResponse response = client.startSessionPipeline(
                101L, "SC-20260624-000101", 9L, 3L,
                "track-it", "新一代信息技术赛道", "v1.2", "sha256:test",
                 "uploaded_video", "/uploads/ai-score/101/abc-video.mp4", "roadshow.mp4",
                 List.of(), false, "http://localhost:8080/api/ai-score/sessions/101/pipeline-callback"
         );

        assertThat(response.isAccepted()).isFalse();
        assertThat(response.getMessage()).contains("AI 服务调用失败");
        server.verify();
    }
}
