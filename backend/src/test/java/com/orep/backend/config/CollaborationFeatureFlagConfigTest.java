package com.orep.backend.config;

import org.junit.jupiter.api.Test;

import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;

import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

class CollaborationFeatureFlagConfigTest {

    @Test
    void collaborationDefaultsToEnabledButKeepsEnvironmentOverride() throws IOException {
        try (InputStream stream = getClass().getResourceAsStream("/application.yml")) {
            assertNotNull(stream);
            String config = new String(stream.readAllBytes(), StandardCharsets.UTF_8);
            assertTrue(config.contains("enabled: ${OREP_COLLABORATION_ENABLED:true}"));
        }
    }
}
