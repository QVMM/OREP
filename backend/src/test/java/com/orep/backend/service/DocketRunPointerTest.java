package com.orep.backend.service;

import com.orep.backend.entity.AiScoreDocketRun;
import org.junit.jupiter.api.Test;

import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

class DocketRunPointerTest {

    @Test
    void olderSessionPointsToLatestRunWithoutChangingThisIndex() {
        DocketRunPointer.Pointer pointer = DocketRunPointer.from(List.of(
                run(1, 38L),
                run(7, 45L),
                run(9, 47L)
        ), 45L);
        assertEquals(7, pointer.thisRunIndex);
        assertEquals(47L, pointer.newerSessionId);
        assertEquals(9, pointer.newerRunIndex);
    }

    @Test
    void latestSessionHasNoNewerPointer() {
        DocketRunPointer.Pointer pointer = DocketRunPointer.from(List.of(
                run(7, 45L),
                run(9, 47L)
        ), 47L);
        assertEquals(9, pointer.thisRunIndex);
        assertNull(pointer.newerSessionId);
        assertNull(pointer.newerRunIndex);
    }

    @Test
    void unknownSessionDoesNotInventACurrentRun() {
        DocketRunPointer.Pointer pointer = DocketRunPointer.from(List.of(run(9, 47L)), 12L);
        assertNull(pointer.thisRunIndex);
        assertNull(pointer.newerSessionId);
    }

    private static AiScoreDocketRun run(int index, Long sessionId) {
        AiScoreDocketRun row = new AiScoreDocketRun();
        row.setRunIndex(index);
        row.setSessionId(sessionId);
        return row;
    }
}
