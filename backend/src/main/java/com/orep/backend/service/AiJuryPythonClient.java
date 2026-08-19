package com.orep.backend.service;

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

import java.util.LinkedHashMap;
import java.util.Map;

@Service
public class AiJuryPythonClient {
    private static final Logger log = LoggerFactory.getLogger(AiJuryPythonClient.class);

    private final RestTemplate restTemplate;
    private final String baseUrl;

    @Autowired
    public AiJuryPythonClient(
            @Value("${ai-scoring.base-url:http://127.0.0.1:8090}") String baseUrl,
            @Value("${ai-scoring.connect-timeout-ms:5000}") int connectTimeoutMs,
            @Value("${ai-scoring.read-timeout-ms:30000}") int readTimeoutMs) {
        SimpleClientHttpRequestFactory requestFactory = new SimpleClientHttpRequestFactory();
        requestFactory.setConnectTimeout(connectTimeoutMs);
        requestFactory.setReadTimeout(readTimeoutMs);
        this.restTemplate = new RestTemplate(requestFactory);
        this.baseUrl = baseUrl;
    }

    public AiJuryPythonClient(RestTemplate restTemplate) {
        this.restTemplate = restTemplate;
        this.baseUrl = "http://127.0.0.1:8090";
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> startJuryReview(Long resultKey) {
        return startJuryReview(resultKey, Map.of());
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> startJuryReview(Long resultKey, Map<String, Object> disputeReviewContext) {
        if (resultKey == null) {
            return empty("当前评分会话暂未关联可用于评审团复核的会议结果");
        }
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        Map<String, Object> body = new LinkedHashMap<>();
        if (disputeReviewContext != null && !disputeReviewContext.isEmpty()) {
            body.put("dispute_review_context", disputeReviewContext);
        }
        HttpEntity<Map<String, Object>> entity = new HttpEntity<>(body, headers);
        try {
            Map<String, Object> response = restTemplate.postForObject(
                    baseUrl + "/api/ai/jury/" + resultKey + "/start",
                    entity,
                    Map.class
            );
            return response == null ? empty("Python评审团服务返回空响应") : response;
        } catch (RestClientException e) {
            log.error("Failed to start Python jury review for result key {}: {}", resultKey, e.getMessage());
            return failed("Python评审团服务调用失败: " + e.getMessage());
        }
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> getJuryResult(Long resultKey) {
        if (resultKey == null) {
            return empty("当前评分会话暂未关联可用于评审团复核的会议结果");
        }
        try {
            Map<String, Object> response = restTemplate.getForObject(
                    baseUrl + "/api/ai/jury/" + resultKey + "/result",
                    Map.class
            );
            return response == null ? empty("Python评审团服务返回空响应") : response;
        } catch (RestClientException e) {
            log.error("Failed to fetch Python jury review for result key {}: {}", resultKey, e.getMessage());
            return failed("Python评审团服务调用失败: " + e.getMessage());
        }
    }

    private Map<String, Object> empty(String message) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("status", "empty");
        payload.put("message", message);
        return payload;
    }

    private Map<String, Object> failed(String message) {
        Map<String, Object> payload = new LinkedHashMap<>();
        payload.put("status", "failed");
        payload.put("message", message);
        return payload;
    }
}
