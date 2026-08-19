package com.orep.backend.service;

import com.orep.backend.dto.DocketIdentity;
import org.springframework.stereotype.Service;

import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.util.Locale;

@Service
public class DocketIdService {

    public String docketId(DocketIdentity identity) {
        if (identity == null) {
            throw new IllegalArgumentException("docket identity cannot be null");
        }
        String videoSha256 = requiredLower(identity.getVideoSha256(), "videoSha256");
        String ruleVersion = requiredTrim(identity.getRuleVersion(), "ruleVersion");
        String ruleHash = requiredLower(identity.getRuleHash(), "ruleHash");
        String contractVersion = requiredTrim(identity.getContractVersion(), "contractVersion");
        String trackId = requiredTrim(identity.getTrackId(), "trackId");
        return sha256(
                "videoSha256=" + videoSha256
                        + "|ruleVersion=" + ruleVersion
                        + "|ruleHash=" + ruleHash
                        + "|contractVersion=" + contractVersion
                        + "|trackId=" + trackId
        );
    }

    private String requiredTrim(String value, String field) {
        if (value == null || value.isBlank()) {
            throw new IllegalArgumentException(field + " cannot be blank");
        }
        return value.trim();
    }

    private String requiredLower(String value, String field) {
        return requiredTrim(value, field).toLowerCase(Locale.ROOT);
    }

    private String sha256(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] hash = digest.digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder builder = new StringBuilder(hash.length * 2);
            for (byte b : hash) {
                builder.append(String.format("%02x", b));
            }
            return builder.toString();
        } catch (Exception e) {
            throw new IllegalStateException("failed to create docket id", e);
        }
    }
}
