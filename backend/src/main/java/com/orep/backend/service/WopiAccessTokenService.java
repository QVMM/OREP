package com.orep.backend.service;

import io.jsonwebtoken.Claims;
import io.jsonwebtoken.Jwts;
import io.jsonwebtoken.security.Keys;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;

/**
 * WOPI access_token：与 OREP 用户登录 JWT 分离用途，但可共用密钥材料。
 */
@Service
public class WopiAccessTokenService {

    @Value("${orep.jwt.secret}")
    private String secret;

    @Value("${orep.inspire-office.wopi-token-ttl-ms:3600000}")
    private long ttlMs;

    private SecretKey key() {
        return Keys.hmacShaKeyFor(secret.getBytes(StandardCharsets.UTF_8));
    }

    public String issue(long documentId, long userId, String username, boolean canWrite) {
        return Jwts.builder()
                .subject(String.valueOf(userId))
                .claim("purpose", "wopi")
                .claim("docId", documentId)
                .claim("username", username == null ? ("user-" + userId) : username)
                .claim("canWrite", canWrite)
                .issuedAt(new Date())
                .expiration(new Date(System.currentTimeMillis() + ttlMs))
                .signWith(key())
                .compact();
    }

    public WopiPrincipal parse(String token) {
        Claims claims = Jwts.parser()
                .verifyWith(key())
                .build()
                .parseSignedClaims(token)
                .getPayload();
        if (!"wopi".equals(claims.get("purpose", String.class))) {
            throw new SecurityException("invalid wopi token purpose");
        }
        long userId = Long.parseLong(claims.getSubject());
        Object docIdObj = claims.get("docId");
        long docId = docIdObj instanceof Number n ? n.longValue() : Long.parseLong(String.valueOf(docIdObj));
        String username = claims.get("username", String.class);
        Boolean canWrite = claims.get("canWrite", Boolean.class);
        return new WopiPrincipal(docId, userId, username, canWrite == null || canWrite);
    }

    public record WopiPrincipal(long documentId, long userId, String username, boolean canWrite) {
    }
}
