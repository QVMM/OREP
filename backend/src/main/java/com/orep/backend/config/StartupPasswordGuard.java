package com.orep.backend.config;

import jakarta.annotation.PostConstruct;
import org.springframework.core.env.Environment;
import org.springframework.stereotype.Component;

import java.io.Console;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;

@Component
public class StartupPasswordGuard {

    private final Environment environment;

    public StartupPasswordGuard(Environment environment) {
        this.environment = environment;
    }

    @PostConstruct
    public void verifyStartupPassword() {
        String expectedHash = readSetting("OREP_STARTUP_PASSWORD_SHA256", "orep.startup.password-sha256");
        if (isBlank(expectedHash)) {
            return;
        }

        String password = readSetting("OREP_STARTUP_PASSWORD", "orep.startup.password");
        if (isBlank(password)) {
            Console console = System.console();
            if (console != null) {
                char[] chars = console.readPassword("OREP startup password: ");
                password = chars == null ? "" : new String(chars);
            }
        }

        if (isBlank(password) || !sha256(password).equalsIgnoreCase(expectedHash.trim())) {
            throw new IllegalStateException("OREP startup password verification failed.");
        }

        System.out.println("OREP startup password verification passed.");
    }

    private String readSetting(String envName, String propertyName) {
        String value = System.getenv(envName);
        if (!isBlank(value)) {
            return value;
        }
        return environment.getProperty(propertyName);
    }

    private static String sha256(String value) {
        try {
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            byte[] bytes = digest.digest(value.getBytes(StandardCharsets.UTF_8));
            StringBuilder builder = new StringBuilder(bytes.length * 2);
            for (byte b : bytes) {
                builder.append(String.format("%02x", b));
            }
            return builder.toString();
        } catch (Exception e) {
            throw new IllegalStateException("Unable to calculate startup password hash.", e);
        }
    }

    private static boolean isBlank(String value) {
        return value == null || value.trim().isEmpty();
    }
}
