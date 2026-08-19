package com.orep.backend.service;

import com.orep.backend.dto.ProjectPreparationAiResponse;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestClientException;
import org.springframework.web.client.RestTemplate;

import java.util.Map;

@Service
public class ProjectPreparationAiClient {
    private static final Logger log = LoggerFactory.getLogger(ProjectPreparationAiClient.class);

    private final RestTemplate restTemplate;
    private final String baseUrl;

    @Autowired
    public ProjectPreparationAiClient(
            @Value("${ai-scoring.base-url:http://127.0.0.1:8090}") String baseUrl,
            @Value("${ai-scoring.connect-timeout-ms:5000}") int connectTimeoutMs,
            @Value("${ai-scoring.prep-read-timeout-ms:180000}") int readTimeoutMs
    ) {
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(connectTimeoutMs);
        requestFactory.setReadTimeout(readTimeoutMs);
        this.restTemplate = new RestTemplate(requestFactory);
        this.baseUrl = baseUrl;
    }

    public ProjectPreparationAiClient(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
        this.baseUrl = "http://127.0.0.1:8090";
    }

    public ProjectPreparationAiResponse analyze(Map<String, Object> body) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);
        try {
            ProjectPreparationAiResponse response = restTemplate.postForObject(
                    baseUrl + "/api/prep/topic-planning/analyze",
                    entity,
                    ProjectPreparationAiResponse.class
            );
            if (response == null) {
                ProjectPreparationAiResponse fallback = new ProjectPreparationAiResponse();
                fallback.setAccepted(false);
                fallback.setMessage("AI 服务返回空响应");
                return fallback;
            }
            return response;
        } catch (RestClientException e) {
            log.error("Failed to call prep AI service at {}: {}", baseUrl, e.getMessage());
            ProjectPreparationAiResponse error = new ProjectPreparationAiResponse();
            error.setAccepted(false);
            error.setMessage("AI 服务调用失败: " + e.getMessage());
            return error;
        } catch (Exception e) {
            log.error("Failed to parse prep AI service response at {}: {}", baseUrl, e.getMessage());
            ProjectPreparationAiResponse error = new ProjectPreparationAiResponse();
            error.setAccepted(false);
            error.setMessage("AI 服务响应解析失败: " + e.getMessage());
            return error;
        }
    }
}
