package com.orep.backend.service;

import org.junit.jupiter.api.Test;

import java.math.BigDecimal;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;

class DimensionScoreDeltaTest {

    @Test
    void missingJsonIsSkipped() {
        assertNull(DimensionScoreDelta.maxRatio(null, "{\"skill_level\":{\"score\":10,\"max_score\":60}}"));
        assertNull(DimensionScoreDelta.maxRatio("{}", "{}"));
    }

    @Test
    void reportsLargestRelativeDimensionMove() {
        String first = "{\"skill_level\":{\"score\":30.0,\"max_score\":60.0},\"professionalism\":{\"score\":5.0,\"max_score\":10.0}}";
        String current = "{\"skill_level\":{\"score\":27.0,\"max_score\":60.0},\"professionalism\":{\"score\":2.3,\"max_score\":10.0}}";
        BigDecimal ratio = DimensionScoreDelta.maxRatio(first, current);
        // professionalism 2.7/10 = 0.27 is larger than skill 3/60 = 0.05
        assertEquals(0, ratio.compareTo(new BigDecimal("0.2700")));
    }

    @Test
    void skipsBareNumberWithoutMax() {
        String first = "{\"技能水平\":80}";
        String current = "{\"技能水平\":84}";
        assertNull(DimensionScoreDelta.maxRatio(first, current));
    }
}
