package com.orep.backend.service;

import com.orep.backend.entity.AiScoreMediaAsset;
import com.orep.backend.mapper.AiScoreMediaAssetMapper;
import io.minio.MinioClient;
import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

import java.io.ByteArrayInputStream;
import java.net.HttpURLConnection;
import java.net.URI;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;
import java.security.MessageDigest;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

class AiScoreMediaAssetMinioRoundtripTest {
    private static final String ENDPOINT = "http://127.0.0.1:9000";
    private static final String ACCESS = "minioadmin";
    private static final String SECRET = "minioadmin";
    private static final String BUCKET = "meeting-recordings";

    @TempDir
    Path tempDir;

    @BeforeEach
    void requireLiveMinio() {
        Assumptions.assumeTrue(minioLive(), "L13 需要本机 MinIO :9000");
    }

    @Test
    void objectStoreRoundtripHashMatchesLocalAndBinds() throws Exception {
        byte[] payload = "l13-minio-roundtrip".getBytes(StandardCharsets.UTF_8);
        String expected = sha256(payload);
        String objectName = "recordings/l13-roundtrip.webm";

        MinioClient client = MinioClient.builder()
                .endpoint(ENDPOINT)
                .credentials(ACCESS, SECRET)
                .build();
        MinioService minio = new MinioService(client, BUCKET);
        minio.ensureBucket();
        minio.uploadStream(objectName, new ByteArrayInputStream(payload), payload.length, "video/webm");

        AiScoreDocketService docketService = mock(AiScoreDocketService.class);
        AiScoreMediaAssetService service = new AiScoreMediaAssetService(
                mock(AiScoreMediaAssetMapper.class),
                tempDir.toString(),
                docketService,
                minio
        );

        AiScoreMediaAsset asset = service.registerMeetingRecordingAsset(
                101L, objectName, "l13-roundtrip.webm", "video/webm", null, 7L);

        assertNotNull(asset.getFileHash());
        assertEquals(expected, asset.getFileHash());
        assertEquals(payload.length, asset.getSizeBytes());
        verify(docketService).bindAfterVideoHash(eq(101L), eq(expected));
    }

    private static boolean minioLive() {
        try {
            HttpURLConnection connection = (HttpURLConnection) URI.create(ENDPOINT + "/minio/health/live").toURL().openConnection();
            connection.setConnectTimeout(400);
            connection.setReadTimeout(400);
            int code = connection.getResponseCode();
            connection.disconnect();
            return code >= 200 && code < 500;
        } catch (Exception ignored) {
            return false;
        }
    }

    private static String sha256(byte[] payload) throws Exception {
        byte[] hashed = MessageDigest.getInstance("SHA-256").digest(payload);
        StringBuilder hex = new StringBuilder();
        for (byte b : hashed) {
            hex.append(String.format("%02x", b));
        }
        return hex.toString();
    }
}
