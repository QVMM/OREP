package com.orep.backend.service;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.*;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import java.util.*;

@Service
public class LiveKitEgressService {

    private final LiveKitService liveKitService;
    private final RestTemplate restTemplate;

    @Value("${livekit.egress.api-url:http://127.0.0.1:7880}")
    private String egressApiUrl;

    @Value("${livekit.egress.s3.endpoint:http://127.0.0.1:9000}")
    private String s3Endpoint;

    @Value("${livekit.egress.s3.access-key:minioadmin}")
    private String s3AccessKey;

    @Value("${livekit.egress.s3.secret-key:minioadmin}")
    private String s3SecretKey;

    @Value("${livekit.egress.s3.region:us-east-1}")
    private String s3Region;

    @Value("${livekit.egress.s3.bucket:meeting-recordings}")
    private String s3Bucket;

    public LiveKitEgressService(LiveKitService liveKitService) {
        this.liveKitService = liveKitService;
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(5000);
        factory.setReadTimeout(30000);
        this.restTemplate = new RestTemplate(factory);
    }

    public Map<String, Object> startRoomComposite(String roomName, String objectPath) {
        Map<String, Object> s3 = new LinkedHashMap<>();
        s3.put("accessKey", s3AccessKey);
        s3.put("secret", s3SecretKey);
        s3.put("region", s3Region);
        s3.put("endpoint", s3Endpoint);
        s3.put("bucket", s3Bucket);
        s3.put("forcePathStyle", true);

        Map<String, Object> output = new LinkedHashMap<>();
        output.put("fileType", "MP4");
        output.put("filepath", objectPath);
        output.put("disableManifest", true);
        output.put("s3", s3);

        Map<String, Object> body = new LinkedHashMap<>();
        body.put("roomName", roomName);
        body.put("layout", "speaker");
        body.put("fileOutputs", List.of(output));
        body.put("preset", "H264_720P_30");

        return post("/twirp/livekit.Egress/StartRoomCompositeEgress", body, roomName);
    }

    public Map<String, Object> stop(String roomName, String egressId) {
        return post("/twirp/livekit.Egress/StopEgress", Map.of("egressId", egressId), roomName);
    }

    public Map<String, Object> listByEgressId(String roomName, String egressId) {
        return post("/twirp/livekit.Egress/ListEgress", Map.of("egressId", egressId), roomName);
    }

    @SuppressWarnings("unchecked")
    public Optional<Map<String, Object>> firstEgressItem(Map<String, Object> response) {
        Object items = response.get("items");
        if (items instanceof List<?> list && !list.isEmpty() && list.get(0) instanceof Map<?, ?> item) {
            return Optional.of((Map<String, Object>) item);
        }
        return Optional.empty();
    }

    public boolean isComplete(Map<String, Object> info) {
        return "EGRESS_COMPLETE".equals(String.valueOf(info.get("status"))) || "3".equals(String.valueOf(info.get("status")));
    }

    public boolean isFailed(Map<String, Object> info) {
        String status = String.valueOf(info.get("status"));
        return "EGRESS_FAILED".equals(status) || "EGRESS_ABORTED".equals(status) || "4".equals(status) || "5".equals(status);
    }

    private Map<String, Object> post(String path, Map<String, Object> body, String roomName) {
        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.APPLICATION_JSON);
        headers.setBearerAuth(liveKitService.generateRoomRecordToken(roomName));

        ResponseEntity<Map> response = restTemplate.exchange(
                egressApiUrl + path,
                HttpMethod.POST,
                new HttpEntity<>(body, headers),
                Map.class
        );
        return response.getBody() == null ? Map.of() : response.getBody();
    }
}
