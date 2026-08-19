package com.orep.backend.service;

import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;

@Service
public class LiveKitService {

    @Value("${livekit.api-key}")
    private String apiKey;

    @Value("${livekit.api-secret}")
    private String apiSecret;

    @Value("${livekit.ws-url}")
    private String wsUrl;

    /**
     * 生成 LiveKit 参会 token
     * LiveKit token 是标准 JWT，格式：
     * {
     *   "iss": "api_key",
     *   "sub": "identity",
     *   "name": "display name",
     *   "metadata": "{...}",
     *   "video": { "room_join": true, "room": "roomId", "can_publish": true, ... },
     *   "exp": timestamp,
     *   "nbf": timestamp
     * }
     */
    public String generateToken(String meetingId, Long userId, String username, String role) {
        SecretKey key = Keys.hmacShaKeyFor(apiSecret.getBytes(StandardCharsets.UTF_8));
        long now = System.currentTimeMillis();

        // video grant（camelCase，LiveKit 1.9.12+ 要求）
        Map<String, Object> videoGrant = new HashMap<>();
        videoGrant.put("roomJoin", true);
        videoGrant.put("room", meetingId);
        videoGrant.put("canPublish", true);
        videoGrant.put("canSubscribe", true);
        videoGrant.put("canPublishData", true);

        return Jwts.builder()
                .issuer(apiKey)
                .subject(userId.toString())
                .claim("name", username)
                .claim("metadata", "{\"role\":\"" + role + "\",\"username\":\"" + username + "\"}")
                .claim("video", videoGrant)
                .notBefore(new Date(now))
                .expiration(new Date(now + 3600 * 1000)) // 1小时
                .signWith(key)
                .compact();
    }

    public String generateRoomRecordToken(String roomName) {
        SecretKey key = Keys.hmacShaKeyFor(apiSecret.getBytes(StandardCharsets.UTF_8));
        long now = System.currentTimeMillis();

        Map<String, Object> videoGrant = new HashMap<>();
        videoGrant.put("roomRecord", true);
        videoGrant.put("room", roomName);

        return Jwts.builder()
                .issuer(apiKey)
                .subject("orep-egress-controller")
                .claim("video", videoGrant)
                .notBefore(new Date(now))
                .expiration(new Date(now + 2 * 3600 * 1000))
                .signWith(key)
                .compact();
    }

    public String getWsUrl() {
        return wsUrl;
    }
}
