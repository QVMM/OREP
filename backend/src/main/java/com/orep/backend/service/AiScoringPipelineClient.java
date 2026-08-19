package com.orep.backend.service;

import com.orep.backend.dto.PipelineStartResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpMethod;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

@Service
public class AiScoringPipelineClient {

    private static final Logger log = LoggerFactory.getLogger(AiScoringPipelineClient.class);

    private final RestTemplate restTemplate;
    private final RestTemplate recomputeRestTemplate;
    private final String baseUrl;

    @Autowired
    public AiScoringPipelineClient(
            @Value("${ai-scoring.base-url:http://127.0.0.1:8090}") String baseUrl,
            @Value("${ai-scoring.connect-timeout-ms:5000}") int connectTimeoutMs,
            @Value("${ai-scoring.read-timeout-ms:15000}") int readTimeoutMs,
            @Value("${ai-scoring.recompute-read-timeout-ms:60000}") int recomputeReadTimeoutMs) {
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(connectTimeoutMs);
        requestFactory.setReadTimeout(readTimeoutMs);
        this.restTemplate = new RestTemplate(requestFactory);
        SimpleClientHttpRequestFactory recomputeFactory = new SimpleClientHttpRequestFactory();
        recomputeFactory.setConnectTimeout(connectTimeoutMs);
        recomputeFactory.setReadTimeout(recomputeReadTimeoutMs);
        this.recomputeRestTemplate = new RestTemplate(recomputeFactory);
        this.baseUrl = baseUrl;
    }

    // Constructor for testing with custom RestTemplate
    public AiScoringPipelineClient(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
        this.recomputeRestTemplate = restTemplate;
        this.baseUrl = "http://127.0.0.1:8090";
    }

    public PipelineStartResponse startSessionPipeline(
            Long sessionId,
            String sessionNo,
            Long teamId,
            Long projectId,
            String trackName,
            String sourceType,
            String videoFilePath,
            String videoOriginalName,
            List<Map<String, String>> materials,
            String callbackUrl) {
        return startSessionPipeline(sessionId, sessionNo, teamId, projectId, trackName, sourceType,
                videoFilePath, videoOriginalName, materials, false, callbackUrl);
    }

    public PipelineStartResponse startSessionPipeline(
            Long sessionId,
            String sessionNo,
            Long teamId,
            Long projectId,
            String trackName,
            String sourceType,
             String videoFilePath,
             String videoOriginalName,
             List<Map<String, String>> materials,
             boolean juryEnabled,
             String callbackUrl) {
        return startSessionPipeline(
                sessionId,
                sessionNo,
                teamId,
                projectId,
                null,
                trackName,
                null,
                null,
                sourceType,
                videoFilePath,
                 videoOriginalName,
                 materials,
                 juryEnabled,
                 null,
                 false,
                 callbackUrl
         );
    }

    public PipelineStartResponse startSessionPipeline(
            Long sessionId,
            String sessionNo,
            Long teamId,
            Long projectId,
            String trackId,
            String trackName,
            String ruleVersion,
            String ruleHash,
            String sourceType,
            String videoFilePath,
            String videoOriginalName,
            List<Map<String, String>> materials,
            String callbackUrl) {
        return startSessionPipeline(sessionId, sessionNo, teamId, projectId, trackId, trackName,
                ruleVersion, ruleHash, sourceType, videoFilePath, videoOriginalName, materials, false,
                null, false, callbackUrl);
    }

    public PipelineStartResponse startSessionPipeline(
            Long sessionId,
            String sessionNo,
            Long teamId,
            Long projectId,
            String trackId,
            String trackName,
            String ruleVersion,
            String ruleHash,
            String sourceType,
             String videoFilePath,
             String videoOriginalName,
             List<Map<String, String>> materials,
             boolean juryEnabled,
             String callbackUrl) {
        return startSessionPipeline(
                sessionId, sessionNo, teamId, projectId, trackId, trackName,
                ruleVersion, ruleHash, sourceType, videoFilePath, videoOriginalName,
                materials, juryEnabled, null, false, callbackUrl
        );
    }

    public PipelineStartResponse startSessionPipeline(
            Long sessionId,
            String sessionNo,
            Long teamId,
            Long projectId,
            String trackId,
            String trackName,
            String ruleVersion,
            String ruleHash,
            String sourceType,
            String videoFilePath,
            String videoOriginalName,
            List<Map<String, String>> materials,
            boolean juryEnabled,
            String videoSha256,
            boolean forceRetranscribe,
            String callbackUrl) {

        if (isBlank(trackId) || isBlank(trackName) || isBlank(ruleVersion) || isBlank(ruleHash)) {
            PipelineStartResponse rejected = new PipelineStartResponse();
            rejected.setAccepted(false);
            rejected.setMessage("track_confirmation_required");
            return rejected;
        }

        Map<String, Object> body = new HashMap<>();
        body.put("sessionId", sessionId);
        body.put("sessionNo", sessionNo);
        body.put("teamId", teamId);
        body.put("projectId", projectId);
        body.put("trackId", trackId);
        body.put("trackName", trackName);
        body.put("competitionBinding", Map.of(
                "trackId", trackId,
                "trackName", trackName,
                "ruleVersion", ruleVersion,
                "ruleHash", ruleHash,
                "selectionSource", "diagnostic_override"
        ));
         body.put("publishOfficialScore", false);
         body.put("juryEnabled", juryEnabled);
        body.put("sourceType", sourceType);
        body.put("videoFilePath", videoFilePath);
        body.put("videoOriginalName", videoOriginalName);
        body.put("materials", materials != null ? materials : List.of());
        body.put("callbackUrl", callbackUrl);
        if (videoSha256 != null && !videoSha256.isBlank()) {
            body.put("videoSha256", videoSha256.trim().toLowerCase());
        }
        body.put("forceRetranscribe", forceRetranscribe);

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);

        try {
            PipelineStartResponse response = restTemplate.postForObject(
                    baseUrl + "/api/ai/score-session",
                    entity,
                    PipelineStartResponse.class
            );
            if (response == null) {
                PipelineStartResponse fallback = new PipelineStartResponse();
                fallback.setAccepted(false);
                fallback.setMessage("AI 服务返回空响应");
                return fallback;
            }
            return response;
        } catch (RestClientException e) {
            log.error("Failed to call ai-scoring service at {}: {}", baseUrl, e.getMessage());
            PipelineStartResponse error = new PipelineStartResponse();
            error.setAccepted(false);
            error.setMessage("AI 服务调用失败: " + e.getMessage());
            return error;
        }
    }

    /**
     * Ask AI service to rebuild FINAL speaker attribution from stored ASR/cluster
     * artifacts (no full rescoring). Returns the raw AI payload including
     * {@code speakerAttribution} snapshot.
     */
    @SuppressWarnings("unchecked")
    public Map<String, Object> recomputeSpeakerAttribution(Long sessionId, Integer contestantSlots) {
        if (sessionId == null || sessionId <= 0) {
            throw new IllegalArgumentException("评分会话无效");
        }
        Map<String, Object> body = new HashMap<>();
        if (contestantSlots != null) {
            body.put("contestantSlots", contestantSlots);
        }
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);
        String url = baseUrl + "/api/ai/score-session/" + sessionId + "/recompute-speaker-attribution";
        try {
            ResponseEntity<Map<String, Object>> response = recomputeRestTemplate.exchange(
                    url,
                    HttpMethod.POST,
                    entity,
                    new ParameterizedTypeReference<Map<String, Object>>() {}
            );
            Map<String, Object> payload = response.getBody();
            if (payload == null) {
                throw new IllegalStateException("AI 服务返回空响应");
            }
            if (!Boolean.TRUE.equals(payload.get("accepted"))) {
                throw new IllegalStateException(String.valueOf(
                        payload.getOrDefault("message", "人物归属重算未被接受")
                ));
            }
            Object snapshot = payload.get("speakerAttribution");
            if (!(snapshot instanceof Map) || ((Map<?, ?>) snapshot).isEmpty()) {
                throw new IllegalStateException("AI 服务未返回人物归属快照");
            }
            return payload;
        } catch (HttpStatusCodeException e) {
            String detail = extractAiErrorMessage(e.getResponseBodyAsString());
            log.warn("recompute speaker attribution rejected session={} status={} body={}",
                    sessionId, e.getStatusCode(), e.getResponseBodyAsString());
            if (e.getStatusCode().value() >= 400 && e.getStatusCode().value() < 500) {
                throw new IllegalArgumentException(
                        detail == null || detail.isBlank() ? "人物归属重算失败" : detail
                );
            }
            throw new IllegalStateException(
                    detail == null || detail.isBlank()
                            ? "AI 服务调用失败: " + e.getStatusCode()
                            : detail
            );
        } catch (RestClientException e) {
            log.error("Failed to recompute speaker attribution at {}: {}", baseUrl, e.getMessage());
            throw new IllegalStateException("AI 服务调用失败: " + e.getMessage());
        }
    }

    private String extractAiErrorMessage(String body) {
        if (body == null || body.isBlank()) {
            return null;
        }
        // FastAPI: {"detail": {"code": "...", "message": "..."}} or {"detail": "..."}
        try {
            // lightweight parse without hard dependency on Jackson tree here
            if (body.contains("\"message\"")) {
                int idx = body.indexOf("\"message\"");
                int colon = body.indexOf(':', idx);
                int start = body.indexOf('"', colon + 1);
                int end = body.indexOf('"', start + 1);
                if (start >= 0 && end > start) {
                    return body.substring(start + 1, end);
                }
            }
            if (body.contains("\"detail\"")) {
                int idx = body.indexOf("\"detail\"");
                int colon = body.indexOf(':', idx);
                int start = body.indexOf('"', colon + 1);
                int end = body.indexOf('"', start + 1);
                if (start >= 0 && end > start) {
                    return body.substring(start + 1, end);
                }
            }
        } catch (Exception ignored) {
            // fall through
        }
        return body.length() > 240 ? body.substring(0, 240) : body;
    }

    private boolean isBlank(String value) {
        return value == null || value.isBlank();
    }
}
