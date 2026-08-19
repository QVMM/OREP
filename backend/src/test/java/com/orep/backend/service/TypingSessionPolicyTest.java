package com.orep.backend.service;

import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

class TypingSessionPolicyTest {

    @Test
    void rankedUnderTwoMinutesBecomesPracticeSoTimeStillCounts() {
        assertEquals("practice", TypingSessionPolicy.resolveMode("ranked", 90_000L, 80, "v1"));
    }

    @Test
    void rankedMeetingThresholdStaysRanked() {
        assertEquals("ranked", TypingSessionPolicy.resolveMode("ranked", 120_000L, 20, "v1"));
    }

    @Test
    void rankedMissingTextVersionCannotEnterBoard() {
        assertEquals("practice", TypingSessionPolicy.resolveMode("ranked", 180_000L, 40, "  "));
    }

    @Test
    void actualSecondsIgnoreConfiguredTargetDuration() {
        assertEquals(15L, TypingSessionPolicy.actualSeconds(15_400L));
        assertEquals(0L, TypingSessionPolicy.actualSeconds(0L));
        assertEquals(0L, TypingSessionPolicy.actualSeconds(null));
    }

    @Test
    void clientSessionIdIsTrimmedAndCapped() {
        assertNull(TypingSessionPolicy.normalizeClientSessionId("  "));
        assertEquals("tp_1", TypingSessionPolicy.normalizeClientSessionId(" tp_1 "));
        assertEquals(64, TypingSessionPolicy.normalizeClientSessionId("x".repeat(80)).length());
    }
}
