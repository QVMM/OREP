package com.orep.backend.service;

/**
 * 打字时长口径：实际 elapsed_ms 才计入学习时长；
 * 排位未达门槛时降级为 practice，避免整场被拒导致「练了不算时间」。
 */
public final class TypingSessionPolicy {

    public static final String RANKED_MODE = "ranked";
    public static final String PRACTICE_MODE = "practice";
    public static final long RANKED_MIN_ELAPSED_MS = 120_000L;
    public static final int RANKED_MIN_CORRECT_CHARS = 20;

    private TypingSessionPolicy() {}

    public static String resolveMode(String requestedMode, long elapsedMs, int correctChars, String textVersion) {
        if (requestedMode == null || !RANKED_MODE.equalsIgnoreCase(requestedMode.trim())) {
            return PRACTICE_MODE;
        }
        if (elapsedMs < RANKED_MIN_ELAPSED_MS || correctChars < RANKED_MIN_CORRECT_CHARS) {
            return PRACTICE_MODE;
        }
        if (textVersion == null || textVersion.isBlank()) {
            return PRACTICE_MODE;
        }
        return RANKED_MODE;
    }

    /** 学情秒数只取实际练习毫秒，忽略配置目标 duration_sec。 */
    public static long actualSeconds(Long elapsedMs) {
        if (elapsedMs == null || elapsedMs <= 0L) return 0L;
        return elapsedMs / 1000L;
    }

    public static String normalizeClientSessionId(String raw) {
        if (raw == null) return null;
        String id = raw.trim();
        if (id.isEmpty()) return null;
        return id.length() > 64 ? id.substring(0, 64) : id;
    }
}
